import tkinter as tk
from detection import *
from pynput import keyboard
import time
import json
import threading

gesture_list = ["peace"]
root = tk.Tk()
current_profile = tk.IntVar()
current_profile_label = tk.StringVar()
profile_select:tk.Menu
loaded_profiles = {}
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

    global loaded_profiles
    global macro_list

    try:
        with open("config.json", 'r') as file:
            json_data = json.load(file)
            loaded_profiles = json_data["Profiles"]
            current_profile.set(json_data["default_profile"])
            current_profile_label.set(f"Profile: {loaded_profiles[str(current_profile.get())]['Name']}")
            macro_list = [Macro(gesture) for gesture in gesture_list]
            print(f"Loaded {current_profile_label.get()}")
            
    except FileNotFoundError:
        json_data = {"default_profile":0,"Profiles":{"0":{"Name":"Default", "Gestures":{}}}}
        for gesture in gesture_list:
            json_data["Profiles"]["0"]["Gestures"][gesture] = {}
            json_data["Profiles"]["0"]["Gestures"][gesture]["Events"] = []
        with open("config.json", 'w') as file:
            json.dump(json_data, file, indent=4)

        loaded_profiles = json_data["Profiles"]
        current_profile.set(json_data["default_profile"])
        current_profile_label.set(f"Profile: {loaded_profiles[str(current_profile.get())]['Name']}")

        profile_select.add_radiobutton(    
          label="Default",
            variable=current_profile,
            value=0,
            command=profile_changed
        )

    load_profile_radiobuttons()

    profiles.add_cascade(label = "Change Profile", menu = profile_select)
    profiles.add_command(label = "Edit Profile Name", command=lambda: edit_profile_name(root.winfo_x(), root.winfo_y()))
    profiles.add_command(label = "Create New Profile")
    profiles.add_command(label = "Import Profile")
    profiles.add_command(label = "Export Profile")
    profiles.add_command(label = "Delete Profile")

    settings = tk.Menu(menubar, tearoff = False)
    menubar.add_cascade(label = "Settings", menu = settings)
    settings.add_command(label = "Preferences", command = None)
    settings.add_checkbutton(label = "Run at Startup", command= None)

    root.config(menu = menubar)

    debug_frame = tk.Frame(root)
    debug_frame.pack(side=tk.BOTTOM, anchor="se", padx=5, pady=5)

    debug_toggle = tk.Checkbutton(debug_frame, text = "Enable Debug", height = 2, width = 10, command = toggle_debug) 
    debug_toggle.pack()

    profile_label = tk.Label(root, textvariable = current_profile_label)
    profile_label.pack(side=tk.TOP, anchor="nw", padx=10, pady=2)
   
    binding_frame = tk.Frame(root)
    binding_frame.pack(side=tk.TOP, anchor="nw", padx=5, pady=0)

    gesture_label = tk.Label(binding_frame, text="Gesture", font="Helvetica 10 bold")
    gesture_label.grid(row=0,column=0, padx=5,pady=0)

    macro_label = tk.Label(binding_frame, text="Macro", font="Helvetica 10 bold")
    macro_label.grid(row=0,column=1, padx=5,pady=0)

    #TODO: remake this to make each row instead of just one.
    #Probably pass the binding frame to a function that loops a list of gestures to create the rows and check if they have saves
    gesture_img = tk.PhotoImage(file="./icons/peace.png").subsample(4,4)
    gesture_icon = tk.Label(binding_frame, image=gesture_img, height=50, width=50)
    gesture_icon.grid(row=1,column=0)

    #TODO: Move record to col 2 and display an edit button in col1
    record_btn = tk.Button(binding_frame, text="Record", command=lambda: macro_list[0].open_record_window(root.winfo_x(), root.winfo_y()))
    record_btn.grid(row=1,column=1)

    #END ROW

    #Every 16ms get an updated list of detections
    def check_detections():
        detections = get_detections()
        for detection in detections:
            for macro in macro_list:
                if detection["name"] == macro.name:
                    if detection["confidence"] > 0.8 and not macro.active:
                        macro.start_playback()
                    
        root.after(16, check_detections)

    check_detections()
    root.mainloop()

#Reloads the macro_list with the settings from the new profile and changes the default profile
def profile_changed():
    global loaded_profiles
    global macro_list

    current_profile_label.set(f"Profile: {loaded_profiles[str(current_profile.get())]['Name']}")

    try:
        with open("config.json", 'r') as file:
            json_data = json.load(file)
    except FileNotFoundError:
        json_data = {}

    macro_list = [Macro(gesture) for gesture in gesture_list]
    loaded_profiles = json_data["Profiles"]
    json_data["default_profile"] = current_profile.get()

    with open("config.json", 'w') as file:
        json.dump(json_data, file, indent=4)
    
    print(f"Loaded {current_profile_label.get()}")
    root.update_idletasks()

#Refreshes the profiles available in the profile select menu
def load_profile_radiobuttons():
    profile_select.delete(0, 'end')

    for profile in loaded_profiles.keys():
        profile_select.add_radiobutton(    
            label=loaded_profiles[profile]["Name"],
            variable=current_profile,
            value=profile,
            command=profile_changed
        )

#Writes loaded_profiles to config
def save_profiles():
    try:
        with open("config.json", 'r') as file:
            json_data = json.load(file)
    except FileNotFoundError:
        json_data = {}

    json_data["Profiles"] = loaded_profiles

    with open("config.json", 'w') as file:
        json.dump(json_data, file, indent=4)

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

        loaded_profiles[str(current_profile.get())]['Name'] = new_name
        save_profiles()
        load_profile_radiobuttons()
        current_profile_label.set("Profile: " + new_name)

        popup.destroy()

    save = tk.Button(button_frame, text="Save", command=save_profile_name)
    save.pack(side="right", anchor="se", padx=5, pady=5)

    popup.focus()

class Macro:
    saved_macro: list["Event"] = []
    recording = []
    last_event_time = 0
    active = False

    #TODO: Instead of opening the file for each gesture this should read from a global variable loaded_profiles that holds the current config profiles
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
        #Reset recording and last_event_time incase there was a previous recording
        self.recording = []
        self.last_event_time = 0

        popup = tk.Toplevel()
        popup.wm_title = "Record Macro"
        popup.geometry(f"300x300+{x-20}+{y+20}")

        cancel = tk.Button(popup, text="Cancel", command=lambda: self.close_window(popup))
        cancel.pack(side=tk.RIGHT, anchor="se", padx=5, pady=5)
        
        save = tk.Button(popup, text="Save", command=lambda: self.save_and_close(popup))
        save.pack(side=tk.RIGHT, anchor="se", padx=5, pady=5)

        #Text box that shows events as they are recorded
        self.event_box = tk.Text(popup, height=6, width=40, state="disabled")
        self.event_box.pack(side=tk.TOP, anchor="n", expand=True, fill="both")

        popup.focus()
        self.record()

    #Record inputs until save/cancel are pressed
    def record(self):
        held_keys = set()

        #Handle a key being pressed
        def on_press(key):
            if key not in held_keys:
                held_keys.add(key)

                self.event_box.configure(state="normal")
                self.event_box.insert(tk.END, f"{key} pressed\n")
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

            self.event_box.configure(state="normal")
            self.event_box.insert(tk.END, f"{key} released\n")
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

    def load_save (self):
        self.saved_macro = []
        events = loaded_profiles[str(current_profile.get())]["Gestures"][self.name]["Events"]
        
        for event in events:
            try:
                self.saved_macro.append(Event(keyboard.HotKey.parse(event["key"])[0], event["delay"], event["pressed"]))
            except ValueError: 
                self.saved_macro.append(Event(keyboard.HotKey.parse(f"<{event['key']}>")[0], event["delay"], event["pressed"]))

    #Save recording and close the window
    def save_and_close (self, window: tk.Toplevel):
        self.saved_macro = self.recording
        self.print()
        self.close_window(window)
        
        new_events = []
        for event in self.saved_macro:
            try:
                new_events.append({"key" : event.key.char, "delay" : event.delay, "pressed" : event.pressed})
            except AttributeError:
                new_events.append({"key" : str(event.key)[4:], "delay" : event.delay, "pressed" : event.pressed})

        global loaded_profiles
        loaded_profiles[str(current_profile.get())]["Gestures"][self.name]["Events"] = new_events

        save_profiles()

    #Close the window and stop the keyboard listener thread
    def close_window (self, window: tk.Toplevel):
        window.destroy()
        self.listener.stop()

    #Start a thread to call playback
    def start_playback (self):
        play_thread = threading.Thread(target=self.playback, daemon=True)
        play_thread.start()

    #Play the saved macro
    def playback (self):
        self.active = True
        controller = keyboard.Controller()

        for event in self.saved_macro:
            time.sleep(event.delay)
            if event.pressed: 
                controller.press(event.key)
            else:
                controller.release(event.key)
        
        self.active = False
               
#A single event, either a key being pressed or released and the about of time in seconds since the last event.
class Event:

    def __init__ (self, key: keyboard.Key, delay: float, pressed: bool):
        self.key = key
        self.delay = delay
        self.pressed = pressed