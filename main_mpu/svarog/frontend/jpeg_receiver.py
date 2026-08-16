#!/usr/bin/env python3
"""
Low-bandwidth camera receiver: connects to the board image service
(board/subcomponents/jpeg_sender.py) and shows the JPEG stream in a small Tk
window.  Optionally saves frames to disk with --save-dir.

The service is request/response: the receiver sends "PLAY_<cam>", the board
replies with a length-prefixed JPEG, and the receiver ACKs it so the board
sends the next frame.  "STREAM_RESIZE_WxHxQ" (optional --resize) shrinks the
stream before playing; "STOP_STREAM" stops the stream.

Usage (on the ground station):
    python3 jpeg_receiver.py --host 172.16.18.191 --port 9001 --cam cam1
"""
import argparse
import io
import os
import socket
import sys
import threading
import time
import tkinter as tk

from PIL import Image, ImageTk

from jpeg_proto import HDR, MAX_JPEG, read_frame, is_jpeg

BG = "#111111"
FG = "#d0d0d0"
ACCENT = "#7fdbca"


class JpegReceiver:
    def __init__(self, root, host, port, cam="cam1", save_dir=None, save_every=1,
                 resize=None):
        self.root = root
        self.host = host
        self.port = port
        self.cam = cam
        self.save_dir = save_dir
        self.save_every = max(1, save_every)
        self.resize = resize
        self.running = True

        self._latest = None
        self._photo = None
        self._arrivals = []
        self._last_t = None
        self._jpeg_size = 0
        self._saved = 0
        self._save_counter = 0

        self.status = tk.StringVar(value="connecting...")
        self._build_ui()
        threading.Thread(target=self._recv_loop, daemon=True).start()
        self.root.after(100, self._tick)

    def _build_ui(self):
        self.root.title(
            f"JPEG receiver {self.host}:{self.port} ({self.cam}) [TCP]")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        img = Image.new("RGB", (640, 360), (0, 0, 0))
        self._photo = ImageTk.PhotoImage(img)
        self.lbl = tk.Label(self.root, image=self._photo, bg="#000000")
        self.lbl.pack(padx=4, pady=4)
        self.info = tk.Label(self.root, textvariable=self.status, fg=ACCENT,
                             bg=BG, font=("DejaVu Sans", 10))
        self.info.pack(fill="x", padx=4, pady=(0, 4))

    def _connect(self):
        """Open a TCP socket to the board."""
        sock = socket.create_connection((self.host, self.port), timeout=5)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return sock

    def _read_msg(self, sock):
        """Read one length-prefixed message over the active transport."""
        return read_frame(sock)

    def _recv_loop(self):
        while self.running:
            try:
                sock = self._connect()
            except OSError as e:
                self._set_status(f"no connection ({e})")
                time.sleep(2)
                continue
            self._set_status(
                f"streaming {self.cam} from {self.host}:{self.port} via TCP")
            try:
                sock.settimeout(10.0)
                if self.resize:
                    sock.sendall((self.resize + "\n").encode("utf-8"))
                    r = self._read_msg(sock)
                    if not is_jpeg(r):
                        self._set_status(r.decode("utf-8", "replace").strip())
                sock.sendall(f"PLAY_{self.cam}\n".encode("utf-8"))
                while self.running:
                    msg = self._read_msg(sock)
                    if is_jpeg(msg):
                        self._on_frame(msg)
                        sock.sendall(b"ACK\n")
                    else:
                        self._set_status(msg.decode("utf-8", "replace").strip())
                        if msg[:3] == b"ERR":
                            time.sleep(1.0)
                            sock.sendall(f"PLAY_{self.cam}\n".encode("utf-8"))
            except (OSError, EOFError, ValueError) as e:
                self._set_status(f"disconnected ({e})")
            finally:
                try:
                    sock.sendall(b"STOP_STREAM\n")
                except OSError:
                    pass
                try:
                    sock.close()
                except OSError:
                    pass
                if self.running:
                    time.sleep(2)

    def _set_status(self, msg):
        self.root.after(0, lambda: self.status.set(msg))

    def _on_frame(self, data):
        now = time.monotonic()
        self._jpeg_size = len(data)
        self._arrivals.append(now)
        self._arrivals = [t for t in self._arrivals if now - t <= 5.0]
        self._last_t = now
        self._latest = data
        if self.save_dir:
            self._save_counter += 1
            if self._save_counter % self.save_every == 0:
                name = f"frame_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
                path = os.path.join(self.save_dir, name)
                try:
                    with open(path, "wb") as f:
                        f.write(data)
                    self._saved += 1
                except OSError:
                    pass

    def _tick(self):
        if self._latest is not None:
            now = time.monotonic()
            try:
                img = Image.open(io.BytesIO(self._latest)).convert("RGB")
                self._photo = ImageTk.PhotoImage(img)
                self.lbl.configure(image=self._photo)
            except Exception:
                pass
            age = now - self._last_t
            fps = len([t for t in self._arrivals if now - t <= 5.0]) / 5.0
            msg = (f"{self.host}:{self.port}  |  {self._jpeg_size // 1024}kB  |  "
                   f"{fps:.1f} fps  |  last {age:.1f}s ago")
            if self.save_dir:
                msg += f"  |  saved {self._saved}"
            self.status.set(msg)
        self.root.after(100, self._tick)

    def _on_close(self):
        self.running = False
        self.root.destroy()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="172.16.18.191",
                    help="board IP running jpeg_sender.py")
    ap.add_argument("--port", type=int, default=9001,
                    help="TCP port of the board image service")
    ap.add_argument("--cam", default="cam1",
                    help="camera to stream (e.g. cam1..cam4, cubesat)")
    ap.add_argument("--save-dir", default=None,
                    help="optional directory to save received frames")
    ap.add_argument("--save-every", type=int, default=1,
                    help="save every Nth frame (default 1 = all frames)")
    ap.add_argument("--resize", default=None,
                    metavar="WxHxQ",
                    help="STREAM_RESIZE before playing, e.g. 320x240x40")
    args = ap.parse_args()

    if args.save_dir:
        os.makedirs(args.save_dir, exist_ok=True)

    root = tk.Tk()
    JpegReceiver(root, args.host, args.port, args.cam, args.save_dir,
                 args.save_every, args.resize)
    root.mainloop()


if __name__ == "__main__":
    main()
