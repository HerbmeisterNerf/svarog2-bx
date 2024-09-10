############ standard libraries ############
import threading

############ custom libraries ############
from CommonData import CommonData
from RespondTCP import RespondTCP
from LiveUpdatesTelemetry import LiveUpdatesTelemetry
from LiveUpdatesCamera import LiveUpdatesCamera

############ class ############
class Watch(threading.Thread):
    '''
    This class is responsible for requesting a new image and updating it in the GUI
    '''

############ Initializer ############

    def __init__(self, 
                current_packet, dataFormat, tableLabels,
                frame1_right, panel, imgtimestamp, rate):
        super().__init__()
        # telemetry variables
        self.current_packet = current_packet
        self.dataFormat = dataFormat
        self.tableLabels = tableLabels
        # camera variables
        self.frame1_right = frame1_right
        self.panel = panel
        self.timestamp = imgtimestamp
        self.rate = rate

############ Methods ############

    def run(self):
        while True:
            try:
                print("Watch is running")
                if CommonData.TCPSTATUS == True:
                    print("RespondTCP is running")
                    RespondTCP().start()
                if CommonData.runTelemetry == True:
                    print("LiveUpdatesTelemetry is running")
                    LiveUpdatesTelemetry(self.current_packet,
                                            self.dataFormat,
                                            self.tableLabels).start()
                if CommonData.runCamera == True:
                    print("LiveUpdatesCamera is running")
                    LiveUpdatesCamera(self.frame1_right,
                                          self.panel,
                                          self.timestamp,
                                          self.rate).start()
            except Exception as e:
                print(f'An exception occurred in the Watch: {e}')
