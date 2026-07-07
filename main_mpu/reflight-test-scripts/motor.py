from declarations import *
import sys

def open_uart(uart_id=7, baud=115200):
    u = mraa.Uart(uart_id)
    u.setBaudRate(baud)
    u.setMode(8, mraa.UART_PARITY_NONE, 1)
    u.setFlowcontrol(False, False)
    return u

def send(u, msg):
    if isinstance(msg, str):
        msg = msg.encode('ascii')
    u.write(msg)
    u.flush()

def recv(u, timeout=0.5):
    start = time.time()
    data = b""
    while time.time() - start < timeout:
        if u.dataAvailable():
            data += u.readStr(128).encode('ascii')
        if data and data[-1] == ord('\n'):
            break
        time.sleep(0.01)
    return data.decode('ascii').strip() if data else None

if __name__ == "__main__":
    uart_id = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    u = open_uart(uart_id)
    resp = recv(u, timeout=2)
    if resp:
        print(resp)
    print("Commands: T<val> (target current), G (get state), I (init FOC), q (quit)")
    try:
        while True:
            inp = input("> ").strip()
            if inp == "q":
                break
            send(u, inp + "\n")
            resp = recv(u, timeout=1)
            if resp:
                print(resp)
    except KeyboardInterrupt:
        pass
    finally:
        u = None
