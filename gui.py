import tkinter as tk
from detection import *
from pynput import keyboard
import time
import json
import threading

def gui_window():
    root = tk.Tk()
    root.title("GestureHotkey")
    root.geometry("200x300")
    
    debug_frame = tk.Frame(root)
    debug_frame.pack(side=tk.BOTTOM, anchor="se", padx=5, pady=5)

    debug_toggle = tk.Checkbutton(debug_frame, text = "Enable Debug", height = 2, width = 10, command = toggle_debug) 
    debug_toggle.pack()

    binding_frame = tk.Frame(root)
    binding_frame.pack(side=tk.LEFT, anchor="nw", padx=5, pady=5)

    gesture_label = tk.Label(binding_frame, text="Gesture", font="Helvetica 10 bold")
    gesture_label.grid(row=0,column=0, padx=5,pady=10)

    macro_label = tk.Label(binding_frame, text="Macro", font="Helvetica 10 bold")
    macro_label.grid(row=0,column=1, padx=5,pady=10)

    #TODO: remake this to make each row instead of just one.
    #Probably pass the binding frame to a function that loops a list of gestures to create the rows and check if they have saves
    gesture_img = tk.PhotoImage(file="./icons/peace.png").subsample(4,4)
    gesture_icon = tk.Label(binding_frame, image=gesture_img, height=50, width=50)
    gesture_icon.grid(row=1,column=0)

    macro = Macro("peace")

    #TODO: Move record to col 2 and display an edit button in col1
    record_btn = tk.Button(binding_frame, text="Record", command=lambda: macro.open_record_window(root.winfo_x(), root.winfo_y()))
    record_btn.grid(row=1,column=1)

    #Temp play button to test macro
    play_btn = tk.Button(binding_frame, text="Play", command=macro.start_playback)
    play_btn.grid(row=1,column=2)

    #END ROW
    root.mainloop()

class Macro:
    saved_macro: list["Event"] = []
    recording = []
    last_event_time = 0

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
            on_release=on_release)
        
        self.listener.start()

    def load_save (self):
        #TODO Handle file that isnt formatted correctly
        try:
            with open("config.json", 'r') as file:
                json_data = json.load(file)["Gestures"][self.name]["Events"]
        except FileNotFoundError:
            json_data = []
        
        for event in json_data:
            try:
                self.saved_macro.append(Event(keyboard.HotKey.parse(event["key"])[0], event["delay"], event["pressed"]))
            except ValueError: 
                self.saved_macro.append(Event(keyboard.HotKey.parse(f"<{event['key']}>")[0], event["delay"], event["pressed"]))

    #Save recording and close the window
    def save_and_close (self, window: tk.Toplevel):
        self.saved_macro = self.recording
        self.print()
        self.close_window(window)

        #TODO Handle file that isnt formatted correctly
        try:
            with open("config.json", 'r') as file:
                json_data = json.load(file)
        except FileNotFoundError:
            json_data = {"Gestures" : {self.name : {"Events" : []}}}
        
        new_data = []
        
        for event in self.saved_macro:
            try:
                new_data.append({"key" : event.key.char, "delay" : event.delay, "pressed" : event.pressed})
            except AttributeError:
                new_data.append({"key" : str(event.key)[4:], "delay" : event.delay, "pressed" : event.pressed})

        json_data["Gestures"][self.name]["Events"] = (new_data)

        with open("config.json", 'w') as file:
            json.dump(json_data, file, indent=4)

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
        controller = keyboard.Controller()

        for event in self.saved_macro:
            time.sleep(event.delay)
            if event.pressed: 
                controller.press(event.key)
            else:
                controller.release(event.key)
               
#A single event, either a key being pressed or released and the about of time in seconds since the last event.
class Event():

    def __init__ (self, key: keyboard.Key, delay: float, pressed: bool):
        self.key = key
        self.delay = delay
        self.pressed = pressed