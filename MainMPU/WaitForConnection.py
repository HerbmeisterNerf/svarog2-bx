############ standard libraries ############
import threading

############ custom libraries ############
from CommonData import CommonData

############ class ############
class WaitForConnection(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self):
        super().__init__()

############ Methods ############

    def run(self):
        try:
            CommonData.commandSocket.listen(1)
            print('Command socket open waiting for connection...')
            CommonData.commandSocket, TCPadd = CommonData.commandSocket.accept()
            print('Connection established with ' + TCPadd[0])
            CommonData.commandSocketStatus = True
            CommonData.commandAdd = TCPadd[0]
        except Exception as e:
            print(f'An exception occurred in WaitForConnection: {e}')

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
