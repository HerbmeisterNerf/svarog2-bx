NODE_ID = "CUBESAT"
NUM_SECONDARY_MPUS = 2
NUM_BW = 5
NUM_HEATERS = 2
NUM_TEMP_SENSORS = 6
UART_MOTOR_IDS = [0, 1]  # board 0 = flywheel, board 1 = deployment
# ESCs over USB CDC-ACM (B-G431B-ESC1): flywheel then deployment.
MOTOR_USB_DEVICES = ["/dev/ttyACM0", "/dev/ttyACM1"]

PERIPH_BINDINGS = {
    "BW_1": 0,
    "BW_2": 1,
    "BW_3": 2,
    "BW_4": 3,
    "BW_5": 4,
    "HEAT_1": 5,
    "HEAT_2": 6,
    "_UNUSED": 7,
}

HEATER_SENSOR_PAIRS = {
    "HEAT_1": 4,
    "HEAT_2": 5,
}
