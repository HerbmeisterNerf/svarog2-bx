############ standard libraries ############
import threading

############ custom libraries ############
from CommonData import CommonData
from PingServer import PingServer

############ class ############
class WatchPing(threading.Thread):
    '''
    This class is responsible for requesting a new image and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self,label):
        super().__init__()
        self.label = label

############ Methods ############

    def run(self):
        while True:
            try:
                r = PingServer(self.label)
                r.start()
                r.join()
            except Exception as e:
                print(f'An exception occurred in the WatchTCP: {e}')
