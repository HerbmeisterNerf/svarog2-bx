#!/usr/bin/env python3
import subprocess
import sys, os, time, threading

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "subcomponents"))

from BOARD_SELECT import is_ebox
from declarations import HEATER_SENSOR_PAIRS
from subcomponents import state as _st
from subcomponents.sensor_reader import SensorReader
from subcomponents.temp_control import HeaterController
from subcomponents.send_telem import telem_server
from subcomponents.command_server import cmd_server
from subcomponents.motor import MotorReader


def _cam_sender_spec():
    """(device, name) tuples for this board's JPEG getter."""
    if is_ebox:
        return [
            ("/dev/video0", "cam1"),
            ("/dev/video2", "cam2"),
            ("/dev/video4", "cam3"),
            ("/dev/video6", "cam4"),
        ]
    return [("/dev/video0", "cubesat")]


def _spawn_sender(specs):
    log = open("/tmp/jpeg_sender.log", "ab")
    cmd = [sys.executable, os.path.join(_HERE, "subcomponents", "jpeg_sender.py"),
           "--port", "9001", "--interval", "0.15"]
    for dev, name in specs:
        cmd += ["--cam", f"{dev}:{name}"]
    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                         stdout=log, stderr=subprocess.STDOUT)
    print(f"[svarog] jpeg service spawned pid={p.pid} "
          f"cams={[n for _, n in specs]}", flush=True)
    return {"proc": p, "log": log, "last_start": time.time()}


def _start_cam_senders():
    # clear any sender left over from a previous main.py instance
    try:
        subprocess.run(["pkill", "-f", r"jpeg_sender\.py --cam"],
                       capture_output=True, timeout=5)
    except Exception:
        pass
    time.sleep(1)
    specs = _cam_sender_spec()
    svc = _spawn_sender(specs)
    stop_evt = threading.Event()

    def _supervise():
        while not stop_evt.is_set():
            if svc["proc"].poll() is not None:
                if time.time() - svc["last_start"] > 10.0:
                    try:
                        svc["log"].write(
                            f"[main] jpeg service exited rc={svc['proc'].returncode}, "
                            "restarting\n".encode())
                        svc["log"].flush()
                    except Exception:
                        pass
                    try:
                        svc["log"].close()
                    except Exception:
                        pass
                    svc.update(_spawn_sender(specs))
            stop_evt.wait(2.0)

    t = threading.Thread(target=_supervise, daemon=True)
    t.start()
    return svc, stop_evt


def _stop_cam_senders(svc):
    try:
        svc["proc"].terminate()
    except Exception:
        pass
    try:
        svc["proc"].wait(timeout=3)
    except Exception:
        try:
            svc["proc"].kill()
        except Exception:
            pass
    try:
        svc["log"].close()
    except Exception:
        pass


def main(telem_port=8005, cmd_port=8006, sensor_interval=2.0):
    role = "EBOX" if is_ebox else "CUBESAT"
    print(f"[svarog] role={role}  telem={telem_port}  cmd={cmd_port}")

    s_reader = SensorReader(interval=sensor_interval, has_adc=is_ebox)
    s_reader.start()
    print(f"[svarog] SensorReader started (role={role}, has_adc={is_ebox}, interval={sensor_interval}s)")


    _hc = HeaterController(s_reader)
    _st.heater_ctrl = _hc
    _hc.start()
    print(f"[svarog] HeaterController started ({len(HEATER_SENSOR_PAIRS)} heaters)")

    t_telem = threading.Thread(target=telem_server, args=(telem_port, s_reader), daemon=True)
    t_cmd = threading.Thread(target=cmd_server, args=(cmd_port, s_reader), daemon=True)
    t_telem.start()
    t_cmd.start()

    _st.motor_reader = MotorReader()
    _st.motor_reader.start()
    print("[svarog] MotorReader started")

    if not is_ebox:
        from subcomponents.encoder_new import EncoderReader, AutoStop
        _st.enc_reader = EncoderReader()
        _st.enc_reader.start()
        print("[svarog] EncoderReader started (cubesat)")
        _st.auto_stop = AutoStop(_st.enc_reader)
        _st.auto_stop.start()
        print("[svarog] AutoStop started (cubesat)")

    jpeg_svc, _jpeg_stop = _start_cam_senders()
    print("[svarog] jpeg service started")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[svarog] shutting down...")
        if _st.auto_stop:
            _st.auto_stop.stop()
        if _st.enc_reader:
            _st.enc_reader.stop()
        if _hc:
            _hc.stop()
            _hc.join(timeout=3)
        if s_reader:
            s_reader.stop()
            s_reader.join(timeout=3)
        _stop_cam_senders(jpeg_svc)
        print("[svarog] done")

if __name__ == "__main__":
    telem_port = int(sys.argv[1]) if len(sys.argv) > 1 else 8005
    cmd_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8006
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    main(telem_port=telem_port, cmd_port=cmd_port, sensor_interval=interval)
