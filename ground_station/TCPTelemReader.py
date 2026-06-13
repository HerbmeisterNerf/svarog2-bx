import select
import threading
import time


class TCPTelemReader(threading.Thread):
    """Reads newline-delimited CSV telemetry pushed from the flight computer over TCP.

    Runs as a daemon thread.  When the socket is None or disconnected it sleeps
    and retries — the caller only needs to update CommonData.client_TCP_socket_* and
    the corresponding status flag; this thread picks up automatically.
    """

    def __init__(self, get_socket_fn, telem_queue, get_status_fn):
        super().__init__(daemon=True)
        self._get_socket = get_socket_fn   # lambda returning current socket or None
        self._queue = telem_queue
        self._get_status = get_status_fn   # lambda returning bool (connected)

    def run(self):
        buf = ""
        while True:
            if not self._get_status():
                time.sleep(0.2)
                buf = ""
                continue

            sock = self._get_socket()
            if sock is None:
                time.sleep(0.2)
                continue

            try:
                ready, _, _ = select.select([sock], [], [], 1.0)
                if not ready:
                    continue
                chunk = sock.recv(4096)
                if not chunk:
                    time.sleep(0.2)
                    continue
                buf += chunk.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        # Keep only the latest packet — drop stale ones
                        while not self._queue.empty():
                            try:
                                self._queue.get_nowait()
                            except Exception:
                                break
                        self._queue.put(line)
            except Exception as e:
                if self._get_status():
                    print(f"TCPTelemReader error: {e}")
                time.sleep(0.5)
                buf = ""
