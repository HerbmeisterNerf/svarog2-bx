############ standard libraries ############
import threading
import time

############ custom libraries ############
from CommonData import CommonData
from WaitForConnection import WaitForConnection
from ProbeTCP import ProbeTCP

############ class ############
class WatchConnections(threading.Thread):
    '''
    '''

############ Initializer ############

    def __init__(self):
        super().__init__()

############ Methods ############

    def run(self):
        while True:
            try:
                time.sleep(1)
                print("command socket status is " + str(CommonData.commandSocketStatus))

                if not CommonData.commandSocketStatus:
                    CommonData.commandAdd = ''
                    WaitForConnection().start()

                if CommonData.commandSocketStatus:
                    p = ProbeTCP()
                    p.start()
                    p.join()

            except Exception as e:
                print(f'An exception occurred in the Watch: {e}')
