############ standard libraries ############
import threading
import re
import time

############ custom libraries ############
from CommonData import CommonData

############ class ############
class ProcessCommands(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self, queue):
        super().__init__()
        #Define selfs here
        self.queue = queue
        self.socket = CommonData.commandSocket

############ Methods ############

    def run(self):
        try:
            print("inside process commands")
            cmsg = self.socket.recv(12)
            cmsg = cmsg.decode()
            result = re.search('start:(.*)end:', cmsg)
            cmsg = result.group(1)
            print(cmsg)
            if cmsg == 'TE':
                self.queue.put(("telemetry"))  
            elif cmsg == 'IM':
                self.queue.put(("image")) 
            else:
                self.queue.put((cmsg))
        except Exception as e:
            print(f'An exception occurred in ProcessCommands: {e}')
            self.queue.put("NONE")
            time.sleep(1)

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
