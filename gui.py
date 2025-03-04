import tkinter as tk
from detection import *
from pynput import keyboard
import time
import json

def gui_window():
    root = tk.Tk()
    root.title("GestureHotkey")
    root.geometry('200x300')
    
    debug_frame = tk.Frame(root)
    debug_frame.pack(side=tk.BOTTOM, anchor="se", padx=5, pady=5)

    debug_toggle = tk.Checkbutton(debug_frame, text = "Enable Debug", 
                    height = 2, 
                    width = 10,
                    command = toggle_debug) 
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

    macro = Macro([])

    #TODO: Move record to col 2 and display an edit button in col1
    record_btn = tk.Button(binding_frame, text="Record", command=macro.record)
    record_btn.grid(row=1,column=1)
    #END ROW
    root.mainloop()

class Macro:

    saved_macro = []
    recording = []
    last_event_time = 0

    def __init__ (self, initial_macro: list):
        self.saved_macro = initial_macro

        #These functions are used by the listener when key is pressed/released
        def on_press(key):
            print('{0} pressed'.format(key))
            if len(self.recording) == 0:
                self.recording.append(Event(key, 0, True))
                self.last_event_time = time.time_ns() / 1000000
            else:
                self.recording.append(Event(key, (time.time_ns() / 1000000) - self.last_event_time, True))
                self.last_event_time = time.time_ns() / 1000000

        def on_release(key):
            print('{0} released'.format(key))
            self.recording.append(Event(key, (time.time_ns() / 1000000) - self.last_event_time, False))
            self.last_event_time = time.time_ns() / 1000000

        self.listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release)
    
    #Print out all the events that were saved
    def print(self):
        for event in self.saved_macro:
            print(event.key, event.delay, event.is_pressed())

    #TODO: Display events as they are recorded so that the users know what they are pressing
    #Create a popup window and record inputs until save/cancel are pressed
    def record(self):
        popup = tk.Toplevel()
        popup.wm_title = "Record"
        popup.geometry("100x150")

        cancel = tk.Button(popup, text="Cancel", command=lambda: self.close_window(popup))
        cancel.pack(side=tk.RIGHT, anchor="se", padx=5, pady=5)

        save = tk.Button(popup, text="Save", command=lambda: self.save_and_close(popup))
        save.pack(side=tk.RIGHT, anchor="se", padx=5, pady=5)

        #TODO: !!!FIX Once the thread is stopped it cant be restarted, a single listener should be
        #passed to the init of the object. close_window needs to pause the thread instead of killing it 
        #https://stackoverflow.com/questions/51911554/how-to-stop-and-start-a-thread-at-will
        self.listener.start()

    def save_and_close (self, window: tk.Toplevel):
        self.saved_macro = self.recording
        self.print()
        self.close_window(window)

    def close_window (self, window: tk.Toplevel):
        window.destroy()
        self.listener.stop()

#A single event, either a key being pressed or released and the about of time in ms since the last event.
class Event():

    def __init__ (self, key: keyboard.Key, delay:float, pressed:bool):
        self.key = key
        self.delay = delay
        self.pressed = pressed

    def is_pressed (self):
        return self.pressed