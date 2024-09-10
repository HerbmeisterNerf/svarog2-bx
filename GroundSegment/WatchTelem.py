############ standard libraries ############
import threading
import time

############ custom libraries ############
from CommonData import CommonData
from RespondTCP import RespondTCP
from LiveUpdatesTelemetry import LiveUpdatesTelemetry
from LiveUpdatesCamera import LiveUpdatesCamera

############ class ############
class WatchTelem(threading.Thread):
    '''
    This class is responsible for requesting a new image and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self, 
                current_packet, dataFormat, tableLabels):
        super().__init__()
        # telemetry variables
        self.current_packet = current_packet
        self.dataFormat = dataFormat
        self.tableLabels = tableLabels

############ Methods ############

    def run(self):
        while True:
            try:
                if CommonData.runTelemetry == True:
                    time.sleep(CommonData.TelemFreqVal)
                    print("LiveUpdatesTelemetry is running")
                    LiveUpdatesTelemetry(self.current_packet,
                                            self.dataFormat,
                                            self.tableLabels).start()
            except Exception as e:
                print(f'An exception occurred in the Watch: {e}')
