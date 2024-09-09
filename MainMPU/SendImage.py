############ standard libraries ############
import threading
import socket
import tkinter as tk
import time
import os

############ custom libraries ############


############ class ############
class SendImage(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self,socket,buffer,UDP_info,rate):
        super().__init__()
        #Define selfs here
        self.socket = socket
        self.buffer = buffer
        self.UDP_info = UDP_info
        self.rate = rate

############ Methods ############

    def run(self):
        try:
#send the image via a UDP connection
            os.system('./takeImage.sh')
            print("Sending image...")
            path = "RealTime.jpg"
            total_size = os.path.getsize(path)

            self.socket.sendto(f"{total_size}".encode('utf-8') + b'\n', self.UDP_info )  # Send the size of the image
            print("Size: ", total_size)
            self.rate, add = self.socket.recvfrom(10)
            print("Rate: ", self.rate.decode())
            with open(path, 'rb') as f:
             while True:
                    time.sleep(float(self.rate))
                    bytes_read = f.read(self.buffer)
                    #print("Bytes: ", bytes_read)
                    if not bytes_read:
                        break  # File transmitting is done
                    self.socket.sendto(bytes_read, self.UDP_info)
            print("Image sent.")

        except Exception as e:
            print(f'An exception occurred: {e}')

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
