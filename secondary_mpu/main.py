"""Secondary MPU daemon — runs on each Radxa Rock Zero.

Exposes a minimal HTTP API on port 9001 so the Main R3B can:
  GET  /status  → JSON health + recording state
  POST /cmd     → JSON {"cmd": "record_start"|"record_stop"|"snapshot"}

Camera capture uses v4l2-ctl / GStreamer via subprocess.
"""

import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 9001
CAMERA_DEVICE = "/dev/video0"
SNAPSHOT_PATH = "/tmp/snapshot.jpg"

_recording_proc = None
_recording_lock = threading.Lock()


def disk_free_gb():
    total, used, free = shutil.disk_usage("/")
    return round(free / (1024 ** 3), 2)


def start_recording():
    global _recording_proc
    with _recording_lock:
        if _recording_proc and _recording_proc.poll() is None:
            return  # already recording
        _recording_proc = subprocess.Popen([
            "gst-launch-1.0",
            "v4l2src", f"device={CAMERA_DEVICE}",
            "!", "video/x-raw,width=1280,height=720,framerate=30/1",
            "!", "jpegenc",
            "!", "avimux",
            "!", "filesink", "location=/tmp/recording.avi",
        ])


def stop_recording():
    global _recording_proc
    with _recording_lock:
        if _recording_proc and _recording_proc.poll() is None:
            _recording_proc.terminate()
            _recording_proc = None


def take_snapshot():
    subprocess.run([
        "v4l2-ctl",
        f"--device={CAMERA_DEVICE}",
        "--stream-mmap",
        "--stream-count=1",
        f"--stream-to={SNAPSHOT_PATH}",
    ], timeout=5)


def is_recording():
    with _recording_lock:
        return _recording_proc is not None and _recording_proc.poll() is None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress per-request stdout noise

    def do_GET(self):
        if self.path == "/status":
            payload = {
                "alive": True,
                "recording": is_recording(),
                "disk_free_gb": disk_free_gb(),
            }
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/cmd":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                cmd = data.get("cmd", "")
                if cmd == "record_start":
                    start_recording()
                elif cmd == "record_stop":
                    stop_recording()
                elif cmd == "snapshot":
                    threading.Thread(target=take_snapshot, daemon=True).start()
                self.send_response(200)
            except Exception as e:
                print(f"cmd error: {e}")
                self.send_response(400)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Secondary MPU daemon listening on :{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        stop_recording()
