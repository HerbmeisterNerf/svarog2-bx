#!/usr/bin/env python3
"""
Camera feed popup: streams raw JPEG over plain TCP from the board image
service (board/subcomponents/jpeg_sender.py).  All EBOX cameras (cam1..cam4)
are served by one process on 172.16.18.191:9001; the cubesat camera is
forwarded through the EBOX on port 9004.  No RTSP anywhere.

The service is request/response so frames never queue up on the wire:

  GUI -> board  "PLAY_<cam>"     start streaming camera <cam>
  board -> GUI  length-prefixed JPEG (or status text)
  GUI -> board  "STREAM_RESIZE_WxHxQ"  shrink the stream to WxH, quality Q
  GUI -> board  "ACK"            got the frame, send the next
  GUI -> board  "STOP_STREAM"    stop streaming

The board always records at full capture resolution; STREAM_RESIZE only
affects the frames sent over the link.

Recording:
  * "Record (GUI)"  -- every frame of the currently-streamed camera is saved
                       as a timestamped JPEG into the chosen folder.
  * "Radxa status"  -- queries both boards ("JPEGREC"): the radxa image
                       service records continuously while it is running.
"""
import io
import os
import queue
import socket
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

PREVIEW_W, PREVIEW_H = 640, 480

# cam_id -> (display, host, port, board cmd target)
CAM_SOURCES = [
    ("cam1",    "CAM 1",    "172.16.18.191", 9001, "ebox"),
    ("cam2",    "CAM 2",    "172.16.18.191", 9001, "ebox"),
    ("cam3",    "CAM 3",    "172.16.18.191", 9001, "ebox"),
    ("cam4",    "CAM 4",    "172.16.18.191", 9001, "ebox"),
    ("cubesat", "CUBESAT",  "172.16.18.191", 9004, "cubesat"),
]
CAM_MAP = {cid: {"display": disp, "host": host, "port": port, "board": board}
           for cid, disp, host, port, board in CAM_SOURCES}
BOARDS = ("ebox", "cubesat")


def _jpeg_proto_module():
    path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if path not in sys.path:
        sys.path.insert(0, path)
    import jpeg_proto
    return jpeg_proto


class VideoWindow(tk.Toplevel):
    """Popup showing the radxa JPEG feeds; captures the preview to JPEGs on GUI
    and can start/stop radxa-side recording on both boards."""

    def __init__(self, root, links=None):
        super().__init__(root)
        self.title("Camera Feed")
        self.geometry("960x640")
        self.minsize(820, 560)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.links = links or {}       # {"ebox": BoardConnector, "cubesat": BoardConnector}
        self.src_var = tk.StringVar(value="172.16.18.191:9001")
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
        self._tx_queue = queue.Queue()      # commands for the stream thread
        self._stop = threading.Event()      # window quit
        self._stream_stop = threading.Event()   # current stream thread
        self._gen = 0                       # bumped on every source switch
        self._thread = None
        self._sock = None                   # current stream socket (main thread may close it)
        self._streaming = True

        self._photo = None
        self._last_t = None
        self._arrivals = []
        self._jpeg_size = 0
        self._jpeg_dims = None

        # GUI-side capture: save previewed frames as timestamped JPEGs
        self.gui_rec = False
        self._gui_saved = 0           # frames saved this session (guarded)
        self._rec_folder = DEFAULT_REC_DIR
        self._rec_lock = threading.Lock()
        self.resize_var = tk.StringVar(value="640x480x40")

        # Radxa-side record-ALL (per board, from "JPEGREC" status responses)
        self._radxa = {b: {"rec": False, "alive": False} for b in BOARDS}

        self._cur_cam = "cam1"
        self.cam_btns = {}

        self._build_ui()
        self._attach_link_responses()
        self._start_stream(cam="cam1")
        self.after(40, self._tick)

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
        self.stream_btn = self._btn(src_bar, "Stop", self._toggle_stream, bg=RED)
        self.stream_btn.pack(side="left", padx=(4, 0))

        res_bar = tk.Frame(left, bg=BG)
        res_bar.pack(fill="x", pady=(4, 0))
        self._label(res_bar, "Stream:", bg=BG).pack(side="left")
        re = tk.Entry(res_bar, textvariable=self.resize_var, font=FONT,
                      bg=BG, fg=FG, insertbackground=FG, relief="flat", bd=2,
                      width=12)
        re.pack(side="left", fill="x", expand=True, padx=4)
        self._btn(res_bar, "Resize", self._send_resize, font=FONT_S,
                  padx=6).pack(side="left")
        for label, val in (("1/2", "640x480x40"), ("1/4", "320x240x40"),
                           ("Full", "1280x720x80"), ("Raw", "0")):
            self._btn(res_bar, label, lambda v=val: self._set_resize(v),
                      font=FONT_S, padx=4).pack(side="left", padx=(2, 0))

        rec_bar = tk.Frame(left, bg=BG)
        rec_bar.pack(fill="x", pady=(4, 0))
        self.gui_rec_btn = self._btn(rec_bar, "Record (GUI)", self._toggle_gui_rec,
                                     bg=GREEN, font=FONT_B, padx=10, pady=3)
        self.gui_rec_btn.pack(side="left")
        self.radxa_rec_btn = self._btn(rec_bar, "Radxa status", self._query_radxa_rec,
                                        bg=GREEN, font=FONT_B, padx=10, pady=3)
        self.radxa_rec_btn.pack(side="left", padx=(8, 0))
        self.prune_var = True
        self.prune_btn = self._btn(rec_bar, "Prune: ON", self._toggle_prune,
                                    bg=GREEN, font=FONT_B, padx=10, pady=3)
        self.prune_btn.pack(side="left", padx=(8, 0))

        fps_bar = tk.Frame(left, bg=BG)
        fps_bar.pack(fill="x", pady=(4, 0))
        self._label(fps_bar, "Rec FPS:", bg=BG).pack(side="left")
        self.fps_entry_var = tk.StringVar(value="6.7")
        fps_e = tk.Entry(fps_bar, textvariable=self.fps_entry_var, font=FONT,
                         bg=BG, fg=FG, insertbackground=FG, relief="flat", bd=2,
                         width=6)
        fps_e.pack(side="left", padx=4)
        self._btn(fps_bar, "Set", self._set_rec_fps, font=FONT_S,
                  padx=6).pack(side="left")
        for label, val in (("1", "1"), ("5", "5"), ("10", "10"), ("20", "20")):
            self._btn(fps_bar, label, lambda v=val: self._set_rec_fps_val(v),
                      font=FONT_S, padx=4).pack(side="left", padx=(2, 0))

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
        self._streaming = True
        self.stream_btn.configure(text="Stop", bg=RED)
        self._start_stream(cam=cid)

    def _parse_source(self):
        s = self.src_var.get().strip() or "172.16.18.191:9001"
        if ":" in s:
            host, _, port = s.rpartition(":")
            host = host.strip() or "172.16.18.191"
            try:
                return host, int(port)
            except ValueError:
                return host, 9001
        return s, 9001

    def _start_stream(self, cam=None):
        # stop the previous stream thread and invalidate any in-flight frames
        self._stream_stop.set()
        self._gen += 1
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self._img_queue.queue.clear()
        self._tx_queue = queue.Queue()
        self._last_t = None
        self._arrivals = []
        self._jpeg_size = 0
        self._jpeg_dims = None

        if cam and cam in CAM_MAP:
            cfg = CAM_MAP[cam]
            host, port = cfg["host"], cfg["port"]
            self._cur_cam = cam
        else:
            self._cur_cam = cam or None
            host, port = self._parse_source()
        self._render_cam_selector()

        # fresh per-stream stop event + generation so this thread is the only
        # one whose frames can ever reach the screen
        cam_id = cam or self._cur_cam or "cam1"
        self._stream_stop = threading.Event()
        self._thread = threading.Thread(
            target=self._stream_loop,
            args=(host, port, cam_id, self._stream_stop, self._gen), daemon=True)
        self._thread.start()
        if self.prune_var:
            self._tx_queue.put("PRUNE_ON")
        self.status_var.set(f"connecting to {host}:{port}...")

    def _restart_stream(self):
        self._img_queue.queue.clear()
        self._tx_queue = queue.Queue()
        self._streaming = True
        self.stream_btn.configure(text="Stop", bg=RED)
        self._start_stream(cam=None)

    def _parse_resize(self, s):
        """Parse 'WxHxQ', 'W_H_Q' or '0'/'raw'.  Return cmd string or None."""
        s = s.strip().lower().replace(",", "_").replace("x", "_")
        if not s:
            return None
        if s in ("0", "raw"):
            return "STREAM_RESIZE_0"
        parts = s.split("_")
        if len(parts) == 3:
            try:
                w, h, q = (int(p) for p in parts)
            except ValueError:
                return None
            if 16 <= w <= 4096 and 16 <= h <= 4096 and 1 <= q <= 100:
                return f"STREAM_RESIZE_{w}_{h}_{q}"
        return None

    def _set_resize(self, s):
        self.resize_var.set(s)
        self._send_resize()

    def _send_resize(self):
        cmd = self._parse_resize(self.resize_var.get())
        if cmd is None:
            self.status_var.set("bad stream size (use WxHxQ or 0 for raw)")
            return
        self._tx_queue.put(cmd)
        self.status_var.set(f"sending {cmd}")

    def _toggle_stream(self):
        if self._streaming:
            self._stop_streaming()
        else:
            self._streaming = True
            self.stream_btn.configure(text="Stop", bg=RED)
            self._start_stream(cam=self._cur_cam or "cam1")

    def _stop_streaming(self):
        self._streaming = False
        self._stream_stop.set()
        self._gen += 1
        if self._sock is not None:
            try:
                self._sock.sendall(b"STOP_STREAM\n")
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self._img_queue.queue.clear()
        self._last_t = None
        self._arrivals = []
        self.status_var.set("stream stopped")
        self.stream_btn.configure(text="Play", bg=GREEN)

    def _stream_loop(self, host, port, cam, stop, gen):
        while not stop.is_set():
            try:
                sock = socket.create_connection((host, port), timeout=5)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.settimeout(10.0)
            except OSError as e:
                self._status_queue.put(f"no connection ({e})")
                stop.wait(2)
                continue
            self._sock = sock
            try:
                if stop.is_set():
                    return
                sock.sendall(f"PLAY_{cam}\n".encode("utf-8"))
                self._status_queue.put(
                    f"streaming {cam} from {host}:{port} via TCP")
                self._read_stream(sock, cam, stop, gen)
            except (OSError, EOFError, ValueError) as e:
                if not stop.is_set():
                    self._status_queue.put(f"disconnected ({e})")
            finally:
                if self._sock is sock:
                    self._sock = None
                try:
                    sock.close()
                except OSError:
                    pass
                stop.wait(2)
        self._status_queue.put("stream stopped")

    def _read_stream(self, sock, cam, stop, gen):
        proto = _jpeg_proto_module()
        await_play = True      # next message is the reply to PLAY_
        while not stop.is_set():
            if await_play:
                await_play = False
                msg = proto.read_frame(sock)
            else:
                try:
                    cmd = self._tx_queue.get_nowait()
                except queue.Empty:
                    cmd = None
                sock.sendall((cmd.encode() + b"\n") if cmd else b"ACK\n")
                msg = proto.read_frame(sock)
            if proto.is_jpeg(msg):
                self._handle_frame(msg, cam, gen)
            else:
                text = msg.decode("utf-8", "replace").strip()
                self._status_queue.put(text)
                if text.upper().startswith("ERR"):
                    stop.wait(1.0)
                    if stop.is_set():
                        return
                    sock.sendall(f"PLAY_{cam}\n".encode("utf-8"))
                    await_play = True

    def _handle_frame(self, jpeg, cam, gen):
        if gen != self._gen:
            return        # stale frame from a stream we switched away from
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
            self._save_gui_frame(jpeg, cam or "custom")

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

    # ── GUI-side capture: save every previewed frame as a JPEG ──────

    def _toggle_gui_rec(self):
        if self.gui_rec:
            self._stop_gui_rec()
        else:
            self.gui_rec = True
            self.gui_rec_btn.configure(text="Stop (GUI)", bg=RED)
            folder = self._rec_folder or DEFAULT_REC_DIR
            self.gui_rec_var.set(f"recording preview to {folder}...")

    def _save_gui_frame(self, jpeg, cam):
        if not self.gui_rec:
            return
        folder = self._rec_folder or DEFAULT_REC_DIR
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError:
            return
        name = (f"frame_{cam}_{time.strftime('%Y%m%d_%H%M%S')}_"
                f"{int(time.time() * 1e6)}.jpg")
        try:
            with open(os.path.join(folder, name), "wb") as f:
                f.write(jpeg)
        except OSError:
            return
        with self._rec_lock:
            self._gui_saved += 1
            n = self._gui_saved
        if n % 5 == 0:
            self._ui_queue.put(self._refresh_gui_rec_status)

    def _refresh_gui_rec_status(self):
        with self._rec_lock:
            n = self._gui_saved
        folder = self._rec_folder or DEFAULT_REC_DIR
        self.gui_rec_var.set(f"recording {n} frames to {folder}")

    def _stop_gui_rec(self):
        self.gui_rec = False
        with self._rec_lock:
            n, self._gui_saved = self._gui_saved, 0
        self.gui_rec_btn.configure(text="Record (GUI)", bg=GREEN)
        folder = self._rec_folder or DEFAULT_REC_DIR
        if n:
            self.gui_rec_var.set(f"Saved {n} frames to {folder}")
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

    def _query_radxa_rec(self):
        for board in BOARDS:
            self._send_board(board, "JPEGREC")

    def _toggle_prune(self):
        self.prune_var = not self.prune_var
        if self.prune_var:
            self.prune_btn.configure(text="Prune: ON", bg=GREEN)
            self._tx_queue.put("PRUNE_ON")
        else:
            self.prune_btn.configure(text="Prune: OFF", bg=RED)
            self._tx_queue.put("PRUNE_OFF")

    def _set_rec_fps_val(self, fps_str):
        self.fps_entry_var.set(fps_str)
        self._set_rec_fps()

    def _set_rec_fps(self):
        try:
            fps = float(self.fps_entry_var.get())
            if fps <= 0:
                fps = 0.1
            interval = 1.0 / fps
            self._tx_queue.put(f"SET_INTERVAL_{interval:.4f}")
            self.status_var.set(f"rec interval -> {interval:.4f}s ({fps:.1f} FPS)")
        except ValueError:
            self.status_var.set("ERR: bad FPS value")

    def _on_resp(self, board, text):
        st = self._radxa.setdefault(board, {"rec": False, "alive": False})
        for token in str(text).replace(";", " ").split():
            if token.startswith("JPEG_REC="):
                st["rec"] = token.split("=", 1)[1] == "1"
            elif token.startswith("SENDER="):
                st["alive"] = token.split("=", 1)[1] == "1"
        self._render_radxa_rec()

    def _render_radxa_rec(self):
        parts = []
        for board, v in self._radxa.items():
            if v["rec"]:
                parts.append(f"{board.upper()} recording")
            elif v["alive"]:
                parts.append(f"{board.upper()} alive")
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
        self._stream_stop.set()
        if self._sock is not None:
            try:
                self._sock.sendall(b"STOP_STREAM\n")
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self._stop_gui_rec()
        for link in self.links.values():
            if link and getattr(link, "on_resp", None):
                link.on_resp = None
        self.destroy()
