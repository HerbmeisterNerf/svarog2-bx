############ standard libraries ############
import threading
import socket
import tkinter as tk
import os
import time

############ custom libraries ############
from CommonData import CommonData

############ class ############
class LiveUpdatesTelemetry(threading.Thread):

    def __init__(self, queue, 
                current_packet,
                dataFormat,
                frame1_left,
                running = False):
        super().__init__()
        self.queue = queue
        self.running = running
        self.current_packet = current_packet
        self.dataFormat = dataFormat
        self.frame1_left = frame1_left

    def run(self):
        while self.running:
            time.sleep(1)
            try:
                # if self.TCPSTATUS == 1:
                # if os.environ["TCPSTATUS"] == "1":
                if CommonData.TCPSTATUS == True:
                    self.__request_telemetry()   
                    LiveUpdatesTelemetry.update_data_table(self.__formatdata(), self.frame1_left, self.dataFormat)
                else:
                    print("Not connected to server")
            except Exception as e:
                print(f'An exception occurred: {e}')

    def __request_telemetry(self):
        self.__open_UDP_telem() 
        message = "telemetry"
        # self.client_TCP_socket.send(message.encode())
        CommonData.client_TCP_socket.send(message.encode())
        bytes_read = self.client_UDP_socket_telem.recvfrom(1024)
        telem =  bytes_read[0].decode("utf-8")
        print(telem)
        self.__process_telemetry(telem)
        self.__close_UDP_telem()
    
    def __open_UDP_telem(self):
        # UDP
        client_UDP_port = 11000
        UDP_info = ("", client_UDP_port)
        self.client_UDP_socket_telem = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_UDP_socket_telem.bind(UDP_info)

    def __close_UDP_telem(self):
        self.client_UDP_socket_telem.close()

    def __process_telemetry(self,string):
        variables = string.split(",")
        for each in variables:
            print(each)
            var,val = each.split("=")
            setattr(self.current_packet,var,val)

    def __formatdata(self):
        data = []
        data.insert(0,self.current_packet.voltage_28V)
        data.insert(1,self.current_packet.voltage_5V)
        data.insert(2,self.current_packet.voltage_12V)
        data.insert(3,self.current_packet.voltage_24V)
        data.insert(4,self.current_packet.current_5V)
        data.insert(5,self.current_packet.current_12V)
        data.insert(6,self.current_packet.current_24V)
        data.insert(7,self.current_packet.ebox_temp)
        data.insert(8,self.current_packet.pressure)
        data.insert(9,self.current_packet.imu_mag_x)
        data.insert(10,self.current_packet.imu_mag_y)
        data.insert(11,self.current_packet.imu_mag_z)
        data.insert(12,self.current_packet.imu_acc_x)
        data.insert(13,self.current_packet.imu_mag_y)
        data.insert(14,self.current_packet.imu_mag_z)
        data.insert(15,self.current_packet.heater_1_status)
        data.insert(16,self.current_packet.heater_2_status)
        data.insert(17,self.current_packet.heater_3_status)
        data.insert(18,self.current_packet.heater_4_status)
        data.insert(19,self.current_packet.heater_5_status)
        data.insert(20,self.current_packet.heater_6_status)
        data.insert(21,self.current_packet.temp_1_status)
        data.insert(22,self.current_packet.temp_2_status)
        data.insert(23,self.current_packet.temp_3_status)
        data.insert(24,self.current_packet.temp_4_status)
        data.insert(25,self.current_packet.temp_5_status)
        data.insert(26,self.current_packet.temp_6_status)
        data.insert(27,self.current_packet.burn_wire_1_status)
        data.insert(28,self.current_packet.burn_wire_2_status)
        data.insert(29,self.current_packet.current_limiting_status)
        data.insert(30,self.current_packet.rpi_1_status)
        data.insert(31,self.current_packet.rpi_2_status)
        data.insert(32,self.current_packet.rpi_3_status)
        data.insert(33,self.current_packet.rpi_4_status)
        data.insert(34,self.current_packet.motor_speed)
        return data

    def update_data_table(data, frame1_left, dataFormat):
        for i in range(len(data)):
            # clear contents
            tk.Label(frame1_left, text='000', bg='lightgray', fg='lightgray').grid(row=(1+i%15), column=(1+2*(i//15)), padx=30, pady=3)

            # set contents
            colourFG = 'black'
            if isinstance(data[i], str):
                if dataFormat[0][i] == 'OFF':
                    colourBG = 'orange'
                else:
                    colourBG = 'green'
                    colourFG = 'white'
            else:
                if data[i] < dataFormat[1][i] or data[i] > dataFormat[4][i]:
                    colourBG = 'red'
                elif dataFormat[1][i] < data[i] and data[i] < dataFormat[2][i]:
                    colourBG = 'orange'
                elif dataFormat[3][i] < data[i] and data[i] < dataFormat[4][i]:
                    colourBG = 'orange'
                else:
                    colourBG = 'green'
                    colourFG = 'white'
            tk.Label(frame1_left, text=data[i], bg=colourBG, fg=colourFG).grid(row=(1+i%15), column=(1+2*(i//15)), padx=30, pady=3)

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
