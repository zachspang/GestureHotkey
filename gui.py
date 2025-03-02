import tkinter as tk
from detection import *
import pynput

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

    gesture_img = tk.PhotoImage(file="./icons/peace.png").subsample(4,4)
    gesture_icon = tk.Label(binding_frame, image=gesture_img, height=50, width=50)
    gesture_icon.grid(row=1,column=0)

    record_btn = tk.Button(binding_frame, text="Record")
    record_btn.grid(row=1,column=1)

    root.mainloop()