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
from Sleeper import Sleeper

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
        
        # action queue
        self.actionqueue = queue.Queue()

        # process and compute queues
        self.queue = queue.Queue(maxsize=15)

        self.queue.put_nowait(self.waitForConnection)

        # sleeper queue
        self.sleeperqueue = queue.Queue()

        self.queue_handler()

    def queue_handler(self):
        '''
        Handles the queue of threads
        '''
        while True:
            try:
                self.queue.get_nowait()()
            except queue.Empty:
                pass
            else:
                pass
            if not CommonData.commandSocketStatus:
                time.sleep(0.5)

    def waitForConnection(self):
        if not CommonData.commandSocketStatus:
            CommonData.commandAdd = ''
            WaitForConnection().start()
            if CommonData.commandSocketStatus:
                self.queue.put_nowait(self.probeTCP)
                self.queue.put(self.processCommands)
                self.queue.put(self.doAction)
                self.queue.put(self.sendImage)
                self.queue.put(self.sendTelem)
            time.sleep(1)
            self.queue.put_nowait(self.waitForConnection)

    def probeTCP(self):
        if CommonData.commandSocketStatus:
            print("probe TCP")
            ProbeTCP(self.queue, self.awkSocket, self.awkSocketPort).start()
            if not CommonData.commandSocketStatus:
                self.queue.put_nowait(self.waitForConnection)
            time.sleep(1)
            self.queue.put_nowait(self.probeTCP)

    def processCommands(self):
        if CommonData.commandSocketStatus:
            ProcessCommands(self.queue, CommonData.commandSocket).start()
            self.nextaction = self.actionqueue.get()
            time.sleep(0.01)
            self.queue.put(self.processCommands)

    def doAction(self):
        if CommonData.commandSocketStatus and self.nextaction != "telemetry" and self.nextaction != "image" and self.nextaction != "NONE":
            DoAction(self.nextaction).start()
            self.queue.put(self.doAction)

    def sendImage(self):
        if CommonData.commandSocketStatus and self.nextaction == "image":
            UDP_client_info = (CommonData.commandAdd,self.imageSocketPort)
            SendImage(self.imageSocket,self.imgbuffer,UDP_client_info,self.imgbaudrate).start()
            self.queue.put(self.sendImage)

    def sendTelem(self):
        if CommonData.commandSocketStatus and self.nextaction == "telemetry":
            UDP_client_info = (CommonData.commandAdd,self.telemetrySocketPort)
            SendTelem(self.telemetrySocket,UDP_client_info).start()
            self.queue.put(self.sendTelem)

    def sleeper(self, timer):
        Sleeper(timer)

# Mainloop

if  __name__ == '__main__':
    a = TCPServerApp()
    TCPServerApp.startLiveProcesses(a)

    while True:
        try:
            TCPServerApp.startLiveProcesses(a)
        except KeyboardInterrupt:
            sys.exit(0)
