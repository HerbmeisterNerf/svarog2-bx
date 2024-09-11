############ standard libraries ############
import threading
import socket

############ custom libraries ############
from CommonData import CommonData

############ class ############
class ProbeTCP(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''


############ Initializer ############

    def __init__(self):
        super().__init__()
        #Define selfs here
        self.socket = CommonData.awkSocket
        self.port = CommonData.awkSocketPort

############ Methods ############

    def run(self):
        try:
            msg = "ACK"
            self.socket.sendto(msg.encode(), (CommonData.commandAdd, self.port))
            ack = self.socket.recv(3)
            if ack.decode() == "ACK":
                CommonData.commandSocketStatus = True
            else:
                CommonData.commandSocketStatus = False
                self.redoSocket()
        except socket.timeout:
            CommonData.commandSocketStatus = False
            self.redoSocket()
        except Exception as e:
            print(f'An exception occurred in ProbeTCP: {e}')
        
    def redoSocket(self):
        CommonData.commandSocket.close()
        CommonData.commandSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        CommonData.commandSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        CommonData.commandSocket.bind(('', CommonData.commandSocketPort))

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
