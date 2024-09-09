############ standard libraries ############
import threading
import socket
import tkinter as tk
import time

############ custom libraries ############


############ class ############
class ProcessCommands(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''


############ Initializer ############

    def __init__(self, queue,socket,acList):
        super().__init__()
        #Define selfs here
        self.queue = queue
        self.socket = socket
        self.list = acList

############ Methods ############

    def run(self):
        try:
            cmsg = self.socket.recv(9)
            cmsg = cmsg.decode()
            print(cmsg)
            if cmsg == "telemetry":
                self.list[0] = 1
            elif cmsg == "image":
                self.list[1] = 1
            else:
                self.list[2] = 1
            cmsg = "el diablo"
            print(self.list)
            print("Whatsup")
            self.queue.put((self.list))
        except Exception as e:
            print(f'An exception occurred: {e}')

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
