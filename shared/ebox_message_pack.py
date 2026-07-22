"""EBOX telemetry packet — comma-separated TCP push format.

Field positions in generate_string() output (must match LiveUpdatesTelemetry parser):
  0: package_count   1: timestamp
  2: voltage_28V     3: voltage_5V     4: voltage_12V    5: voltage_24V (9V rail)
  6: current_5V      7: current_12V    8: current_24V
  9: ebox_temp      10: pressure
 11: imu_mag_x      12: imu_mag_y     13: imu_mag_z
 14: imu_acc_x      15: imu_acc_y     16: imu_acc_z
 17-22: heater_1..6_status
 23-28: temp_1..6_status
 29: burn_wire_1    30: burn_wire_2   31: current_lim_status
 32-35: rz_1..4_status
 36: motor_speed   37: encoder_angle (AS5047 shaft angle, deg)
"""


class EBoxMessagePack:
    def __init__(self):
        self.package_count = 0
        self.timestamp = 0
        self.voltage_28V = 0
        self.voltage_5V = 0
        self.voltage_12V = 0
        self.voltage_24V = 0   # 9V rail on EBOX hardware
        self.current_5V = 0
        self.current_12V = 0
        self.current_24V = 0
        self.ebox_temp = 0
        self.pressure = 0
        self.imu_mag_x = 0
        self.imu_mag_y = 0
        self.imu_mag_z = 0
        self.imu_acc_x = 0
        self.imu_acc_y = 0
        self.imu_acc_z = 0
        self.heater_1_status = 0
        self.heater_2_status = 0
        self.heater_3_status = 0
        self.heater_4_status = 0
        self.heater_5_status = 0
        self.heater_6_status = 0
        self.temp_1_status = 0
        self.temp_2_status = 0
        self.temp_3_status = 0
        self.temp_4_status = 0
        self.temp_5_status = 0
        self.temp_6_status = 0
        self.burn_wire_1_status = 0
        self.burn_wire_2_status = 0
        self.current_lim_status = 0
        self.rz_1_status = 0
        self.rz_2_status = 0
        self.rz_3_status = 0
        self.rz_4_status = 0
        self.motor_speed = 0
        self.encoder_angle = 0   # AS5047 absolute shaft angle (deg)

    def generate_string(self):
        fields = [
            self.package_count, self.timestamp,
            self.voltage_28V, self.voltage_5V, self.voltage_12V, self.voltage_24V,
            self.current_5V, self.current_12V, self.current_24V,
            self.ebox_temp, self.pressure,
            self.imu_mag_x, self.imu_mag_y, self.imu_mag_z,
            self.imu_acc_x, self.imu_acc_y, self.imu_acc_z,
            self.heater_1_status, self.heater_2_status, self.heater_3_status,
            self.heater_4_status, self.heater_5_status, self.heater_6_status,
            self.temp_1_status, self.temp_2_status, self.temp_3_status,
            self.temp_4_status, self.temp_5_status, self.temp_6_status,
            self.burn_wire_1_status, self.burn_wire_2_status,
            self.current_lim_status,
            self.rz_1_status, self.rz_2_status, self.rz_3_status, self.rz_4_status,
            self.motor_speed,
            self.encoder_angle,
        ]
        return ",".join(str(f) for f in fields)
