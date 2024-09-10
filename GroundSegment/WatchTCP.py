############ standard libraries ############
import threading

############ custom libraries ############
from CommonData import CommonData
from RespondTCP import RespondTCP

############ class ############
class WatchTCP(threading.Thread):
    '''
    This class is responsible for requesting a new image and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self):
        super().__init__()

############ Methods ############

    def run(self):
        while True:
            try:
                if CommonData.TCPSTATUS == True:
                    print("RespondTCP is running")
                    r = RespondTCP()
                    r.start()
                    r.join()
            except Exception as e:
                print(f'An exception occurred in the Watch: {e}')
