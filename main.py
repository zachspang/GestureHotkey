from threading import *
from gui import gui_window
from detection import detection_window

t1 = Thread(target=gui_window)
t2 = Thread(target=detection_window)
t2.daemon = True

t1.start()
t2.start()