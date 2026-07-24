"""Loss-tolerant chunked-JPEG snapshot framing (shared flight <-> ground).

The camera path must survive the lossy RF hop, so it is pure best-effort UDP
with no ACKs (same philosophy as the TM broadcast). The ground station requests
a frame with a ``CMD_CAM_SNAPSHOT`` telecommand; the flight computer grabs one
JPEG from the camera and blasts it back as a sequence of self-describing chunks.

Each chunk datagram:
    MAGIC (5 bytes)  b"SVIMG"
    frame_id     uint16   increments per snapshot — lets the ground drop a
                          half-received older frame the moment a newer one starts
    chunk_idx    uint16   0-based index of this chunk within the frame
    total_chunks uint16   number of chunks the whole JPEG was split into
    payload      bytes    slice of the JPEG

A frame is only displayed once every chunk 0..total_chunks-1 has arrived. A lost
chunk simply means that frame never completes — the reassembler discards it when
the next frame starts (or on timeout) and the ground asks again. No stalls.
"""

import struct

IMG_UDP_PORT = 8007          # ground station binds here to receive image chunks
IMG_MAGIC = b"SVIMG"
_HEADER = ">HHH"             # frame_id, chunk_idx, total_chunks
_HEADER_LEN = len(IMG_MAGIC) + struct.calcsize(_HEADER)   # 5 + 6 = 11
# Keep each datagram comfortably under a typical 1500-byte MTU.
IMG_CHUNK_PAYLOAD = 1400


def pack_chunks(frame_id, jpeg_bytes, chunk_payload=IMG_CHUNK_PAYLOAD):
    """Split a JPEG into a list of ready-to-send chunk datagrams."""
    frame_id &= 0xFFFF
    total = max(1, (len(jpeg_bytes) + chunk_payload - 1) // chunk_payload)
    datagrams = []
    for idx in range(total):
        payload = jpeg_bytes[idx * chunk_payload:(idx + 1) * chunk_payload]
        header = IMG_MAGIC + struct.pack(_HEADER, frame_id, idx, total)
        datagrams.append(header + payload)
    return datagrams


def parse_chunk(datagram):
    """Return (frame_id, chunk_idx, total_chunks, payload) or None if not ours."""
    if len(datagram) < _HEADER_LEN or datagram[:len(IMG_MAGIC)] != IMG_MAGIC:
        return None
    off = len(IMG_MAGIC)
    frame_id, chunk_idx, total_chunks = struct.unpack(
        _HEADER, datagram[off:_HEADER_LEN])
    return frame_id, chunk_idx, total_chunks, datagram[_HEADER_LEN:]


class ImageReassembler:
    """Collects chunks for the newest frame; yields the JPEG once complete.

    Single-frame-at-a-time: a chunk from a newer ``frame_id`` abandons any
    older partially-received frame (that older frame lost a chunk to the link).
    """

    def __init__(self):
        self.frame_id = None
        self.total = 0
        self.chunks = {}

    def add(self, datagram):
        """Feed one datagram. Returns the assembled JPEG bytes when the current
        frame is complete, else None."""
        parsed = parse_chunk(datagram)
        if parsed is None:
            return None
        frame_id, chunk_idx, total_chunks, payload = parsed

        if frame_id != self.frame_id:
            # New frame — start fresh, discarding any incomplete previous one.
            self.frame_id = frame_id
            self.total = total_chunks
            self.chunks = {}

        self.chunks[chunk_idx] = payload

        if len(self.chunks) >= self.total:
            data = b"".join(self.chunks[i] for i in range(self.total))
            self.reset()
            return data
        return None

    def reset(self):
        self.frame_id = None
        self.total = 0
        self.chunks = {}
