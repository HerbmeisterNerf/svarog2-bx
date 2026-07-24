"""BEXUS 36 flight simulator — runs on a single machine without flight hardware.

Simulates both EBOX and CubeSat nodes over loopback UDP so the ground station
GUI can be tested end-to-end without any R3B hardware.

Usage (two terminals):

  Terminal 1:
      cd svarog2-bx
      python scripts/flight_sim.py

  Terminal 2:
      cd svarog2-bx/ground_station
      python TCPClientApp.py

  In the GUI:
      - EBOX tab → enter IP "127.0.0.1" → Connect → Telemetry ON
      - CubeSat tab → enter IP "127.0.0.1" → Connect CubeSat → Telem ON
      - Press any command button → sim terminal shows the received TC

What is tested:
  ✓ Space Packet encode / decode (both directions)
  ✓ CRC-16-CCITT on every packet
  ✓ TM secondary header (timestamp, last_tc_seq echo)
  ✓ GUI → TC → sim dispatch → state update
  ✓ Sim → TM → UDPTelemReader → WatchTelem → table update
  ✓ TC acknowledgement visible in next TM (last_tc_seq changes)

What is NOT tested here:
  ✗ Real ADC readings
  ✗ UART motor control
  ✗ GPIO / shift registers
  ✗ E-Link radio link behaviour
"""

import math
import random
import socket
import struct
import sys
import threading
import time
import os

# ------------------------------------------------------------------ path setup
_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(_root, 'shared'))

from space_packet import (
    build_packet, parse_packet,
    build_tm_data_field, parse_tm_data_field,
    PKT_TYPE_TM, PKT_TYPE_TC,
    APID_EBOX_TM, APID_CS_TM,
    TC_UDP_PORT, TM_UDP_PORT,
)
from tc_commands import (
    CMD_HEATER_TOGGLE, CMD_BW_PULSE,
    CMD_MOT_ENABLE, CMD_MOT_DISABLE,
    CMD_FW_ENABLE, CMD_FW_SPEED,
    CMD_DEPLOY_ARM, CMD_DEPLOY_FIRE,
    CMD_CAM_RECORD, CMD_CAM_SNAPSHOT,
    CMD_FOC_MODE, CMD_FOC_TARGET, CMD_FOC_LIMITS, CMD_FOC_ALIGN, CMD_FOC_ZERO,
    FOC_MODE_OPEN, FOC_MODE_VELOCITY, FOC_MODE_POSITION,
    unpack_tc,
)
from image_snapshot import pack_chunks, IMG_UDP_PORT

# On a single machine, send TM to loopback so the ground station receives it
TM_DEST = "127.0.0.1"

# ------------------------------------------------------------------ sim state

class SimState:
    """Mutable state shared between the TC receiver and TM sender threads."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.lock = threading.Lock()
        self.pkg_count = 0
        self.last_tc_seq = 0

        # Power (nominal voltages ± noise)
        self.v28 = 27.8;  self.v5 = 4.95; self.v12 = 11.82
        self.i5  = 0.82;  self.i12 = 0.51

        # Environment
        self.temp      = 22.0   # internal node temperature °C
        self.pressure  = 1013.0 # hPa  (slowly drops on ascent)
        self.mag_x     = 0.12;  self.mag_y = -0.08; self.mag_z = 0.44
        self.acc_x     = 0.01;  self.acc_y = -0.01; self.acc_z = 9.81

        # Peripherals
        self.heaters   = [0] * 6    # heater_1..6 on/off
        self.temps     = [22.0] * 6 # temp_1..6 °C
        self.bws       = [0] * 5    # burn wire pulse state

        # EBOX motor
        self.motor_enabled = False
        self.motor_speed   = 0.0
        self.rz_status     = [1, 1, 1, 1]   # Rock Zeros alive

        # FOC motor (B-G431B-ESC1 / SimpleFOC) — drives the MotorPanel
        self.foc_mode    = FOC_MODE_VELOCITY
        self.foc_target  = 0.0     # rad/s (vel/open) or rad (position)
        self.foc_angle   = 0.0     # shaft angle, rad (integrated)
        self.foc_vel     = 0.0     # shaft velocity, rad/s
        self.foc_cur     = 0.0     # q-axis current, A
        self.foc_trq     = 0.0     # torque, Nm
        self.foc_hall    = "101"
        self.foc_vlim    = 6.0
        self.foc_clim    = 1.0
        self.foc_aligned = False
        self.encoder_angle = 0.0   # AS5047 absolute angle, deg
        self._t_last     = time.time()

        # CubeSat specific
        self.fw_speed      = 0
        self.fw_mode       = 0
        self.deploy_armed  = False
        self.deploy_fired  = False
        self.motor_fault   = 0

    def tick(self, t: float):
        """Advance simulated sensor values each cycle."""
        with self.lock:
            self.pkg_count += 1
            # Slow drift — temperature oscillates, pressure drops (ascent sim)
            self.temp     = 22.0 + 4.0 * math.sin(t / 60.0) + _noise(0.2)
            self.pressure = max(10.0, 1013.0 - (t / 600.0) * 900.0)  # ascent over 10 min
            self.v28  = 27.8 + _noise(0.15)
            self.v5   = 4.95 + _noise(0.02)
            self.v12  = 11.82 + _noise(0.05)
            self.i5   = 0.82 + _noise(0.04) + 0.15 * sum(self.heaters[:2])
            self.i12  = 0.51 + _noise(0.02)
            self.mag_x = 0.12 + _noise(0.01)
            self.mag_y = -0.08 + _noise(0.01)
            self.mag_z = 0.44 + _noise(0.01)
            # Temps track heater state with lag
            for i in range(6):
                target = 22.0 + 8.0 * (1 if (i < len(self.heaters) and self.heaters[i]) else 0)
                self.temps[i] += (target - self.temps[i]) * 0.1 + _noise(0.1)
            # Motor speed ramps
            if self.motor_enabled and self.motor_speed < 1200:
                self.motor_speed = min(1200, self.motor_speed + 50)
            elif not self.motor_enabled and self.motor_speed > 0:
                self.motor_speed = max(0, self.motor_speed - 100)

            self._tick_foc()

    def _tick_foc(self):
        """First-order FOC motor model: velocity chases target, angle integrates,
        current tracks the acceleration effort plus a small load term."""
        now = time.time()
        dt = max(1e-3, min(1.0, now - self._t_last))
        self._t_last = now

        if self.foc_mode == FOC_MODE_POSITION:
            # P-controller on angle -> velocity command (clamped by voltage limit).
            # Gain is kept below 1/dt so the discrete loop stays damped rather
            # than ringing around the setpoint.
            err = self.foc_target - self.foc_angle
            cmd_vel = max(-25.0 * self.foc_vlim, min(25.0 * self.foc_vlim, 0.8 * err))
        else:
            cmd_vel = self.foc_target

        prev_vel = self.foc_vel
        # first-order lag toward the commanded velocity
        self.foc_vel += (cmd_vel - self.foc_vel) * min(1.0, 4.0 * dt)
        self.foc_angle += self.foc_vel * dt

        accel = (self.foc_vel - prev_vel) / dt
        # current: acceleration effort + viscous load + noise, clamped to the limit
        raw = abs(accel) * 0.004 + abs(self.foc_vel) * 0.0035 + _noise(0.006)
        self.foc_cur = max(-self.foc_clim, min(self.foc_clim, raw))
        self.foc_trq = self.foc_cur * 0.047          # Kt = 0.047 Nm/A

        # hall bits cycle through the 6 valid states with shaft position
        states = ["001", "011", "010", "110", "100", "101"]
        self.foc_hall = states[int(abs(self.foc_angle) / (math.pi / 3)) % 6]
        self.encoder_angle = round(math.degrees(self.foc_angle) % 360, 2)
        self.motor_speed = self.foc_vel

    def build_ebox_csv(self) -> str:
        with self.lock:
            h = self.heaters
            tmp = self.temps
            rz = self.rz_status
            fields = [
                self.pkg_count, int(time.time()),
                round(self.v28, 3), round(self.v5, 3), round(self.v12, 3), 0,  # no 24V
                round(self.i5, 3), round(self.i12, 3), 0,
                round(self.temp, 1), round(self.pressure, 1),
                round(self.mag_x, 4), round(self.mag_y, 4), round(self.mag_z, 4),
                round(self.acc_x, 4), round(self.acc_y, 4), round(self.acc_z, 4),
                h[0], h[1], h[2], h[3], h[4], h[5],
                round(tmp[0], 1), round(tmp[1], 1), round(tmp[2], 1),
                round(tmp[3], 1), round(tmp[4], 1), round(tmp[5], 1),
                self.bws[0], self.bws[1],   # burn wires (EBOX has 2)
                0,                           # current_lim_status
                rz[0], rz[1], rz[2], rz[3],
                round(self.motor_speed, 3),
                # --- FOC motor telemetry (fields 37-41) ---
                round(self.encoder_angle, 2),
                round(self.foc_angle, 4),
                round(self.foc_cur, 3),
                round(self.foc_trq, 4),
                self.foc_hall,
            ]
        return ",".join(str(f) for f in fields)

    def build_cs_csv(self) -> str:
        with self.lock:
            h = self.heaters
            tmp = self.temps
            bw = self.bws
            fields = [
                self.pkg_count, int(time.time()),
                round(self.v28, 3), round(self.v5, 3), round(self.v12, 3),
                round(self.i5, 3), round(self.i12, 3),
                round(self.temp, 1), round(self.pressure, 1),
                round(self.mag_x, 4), round(self.mag_y, 4), round(self.mag_z, 4),
                round(self.acc_x, 4), round(self.acc_y, 4), round(self.acc_z, 4),
                h[0], h[1],
                round(tmp[0], 1), round(tmp[1], 1), round(tmp[2], 1),
                round(tmp[3], 1), round(tmp[4], 1), round(tmp[5], 1),
                bw[0], bw[1], bw[2], bw[3], bw[4],
                self.fw_speed, self.fw_mode,
                int(self.deploy_fired), self.motor_fault,
                self.rz_status[0], self.rz_status[1],
            ]
        return ",".join(str(f) for f in fields)


def _noise(sigma: float) -> float:
    return random.gauss(0, sigma)


# --------------------------------------------------------------- TC dispatcher

_CMD_NAMES = {
    CMD_HEATER_TOGGLE: "HEATER_TOGGLE",
    CMD_BW_PULSE:      "BW_PULSE",
    CMD_MOT_ENABLE:    "MOT_ENABLE",
    CMD_MOT_DISABLE:   "MOT_DISABLE",
    CMD_FW_ENABLE:     "FW_ENABLE",
    CMD_FW_SPEED:      "FW_SPEED",
    CMD_DEPLOY_ARM:    "DEPLOY_ARM",
    CMD_DEPLOY_FIRE:   "DEPLOY_FIRE",
    CMD_CAM_RECORD:    "CAM_RECORD",
    CMD_CAM_SNAPSHOT:  "CAM_SNAPSHOT",
    CMD_FOC_MODE:      "FOC_MODE",
    CMD_FOC_TARGET:    "FOC_TARGET",
    CMD_FOC_LIMITS:    "FOC_LIMITS",
    CMD_FOC_ALIGN:     "FOC_ALIGN",
    CMD_FOC_ZERO:      "FOC_ZERO",
}

_FOC_MODE_NAMES = {
    FOC_MODE_OPEN: "open-loop", FOC_MODE_VELOCITY: "velocity", FOC_MODE_POSITION: "position",
}


def dispatch_tc(cmd_id: int, args: bytes, state: SimState, node_label: str, addr=None):
    name = _CMD_NAMES.get(cmd_id, f"0x{cmd_id:02X}")
    with state.lock:
        if cmd_id == CMD_HEATER_TOGGLE:
            n = (args[0] if args else 1) - 1
            if 0 <= n < 6:
                state.heaters[n] ^= 1
                print(f"  [{node_label}] HEAT_{n+1} → {'ON' if state.heaters[n] else 'OFF'}")

        elif cmd_id == CMD_BW_PULSE:
            n = (args[0] if args else 1) - 1
            if 0 <= n < 5:
                state.bws[n] = 1
                print(f"  [{node_label}] BW_{n+1} PULSE start")
                threading.Timer(3.0, _bw_off, args=[state, n, node_label]).start()

        elif cmd_id == CMD_MOT_ENABLE:
            state.motor_enabled = True
            print(f"  [{node_label}] Spinning motor ENABLED")

        elif cmd_id == CMD_MOT_DISABLE:
            state.motor_enabled = False
            print(f"  [{node_label}] Spinning motor DISABLED")

        elif cmd_id == CMD_FW_ENABLE:
            state.fw_mode = 1
            print(f"  [{node_label}] Flywheel ENABLED")

        elif cmd_id == CMD_FW_SPEED:
            if len(args) >= 2:
                rpm = struct.unpack(">H", args[:2])[0]
                state.fw_speed = rpm
                state.fw_mode  = 1 if rpm > 0 else 0
                print(f"  [{node_label}] Flywheel speed → {rpm} RPM")

        elif cmd_id == CMD_DEPLOY_ARM:
            state.deploy_armed = True
            print(f"  [{node_label}] Deployment ARMED  ⚠")

        elif cmd_id == CMD_DEPLOY_FIRE:
            if state.deploy_armed:
                state.deploy_fired = True
                state.deploy_armed = False
                print(f"  [{node_label}] Deployment FIRED  🔥")
            else:
                print(f"  [{node_label}] DEPLOY_FIRE ignored — not armed")

        elif cmd_id == CMD_CAM_RECORD:
            if len(args) >= 2:
                rz, act = args[0], args[1]
                print(f"  [{node_label}] RZ{rz} camera {'RECORD START' if act else 'RECORD STOP'}")

        elif cmd_id == CMD_CAM_SNAPSHOT:
            rz = args[0] if args else 1
            print(f"  [{node_label}] camera {rz} SNAPSHOT requested")
            if addr:
                threading.Thread(target=_send_snapshot, args=(addr[0],),
                                 daemon=True).start()

        # ---------------- fine FOC motor control ----------------
        elif cmd_id == CMD_FOC_MODE:
            if args:
                state.foc_mode = args[0]
                state.foc_target = 0.0
                print(f"  [{node_label}] FOC mode → "
                      f"{_FOC_MODE_NAMES.get(args[0], args[0])}")

        elif cmd_id == CMD_FOC_TARGET:
            if len(args) >= 4:
                state.foc_target = struct.unpack(">f", args[:4])[0]
                unit = "rad" if state.foc_mode == FOC_MODE_POSITION else "rad/s"
                print(f"  [{node_label}] FOC target → {state.foc_target:g} {unit}")

        elif cmd_id == CMD_FOC_LIMITS:
            if len(args) >= 8:
                state.foc_vlim, state.foc_clim = struct.unpack(">ff", args[:8])
                print(f"  [{node_label}] FOC limits → {state.foc_vlim:.1f} V, "
                      f"{state.foc_clim:.1f} A")

        elif cmd_id == CMD_FOC_ALIGN:
            state.foc_aligned = True
            print(f"  [{node_label}] FOC align (initFOC) — Hall aligned")

        elif cmd_id == CMD_FOC_ZERO:
            state.foc_angle = 0.0
            state.foc_target = 0.0
            print(f"  [{node_label}] FOC zero — shaft position tared")

        else:
            print(f"  [{node_label}] Unknown cmd 0x{cmd_id:02X} args={args.hex()}")


_snap_frame_id = [0]


def _sim_frame() -> bytes:
    """A JPEG for the snapshot reply.

    Uses a real Arducam capture (scripts/sim_frame.jpg) when one is present,
    otherwise renders a synthetic frame so the camera panel still has something
    to show without flight hardware.
    """
    real = os.path.join(os.path.dirname(__file__), "sim_frame.jpg")
    if os.path.exists(real) and os.path.getsize(real) > 1000:
        with open(real, "rb") as f:
            return f.read()
    try:
        from PIL import Image, ImageDraw
        import io
        w, h = 640, 400
        im = Image.new("L", (w, h), 30)
        d = ImageDraw.Draw(im)
        # grid + moving marker so successive snapshots visibly differ
        for x in range(0, w, 40):
            d.line([(x, 0), (x, h)], fill=60)
        for y in range(0, h, 40):
            d.line([(0, y), (w, y)], fill=60)
        n = _snap_frame_id[0]
        cx = 60 + (n * 37) % (w - 120)
        d.ellipse([cx - 26, h // 2 - 26, cx + 26, h // 2 + 26], fill=220)
        d.text((12, 10), "SVAROG SIM FRAME  #%d" % n, fill=255)
        d.text((12, h - 22), time.strftime("%H:%M:%S"), fill=255)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=80)
        return buf.getvalue()
    except ImportError:
        return b""


def _send_snapshot(dest_ip: str):
    """Reply to a snapshot TC with a chunked JPEG over UDP (loss-tolerant)."""
    jpeg = _sim_frame()
    if not jpeg:
        print("  [SIM] no frame available (install Pillow or add scripts/sim_frame.jpg)")
        return
    _snap_frame_id[0] = (_snap_frame_id[0] + 1) & 0xFFFF
    dgs = pack_chunks(_snap_frame_id[0], jpeg)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for d in dgs:
        s.sendto(d, (dest_ip, IMG_UDP_PORT))
    s.close()
    print(f"  [SIM] snapshot frame {_snap_frame_id[0]}: {len(jpeg)} bytes "
          f"in {len(dgs)} chunks → {dest_ip}:{IMG_UDP_PORT}")


def _bw_off(state: SimState, n: int, node_label: str):
    with state.lock:
        state.bws[n] = 0
    print(f"  [{node_label}] BW_{n+1} PULSE end (3 s)")


# ----------------------------------------------------------------- TC receiver

def tc_receiver(rx_sock: socket.socket, ebox_state: SimState, cs_state: SimState):
    """Receives TC Space Packets on UDP:8005 and dispatches to the right node state."""
    from space_packet import APID_EBOX_TC, APID_CS_TC
    while True:
        try:
            raw, addr = rx_sock.recvfrom(512)
        except Exception as e:
            print(f"[SIM] TC recv error: {e}")
            continue

        pkt = parse_packet(raw)
        if pkt is None:
            print(f"[SIM] Bad TC from {addr} — CRC fail / malformed")
            continue
        if pkt["pkt_type"] != PKT_TYPE_TC:
            continue

        parsed = unpack_tc(pkt["data_field"])
        if parsed is None:
            continue
        cmd_id, args = parsed
        seq = pkt["seq_count"]
        apid = pkt["apid"]

        if apid == APID_EBOX_TC:
            state = ebox_state
            label = "EBOX"
        elif apid == APID_CS_TC:
            state = cs_state
            label = "CS"
        else:
            print(f"[SIM] Unknown APID 0x{apid:03X} from {addr}")
            continue

        print(f"\n>>> TC #{seq}  APID=0x{apid:03X}  cmd={_CMD_NAMES.get(cmd_id, f'0x{cmd_id:02X}')}"
              f"  args={args.hex() if args else '(none)'}")
        dispatch_tc(cmd_id, args, state, label, addr)

        with state.lock:
            state.last_tc_seq = seq


# ----------------------------------------------------------------- TM sender

def tm_sender(tx_sock: socket.socket, ebox_state: SimState, cs_state: SimState,
              interval: float = 5.0):
    """Broadcasts TM Space Packets for both nodes (flight cadence is 5 s)."""
    t_start = time.time()
    while True:
        t = time.time() - t_start
        ebox_state.tick(t)
        cs_state.tick(t)

        for state, apid, csv_fn, label in (
            (ebox_state, APID_EBOX_TM, ebox_state.build_ebox_csv, "EBOX"),
            (cs_state,   APID_CS_TM,   cs_state.build_cs_csv,     "CS  "),
        ):
            csv = csv_fn()
            with state.lock:
                last_tc = state.last_tc_seq
                seq = state.pkg_count & 0x3FFF

            df  = build_tm_data_field(int(time.time()), last_tc, csv)
            pkt = build_packet(apid, PKT_TYPE_TM, seq, df)
            tx_sock.sendto(pkt, (TM_DEST, TM_UDP_PORT))
            print(f"[{label}] TM #{seq:4d}  last_tc_ack={last_tc:4d}"
                  f"  temp={state.temp:.1f}°C  p={state.pressure:.0f}hPa"
                  f"  heaters={state.heaters[:4]}"
                  + (f"  fw={state.fw_speed}rpm" if label.startswith("CS") else
                     f"  mot={state.motor_speed:.0f}rpm"))

        time.sleep(interval)


# ----------------------------------------------------------------------- main

def main():
    # The status lines use arrows/ticks; Windows consoles default to cp1252 and
    # would raise UnicodeEncodeError mid-run. Force UTF-8 output where supported.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--tm-interval', type=float, default=5.0,
                    help='TM broadcast period in seconds (flight uses 5)')
    cli = ap.parse_args()
    print("=" * 60)
    print("  BEXUS 36 Flight Simulator")
    print("  TC listen : UDP 0.0.0.0:8005")
    print(f"  TM dest   : UDP {TM_DEST}:{TM_UDP_PORT}")
    print()
    print("  Ground station: connect both tabs to 127.0.0.1")
    print("=" * 60)
    print()

    ebox_state = SimState("EBOX")
    cs_state   = SimState("CUBESAT")

    # Receive TC from both nodes on a single socket (distinguished by APID)
    rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rx_sock.bind(("0.0.0.0", TC_UDP_PORT))

    # Send TM (unicast to loopback so no broadcast permission required)
    tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    rx_thread = threading.Thread(
        target=tc_receiver,
        args=(rx_sock, ebox_state, cs_state),
        daemon=True,
    )
    rx_thread.start()

    try:
        tm_sender(tx_sock, ebox_state, cs_state, cli.tm_interval)
    except KeyboardInterrupt:
        print("\n[SIM] Stopped")
    finally:
        rx_sock.close()
        tx_sock.close()


if __name__ == "__main__":
    main()
