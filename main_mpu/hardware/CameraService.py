"""Flight-side camera snapshot service.

On a ``CMD_CAM_SNAPSHOT`` telecommand the flight computer grabs one JPEG from a
local V4L2 camera (the Arducam on ``/dev/video0``) and blasts it back to the
ground station as loss-tolerant UDP chunks (see ``shared/image_snapshot.py``).

This replaces the RTSP path (``main_camera.py``) for the ground link: RTSP runs
over TCP and stalls badly on the lossy RF hop, whereas request/response JPEG
snapshots degrade gracefully — a dropped chunk just costs one frame.

Capture uses gstreamer (``gst-launch-1.0``) with a single-buffer pipeline, the
same element chain already proven in ``main_camera.py``. ffmpeg is tried as a
fallback if gstreamer isn't present.
"""

import os
import socket
import subprocess
import sys

_shared = os.path.join(os.path.dirname(__file__), '..', '..', 'shared')
if _shared not in sys.path:
    sys.path.insert(0, _shared)

from image_snapshot import pack_chunks, IMG_UDP_PORT


class CameraService:
    """Captures a JPEG from a local camera and sends it back over UDP chunks."""

    def __init__(self, device="/dev/video0", width=1280, height=800,
                 tmp_path="/tmp/svarog_snapshot.jpg"):
        self.device = device
        self.width = width
        self.height = height
        self.tmp_path = tmp_path
        self._frame_id = 0
        # A dedicated UDP socket for outbound image chunks.
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # ------------------------------------------------------------- capture
    def capture_jpeg(self):
        """Grab one JPEG frame; return the bytes, or None on failure."""
        # Clear any previous frame so a failed grab can never serve a stale image.
        try:
            os.remove(self.tmp_path)
        except OSError:
            pass
        if self._grab_gstreamer() or self._grab_ffmpeg():
            try:
                with open(self.tmp_path, "rb") as f:
                    data = f.read()
                return data if data else None
            except OSError:
                return None
        return None

    def _grab_gstreamer(self):
        return self._run([
            "gst-launch-1.0", "-q",
            "v4l2src", "device=%s" % self.device, "num-buffers=1", "!",
            "image/jpeg,width=%d,height=%d" % (self.width, self.height), "!",
            "jpegparse", "!",
            "filesink", "location=%s" % self.tmp_path,
        ])

    def _grab_ffmpeg(self):
        return self._run([
            "ffmpeg", "-y", "-f", "v4l2", "-input_format", "mjpeg",
            "-video_size", "%dx%d" % (self.width, self.height),
            "-i", self.device, "-frames:v", "1", self.tmp_path,
        ])

    @staticmethod
    def _run(argv):
        """Run a capture command as a direct child (never via a shell).

        shell=True would leave the real capture process orphaned when the
        timeout fires — subprocess only kills the shell, and the surviving
        gst/ffmpeg keeps /dev/video0 open, breaking every later snapshot.
        Passing argv directly means the timeout kills the capture process itself.
        """
        try:
            r = subprocess.run(argv, timeout=10,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return r.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    # ---------------------------------------------------------------- send
    def send_snapshot(self, dest_ip, dest_port=IMG_UDP_PORT):
        """Capture a frame and send it chunked to ``dest_ip``.

        Returns the number of chunks sent, or 0 if capture failed.
        """
        jpeg = self.capture_jpeg()
        if not jpeg:
            print(f"[camera] capture failed on {self.device}")
            return 0
        self._frame_id = (self._frame_id + 1) & 0xFFFF
        datagrams = pack_chunks(self._frame_id, jpeg)
        for dg in datagrams:
            try:
                self._sock.sendto(dg, (dest_ip, dest_port))
            except OSError as e:
                print(f"[camera] send error: {e}")
                break
        print(f"[camera] snapshot frame {self._frame_id}: "
              f"{len(jpeg)} bytes in {len(datagrams)} chunks -> {dest_ip}")
        return len(datagrams)

    def close(self):
        try:
            self._sock.close()
        except OSError:
            pass
