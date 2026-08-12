#!/usr/bin/env python3
"""
Dead-simple camera sender: grab one JPEG from a V4L2 camera every second
and push it over plain TCP.  No RTSP, no daemon, no GStreamer bindings
-- it only shells out to gst-launch-1.0 to read + shrink a single camera
frame into a JPEG.

Wire format: 4-byte big-endian length + JPEG bytes.
Receiver: frontend/jpeg_receiver.py / frontend/subcomponents/gui_video.py

Radxa-side recording: when the flag file exists (toggled by the board cmd
server via "JPEGREC ON/OFF", see commands.py), every frame is also appended
to an MJPEG AVI in <board>/cam_recordings/jpeg/<tag>/.

Usage (on the board):
    python3 jpeg_sender.py --device /dev/video0 --port 9000 --tag cam1
"""
import argparse
import os
import socket
import struct
import subprocess
import time

import mjpeg_avi

HDR = struct.Struct(">I")
FRAME = "/tmp/svarog_frame.jpg"

REC_FLAG = "/tmp/svarog_jpeg_rec"
REC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cam_recordings", "jpeg",
)


def _set_cpu_profile():
    # 1. Lower process priority so OpenSSH (sshd) gets CPU preference.
    try:
        os.nice(19)
    except AttributeError:
        pass
    # 2. Pin process to Cores 1, 2, 3 (leaves Core 0 for OS/SSH).
    try:
        os.sched_setaffinity(0, {1, 2, 3})
    except (AttributeError, OSError):
        pass


def grab_jpeg(device, src_w, src_h, src_fps, width, height, quality):
    """Capture one MJPEG frame and re-encode it as a JPEG file."""
    cmd = [
        "v4l2src", f"device={device}", "num-buffers=1",
        "!", f"image/jpeg,width={src_w},height={src_h},framerate={src_fps}/1",
        "!", "jpegdec", "!", "videoscale",
        "!", f"video/x-raw,width={width},height={height}",
        "!", "jpegenc", f"quality={quality}",
        "!", "filesink", f"location={FRAME}",
    ]
    try:
        r = subprocess.run(["gst-launch-1.0", "-q"] + cmd,
                           capture_output=True, timeout=20)
    except subprocess.TimeoutExpired:
        print("[jpeg_sender] grab timed out", flush=True)
        return b""
    except OSError as e:
        print(f"[jpeg_sender] grab launch failed: {e}", flush=True)
        return b""
    if r.returncode != 0:
        print(f"[jpeg_sender] gst-launch rc={r.returncode}: "
              f"{r.stderr.decode(errors='replace')[-200:]}", flush=True)
        return b""
    try:
        with open(FRAME, "rb") as f:
            return f.read()
    except OSError as e:
        print(f"[jpeg_sender] read failed: {e}", flush=True)
        return b""


def _sync_recorder(rec_writer, rec_path, width, height, fps, rec_dir, tag):
    """Open/close the AVI recorder to match the flag file; return new state."""
    want = os.path.exists(REC_FLAG)
    if want and rec_writer is None:
        os.makedirs(rec_dir, exist_ok=True)
        path = os.path.join(rec_dir,
                            f"rec_{time.strftime('%Y%m%d_%H%M%S')}.avi")
        rec_writer = mjpeg_avi.MjpegAvi(path, width, height, fps=fps)
        rec_path = path
        print(f"[jpeg_sender:{tag}] radxa recording -> {path}", flush=True)
    elif not want and rec_writer is not None:
        try:
            rec_writer.close()
        finally:
            rec_writer = None
        print(f"[jpeg_sender:{tag}] radxa recording stopped: {rec_path}",
              flush=True)
        rec_path = None
    return rec_writer, rec_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--device", default="/dev/video0")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--src-width", type=int, default=1280)
    ap.add_argument("--src-height", type=int, default=720)
    ap.add_argument("--src-fps", type=int, default=120,
                    help="capture framerate the camera can negotiate (e.g. 120 or 30)")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--quality", type=int, default=40)
    ap.add_argument("--fps", type=float, default=1.0)
    ap.add_argument("--tag", default="cam",
                    help="camera id used for recording folder/log labels")
    args = ap.parse_args()

    _set_cpu_profile()
    rec_dir = os.path.join(REC_DIR, args.tag)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen(1)
    srv.settimeout(0.2)
    print(f"[jpeg_sender:{args.tag}] listening on {args.host}:{args.port} "
          f"({args.width}x{args.height}@{args.fps}fps quality={args.quality})",
          flush=True)

    current = None   # the client we are streaming to (newest wins)
    rec_writer = None
    rec_path = None
    try:
        while True:
            # pick up any new client; if one connects, drop the previous one
            try:
                newconn, addr = srv.accept()
            except socket.timeout:
                newconn = None
            except KeyboardInterrupt:
                break
            if newconn is not None:
                if current is not None:
                    print(f"[jpeg_sender:{args.tag}] new client connected, "
                          "dropping previous", flush=True)
                    try:
                        current.close()
                    except OSError:
                        pass
                current = newconn
                current.settimeout(10.0)
                print(f"[jpeg_sender:{args.tag}] client connected: {addr}",
                      flush=True)

            rec_writer, rec_path = _sync_recorder(
                rec_writer, rec_path, args.width, args.height, args.fps,
                rec_dir, args.tag)

            if current is None and rec_writer is None:
                time.sleep(0.2)
                continue

            t0 = time.monotonic()
            data = grab_jpeg(args.device, args.src_width,
                             args.src_height, args.src_fps,
                             args.width, args.height, args.quality)
            if data:
                if current is not None:
                    try:
                        current.sendall(HDR.pack(len(data)) + data)
                    except (socket.timeout, ConnectionError, OSError):
                        print(f"[jpeg_sender:{args.tag}] client gone",
                              flush=True)
                        try:
                            current.close()
                        except OSError:
                            pass
                        current = None
                if rec_writer is not None:
                    rec_writer.write(data)
            time.sleep(max(0.0, (1.0 / args.fps) - (time.monotonic() - t0)))
    except KeyboardInterrupt:
        pass
    finally:
        if current is not None:
            try:
                current.close()
            except OSError:
                pass
        if rec_writer is not None:
            try:
                rec_writer.close()
            except Exception:
                pass
        srv.close()
        print(f"[jpeg_sender:{args.tag}] stopped", flush=True)


if __name__ == "__main__":
    main()
