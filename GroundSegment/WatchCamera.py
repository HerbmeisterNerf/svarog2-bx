############ standard libraries ############
import threading
import time

############ custom libraries ############
from CommonData import CommonData
from LiveUpdatesCamera import LiveUpdatesCamera

############ class ############
class WatchCamera(threading.Thread):
    '''
    This class is responsible for requesting a new image and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self,
                frame1_right, panel, imgtimestamp,save):
        super().__init__()
        # camera variables
        self.frame1_right = frame1_right
        self.panel = panel
        self.timestamp = imgtimestamp
        self.save = save

############ Methods ############

    def run(self):
        while True:
            try:
                time.sleep(CommonData.ImgFreqVal)
                if CommonData.runCamera == True:
                    l = LiveUpdatesCamera(self.frame1_right,
                                          self.panel,
                                          self.timestamp,self.save)
                    l.start()
                    l.join(60)
            except Exception as e:
                print(f'An exception occurred in the WatchCamera: {e}')
