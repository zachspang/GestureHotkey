from threading import *
from gui import gui_window
from detection import detection_window

detection_thread = Thread(target=detection_window)
detection_thread.daemon = True

detection_thread.start()
gui_window()