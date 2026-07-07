from declarations import *
from adc import PDU_ADC, THERMAL_ADC
from dataclasses import dataclass
import motor as motor_ctrl
import threading
import socket
import time
import sys


@dataclass(frozen=True)
class SensorSnapshot:
    timestamp: float
    pdu: dict
    thermal: dict
    pwr_good: dict
    faults: dict


class SensorReader(threading.Thread):
    def __init__(self, interval=2.0):
        super().__init__(daemon=True)
        self.interval = interval
        self._latest = None
        self._lock = threading.Lock()
        self._continue = True

        self.pdu_adc = PDU_ADC()
        self.thermal_adc = THERMAL_ADC()

        self.pg_pins = {
            "PWR_GOOD_12": gpio_PWR_GOOD_12,
            "PWR_GOOD_5": gpio_PWR_GOOD_5,
            "PWR_GOOD_9": gpio_PWR_GOOD_9,
        }
        self.flt_pins = {
            "FLT_P1": gpio_FLT_P1,
            "FLT_P2": gpio_FLT_P2,
            "FLT_P3": gpio_FLT_P3,
            "FLT_P4": gpio_FLT_P4,
            "FLT_P5": gpio_FLT_P5,
            "FLT_MOTCON": gpio_FLT_MOTCON,
        }

    @property
    def latest(self):
        return self._latest

    def stop(self):
        self._continue = False

    def run(self):
        while self._continue:
            t0 = time.time()
            pdu = self._read_pdu()
            thermal = self._read_thermal()
            pg = {k: p.read() for k, p in self.pg_pins.items()}
            flt = {k: p.read() for k, p in self.flt_pins.items()}
            snap = SensorSnapshot(
                timestamp=time.time(),
                pdu=pdu,
                thermal=thermal,
                pwr_good=pg,
                faults=flt,
            )
            with self._lock:
                self._latest = snap
            elapsed = time.time() - t0
            time.sleep(max(0, self.interval - elapsed))

    def _read_pdu(self):
        try:
            return self.pdu_adc.poll()
        except Exception as e:
            print(f"PDU ADC error: {e}")
            return {}

    def _read_thermal(self):
        try:
            return self.thermal_adc.poll()
        except Exception as e:
            print(f"Thermal ADC error: {e}")
            return {}


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
                snap = self.reader.latest
                if snap is None:
                    time.sleep(1)
                    continue
                lines = [f"TS={snap.timestamp:.3f}"]
                for k, v in snap.pdu.items():
                    lines.append(f"{k}={v}")
                for k, v in snap.thermal.items():
                    lines.append(f"{k}={v}")
                for k, v in snap.pwr_good.items():
                    lines.append(f"{k}={v}")
                for k, v in snap.faults.items():
                    lines.append(f"{k}={v}")
                payload = "\n".join(lines) + "\n"
                try:
                    self.sock.sendall(payload.encode("utf-8"))
                except OSError:
                    break
                time.sleep(2)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            try:
                self.sock.close()
            except OSError:
                pass
            print(f"[telem] client disconnected: {self.addr}")


_EN_PINS = [gpio_EN_P1, gpio_EN_P2, gpio_EN_P3, gpio_EN_P4, gpio_EN_P5]

def _periph_to_gpio(name):
    if name == "MOTCON":
        return gpio_EN_MOTCON
    if name in PERIPH_BINDINGS:
        idx = PERIPH_BINDINGS[name]
        if 0 <= idx < len(_EN_PINS):
            return _EN_PINS[idx]
    return None


class CommandThread(threading.Thread):
    def __init__(self, cmd_port, reader):
        super().__init__(daemon=True)
        self.port = cmd_port
        self.reader = reader
        self._uart = None
        self._uart_lock = threading.Lock()

    def _get_uart(self):
        with self._uart_lock:
            if self._uart is None:
                self._uart = motor_ctrl.open_uart()
            return self._uart

    def _do_motor(self, parts):
        if len(parts) < 2:
            return "ERR: missing motor subcommand"
        sub = parts[1]
        u = self._get_uart()
        if sub == "PING":
            motor_ctrl.send(u, "HI\n")
        elif sub == "SM":
            if len(parts) < 4:
                return "ERR: usage: MOTOR SM <board> <0|1>"
            motor_ctrl.send(u, f"SM_{parts[2]}_{parts[3]}\n")
        elif sub == "SS":
            if len(parts) < 4:
                return "ERR: usage: MOTOR SS <board> <speed>"
            motor_ctrl.send(u, f"SS_{parts[2]}_{parts[3]}\n")
        elif sub == "GS":
            if len(parts) < 3:
                return "ERR: usage: MOTOR GS <board>"
            motor_ctrl.send(u, f"GS_{parts[2]}\n")
        elif sub == "CE":
            motor_ctrl.send(u, "CE\n")
        elif sub == "SP":
            if len(parts) < 4:
                return "ERR: usage: MOTOR SP <board> <PARAM=VAL>"
            motor_ctrl.send(u, f"SP_{parts[2]}_{parts[3]}\n")
        elif sub == "RAW":
            motor_ctrl.send(u, " ".join(parts[2:]) + "\n")
        else:
            return f"ERR: unknown motor subcommand: {sub}"
        resp = motor_ctrl.recv(u, timeout=2)
        return resp if resp else "OK"

    def _do_en(self, parts):
        if len(parts) < 3:
            return "ERR: usage: EN <name> <0|1>"
        gpio = _periph_to_gpio(parts[1])
        if gpio is None:
            return f"ERR: unknown peripheral: {parts[1]}"
        if parts[2] not in ("0", "1"):
            return "ERR: val must be 0 or 1"
        gpio.write(int(parts[2]))
        return "OK"

    def _do_bw(self, parts):
        if len(parts) < 2:
            return "ERR: usage: BW <name> [ms]"
        gpio = _periph_to_gpio(parts[1])
        if gpio is None:
            return f"ERR: unknown peripheral: {parts[1]}"
        ms = int(parts[2]) if len(parts) > 2 else 2000
        gpio.write(1)
        time.sleep(ms / 1000.0)
        gpio.write(0)
        return "OK"

    def _do_status(self, parts):
        snap = self.reader.latest
        if snap is None:
            return "ERR: no data yet"
        if parts:
            subset = parts[0]
            if subset == "PG":
                d = snap.pwr_good
            elif subset == "FLT":
                d = snap.faults
            elif subset == "EN":
                d = {k: _periph_to_gpio(k).read()
                     for k in PERIPH_BINDINGS}
                d["MOTCON"] = gpio_EN_MOTCON.read()
            else:
                return "ERR: unknown status subset"
            return "\n".join(f"{k}={v}" for k, v in d.items())
        lines = [f"TS={snap.timestamp:.3f}"]
        for k, v in snap.pdu.items():
            lines.append(f"{k}={v}")
        for k, v in snap.thermal.items():
            lines.append(f"{k}={v}")
        for k, v in snap.pwr_good.items():
            lines.append(f"{k}={v}")
        for k, v in snap.faults.items():
            lines.append(f"{k}={v}")
        return "\n".join(lines)

    def run(self):
        print(f"[cmd] listening on 0.0.0.0:{self.port}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.settimeout(1.0)
                srv.bind(("0.0.0.0", self.port))
                srv.listen()
                while True:
                    try:
                        client, addr = srv.accept()
                    except socket.timeout:
                        continue
                    print(f"[cmd] client connected: {addr}")
                    with client:
                        client.settimeout(5.0)
                        f = client.makefile("rw", buffering=1)
                        try:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                parts = line.split()
                                cmd = parts[0]
                                try:
                                    if cmd == "PING":
                                        resp = "PONG"
                                    elif cmd == "STATUS":
                                        resp = self._do_status(parts[1:])
                                    elif cmd == "EN":
                                        resp = self._do_en(parts)
                                    elif cmd == "BW":
                                        resp = self._do_bw(parts)
                                    elif cmd == "MOTOR":
                                        resp = self._do_motor(parts)
                                    else:
                                        resp = f"ERR: unknown: {cmd}"
                                except Exception as e:
                                    resp = f"ERR: {e}"
                                f.write(resp + "\n")
                                f.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            pass
                        except socket.timeout:
                            pass
                        print(f"[cmd] client disconnected: {addr}")
        except OSError as e:
            print(f"[cmd] failed to bind port {self.port}: {e}")


def main(telem_port=8005, cmd_port=8006, sensor_interval=2.0):
    reader = SensorReader(interval=sensor_interval)
    reader.start()
    print(f"[host] SensorReader started (interval={sensor_interval}s)")

    cmd = CommandThread(cmd_port, reader)
    cmd.start()

    telem_threads = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.settimeout(1.0)
            srv.bind(("0.0.0.0", telem_port))
            srv.listen()
            print(f"[host] telem on 0.0.0.0:{telem_port}, cmd on 0.0.0.0:{cmd_port}")

            while True:
                try:
                    client, addr = srv.accept()
                    t = TelemThread(client, reader, addr)
                    t.start()
                    telem_threads.append(t)
                except socket.timeout:
                    continue
    except KeyboardInterrupt:
        print("\n[host] KeyboardInterrupt")
    finally:
        print("[host] shutting down...")
        reader.stop()
        reader.join(timeout=3)
        for t in telem_threads:
            t.join(timeout=1)
        print("[host] done")


if __name__ == "__main__":
    telem_port = int(sys.argv[1]) if len(sys.argv) > 1 else 8005
    cmd_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8006
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    main(telem_port=telem_port, cmd_port=cmd_port, sensor_interval=interval)
