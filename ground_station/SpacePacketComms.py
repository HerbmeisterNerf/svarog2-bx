"""Ground station packet helpers: build TC space packets, parse received TM packets.

This is the single import point for the GUI — it re-exports tc_commands functions
so callers only need one import.

Usage:
    from SpacePacketComms import SpacePacketComms, tc_heater_toggle, tc_fw_speed
    SpacePacketComms.send_ebox_tc(tc_heater_toggle(1))
    result = SpacePacketComms.parse_tm(raw_bytes)  # called by UDPTelemReader
"""

import os
import sys

_shared = os.path.join(os.path.dirname(__file__), '..', 'shared')
sys.path.insert(0, _shared)

from space_packet import (
    build_packet, parse_packet, parse_tm_data_field,
    PKT_TYPE_TC, PKT_TYPE_TM,
    APID_EBOX_TC, APID_CS_TC,
    TC_UDP_PORT,
)

# Re-export tc_commands so callers only need one import
from tc_commands import (  # noqa: F401
    tc_heater_toggle, tc_bw_pulse,
    tc_mot_enable, tc_mot_disable,
    tc_fw_enable, tc_fw_speed,
    tc_deploy_arm, tc_deploy_fire,
    tc_cam_record, tc_cam_snapshot,
    tc_foc_mode, tc_foc_target, tc_foc_limits, tc_foc_align, tc_foc_zero,
    FOC_MODE_OPEN, FOC_MODE_VELOCITY, FOC_MODE_POSITION,
)

from CommonData import CommonData


class SpacePacketComms:
    """Static helpers for sending TC and parsing TM on the ground station."""

    @staticmethod
    def send_tc(apid: int, tc_data_field: bytes) -> int:
        """Build and send one TC space packet over UDP.

        Returns the 14-bit sequence count used, or -1 on failure.
        """
        sock = CommonData.udp_tc_socket
        if sock is None:
            print("SpacePacketComms: udp_tc_socket is None — create it first")
            return -1

        if apid == APID_EBOX_TC:
            ip = CommonData.server_name
            seq = CommonData.ebox_tc_seq
            CommonData.ebox_tc_seq = (seq + 1) & 0x3FFF
        else:
            ip = CommonData.server_name_cs
            seq = CommonData.cs_tc_seq
            CommonData.cs_tc_seq = (seq + 1) & 0x3FFF

        if not ip:
            print(f"SpacePacketComms: no target IP configured for APID 0x{apid:03X}")
            return -1

        packet = build_packet(apid, PKT_TYPE_TC, seq, tc_data_field)
        try:
            sock.sendto(packet, (ip, TC_UDP_PORT))
        except Exception as e:
            print(f"SpacePacketComms: send error: {e}")
        return seq

    @staticmethod
    def send_ebox_tc(tc_data_field: bytes) -> int:
        return SpacePacketComms.send_tc(APID_EBOX_TC, tc_data_field)

    @staticmethod
    def send_cs_tc(tc_data_field: bytes) -> int:
        return SpacePacketComms.send_tc(APID_CS_TC, tc_data_field)

    @staticmethod
    def parse_tm(raw: bytes) -> dict | None:
        """Parse a received TM space packet.

        Returns dict{apid, seq_count, timestamp, last_tc_seq, csv_payload}
        or None if the packet is malformed or fails CRC.
        """
        pkt = parse_packet(raw)
        if pkt is None or pkt["pkt_type"] != PKT_TYPE_TM:
            return None
        result = parse_tm_data_field(pkt["data_field"])
        if result is None:
            return None
        timestamp, last_tc_seq, csv_payload = result
        return {
            "apid":        pkt["apid"],
            "seq_count":   pkt["seq_count"],
            "timestamp":   timestamp,
            "last_tc_seq": last_tc_seq,
            "csv_payload": csv_payload,
        }
