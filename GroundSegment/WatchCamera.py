############ standard libraries ############
import threading
import time

############ custom libraries ############
from CommonData import CommonData
from RespondTCP import RespondTCP
from LiveUpdatesTelemetry import LiveUpdatesTelemetry
from LiveUpdatesCamera import LiveUpdatesCamera

############ class ############
class WatchCamera(threading.Thread):
    '''
    This class is responsible for requesting a new image and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self,
                frame1_right, panel, imgtimestamp, rate):
        super().__init__()
        # camera variables
        self.frame1_right = frame1_right
        self.panel = panel
        self.timestamp = imgtimestamp
        self.rate = rate

############ Methods ############

    def run(self):
        while True:
            try:
                if CommonData.runCamera == True:
                    time.sleep(CommonData.ImgFreqVal)
                    print("LiveUpdatesCamera is running")
                    LiveUpdatesCamera(self.frame1_right,
                                          self.panel,
                                          self.timestamp,
                                          self.rate).start()
            except Exception as e:
                print(f'An exception occurred in the Watch: {e}')
