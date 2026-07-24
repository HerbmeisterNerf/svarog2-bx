NODE_ID = "EBOX"
NUM_SECONDARY_MPUS = 4
NUM_BW = 4
NUM_HEATERS = 4
NUM_TEMP_SENSORS = 4
UART_MOTOR_IDS = [0]  # one Arduino (spinning motor)
# ESC over USB CDC-ACM (B-G431B-ESC1). One spinning motor on the EBOX.
MOTOR_USB_DEVICES = ["/dev/ttyACM0"]

PERIPH_BINDINGS = {
    "BW_1": 0,
    "BW_2": 1,
    "BW_3": 2,
    "BW_4": 3,
    "HEAT_1": 4,
    "HEAT_2": 5,
    "HEAT_3": 6,
    "HEAT_4": 7,
}

HEATER_SENSOR_PAIRS = {
    "HEAT_1": 0,
    "HEAT_2": 1,
    "HEAT_3": 2,
    "HEAT_4": 3,
}
