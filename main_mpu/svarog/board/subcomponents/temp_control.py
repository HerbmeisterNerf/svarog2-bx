import time, threading
from BOARD_SELECT import is_ebox
from declarations import HEATER_SENSOR_PAIRS, PERIPH_BINDINGS, OPEN_LOOP_WAIT

class RoundRobinArbiter:
    def __init__(self, num : int):
        self.last_rq = 0
        self.num = num

    def arbitrate(self, requests : list[int]):
        if not requests:
            return None
        best = None
        for r in requests:
            if r > self.last_rq and (best is None or r < best):
                best = r
        if best is None:
            best = min(requests)
        self.last_rq = best
        return best


class DutyCycleManager:
    def __init__(self):
        self._off_timers = {}

    def fire(self, htr, gpio, duty_pct, cycle_len=1.0):
        # print(f"Firing heater {htr} at duty cycle {duty_pct}")
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
        self._sp   = {h: -20.0 for h in self._names}
        self._arbiter = RoundRobinArbiter(len(self._names))
        self._duty_mgr = DutyCycleManager()
        self._lock = threading.Lock()
        self._continue = True
        # cubesat has no ADC so it runs open loop; ebox runs closed loop
        self.open_loop = {name: not is_ebox for name in self._names}
        self.ol_last_actuated = {name : 0 for name in self._names}

    def get_data(self):
        with self._lock:
            return dict(self._duty)

    def get_setpoints(self):
        with self._lock:
            return dict(self._sp)

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
                # print(f"Current thermals: {thermal}")
                with self._lock:
                    setpoints = dict(self._sp)
                requests = []
                for i, htr in enumerate(self._names):
                    if self.open_loop[htr]: # automatically add to arbiter if open loop
                        requests.append(i)
                        continue
                    skey = HEATER_SENSOR_PAIRS[htr]
                    temp = thermal.get(skey, 0.0)
                    sp = setpoints.get(htr, -20.0)
                    if temp < (sp - 0.5):
                        requests.append(i)
                chosen = self._arbiter.arbitrate(requests)
                for i, htr in enumerate(self._names):
                    gpio = PERIPH_BINDINGS.get(htr)
                    # duty = 50.0 if i == chosen else 0.0
                    if i != chosen:
                        duty = 0
                    elif self.open_loop[htr] and time.time() - self.ol_last_actuated[htr] > OPEN_LOOP_WAIT:
                        # open loop, chosen, and enough time has passed
                        duty = 10
                        self.ol_last_actuated[htr] = time.time()
                    elif not self.open_loop[htr]: # closed loop control scheme, and chosen
                        duty = 10
                    else:
                        duty = 0
                    self._duty_mgr.fire(htr, gpio, duty)
                    with self._lock:
                        self._duty[htr] = duty
            elapsed = time.time() - t0
            time.sleep(max(0, 0.1 - elapsed))
        print("[heater] controller stopped")
