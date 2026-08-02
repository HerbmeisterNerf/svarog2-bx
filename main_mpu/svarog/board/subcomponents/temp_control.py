import time, threading
from declarations import HEATER_SENSOR_PAIRS, PERIPH_BINDINGS

class RoundRobinArbiter:
    def __init__(self, num : int):
        self.last_rq = 0
        self.num = num

    def arbitrate(self, requests : list[int]):
        if not requests:
            return None
        best = None
        for r in requests:
            if r >= self.last_rq and (best is None or r < best):
                best = r
        if best is None:
            best = min(requests)
        self.last_rq = best
        return best


class DutyCycleManager:
    def __init__(self):
        self._off_timers = {}

    def fire(self, htr, gpio, duty_pct, cycle_len=1.0):
        if gpio is None:
            return
        t = self._off_timers.pop(htr, None)
        if t:
            t.cancel()
        on_duration = (duty_pct / 100.0) * cycle_len
        if on_duration <= 0:
            gpio.write(0)
            return
        gpio.write(1)
        t = threading.Timer(on_duration, lambda g=gpio: g.write(0))
        t.daemon = True
        t.start()
        self._off_timers[htr] = t

    def cancel_all(self):
        for t in self._off_timers.values():
            t.cancel()
        self._off_timers.clear()


class HeaterController(threading.Thread):
    def __init__(self, reader):
        super().__init__(daemon=True)
        self.reader = reader
        self._names = list(HEATER_SENSOR_PAIRS.keys())
        self._duty = {h: 0.0 for h in self._names}
        self._sp   = {h: 30.0 for h in self._names}
        self._arbiter = RoundRobinArbiter(len(self._names))
        self._duty_mgr = DutyCycleManager()
        self._lock = threading.Lock()
        self._continue = True

    def get_data(self):
        with self._lock:
            return dict(self._duty)

    def set_setpoint(self, name, value):
        with self._lock:
            if name in self._sp:
                self._sp[name] = value
                return True
        return False

    def stop(self):
        self._continue = False

    def run(self):
        print("[heater] controller started")
        self._last_cycle = -1
        while self._continue:
            t0 = time.time()
            cycle = int(t0)
            if cycle != self._last_cycle:
                self._last_cycle = cycle
                snap = self.reader.latest()
                thermal = snap.thermal if snap and hasattr(snap, "thermal") else {}
                with self._lock:
                    setpoints = dict(self._sp)
                requests = []
                for i, htr in enumerate(self._names):
                    skey = HEATER_SENSOR_PAIRS[htr]
                    temp = thermal.get(skey, 0.0)
                    sp = setpoints.get(htr, 30.0)
                    if temp < (sp - 0.5):
                        requests.append(i)
                chosen = self._arbiter.arbitrate(requests)
                for i, htr in enumerate(self._names):
                    gpio = PERIPH_BINDINGS.get(htr)
                    duty = 50.0 if i == chosen else 0.0
                    self._duty_mgr.fire(htr, gpio, duty)
                    with self._lock:
                        self._duty[htr] = duty
            elapsed = time.time() - t0
            time.sleep(max(0, 0.1 - elapsed))
        print("[heater] controller stopped")
