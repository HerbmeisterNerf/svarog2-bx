class MessagePack:
    def __init__(self, message='0' * 311):
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

    def generateString(self):
        bits = [
            f'{self.package_count:08b}',
            f'{self.timestamp:032b}',
            f'{self.voltage_28V:08b}',
            f'{self.voltage_5V:08b}',
            f'{self.voltage_12V:08b}',
            f'{self.voltage_24V:08b}',
            f'{self.current_5V:016b}',
            f'{self.current_12V:016b}',
            f'{self.current_24V:016b}',
            f'{self.ebox_temp:09b}',
            f'{self.pressure:016b}',
            f'{self.imu_mag_x:08b}',
            f'{self.imu_mag_y:08b}',
            f'{self.imu_mag_z:08b}',
            f'{self.imu_acc_x:08b}',
            f'{self.imu_acc_y:08b}',
            f'{self.imu_acc_z:08b}',
            f'{self.heater_1_status:03b}',
            f'{self.heater_2_status:03b}',
            f'{self.heater_3_status:03b}',
            f'{self.heater_4_status:03b}',
            f'{self.heater_5_status:03b}',
            f'{self.heater_6_status:03b}',
            f'{self.temp_1_status:09b}',
            f'{self.temp_2_status:09b}',
            f'{self.temp_3_status:09b}',
            f'{self.temp_4_status:09b}',
            f'{self.temp_5_status:09b}',
            f'{self.temp_6_status:09b}',
            f'{self.burn_wire_1_status:03b}',
            f'{self.burn_wire_2_status:03b}',
            f'{self.current_limiting_status:03b}',
            f'{self.rpi_1_status:03b}',
            f'{self.rpi_2_status:03b}',
            f'{self.rpi_3_status:03b}',
            f'{self.rpi_4_status:03b}',
            f'{self.motor_speed:016b}',
            f'{self.recording_mode_flag:03b}',
            f'{self.deployment_mode_flag:03b}',
            f'{self.auto_mode_flag:03b}',
        ]
        return ''.join(bits)

