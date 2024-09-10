############ standard libraries ############
import threading

############ custom libraries ############
from CommonData import CommonData
from PortCommunication import PortCommunication

############ class ############
class RespondTCP(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self):
        super().__init__()
        #Define selfs here

############ Methods ############

    def run(self):
        try:
            awksocket = PortCommunication.open_UDP(CommonData.probe_port)
            print("Waiting for message")
            msg = awksocket.recvfrom(3)
            print("Received it mate")
            cmd = "ACK"
            if msg[0].decode() == cmd:
               awksocket.sendto(cmd.encode(), (CommonData.server_name, CommonData.probe_port))
               print("Sent it mate")
            PortCommunication.close_UDP(awksocket)
        except Exception as e:
            print(f'An exception occurred: {e}')

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
