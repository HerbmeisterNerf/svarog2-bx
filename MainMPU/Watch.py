############ standard libraries ############
import threading
import queue

############ custom libraries ############
from CommonData import CommonData
from WaitForConnection import WaitForConnection
from ProbeTCP import ProbeTCP
from ProcessCommands import ProcessCommands
from DoAction import DoAction
from SendImage import SendImage
from SendTelem import SendTelem

############ class ############
class Watch(threading.Thread):
    '''
    This class is responsible for requesting a new image and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self):
        super().__init__()
        self.actionqueue = queue.Queue()
        self.nextaction = ""

############ Methods ############

    def run(self):
        while True:
            try:
                if not CommonData.commandSocketStatus:
                    CommonData.commandAdd = ''
                    WaitForConnection().start()

                if CommonData.commandSocketStatus:
                    ProbeTCP().start()
                    ProcessCommands(self.actionqueue).start()
                    self.nextaction = self.actionqueue.get()

                if CommonData.commandSocketStatus and self.nextaction != "telemetry" and self.nextaction != "image" and self.nextaction != "NONE":
                    DoAction(CommonData.nextaction).start()
                
                if CommonData.commandSocketStatus and self.nextaction == "image":
                    UDP_client_info = (CommonData.commandAdd, CommonData.imageSocketPort)
                    SendImage(CommonData.imageSocket, CommonData.imgbuffer, UDP_client_info).start()

                if CommonData.commandSocketStatus and self.nextaction == "telemetry":
                    UDP_client_info = (CommonData.commandAdd, CommonData.telemetrySocketPort)
                    SendTelem(CommonData.telemetrySocket, UDP_client_info).start()

            except Exception as e:
                print(f'An exception occurred in the Watch: {e}')
