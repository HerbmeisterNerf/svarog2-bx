import threading

heater_ctrl = None
enc_reader = None
motor_reader = None
motor_speed = 0.0
auto_stop_enabled = True
auto_stop = None
telem_push_interval = 2.0
telem_push_lock = threading.Lock()
