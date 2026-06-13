import queue
import threading
import time

from CommonData import CommonData
from LiveUpdatesTelemetry import LiveUpdatesTelemetry


class WatchTelem(threading.Thread):
    '''Blocks on the EBOX telemetry queue and updates the telemetry table.'''

    def __init__(self, dataFormat, tableLabels):
        super().__init__(daemon=True)
        self.dataFormat = dataFormat
        self.tableLabels = tableLabels

    def run(self):
        while True:
            try:
                if CommonData.runTelemetry and CommonData.TCPSTATUS:
                    telem_str = CommonData.ebox_telem_queue.get(timeout=10)
                    l = LiveUpdatesTelemetry(self.dataFormat, self.tableLabels, telem_str)
                    l.start()
                    l.join(3)
                else:
                    time.sleep(0.5)
            except queue.Empty:
                pass
            except Exception as e:
                print(f'WatchTelem error: {e}')
