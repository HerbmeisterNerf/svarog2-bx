############ standard libraries ############
import threading
import os
import time
import subprocess
############ custom libraries ############
from CommonData import CommonData
from PortCommunication import PortCommunication

############ class ############
class PingServer(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self,label):
        super().__init__()

        self.label= label
        #Define selfs here

############ Methods ############

    def run(self):
        try:
            
            #prog = subprocess.call(["ping", CommonData.server_name, "-c","2"])
            prog = subprocess.run(['ping', '-n', '1', CommonData.server_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            outcome = prog.returncode
            result = prog.stdout.decode('utf-8')
            if outcome == 0:
                if "Sent = 1, Received = 1," in result:
                    self.label.config(bg="green")
                else:
                    self.label.config(bg="red")
                    print("red")
            else:
                self.label.config(bg="red")
            time.sleep(1)
        except Exception as e:
            print(f'An exception occurred: {e}')

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
