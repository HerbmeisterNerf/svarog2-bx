import threading
import csv
from CommonData import CommonData
from PortCommunication import PortCommunication
from MessagePack import MessagePack


class LiveUpdatesTelemetry(threading.Thread):
    '''Parses an EBOX CSV telemetry string and updates the GUI table labels.'''

    def __init__(self, dataFormat, tableLabels, telem_str=""):
        super().__init__(daemon=True)
        self.current_packet = MessagePack()
        self.dataFormat = dataFormat
        self.tableLabels = tableLabels
        self.telem_str = telem_str

        if CommonData.firstCSV:
            columns = [
                'voltage_28V', 'voltage_5V', 'voltage_12V', 'voltage_24V',
                'current_5V', 'current_12V', 'current_24V', 'ebox_temp',
                'pressure', 'imu_mag_x', 'imu_mag_y', 'imu_mag_z',
                'imu_acc_x', 'imu_acc_y', 'imu_acc_z',
                'heater_1_status', 'heater_2_status', 'heater_3_status',
                'heater_4_status', 'heater_5_status', 'heater_6_status',
                'temp_1_status', 'temp_2_status', 'temp_3_status',
                'temp_4_status', 'temp_5_status', 'temp_6_status',
                'burn_wire_1_status', 'burn_wire_2_status',
                'current_limiting_status',
                'rz_1_status', 'rz_2_status', 'rz_3_status', 'rz_4_status',
                'motor_speed',
            ]
            try:
                with open(CommonData.outputTelemetryDir + 'telemOut.csv', 'w', newline='') as f:
                    csv.writer(f).writerow(columns)
            except Exception:
                pass
            CommonData.firstCSV = False

    def run(self):
        try:
            if self.telem_str:
                self.__process_telemetry(self.telem_str)
            self.__update_data_table()
        except Exception as e:
            print(f'LiveUpdatesTelemetry error: {e}')

    def __process_telemetry(self, string) -> None:
        v = string.split(",")
        if len(v) < 37:
            return
        setattr(self.current_packet, "voltage_28V",           v[2])
        setattr(self.current_packet, "voltage_5V",            v[3])
        setattr(self.current_packet, "voltage_12V",           v[4])
        setattr(self.current_packet, "voltage_24V",           v[5])
        setattr(self.current_packet, "current_5V",            v[6])
        setattr(self.current_packet, "current_12V",           v[7])
        setattr(self.current_packet, "current_24V",           v[8])
        setattr(self.current_packet, "ebox_temp",             v[9])
        setattr(self.current_packet, "pressure",              v[10])
        setattr(self.current_packet, "imu_mag_x",            v[11])
        setattr(self.current_packet, "imu_mag_y",            v[12])
        setattr(self.current_packet, "imu_mag_z",            v[13])
        setattr(self.current_packet, "imu_acc_x",            v[14])
        setattr(self.current_packet, "imu_acc_y",            v[15])
        setattr(self.current_packet, "imu_acc_z",            v[16])
        setattr(self.current_packet, "heater_1_status",      v[17])
        setattr(self.current_packet, "heater_2_status",      v[18])
        setattr(self.current_packet, "heater_3_status",      v[19])
        setattr(self.current_packet, "heater_4_status",      v[20])
        setattr(self.current_packet, "heater_5_status",      v[21])
        setattr(self.current_packet, "heater_6_status",      v[22])
        setattr(self.current_packet, "temp_1_status",        v[23])
        setattr(self.current_packet, "temp_2_status",        v[24])
        setattr(self.current_packet, "temp_3_status",        v[25])
        setattr(self.current_packet, "temp_4_status",        v[26])
        setattr(self.current_packet, "temp_5_status",        v[27])
        setattr(self.current_packet, "temp_6_status",        v[28])
        setattr(self.current_packet, "burn_wire_1_status",   v[29])
        setattr(self.current_packet, "burn_wire_2_status",   v[30])
        setattr(self.current_packet, "current_limiting_status", v[31])
        setattr(self.current_packet, "rpi_IO_1",             v[32])
        setattr(self.current_packet, "rpi_IO_2",             v[33])
        setattr(self.current_packet, "rpi_IO_3",             v[34])
        setattr(self.current_packet, "rpi_IO_4",             v[35])
        setattr(self.current_packet, "motor_speed",          v[36])

    def __formatdata(self) -> list:
        p = self.current_packet
        data = [
            float(p.voltage_28V),
            float(p.voltage_5V),
            float(p.voltage_12V),
            float(p.voltage_24V),
            float(p.current_5V),
            float(p.current_12V),
            float(p.current_24V),
            float(p.ebox_temp),
            float(p.pressure),
            float(p.imu_mag_x),
            float(p.imu_mag_y),
            float(p.imu_mag_z),
            float(p.imu_acc_x),
            float(p.imu_acc_y),
            float(p.imu_acc_z),
            int(p.heater_1_status),
            int(p.heater_2_status),
            int(p.heater_3_status),
            int(p.heater_4_status),
            int(p.heater_5_status),
            int(p.heater_6_status),
            float(p.temp_1_status),
            float(p.temp_2_status),
            float(p.temp_3_status),
            float(p.temp_4_status),
            float(p.temp_5_status),
            float(p.temp_6_status),
            int(p.burn_wire_1_status),
            int(p.burn_wire_2_status),
            int(p.current_limiting_status),
            int(p.rpi_IO_1),
            int(p.rpi_IO_2),
            int(p.rpi_IO_3),
            int(p.rpi_IO_4),
            float(p.motor_speed),
        ]
        return data

    def __update_data_table(self) -> None:
        data = self.__formatdata()
        for i in range(CommonData.telemetryParameters):
            colourBG, colourFG = update_data_table_colours(i, data, self.dataFormat)
            self.tableLabels[i].configure(text=data[i], bg=colourBG, fg=colourFG)
        if CommonData.outputTelemetry:
            self.__save_telemetry(data)

    def __save_telemetry(self, data) -> None:
        try:
            with open(CommonData.outputTelemetryDir + 'telemOut.csv', 'a', newline='') as f:
                csv.writer(f).writerow(data)
        except Exception:
            pass


def update_data_table_colours(i, data, dataFormat) -> tuple:
    colourFG = 'black'
    val = data[i]
    lo_red    = dataFormat.iloc[i, 1]
    lo_orange = dataFormat.iloc[i, 2]
    hi_orange = dataFormat.iloc[i, 3]
    hi_red    = dataFormat.iloc[i, 4]

    if val < lo_red or val > hi_red:
        colourBG = 'red'
    elif val < lo_orange or val > hi_orange:
        colourBG = 'orange'
    else:
        colourBG = 'green'
        colourFG = 'white'

    return colourBG, colourFG


if __name__ == '__main__':
    print('Cannot run this file directly')
