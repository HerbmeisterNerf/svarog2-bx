#!/usr/bin/env python3
"""
Board image service: a JpegGetter thread captures a frame from every camera
into a timestamped JPEG file, and a JpegSender thread serves the latest frame
of each camera over plain TCP.  No RTSP, no daemon, no GStreamer bindings.

Frames are grabbed with a single-frame gst-launch-1.0 pipeline: the camera
delivers MJPEG natively, so the pipeline is v4l2src -> filesink with no
decode/re-encode.  Pillow (if installed) shrinks + re-encodes the frame at
send time to the target size/quality to keep radio-link payloads small;
otherwise the raw MJPEG frame is served as-is.

JpegGetter
    Loops forever; each pass grabs one frame from every camera, saves it
    VERBATIM at full capture resolution (e.g. 1280x720) to
    <save_dir>/<cam>/frame_<timestamp>.jpg, then sleeps interval s.
    A lock-guarded dict maps each camera name to the path of its latest file
    (and to the raw bytes) so the sender can serve any camera.

JpegSender
    Listens on one TCP port.  The ground station drives it request/response
    so frames never pile up in the TCP send buffer:

      GS  -> board  "PLAY_<cam>\n"           start streaming camera <cam>
      GS  -> board  "STREAM_RESIZE_WxHxQ\n"  change stream size/quality now
                                               (STREAM_RESIZE_0 = raw frames)
      GS  -> board  "ACK\n"                  frame received, send the next one
      GS  -> board  "STOP_STREAM\n"          stop streaming

      board -> GS   4-byte big-endian length + payload
                    payload is the JPEG bytes for an image frame, or UTF-8
                    text for a status/error message (a JPEG starts with 0xFFD8)

    Recording keeps the raw full-res frame; the stream is shrunk/re-encoded
    on the fly at send time to the current STREAM_RESIZE setting (default
    640x480 q40), so a live resize never touches the recorded files.

    While playing, the sender sends the latest JPEG for the requested camera
    and then blocks reading until the GS ACKs (or sends a new command) before
    sending again -- so the link runs at full speed with zero TCP queuing.

Usage (on the board):
    python3 jpeg_sender.py --port 9001 \
        --cam /dev/video0:cam1 --cam /dev/video2:cam2
"""
import argparse
import os
import socket
import struct
import subprocess
import sys
import threading
import time

try:
    import PIL  # noqa: F401
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

HDR = struct.Struct(">I")
FRAME = "/tmp/svarog_frame.jpg"

DEFAULT_SAVE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cam_recordings", "jpeg",
)

GRAB_TIMEOUT = 20.0    # per-frame gst-launch timeout
RECV_TIMEOUT = 30.0    # waiting for a client command/ACK before dropping it
RETENTION = 120.0      # delete captured files older than this many seconds


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


def grab_jpeg(device, src_w, src_h):
    """Capture one raw full-res MJPEG frame via gst-launch (num-buffers=1).

    The frame is kept raw: no decode/scale/re-encode here, so recordings are
    full-resolution and STREAM_RESIZE re-encoding happens at send time.  If the
    camera rejects the requested source size, retry with 640x480.
    """
    for (w, h) in ((src_w, src_h), (640, 480)):
        cmd = [
            "v4l2src", f"device={device}", "num-buffers=1",
            "!", f"image/jpeg,width={w},height={h}",
            "!", "filesink", f"location={FRAME}",
        ]
        try:
            r = subprocess.run(["gst-launch-1.0", "-q"] + cmd,
                               capture_output=True, timeout=GRAB_TIMEOUT)
        except subprocess.TimeoutExpired:
            print("[jpeg_sender] grab timed out", flush=True)
            return b""
        except OSError as e:
            print(f"[jpeg_sender] grab launch failed: {e}", flush=True)
            return b""
        if r.returncode == 0:
            try:
                with open(FRAME, "rb") as f:
                    return f.read()
            except OSError as e:
                print(f"[jpeg_sender] read failed: {e}", flush=True)
                return b""
        print(f"[jpeg_sender] gst-launch {w}x{h} rc={r.returncode}: "
              f"{r.stderr.decode(errors='replace')[-120:]}", flush=True)
    return b""


def _reencode_jpeg(data, width, height, quality):
    """Shrink + re-encode a raw MJPEG frame; the original on any error."""
    if not _HAS_PIL:
        return data
    try:
        import io
        from PIL import Image
    except ImportError:
        return data
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        if (width, height) != img.size:
            img = img.resize((width, height), Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality)
        out = buf.getvalue()
        return out if out else data
    except Exception as e:
        print(f"[jpeg_sender] re-encode failed ({e}), sending raw frame",
              flush=True)
        return data


class JpegGetter(threading.Thread):
    """Continuously grabs a frame from every camera into a timestamped file."""

    def __init__(self, cam_specs, save_dir, src_w, src_h, width, height,
                 quality, interval=0.01):
        super().__init__(daemon=True)
        self.cam_specs = cam_specs        # [(device, name), ...]
        self.save_dir = save_dir
        self.src_w = src_w
        self.src_h = src_h
        self.width = width
        self.height = height
        self.quality = quality
        self.interval = interval
        self.latest_files = {}            # name -> path of newest frame
        self.latest_bufs = {}             # name -> raw bytes of newest frame
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def _grab(self, device, name):
        """One raw full-res MJPEG frame for a camera via gst-launch."""
        return grab_jpeg(device, self.src_w, self.src_h)

    def stop(self):
        self._stop.set()

    def camera_names(self):
        return [name for _, name in self.cam_specs]

    def resolve(self, cam):
        """Map a request id to a real camera name (PLAY_1 -> cam1)."""
        for _, name in self.cam_specs:
            if cam == name:
                return name
        if cam.isdigit():
            for _, name in self.cam_specs:
                if name == f"cam{cam}":
                    return name
        return None

    def latest(self, name):
        """Path of the most recently written frame for a camera."""
        with self._lock:
            return self.latest_files.get(name)

    def latest_data(self, name):
        """Raw (full-res) bytes of the most recent frame for a camera."""
        with self._lock:
            return self.latest_bufs.get(name)

    def run(self):
        print(f"[jpeg_sender] image getter started "
              f"cams={self.camera_names()} save_dir={self.save_dir} "
              f"interval={self.interval}s", flush=True)
        while not self._stop.is_set():
            for device, name in self.cam_specs:
                data = self._grab(device, name)
                if not data:
                    continue
                cam_dir = os.path.join(self.save_dir, name)
                path = os.path.join(
                    cam_dir,
                    f"frame_{time.strftime('%Y%m%d_%H%M%S')}_"
                    f"{int(time.time() * 1e6)}.jpg")
                try:
                    os.makedirs(cam_dir, exist_ok=True)
                    with open(path, "wb") as f:
                        f.write(data)
                except OSError as e:
                    print(f"[jpeg_sender:{name}] save failed: {e}", flush=True)
                    continue
                with self._lock:
                    self.latest_files[name] = path
                    self.latest_bufs[name] = data
            self._stop.wait(self.interval)

    # @staticmethod
    # def _prune(cam_dir):
    #     """Drop stale capture files so the disk doesn't fill up."""
    #     try:
    #         now = time.time()
    #         for fn in os.listdir(cam_dir):
    #             p = os.path.join(cam_dir, fn)
    #             try:
    #                 if now - os.path.getmtime(p) > RETENTION:
    #                     os.remove(p)
    #             except OSError:
    #                 pass
    #     except OSError:
    #         pass


def _read_line(sock):
    """Read one newline-terminated client command; None on EOF."""
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            return None
        buf += chunk
        if len(buf) > 4096:
            break
    return buf.decode("utf-8", "replace").strip()


def _msg(payload):
    """One length-prefixed message (JPEG bytes or UTF-8 text)."""
    return HDR.pack(len(payload)) + payload


def _text(text):
    """One length-prefixed UTF-8 text message."""
    return _msg(text.encode("utf-8", "replace"))


class JpegSender(threading.Thread):
    """Serves the JpegGetter's latest frame per camera over TCP."""

    def __init__(self, getter, host, port, recv_timeout=RECV_TIMEOUT,
                 resize=(640, 480, 40), reencode=True):
        super().__init__(daemon=True)
        self.getter = getter
        self.host = host
        self.port = port
        self.recv_timeout = recv_timeout
        self.reencode = reencode
        self._resize = tuple(resize)
        self._resize_lock = threading.Lock()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(4)
        srv.settimeout(0.2)
        print(f"[jpeg_sender] listening on {self.host}:{self.port} (TCP)",
              flush=True)
        try:
            while not self._stop.is_set():
                try:
                    conn, addr = srv.accept()
                except socket.timeout:
                    continue
                threading.Thread(target=self._handle_client,
                                 args=(conn, addr), daemon=True).start()
        finally:
            srv.close()

    def _send_latest(self, send_payload, cam):
        """Send the newest frame of a camera, shrunk to the current stream
        resize setting; a text error if there is no frame yet."""
        data = self.getter.latest_data(cam)
        print(f"Sending 1 image from {cam}", flush=True)
        if data is None:
            send_payload(_text(f"ERR no frames yet for {cam}"))
            return
        if self.reencode:
            with self._resize_lock:
                w, h, q = self._resize
            data = _reencode_jpeg(data, w, h, q)
        send_payload(_msg(data))

    def _set_resize(self, line):
        """Apply a STREAM_RESIZE command; text reply on success/error.

        STREAM_RESIZE_0 / STREAM_RESIZE_RAW serves the raw full-res frame
        (re-encode disabled); STREAM_RESIZE_WxHxQ re-enables shrinking.
        """
        rest = line[len("STREAM_RESIZE"):].strip().strip("_")
        if rest.lower() in ("0", "raw"):
            self.reencode = False
            print("[jpeg_sender] stream resize -> raw passthrough",
                  flush=True)
            return "STREAM_RESIZE ok raw"
        parts = rest.split("_") if rest else []
        if len(parts) == 3:
            try:
                w, h, q = (int(p) for p in parts)
            except ValueError:
                w = h = q = None
            if (w is not None and 16 <= w <= 4096 and 16 <= h <= 4096
                    and 1 <= q <= 100):
                with self._resize_lock:
                    self._resize = (w, h, q)
                self.reencode = True
                print(f"[jpeg_sender] stream resize -> {w}x{h} q{q}",
                      flush=True)
                return f"STREAM_RESIZE ok {w}x{h} q{q}"
        return f"ERR bad STREAM_RESIZE: {line}"

    def _process_command(self, line, send_payload, addr, playing):
        """Handle one command line; return the new playing camera for the
        client (None if the stream stopped)."""
        cmd = line.upper()
        if cmd.startswith("PLAY_"):
            raw = line[len("PLAY_"):].strip().lower()
            cam = self.getter.resolve(raw)
            if cam is None:
                send_payload(_text(f"ERR unknown camera: {raw}"))
                return None
            print(f"[jpeg_sender] play {cam} for {addr}", flush=True)
            if self.getter.latest(cam) is None:
                send_payload(_text(f"ERR no frames yet for {cam}"))
                return None
            self._send_latest(send_payload, cam)
            return cam
        if cmd == "ACK":
            if playing:
                self._send_latest(send_payload, playing)
            else:
                send_payload(_text("ERR no active stream"))
            return playing
        if cmd.startswith("STREAM_RESIZE"):
            send_payload(_text(self._set_resize(cmd)))
            return playing
        if cmd == "STOP_STREAM":
            print(f"[jpeg_sender] stop stream for {addr}", flush=True)
            send_payload(_text("STOPPED"))
            return None
        send_payload(_text(f"ERR unknown command: {line}"))
        return playing

    def _handle_client(self, conn, addr):
        conn.settimeout(self.recv_timeout)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536 // 2)
        playing = None
        print(f"[jpeg_sender] client connected: {addr}", flush=True)

        def send_payload(payload):
            conn.sendall(payload)

        try:
            while True:
                try:
                    line = _read_line(conn)
                except socket.timeout:
                    print(f"[jpeg_sender] client {addr} idle timeout",
                          flush=True)
                    break
                if line is None:
                    break
                playing = self._process_command(
                    line, send_payload, addr, playing)
        except (ConnectionError, OSError) as e:
            print(f"[jpeg_sender] client {addr} gone: {e}", flush=True)
        finally:
            try:
                conn.close()
            except OSError:
                pass
            print(f"[jpeg_sender] client {addr} disconnected", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=9001)
    ap.add_argument("--save-dir", default=DEFAULT_SAVE_DIR)
    ap.add_argument("--src-width", type=int, default=1280)
    ap.add_argument("--src-height", type=int, default=720)
    ap.add_argument("--width", type=int, default=640,
                    help="default stream width (STREAM_RESIZE can change it)")
    ap.add_argument("--height", type=int, default=480,
                    help="default stream height (STREAM_RESIZE can change it)")
    ap.add_argument("--quality", type=int, default=40,
                    help="default stream JPEG quality 1-100 (STREAM_RESIZE)")
    ap.add_argument("--interval", type=float, default=0.5,
                    help="seconds between capture passes (per camera)")
    ap.add_argument("--no-reencode", action="store_true",
                    help="serve raw MJPEG frames, no shrink/re-encode")
    ap.add_argument("--cam", action="append", default=[], metavar="DEV:NAME",
                    help="camera source, e.g. /dev/video0:cam1 (repeatable)")
    args = ap.parse_args()

    if not args.cam:
        print("ERR: at least one --cam DEV:NAME is required", file=sys.stderr)
        sys.exit(2)

    cam_specs = []
    for entry in args.cam:
        dev, _, name = entry.partition(":")
        cam_specs.append((dev, name))

    _set_cpu_profile()
    if not _HAS_PIL:
        print("WARN: Pillow not installed -- STREAM_RESIZE has no effect, "
              "raw frames are served as-is", flush=True)
    getter = JpegGetter(cam_specs, args.save_dir,
                        args.src_width, args.src_height,
                        args.width, args.height, args.quality,
                        args.interval)
    sender = JpegSender(getter, args.host, args.port,
                        resize=(args.width, args.height, args.quality),
                        reencode=not args.no_reencode)
    getter.start()
    sender.start()
    print(f"[jpeg_sender] running cams={getter.camera_names()} "
          f"on {args.host}:{args.port} (TCP)", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        getter.stop()
        sender.stop()
        print("[jpeg_sender] stopped", flush=True)


if __name__ == "__main__":
    main()
