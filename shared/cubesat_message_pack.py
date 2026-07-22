"""CubeSat telemetry packet — 34-field comma-separated format.

Field order must match ground_station/CubeSatPanel.py parser exactly.
"""


class CubeSatMessagePack:
    def __init__(self):
        self.package_count = 0
        self.timestamp = 0

        # PDU power (CubeSat has no 24V rail)
        self.voltage_28V = 0
        self.voltage_5V = 0
        self.voltage_12V = 0
        self.current_5V = 0
        self.current_12V = 0

        # Environment
        self.cs_temp = 0       # internal CubeSat temperature
        self.pressure = 0
        self.imu_mag_x = 0
        self.imu_mag_y = 0
        self.imu_mag_z = 0
        self.imu_acc_x = 0
        self.imu_acc_y = 0
        self.imu_acc_z = 0

        # Peripherals (2 heaters)
        self.heater_1_status = 0
        self.heater_2_status = 0

        # Temp sensors (6 distributed around CubeSat)
        self.temp_1_status = 0
        self.temp_2_status = 0
        self.temp_3_status = 0
        self.temp_4_status = 0
        self.temp_5_status = 0
        self.temp_6_status = 0

        # Burn wires (5 for sail deployment)
        self.bw_1_status = 0
        self.bw_2_status = 0
        self.bw_3_status = 0
        self.bw_4_status = 0
        self.bw_5_status = 0

        # Motors
        self.flywheel_speed = 0    # RPM from Arduino GS_0 response
        self.flywheel_mode = 0     # 0=off, 1=running
        self.deployment_fired = 0  # 0=armed, 1=fired
        self.motor_fault = 0

        # Secondary MPU health
        self.rz_1_status = 0
        self.rz_2_status = 0

        # Encoder (AS5047 absolute shaft angle, deg)
        self.encoder_angle = 0

    def generate_string(self):
        """Return comma-separated telemetry string in field order."""
        fields = [
            self.package_count,
            self.timestamp,
            self.voltage_28V,
            self.voltage_5V,
            self.voltage_12V,
            self.current_5V,
            self.current_12V,
            self.cs_temp,
            self.pressure,
            self.imu_mag_x,
            self.imu_mag_y,
            self.imu_mag_z,
            self.imu_acc_x,
            self.imu_acc_y,
            self.imu_acc_z,
            self.heater_1_status,
            self.heater_2_status,
            self.temp_1_status,
            self.temp_2_status,
            self.temp_3_status,
            self.temp_4_status,
            self.temp_5_status,
            self.temp_6_status,
            self.bw_1_status,
            self.bw_2_status,
            self.bw_3_status,
            self.bw_4_status,
            self.bw_5_status,
            self.flywheel_speed,
            self.flywheel_mode,
            self.deployment_fired,
            self.motor_fault,
            self.rz_1_status,
            self.rz_2_status,
            self.encoder_angle,
        ]
        return ",".join(str(f) for f in fields)
