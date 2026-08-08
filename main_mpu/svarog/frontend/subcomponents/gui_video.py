#!/usr/bin/env python3
"""
Camera feed popup: runs the RTSP gst-launch pipeline from gstreamer_recv_cmd.txt,
embeds the preview in the window via fdsink + PIL/Tk, and records the stream to
a local .mp4 through a second gst-launch process (x264enc + mp4mux).

Right side: per-camera panel (CAM 1-4 + CUBESAT) controlling the on-board
streaming/recording service via the EBOX/CUBESAT board connectors
(CAM START/STOP/REC/STOPREC commands, see board/subcomponents/camstream.py).
"""
import os, re, signal, subprocess, threading, time
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk

from gui_theme import (BG, BG2, BG3, FG, FG_DIM, ACCENT, GREEN, RED, TEAL,
                       FONT, FONT_B, FONT_S)

SAROG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GSTREAMER_CMD_FILE = os.path.join(SAROG_DIR, "gstreamer_recv_cmd.txt")
DEFAULT_REC_DIR = os.path.join(SAROG_DIR, "recordings")

PREVIEW_W, PREVIEW_H = 640, 480
FRAME_SIZE = PREVIEW_W * PREVIEW_H * 3

CAM_SOURCES = [
    ("cam1",    "CAM 1",    "rtsp://172.16.18.191:1234/cam", "ebox"),
    ("cam2",    "CAM 2",    "rtsp://172.16.18.191:1235/cam", "ebox"),
    ("cam3",    "CAM 3",    "rtsp://172.16.18.191:1236/cam", "ebox"),
    ("cam4",    "CAM 4",    "rtsp://172.16.18.191:1237/cam", "ebox"),
    ("cubesat", "CUBESAT",  "rtsp://172.16.18.191:1238/cam", "cubesat"),
]


def load_gstreamer_cmd():
    try:
        with open(GSTREAMER_CMD_FILE, "r") as f:
            return f.read().strip()
    except OSError:
        return ""


def rtsp_location_from_cmd(cmd):
    m = re.search(r"location=(\S+)", cmd)
    return m.group(1) if m else "rtsp://172.16.18.191:1234/cam"


class VideoWindow(tk.Toplevel):
    """Popup showing the ebox camera feed; start/stop local recording."""

    def __init__(self, root, links=None):
        super().__init__(root)
        self.title("Camera Feed")
        self.geometry("1080x680")
        self.minsize(900, 580)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.links = links or {}          # {"ebox": BoardConnector, "cubesat": BoardConnector}
        self.proc = None
        self.record_proc = None
        self.recording = False
        self._latest = None
        self._photo = None
        self._photo_src = None
        self._frame_arrivals = []
        self._last_frame_t = None
        self.fps_var = tk.StringVar(value="FPS: --")
        self.stale_var = tk.StringVar(value="")
        self.record_folder = DEFAULT_REC_DIR
        os.makedirs(self.record_folder, exist_ok=True)

        self.loc_var = tk.StringVar(value=rtsp_location_from_cmd(load_gstreamer_cmd()))
        self.status_var = tk.StringVar(value="Starting preview...")
        self.rec_status_var = tk.StringVar(value="")
        self.cam_state = {}               # cam_id -> {"stream": bool, "rec": bool}

        self._build_ui()
        self._attach_link_responses()
        self._start_preview()
        self.after(40, self._tick)
        self.after(2000, self._poll_cam_status)

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

        bar = tk.Frame(left, bg=BG)
        bar.pack(fill="x")
        self._label(bar, "RTSP:", bg=BG).pack(side="left")
        e = tk.Entry(bar, textvariable=self.loc_var, font=FONT,
                     bg=BG, fg=FG, insertbackground=FG, relief="flat", bd=2)
        e.pack(side="left", fill="x", expand=True, padx=4)
        self._btn(bar, "Apply", self._start_preview).pack(side="left")

        rec_bar = tk.Frame(left, bg=BG)
        rec_bar.pack(fill="x")
        self.rec_btn = self._btn(rec_bar, "Start Recording", self._toggle_record,
                                 bg=GREEN, font=FONT_B, padx=10, pady=3)
        self.rec_btn.pack(side="left")
        self._label(rec_bar, textvariable=self.rec_status_var, fg=FG_DIM,
                    bg=BG, anchor="w", font=FONT_S).pack(side="left",
                                                         fill="x", expand=True, padx=6)

        folder_bar = tk.Frame(left, bg=BG)
        folder_bar.pack(fill="x")
        self._label(folder_bar, "Save to:", bg=BG).pack(side="left")
        self.folder_var = tk.StringVar(value=self.record_folder)
        fe = tk.Entry(folder_bar, textvariable=self.folder_var, font=FONT_S,
                      bg=BG, fg=FG, insertbackground=FG, relief="flat", bd=2)
        fe.pack(side="left", fill="x", expand=True, padx=4)
        self._btn(folder_bar, "Browse", self._browse_folder, font=FONT_S,
                  padx=6).pack(side="left")

        status_frame = tk.Frame(left, bg=BG)
        status_frame.pack(fill="x")
        self._label(status_frame, textvariable=self.status_var, fg=FG_DIM,
                    bg=BG, anchor="w", font=FONT_S).pack(side="left", fill="x", expand=True)
        self._label(status_frame, textvariable=self.stale_var, fg=RED,
                    bg=BG, anchor="e", font=FONT_S).pack(side="right")
        self._label(status_frame, textvariable=self.fps_var, fg=GREEN,
                    bg=BG, anchor="e", font=FONT_B).pack(side="right", padx=(0, 10))

        self._build_cam_panel(body)

    def _build_cam_panel(self, parent):
        panel = tk.Frame(parent, bg=BG2, bd=1, relief="groove", width=330)
        panel.pack(side="right", fill="y", padx=(8, 0))
        panel.pack_propagate(False)

        self._label(panel, " Cameras ", font=FONT_B, fg=ACCENT,
                    bg=BG2).pack(anchor="w", padx=6, pady=(6, 2))

        g = tk.Frame(panel, bg=BG2)
        g.pack(fill="x", padx=6, pady=2)
        self._btn(g, "Start Streaming (all)", lambda: self._cam_all("START"),
                  font=FONT_S, bg=TEAL).pack(side="left", fill="x", expand=True)
        self._btn(g, "Stop", lambda: self._cam_all("STOP"),
                  font=FONT_S).pack(side="left", fill="x", expand=True, padx=(4, 0))

        g2 = tk.Frame(panel, bg=BG2)
        g2.pack(fill="x", padx=6, pady=2)
        self._btn(g2, "Record All", lambda: self._cam_all("REC"),
                  font=FONT_S, bg=GREEN).pack(side="left", fill="x", expand=True)
        self._btn(g2, "Stop Rec All", lambda: self._cam_all("STOPREC"),
                  font=FONT_S).pack(side="left", fill="x", expand=True, padx=(4, 0))

        self._label(panel, "─" * 36, fg=FG_DIM, bg=BG2, font=FONT_S).pack(pady=(2, 2))

        self.cam_rows = {}
        for cid, display, url, board in CAM_SOURCES:
            row = tk.Frame(panel, bg=BG3, bd=1, relief="groove")
            row.pack(fill="x", padx=6, pady=2)

            top = tk.Frame(row, bg=BG3)
            top.pack(fill="x", padx=4, pady=(3, 0))
            self._label(top, display, font=FONT_B, bg=BG3).pack(side="left")
            st = self._label(top, "stop", fg=RED, bg=BG3, font=FONT_S)
            st.pack(side="right")
            rc = self._label(top, "", fg=RED, bg=BG3, font=FONT_S)
            rc.pack(side="right", padx=(0, 6))

            self._label(row, url, fg=FG_DIM, bg=BG3, font=FONT_S).pack(anchor="w", padx=4)

            btns = tk.Frame(row, bg=BG3)
            btns.pack(fill="x", padx=4, pady=(0, 3))
            rec_btn = self._btn(btns, "Start Record", lambda c=cid: self._toggle_cam_rec(c),
                                bg=GREEN, font=FONT_S)
            rec_btn.pack(side="left", fill="x", expand=True)
            self._btn(btns, "Preview", lambda u=url: self._preview_url(u),
                      font=FONT_S).pack(
                          side="left", fill="x", expand=True, padx=(4, 0))

            self.cam_rows[cid] = {"st": st, "rc": rc, "btn": rec_btn,
                                  "url": url, "board": board}

        self.cam_link_note = tk.StringVar(
            value="Commands go to EBOX :8006 / CUBESAT :8016")
        self._label(panel, textvariable=self.cam_link_note, fg=FG_DIM,
                    bg=BG2, font=FONT_S, anchor="w", wraplength=310,
                    justify="left").pack(side="bottom", anchor="w", padx=6, pady=4)

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

    # ── gst-launch pipelines ───────────────────────────────────────

    def _preview_cmd(self):
        return [
            "gst-launch-1.0", "-q",
            "rtspsrc", "latency=0", "protocols=tcp", "buffer-mode=none",
            "drop-on-latency=true", f"location={self.loc_var.get().strip()}",
            "!", "rtpjpegdepay", "!", "jpegparse", "!", "avdec_mjpeg",
            "!", "queue", "max-size-buffers=1", "max-size-bytes=0",
            "max-size-time=0", "leaky=downstream",
            "!", "videoconvert", "!", "videoscale",
            "!", f"video/x-raw,format=RGB,width={PREVIEW_W},height={PREVIEW_H}",
            "!", "fdsink", "fd=1", "sync=false",
        ]

    def _record_cmd(self, path):
        return [
            "gst-launch-1.0",
            "rtspsrc", "latency=0", "protocols=tcp",
            f"location={self.loc_var.get().strip()}",
            "!", "rtpjpegdepay", "!", "jpegparse", "!", "avdec_mjpeg",
            "!", "queue",
            "!", "videoconvert",
            "!", "x264enc", "tune=zerolatency", "bitrate=4000", "key-int-max=5",
            "!", "mp4mux", "streamable=true", "fragment-duration=1000",
            "!", "filesink", f"location={path}",
        ]

    def _spawn(self, cmd, use_stdout):
        return subprocess.Popen(cmd,
                                stdout=subprocess.PIPE if use_stdout else subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)

    def _start_preview(self):
        self._kill_proc(self.proc)
        self.proc = None
        self._latest = None
        self.status_var.set("Starting preview...")
        try:
            self.proc = self._spawn(self._preview_cmd(), use_stdout=True)
        except OSError as e:
            self.status_var.set(f"Failed to launch gst-launch: {e}")
            return
        threading.Thread(target=self._reader, daemon=True).start()

    def _preview_url(self, url):
        self.loc_var.set(url)
        self._start_preview()

    def _reader(self):
        proc = self.proc
        if not proc:
            return
        buf = b""
        while proc is self.proc and proc.poll() is None:
            try:
                chunk = proc.stdout.read(FRAME_SIZE)
            except (ValueError, OSError):
                break
            if not chunk:
                break
            buf += chunk
            while len(buf) >= FRAME_SIZE:
                self._latest = buf[:FRAME_SIZE]
                buf = buf[FRAME_SIZE:]

    def _tick(self):
        if self._latest is not None:
            now = time.monotonic()
            if self._latest is not self._photo_src:
                self._photo_src = self._latest
                self._last_frame_t = now
                self._frame_arrivals.append(now)
                self._frame_arrivals = [t for t in self._frame_arrivals if now - t <= 2.0]
            self._update_fps(now)
            try:
                img = Image.frombytes("RGB", (PREVIEW_W, PREVIEW_H), self._latest)
                self._photo = ImageTk.PhotoImage(img)
                self.video_lbl.configure(image=self._photo)
            except Exception:
                pass
        if self.proc and self.proc.poll() is not None:
            self.status_var.set(f"Preview stopped (exit {self.proc.returncode})")
            self._latest = None
            self._photo_src = None
            self._frame_arrivals = []
            self._last_frame_t = None
            self.fps_var.set("FPS: --")
            self.stale_var.set("waiting for frames...")
            self.proc = None
        if self.recording and self.record_proc and self.record_proc.poll() is not None:
            self.recording = False
            self.record_proc = None
            self.rec_btn.configure(text="Start Recording", bg=GREEN)
            self.rec_status_var.set("Recording ended unexpectedly")
        self.after(40, self._tick)

    def _update_fps(self, now):
        if self._frame_arrivals:
            fps = len(self._frame_arrivals) / 2.0
        else:
            fps = 0.0
        self.fps_var.set(f"FPS: {fps:.1f}")
        if self._last_frame_t is not None:
            age = now - self._last_frame_t
            self.stale_var.set(f"last frame {age:.1f}s ago")
        else:
            self.stale_var.set("waiting for frames...")

    # ── local recording (GUI side) ──────────────────────────────────

    def _toggle_record(self):
        if self.recording:
            self._stop_record()
        else:
            self._start_record()

    def _start_record(self):
        folder = self.folder_var.get().strip() or self.record_folder
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"rec_{time.strftime('%Y%m%d_%H%M%S')}.mp4")
        try:
            self.record_proc = self._spawn(self._record_cmd(path), use_stdout=False)
        except OSError as e:
            self.rec_status_var.set(f"Failed: {e}")
            return
        self.recording = True
        self.rec_btn.configure(text="Stop Recording", bg=RED)
        self.rec_status_var.set(f"Saving to {path}")

    def _stop_record(self):
        self._kill_proc(self.record_proc)
        self.record_proc = None
        self.recording = False
        self.rec_btn.configure(text="Start Recording", bg=GREEN)
        if not self.rec_status_var.get().startswith("Saving"):
            self.rec_status_var.set(self.rec_status_var.get())
        else:
            self.rec_status_var.set(self.rec_status_var.get() + " (stopped)")

    # ── on-board camera control (via board connectors) ──────────────

    def _attach_link_responses(self):
        for board, link in self.links.items():
            if link:
                link.on_resp = self._on_resp

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

    def _send_cam(self, board, cmd):
        link = self._link(board)
        if link is None:
            return
        link.send(cmd)

    def _cam_all(self, action):
        self._send_cam("ebox", f"CAM {action} ALL")
        self._send_cam("cubesat", f"CAM {action} ALL")
        if action == "STOP":
            self._kill_proc(self.proc)
            self.proc = None
            self._latest = None
            self._photo_src = None
            self._frame_arrivals = []
            self._last_frame_t = None
            self.fps_var.set("FPS: --")
            self.stale_var.set("waiting for frames...")
            self.status_var.set("Streams stopped")

    def _toggle_cam_rec(self, cid):
        row = self.cam_rows[cid]
        rec = self.cam_state.get(cid, {}).get("rec", False)
        action = "STOPREC" if rec else "REC"
        self._send_cam(row["board"], f"CAM {action} {cid}")
        self.cam_state.setdefault(cid, {})["rec"] = not rec
        self._render_cam(cid, optimistic=True)

    def _poll_cam_status(self):
        for board in ("ebox", "cubesat"):
            link = self.links.get(board)
            if link and link.connected:
                link.send("CAM STATUS")
        self.after(4000, self._poll_cam_status)

    def _on_resp(self, text):
        for part in str(text).split(";"):
            if "=" not in part:
                continue
            cid, val = part.split("=", 1)
            cid = cid.strip().lower()
            if cid not in self.cam_rows:
                continue
            vals = val.split(",")
            try:
                stream = int(vals[0]) == 1
                rec = int(vals[1]) == 1 if len(vals) > 1 else False
            except ValueError:
                continue
            self.cam_state.setdefault(cid, {}).update({"stream": stream, "rec": rec})
            self._render_cam(cid)

    def _render_cam(self, cid, optimistic=False):
        row = self.cam_rows[cid]
        st = self.cam_state.get(cid, {})
        streaming = bool(st.get("stream"))
        rec = bool(st.get("rec"))
        row["st"].config(text="stream" if streaming else "stop",
                         fg=GREEN if streaming else RED)
        if rec:
            row["rc"].config(text="● REC", fg=RED)
            row["btn"].config(text="Stop Record", bg=RED)
        else:
            row["rc"].config(text="")
            row["btn"].config(text="Start Record", bg=GREEN)
        if not optimistic:
            row["btn"].config(state="normal" if streaming or rec else "disabled")

    # ── misc ───────────────────────────────────────────────────────

    def _browse_folder(self):
        d = filedialog.askdirectory(initialdir=self.folder_var.get() or self.record_folder,
                                    parent=self, title="Recording folder")
        if d:
            self.folder_var.set(d)

    @staticmethod
    def _kill_proc(proc):
        if not proc or proc.poll() is not None:
            return
        try:
            proc.send_signal(signal.SIGINT)
        except (OSError, ValueError):
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

    def _on_close(self):
        self._kill_proc(self.record_proc)
        self._kill_proc(self.proc)
        self.record_proc = None
        self.proc = None
        for link in self.links.values():
            if link and getattr(link, "on_resp", None) is self._on_resp:
                link.on_resp = None
        self.destroy()
