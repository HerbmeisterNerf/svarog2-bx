# Default libraries
import socket
import sys

#Custom libraries
from CommonData import CommonData
from WatchConnections import WatchConnections
from WatchCommands import WatchCommands

# Class definition
class TCPServerApp:
    '''
    This class contains the backend of the TCP server
    '''

    #Initialiser

    def __init__(self):

        #Command socket
        CommonData.commandSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        CommonData.commandSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        CommonData.commandSocket.bind(('', CommonData.commandSocketPort))
        print("Command socket defined.")

        #Telemetry socket
        CommonData.telemetrySocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        CommonData.telemetrySocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        CommonData.telemetrySocket.bind(('', CommonData.telemetrySocketPort))
        print("Telemetry socket defined.")

        #Image socket
        CommonData.imageSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        CommonData.imageSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        CommonData.imageSocket.bind(('', CommonData.imageSocketPort))
        print("Image socket defined.")

        #Awk socket
        CommonData.awkSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        CommonData.awkSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        CommonData.awkSocket.bind(('', CommonData.awkSocketPort))
        CommonData.awkSocket.settimeout(5)
        print("Awake socket defined.")

    # Methods

    # Live updates
    def startLiveProcesses(self):
        '''
        Starts the live updates for telemetry and camera by means of a thread queue
        '''

        try:
            WatchConnections().start()
            WatchCommands().start()

        except Exception as e:
            print(f'An exception occurred in the live updates: {e}')

# Mainloop

if  __name__ == '__main__':
    a = TCPServerApp()

    try:
        a.startLiveProcesses()
    except KeyboardInterrupt:
        sys.exit(0)
