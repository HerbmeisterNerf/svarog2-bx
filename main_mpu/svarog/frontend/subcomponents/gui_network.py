import socket, threading, queue, time
from tkinter import messagebox

TELEM_RECV_TIMEOUT = 30.0   # seconds without telem data before declaring the link dead
RECONNECT_DELAY = 5.0       # seconds between automatic reconnect attempts


class BoardConnector:
    """Functional TCP layer for one board: sockets, command send, telem receive.
    No GUI widget knowledge; reports via callbacks and queues."""

    def __init__(self, name, default_ip, default_cmd, default_telem):
        self.name = name
        self.default_ip = default_ip
        self.default_cmd = default_cmd
        self.default_telem = default_telem

        self.cmd_sock = None
        self.telem_sock = None
        self.connected = False
        self.resp_queue = queue.Queue()
        self.telem_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.log_queue = queue.Queue()
        self.disconnect_queue = queue.Queue()
        self._cmd_lock = threading.Lock()
        self._io_lock = threading.Lock()

        self.on_telem = None              # callable(snapshot_text)
        self.on_status = None             # callable(connected: bool)
        self.on_async_disconnect = None   # callable()  (telem socket dropped)
        self.on_log = None                # callable(text, tag)
        self.on_resp = None               # callable(text)  (every cmd response)

        # Auto-reconnect state.
        self.auto_reconnect = False
        self._connect_args = None
        self._reconnect_stop = threading.Event()
        self._reconnect_thread = None

    def connect(self, ip, cmd_port, telem_port, silent=False):
        with self._io_lock:
            try:
                self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.cmd_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                self.cmd_sock.settimeout(5)
                self.cmd_sock.connect((ip, cmd_port))
            except Exception as e:
                self.cmd_sock = None
                if not silent:
                    messagebox.showerror(f"{self.name} CMD", str(e))
                self._log(f"[connect failed: {e}]", "err")
                return False
            try:
                self.telem_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.telem_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                self.telem_sock.settimeout(5)
                self.telem_sock.connect((ip, telem_port))
            except Exception:
                self.telem_sock = None
            self._connect_args = (ip, cmd_port, telem_port)
            self.connected = True
            if self.telem_sock:
                self.telem_sock.settimeout(TELEM_RECV_TIMEOUT)
                threading.Thread(target=self._recv_telem_loop, daemon=True).start()
            self._log("[connected]", "ok")
            self.status_queue.put(True)
            return True

    def disconnect(self):
        with self._io_lock:
            self.connected = False
            for s in (self.cmd_sock, self.telem_sock):
                if s:
                    try: s.close()
                    except Exception: pass
            self.cmd_sock = None
            self.telem_sock = None
        self._log("[disconnected]", "err")
        self.status_queue.put(False)
        if self.auto_reconnect:
            self._start_reconnect_loop()

    def toggle_connect(self, ip, cmd_port, telem_port):
        if self.connected:
            self.disconnect()
        else:
            self.connect(ip, cmd_port, telem_port)

    def send(self, cmd):
        if not self.connected or not self.cmd_sock:
            self._log("[not connected]", "err")
            return
        self._log(f"> {cmd}", "cmd")
        threading.Thread(target=self._send_and_recv, args=(cmd,), daemon=True).start()

    def _send_and_recv(self, cmd):
        with self._cmd_lock:
            try:
                self.cmd_sock.sendall((cmd + "\n").encode("utf-8"))
                buf = b""
                while True:
                    chunk = self.cmd_sock.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    if b"\n" in buf:
                        break
                self.resp_queue.put(buf.decode("utf-8").strip())
            except Exception as e:
                self.resp_queue.put(f"ERR: {e}")

    def _recv_telem_loop(self):
        try:
            buf = b""
            while self.connected:
                chunk = self.telem_sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    block, buf = buf.split(b"\n", 1)
                    self.telem_queue.put(block.decode("utf-8").strip())
        except Exception:
            pass
        if self.connected:
            self.disconnect_queue.put(True)

    # ── auto-reconnect ──────────────────────────────────────────────

    def set_auto_reconnect(self, enabled):
        self.auto_reconnect = bool(enabled)
        if enabled:
            self._start_reconnect_loop()
        else:
            self._reconnect_stop.set()

    def _start_reconnect_loop(self):
        if self.connected or self._connect_args is None:
            return
        if self._reconnect_thread is not None and self._reconnect_thread.is_alive():
            return
        self._reconnect_stop.clear()
        self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()

    def _reconnect_loop(self):
        while not self._reconnect_stop.is_set():
            if not self.auto_reconnect or self.connected:
                break
            time.sleep(RECONNECT_DELAY)
            if self._reconnect_stop.is_set() or not self.auto_reconnect or self.connected:
                break
            args = self._connect_args
            if args is None:
                break
            self._log(f"[auto-reconnect] trying {args[0]}:{args[1]}/{args[2]}", "cmd")
            if self.connect(*args, silent=True):
                break

    # ── queue draining (GUI calls poll() via tk after()) ──────────────

    def poll(self):
        while not self.log_queue.empty():
            text, tag = self.log_queue.get_nowait()
            if self.on_log:
                self.on_log(text, tag)
        while not self.resp_queue.empty():
            resp = self.resp_queue.get_nowait()
            if self.on_log:
                self.on_log(resp)
            if self.on_resp:
                self.on_resp(resp)
        while not self.status_queue.empty():
            state = self.status_queue.get_nowait()
            if self.on_status:
                self.on_status(state)
        while not self.disconnect_queue.empty():
            self.disconnect_queue.get_nowait()
            if self.connected and self.on_async_disconnect:
                self.on_async_disconnect()
        lines = []
        while not self.telem_queue.empty():
            line = self.telem_queue.get_nowait()
            if not line:
                if lines:
                    text = "\n".join(lines)
                    if self.on_telem:
                        self.on_telem(text)
                    lines = []
            else:
                lines.append(line)
        if lines:
            text = "\n".join(lines)
            if self.on_telem:
                self.on_telem(text)

    def _log(self, text, tag=None):
        self.log_queue.put((text, tag))
