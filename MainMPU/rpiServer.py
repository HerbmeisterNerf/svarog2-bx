# Default libraries
import socket
import sys

#Custom libraries
from CommonData import CommonData
from WaitForConnection import WaitForConnection
from ProcessCommands import ProcessCommands
from SendImage import SendImage
from SendTelem import SendTelem
from DoAction import DoAction
from ProbeTCP import ProbeTCP
from Watch import Watch

# Class definition
class TCPServerApp:
    '''
    This class contains the backend of the TCP server
    '''

    #Initialiser

    def __init__(self):

        #Command socket
        self.commandSocketPort = 12000
        CommonData.commandSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        CommonData.commandSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        CommonData.commandSocket.bind(('', self.commandSocketPort))
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
        print("Awake socket defined.")

    # Methods

    # Live updates
    def startLiveProcesses(self):
        '''
        Starts the live updates for telemetry and camera by means of a thread queue
        '''

        Watch().start()
        print("end watch")

        # process and compute queues
        # self.queue = queue.Queue(maxsize=15)

        # self.queue.put_nowait(self.waitForConnection)

    # def waitForConnection(self):
    #     if not CommonData.commandSocketStatus:
    #         CommonData.commandAdd = ''
    #         WaitForConnection().start()
    #         if CommonData.commandSocketStatus:
    #             self.queue.put(self.probeTCP)
    #             self.queue.put(self.processCommands)
    #             self.queue.put(self.doAction)
    #             self.queue.put(self.sendImage)
    #             self.queue.put(self.sendTelem)
    #         time.sleep(1)
    #         self.queue.put(self.waitForConnection)

    # def probeTCP(self):
    #     if CommonData.commandSocketStatus:
    #         print("probe TCP")
    #         ProbeTCP(self.queue, self.awkSocket, self.awkSocketPort).start()
    #         if not CommonData.commandSocketStatus:
    #             self.queue.put(self.waitForConnection)
    #         time.sleep(1)
    #         self.queue.put(self.probeTCP)

    # def processCommands(self):
    #     if CommonData.commandSocketStatus:
    #         ProcessCommands(self.queue).start()
    #         self.nextaction = self.actionqueue.get()
    #         time.sleep(0.01)
    #         self.queue.put(self.processCommands)

    # def doAction(self):
    #     if CommonData.commandSocketStatus and self.nextaction != "telemetry" and self.nextaction != "image" and self.nextaction != "NONE":
    #         DoAction(self.nextaction).start()
    #         self.queue.put(self.doAction)

    # def sendImage(self):
    #     if CommonData.commandSocketStatus and self.nextaction == "image":
    #         UDP_client_info = (CommonData.commandAdd,self.imageSocketPort)
    #         SendImage(self.imageSocket,self.imgbuffer,UDP_client_info,self.imgbaudrate).start()
    #         self.queue.put(self.sendImage)

    # def sendTelem(self):
    #     if CommonData.commandSocketStatus and self.nextaction == "telemetry":
    #         UDP_client_info = (CommonData.commandAdd,self.telemetrySocketPort)
    #         SendTelem(self.telemetrySocket,UDP_client_info).start()
    #         self.queue.put(self.sendTelem)

# Mainloop

if  __name__ == '__main__':
    a = TCPServerApp()
    TCPServerApp.startLiveProcesses(a)

    while True:
        try:
            TCPServerApp.startLiveProcesses(a)
        except KeyboardInterrupt:
            sys.exit(0)
