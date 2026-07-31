import time, threading, socket
from BOARD_SELECT import is_ebox
from declarations import PERIPH_BINDINGS
import motor
import check_status
from subcomponents import state as _st
from subcomponents.send_telem import snap_to_text, set_push_interval

def _do_motor(parts):
    if len(parts) < 2:
        return "ERR: MOTOR subcommand required"
    sub = parts[1].upper()
    if sub == "PING":
        return motor.ping() or "NO RESPONSE"
    elif sub.startswith("TC"):
        val = sub[2:] if len(sub) > 2 else (parts[2] if len(parts) > 2 else None)
        if val is None:
            return "ERR: MOTOR TC<0-3>"
        return motor.set_mode(val) or "OK"
    elif sub.startswith("T") and not sub.startswith("TC"):
        val = sub[1:] if len(sub) > 1 else (parts[2] if len(parts) > 2 else None)
        if val is None:
            return "ERR: MOTOR T<val>"
        return motor.set_speed(val) or "OK"
    elif sub.startswith("C"):
        val = sub[1:] if len(sub) > 1 else (parts[2] if len(parts) > 2 else None)
        if val is None:
            return "ERR: MOTOR C<val>"
        return motor.set_current(val) or "OK"
    elif sub == "RAW":
        return motor.raw(" ".join(parts[2:])) or "OK"
    return f"ERR: unknown MOTOR subcommand: {sub}"

def _do_en(parts):
    if len(parts) < 3:
        return "ERR: usage: EN <name> <0|1>"
    gpio = PERIPH_BINDINGS.get(parts[1])
    if gpio is None:
        return f"ERR: unknown peripheral: {parts[1]}"
    if parts[2] not in ("0", "1"):
        return "ERR: val must be 0 or 1"
    gpio.write(int(parts[2]))
    return "OK"

def _do_bw(parts):
    if len(parts) < 2:
        return "ERR: usage: BW <name> [ms]"
    gpio = PERIPH_BINDINGS.get(parts[1])
    if gpio is None:
        return f"ERR: unknown peripheral: {parts[1]}"
    ms = int(parts[2]) if len(parts) > 2 else 1500
    gpio.write(1)
    time.sleep(ms / 1000.0)
    gpio.write(0)
    return "OK"

def _do_status(reader, parts):
    if not is_ebox:
        pg, flt = check_status.read_all()
        en = check_status.read_en()
        lines = []
        for k, v in pg.items():
            lines.append(f"{k}={v}")
        for k, v in flt.items():
            lines.append(f"{k}={v}")
        for k, v in en.items():
            lines.append(f"{k}={v}")
        return "\n".join(lines)
    snap = reader.latest() if reader else None
    if snap is None:
        return "ERR: no data yet"
    if parts:
        subset = parts[0].upper()
        if subset == "PG":
            d = snap.pwr_good
        elif subset == "FLT":
            d = snap.faults
        elif subset == "EN":
            d = check_status.read_en()
        else:
            return "ERR: unknown status subset"
        return "\n".join(f"{k}={v}" for k, v in d.items())
    return snap_to_text(snap)

def handle_command(line, reader):
    parts = line.split()
    if not parts:
        return ""
    cmd = parts[0].upper()
    try:
        if cmd == "PING":
            return "PONG"
        elif cmd == "STATUS":
            return _do_status(reader, parts[1:])
        elif cmd == "EN":
            return _do_en(parts)
        elif cmd == "BW":
            return _do_bw(parts)
        elif cmd == "MOTOR":
            return _do_motor(parts)
        elif cmd == "TEMP":
            if not is_ebox:
                return "ERR: no sensors"
            snap = reader.latest() if reader else None
            if snap is None:
                return "ERR: no data yet"
            return "\n".join(f"{k}={v}" for k, v in snap.thermal.items())
        elif cmd == "PDU":
            if not is_ebox:
                return "ERR: no sensors"
            snap = reader.latest() if reader else None
            if snap is None:
                return "ERR: no data yet"
            return "\n".join(f"{k}={v}" for k, v in snap.pdu.items())
        elif cmd == "ENCODER":
            try:
                from encoder import SPIEncoder
                enc = SPIEncoder()
                data = enc.read_all()
                enc.close()
                return "\n".join(f"{k}={v}" for k, v in data.items())
            except Exception as e:
                return f"ERR: {e}"
        elif cmd == "I2C":
            try:
                from sensor import scan
                scan()
                return "OK"
            except Exception as e:
                return f"ERR: {e}"
        elif cmd == "HEATER":
            if len(parts) < 3:
                return "ERR: usage: HEATER <name> <duty>"
            name = parts[1]
            duty = float(parts[2])
            gpio = PERIPH_BINDINGS.get(name)
            if gpio is not None:
                gpio.write(1 if duty > 0 else 0)
                return "OK"
            return f"ERR: unknown heater: {name}"
        elif cmd == "SET_TRANS_PERIOD":
            if len(parts) < 2:
                return "ERR: usage: SET_TRANS_PERIOD <seconds>"
            try:
                val = float(parts[1])
                set_push_interval(val)
                if reader:
                    reader.set_interval(val)
                return f"OK interval={val}"
            except ValueError:
                return "ERR: invalid number"
        elif cmd == "HEATER_SETPOINT":
            if len(parts) < 3:
                return "ERR: usage: HEATER_SETPOINT <name> <temp_C>"
            name = parts[1]
            try:
                sp = float(parts[2])
            except ValueError:
                return "ERR: invalid temperature"
            if _st.heater_ctrl and _st.heater_ctrl.set_setpoint(name, sp):
                return f"OK {name} setpoint={sp}C"
            return f"ERR: unknown heater: {name}"
        else:
            return f"ERR: unknown command: {cmd}"
    except Exception as e:
        return f"ERR: {e}"

def _keepalive_sock(sock):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    try:
        import struct
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
    except (AttributeError, OSError):
        pass

def cmd_server(port, reader):
    print(f"[cmd] listening on 0.0.0.0:{port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.settimeout(1.0)
            srv.bind(("0.0.0.0", port))
            srv.listen()
            while True:
                try:
                    client, addr = srv.accept()
                except socket.timeout:
                    continue
                print(f"[cmd] client connected: {addr}")
                _keepalive_sock(client)
                f = client.makefile("rw", buffering=1)
                try:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        resp = handle_command(line, reader)
                        f.write(resp + "\n")
                        f.flush()
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
                except (OSError, ValueError):
                    pass
                finally:
                    try:
                        f.close()
                    except Exception:
                        pass
                    try:
                        client.close()
                    except Exception:
                        pass
                print(f"[cmd] client disconnected: {addr}")
    except OSError as e:
        print(f"[cmd] failed to bind port {port}: {e}")
