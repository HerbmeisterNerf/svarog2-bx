import time, threading
from BOARD_SELECT import is_ebox
import check_status

# TODO: fix this stuff

if is_ebox:
    from adc import PDU_ADC, THERMAL_ADC

class SensorSnapshot:
    __slots__ = ("timestamp", "pdu", "thermal", "pwr_good", "faults")
    def __init__(self, timestamp, pdu, thermal, pwr_good, faults):
        self.timestamp = timestamp
        self.pdu = pdu
        self.thermal = thermal
        self.pwr_good = pwr_good
        self.faults = faults

class SensorReader(threading.Thread):
    def __init__(self, interval=2.0, has_adc=True):
        super().__init__(daemon=True)
        self.interval = interval
        self._latest = None
        self._lock = threading.Lock()
        self._continue = True
        self.has_adc = has_adc
        if has_adc:
            self.pdu_adc = PDU_ADC()
            self.thermal_adc = THERMAL_ADC()

    def latest(self):
        with self._lock:
            return self._latest

    def stop(self):
        self._continue = False

    def set_interval(self, sec):
        self.interval = max(0.1, float(sec))

    def run(self):
        while self._continue:
            t0 = time.time()
            interval = self.interval
            if self.has_adc:
                try:
                    pdu = self.pdu_adc.poll()
                except Exception:
                    pdu = {}
                try:
                    thermal = self.thermal_adc.poll_all()
                except Exception:
                    thermal = {}
            else:
                pdu = {}
                thermal = {}
            pg, flt = check_status.read_all()
            snap = SensorSnapshot(
                timestamp=time.time(),
                pdu=pdu,
                thermal=thermal,
                pwr_good=pg,
                faults=flt,
            )
            with self._lock:
                self._latest = snap
            elapsed = time.time() - t0
            time.sleep(max(0, interval - elapsed))
