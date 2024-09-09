# Default libraries
import queue
import socket
from PIL import Image
import os
import tkinter as tk
import io
import time
from messagePack import MessagePack
import time
import sys
from datetime import datetime

#Custom libraries

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
        self.commandSocketStatus = False
        self.commandAdd = ''
        self.nextaction = ""
        self.acList = [] #Telem, Image, Actuate
        self.action = ""
        self.imgbuffer = 4096

        #Command socket
        self.commandSocketPort = 12000
        self.commandSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.commandSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.commandSocket.bind(('', self.commandSocketPort))
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

    #Methods

    #Live updates
    def startLiveProcesses(self):
        '''
        Starts the live updates for telemetry and camera by means of a thread queue
        '''

        self.queue = queue.Queue()
        self.dataqueue = queue.Queue()
        self.actionsqueue = queue.Queue()
        self.queue.put_nowait(self.waitForConnection())
        self.queue.put_nowait(self.probeTCP())
        self.queue.put_nowait(self.processCommands())
        self.queue.put_nowait(self.sendImage())
        self.queue.put_nowait(self.sendTelem())
        self.queue.put_nowait(self.doAction())

    def waitForConnection(self):
        try:
            if not self.commandSocketStatus:
                print(self.commandSocketStatus)
                self.commandAdd = ''
                # Here start thread of waiting, requires, queue and thats all I believe all
                WaitForConnection(self.dataqueue,self.commandSocket).start()
                self.commandSocket,self.commandSocketStatus,self.commandAdd = self.dataqueue.get()
                print(self.commandSocketStatus)
            time.sleep(1)
            self.queue.put_nowait(self.waitForConnection) # Put
        except queue.Empty:
            time.sleep(1)
            self.queue.put_nowait(self.waitForConnection)

    def processCommands(self):
        try:
            if self.commandSocketStatus:
                ProcessCommands(self.actionsqueue,self.commandSocket).start()
                self.acList= self.actionsqueue.get()
                self.nextaction = self.acList
            self.queue.put_nowait(self.processCommands) # Put
        except queue.Empty:
            self.queue.put_nowait(self.processCommands)

    def sendImage(self):
        try:
            if self.commandSocketStatus and self.nextaction == "image":
                UDP_client_info = (self.commandAdd,self.imageSocketPort)
                SendImage(self.imageSocket,self.imgbuffer,UDP_client_info,self.imgbaudrate).start()
            self.queue.put_nowait(self.sendImage)
        except queue.Empty:
            self.queue.put_nowait(self.sendImage)

    def sendTelem(self):
        try:
            if self.commandSocketStatus and self.nextaction == "telemetry":
                UDP_client_info = (self.commandAdd,self.telemetrySocketPort)
                SendTelem(self.telemetrySocket,UDP_client_info).start()
            self.queue.put_nowait(self.sendTelem)
        except queue.Empty:
            self.queue.put_nowait(self.sendTelem)

    def doAction(self):
        try:
            if self.commandSocketStatus and self.nextaction != "telemetry" and self.nextaction != "image" and self.nextaction != "NONE":
                DoAction(self.nextaction).start()
            self.queue.put_nowait(self.doAction)
        except queue.Empty:
            self.queue.put_nowait(self.doAction)
    
    def probeTCP(self):
        print(self.commandSocketStatus)
        try:
            if self.commandSocketStatus:
                print("Inside fucking thing")
                ProbeTCP(self.dataqueue,self.awkSocket,self.commandAdd,self.awkSocketPort).start()
                self.commandSocketStatus = self.dataqueue.get()
                print(self.commandSocketStatus)
            time.sleep(1)
            self.queue.put_nowait(self.probeTCP)
        except queue.Empty:
            time.sleep(1)
            self.queue.put_nowait(self.probeTCP)

# Mainloop

if  __name__ == '__main__':
    a = TCPServerApp()
    TCPServerApp.startLiveProcesses(a)

    while True:
        try:
            TCPServerApp.startLiveProcesses(a)
        except KeyboardInterrupt:
            sys.exit(0)
