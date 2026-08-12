#!/usr/bin/env python3
"""
Camera feed popup: connects to the board JPEG senders (raw JPEG over plain
TCP, ~1 fps).  cam1..cam4 run on the EBOX (ports 9000-9003); the cubesat
camera is forwarded through the EBOX on port 9004.  No RTSP anywhere.

Camera selector switches which camera the preview shows.  Recording is
record-ALL on both sides:

  * "Record (GUI)"  -- the ground station saves one MJPEG .avi per camera
                       (cam1-4 + cubesat) into the chosen folder, even for
                       cameras that are not currently previewed.
  * "Record (Radxa)" -- tells both boards (EBOX + CUBESAT cmd servers) to
                       start/stop recording on the radxa itself ("JPEGREC
                       ON/OFF"); every sender on that board records into
                       ~/Desktop/svarog/board/cam_recordings/jpeg/<cam>/.
"""
import io
import os
import queue
import socket
import struct
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog

from PIL import Image, ImageTk

from gui_theme import (BG, BG2, BG3, FG, FG_DIM, ACCENT, GREEN, RED,
                       FONT, FONT_B, FONT_S)

SAROG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_REC_DIR = os.path.join(SAROG_DIR, "recordings", "jpeg")

HDR = struct.Struct(">I")
MAX_JPEG = 4 * 1024 * 1024
PREVIEW_W, PREVIEW_H = 640, 480

# cam_id -> (display, host, port, board cmd target)
CAM_SOURCES = [
    ("cam1",    "CAM 1",    "172.16.18.191", 9000, "ebox"),
    ("cam2",    "CAM 2",    "172.16.18.191", 9001, "ebox"),
    ("cam3",    "CAM 3",    "172.16.18.191", 9002, "ebox"),
    ("cam4",    "CAM 4",    "172.16.18.191", 9003, "ebox"),
    ("cubesat", "CUBESAT",  "172.16.18.191", 9004, "cubesat"),
]
CAM_MAP = {cid: {"display": disp, "host": host, "port": port, "board": board}
           for cid, disp, host, port, board in CAM_SOURCES}
BOARDS = ("ebox", "cubesat")


def _mjpeg_avi_module():
    path = os.path.join(SAROG_DIR, "board", "subcomponents")
    if path not in sys.path:
        sys.path.insert(0, path)
    import mjpeg_avi
    return mjpeg_avi


class VideoWindow(tk.Toplevel):
    """Popup showing the radxa JPEG feeds; records all cams on GUI or radxa."""

    def __init__(self, root, links=None):
        super().__init__(root)
        self.title("Camera Feed")
        self.geometry("960x640")
        self.minsize(820, 560)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.links = links or {}       # {"ebox": BoardConnector, "cubesat": BoardConnector}
        self.src_var = tk.StringVar(value="172.16.18.191:9000")
        self.status_var = tk.StringVar(value="not connected")
        self.rec_folder_var = tk.StringVar(value=DEFAULT_REC_DIR)
        self.fps_var = tk.StringVar(value="FPS: --")
        self.stale_var = tk.StringVar(value="waiting for frames...")
        self.gui_rec_var = tk.StringVar(value="")
        self.radxa_rec_var = tk.StringVar(value="Radxa: idle")

        # cross-thread handoff: stream/record threads never touch Tk directly
        self._img_queue = queue.Queue(maxsize=2)
        self._status_queue = queue.Queue()
        self._ui_queue = queue.Queue()
        self._stop = threading.Event()
        self._thread = None

        self._photo = None
        self._last_t = None
        self._arrivals = []
        self._jpeg_size = 0
        self._jpeg_dims = None

        # GUI-side record-ALL
        self.gui_rec = False
        self._gui_writers = {}         # cam_id -> MjpegAvi (guarded by _rec_lock)
        self._bg_recs = {}             # cam_id -> {"thread", "stop"}
        self._rec_folder = DEFAULT_REC_DIR
        self._rec_lock = threading.Lock()

        # Radxa-side record-ALL (per board, from "JPEGREC" status responses)
        self._radxa = {b: {"rec": False, "alive": False} for b in BOARDS}

        self._cur_cam = "cam1"
        self.cam_btns = {}

        self._build_ui()
        self._attach_link_responses()
        self._start_stream(cam="cam1")
        self.after(40, self._tick)
        self.after(4000, self._poll_radxa)

    # ── UI ─────────────────────────────────────────────────────────

    def _build_ui(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=6, pady=6)

        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        ph = Image.new("RGB", (PREVIEW_W, PREVIEW_H), (0, 0, 0))
        self._photo = ImageTk.PhotoImage(ph)
        self.video_lbl = tk.Label(left, image=self._photo, bg="#000000")
        self.video_lbl.pack(fill="both", expand=True)

        self._build_cam_selector(left)

        src_bar = tk.Frame(left, bg=BG)
        src_bar.pack(fill="x")
        self._label(src_bar, "Source:", bg=BG).pack(side="left")
        e = tk.Entry(src_bar, textvariable=self.src_var, font=FONT,
                     bg=BG, fg=FG, insertbackground=FG, relief="flat", bd=2)
        e.pack(side="left", fill="x", expand=True, padx=4)
        self._btn(src_bar, "Apply", self._restart_stream).pack(side="left")

        rec_bar = tk.Frame(left, bg=BG)
        rec_bar.pack(fill="x", pady=(4, 0))
        self.gui_rec_btn = self._btn(rec_bar, "Record (GUI)", self._toggle_gui_rec,
                                     bg=GREEN, font=FONT_B, padx=10, pady=3)
        self.gui_rec_btn.pack(side="left")
        self.radxa_rec_btn = self._btn(rec_bar, "Record (Radxa)", self._toggle_radxa_rec,
                                       bg=GREEN, font=FONT_B, padx=10, pady=3)
        self.radxa_rec_btn.pack(side="left", padx=(8, 0))

        folder_bar = tk.Frame(left, bg=BG)
        folder_bar.pack(fill="x")
        self._label(folder_bar, "GUI save to:", bg=BG).pack(side="left")
        fe = tk.Entry(folder_bar, textvariable=self.rec_folder_var, font=FONT_S,
                      bg=BG, fg=FG, insertbackground=FG, relief="flat", bd=2)
        fe.pack(side="left", fill="x", expand=True, padx=4)
        self._btn(folder_bar, "Browse", self._browse_folder, font=FONT_S,
                  padx=6).pack(side="left")

        rec_status = tk.Frame(left, bg=BG)
        rec_status.pack(fill="x")
        self._label(rec_status, textvariable=self.gui_rec_var, fg=FG_DIM,
                    bg=BG, anchor="w", font=FONT_S).pack(side="left",
                                                         fill="x", expand=True)
        self._label(rec_status, textvariable=self.radxa_rec_var, fg=FG_DIM,
                    bg=BG, anchor="e", font=FONT_S).pack(side="right")

        status_frame = tk.Frame(left, bg=BG)
        status_frame.pack(fill="x")
        self._label(status_frame, textvariable=self.status_var, fg=FG_DIM,
                    bg=BG, anchor="w", font=FONT_S).pack(side="left", fill="x", expand=True)
        self._label(status_frame, textvariable=self.stale_var, fg=RED,
                    bg=BG, anchor="e", font=FONT_S).pack(side="right")
        self._label(status_frame, textvariable=self.fps_var, fg=GREEN,
                    bg=BG, anchor="e", font=FONT_B).pack(side="right", padx=(0, 10))

    def _build_cam_selector(self, parent):
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x")
        self._label(bar, "View:", bg=BG).pack(side="left")
        for cid, disp, host, port, board in CAM_SOURCES:
            b = self._btn(bar, disp, lambda c=cid: self._select_cam(c),
                          bg=BG3, fg=FG, padx=10, pady=2)
            b.pack(side="left", padx=(6, 0))
            self.cam_btns[cid] = b
        self._render_cam_selector()

    def _render_cam_selector(self):
        for cid, b in self.cam_btns.items():
            if cid == self._cur_cam:
                b.configure(bg=ACCENT, fg=BG, activebackground=ACCENT,
                            activeforeground=BG)
            else:
                b.configure(bg=BG3, fg=FG, activebackground=BG3,
                            activeforeground=FG)

    def _label(self, parent, text=None, **kw):
        kw.setdefault("font", FONT)
        kw.setdefault("fg", FG)
        kw.setdefault("bg", BG2)
        if text is not None:
            kw["text"] = text
        return tk.Label(parent, **kw)

    def _btn(self, parent, text, cmd, fg=BG, bg=ACCENT, **kw):
        kw.setdefault("font", FONT_B)
        kw.setdefault("padx", 8)
        kw.setdefault("pady", 2)
        return tk.Button(parent, text=text, command=cmd,
                         fg=fg, bg=bg, activebackground=bg,
                         activeforeground=FG, relief="flat", bd=0,
                         cursor="hand2", **kw)

    # ── camera selection / stream ───────────────────────────────────

    def _select_cam(self, cid):
        cfg = CAM_MAP[cid]
        self.src_var.set(f"{cfg['host']}:{cfg['port']}")
        self._cur_cam = cid
        self._render_cam_selector()
        self._start_stream(cam=cid)
        self._sync_bg_recorders()

    def _parse_source(self):
        s = self.src_var.get().strip() or "172.16.18.191:9000"
        if ":" in s:
            host, _, port = s.rpartition(":")
            host = host.strip() or "172.16.18.191"
            try:
                return host, int(port)
            except ValueError:
                return host, 9000
        return s, 9000

    def _start_stream(self, cam=None):
        self._stop.set()
        if cam and cam in CAM_MAP:
            cfg = CAM_MAP[cam]
            host, port = cfg["host"], cfg["port"]
            self._cur_cam = cam
        else:
            self._cur_cam = cam or None
            host, port = self._parse_source()
        self._render_cam_selector()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._stream_loop,
                                        args=(host, port, cam), daemon=True)
        self._thread.start()
        self.status_var.set(f"connecting to {host}:{port}...")

    def _restart_stream(self):
        self._stop.set()
        self._img_queue.queue.clear()
        self._start_stream(cam=None)
        self._sync_bg_recorders()

    def _stream_loop(self, host, port, cam):
        while not self._stop.is_set():
            try:
                sock = socket.create_connection((host, port), timeout=5)
            except OSError as e:
                self._status_queue.put(f"no connection ({e})")
                self._stop.wait(2)
                continue
            self._status_queue.put(f"connected to {host}:{port}")
            try:
                sock.settimeout(10.0)
                self._read_stream(sock, cam)
            except (OSError, EOFError, ValueError) as e:
                self._status_queue.put(f"disconnected ({e})")
            finally:
                try:
                    sock.close()
                except OSError:
                    pass
                self._stop.wait(2)
        self._status_queue.put("stream stopped")

    def _read_stream(self, sock, cam):
        buf = b""
        while not self._stop.is_set():
            chunk = sock.recv(65536)
            if not chunk:
                return
            buf += chunk
            while len(buf) >= HDR.size:
                n = HDR.unpack(buf[:HDR.size])[0]
                if n < 1 or n > MAX_JPEG:       # lost sync, drop header
                    buf = buf[HDR.size:]
                    continue
                if len(buf) < HDR.size + n:
                    break
                jpeg = buf[HDR.size:HDR.size + n]
                buf = buf[HDR.size + n:]
                self._handle_frame(jpeg, cam)

    def _handle_frame(self, jpeg, cam):
        now = time.monotonic()
        self._jpeg_size = len(jpeg)
        self._arrivals.append(now)
        self._arrivals = [t for t in self._arrivals if now - t <= 5.0]
        self._last_t = now
        try:
            img = Image.open(io.BytesIO(jpeg)).convert("RGB")
        except Exception:
            return
        self._jpeg_dims = img.size
        if self._img_queue.full():
            try:
                self._img_queue.get_nowait()
            except queue.Empty:
                pass
        self._img_queue.put(img)
        if self.gui_rec:
            self._record_gui_frame(jpeg, img.size, cam or "custom")

    # ── tick (main thread: drain queues, render, HUD) ───────────────

    def _tick(self):
        self._rec_folder = self.rec_folder_var.get().strip() or DEFAULT_REC_DIR
        while not self._status_queue.empty():
            self.status_var.set(self._status_queue.get_nowait())
        while not self._ui_queue.empty():
            try:
                self._ui_queue.get_nowait()()
            except Exception:
                pass
        while not self._img_queue.empty():
            img = self._img_queue.get_nowait()
            self._photo = ImageTk.PhotoImage(img)
            self.video_lbl.configure(image=self._photo)

        now = time.monotonic()
        if self._last_t is not None:
            fps = len([t for t in self._arrivals if now - t <= 5.0]) / 5.0
            age = now - self._last_t
            dims = self._jpeg_dims or (0, 0)
            self.fps_var.set(f"FPS: {fps:.1f}")
            self.stale_var.set(
                f"{dims[0]}x{dims[1]} {self._jpeg_size // 1024}kB · last {age:.1f}s ago")
        else:
            self.fps_var.set("FPS: --")
        self.after(40, self._tick)

    # ── GUI-side record-ALL ─────────────────────────────────────────

    def _toggle_gui_rec(self):
        if self.gui_rec:
            self._stop_gui_rec()
        else:
            self.gui_rec = True
            self.gui_rec_btn.configure(text="Stop (GUI)", bg=RED)
            self.gui_rec_var.set("recording all cams...")
            self._sync_bg_recorders()

    def _record_gui_frame(self, jpeg, dims, cam):
        if not self.gui_rec:
            return
        with self._rec_lock:
            w = self._gui_writers.get(cam)
            if w is None:
                try:
                    mjpeg_avi = _mjpeg_avi_module()
                except Exception as e:
                    self._ui_queue.put(lambda e=e: self.gui_rec_var.set(f"record failed: {e}"))
                    return
                folder = self._rec_folder or DEFAULT_REC_DIR
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(
                    folder, f"rec_{cam}_{time.strftime('%Y%m%d_%H%M%S')}.avi")
                w = mjpeg_avi.MjpegAvi(path, dims[0], dims[1], fps=1.0)
                self._gui_writers[cam] = w
                self._ui_queue.put(self._refresh_gui_rec_status)
            w.write(jpeg)

    def _refresh_gui_rec_status(self):
        n = len(self._gui_writers)
        total = len(CAM_MAP) + 1 if self._cur_cam is None else len(CAM_MAP)
        folder = self._rec_folder or DEFAULT_REC_DIR
        if n:
            self.gui_rec_var.set(f"recording {min(n, total)}/{total} cams to {folder}")
        else:
            self.gui_rec_var.set("recording...")

    def _sync_bg_recorders(self):
        if not self.gui_rec:
            for ent in self._bg_recs.values():
                ent["stop"].set()
            self._bg_recs.clear()
            return
        for cid in CAM_MAP:
            if cid == self._cur_cam or cid in self._bg_recs:
                continue
            stop = threading.Event()
            t = threading.Thread(target=self._bg_loop, args=(cid, stop), daemon=True)
            self._bg_recs[cid] = {"thread": t, "stop": stop}
            t.start()

    def _bg_loop(self, cid, stop):
        cfg = CAM_MAP[cid]
        while not stop.is_set():
            try:
                sock = socket.create_connection((cfg["host"], cfg["port"]), timeout=5)
            except OSError:
                stop.wait(2)
                continue
            try:
                sock.settimeout(10.0)
                self._bg_read(sock, cid, stop)
            except (OSError, EOFError, ValueError):
                pass
            finally:
                try:
                    sock.close()
                except OSError:
                    pass
                stop.wait(2)

    def _bg_read(self, sock, cid, stop):
        buf = b""
        while not stop.is_set():
            chunk = sock.recv(65536)
            if not chunk:
                return
            buf += chunk
            while len(buf) >= HDR.size:
                n = HDR.unpack(buf[:HDR.size])[0]
                if n < 1 or n > MAX_JPEG:
                    buf = buf[HDR.size:]
                    continue
                if len(buf) < HDR.size + n:
                    break
                jpeg = buf[HDR.size:HDR.size + n]
                buf = buf[HDR.size + n:]
                try:
                    dims = Image.open(io.BytesIO(jpeg)).size
                except Exception:
                    continue
                self._record_gui_frame(jpeg, dims, cid)

    def _stop_gui_rec(self):
        self.gui_rec = False
        self._sync_bg_recorders()
        self.gui_rec_btn.configure(text="Record (GUI)", bg=GREEN)
        with self._rec_lock:
            writers, self._gui_writers = self._gui_writers, {}
        for w in writers.values():
            try:
                w.close()
            except Exception:
                pass
        if writers:
            folder = self._rec_folder or DEFAULT_REC_DIR
            self.gui_rec_var.set(f"Saved {len(writers)} cams to {folder}")
        else:
            self.gui_rec_var.set("")

    # ── radxa-side record-ALL (via both board cmd servers) ──────────

    def _attach_link_responses(self):
        for board, link in self.links.items():
            if link:
                link.on_resp = (lambda text, b=board: self._on_resp(b, text))

    def _link(self, board):
        link = self.links.get(board)
        if link is None or link.connected:
            return link
        try:
            link.connect(link.default_ip, link.default_cmd,
                         link.default_telem, silent=True)
        except Exception:
            return None
        return link if link.connected else None

    def _send_board(self, board, cmd):
        link = self._link(board)
        if link is None:
            return
        link.send(cmd)

    def _toggle_radxa_rec(self):
        on = not any(v["rec"] for v in self._radxa.values())
        for board in BOARDS:
            self._send_board(board, "JPEGREC ON" if on else "JPEGREC OFF")

    def _poll_radxa(self):
        for board in BOARDS:
            link = self.links.get(board)
            if link and link.connected:
                link.send("JPEGREC")
        self.after(4000, self._poll_radxa)

    def _on_resp(self, board, text):
        st = self._radxa.setdefault(board, {"rec": False, "alive": False})
        for token in str(text).replace(";", " ").split():
            if token.startswith("JPEG_REC="):
                st["rec"] = token.split("=", 1)[1] == "1"
            elif token.startswith("SENDER="):
                st["alive"] = token.split("=", 1)[1] == "1"
        self._render_radxa_rec()

    def _render_radxa_rec(self):
        rec_any = any(v["rec"] for v in self._radxa.values())
        self.radxa_rec_btn.configure(
            text="Stop (Radxa)" if rec_any else "Record (Radxa)",
            bg=RED if rec_any else GREEN)
        parts = []
        for board, v in self._radxa.items():
            if v["rec"]:
                parts.append(f"{board.upper()} ●")
            elif v["alive"]:
                parts.append(f"{board.upper()} ready")
            else:
                parts.append(f"{board.upper()} idle")
        self.radxa_rec_var.set("Radxa: " + "  ".join(parts))

    # ── misc ───────────────────────────────────────────────────────

    def _browse_folder(self):
        d = filedialog.askdirectory(initialdir=self._rec_folder,
                                    parent=self, title="GUI recording folder")
        if d:
            self.rec_folder_var.set(d)
            self._rec_folder = d

    def _on_close(self):
        self._stop.set()
        self._stop_gui_rec()
        for link in self.links.values():
            if link and getattr(link, "on_resp", None):
                link.on_resp = None
        self.destroy()
