#!/usr/bin/env python3
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
from subcomponents.motor import setup as setup_motor

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

    if is_ebox:
        setup_motor()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[svarog] shutting down...")
        if _hc:
            _hc.stop()
            _hc.join(timeout=3)
        if s_reader:
            s_reader.stop()
            s_reader.join(timeout=3)
        print("[svarog] done")

if __name__ == "__main__":
    telem_port = int(sys.argv[1]) if len(sys.argv) > 1 else 8005
    cmd_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8006
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    main(telem_port=telem_port, cmd_port=cmd_port, sensor_interval=interval)
