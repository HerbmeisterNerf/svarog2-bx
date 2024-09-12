############ standard libraries ############
import threading
import queue

############ custom libraries ############
from CommonData import CommonData
from ProcessCommands import ProcessCommands
from DoAction import DoAction
from SendImage import SendImage
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
                # prep sockets and threads
                UDP_client_info_image = (CommonData.commandAdd, CommonData.imageSocketPort)
                i = SendImage(CommonData.imageSocket, CommonData.imgbuffer, UDP_client_info_image)

                UDP_client_info_telem = (CommonData.commandAdd, CommonData.telemetrySocketPort)
                t = SendTelem(CommonData.telemetrySocket, UDP_client_info_telem)

                # checks
                if CommonData.commandSocketStatus:
                    p = ProcessCommands(self.actionqueue)
                    p.start()
                    p.join()
                    self.nextaction = self.actionqueue.get()

                if CommonData.commandSocketStatus and self.nextaction != "telemetry" and self.nextaction != "image" and self.nextaction != "NONE":
                    d = DoAction(self.nextaction)
                    d.start()
                    d.join()
                
                if CommonData.commandSocketStatus and self.nextaction == "image":
                    i.start()

                if CommonData.commandSocketStatus and self.nextaction == "telemetry":
                    t.start()

                if CommonData.commandSocketStatus and self.nextaction == "image":
                    i.join()
                
                if CommonData.commandSocketStatus and self.nextaction == "telemetry":
                    t.join()

            except Exception as e:
                print(f'An exception occurred in the Watch: {e}')
