############ standard libraries ############
import threading

############ custom libraries ############
from CommonData import CommonData

############ class ############
class ProcessCommands(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self, queue, socket):
        super().__init__()
        #Define selfs here
        self.queue = queue
        self.socket = socket

############ Methods ############

    def run(self):
        try:
            cmsg = self.socket.recv(9)
            cmsg = cmsg.decode()
            print(cmsg)
            if cmsg == "telemetry":
                CommonData.telemetry = 1
            elif cmsg == "image":
                CommonData.image = 1
            else:
                CommonData.actuate = 1
            cmsg = "el diablo"
            print(CommonData.telemetry, CommonData.image, CommonData.actuate)
            print("Whatsup")
        except Exception as e:
            print(f'An exception occurred: {e}')

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
