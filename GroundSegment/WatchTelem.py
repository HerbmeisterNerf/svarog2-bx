############ standard libraries ############
import threading
import time

############ custom libraries ############
from CommonData import CommonData
from LiveUpdatesTelemetry import LiveUpdatesTelemetry

############ class ############
class WatchTelem(threading.Thread):
    '''
    This class is responsible for requesting a new image and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self, dataFormat, tableLabels):
        super().__init__()
        # telemetry variables
        self.dataFormat = dataFormat
        self.tableLabels = tableLabels

############ Methods ############

    def run(self):
        while True:
            try:
                time.sleep(CommonData.TelemFreqVal)
                if CommonData.runTelemetry:
                    l = LiveUpdatesTelemetry(self.dataFormat,
                                        self.tableLabels)
                    l.start()
                    l.join(3)
            except Exception as e:
                print(f'An exception occurred in the WatchTelem: {e}')
