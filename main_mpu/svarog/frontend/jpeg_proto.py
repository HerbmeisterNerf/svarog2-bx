#!/usr/bin/env python3
"""
Shared wire protocol for the board image service (jpeg_sender.py), used by
frontend/jpeg_receiver.py (standalone CLI receiver) and
frontend/subcomponents/gui_video.py (camera popup).

Server -> client messages: 4-byte big-endian length + payload, where the
payload is JPEG bytes for an image frame or UTF-8 text for a status message.
Client -> server commands are newline-terminated text lines:
PLAY_<cam>, STREAM_RESIZE_<W>_<H>_<Q>, ACK, STOP_STREAM.
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
    """Read one length-prefixed message (JPEG frame or status text).

    Raises EOFError on a clean close mid-frame and ValueError if a message is
    bigger than MAX_JPEG (protocol error / lost sync).
    """
    length = HDR.unpack(recv_exact(sock, HDR.size))[0]
    if length > MAX_JPEG:
        raise ValueError(f"frame too large: {length} bytes")
    return recv_exact(sock, length)


def is_jpeg(data):
    """True if a received payload is a JPEG image frame (vs. status text)."""
    return data[:2] == b"\xff\xd8"
