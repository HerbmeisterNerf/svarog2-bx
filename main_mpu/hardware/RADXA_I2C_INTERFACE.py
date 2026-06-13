import mraa
import time
import threading

import declarations

class I2CInterface:
    def __init__(self, i2c_bus=1): #bus 1 for ports 3 and 5
        """Initialize I2C bus and sensors."""
        self.i2c_bus = mraa.I2c(i2c_bus)
        self._lock = threading.Lock()  # shared bus — serialize all reads/writes

        # Pressure Sensor
        self.lps22hb_addr = 0x5C
        self.LPS_CTRL_REG1 = 0x10
        self.LPS_PRESS_OUT_XL = 0x28

        # IMU
        self.mc6470_acc_addr = 0x4C #Assuming A5 pin on GND
        self.XOUT_EX_L = 0x0D
        self.ACC_OUTCFG = 0x20

        self.mc6470_mag_addr = 0x0C #Default for mag
        self.XOUT_LSB = 0x10

        self.MC_CHIP_ID_REG = 0x40 #Needs verification

        # All three devices share one bus object; lock before switching address
        self.lps22hb = self.i2c_bus
        self.lps22hb.address(self.lps22hb_addr)

        self.imu_acc = self.i2c_bus
        self.imu_acc.address(self.mc6470_acc_addr)

        self.imu_mag = self.i2c_bus
        self.imu_mag.address(self.mc6470_mag_addr)
        
        # Initialize sensors
        self.initialize_lps22hb()
        self.initialize_mc6470()
        
    def initialize_lps22hb(self):
        """Initialize the LPS22HB pressure sensor."""
        # Using default values
        return

    def initialize_mc6470(self):
        """Initialize the MC6470 accelerometer. Magnetometer does not need initialization."""
        config = self.lps22hb.readBytesReg(self.ACC_OUTCFG,1)
        desiredConfig = 0x35 # Setting the range to +-16g and 14-bit measurements
        newConfig = desiredConfig | (config & 1 << 3)
        self.lps22hb.writeReg(self.ACC_OUTCFG, newConfig)
        return

    def read_pressure(self):
        """Read pressure from the LPS22HB sensor."""
        with self._lock:
            self.lps22hb.address(self.lps22hb_addr)
            data = self.lps22hb.readBytesReg(self.LPS_PRESS_OUT_XL, 3)
        raw_press = data[2] << 16 | data[1] << 8 | data[0]
        if raw_press & 0x800000:
            raw_press -= 1 << 24
        return raw_press / 4096.0

    def read_mc6470_chip_id(self):
        """Read the MC6470 chip ID."""
        with self._lock:
            self.imu_acc.address(self.mc6470_acc_addr)
            return self.imu_acc.readReg(self.MC_CHIP_ID_REG)

    def read_accelerometer_data(self):
        """Read raw data from the accelerometer."""
        with self._lock:
            self.imu_acc.address(self.mc6470_acc_addr)
            acc_out = self.imu_acc.readBytesReg(self.XOUT_EX_L, 6)

        x_acc = acc_out[1] << 8 | acc_out[0]
        if x_acc & 0x8000:
            x_acc -= 1 << 16
        y_acc = acc_out[3] << 8 | acc_out[2]
        if y_acc & 0x8000:
            y_acc -= 1 << 16
        z_acc = acc_out[5] << 8 | acc_out[4]
        if z_acc & 0x8000:
            z_acc -= 1 << 16

        sensitivity = 0.512  # 1/(32000mg/2^14bits)
        return x_acc / sensitivity, y_acc / sensitivity, z_acc / sensitivity

    def read_magnetometer_data(self):
        """Read raw data from the magnetometer."""
        with self._lock:
            self.imu_mag.address(self.mc6470_mag_addr)
            mag_out = self.imu_mag.readBytesReg(self.XOUT_LSB, 6)

        x_mag = mag_out[1] << 8 | mag_out[0]
        if x_mag & 0x8000:
            x_mag -= 1 << 16
        y_mag = mag_out[3] << 8 | mag_out[2]
        if y_mag & 0x8000:
            y_mag -= 1 << 16
        z_mag = mag_out[5] << 8 | mag_out[4]
        if z_mag & 0x8000:
            z_mag -= 1 << 16

        sensitivity = 0.15
        return x_mag / sensitivity, y_mag / sensitivity, z_mag / sensitivity  # uT

if __name__ == "__main__":
    sensor_interface = I2CInterface()

    # Read sensor data
    pressure = sensor_interface.read_pressure()
    chip_id = sensor_interface.read_mc6470_chip_id()
    acc = sensor_interface.read_accelerometer_data()
    mag_field = sensor_interface.read_magnetometer_data()
    
    # Output the results
    print(f"Pressure_hPa = {pressure:.2f}")
    print(f"xAcceleration_mg = {acc[0]:.2f}")
    print(f"yAcceleration_mg = {acc[1]:.2f}")
    print(f"zAcceleration_mg = {acc[2]:.2f}")
    print(f"xMagField_uT = {mag_field[0]:.2f}")
    print(f"yMagField_uT = {mag_field[1]:.2f}")
    print(f"zMagField_uT = {mag_field[2]:.2f}")

    time.sleep(0.01) #Needs to be decided on a higher level
