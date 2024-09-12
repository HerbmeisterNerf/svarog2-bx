############ standard libraries ############
import threading
import queue

############ custom libraries ############
from CommonData import CommonData
from ProcessCommands import ProcessCommands
from DoAction import DoAction
from SendTelem import SendTelem

############ class ############
class WatchCommands(threading.Thread):
    '''
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

                if CommonData.commandSocketStatus:
                    p = ProcessCommands(self.actionqueue)
                    p.start()
                    p.join()
                    self.nextaction = self.actionqueue.get()

                if CommonData.commandSocketStatus and self.nextaction != "telemetry" and self.nextaction != "image" and self.nextaction != "NONE" and self.nextaction != "":
                    d = DoAction(self.nextaction)
                    d.start()
                    d.join()

                if CommonData.commandSocketStatus and self.nextaction == "telemetry":
                    UDP_client_info_telem = (CommonData.commandAdd, CommonData.telemetrySocketPort)
                    t = SendTelem(CommonData.telemetrySocket, UDP_client_info_telem)
                    t.start()
                    t.join()

                if CommonData.commandSocketStatus and self.nextaction == "image":
                    CommonData.send_image = True

            except Exception as e:
                print(f'An exception occurred in the Watch Commands: {e}')
