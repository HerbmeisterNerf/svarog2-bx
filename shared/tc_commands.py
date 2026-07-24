"""Telecommand IDs and argument packing helpers.

TC data field layout (following 6-byte primary header):
  Byte 0:   cmd_id (uint8)
  Bytes 1+: cmd_args (command-specific, variable length)

The 14-bit sequence count in the primary header is used as the TC sequence
number.  The flight computer echoes it back in every TM secondary header
as `last_tc_seq`, giving the ground station application-layer delivery
confirmation (a minimal CLCW).
"""

from __future__ import annotations  # PEP 604 (X | None) hints on Python 3.9 flight computer

import struct

# Command identifiers (1 byte each)
CMD_HEATER_TOGGLE = 0x01   # args: [heater_num: uint8]   1-indexed
CMD_BW_PULSE      = 0x02   # args: [bw_num: uint8]        1-indexed, 3 s pulse
CMD_MOT_ENABLE    = 0x03   # args: none     EBOX spinning motor enable
CMD_FW_ENABLE     = 0x04   # args: none     CubeSat flywheel enable
CMD_FW_SPEED      = 0x05   # args: [speed: uint16 BE]     0-900 RPM
CMD_DEPLOY_ARM    = 0x06   # args: none
CMD_DEPLOY_FIRE   = 0x07   # args: none     only executes if flight-side armed
CMD_MOT_DISABLE   = 0x0A   # args: none     EBOX spinning motor disable
CMD_CAM_RECORD    = 0x08   # args: [rz_index: uint8, action: uint8]  1=start, 0=stop
CMD_CAM_SNAPSHOT  = 0x09   # args: [rz_index: uint8]

# Fine FOC motor control (relayed by the flight computer to the ESC over USB).
# These drive the SimpleFOC B-G431B-ESC1 in place of the coarse enable/disable.
CMD_FOC_MODE      = 0x0B   # args: [mode: uint8]           see FOC_MODE_* below
CMD_FOC_TARGET    = 0x0C   # args: [target: float32 BE]    rad/s (vel), V (open), rad (pos)
CMD_FOC_LIMITS    = 0x0D   # args: [vlim: float32 BE, clim: float32 BE]
CMD_FOC_ALIGN     = 0x0E   # args: none                    run initFOC() on demand ('I')
CMD_FOC_ZERO      = 0x0F   # args: none                    tare shaft position ('Z')

# FOC control modes (arg for CMD_FOC_MODE)
FOC_MODE_OPEN     = 0       # open-loop velocity  (O1)
FOC_MODE_VELOCITY = 1       # closed-loop velocity (O0 + MC1)
FOC_MODE_POSITION = 2       # closed-loop angle    (O0 + MC2)


def pack_tc(cmd_id: int, *arg_bufs: bytes) -> bytes:
    """Combine cmd_id byte with zero or more argument buffers into a TC data field."""
    return bytes([cmd_id & 0xFF]) + b"".join(arg_bufs)


# ---------------------------------------------------------------- convenience packers

def tc_heater_toggle(heater_num: int) -> bytes:
    return pack_tc(CMD_HEATER_TOGGLE, bytes([heater_num & 0xFF]))

def tc_bw_pulse(bw_num: int) -> bytes:
    return pack_tc(CMD_BW_PULSE, bytes([bw_num & 0xFF]))

def tc_mot_enable() -> bytes:
    return pack_tc(CMD_MOT_ENABLE)

def tc_mot_disable() -> bytes:
    return pack_tc(CMD_MOT_DISABLE)

def tc_fw_enable() -> bytes:
    return pack_tc(CMD_FW_ENABLE)

def tc_fw_speed(rpm: int) -> bytes:
    return pack_tc(CMD_FW_SPEED, struct.pack(">H", rpm & 0xFFFF))

def tc_deploy_arm() -> bytes:
    return pack_tc(CMD_DEPLOY_ARM)

def tc_deploy_fire() -> bytes:
    return pack_tc(CMD_DEPLOY_FIRE)

def tc_cam_record(rz_index: int, action: int) -> bytes:
    return pack_tc(CMD_CAM_RECORD, bytes([rz_index & 0xFF, action & 0xFF]))

def tc_cam_snapshot(rz_index: int) -> bytes:
    return pack_tc(CMD_CAM_SNAPSHOT, bytes([rz_index & 0xFF]))

# ---- fine FOC motor control ----

def tc_foc_mode(mode: int) -> bytes:
    return pack_tc(CMD_FOC_MODE, bytes([mode & 0xFF]))

def tc_foc_target(target: float) -> bytes:
    return pack_tc(CMD_FOC_TARGET, struct.pack(">f", float(target)))

def tc_foc_limits(vlim: float, clim: float) -> bytes:
    return pack_tc(CMD_FOC_LIMITS, struct.pack(">ff", float(vlim), float(clim)))

def tc_foc_align() -> bytes:
    return pack_tc(CMD_FOC_ALIGN)

def tc_foc_zero() -> bytes:
    return pack_tc(CMD_FOC_ZERO)


# ---------------------------------------------------------------- unpack (flight side)

def unpack_tc(data_field: bytes) -> tuple | None:
    """Extract (cmd_id, args_bytes) from a TC data field, or None if empty."""
    if not data_field:
        return None
    return data_field[0], data_field[1:]
