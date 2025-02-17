from tkinter import *
from detection import *
def gui_window():
    root = Tk()
    root.title("GestureHotkey")
    root.geometry('400x200')
    debug_toggle = Checkbutton(root, text = "Enable Debug", 
                    variable = debug, 
                    onvalue = True, 
                    offvalue = False, 
                    height = 2, 
                    width = 10,
                    command = toggle_debug) 
    debug_toggle.pack()

    root.mainloop()