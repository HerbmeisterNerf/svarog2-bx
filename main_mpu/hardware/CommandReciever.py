"""Receives TC Space Packets from the ground station over UDP and dispatches commands.

Each UDP datagram is one complete space packet.  CRC validation and command dispatch
happen synchronously in the recv loop — the thread is simple and stateless apart
from the deploy-arm flag and the shared tc_ack dict.
"""

import os
import sys
import struct
import threading

from declarations import PERIPH_BINDINGS, peripheral_requests, peripheral_requests_lock, NODE_ID

_shared = os.path.join(os.path.dirname(__file__), '..', '..', 'shared')
sys.path.insert(0, _shared)

from space_packet import parse_packet, PKT_TYPE_TC
from tc_commands import (
    CMD_HEATER_TOGGLE, CMD_BW_PULSE,
    CMD_MOT_ENABLE, CMD_FW_ENABLE, CMD_FW_SPEED,
    CMD_DEPLOY_ARM, CMD_DEPLOY_FIRE,
    CMD_CAM_RECORD, CMD_CAM_SNAPSHOT,
    unpack_tc,
)

# Placeholder deployment-motor target (rad/s, velocity mode) until the real
# deployment motion profile is defined. See CMD_DEPLOY_FIRE handling below.
DEPLOY_SPEED = 10


class CommandReceiver(threading.Thread):
    """Reads TC Space Packets from a UDP socket and dispatches commands."""

    def __init__(self, udp_sock, motor_flywheel=None, motor_deployment=None, tc_ack=None):
        super().__init__(daemon=True)
        self._sock = udp_sock
        self.motor_flywheel  = motor_flywheel      # MotorController (SimpleFOC Commander)
        self.motor_deployment = motor_deployment   # MotorController (SimpleFOC Commander)
        self.tc_ack = tc_ack if tc_ack is not None else {"seq": 0}
        self._deploy_armed = False

    def run(self):
        while True:
            try:
                raw, addr = self._sock.recvfrom(512)
            except OSError:
                break
            except Exception as e:
                print(f"[{NODE_ID}] CommandReceiver recv error: {e}")
                continue

            pkt = parse_packet(raw)
            if pkt is None:
                print(f"[{NODE_ID}] Bad TC packet from {addr} — CRC fail or malformed")
                continue
            if pkt["pkt_type"] != PKT_TYPE_TC:
                continue

            parsed = unpack_tc(pkt["data_field"])
            if parsed is None:
                continue
            cmd_id, args = parsed

            self._dispatch(cmd_id, args)
            self.tc_ack["seq"] = pkt["seq_count"]
            print(f"[{NODE_ID}] TC #{pkt['seq_count']} cmd=0x{cmd_id:02X} accepted")

    def _dispatch(self, cmd_id: int, args: bytes):
        if cmd_id == CMD_HEATER_TOGGLE:
            n = args[0] if args else 1
            self._toggle_peripheral(f"HEAT_{n}")

        elif cmd_id == CMD_BW_PULSE:
            n = args[0] if args else 1
            self._pulse_bw(f"BW_{n}")

        elif cmd_id == CMD_MOT_ENABLE:
            if self.motor_flywheel:
                self.motor_flywheel.enable("velocity")

        elif cmd_id == CMD_FW_ENABLE:
            if self.motor_flywheel:
                self.motor_flywheel.enable("velocity")

        elif cmd_id == CMD_FW_SPEED:
            if len(args) >= 2 and self.motor_flywheel:
                speed = struct.unpack(">H", args[:2])[0]
                # velocity-mode target in rad/s (was RPM to the old Nano firmware)
                self.motor_flywheel.set_target(speed)

        elif cmd_id == CMD_DEPLOY_ARM:
            self._deploy_armed = True
            print(f"[{NODE_ID}] Deployment ARMED")

        elif cmd_id == CMD_DEPLOY_FIRE:
            if self._deploy_armed:
                if self.motor_deployment:
                    # TODO: define the deployment motion profile (target/duration).
                    # Placeholder: spin the deployment motor in velocity mode.
                    self.motor_deployment.enable("velocity")
                    self.motor_deployment.set_target(DEPLOY_SPEED)
                    print(f"[{NODE_ID}] Deployment FIRED")
                self._deploy_armed = False
            else:
                print(f"[{NODE_ID}] DPFIRE ignored — not armed")

        elif cmd_id == CMD_CAM_RECORD:
            if len(args) >= 2:
                rz_idx, action = args[0], args[1]
                self._camera_command(rz_idx, "record_start" if action else "record_stop")

        elif cmd_id == CMD_CAM_SNAPSHOT:
            if args:
                self._camera_command(args[0], "snapshot")

    def _toggle_peripheral(self, name: str):
        if name not in PERIPH_BINDINGS:
            print(f"[{NODE_ID}] Unknown peripheral: {name}")
            return
        with peripheral_requests_lock:
            peripheral_requests[name] = 1 - peripheral_requests[name]

    def _pulse_bw(self, name: str, duration: float = 3.0):
        if name not in PERIPH_BINDINGS:
            print(f"[{NODE_ID}] Unknown burn wire: {name}")
            return
        with peripheral_requests_lock:
            peripheral_requests[name] = 1
        threading.Timer(duration, self._bw_off, args=[name]).start()

    def _bw_off(self, name: str):
        with peripheral_requests_lock:
            peripheral_requests[name] = 0

    def _camera_command(self, index: int, cmd: str):
        try:
            from secondary_mpu_client import SecondaryMPUClient
            SecondaryMPUClient().send_command(index, cmd)
        except Exception as e:
            print(f"[{NODE_ID}] Camera {index} command failed: {e}")
