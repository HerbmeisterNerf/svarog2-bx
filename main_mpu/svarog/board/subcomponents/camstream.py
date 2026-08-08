#!/usr/bin/env python3
"""
Camera streaming + recording service for the boards (EBOX / CUBESAT).

Runs inside the board main.py process (Gst.init first, static RTSP factories
with set_shared(True) -- the pattern verified on hardware; no appsrc).

EBOX    : cam1..cam4  from /dev/video{0,2,4,6} on RTSP ports 1234..1237
CUBESAT : cubesat     from /dev/video0          on RTSP port 1234

Recording pulls the board's own shared RTSP stream over loopback and muxes
to AVI (start_video_record pattern), so remote clients and the local recorder
run concurrently.

Commands (over the board cmd server, see commands.py):
  CAM STATUS
  CAM START  [all|<id>]
  CAM STOP   [all|<id>]
  CAM REC    [all|<id>]
  CAM STOPREC [all|<id>]
"""
import os
import threading
import time

try:
    import gi
    gi.require_version("Gst", "1.0")
    gi.require_version("GstRtspServer", "1.0")
    from gi.repository import GLib, Gst, GstRtspServer
    HAVE_GST = True
except Exception:
    HAVE_GST = False

if HAVE_GST:
    Gst.init(None)

from BOARD_SELECT import is_ebox

BASE_PORT = 1234
STREAM_NAME = "cam"

_RECORD_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cam_recordings"
)

# Low-bandwidth transcode chain proven on the ground link (640x360 @ 10fps JPEG q40).
# Leaky 1-buffer queue: only the newest captured frame is transcoded, old frames
# buffered during link stalls are dropped instead of delivered late.
_LEAKY_QUEUE = "queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream"
_LOWBW = (
    f"jpegparse ! {_LEAKY_QUEUE} ! jpegdec ! videoconvert ! videoscale ! videorate "
    "! video/x-raw,format=I420,width=640,height=360,framerate=10/1 "
    "! jpegenc quality=40"
)


def _build_cams():
    cams = {}
    if is_ebox:
        for i in range(4):
            dev = f"/dev/video{i * 2}"
            if not os.path.exists(dev):
                continue
            cams[f"cam{i + 1}"] = {
                "port": BASE_PORT + i,
                "launch": (
                    f"( v4l2src device={dev} ! image/jpeg,width=1280,height=720 "
                    f"! {_LOWBW} ! rtpjpegpay name=pay0 pt=26 )"
                ),
            }
    else:
        cams["cubesat"] = {
            "port": BASE_PORT,
            "launch": (
                "( v4l2src device=/dev/video0 ! image/jpeg,width=1280,height=720 "
                "! queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 "
                "leaky=downstream ! jpegparse ! rtpjpegpay name=pay0 pt=26 )"
            ),
        }
    return cams


class CameraStreamManager:
    def __init__(self):
        self.cams = _build_cams()
        self._lock = threading.Lock()
        self._servers = {}
        self._recordings = {}
        self._loop = None
        self._loop_lock = threading.Lock()
        os.makedirs(_RECORD_ROOT, exist_ok=True)

    # ── GLib main loop (drives the RTSP servers) ────────────────────

    def _ensure_loop(self):
        with self._loop_lock:
            if self._loop is None:
                self._loop = GLib.MainLoop()
                threading.Thread(target=self._loop.run, daemon=True).start()

    # ── stream control ──────────────────────────────────────────────

    def start(self, cam_id):
        if not HAVE_GST:
            return "ERR: gstreamer unavailable"
        cam = self.cams.get(cam_id)
        if not cam:
            return f"ERR: unknown camera: {cam_id}"
        with self._lock:
            if cam_id in self._servers:
                return f"OK {cam_id} already running"
            self._ensure_loop()
            try:
                server = GstRtspServer.RTSPServer.new()
                server.props.service = str(cam["port"])
                factory = GstRtspServer.RTSPMediaFactory.new()
                factory.set_launch(cam["launch"])
                factory.set_shared(True)
                server.get_mount_points().add_factory(f"/{STREAM_NAME}", factory)
                sid = server.attach(None)
            except Exception as e:
                return f"ERR: {e}"
            self._servers[cam_id] = (server, factory, sid)
            return f"OK {cam_id} rtsp://0.0.0.0:{cam['port']}/{STREAM_NAME}"

    def start_all(self):
        out = []
        for cam_id in list(self.cams):
            out.append(self.start(cam_id))
        return "; ".join(out)

    def stop(self, cam_id):
        with self._lock:
            ent = self._servers.pop(cam_id, None)
        if not ent:
            return f"ERR: {cam_id} not running"
        _, _, sid = ent
        try:
            GLib.source_remove(sid)
        except Exception:
            pass
        return f"OK {cam_id} stopped"

    def stop_all(self):
        out = []
        for cam_id in list(self._servers):
            out.append(self.stop(cam_id))
        return "; ".join(out)

    # ── recording (loopback pull of own shared RTSP -> AVI) ─────────

    def start_record(self, cam_id):
        if not HAVE_GST:
            return "ERR: gstreamer unavailable"
        cam = self.cams.get(cam_id)
        if not cam:
            return f"ERR: unknown camera: {cam_id}"
        with self._lock:
            if cam_id in self._recordings:
                return f"OK {cam_id} already recording"
            if cam_id not in self._servers:
                return f"ERR: {cam_id} stream not running (CAM START first)"
            folder = os.path.join(_RECORD_ROOT, cam_id)
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder,
                                f"{cam_id}_{time.strftime('%Y%m%d_%H%M%S')}.avi")
            url = f"rtsp://127.0.0.1:{cam['port']}/{STREAM_NAME}"
            pstr = (
                f"rtspsrc location={url} is-live=true ! "
                "rtpjpegdepay ! jpegparse ! avimux ! filesink "
                f"name=sink location={path}"
            )
            try:
                p = Gst.parse_launch(pstr)
                p.set_state(Gst.State.PLAYING)
            except Exception as e:
                return f"ERR: {e}"
            self._recordings[cam_id] = p
            return f"OK {cam_id} recording -> {path}"

    def start_record_all(self):
        out = []
        for cam_id in list(self.cams):
            out.append(self.start_record(cam_id))
        return "; ".join(out)

    def stop_record(self, cam_id):
        with self._lock:
            p = self._recordings.pop(cam_id, None)
        if not p:
            return f"ERR: {cam_id} not recording"
        try:
            p.set_state(Gst.State.NULL)
        except Exception:
            pass
        return f"OK {cam_id} recording stopped"

    def stop_record_all(self):
        out = []
        for cam_id in list(self._recordings):
            out.append(self.stop_record(cam_id))
        return "; ".join(out)

    # ── status (single line for the GUI) ────────────────────────────

    def status(self):
        with self._lock:
            parts = []
            for cam_id, cam in self.cams.items():
                run = 1 if cam_id in self._servers else 0
                rec = 1 if cam_id in self._recordings else 0
                parts.append(f"{cam_id}={run},{rec}")
            return ";".join(parts) if parts else "none"


cam_manager = CameraStreamManager()
