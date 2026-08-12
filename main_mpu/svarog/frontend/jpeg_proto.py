#!/usr/bin/env python3
"""
Shared low-bandwidth JPEG-over-TCP wire protocol, used by both
frontend/jpeg_receiver.py (standalone CLI receiver) and
frontend/subcomponents/gui_video.py (camera popup).

Wire format: 4-byte big-endian length + JPEG bytes.
"""
import struct

HDR = struct.Struct(">I")
MAX_JPEG = 4 * 1024 * 1024


def recv_exact(sock, n):
    """Read exactly n bytes, raising EOFError if the peer closes first."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError("connection closed")
        buf += chunk
    return buf


def read_frame(sock):
    """Read one length-prefixed JPEG frame.

    Raises EOFError on a clean close mid-frame and ValueError if a frame is
    bigger than MAX_JPEG (protocol error / lost sync).
    """
    length = HDR.unpack(recv_exact(sock, HDR.size))[0]
    if length > MAX_JPEG:
        raise ValueError(f"frame too large: {length} bytes")
    return recv_exact(sock, length)
