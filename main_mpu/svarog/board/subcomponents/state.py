import threading

heater_ctrl = None
telem_push_interval = 2.0
telem_push_lock = threading.Lock()
