class MessagePack:
    def __init__(self, message='0' * 314):
         self.package_count = int(message[0:8], 2)
         self.timestamp = int(message[8:40], 2)
         self.voltage_28V = int(message[40:48], 2)
         self.voltage_5V = int(message[48:56], 2)
         self.voltage_12V = int(message[56:64], 2)
         self.voltage_24V = int(message[64:72], 2)
         self.current_5V = int(message[72:88], 2)
         self.current_12V = int(message[88:104], 2)
         self.current_24V = int(message[104:120], 2)
         self.ebox_temp = int(message[120:129], 2)
         self.pressure = int(message[129:145], 2)
         self.imu_mag_x = int(message[145:153], 2)
         self.imu_mag_y = int(message[153:161], 2)
         self.imu_mag_z = int(message[161:169], 2)
         self.imu_acc_x = int(message[169:177], 2)
         self.imu_acc_y = int(message[177:185], 2)
         self.imu_acc_z = int(message[185:193], 2)
         self.heater_1_status = int(message[193:196], 2)
         self.heater_2_status = int(message[196:199], 2)
         self.heater_3_status = int(message[199:202], 2)
         self.heater_4_status = int(message[202:205], 2)
         self.heater_5_status = int(message[205:208], 2)
         self.heater_6_status = int(message[208:211], 2)
         self.temp_1_status = int(message[211:220], 2)
         self.temp_2_status = int(message[220:229], 2)
         self.temp_3_status = int(message[229:238], 2)
         self.temp_4_status = int(message[238:247], 2)
         self.temp_5_status = int(message[247:256], 2)
         self.temp_6_status = int(message[256:265], 2)
         self.burn_wire_1_status = int(message[265:268], 2)
         self.burn_wire_2_status = int(message[268:271], 2)
         self.current_limiting_status = int(message[271:274], 2)
         self.rpi_1_status = int(message[274:277], 2)
         self.rpi_2_status = int(message[277:280], 2)
         self.rpi_3_status = int(message[280:283], 2)
         self.rpi_4_status = int(message[283:286], 2)
         self.motor_speed = int(message[286:302], 2)
         self.recording_mode_flag = int(message[302:305], 2)
         self.deployment_mode_flag = int(message[305:308], 2)
         self.auto_mode_flag = int(message[308:311], 2)
         self.motor_fault = int(message[311:314],2)
         self.rpi_IO_1 = 0
         self.rpi_IO_2 = 0
         self.rpi_IO_3 = 0
         self.rpi_IO_4 = 0
         self.motor_serial = 0
         self.C1 = 0
         self.C2 = 0
         self.C3 = 0
         self.C4 = 0
         self.SD1 = 0
         self.SD2 = 0
         self.SD3 = 0
         self.SD4 = 0

    def generateString(self):
        bits = [
           str(self.package_count),
           str(self.timestamp),
           str(self.voltage_28V),
           str(self.voltage_5V),
            str(self.voltage_12V),
            str(self.voltage_24V),
            str(self.current_5V),
            str(self.current_12V),
            str(self.current_24V),
            str(self.ebox_temp),
            str(self.pressure),
            str(self.imu_mag_x),
            str(self.imu_mag_y),
            str(self.imu_mag_z),
            str(self.imu_acc_x),
            str(self.imu_acc_y),
            str(self.imu_acc_z),
            str(self.heater_1_status),
            str(self.heater_2_status),
            str(self.heater_3_status),
            str(self.heater_4_status),
            str(self.heater_5_status),
            str(self.heater_6_status),
            str(self.temp_1_status),
            str(self.temp_2_status),
            str(self.temp_3_status),
            str(self.temp_4_status),
            str(self.temp_5_status),
            str(self.temp_6_status),
            str(self.burn_wire_1_status),
            str(self.burn_wire_2_status),
            str(self.current_limiting_status),
            str(self.rpi_IO_1),
            str(self.rpi_IO_2),
            str(self.rpi_IO_3),
            str(self.rpi_IO_4),
            str(self.motor_speed),
            str(self.recording_mode_flag),
            str(self.deployment_mode_flag),
            str(self.auto_mode_flag),
            str(self.motor_fault),
            str(self.rpi_1_status),
            str(self.rpi_2_status),
            str(self.rpi_3_status),
            str(self.rpi_4_status)
        ]
        return ','.join(bits)

    def HealthCheckupString(self):
        bits = [
            str(self.motor_serial),
            str(self.C1),
            str(self.C2),
            str(self.C3),
            str(self.C4),
            str(self.SD1),
            str(self.SD2),
            str(self.SD3),
            str(self.SD4)
        ]
        return ','.join(bits)
