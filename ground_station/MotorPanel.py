"""Embeddable FOC motor-control panel for the Svarog ground station.

Ports the rich rspro-bldc-foc GUI (open/closed-loop, velocity/position, Hall
dial, current/torque strip chart, live limits, STOP) into a widget that drops
into the ground-station center column.

Transport is flight-compatible: **commands go out as UDP Space Packet
telecommands** (``SpacePacketComms.send_ebox_tc(tc_foc_*(...))``) and
**telemetry comes in from the parsed TM broadcast** via ``CommonData.motor_state``
(filled by ``LiveUpdatesTelemetry``). No serial link, no TCP — works over the
lossy antenna and on the bench alike. The refresh loop only reads shared state,
so a dropped TM just freezes the readouts until the next broadcast.
"""

import math
import time
import tkinter as tk
from collections import deque

from CommonData import CommonData
from SpacePacketComms import (
    SpacePacketComms,
    tc_foc_mode, tc_foc_target, tc_foc_limits, tc_foc_align, tc_foc_zero,
    FOC_MODE_OPEN, FOC_MODE_VELOCITY, FOC_MODE_POSITION,
)

# ── palette (matches TCPClientApp) ───────────────────────────────────────────
PANEL   = "#232323"
HEADER  = "#2b2b2b"
ACCENT  = "#1e88e5"
TEXT    = "#e0e0e0"
TEXT_DIM = "#888888"
TEXT_VAL = "#d4d4d4"
COL_ON  = "#43a047"
COL_OFF = "#e53935"
COL_WARN = "#f57c00"
GREEN_SPOOL = "#43a047"
_SANS = "Segoe UI"
_MONO = "Consolas"

# ── motor constants (from rspro firmware / gearbox) ──────────────────────────
HIST = 200
KT = 0.047              # Nm/A
GEAR_RATIO = 688        # motor turns : spool turns
CUR_WARN = 0.8          # A  → "high torque"
CUR_MAX = 2.3           # A  peak (bar full-scale)
STALL_CMD = 1.0         # rad/s commanded above which the shaft should move
STALL_FRAC = 0.4        # stalled if |vel| < this fraction of target ...
CUR_STALL = 0.3         # ... while drawing more than this current
STALE_S = 12.0          # TM older than this ⇒ readouts greyed (≈2 missed 5 s TMs)


class MotorPanel:
    """FOC control panel bound to a parent tk frame. Not a window of its own."""

    def __init__(self, parent):
        self.parent = parent
        self.mode = tk.StringVar(value="vel")
        self.target = 0.0
        self._open = False
        self.vel_ema = 0.0
        self.cur_ema = 0.0
        self.hist_cur = deque(maxlen=HIST)
        self.hist_trq = deque(maxlen=HIST)
        self._last_tm_t = 0.0
        self._last_send = 0.0
        self.vlim = tk.DoubleVar(value=6.0)
        self.clim = tk.DoubleVar(value=1.0)
        self.vlim_closed = 6.0
        self.limits_locked = True
        self._running = True

        self._build(parent)
        self.parent.after(80, self._refresh)

    # ---------------------------------------------------------------- build UI
    def _build(self, parent):
        self._section(parent, "FOC Motor  ·  EBOX")

        body = tk.Frame(parent, bg=PANEL)
        body.pack(fill=tk.X, padx=10, pady=(2, 6))

        # --- mode row ---
        mrow = tk.Frame(body, bg=PANEL)
        mrow.pack(anchor="w", pady=(0, 4))
        for txt, val in (("Velocity", "vel"), ("Position", "pos"), ("Open-loop", "open")):
            tk.Radiobutton(mrow, text=txt, variable=self.mode, value=val,
                           command=self.set_mode, font=(_SANS, 8),
                           bg=PANEL, fg=TEXT, selectcolor="#555555",
                           activebackground=PANEL, activeforeground=TEXT,
                           relief=tk.FLAT).pack(side=tk.LEFT, padx=(0, 4))
        self._mkbtn(mrow, "Align FOC", self.align, bg="#2d2d2d").pack(side=tk.LEFT, padx=(8, 0))
        self._mkbtn(mrow, "Set 0", self.set_zero, bg="#2d2d2d").pack(side=tk.LEFT, padx=(4, 0))

        # --- target slider ---
        self.tgt_lbl = tk.Label(body, text="Target: 0", font=(_SANS, 9, "bold"),
                                bg=PANEL, fg=TEXT, anchor="w")
        self.tgt_lbl.pack(anchor="w")
        self.slider = tk.Scale(body, from_=-130, to=130, resolution=1,
                               orient="horizontal", length=300, showvalue=False,
                               command=self.on_slider, bg=PANEL, fg=TEXT,
                               troughcolor="#2d2d2d", highlightthickness=0,
                               activebackground=ACCENT)
        self.slider.pack(fill=tk.X)

        erow = tk.Frame(body, bg=PANEL)
        erow.pack(anchor="w", pady=4)
        self.entry = tk.Entry(erow, width=7, bg="#2d2d2d", fg=TEXT,
                              insertbackground=TEXT, relief=tk.FLAT)
        self.entry.pack(side=tk.LEFT)
        self._mkbtn(erow, "Set", self.on_entry).pack(side=tk.LEFT, padx=3)
        self._mkbtn(erow, "− step", lambda: self.nudge(-1)).pack(side=tk.LEFT, padx=3)
        self._mkbtn(erow, "+ step", lambda: self.nudge(1)).pack(side=tk.LEFT)
        self.stop_btn = tk.Button(erow, text="STOP", bg=COL_OFF, fg="white",
                                  font=(_SANS, 10, "bold"), relief=tk.FLAT,
                                  command=self.stop, padx=12)
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0))

        # --- live limits ---
        lim = tk.Frame(body, bg=PANEL)
        lim.pack(fill=tk.X, pady=(4, 0))
        tk.Label(lim, text="V (speed)", font=(_SANS, 8), bg=PANEL,
                 fg=TEXT_DIM).grid(row=0, column=0, sticky="w")
        self.vscale = tk.Scale(lim, from_=0.5, to=7.0, resolution=0.5,
                               orient="horizontal", variable=self.vlim, showvalue=False,
                               length=120, command=self.on_lim, state="disabled",
                               bg=PANEL, fg=TEXT, troughcolor="#2d2d2d",
                               highlightthickness=0)
        self.vscale.grid(row=0, column=1, padx=4)
        self.vlim_lbl = tk.Label(lim, text="6.0 V", width=6, font=(_MONO, 8),
                                 bg=PANEL, fg=TEXT_VAL)
        self.vlim_lbl.grid(row=0, column=2)
        tk.Label(lim, text="C (torque)", font=(_SANS, 8), bg=PANEL,
                 fg=TEXT_DIM).grid(row=1, column=0, sticky="w")
        self.cscale = tk.Scale(lim, from_=0.3, to=2.3, resolution=0.1,
                               orient="horizontal", variable=self.clim, showvalue=False,
                               length=120, command=self.on_lim, state="disabled",
                               bg=PANEL, fg=TEXT, troughcolor="#2d2d2d",
                               highlightthickness=0)
        self.cscale.grid(row=1, column=1, padx=4)
        self.clim_lbl = tk.Label(lim, text="1.0 A", width=6, font=(_MONO, 8),
                                 bg=PANEL, fg=TEXT_VAL)
        self.clim_lbl.grid(row=1, column=2)
        self.lock_btn = self._mkbtn(lim, "Unlock", self.toggle_lock, bg="#2d2d2d")
        self.lock_btn.grid(row=0, column=3, rowspan=2, padx=(8, 0))

        # --- telemetry: dial + readouts ---
        tel = tk.Frame(body, bg=PANEL)
        tel.pack(fill=tk.X, pady=(6, 0))
        self.dial = tk.Canvas(tel, width=120, height=120, bg=PANEL,
                              highlightthickness=0)
        self.dial.grid(row=0, column=0, rowspan=7, padx=(0, 10))
        self.vals = {}
        rows = [("pos", "Hall pos"), ("vel", "Velocity"), ("cur", "Current"),
                ("trq", "Torque"), ("hall", "Hall bits"),
                ("spool_pos", f"Spool (÷{GEAR_RATIO})"),
                ("spool_rpm", f"Spool rpm")]
        for i, (key, label) in enumerate(rows):
            tk.Label(tel, text=label + ":", font=(_SANS, 8), bg=PANEL,
                     fg=TEXT_DIM, anchor="e").grid(row=i, column=1, sticky="e", padx=3)
            fg = GREEN_SPOOL if key.startswith("spool") else TEXT_VAL
            v = tk.Label(tel, text="—", font=(_MONO, 9, "bold"), bg=PANEL,
                         fg=fg, anchor="w")
            v.grid(row=i, column=2, sticky="w")
            self.vals[key] = v

        # --- lamps ---
        st = tk.Frame(body, bg=PANEL)
        st.pack(anchor="w", pady=(6, 0))
        self.stall_lamp = tk.Label(st, text="  STALL  ", bg="#3a3a3a", fg="#777",
                                   font=(_SANS, 9, "bold"), padx=5, pady=2)
        self.stall_lamp.pack(side=tk.LEFT, padx=(0, 6))
        self.torque_lamp = tk.Label(st, text="  HIGH TORQUE  ", bg="#3a3a3a",
                                    fg="#777", font=(_SANS, 9, "bold"), padx=5, pady=2)
        self.torque_lamp.pack(side=tk.LEFT)
        self.link_lbl = tk.Label(st, text="no telemetry", bg=PANEL, fg=COL_WARN,
                                 font=(_SANS, 8))
        self.link_lbl.pack(side=tk.LEFT, padx=(8, 0))

        # --- strip chart ---
        self.graph = tk.Canvas(body, width=430, height=120, bg="#111",
                              highlightthickness=0)
        self.graph.pack(fill=tk.X, pady=(6, 0))

    def _section(self, parent, text):
        f = tk.Frame(parent, bg=HEADER)
        f.pack(fill=tk.X, pady=(8, 2))
        tk.Frame(f, width=3, bg=ACCENT).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(f, text=text, font=(_SANS, 8, "bold"), bg=HEADER, fg=TEXT,
                 padx=8, pady=4).pack(side=tk.LEFT)

    @staticmethod
    def _mkbtn(parent, text, command, bg="#363636"):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=TEXT,
                         font=(_SANS, 8), activebackground=bg, activeforeground=TEXT,
                         relief=tk.FLAT, bd=0, padx=8, pady=3, cursor="hand2")

    # ---------------------------------------------------------------- commands
    @staticmethod
    def _tc(data):
        try:
            SpacePacketComms.send_ebox_tc(data)
        except Exception as e:
            print(f"MotorPanel TC send failed: {e}")

    def set_mode(self):
        m = self.mode.get()
        if m == "open":
            if not self._open:
                self.vlim_closed = self.vlim.get()
                self.vlim.set(2.5)
            self._open = True
            self.slider.config(from_=-80, to=80, resolution=1)
            self._tc(tc_foc_mode(FOC_MODE_OPEN))
        else:
            if self._open:
                self.vlim.set(self.vlim_closed)
            self._open = False
            if m == "vel":
                self.slider.config(from_=-130, to=130, resolution=1)
                self._tc(tc_foc_mode(FOC_MODE_VELOCITY))
            else:  # position — slider is spool revolutions
                self.slider.config(from_=-20, to=20, resolution=0.05)
                self._tc(tc_foc_mode(FOC_MODE_POSITION))
        self._send_limits()
        self.slider.set(0)
        self.send_target(0)

    def send_target(self, val):
        if self.mode.get() == "pos":
            motor_rad = val * 2 * math.pi * GEAR_RATIO
            self.target = motor_rad
            self.tgt_lbl.config(text=f"Target: {val:g} spool rev")
            self._tc(tc_foc_target(motor_rad))
        else:
            self.target = val
            self.tgt_lbl.config(text=f"Target: {val:g}")
            self._tc(tc_foc_target(val))

    def on_slider(self, _):
        now = time.time()
        if now - self._last_send > 0.12:      # throttle TC rate
            self._last_send = now
            self.send_target(self.slider.get())

    def on_entry(self):
        try:
            v = float(self.entry.get())
            self.slider.set(v)
            self.send_target(v)
        except ValueError:
            pass

    def nudge(self, sign):
        step = 2.0 if self.mode.get() in ("vel", "open") else 0.25
        v = round(self.slider.get() + sign * step, 2)
        self.slider.set(v)
        self.send_target(v)

    def stop(self):
        self.slider.set(0)
        self.send_target(0)

    def set_zero(self):
        self._tc(tc_foc_zero())
        self.slider.set(0)
        self.tgt_lbl.config(text="Target: 0")

    def align(self):
        """On-demand Hall alignment (initFOC) — needed after power-up before
        closed-loop velocity/position modes work on the boot-silent firmware."""
        self._tc(tc_foc_align())

    def on_lim(self, _):
        self.vlim_lbl.config(text=f"{self.vlim.get():.1f} V")
        self.clim_lbl.config(text=f"{self.clim.get():.1f} A")
        self._send_limits()

    def _send_limits(self):
        self.vlim_lbl.config(text=f"{self.vlim.get():.1f} V")
        self.clim_lbl.config(text=f"{self.clim.get():.1f} A")
        self._tc(tc_foc_limits(self.vlim.get(), self.clim.get()))

    def toggle_lock(self):
        if self.limits_locked:
            from tkinter import messagebox
            if not messagebox.askyesno(
                    "Unlock limits",
                    "These set motor voltage (speed) and current (torque).\n\n"
                    "Raising current can OVERHEAT the motor (0.6 A continuous, "
                    "2.3 A peak). Raise only briefly and watch the current.\n\n"
                    "Unlock the sliders?"):
                return
            self.limits_locked = False
            self.vscale.config(state="normal")
            self.cscale.config(state="normal")
            self.lock_btn.config(text="Lock")
        else:
            self.limits_locked = True
            self.vscale.config(state="disabled")
            self.cscale.config(state="disabled")
            self.lock_btn.config(text="Unlock")

    # ---------------------------------------------------------------- refresh
    def _refresh(self):
        if not self._running:
            return
        s = CommonData.motor_state
        stale = (time.time() - s.get("t", 0.0)) > STALE_S
        ang = s.get("angle", 0.0); vel = s.get("vel", 0.0)
        cur = s.get("cur", 0.0); trq = s.get("trq", 0.0)

        a = 0.2
        self.vel_ema = a * vel + (1 - a) * self.vel_ema
        self.cur_ema = a * cur + (1 - a) * self.cur_ema
        rpm = self.vel_ema * 9.5493
        deg = math.degrees(ang) % 360
        self.vals["pos"].config(text=f"{ang:7.3f} rad ({deg:5.1f}°)")
        self.vals["vel"].config(text=f"{self.vel_ema:6.1f} rad/s ({rpm:5.0f} rpm)")
        self.vals["cur"].config(text=f"{self.cur_ema:6.3f} A")
        self.vals["trq"].config(text=f"{self.cur_ema * KT * 1000:6.2f} mNm")
        self.vals["hall"].config(text=str(s.get("hall", "---")))
        spool_rev = ang / (2 * math.pi * GEAR_RATIO)
        spool_deg = math.degrees(ang / GEAR_RATIO) % 360
        self.vals["spool_pos"].config(text=f"{spool_rev:6.2f} rev ({spool_deg:4.0f}°)")
        self.vals["spool_rpm"].config(text=f"{rpm / GEAR_RATIO:6.2f} rpm")
        self.draw_dial(ang)

        # Append to the strip chart only when a fresh TM sample arrived, so the
        # graph reflects the real TM cadence rather than the 80 ms UI tick.
        if s.get("t", 0.0) != self._last_tm_t:
            self._last_tm_t = s.get("t", 0.0)
            self.hist_cur.append(cur)
            self.hist_trq.append(trq * 1000.0)
        self.draw_graph()

        # stall: commanded to move + drawing current, but shaft barely turning
        stalled = (self.mode.get() == "vel" and abs(self.target) >= STALL_CMD
                   and abs(vel) < STALL_FRAC * abs(self.target)
                   and abs(self.cur_ema) > CUR_STALL)
        self.lamp(self.stall_lamp, stalled and not stale, COL_OFF)
        self.lamp(self.torque_lamp, abs(cur) > CUR_WARN and not stale, COL_WARN)

        if stale:
            self.link_lbl.config(text="no telemetry", fg=COL_WARN)
        else:
            self.link_lbl.config(text="live", fg=COL_ON)

        self.parent.after(80, self._refresh)

    def lamp(self, w, on, color):
        w.config(bg=color, fg="white") if on else w.config(bg="#3a3a3a", fg="#777")

    def draw_dial(self, ang):
        c = self.dial
        c.delete("all")
        cx, cy, r = 60, 60, 50
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#666", width=2)
        for k in range(12):
            aa = math.radians(k * 30)
            c.create_line(cx + (r - 5) * math.sin(aa), cy - (r - 5) * math.cos(aa),
                          cx + r * math.sin(aa), cy - r * math.cos(aa), fill="#555")
        c.create_line(cx, cy, cx + (r - 10) * math.sin(ang), cy - (r - 10) * math.cos(ang),
                      fill=ACCENT, width=3)
        c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=ACCENT, outline="")

    def draw_graph(self):
        g = self.graph
        g.delete("all")
        W = int(g["width"]); H = int(g["height"])
        mid = H / 2
        g.create_line(0, mid, W, mid, fill="#333")
        g.create_text(4, mid - 8, anchor="w", fill="#555", text="0", font=(_MONO, 7))
        if len(self.hist_cur) < 2:
            return
        peak = max(0.3, max(abs(v) for v in self.hist_cur))
        g.create_text(4, 8, anchor="w", fill="#555", text=f"+{peak:.2f}A", font=(_MONO, 7))
        g.create_text(4, H - 8, anchor="w", fill="#555", text=f"-{peak:.2f}A", font=(_MONO, 7))

        def poly(series, color):
            n = len(series)
            pts = []
            for i, v in enumerate(series):
                x = W - (n - 1 - i) * (W / (HIST - 1))
                y = mid - (v / peak) * (mid - 6)
                y = max(2, min(H - 2, y))
                pts += [x, y]
            if len(pts) >= 4:
                g.create_line(*pts, fill=color, width=1.5)

        poly(self.hist_cur, "#3498db")                            # current, blue
        poly([t / (KT * 1000) for t in self.hist_trq], "#e67e22")  # torque, orange
        g.create_text(W - 6, 8, anchor="e", fill="#3498db", text="current", font=(_MONO, 8))
        g.create_text(W - 6, 22, anchor="e", fill="#e67e22", text="torque", font=(_MONO, 8))

    def close(self):
        """Stop the refresh loop and command the motor to a safe stop."""
        self._running = False
        try:
            self._tc(tc_foc_target(0))
        except Exception:
            pass
