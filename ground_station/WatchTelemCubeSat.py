import queue
import threading
import time

from CommonData import CommonData
from LiveUpdatesTelemetryCubeSat import LiveUpdatesTelemetryCubeSat


class WatchTelemCubeSat(threading.Thread):
    """Reads CubeSat telemetry from the queue and updates the CubeSat GUI table."""

    def __init__(self, dataFormat, tableLabels):
        super().__init__(daemon=True)
        self.dataFormat = dataFormat
        self.tableLabels = tableLabels

    def run(self):
        while True:
            try:
                if CommonData.runTelemetry_cs and CommonData.TCPSTATUS_cs:
                    telem_str = CommonData.cs_telem_queue.get(timeout=10)
                    l = LiveUpdatesTelemetryCubeSat(
                        self.dataFormat, self.tableLabels, telem_str
                    )
                    l.start()
                    l.join(3)
                else:
                    time.sleep(0.5)
            except queue.Empty:
                pass
            except Exception as e:
                print(f"WatchTelemCubeSat error: {e}")
