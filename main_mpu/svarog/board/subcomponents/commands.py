import os
import subprocess
import time
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
        try:
            _st.motor_speed = float(val)
        except ValueError:
            pass
        if _st.auto_stop:
            _st.auto_stop.rearm()
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
    # turn off heaters to limit current
    _st.heater_ctrl._continue = False
    try:
        time.sleep(0.5)
        gpio.write(1)
        time.sleep(ms / 1000.0)
        gpio.write(0)
        time.sleep(0.5)
    finally:
        _st.heater_ctrl._continue = True
    return "OK"

def _do_cam(parts):
    try:
        from camstream import cam_manager
    except Exception as e:
        return f"ERR: camstream unavailable: {e}"
    if not parts:
        return "ERR: usage: CAM START|STOP|STATUS|REC|STOPREC [all|<id>]"
    sub = parts[0].upper()
    target = parts[1].lower() if len(parts) > 1 else "all"
    if sub == "STATUS":
        return cam_manager.status()
    if sub == "START":
        return cam_manager.start_all() if target == "all" else cam_manager.start(target)
    if sub == "STOP":
        return cam_manager.stop_all() if target == "all" else cam_manager.stop(target)
    if sub == "REC":
        return (cam_manager.start_record_all() if target == "all"
                else cam_manager.start_record(target))
    if sub == "STOPREC":
        return (cam_manager.stop_record_all() if target == "all"
                else cam_manager.stop_record(target))
    return f"ERR: unknown CAM subcommand: {sub}"

JPEG_REC_FLAG = "/tmp/svarog_jpeg_rec"

def _jpeg_sender_alive():
    try:
        out = subprocess.run(["pgrep", "-f", r"jpeg_sender\.py --device"],
                             capture_output=True, text=True, timeout=5)
        return bool(out.stdout.strip())
    except Exception:
        return False

def _do_jpeg_rec(parts):
    if not parts:
        rec = 1 if os.path.exists(JPEG_REC_FLAG) else 0
        return (f"JPEG_REC={rec} SENDER={1 if _jpeg_sender_alive() else 0}")
    sub = parts[0].upper()
    if sub in ("ON", "1"):
        try:
            with open(JPEG_REC_FLAG, "w") as f:
                f.write(str(int(time.time())))
        except OSError as e:
            return f"ERR: {e}"
        return "OK JPEG_REC=1"
    if sub in ("OFF", "0"):
        try:
            os.remove(JPEG_REC_FLAG)
        except OSError:
            pass
        return "OK JPEG_REC=0"
    return "ERR: usage: JPEGREC <ON|OFF>"

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
        elif cmd == "ENCODER_RESET":
            if is_ebox:
                return "ERR: no encoder on ebox"
            if not _st.enc_reader:
                return "ERR: encoder not running"
            _st.enc_reader.reset_accum()
            return "OK"
        elif cmd == "AUTOSTOP":
            if is_ebox:
                return "ERR: no auto-stop on ebox"
            if len(parts) < 2:
                return f"AUTO_STOP={1 if _st.auto_stop_enabled else 0}"
            val = parts[1].upper()
            if val == "ON" or val == "1":
                _st.auto_stop_enabled = True
                if _st.auto_stop:
                    _st.auto_stop.rearm()
                return "OK AUTO_STOP=1"
            if val == "OFF" or val == "0":
                _st.auto_stop_enabled = False
                return "OK AUTO_STOP=0"
            return "ERR: AUTOSTOP <ON|OFF>"
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
        elif cmd == "CAM":
            return _do_cam(parts[1:])
        elif cmd == "JPEGREC":
            return _do_jpeg_rec(parts[1:])
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