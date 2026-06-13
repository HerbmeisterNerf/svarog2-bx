import re
import threading
from declarations import PERIPH_BINDINGS, peripheral_requests, peripheral_requests_lock, NODE_ID


class CommandReceiver(threading.Thread):
    """Reads ground station commands from the TCP socket and dispatches them."""

    _CMD_PATTERN = re.compile(r'start:(.+?)end:')

    def __init__(self, sock, uart_flywheel=None, uart_deployment=None):
        super().__init__(daemon=True)
        self.sock = sock
        self.uart_flywheel = uart_flywheel
        self.uart_deployment = uart_deployment
        self._buf = ""
        self._deploy_armed = False

    def run(self):
        while True:
            try:
                chunk = self.sock.recv(64).decode("utf-8", errors="replace")
                if not chunk:
                    break
                self._buf += chunk
                for match in self._CMD_PATTERN.finditer(self._buf):
                    self._dispatch(match.group(1))
                # Discard everything up to and including the last complete match
                last_end = 0
                for m in self._CMD_PATTERN.finditer(self._buf):
                    last_end = m.end()
                self._buf = self._buf[last_end:]
            except OSError:
                break
            except Exception as e:
                print(f"[{NODE_ID}] CommandReceiver error: {e}")
                break

    def _dispatch(self, cmd):
        print(f"[{NODE_ID}] CMD: {cmd}")

        # Heaters: H1 .. H<NUM_HEATERS>
        m = re.match(r'^H(\d)$', cmd)
        if m:
            self._toggle_peripheral(f"HEAT_{m.group(1)}")
            return

        # Burn wires: B1 .. B<NUM_BW>
        m = re.match(r'^B(\d)$', cmd)
        if m:
            self._pulse_bw(f"BW_{m.group(1)}")
            return

        # Cameras: C1 .. C<NUM_SECONDARY_MPUS>
        m = re.match(r'^C(\d)$', cmd)
        if m:
            self._camera_command(int(m.group(1)))
            return

        if cmd == "MO":
            # EBOX spinning motor enable
            if self.uart_flywheel:
                self.uart_flywheel.send("SM_0_1\n")

        elif cmd == "FWEN":
            # CubeSat flywheel enable
            if self.uart_flywheel:
                self.uart_flywheel.send("SM_0_1\n")

        elif cmd.startswith("FW_"):
            # CubeSat flywheel speed: FW_<0-900>
            parts = cmd.split("_", 1)
            if len(parts) == 2 and self.uart_flywheel:
                self.uart_flywheel.send(f"SS_0_{parts[1]}\n")

        elif cmd == "DPARM":
            self._deploy_armed = True
            print(f"[{NODE_ID}] Deployment ARMED")

        elif cmd == "DPFIRE":
            if self._deploy_armed:
                if self.uart_deployment:
                    self.uart_deployment.send("SM_1_1\n")
                    print(f"[{NODE_ID}] Deployment FIRED")
                self._deploy_armed = False
            else:
                print(f"[{NODE_ID}] Deployment fire ignored — not armed")

        elif cmd == "TE":
            pass  # telemetry is pushed continuously; no action needed

        elif cmd == "IM":
            # Signal WatchImage to send a snapshot
            try:
                from WatchImage import WatchImage
                WatchImage.send_image = True
            except ImportError:
                pass

    def _toggle_peripheral(self, name):
        if name not in PERIPH_BINDINGS:
            print(f"[{NODE_ID}] Unknown peripheral: {name}")
            return
        with peripheral_requests_lock:
            peripheral_requests[name] = 1 - peripheral_requests[name]

    def _pulse_bw(self, name, duration=3.0):
        if name not in PERIPH_BINDINGS:
            print(f"[{NODE_ID}] Unknown burn wire: {name}")
            return
        with peripheral_requests_lock:
            peripheral_requests[name] = 1
        threading.Timer(duration, self._bw_off, args=[name]).start()

    def _bw_off(self, name):
        with peripheral_requests_lock:
            peripheral_requests[name] = 0

    def _camera_command(self, index):
        try:
            from secondary_mpu_client import SecondaryMPUClient
            SecondaryMPUClient().send_command(index, "record_start")
        except Exception as e:
            print(f"[{NODE_ID}] Camera {index} command failed: {e}")
