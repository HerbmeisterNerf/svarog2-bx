############ standard libraries ############
import threading
import socket
import tkinter as tk
import time
import os
from messagePack import MessagePack
############ custom libraries ############


############ class ############
class SendTelem(threading.Thread):
    '''
    This class is responsible for requesting a new telemtry package and updating it in the GUI
    '''


############ Initializer ############

    def __init__(self, socket, UDP_info):
        super().__init__()
        #Define selfs here
        self.socket = socket
        self.packet = MessagePack()
        self.UDP_info = UDP_info

############ Methods ############

    def run(self):
        try:
            self.packet = self.updateTelem(self.packet)
            lol = self.packet.generateString()
            #print(lol)
            self.socket.sendto(lol.encode('utf-8'), self.UDP_info)
            print("Telemetry sent")
        except Exception as e:
            print(f'An exception occurred in SendTelem: {e}')
    
    def updateTelem(self,packet):
        packet = self.updatePDU(packet)
        packet = self.updateHeaters(packet)
        packet = self.updateTemp(packet)
        packet = self.updateBWMotor(packet)
        packet = self.updateSecondaries(packet)
        return packet

    def updateSecondaries(self,pack):
        os.system('sudo python ReadSecondaries.py')
        statusfile = open("Secondarystatus.txt","r")
        for x in statusfile:
            #print(x)
            var,val = x.split("=")
            setattr(pack,var,val)
        return pack


    def updateBWMotor(self,pack):
        os.system('sudo python ReadBwMotor.py')
        statusfile = open("BWMotorstatus.txt","r")
        for x in statusfile:
            #print(x)
            var,val = x.split("=")
            setattr(pack,var,val)
        return pack

    def updateTemp(self,pack):
        os.system('sudo python ReadTempADC.py')
        statusfile = open("Tempstatus.txt","r")
        for x in statusfile:
            #print(x)
            var,val = x.split("=")
            setattr(pack,var,val)
        return pack

    def updateHeaters(self,pack):
        os.system('sudo python ReadHeaters.py')
        statusfile = open("Heaterstatus.txt","r")
        for x in statusfile:
            #print(x)
            var,val = x.split("=")
            setattr(pack,var,val)
        return pack
    
    def updatePDU(self,pack):
        os.system('sudo python ReadPDUADC.py')
        statusfile = open("PDUstatus.txt","r")
        for x in statusfile:
            #print(x)
            var,val = x.split("=")
            setattr(pack,var,val)
        return pack

############ Main ############

if __name__ == '__main__':
    print('Cannot run this file directly')
