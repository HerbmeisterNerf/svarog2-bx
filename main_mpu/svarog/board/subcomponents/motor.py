#!/usr/bin/env python3
import mraa, time, sys

UART_ID = 7

def _open():
    u = mraa.Uart(UART_ID)
    u.setBaudRate(115200)
    u.setMode(8, mraa.UART_PARITY_NONE, 1)
    u.setFlowcontrol(False, False)
    return u

def cmd(cmd_str, timeout=0.5):
    u = _open()
    try:
        u.write((cmd_str + "\n").encode("ascii"))
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

def ping():          return cmd("PING")
def set_mode(val):   return cmd(f"TC{val}")
def set_speed(val):  return cmd(f"T{val}")
def set_current(val): return cmd(f"C{val}")
def raw(text):       return cmd(text)

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
