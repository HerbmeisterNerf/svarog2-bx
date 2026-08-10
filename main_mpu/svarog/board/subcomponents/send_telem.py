import time, threading, socket
from declarations import HEATER_SENSOR_PAIRS
from subcomponents import state as _st

def set_push_interval(sec):
    with _st.telem_push_lock:
        _st.telem_push_interval = max(0.5, float(sec))

def get_push_interval():
    with _st.telem_push_lock:
        return _st.telem_push_interval

def snap_to_text(snap):
    lines = [f"TS={snap.timestamp:.3f}"]
    for k, v in snap.pdu.items():
        lines.append(f"{k}={v}")
    for k, v in snap.thermal.items():
        lines.append(f"{k}={v}")
    for k, v in snap.pwr_good.items():
        lines.append(f"{k}={v}")
    for k, v in snap.faults.items():
        lines.append(f"{k}={v}")
    if _st.heater_ctrl:
        duties = _st.heater_ctrl.get_data()
        for name in duties:
            skey = HEATER_SENSOR_PAIRS.get(name)
            temp = snap.thermal.get(skey, 0.0) if skey else 0.0
            lines.append(f"{name}_TEMP={temp}")
            lines.append(f"{name}_DUTY={duties.get(name, 0)}")
    if _st.enc_reader:
        enc = _st.enc_reader.latest()
        for k, v in enc.items():
            if v is not None:
                lines.append(f"{k}={v}")
        lines.append(f"AUTO_STOP={1 if _st.auto_stop_enabled else 0}")
    if _st.motor_reader:
        mtr = _st.motor_reader.latest()
        for k, v in mtr.items():
            if v is not None:
                lines.append(f"{k}={v}")
    return "\n".join(lines) + "\n"

class TelemThread(threading.Thread):
    def __init__(self, client_sock, reader, addr):
        super().__init__(daemon=True)
        self.sock = client_sock
        self.reader = reader
        self.addr = addr
        self.sock.settimeout(5.0)

    def run(self):
        print(f"[telem] client connected: {self.addr}")
        try:
            while True:
                snap = self.reader.latest()
                if snap is None:
                    time.sleep(1)
                    continue
                payload = snap_to_text(snap)
                try:
                    self.sock.sendall(payload.encode("utf-8"))
                except OSError:
                    break
                time.sleep(get_push_interval())
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            try:
                self.sock.close()
            except OSError:
                pass
            print(f"[telem] client disconnected: {self.addr}")

def telem_server(port, reader):
    print(f"[telem] listening on 0.0.0.0:{port}")
    threads = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.settimeout(1.0)
            srv.bind(("0.0.0.0", port))
            srv.listen()
            while True:
                try:
                    client, addr = srv.accept()
                    t = TelemThread(client, reader, addr)
                    t.start()
                    threads.append(t)
                except socket.timeout:
                    continue
    except KeyboardInterrupt:
        pass
