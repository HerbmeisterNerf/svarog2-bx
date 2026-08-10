#!/usr/bin/env python3
import mraa, time, sys, threading

UART_ID = 7
GEAR_RATIO = 688.0

def _open():
    u = mraa.Uart("/dev/ttyS7")
    u.setBaudRate(115200)
    u.setMode(8, mraa.UART_PARITY_NONE, 1)
    u.setFlowcontrol(False, False)
    return u

def cmd(cmd_str, timeout=0.5):
    u = _open()
    try:
        u.writeStr((cmd_str + "\n"))
        u.flush()
        time.sleep(0.05)
        data = b""
        start = time.time()
        while time.time() - start < timeout:
            if u.dataAvailable():
                data += u.readStr(128).encode("ascii")
                if data[-1:] == b"\n":
                    break
            time.sleep(0.01)
        return data.decode("ascii").strip() if data else None
    finally:
        u = None

# new command:
# u.writeStr("R\n")
# returns [num_full_rot],abs_angle
# angle = abs_angle
# accum = 360*num_full_rot + abs_angle
# both are motor-shaft degrees; divide by GEAR_RATIO for output angle.

def ping():          return cmd("PING")
def set_mode(val):   return cmd(f"TC{val}")
def set_speed(val):  return cmd(f"T{val}")
def set_current(val): return cmd(f"C{val}")
def raw(text):       return cmd(text)

def setup():
    u = _open()
    try:
        u.writeStr("I\n")
        time.sleep(0.01)
    finally:
        u = None


class MotorReader(threading.Thread):
    """Background poller for the motor-controller angle ("R" command).

    The controller answers `[num_full_rot],abs_angle`; we expose the
    absolute angle and the accumulated angle = 360*num_full_rot + abs_angle.
    """

    def __init__(self, interval=0.2):
        super().__init__(daemon=True)
        self.interval = max(0.05, float(interval))
        self._lock = threading.Lock()
        self._continue = True
        self._rot = None
        self._angle = None
        self._accum = None

    def latest(self):
        with self._lock:
            return {
                "MOTOR_ANGLE": self._angle,
                "MOTOR_ACCUM": self._accum,
                "MOTOR_ROT": self._rot,
            }

    def stop(self):
        self._continue = False

    def run(self):
        while self._continue:
            t0 = time.time()
            try:
                resp = cmd("R")
                if resp:
                    self._parse(resp)
            except Exception as e:
                print(f"[motor] read error: {e}")
            time.sleep(max(0, self.interval - (time.time() - t0)))

    def _parse(self, resp):
        s = resp.strip().replace("[", "").replace("]", "")
        if "," not in s:
            return
        rot_s, angle_s = s.split(",", 1)
        try:
            rot = int(rot_s.strip())
            angle = float(angle_s.strip())
        except ValueError:
            return
        with self._lock:
            self._rot = rot
            self._angle = angle / GEAR_RATIO
            self._accum = (360.0 * rot + angle) / GEAR_RATIO


if __name__ == "__main__":
    print(f"Motor UART: /dev/ttyS{UART_ID}")
    print("TC<0-3> mode | T<val> speed | C<val> current | q quit")
    try:
        while True:
            inp = input("> ").strip()
            if inp == "q":
                break
            print(cmd(inp))
    except KeyboardInterrupt:
        pass
