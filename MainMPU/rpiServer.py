# Default libraries
import queue
import socket
import time
import sys

#Custom libraries
from CommonData import CommonData
from WaitForConnection import WaitForConnection
from ProcessCommands import ProcessCommands
from SendImage import SendImage
from SendTelem import SendTelem
from DoAction import DoAction
from ProbeTCP import ProbeTCP

# Class definition
class TCPServerApp:
    '''
    This class contains the backend of the TCP server
    '''

    #Initialiser

    def __init__(self):
        #STATUS VARIABLES
        self.nextaction = ""
        self.action = ""
        self.imgbuffer = 4096

        #Command socket
        self.commandSocketPort = 12000
        CommonData.commandSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        CommonData.commandSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        CommonData.commandSocket.bind(('', self.commandSocketPort))
        print("Command socket defined.")

        #Telemetry socket
        self.telemetrySocketPort = 11000
        self.telemetrySocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.telemetrySocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.telemetrySocket.bind(('', self.telemetrySocketPort))
        print("Telemetry socket defined.")

        #Image socket
        self.imageSocketPort = 15000
        self.imageSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.imageSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.imageSocket.bind(('', self.imageSocketPort))
        print("Image socket defined.")

        #Awk socket
        self.awkSocketPort = 50007
        self.awkSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.awkSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.awkSocket.bind(('', self.awkSocketPort))
        print("Awake socket defined.")

    # Methods

    # Live updates
    def startLiveProcesses(self):
        '''
        Starts the live updates for telemetry and camera by means of a thread queue
        '''

        # self.waitqueue = queue.Queue()
        # self.probequeue = queue.Queue()
        # self.actionsqueue = queue.Queue()
        # self.dataqueue = queue.Queue()

        # self.waitqueue.put_nowait(self.waitForConnection())

        # self.probequeue.put_nowait(self.probeTCP())

        # self.actionsqueue.put_nowait(self.processCommands())
        # self.actionsqueue.put_nowait(self.doAction())

        # self.dataqueue.put_nowait(self.sendImage())
        # self.dataqueue.put_nowait(self.sendTelem())
        
        self.queue = queue.Queue()

        self.queue.put_nowait(self.waitForConnection)
        self.queue.put_nowait(self.probeTCP)
        self.queue.put_nowait(self.processCommands)
        self.queue.put_nowait(self.doAction)
        self.queue.put_nowait(self.sendImage)
        self.queue.put_nowait(self.sendTelem)

        self.queue_handler()

    def queue_handler(self):
        '''
        Handles the queue of threads
        '''
        try:
            self.queue.get_nowait()()
        except queue.Empty:
            pass
        time.sleep(0.05)
        self.queue_handler()

    def waitForConnection(self):
        if not CommonData.commandSocketStatus:
            CommonData.commandAdd = ''
            WaitForConnection(self.queue).start()
        time.sleep(1)
        self.queue.put_nowait(self.waitForConnection)

    def probeTCP(self):
        if CommonData.commandSocketStatus:
            ProbeTCP(self.queue, self.awkSocket, self.awkSocketPort).start()
            print("socket status ", CommonData.commandSocketStatus)
            time.sleep(2)
        self.queue.put_nowait(self.probeTCP)

    def processCommands(self):
        if CommonData.commandSocketStatus:
            ProcessCommands(self.queue,CommonData.commandSocket).start()
            self.nextaction = [CommonData.telemetry, CommonData.image, CommonData.actuate]
        self.queue.put_nowait(self.processCommands)

    def doAction(self):
        if CommonData.commandSocketStatus and self.nextaction != "telemetry" and self.nextaction != "image" and self.nextaction != "NONE":
            DoAction(self.nextaction).start()
        self.queue.put_nowait(self.doAction)

    def sendImage(self):
        if CommonData.commandSocketStatus and self.nextaction == "image":
            UDP_client_info = (CommonData.commandAdd,self.imageSocketPort)
            SendImage(self.imageSocket,self.imgbuffer,UDP_client_info,self.imgbaudrate).start()
        self.queue.put_nowait(self.sendImage)

    def sendTelem(self):
        if CommonData.commandSocketStatus and self.nextaction == "telemetry":
            UDP_client_info = (CommonData.commandAdd,self.telemetrySocketPort)
            SendTelem(self.telemetrySocket,UDP_client_info).start()
        self.queue.put_nowait(self.sendTelem)

# Mainloop

if  __name__ == '__main__':
    a = TCPServerApp()
    TCPServerApp.startLiveProcesses(a)

    while True:
        try:
            TCPServerApp.startLiveProcesses(a)
        except KeyboardInterrupt:
            sys.exit(0)
