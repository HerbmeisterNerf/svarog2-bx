#!/usr/bin/env python3
"""
Low-bandwidth camera receiver: connects to board/subcomponents/jpeg_sender.py
and displays the ~1 fps JPEG frames in a small Tk window.  Optionally saves
frames to disk with --save-dir.

The wire format is a 4-byte big-endian length followed by the JPEG bytes.

Usage (on the ground station):
    python3 jpeg_receiver.py --host 172.16.18.191 --port 9000
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

from jpeg_proto import HDR, MAX_JPEG, read_frame, recv_exact

BG = "#111111"
FG = "#d0d0d0"
ACCENT = "#7fdbca"


class JpegReceiver:
    def __init__(self, root, host, port, save_dir=None, save_every=1):
        self.root = root
        self.host = host
        self.port = port
        self.save_dir = save_dir
        self.save_every = max(1, save_every)
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
        self.root.title(f"JPEG receiver {self.host}:{self.port}")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        img = Image.new("RGB", (640, 360), (0, 0, 0))
        self._photo = ImageTk.PhotoImage(img)
        self.lbl = tk.Label(self.root, image=self._photo, bg="#000000")
        self.lbl.pack(padx=4, pady=4)
        self.info = tk.Label(self.root, textvariable=self.status, fg=ACCENT,
                             bg=BG, font=("DejaVu Sans", 10))
        self.info.pack(fill="x", padx=4, pady=(0, 4))

    def _recv_loop(self):
        while self.running:
            try:
                sock = socket.create_connection((self.host, self.port), timeout=5)
            except OSError as e:
                self._set_status(f"no connection ({e})")
                time.sleep(2)
                continue
            self._set_status(f"connected to {self.host}:{self.port}")
            try:
                sock.settimeout(10.0)
                while self.running:
                    data = read_frame(sock)
                    self._on_frame(data)
            except (OSError, EOFError, ValueError) as e:
                self._set_status(f"disconnected ({e})")
            finally:
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
    ap.add_argument("--port", type=int, default=9000,
                    help="TCP port of jpeg_sender.py")
    ap.add_argument("--save-dir", default=None,
                    help="optional directory to save received frames")
    ap.add_argument("--save-every", type=int, default=1,
                    help="save every Nth frame (default 1 = all frames)")
    args = ap.parse_args()

    if args.save_dir:
        os.makedirs(args.save_dir, exist_ok=True)

    root = tk.Tk()
    JpegReceiver(root, args.host, args.port, args.save_dir, args.save_every)
    root.mainloop()


if __name__ == "__main__":
    main()
