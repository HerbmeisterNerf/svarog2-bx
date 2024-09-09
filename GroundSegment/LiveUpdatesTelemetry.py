############ standard libraries ############
import threading
import pandas as pd

############ custom libraries ############
from CommonData import CommonData
from PortCommunication import PortCommunication

############ class ############
class LiveUpdatesTelemetry(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self, queue, 
                current_packet,
                dataFormat,
                tableLabels):
        super().__init__()
        self.queue = queue
        self.current_packet = current_packet
        self.dataFormat = dataFormat
        self.tableLabels = tableLabels
        self.telemOut_df = pd.DataFrame([[
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ]], columns = [[
            'voltage_28V',
            'voltage_5V',
            'voltage_12V',
            'voltage_24V',
            'current_5V',
            'current_12V',
            'current_24V',
            'ebox_temp',
            'pressure',
            'imu_mag_x',
            'imu_mag_y',
            'imu_mag_z',
            'imu_acc_x',
            'imu_acc_y',
            'imu_acc_z',
            'heater_1_status',
            'heater_2_status',
            'heater_3_status',
            'heater_4_status',
            'heater_5_status',
            'heater_6_status',
            'temp_1_status',
            'temp_2_status',
            'temp_3_status',
            'temp_4_status',
            'temp_5_status',
            'temp_6_status',
            'burn_wire_1_status',
            'burn_wire_2_status',
            'current_limiting_status',
            'rpi_1_status',
            'rpi_2_status',
            'rpi_3_status',
            'rpi_4_status',
            'motor_speed',
            'recording_mode_flag',
            'deployment_mode_flag',
            'auto_mode_flag',
            'motor_fault'
        ]])
        self.telemOut_df.to_csv(CommonData.outputTelemetryDir + 'telemOut.csv', header=True, mode="w")

############ Methods ############

    def run(self):
        try:
            if CommonData.TCPSTATUS == True:
                self.__request_telemetry()
                self.__update_data_table()
            else:
                print("Not connected to server")
        except Exception as e:
            print(f'An exception occurred: {e}')

    def __request_telemetry(self) -> None:
        client_UDP_socket = PortCommunication.open_UDP(CommonData.telemetry_port_UDP) 
        message = "start:TEend:"
        CommonData.client_TCP_socket.send(message.encode())
        bytes_read = client_UDP_socket.recvfrom(1024)
        telem =  bytes_read[0].decode("utf-8")
        self.__process_telemetry(telem)
        PortCommunication.close_UDP(client_UDP_socket)

    def __process_telemetry(self,string) -> None:
        variables = string.split(",")
        for each in variables:
            var,val = each.split("=")
            setattr(self.current_packet,var,val)

    def __formatdata(self) -> list:
        data = []
        data.insert(0,float(self.current_packet.voltage_28V))
        data.insert(1,float(self.current_packet.voltage_5V))
        data.insert(2,float(self.current_packet.voltage_12V))
        data.insert(3,float(self.current_packet.voltage_24V))
        data.insert(4,float(self.current_packet.current_5V))
        data.insert(5,float(self.current_packet.current_12V))
        data.insert(6,float(self.current_packet.current_24V))
        data.insert(7,float(self.current_packet.ebox_temp))
        data.insert(8,float(self.current_packet.pressure))
        data.insert(9,float(self.current_packet.imu_mag_x))
        data.insert(10,float(self.current_packet.imu_mag_y))
        data.insert(11,float(self.current_packet.imu_mag_z))
        data.insert(12,float(self.current_packet.imu_acc_x))
        data.insert(13,float(self.current_packet.imu_mag_y))
        data.insert(14,float(self.current_packet.imu_mag_z))
        data.insert(15,int(self.current_packet.heater_1_status))
        data.insert(16,int(self.current_packet.heater_2_status))
        data.insert(17,int(self.current_packet.heater_3_status))
        data.insert(18,int(self.current_packet.heater_4_status))
        data.insert(19,int(self.current_packet.heater_5_status))
        data.insert(20,int(self.current_packet.heater_6_status))
        data.insert(21,float(self.current_packet.temp_1_status))
        data.insert(22,float(self.current_packet.temp_2_status))
        data.insert(23,float(self.current_packet.temp_3_status))
        data.insert(24,float(self.current_packet.temp_4_status))
        data.insert(25,float(self.current_packet.temp_5_status))
        data.insert(26,float(self.current_packet.temp_6_status))
        data.insert(27,int(self.current_packet.burn_wire_1_status))
        data.insert(28,int(self.current_packet.burn_wire_2_status))
        data.insert(29,int(self.current_packet.current_limiting_status))
        data.insert(30,int(self.current_packet.rpi_1_status))
        data.insert(31,int(self.current_packet.rpi_2_status))
        data.insert(32,int(self.current_packet.rpi_3_status))
        data.insert(33,int(self.current_packet.rpi_4_status))
        data.insert(34,float(self.current_packet.motor_speed))
        return data

    def update_data_table(data, tableLabels, dataFormat) -> None:
        for i in range(CommonData.telemetryParameters):
            # set contents
            colourBG, colourFG = update_data_table_colours(i, data, dataFormat)

            tableLabels[i].configure(text=data[i], bg=colourBG, fg=colourFG)

    def __update_data_table(self) -> None:
        data = self.__formatdata()
        for i in range(CommonData.telemetryParameters):
            # set contents
            colourBG, colourFG = update_data_table_colours(i, data, self.dataFormat)

            self.tableLabels[i].configure(text=data[i], bg=colourBG, fg=colourFG)

            # save telemetry
            if CommonData.outputTelemetry == True:
                self.__save_telemetry(data)

    def __save_telemetry(self, data) -> None:
        for i in range(CommonData.telemetryParameters):
            self.telemOut_df.iloc[i] = data[i]
        self.telemOut_df.to_csv(CommonData.outputTelemetryDir + 'telemOut.csv', header=None, mode="a")

def update_data_table_colours(i, data, dataFormat) -> tuple:
    colourFG = 'black'

    if data[i] < dataFormat.iloc[i, 1] or data[i] > dataFormat.iloc[i, 4]:
        colourBG = 'red'
    elif dataFormat.iloc[i, 1] < data[i] and data[i] < dataFormat.iloc[i, 2]:
        colourBG = 'orange'
    elif dataFormat.iloc[i, 3] < data[i] and data[i] < dataFormat.iloc[i, 4]:
        colourBG = 'orange'
    else:
        colourBG = 'green'
        colourFG = 'white'
    
    return colourBG, colourFG

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
