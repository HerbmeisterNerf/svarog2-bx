"""CCSDS Space Packet Protocol (CCSDS 133.0-B-2) — minimal implementation.

Primary Header (6 bytes, big-endian):
  [0-1]  Word 0: PVN(3) | Type(1) | SHF(1) | APID(11)
  [2-3]  Word 1: SeqFlags(2) | SeqCount(14)
  [4-5]  Word 2: DataLength(16)  — length of Data Field minus 1

Data Field  = user data bytes (variable)
Packet ends with CRC-16-CCITT covering the entire packet except the final 2 bytes.

Transport:
  TC (telecommands)  ground → flight on UDP port 8005
  TM (telemetry)     flight → ground broadcast on UDP port 8006
"""

from __future__ import annotations  # PEP 604 (X | None) hints on Python 3.9 flight computer

import struct

_PVN = 0b000             # Packet Version Number, always 0
_SEQ_STANDALONE = 0b11   # Sequence Flags: standalone unsegmented packet

PKT_TYPE_TM = 0   # Telemetry
PKT_TYPE_TC = 1   # Telecommand

# APID assignments
APID_EBOX_TM = 0x001
APID_CS_TM   = 0x002
APID_EBOX_TC = 0x041
APID_CS_TC   = 0x042

# UDP ports
TC_UDP_PORT = 8005   # flight computer listens for TC
TM_UDP_PORT = 8006   # ground station listens for TM

# TM secondary header: timestamp(4) + last_tc_seq(2) + flags(1) + pad(1) = 8 bytes
_TM_SH_FMT = ">IHBx"
TM_SECONDARY_HEADER_LEN = 8


def crc16_ccitt(data: bytes) -> int:
    """CRC-16-CCITT: poly 0x1021, init 0xFFFF, no reflection, no final XOR."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
        crc &= 0xFFFF
    return crc


def build_packet(apid: int, pkt_type: int, seq_count: int, data_field: bytes) -> bytes:
    """Serialise one Space Packet.  CRC is appended automatically.

    data_field: everything after the 6-byte primary header, before the CRC.
    """
    word0 = (_PVN << 13) | (pkt_type << 12) | (apid & 0x7FF)
    word1 = (_SEQ_STANDALONE << 14) | (seq_count & 0x3FFF)
    word2 = len(data_field) + 2 - 1   # DataLength = data_field + CRC - 1
    header = struct.pack(">HHH", word0, word1, word2)
    body = header + data_field
    return body + struct.pack(">H", crc16_ccitt(body))


def parse_packet(raw: bytes) -> dict | None:
    """Decode a Space Packet.

    Returns None if the datagram is too short, truncated, or fails the CRC check.
    Otherwise returns:
      apid, pkt_type, seq_count, data_field (bytes, excluding CRC)
    """
    if len(raw) < 8:   # 6-byte header + at least 1 data byte + 2-byte CRC
        return None
    word0, word1, word2 = struct.unpack(">HHH", raw[:6])
    apid      = word0 & 0x7FF
    pkt_type  = (word0 >> 12) & 0x1
    seq_count = word1 & 0x3FFF
    pkt_len   = 6 + word2 + 1     # 6-byte header + (DataLength+1) bytes of data field
    if len(raw) < pkt_len:
        return None
    body     = raw[:pkt_len - 2]
    recv_crc = struct.unpack(">H", raw[pkt_len - 2:pkt_len])[0]
    if crc16_ccitt(body) != recv_crc:
        return None
    return {
        "apid":       apid,
        "pkt_type":   pkt_type,
        "seq_count":  seq_count,
        "data_field": raw[6:pkt_len - 2],
    }


def build_tm_data_field(timestamp: int, last_tc_seq: int, csv_payload: str) -> bytes:
    """Pack the TM secondary header (8 bytes) followed by the CSV telemetry string."""
    hdr = struct.pack(_TM_SH_FMT, timestamp & 0xFFFFFFFF, last_tc_seq & 0xFFFF, 0)
    return hdr + csv_payload.encode("utf-8")


def parse_tm_data_field(data_field: bytes) -> tuple | None:
    """Unpack TM data field.

    Returns (timestamp, last_tc_seq, csv_str) or None if too short.
    """
    if len(data_field) < TM_SECONDARY_HEADER_LEN:
        return None
    timestamp, last_tc_seq, _ = struct.unpack_from(_TM_SH_FMT, data_field)
    csv_str = data_field[TM_SECONDARY_HEADER_LEN:].decode("utf-8", errors="replace")
    return timestamp, last_tc_seq, csv_str
