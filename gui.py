import tkinter as tk
from tkinter.messagebox import askyesno
from tkinter import filedialog, ttk
from detection import *
from pynput import keyboard
import time
import json
from threading import Thread
import os
from icons import get_icon
import webbrowser
import cv2
from cv2_enumerate_cameras import enumerate_cameras
from PIL import ImageTk, Image, ImageDraw, ImageFont

gesture_list = ["peace", "fist", "call", "thumbs up", "thumbs down", "ok", "rock", "one", "three", "four", "palm", "stop"]
root = tk.Tk()
current_profile = tk.IntVar()
current_profile_label = tk.StringVar()
profile_select:tk.Menu
loaded_config = {}
macro_list = []

def gui_window():
    global root
    root.title("GestureHotkey")
    root.geometry("200x300")

    menubar = tk.Menu()

    profiles = tk.Menu(menubar, tearoff = False)
    menubar.add_cascade(label = "Profiles", menu = profiles)

    global profile_select
    profile_select = tk.Menu(menubar, tearoff=False)

    global loaded_config
    global macro_list

    try:
        with open("config.json", 'r') as file:
            loaded_config = json.load(file)
            current_profile.set(loaded_config["default_profile"])
            current_profile_label.set(f"Profile: {loaded_config['Profiles'][str(current_profile.get())]['Name']}")
            macro_list = [Macro(gesture) for gesture in gesture_list]
            print(f"Loaded {current_profile_label.get()}")
            
    except FileNotFoundError:
        loaded_config = {"default_profile":0,"default_cam":0,"Profiles":{"0":{"Name":"Default", "Gestures":{}}}}
        for gesture in gesture_list:
            loaded_config["Profiles"]["0"]["Gestures"][gesture] = {}
            loaded_config["Profiles"]["0"]["Gestures"][gesture]["Events"] = []
            loaded_config["Profiles"]["0"]["Gestures"][gesture]["min_confidence"] = 80
            loaded_config["Profiles"]["0"]["Gestures"][gesture]["reactivation_delay"] = 0
        with open("config.json", 'w') as file:
            json.dump(loaded_config, file, indent=4)

        current_profile.set(loaded_config["default_profile"])
        current_profile_label.set(f"Profile: {loaded_config['Profiles'][str(current_profile.get())]['Name']}")

        profile_select.add_radiobutton(    
          label="Default",
            variable=current_profile,
            value=0,
            command=profile_changed
        )
        macro_list = [Macro(gesture) for gesture in gesture_list]

    load_profile_radiobuttons()
    set_cam(loaded_config["default_cam"])

    profiles.add_cascade(label = "Change Profile", menu = profile_select)
    profiles.add_command(label = "Edit Profile Name", command=lambda: edit_profile_name(root.winfo_x(), root.winfo_y()))
    profiles.add_command(label = "Create New Profile", command=create_profile)
    profiles.add_command(label = "Import Profile", command=import_profile)
    profiles.add_command(label = "Export Profile", command=export_profile)
    profiles.add_command(label = "Delete Profile", command=delete_profile)

    settings = tk.Menu(menubar, tearoff = False)
    menubar.add_cascade(label = "Settings", menu = settings)
    settings.add_command(label = "Camera Settings", command = lambda: camera_settings(root.winfo_x(), root.winfo_y()))
    settings.add_checkbutton(label = "Run at Startup", command= None)

    menubar.add_command(label="About", command=lambda: about_popup(root.winfo_x(), root.winfo_y()))

    root.config(menu = menubar)

    debug_frame = tk.Frame(root)
    debug_frame.pack(side=tk.BOTTOM, anchor="se", padx=5, pady=5)

    debug_toggle = tk.Checkbutton(debug_frame, text = "Enable Debug", height = 2, width = 10, command = toggle_debug) 
    debug_toggle.pack()
   
    binding_frame = tk.Frame(root)
    binding_frame.pack(side=tk.TOP, anchor="nw", padx=5, pady=0, expand=True, fill="y")

    label_frame = tk.Frame(binding_frame)
    label_frame.pack(anchor="nw")
    
    profile_label = tk.Label(label_frame, textvariable = current_profile_label)
    profile_label.grid(row=0,column=0)

    gesture_label = tk.Label(label_frame, text="Gesture", font="Helvetica 10 bold")
    gesture_label.grid(row=1,column=0, sticky="w")

    macro_label = tk.Label(label_frame, text="Macro", font="Helvetica 10 bold")
    macro_label.grid(row=1,column=1, sticky="w")

    #binding_frame holds the labels and macro_canvas_frame which holds macro_canvas. macro_canvas has a scrollbar and holds macro_button_frame
    macro_canvas_frame = tk.Frame(binding_frame)
    macro_canvas_frame.pack(anchor="nw", expand=True, fill="y")
    binding_frame.grid_rowconfigure(1, weight=1)

    macro_canvas = tk.Canvas(macro_canvas_frame, width=140)
    scrollbar = tk.Scrollbar(macro_canvas_frame, orient="vertical", command=macro_canvas.yview)
    macro_canvas.configure(yscrollcommand=scrollbar.set)

    macro_button_frame = tk.Frame(macro_canvas)
    macro_button_frame.bind("<Configure>", lambda e:macro_canvas.configure(scrollregion=macro_canvas.bbox("all")))

    gesture_img_list = []
    for index, gesture in enumerate(gesture_list):
        gesture_img_list.append(tk.PhotoImage(data=get_icon(gesture)))        
        gesture_icon = tk.Label(macro_button_frame, image=gesture_img_list[index], height=50, width=50)
        gesture_icon.grid(row=index,column=0)
        
        edit_btn = tk.Button(macro_button_frame, text="Edit", command=lambda index=index: macro_list[index].open_edit_window(root.winfo_x(), root.winfo_y()))
        edit_btn.grid(row=index,column=1, padx=35)

    macro_canvas.create_window((0,0), window=macro_button_frame, anchor="nw")
    macro_canvas.pack(side="left", anchor="w", expand=True, fill="y")
    scrollbar.pack(side="left", anchor="w", expand=True, fill="y")

    def _on_mousewheel(event):
        macro_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    macro_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    previously_detected = []
    waiting_to_release = set()

    #Every 16ms get an updated list of detections
    def check_detections():
        nonlocal previously_detected
        detections = get_detections()
        currently_detected = [detection["name"] for detection in detections]

        #If a detection is no longer detected add it to a set. when the macro is done its keys will be released unless it is detected again while playing
        for detection in previously_detected:
            if detection not in currently_detected:
                waiting_to_release.add(detection)

        for macro in macro_list:
            for detection in detections:
                if macro.name == detection["name"]:
                    try:
                        waiting_to_release.remove(macro.name)
                    except KeyError:
                        pass

                    if detection["confidence"] > (macro.min_confidence / 100) and not macro.active:
                        macro.start_playback()

            if macro.name in waiting_to_release and not macro.active:
                macro.start_release()
                waiting_to_release.remove(macro.name)
        
        previously_detected = currently_detected
        root.after(16, check_detections)

    check_detections()
    root.mainloop()

#Reloads the macro_list with the settings from the new profile and changes the default profile
def profile_changed():
    global loaded_config
    global macro_list

    current_profile_label.set(f"Profile: {loaded_config['Profiles'][str(current_profile.get())]['Name']}")

    macro_list = [Macro(gesture) for gesture in gesture_list]
    loaded_config["default_profile"] = current_profile.get()
    save_config()
    
    print(f"Loaded {current_profile_label.get()}")
    root.update_idletasks()

#Refreshes the profiles available in the profile select menu
def load_profile_radiobuttons():
    profile_select.delete(0, 'end')

    for profile in loaded_config["Profiles"].keys():
        profile_select.add_radiobutton(    
            label=loaded_config["Profiles"][profile]["Name"],
            variable=current_profile,
            value=profile,
            command=profile_changed
        )

#Writes loaded_config to config
def save_config():
    with open("config.json", 'w') as file:
        json.dump(loaded_config, file, indent=4)

#Pops out a window where a user can change the name of a profile
def edit_profile_name(x,y):
    popup = tk.Toplevel()
    popup.wm_title = "Edit Profile Name"
    popup.geometry(f"200x80+{x-20}+{y+20}")
    
    text_frame = tk.Frame(popup)
    text_frame.pack(side = "top", fill = "x")

    label = tk.Label(text_frame, text="Profile Name: ")
    label.pack(side = "left")

    text_entry = tk.Entry(text_frame, bd = 5)
    text_entry.pack(side = "right")

    button_frame = tk.Frame(popup)
    button_frame.pack(side = "bottom", fill = "x")

    cancel = tk.Button(button_frame, text="Cancel", command=popup.destroy)
    cancel.pack(side="right", anchor="se", padx=5, pady=5)

    def save_profile_name():
        new_name = text_entry.get()
        if new_name == "":
            popup.destroy()
            return

        loaded_config["Profiles"][str(current_profile.get())]['Name'] = new_name
        save_config()
        load_profile_radiobuttons()
        current_profile_label.set("Profile: " + new_name)

        popup.destroy()

    save = tk.Button(button_frame, text="Save", command=save_profile_name)
    save.pack(side="right", anchor="se", padx=5, pady=5)

    popup.focus()

def create_profile():
    global loaded_config
    new_index = str(int(max(loaded_config["Profiles"].keys())) + 1)
    new_profile = {"Name":f"Profile {new_index}", "Gestures":{}}

    for gesture in gesture_list:
        new_profile["Gestures"][gesture] = {}
        new_profile["Gestures"][gesture]["Events"] = []
        new_profile["Gestures"][gesture]["min_confidence"] = 80
        new_profile["Gestures"][gesture]["reactivation_delay"] = 0

    loaded_config["Profiles"][new_index] = new_profile
    save_config()

    profile_select.add_radiobutton(    
        label=f"Profile {new_index}",
        variable=current_profile,
        value=new_index,
        command=profile_changed
    )

    current_profile.set(new_index)
    profile_changed()

#Prompts user to import a profile
def import_profile():
    file = filedialog.askopenfile(initialdir=os.getcwd(), filetypes=[("JSON files", "*.json")])

    if file:
        global loaded_config
        new_index = str(int(max(loaded_config["Profiles"].keys())) + 1)
        new_profile = json.load(file)

        loaded_config["Profiles"][new_index] = new_profile
        save_config()

        profile_select.add_radiobutton(    
            label=new_profile["Name"],
            variable=current_profile,
            value=new_index,
            command=profile_changed
        )

        current_profile.set(new_index)
        profile_changed()

#Prompts user to save current profile
def export_profile():
    file = filedialog.asksaveasfile(initialdir=os.getcwd(), initialfile="export.json", filetypes=[("JSON files", "*.json")])
    
    if file:
        json.dump(loaded_config["Profiles"][str(current_profile.get())], file, indent=4)

#Prompts user to delete current profile if there are more than 1 profile
def delete_profile():
    if len(loaded_config["Profiles"].keys()) == 1:
        return
    
    answer = askyesno(title="Confirmation", message=f"Permanently delete {loaded_config['Profiles'][str(current_profile.get())]['Name']}?")

    #Deletes profile and updates the keys of the other profiles so that continue to act as indexes
    if answer:
        loaded_config["Profiles"].pop(str(current_profile.get()))

        index = 0
        keys = list(loaded_config["Profiles"].keys())
        for key in keys:
            loaded_config["Profiles"][str(index)] = loaded_config["Profiles"].pop(key)
            index += 1

        save_config()
        current_profile.set(min(loaded_config["Profiles"].keys()))
        profile_changed()
        load_profile_radiobuttons()

def about_popup(x,y):
    def open_url(url):
        webbrowser.open_new_tab(url)

    popup = tk.Toplevel()
    popup.wm_title = "About"
    popup.geometry(f"230x200+{x-20}+{y+20}")

    title = tk.Label(popup, text="GestureHotkey v0.1")
    title.grid(row=0, column=0, padx=5, pady=5)

    hagrid_link = tk.Label(popup, font=('Arial',8,'bold','underline'), text= "HaGRID used for hand gesture detection", fg="blue", cursor="hand2")
    hagrid_link.grid(row=1, column=0, padx=5, pady=5)
    hagrid_link.bind("<Button-1>", lambda e:open_url("https://github.com/hukenovs/hagrid"))

    icons8_link = tk.Label(popup, font=('Arial',8,'bold','underline'), text = "Most gesture icons from Icons8", fg="blue", cursor="hand2")
    icons8_link.grid(row=2, column=0, padx=5, pady=5)
    icons8_link.bind("<Button-1>", lambda e:open_url("https://icons8.com/"))

    close = tk.Button(popup, text="Close", command=popup.destroy)
    close.grid(row=5, column=0, padx=5, pady=5)
    
def camera_settings(x,y):
    prev_cam = get_cam()
    #End detection thread
    set_cam(-1)

    popup = tk.Toplevel()
    cap:cv2.VideoCapture = None

    #Close the popup and start detection thread
    def close_window():
        if get_cam() == -1:
            set_cam(prev_cam)

        popup.destroy()

        detection_thread = Thread(target=detection_window, daemon=True)
        detection_thread.start()
    
    def save_and_close():
        set_cam(combo.current())
        loaded_config["default_cam"] = combo.current()
        save_config()
        close_window()

    popup.protocol("WM_DELETE_WINDOW", lambda: close_window())
    popup.wm_title = "Select Camera"
    popup.geometry(f"300x300+{x+5}+{y+20}")

    options = []
    for camera in enumerate_cameras(cv2.CAP_DSHOW):
        options.append(camera.name)

    combo = ttk.Combobox(popup, values=options, state="readonly")

    if loaded_config["default_cam"] < len(options):
        combo.current(loaded_config["default_cam"])  
    else:
        combo.current(0)  

    combo.pack()
    
    display_frame = tk.Frame(popup, bg = "black", width=250, height= 200)
    display_frame.pack(pady=10)

    image_label = tk.Label(display_frame, width=250, height= 200)
    image_label.pack()

    curr_cam_index = combo.current()
    starting_cap = False

    def video_stream():
        #Start a new capture
        def start_capture():
            nonlocal cap
            nonlocal starting_cap

            cap = cv2.VideoCapture(combo.current())
            starting_cap = False
        
        nonlocal cap
        nonlocal curr_cam_index
        nonlocal starting_cap

        start_cap = Thread(target=start_capture, daemon=True)

        #If the capture selected is not the one open, close it
        if cap and combo.current() != curr_cam_index:
            cap.release()
            cap = None
            curr_cam_index = combo.current()

        #Open a new capture if there is not one and one is not in the process of starting
        if not cap and not starting_cap:
            starting_cap = True
            start_cap.start()
        
        font = ImageFont.truetype('arial', 24)

        #If there is a capture read it and if the read is successful display it, if the read fails display a black screen, if there is no capture it must be starting so display loading
        if cap:
            success, frame = cap.read()
            if success:
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
                image = image.resize((250,200))
            else:
                image = Image.new(mode="RGB", size=(250,200))
                draw = ImageDraw.Draw(image)
                draw.text((0,0), "Could not start device.", (256,256,256), font=font)
        else:
            image = Image.new(mode="RGB", size=(250,200))
            draw = ImageDraw.Draw(image)
            draw.text((0,0), "Loading ...", (256,256,256), font=font)

        imageTk = ImageTk.PhotoImage(image=image)
        image_label.imageTk = imageTk
        image_label.configure(image=imageTk)

        image_label.after(16, video_stream)

    cancel = tk.Button(popup, text="Cancel", command=close_window)
    cancel.pack(side=tk.RIGHT, anchor="se", padx=5, pady=5)
    
    save = tk.Button(popup, text="Save", command=save_and_close)
    save.pack(side=tk.RIGHT, anchor="se", padx=5, pady=5)

    video_stream()
    popup.focus()

class Macro:
    saved_macro: list["Event"] = []
    lboxvar = tk.StringVar()
    min_confidence = 80
    reactivation_delay = 0
    recording = []
    last_event_time = 0
    active = False
    listener: keyboard.Listener = None

    def __init__ (self, name: str):
        self.name = name
        self.load_save()

    #Print out all the events that were saved
    def print(self):
        print("\nSaved the following events:")
        for event in self.saved_macro:
            print(event.key, str(round(event.delay, 2)) + "s", "Pressed" if event.pressed else "Released")

    #Create a popup window at coords x,y
    def open_record_window(self, x, y):
        #Record inputs until save/cancel are pressed
        def record():
            held_keys = set()

            #Handle a key being pressed
            def on_press(key):
                if key not in held_keys:
                    held_keys.add(key)

                    keyname = str(key)
                    if keyname[:4] == "Key.":
                        keyname = keyname[4:]
                        keyname = keyname.capitalize()
                        keyname = keyname.replace("_", " ")

                    self.event_box.configure(state="normal")
                    self.event_box.insert(tk.END, f"{keyname} pressed\n")
                    self.event_box.configure(state="disabled")
                    self.event_box.see(tk.END)

                    if len(self.recording) == 0:
                        self.recording.append(Event(key, 0, True))
                        self.last_event_time = time.time_ns() / 1000000000
                    else:
                        self.recording.append(Event(key, (time.time_ns() / 1000000000) - self.last_event_time, True))
                        self.last_event_time = time.time_ns() / 1000000000

            #Handle a key being released
            def on_release(key):
                held_keys.remove(key)
            
                keyname = str(key)
                if keyname[:4] == "Key.":
                    keyname = keyname[4:]
                    keyname = keyname.capitalize()
                    keyname = keyname.replace("_", " ")

                self.event_box.configure(state="normal")
                self.event_box.insert(tk.END, f"{keyname} released\n")
                self.event_box.configure(state="disabled")
                self.event_box.see(tk.END)

                self.recording.append(Event(key, (time.time_ns() / 1000000000) - self.last_event_time, False))
                self.last_event_time = time.time_ns() / 1000000000

            self.last_event_time = 0
            self.recording = []
            self.listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release,
                suppress=True)
            
            self.listener.start()

        #Reset recording and last_event_time incase there was a previous recording
        self.recording = []
        self.last_event_time = 0

        popup = tk.Toplevel()
        popup.wm_title = "Record Macro"
        popup.geometry(f"300x300+{x+5}+{y+20}")
        popup.protocol("WM_DELETE_WINDOW", lambda: self.close_window(popup))

        cancel = tk.Button(popup, text="Cancel", command=lambda: self.close_window(popup))
        cancel.pack(side=tk.RIGHT, anchor="se", padx=5, pady=5)
        
        save = tk.Button(popup, text="Save", command=lambda: self.save_and_close(popup))
        save.pack(side=tk.RIGHT, anchor="se", padx=5, pady=5)

        #Text box that shows events as they are recorded
        self.event_box = tk.Text(popup, height=6, width=40, state="disabled")
        self.event_box.pack(side=tk.TOP, anchor="n", expand=True, fill="both")

        popup.focus()
        record()

    def load_save (self):
        self.saved_macro = []
        self.min_confidence = loaded_config["Profiles"][str(current_profile.get())]["Gestures"][self.name]["min_confidence"]
        self.reactivation_delay = loaded_config["Profiles"][str(current_profile.get())]["Gestures"][self.name]["reactivation_delay"] = 0
        events = loaded_config["Profiles"][str(current_profile.get())]["Gestures"][self.name]["Events"]

        for event in events:
            try:
                self.saved_macro.append(Event(keyboard.HotKey.parse(event["key"])[0], event["delay"], event["pressed"]))
            except ValueError: 
                self.saved_macro.append(Event(eval(f"keyboard.Key.{event['key']}"), event["delay"], event["pressed"]))

    #Save recording and close the window
    def save_and_close (self, window: tk.Toplevel):
        self.save()
        self.close_window(window)
        
    #Save the macro
    def save(self):
        if len(self.recording) != 0:
            self.saved_macro = self.recording

        self.update_lbox()
        
        new_events = []
        for event in self.saved_macro:
            try:
                new_events.append({"key" : event.key.char, "delay" : event.delay, "pressed" : event.pressed})
            except AttributeError:
                new_events.append({"key" : str(event.key)[4:], "delay" : event.delay, "pressed" : event.pressed})

        global loaded_config
        loaded_config["Profiles"][str(current_profile.get())]["Gestures"][self.name]["Events"] = new_events
        loaded_config["Profiles"][str(current_profile.get())]["Gestures"][self.name]["min_confidence"] = self.min_confidence
        loaded_config["Profiles"][str(current_profile.get())]["Gestures"][self.name]["reactivation_delay"] = self.reactivation_delay

        save_config()

    #Close the window and stop the keyboard listener thread
    def close_window (self, window: tk.Toplevel):
        window.destroy()
        self.recording = []

        if self.listener:
            self.listener.stop()

    #Start a thread to call playback
    def start_playback (self):
        #Play the saved macro
        def playback ():
            self.active = True
            controller = keyboard.Controller()

            for event in self.saved_macro:
                time.sleep(event.delay)
                if event.pressed: 
                    controller.press(event.key)
                else:
                    controller.release(event.key)
            
            time.sleep(self.reactivation_delay)

            self.active = False

        play_thread = Thread(target=playback, daemon=True)
        play_thread.start()
    
    #Start a thread to release all held keys
    def start_release(self):
        def release():
            controller = keyboard.Controller()
            for event in self.saved_macro:
                controller.release(event.key)

        release_thread = Thread(target=release, daemon=True)
        release_thread.start()

    def update_lbox(self):
        new_lbox = []
        for event in self.saved_macro:
            list_string = str(event.key)
            if list_string[:4] == "Key.":
                list_string = list_string[4:]
                list_string = list_string.capitalize()
                list_string = list_string.replace("_", " ")
            else:
                list_string = list_string[1:-1]

            if event.pressed:
                list_string = "\u2193 " + list_string
            else:
                list_string = "\u2191 " + list_string

            new_lbox.append(list_string)
        self.lboxvar.set(new_lbox)

    def open_edit_window(self,x,y):
        popup = tk.Toplevel()
        popup.wm_title = "Edit Macro"
        popup.geometry(f"400x350+{x+5}+{y+20}")

        #Event Listbox
        self.update_lbox()
        lbox = tk.Listbox(popup, listvariable=self.lboxvar, width=10, height=12, font="Helvetica 14 bold", selectmode=tk.SINGLE, exportselection=False)
        lbox.pack(padx=5, side="left")

        gesture_settings_frame = tk.Frame(popup)

        #Confidence Slider
        confindence_label = tk.Label(gesture_settings_frame, text="Minimum Confidence:")
        confindence_label.grid(row=0, column=0, pady=(10,0))

        def min_confidence_changed(_):
            self.min_confidence = confidence_slider.get()
            self.save()

        confidence_slider = tk.Scale(gesture_settings_frame, from_=0, to=100, orient="horizontal", command=min_confidence_changed)
        confidence_slider.set(self.min_confidence)
        confidence_slider.grid(row=0, column=1)

        #Reactivation delay
        reactivation_label = tk.Label(gesture_settings_frame, text="How many seconds after macro \nends can be activated again: ")
        reactivation_label.grid(row=1, column=0)

        def validate_entry(new_entry):
            if not new_entry:
                return True
            try:
                float(new_entry)
                return True
            except ValueError:
                return False
            
        def reactivation_changed(event):
            entry = event.widget.get()
            if entry == "":
                self.reactivation_delay = 0
            else:
                self.reactivation_delay = float(entry)
            self.save()
            
        vcmd = popup.register(validate_entry)
        reactivation_entry = tk.Entry(gesture_settings_frame, validate="key", validatecommand=(vcmd, "%P",), width=10)
        reactivation_entry.grid(row=1,column=1)
        reactivation_entry.bind("<KeyRelease>", reactivation_changed)

        #Record button
        record = tk.Button(gesture_settings_frame, text="Record from keyboard", command=lambda: self.open_record_window(popup.winfo_x(), popup.winfo_y()))
        record.grid(row=2, column=0, pady=5)

        gesture_settings_frame.pack()

        event_settings_frame = tk.Frame(popup)
        event_settings_label = tk.Label(event_settings_frame, text="Settings for individual key:")
        event_settings_label.grid(row=0, column=0)

        event_properties_frame = tk.Frame(event_settings_frame)

        #key_selection combobox that lets users change the key of an event
        all_keys = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 
                    'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '!', '"', '#', '$', '%', '&', 
                    "'", '(', ')', '*', '+', ',', '-', '.', '/', ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', 
                    '`', '{', '|', '}', '~', 'Alt', 'Alt l', 'Alt r', 'Alt gr', 'Backspace', 'Caps lock', 'Cmd', 'Cmd r', 'Ctrl', 
                    'Ctrl l', 'Ctrl r', 'Delete', 'Down', 'End', 'Enter', 'Esc', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 
                    'F9', 'F10', 'F11', 'F12', 'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'F20', 'F21', 'F22', 'F23', 'F24', 
                    'Home', 'Left', 'Page down', 'Page up', 'Right', 'Shift', 'Shift r', 'Space', 'Tab', 'Up', 'Media play pause', 
                    'Media stop', 'Media volume mute', 'Media volume down', 'Media volume up', 'Media previous', 'Media next', 'Insert', 
                    'Menu', 'Num lock', 'Pause', 'Print screen', 'Scroll lock'
                ]
        
        def key_changed(event):
            new_key:str = event.widget.get()
            new_key = new_key.replace(" ", "_").lower()
            try:
                new_key = keyboard.HotKey.parse(new_key)[0]
            except ValueError:
                new_key = eval(f"keyboard.Key.{new_key}")
            self.saved_macro[lbox.curselection()[0]].key = new_key
            self.save()

        key_selection_label = tk.Label(event_properties_frame, text="Key to activate:")
        key_selection_label.grid(row=0,column=0)

        key_selection = ttk.Combobox(event_properties_frame, values=all_keys, state="disabled")
        key_selection.grid(row=0, column=1)
        key_selection.bind("<<ComboboxSelected>>", key_changed)

        #delay_entry text box that lets users change delay of an event
        delay_entry_label = tk.Label(event_properties_frame, text="Seconds before \n key is activated:")
        delay_entry_label.grid(row=1,column=0)

        def delay_changed(event):
            entry = event.widget.get()
            if entry == "":
                self.saved_macro[lbox.curselection()[0]].delay = 0
            else:
                self.saved_macro[lbox.curselection()[0]].delay = float(entry)
            self.save()

        delay_entry = tk.Entry(event_properties_frame, state="readonly", validate="key", validatecommand=(vcmd, "%P",))
        delay_entry.grid(row=1,column=1)
        delay_entry.bind("<KeyRelease>", delay_changed)

        #Press/release toggle
        pressed_label = tk.Label(event_properties_frame, text="Press or release key:")
        pressed_label.grid(row=2,column=0)

        pressed_frame = tk.Frame(event_properties_frame)
        pressed_var = tk.BooleanVar(value=True)

        def toggle_press(_var, _index, _mode):
            if len(self.saved_macro) != 0 and lbox.curselection() and self.saved_macro[lbox.curselection()[0]].pressed != pressed_var.get():
                self.saved_macro[lbox.curselection()[0]].pressed = pressed_var.get()
                self.save()

        pressed_var.trace_add("write", toggle_press)

        pressed_button = tk.Radiobutton(pressed_frame, text="Press", variable=pressed_var, value=True, state="disabled")
        pressed_button.grid(row=0, column=0)
        released_button = tk.Radiobutton(pressed_frame, text="Release", variable=pressed_var, value=False, state="disabled")
        released_button.grid(row=1, column=0)

        pressed_frame.grid(row=2,column=1)
        event_properties_frame.grid(row=1, column=0)

        move_button_frame = tk.Frame(event_settings_frame)

        #Buttons to rearrange events
        def move_up():
            index = lbox.curselection()[0]
            if index == 0:
                return
            temp = self.saved_macro[index]
            self.saved_macro[index] = self.saved_macro[index - 1]
            self.saved_macro[index - 1] = temp

            lbox.selection_clear(0, tk.END)
            lbox.activate(index - 1)
            lbox.selection_set(index - 1)

            self.save()

        def move_down():
            index = lbox.curselection()[0]
            if index == len(self.saved_macro) - 1:
                return
            temp = self.saved_macro[index]
            self.saved_macro[index] = self.saved_macro[index + 1]
            self.saved_macro[index + 1] = temp

            lbox.selection_clear(0, tk.END)
            lbox.activate(index + 1)
            lbox.selection_set(index + 1)

            self.save()

        up_button = tk.Button(move_button_frame, text="^", height=1,width=3, font="Helvetica 20 bold", command=move_up, state="disabled")
        up_button.grid(row=0,column=2)

        down_button = tk.Button(move_button_frame, text="v", height=1,width=3, font="Helvetica 20 bold", command= move_down, state="disabled")
        down_button.grid(row=0,column=3)

        #Buttons to add and delete events
        def add_event():
            if lbox.curselection():
                index = lbox.curselection()[0]
            else:
                index = 0
            self.saved_macro.insert(index, Event(key=keyboard.HotKey.parse("0")[0],delay=0, pressed=True))

            lbox.selection_clear(0, tk.END)
            lbox.activate(index)
            lbox.selection_set(index)
            lbox.event_generate('<<ListboxSelect>>')

            self.save()

        def remove_event():
            index = lbox.curselection()[0]
            self.saved_macro.pop(index)

            lbox.selection_clear(0, tk.END)
            lbox.activate(index)
            lbox.selection_set(index)
            lbox.event_generate('<<ListboxSelect>>')

            self.save()

        add_button = tk.Button(move_button_frame, text="+", height=1,width=3, font="Helvetica 20 bold", command=add_event, state="normal")
        add_button.grid(row=0,column=0)

        del_button = tk.Button(move_button_frame, text="-", height=1,width=3, font="Helvetica 20 bold", command=remove_event, state="disabled")
        del_button.grid(row=0,column=1)

        move_button_frame.grid(row=2, column=0, pady=5)
        event_settings_frame.pack(side="bottom")

        def item_selected(event):
            if not event.widget.curselection() or len(self.saved_macro) == 0:
                #Reset key_selection
                key_selection.current(0)
                key_selection.configure(state="disabled")

                #Reset delay_entry
                delay_entry.delete(0, tk.END)
                delay_entry.configure(state="readonly")

                #Reset press/release
                pressed_var.set(True)
                pressed_button.configure(state="disabled")
                released_button.configure(state="disabled")

                #Disable rearrange buttons
                up_button.configure(state="disabled")
                down_button.configure(state="disabled")

                #Disable del button
                del_button.configure(state="disabled")
                return
            selection = self.saved_macro[event.widget.curselection()[0]]
            
            #update key_selection
            keyname = str(selection.key)
            if keyname[:4] == "Key.":
                keyname = keyname[4:]
                keyname = keyname.capitalize()
                keyname = keyname.replace("_", " ")
            else:
                keyname = keyname[1:-1]

            key_selection.configure(state="readonly")
            key_selection.current(all_keys.index(keyname))

            #update delay
            delay_entry.configure(state="normal")
            delay_entry.delete(0, tk.END)
            delay_entry.insert(0, round(selection.delay, 3))

            #update press/release
            pressed_button.configure(state="normal")
            released_button.configure(state="normal")
            pressed_var.set(selection.pressed)

            #Enable rearrange buttons
            up_button.configure(state="normal")
            down_button.configure(state="normal")

            #Enable del button
            del_button.configure(state="normal")

        lbox.bind('<<ListboxSelect>>', item_selected)

#A single event, either a key being pressed or released and the about of time in seconds since the last event.
class Event:

    def __init__ (self, key: keyboard.Key, delay: float, pressed: bool):
        self.key = key
        self.delay = delay
        self.pressed = pressed