#!/usr/bin/env python3
"""Tiny single-stream MJPEG AVI writer (stdlib only).

Hands raw JPEG bytes to write() and on close() patches a valid AVI (RIFF)
container with an idx1 index, so boards and the ground station can produce
playable videos without ffmpeg.  Low frame rates (e.g. 1 fps from
jpeg_sender.py) are fine -- players honour the avih/strh rate fields.
"""
import struct


def _u32(v):
    return struct.pack("<I", v)


class MjpegAvi:
    def __init__(self, path, width, height, fps=1.0):
        self.path = path
        self.width = int(width)
        self.height = int(height)
        self.fps = float(fps) or 1.0
        self.frames = 0
        self._index = []        # (chunk offset within movi data, chunk length)
        self._closed = False
        self._f = open(path, "wb")
        self._write_header()

    # ── header ──────────────────────────────────────────────────────

    def _write_header(self):
        f = self._f
        f.write(b"RIFF" + _u32(0) + b"AVI ")
        self._hdrl_pos = f.tell()
        f.write(b"LIST" + _u32(0) + b"hdrl")

        f.write(b"avih" + _u32(56))
        avih = struct.pack(
            "<14I",
            1000000, 0, 0, 0x10, 0, 0, 1, 0,      # microsec, bytes/s, pad, flags, frames, init, streams, buf
            self.width, self.height, 0, 0, 0, 0,  # width, height, reserved x4
        )
        self._avih_frames_pos = f.tell() + 16     # dwTotalFrames is the 5th u32
        f.write(avih)

        self._strl_pos = f.tell()
        f.write(b"LIST" + _u32(0) + b"strl")

        f.write(b"strh" + _u32(56))
        strh = struct.pack(
            "<4s4sI2H8I4h",
            b"vids", b"MJPG", 0, 0, 0,            # type, handler, flags, priority, language
            0, 1, int(self.fps), 0, 0,            # init, scale, rate, start, length
            0, 0, 0,                              # buf, quality, sample
            0, 0, self.width, self.height,        # rcFrame left, top, right, bottom
        )
        self._strh_len_pos = f.tell() + 32        # dwLength is the 10th u32
        f.write(strh)

        f.write(b"strf" + _u32(40))
        strf = struct.pack(
            "<IiiHHIIiiII",
            40, self.width, self.height, 1, 24,
            int.from_bytes(b"MJPG", "little"), 0, 0, 0, 0, 0,
        )
        f.write(strf)

        self._movi_pos = f.tell()
        f.write(b"LIST" + _u32(0) + b"movi")

    # ── frames ──────────────────────────────────────────────────────

    def write(self, jpeg):
        if self._closed or not jpeg:
            return
        f = self._f
        off = f.tell() - (self._movi_pos + 8)
        f.write(b"00dc" + _u32(len(jpeg)))
        f.write(jpeg)
        if len(jpeg) % 2:
            f.write(b"\0")
        self._index.append((off, len(jpeg)))
        self.frames += 1

    def close(self):
        if self._closed:
            return
        self._closed = True
        f = self._f
        movi_data = f.tell() - (self._movi_pos + 8)
        idx = b"".join(b"00dc" + _u32(0x10) + _u32(off) + _u32(ln)
                       for off, ln in self._index)
        f.write(b"idx1" + _u32(len(idx)) + idx)
        end = f.tell()

        def _patch(pos, val):
            f.seek(pos)
            f.write(_u32(val))

        _patch(4, end - 8)                                  # RIFF size
        _patch(self._hdrl_pos + 4, self._movi_pos - (self._hdrl_pos + 8))
        _patch(self._strl_pos + 4, self._movi_pos - (self._strl_pos + 8))
        _patch(self._movi_pos + 4, movi_data)               # LIST movi size
        _patch(self._avih_frames_pos, self.frames)
        _patch(self._strh_len_pos, self.frames)
        f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
