# how this works: send over UART
import threading, time
from declarations import *
from subcomponents import state as _st

try:
    import motor
    HAS_MOTOR = True
except Exception:
    HAS_MOTOR = False

class EncoderViaArduino:

    def __init__(self):
        pass

    def init_usb(self):
        self.u = mraa.Uart("/dev/ttyACM0")
        self.u.setBaudRate(115200)
        self.u.setMode(8, mraa.UART_PARITY_NONE, 1)
        self.u.setFlowcontrol(False, False)

    def read_raw_enc(self):
        try:
            self.u.writeStr("R\n")
        except:
            print("Error reading raw value from encoder")
            return
        time.sleep(0.05)
        if self.u.dataAvailable():
            data = self.u.readStr(128).encode("ascii").strip()
            return int(data)
        else:
            print("Error reading raw value from encoder")


class EncoderReader(threading.Thread):
    """Background poller for the UART encoder.

    Computes angle = raw * 360 / 16384 and a continuous accumulated
    angle that unwraps across the 14-bit count wrap-around.
    """

    COUNT_MAX = 16384
    DEG_PER_COUNT = 360.0 / 16384.0

    def __init__(self, interval=0.2):
        super().__init__(daemon=True)
        self.interval = max(0.05, float(interval))
        self._lock = threading.Lock()
        self._continue = True
        self._raw = None
        self._angle = 0.0
        self._accum = 0.0
        self._last_raw = None
        self.enc = None

    def latest(self):
        with self._lock:
            return {
                "ENC_RAW": self._raw,
                "ENC_ANGLE": self._angle,
                "ENC_ACCUM": self._accum,
            }

    def reset_accum(self):
        with self._lock:
            self._accum = 0.0

    def stop(self):
        self._continue = False

    def run(self):
        try:
            self.enc = EncoderViaArduino()
            self.enc.init_usb()
        except Exception as e:
            print(f"[enc] init failed: {e}")
            return
        while self._continue:
            t0 = time.time()
            try:
                raw = self.enc.read_raw_enc()
                if raw is not None:
                    self._ingest(raw)
            except Exception as e:
                print(f"[enc] read error: {e}")
            time.sleep(max(0, self.interval - (time.time() - t0)))

    def _ingest(self, raw):
        with self._lock:
            if self._last_raw is not None:
                delta = raw - self._last_raw
                half = self.COUNT_MAX // 2
                if delta > half:
                    delta -= self.COUNT_MAX
                elif delta < -half:
                    delta += self.COUNT_MAX
                self._accum += delta * self.DEG_PER_COUNT
            self._last_raw = raw
            self._raw = raw
            self._angle = raw * self.DEG_PER_COUNT


class AutoStop(threading.Thread):
    """Monitors the encoder accumulated angle while the motor retracts.

    When auto-stop is enabled and the motor is retracting (T<0):
      * once |accum| drops to SLOW_AT deg, command speed to SLOW_SPEED (-10)
      * once |accum| drops to STOP_AT deg, command speed to 0
    Re-arms whenever a fresh retract speed is issued.
    """

    SLOW_AT = 5.0
    STOP_AT = 0.1
    SLOW_SPEED = -10.0
    STOP_SPEED = 0.0

    def __init__(self, enc_reader, interval=0.05):
        super().__init__(daemon=True)
        self.enc = enc_reader
        self.interval = max(0.02, float(interval))
        self._lock = threading.Lock()
        self._continue = True
        self._last_speed = None
        self._slow_done = False
        self._stop_done = False

    def stop(self):
        self._continue = False

    def rearm(self):
        with self._lock:
            self._slow_done = False
            self._stop_done = False

    def run(self):
        while self._continue:
            t0 = time.time()
            try:
                self._tick()
            except Exception as e:
                print(f"[autostop] error: {e}")
            time.sleep(max(0, self.interval - (time.time() - t0)))

    def _tick(self):
        if not HAS_MOTOR or not _st.auto_stop_enabled:
            return
        speed = _st.motor_speed
        if speed >= 0:  # not retracting
            self.rearm()
            self._last_speed = speed
            return
        if speed != self._last_speed:  # fresh retract command
            self.rearm()
            self._last_speed = speed
        accum = self.enc.latest().get("ENC_ACCUM")
        if accum is None:
            return
        a = abs(accum)
        with self._lock:
            if not self._stop_done and a <= self.STOP_AT:
                motor.set_speed(self.STOP_SPEED)
                _st.motor_speed = self.STOP_SPEED
                self._last_speed = self.STOP_SPEED
                self._stop_done = True
                self._slow_done = True
                print(f"[autostop] stop at |accum|={a:.3f}")
            elif not self._slow_done and a <= self.SLOW_AT:
                motor.set_speed(self.SLOW_SPEED)
                _st.motor_speed = self.SLOW_SPEED
                self._last_speed = self.SLOW_SPEED
                self._slow_done = True
                print(f"[autostop] slow to {self.SLOW_SPEED} at |accum|={a:.3f}")


if __name__ == "__main__":
    e = EncoderViaArduino()
    e.init_usb()
    while True:
        print(e.read_raw_enc())