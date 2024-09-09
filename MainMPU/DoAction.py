############ standard libraries ############
import threading
import socket
import tkinter as tk
import time
import os
############ custom libraries ############


############ class ############
class DoAction(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''


############ Initializer ############

    def __init__(self, pin):
        super().__init__()
        #Define selfs here
        self.pin = pin

############ Methods ############

    def run(self):
        try:
            command = 'sudo python toggle' + self.pin + '.py'
            os.system(command)
        except Exception as e:
            print(f'An exception occurred: {e}')

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
