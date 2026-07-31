#!/usr/bin/env python3
"""
SVAROG ground-station GUI (Tkinter).
Two panels: EBOX (172.16.18.191) and CUBESAT (192.168.78.2).
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import socket, threading, queue

BG      = "#1e1e2e"
BG2     = "#282a3a"
BG3     = "#313244"
FG      = "#cdd6f4"
FG_DIM  = "#6c7086"
ACCENT  = "#89b4fa"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
YELLOW  = "#f9e2af"
ORANGE  = "#fab387"
TEAL    = "#94e2d5"
BORDER  = "#45475a"
FONT    = ("Courier", 10)
FONT_B  = ("Courier", 10, "bold")
FONT_H  = ("Courier", 12, "bold")
FONT_S  = ("Courier", 9)


class LED(tk.Canvas):
    def __init__(self, parent, size=10, off="#45475a", on="#a6e3a1", **kw):
        super().__init__(parent, width=size, height=size, highlightthickness=0,
                         bg=BG2, **kw)
        self._on, self._off, self._sz = on, off, size
        self.set(False)

    def set(self, state):
        c = self._on if state else self._off
        self.delete("all")
        self.create_oval(1, 1, self._sz - 1, self._sz - 1, fill=c, outline="")


class HeaterIndicator(tk.Canvas):
    """Small colored box showing heater duty cycle (0-100%)."""
    def __init__(self, parent, size=16, **kw):
        super().__init__(parent, width=size, height=size, highlightthickness=0,
                         bg=BG2, **kw)
        self._sz = size
        self._duty = 0.0
        self.set_duty(0.0)

    def set_duty(self, duty):
        self._duty = max(0.0, min(1.0, duty))
        self.delete("all")
        if self._duty <= 0.0:
            color = "#45475a"
        elif self._duty < 0.33:
            color = "#89b4fa"   # blue = low
        elif self._duty < 0.66:
            color = "#fab387"   # orange = medium
        else:
            color = "#f38ba8"   # red = high
        self.create_rectangle(1, 1, self._sz - 1, self._sz - 1,
                              fill=color, outline=BORDER)


class Collapsible(tk.Frame):
    """Frame with a (+) button that shows/hides extra content."""
    def __init__(self, parent, label, **kw):
        super().__init__(parent, bg=BG2, **kw)
        self._open = False
        self._btn = tk.Button(self, text=f"+ {label}", font=FONT_S,
                              fg=FG_DIM, bg=BG2, activebackground=BG3,
                              activeforeground=FG, relief="flat", bd=0,
                              padx=4, pady=1, cursor="hand2",
                              command=self._toggle)
        self._btn.pack(anchor="w")
        self._content = tk.Frame(self, bg=BG2)

    def _toggle(self):
        self._open = not self._open
        if self._open:
            self._content.pack(fill="x", padx=4, pady=(0, 2))
            self._btn.configure(text=f"- {self._btn.cget('text')[2:]}")
        else:
            self._content.pack_forget()
            self._btn.configure(text=f"+ {self._btn.cget('text')[2:]}")

    @property
    def content(self):
        return self._content


class BoardPanel(tk.Frame):
    def __init__(self, parent, name, ip, cmd_port, telem_port,
                 peripherals, bw_labels=None, heaters=None, has_sensors=True):
        super().__init__(parent, bg=BG, bd=1, relief="groove")
        self.name = name
        self.default_ip = ip
        self.default_cmd = cmd_port
        self.default_telem = telem_port
        self.peripherals = peripherals         # [(display, en_name), ...]
        self.bw_labels = bw_labels or {}       # en_name -> display label
        self.heaters = heaters or []           # [(display, en_name), ...]

        self.cmd_sock = None
        self.telem_sock = None
        self.connected = False
        self.resp_queue = queue.Queue()
        self.telem_queue = queue.Queue()
        self._cmd_lock = threading.Lock()
        self.on_telem = None  # callback(telem_snapshot_text)

        self._build_controls()
        self._poll_queues()

    def _label(self, parent, text=None, **kw):
        kw.setdefault("font", FONT)
        kw.setdefault("fg", FG)
        kw.setdefault("bg", BG2)
        if text is not None:
            kw["text"] = text
        return tk.Label(parent, **kw)

    def _entry(self, parent, var, width=8):
        return tk.Entry(parent, textvariable=var, width=width, font=FONT,
                        bg=BG, fg=FG, insertbackground=FG, relief="flat", bd=2)

    def _btn(self, parent, text, cmd, fg=BG, bg=ACCENT, **kw):
        kw.setdefault("font", FONT_B)
        kw.setdefault("padx", 8)
        kw.setdefault("pady", 2)
        return tk.Button(parent, text=text, command=cmd,
                         fg=fg, bg=bg, activebackground=ACCENT,
                         activeforeground=FG, relief="flat", bd=0,
                         cursor="hand2", **kw)

    def _btn_sm(self, parent, text, cmd, fg=FG, bg=BORDER):
        return tk.Button(parent, text=text, command=cmd, font=FONT_S,
                         fg=fg, bg=bg, activebackground=FG_DIM,
                         activeforeground=FG, relief="flat", bd=0,
                         padx=5, pady=1, cursor="hand2")

    def build_connection_bar(self, parent):
        """Create connection controls in parent Frame, return the Frame."""
        conn = tk.Frame(parent, bg=BG3, padx=6, pady=2)
        self.led = LED(conn, size=10, on=GREEN, off=RED)
        self.led.pack(side="left", padx=(0, 4))
        self._label(conn, self.name, font=FONT_B, fg=ACCENT, bg=BG3).pack(side="left")
        self._label(conn, "IP", font=FONT_S).pack(side="left", padx=(6, 0))
        self.ip_var = tk.StringVar(value=self.default_ip)
        self._entry(conn, self.ip_var, 12).pack(side="left", padx=1)
        self._label(conn, "CMD", font=FONT_S).pack(side="left", padx=(4, 0))
        self.cmd_port_var = tk.StringVar(value=str(self.default_cmd))
        self._entry(conn, self.cmd_port_var, 5).pack(side="left", padx=1)
        self._label(conn, "TELEM", font=FONT_S).pack(side="left", padx=(4, 0))
        self.telem_port_var = tk.StringVar(value=str(self.default_telem))
        self._entry(conn, self.telem_port_var, 5).pack(side="left", padx=1)
        self.connect_btn = self._btn(conn, "Connect", self._toggle_connect,
                                     font=FONT_S, padx=5, pady=1)
        self.connect_btn.pack(side="left", padx=4)
        self.status_var = tk.StringVar(value="Disconnected")
        sl = self._label(conn, textvariable=self.status_var, fg=RED, font=FONT_S)
        sl.pack(side="left")
        self._btn_sm(conn, "STATUS", lambda: self._send("STATUS"),
                     bg=ACCENT, fg=BG).pack(side="left", padx=2)
        return conn

    def _build_controls(self):

        body = tk.Frame(self, bg=BG2, padx=4, pady=4)
        body.pack(fill="both", expand=True)

        # Controls fill the body
        ctrl = tk.Frame(body, bg=BG2)
        ctrl.pack(fill="both", expand=True)

        # ── Burnwires ──────────────────────────────────────────────────

        if self.bw_labels:
            bw_f = tk.LabelFrame(ctrl, text=" Burnwires ", font=FONT_B,
                                 fg=FG, bg=BG2, bd=1, relief="groove")
            bw_f.pack(fill="x", pady=(0, 4))
            for en_name, display in self.bw_labels.items():
                row = tk.Frame(bw_f, bg=BG2)
                row.pack(fill="x", padx=4, pady=1)
                self._btn_sm(row, display,
                             lambda n=en_name: self._send(f"BW {n} 3000"),
                             bg=ORANGE, fg=BG).pack(side="left")

        # ── Heaters ────────────────────────────────────────────────────

        if self.heaters:
            ht_f = tk.LabelFrame(ctrl, text=" Heaters ", font=FONT_B,
                                 fg=FG, bg=BG2, bd=1, relief="groove")
            ht_f.pack(fill="x", pady=(0, 4))
            self._heater_indicators = {}
            for display, en_name in self.heaters:
                row = tk.Frame(ht_f, bg=BG2)
                row.pack(fill="x", padx=4, pady=1)
                self._label(row, display, font=FONT_S).pack(side="left")
                ind = HeaterIndicator(row, size=14)
                ind.pack(side="left", padx=4)
                self._heater_indicators[en_name] = ind

        # ── Advanced toggle (BW + Heater ON/OFF) ─────────────────────

        self._advanced_open = False
        self._advanced_btn = tk.Button(ctrl, text="[ + ] Advanced", font=FONT_S,
                                       fg=FG_DIM, bg=BG3, relief="flat",
                                       bd=0, padx=8, cursor="hand2",
                                       command=self._toggle_advanced)
        self._advanced_btn.pack(fill="x", padx=4, pady=(0, 4))

        self._advanced_frame = tk.Frame(ctrl, bg=BG3, bd=1, relief="groove")
        self._advanced_frame.pack(fill="x", pady=(0, 4))
        self._advanced_frame.pack_forget()

        # BW advanced
        if self.bw_labels:
            self._label(self._advanced_frame, " Burnwire options ", font=FONT_S,
                        bg=BG3).pack(padx=4, pady=(4, 0))
            ms_row = tk.Frame(self._advanced_frame, bg=BG3)
            ms_row.pack(fill="x", padx=4, pady=1)
            self._label(ms_row, "Custom ms:", font=FONT_S, bg=BG3).pack(side="left")
            self.bw_ms_var = tk.StringVar(value="1500")
            self._entry(ms_row, self.bw_ms_var, 5).pack(side="left", padx=2)
            for en_name, display in self.bw_labels.items():
                r = tk.Frame(self._advanced_frame, bg=BG3)
                r.pack(fill="x", padx=4, pady=1)
                self._label(r, display, font=FONT_S, bg=BG3).pack(side="left")
                self._btn_sm(r, "Pulse",
                             lambda n=en_name: self._send(f"BW {n} {self.bw_ms_var.get()}")).pack(side="left", padx=2)
                self._btn_sm(r, "ON", lambda n=en_name: self._send(f"EN {n} 1")).pack(side="left", padx=1)
                self._btn_sm(r, "OFF", lambda n=en_name: self._send(f"EN {n} 0")).pack(side="left", padx=1)

        # Heater advanced
        if self.heaters:
            self._label(self._advanced_frame, " Heater override ", font=FONT_S,
                        bg=BG3).pack(padx=4, pady=(4, 0))
            for display, en_name in self.heaters:
                r = tk.Frame(self._advanced_frame, bg=BG3)
                r.pack(fill="x", padx=4, pady=1)
                self._label(r, display, font=FONT_S, bg=BG3).pack(side="left")
                self._btn_sm(r, "ON", lambda n=en_name: self._send(f"EN {n} 1")).pack(side="left", padx=1)
                self._btn_sm(r, "OFF", lambda n=en_name: self._send(f"EN {n} 0")).pack(side="left", padx=1)

        # ── Motor ──────────────────────────────────────────────────────

        mot_f = tk.LabelFrame(ctrl, text=" Motor ", font=FONT_B,
                              fg=FG, bg=BG2, bd=1, relief="groove")
        mot_f.pack(fill="x", pady=(0, 4))

        for lbl, var_name, default, prefix in [
            ("Mode TC0-3:", "mot_mode", "1", "MOTOR TC"),
            ("Speed T:",    "mot_speed", "0", "MOTOR T"),
            ("Current C:",  "mot_cur", "1.0", "MOTOR C"),
        ]:
            r = tk.Frame(mot_f, bg=BG2)
            r.pack(fill="x", padx=4, pady=1)
            self._label(r, lbl, font=FONT_S).pack(side="left")
            v = tk.StringVar(value=default)
            setattr(self, var_name, v)
            self._entry(r, v, 6).pack(side="left", padx=2)
            self._btn_sm(r, "Set",
                         lambda p=prefix, vv=v: self._send(f"{p}{vv.get()}")).pack(side="left", padx=2)

        mot_btns = tk.Frame(mot_f, bg=BG2)
        mot_btns.pack(fill="x", padx=4, pady=(2, 2))
        self._btn_sm(mot_btns, "PING", lambda: self._send("MOTOR PING")).pack(side="left", padx=1)
        self._btn_sm(mot_btns, "RAW", self._raw_motor).pack(side="left", padx=1)

        # ── Command entry ──────────────────────────────────────────────

        cmd_f = tk.Frame(ctrl, bg=BG2)
        cmd_f.pack(fill="x", pady=(0, 4))
        self.cmd_var = tk.StringVar()
        e = tk.Entry(cmd_f, textvariable=self.cmd_var, font=FONT,
                     bg=BG, fg=FG, insertbackground=FG, relief="flat")
        e.pack(side="left", fill="x", expand=True, ipady=3)
        e.bind("<Return>", lambda ev: self._send_cmd())
        self._btn(cmd_f, "Send", self._send_cmd).pack(side="left", padx=2)

        # ── Log ────────────────────────────────────────────────────────

        resp_f = tk.LabelFrame(ctrl, text=" Log ", font=FONT_B,
                               fg=FG, bg=BG2, bd=1, relief="groove")
        resp_f.pack(fill="both", expand=True)
        self.resp_text = tk.Text(resp_f, font=FONT_S, bg=BG, fg=FG,
                                 insertbackground=FG, relief="flat",
                                 state="disabled", bd=0, padx=4, pady=2,
                                 height=5)
        self.resp_text.tag_config("cmd", foreground=ACCENT)
        self.resp_text.tag_config("ok", foreground=GREEN)
        self.resp_text.tag_config("err", foreground=RED)
        self.resp_text.pack(fill="both", expand=True)

    # ── advanced panel toggle ──────────────────────────────────────────

    def _toggle_advanced(self):
        self._advanced_open = not self._advanced_open
        if self._advanced_open:
            self._advanced_frame.pack(fill="x", pady=(0, 4), before=self._advanced_btn)
            self._advanced_btn.configure(text="[ - ] Advanced")
        else:
            self._advanced_frame.pack_forget()
            self._advanced_btn.configure(text="[ + ] Advanced")

    # ── telemetry ──────────────────────────────────────────────────────

    def _update_heater_indicators(self, text):
        for line in text.split("\n"):
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            ind = getattr(self, "_heater_indicators", {}).get(k)
            if ind is not None:
                try:
                    ind.set_duty(float(v) / 100.0)
                except ValueError:
                    pass

    # ── connection ─────────────────────────────────────────────────────

    def _toggle_connect(self):
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        ip = self.ip_var.get()
        cmd_port = int(self.cmd_port_var.get())
        telem_port = int(self.telem_port_var.get())
        try:
            self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.cmd_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.cmd_sock.settimeout(5)
            self.cmd_sock.connect((ip, cmd_port))
        except Exception as e:
            messagebox.showerror(f"{self.name} CMD", str(e))
            self.cmd_sock = None
            return
        try:
            self.telem_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.telem_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.telem_sock.settimeout(5)
            self.telem_sock.connect((ip, telem_port))
        except Exception:
            self.telem_sock = None
        self.connected = True
        self.status_var.set(f"Connected  {ip}")
        self.connect_btn.configure(text="Disconnect", bg=RED)
        self.led.set(True)
        self._log("[connected]", "ok")
        if self.telem_sock:
            threading.Thread(target=self._recv_telem_loop, daemon=True).start()

    def _disconnect(self):
        self.connected = False
        for s in (self.cmd_sock, self.telem_sock):
            if s:
                try: s.close()
                except Exception: pass
        self.cmd_sock = None
        self.telem_sock = None
        self.status_var.set("Disconnected")
        self.connect_btn.configure(text="Connect", bg=ACCENT)
        self.led.set(False)
        self._log("[disconnected]", "err")

    # ── commands ───────────────────────────────────────────────────────

    def _send(self, cmd):
        if not self.connected or not self.cmd_sock:
            self._log("[not connected]", "err")
            return
        self._log(f"> {cmd}", "cmd")
        threading.Thread(target=self._send_and_recv, args=(cmd,), daemon=True).start()

    def _send_cmd(self):
        cmd = self.cmd_var.get().strip()
        if not cmd: return
        self.cmd_var.set("")
        self._send(cmd)

    def _raw_motor(self):
        raw = simpledialog.askstring("MOTOR RAW", "Raw command:", parent=self)
        if raw:
            self._send(f"MOTOR RAW {raw}")

    def _send_and_recv(self, cmd):
        with self._cmd_lock:
            try:
                self.cmd_sock.sendall((cmd + "\n").encode("utf-8"))
                buf = b""
                while True:
                    chunk = self.cmd_sock.recv(4096)
                    if not chunk: break
                    buf += chunk
                    if b"\n" in buf: break
                self.resp_queue.put(buf.decode("utf-8").strip())
            except Exception as e:
                self.resp_queue.put(f"ERR: {e}")

    def _recv_telem_loop(self):
        try:
            buf = b""
            while self.connected:
                chunk = self.telem_sock.recv(4096)
                if not chunk: break
                buf += chunk
                while b"\n" in buf:
                    block, buf = buf.split(b"\n", 1)
                    self.telem_queue.put(block.decode("utf-8").strip())
        except Exception: pass
        if self.connected:
            self.after(0, self._disconnect)

    # ── polling ────────────────────────────────────────────────────────

    def _poll_queues(self):
        while not self.resp_queue.empty():
            self._log(self.resp_queue.get_nowait())
        # Aggregate individual telemetry lines into a complete snapshot
        lines = []
        while not self.telem_queue.empty():
            line = self.telem_queue.get_nowait()
            if not line:
                if lines:
                    text = "\n".join(lines)
                    if self.on_telem:
                        self.on_telem(text)
                    self._update_heater_indicators(text)
                    lines = []
            else:
                lines.append(line)
        if lines:
            text = "\n".join(lines)
            if self.on_telem:
                self.on_telem(text)
            self._update_heater_indicators(text)
        self.after(100, self._poll_queues)

    def _log(self, text, tag=None):
        self.resp_text.configure(state="normal")
        if tag:
            self.resp_text.insert("end", text + "\n", tag)
        else:
            self.resp_text.insert("end", text + "\n")
        self.resp_text.see("end")
        self.resp_text.configure(state="disabled")


# ═══════════════════════════════════════════════════════════════════════════

EBOX_BW     = {"BW_1": "Spinbrake"}
EBOX_HEATER = [("HEAT_1", "HEAT_1"), ("HEAT_2", "HEAT_2"),
               ("HEAT_3", "HEAT_3"), ("HEAT_4", "HEAT_4")]

CUBESAT_BW     = {"BW_1": "BW Set 1 (P2)", "BW_2": "BW Set 2 (P4)"}
CUBESAT_HEATER = [("HEAT_1", "HEAT_1")]


class SvarogGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SVAROG Ground Station")
        self.root.geometry("1400x850")
        self.root.minsize(1000, 600)
        self.root.configure(bg=BG)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # ── Resizable panes ───────────────────────────────────────
        pw = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        pw.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        # Pane 0: EBOX Telemetry
        ebox_tf = tk.Frame(pw, bg=BG2, bd=1, relief="groove")
        pw.add(ebox_tf, weight=1)
        hdr1 = tk.Frame(ebox_tf, bg=BG2)
        hdr1.pack(fill="x")
        tk.Label(hdr1, text=" EBOX Telemetry ", font=FONT_B,
                 fg=ACCENT, bg=BG2).pack(side="left")
        self.ebox_telem = tk.Text(ebox_tf, font=FONT, bg=BG, fg=FG,
                                   insertbackground=FG, relief="flat",
                                   state="disabled", wrap="word", bd=0,
                                   padx=4, pady=2)
        self.ebox_telem.tag_config("section", foreground=YELLOW, font=FONT_B)
        self.ebox_telem.tag_config("key", foreground=TEAL)
        self.ebox_telem.tag_config("val", foreground=FG)
        self.ebox_telem.pack(fill="both", expand=True)

        # Pane 1: CUBESAT Telemetry
        cubesat_tf = tk.Frame(pw, bg=BG2, bd=1, relief="groove")
        pw.add(cubesat_tf, weight=1)
        hdr2 = tk.Frame(cubesat_tf, bg=BG2)
        hdr2.pack(fill="x")
        tk.Label(hdr2, text=" CUBESAT Telemetry ", font=FONT_B,
                 fg=ACCENT, bg=BG2).pack(side="left")
        self.cubesat_telem = tk.Text(cubesat_tf, font=FONT, bg=BG, fg=FG,
                                      insertbackground=FG, relief="flat",
                                      state="disabled", wrap="word", bd=0,
                                      padx=4, pady=2)
        self.cubesat_telem.tag_config("section", foreground=YELLOW, font=FONT_B)
        self.cubesat_telem.tag_config("key", foreground=TEAL)
        self.cubesat_telem.tag_config("val", foreground=FG)
        self.cubesat_telem.pack(fill="both", expand=True)

        # Pane 2: EBOX Controls
        self.ebox = BoardPanel(pw, "EBOX", "172.16.18.191", 8006, 8005,
                               peripherals=[],
                               bw_labels=EBOX_BW,
                               heaters=EBOX_HEATER,
                               has_sensors=True)
        self.ebox.on_telem = self._update_ebox_telem
        pw.add(self.ebox, weight=1)

        # Pane 3: CUBESAT Controls
        self.cubesat = BoardPanel(pw, "CUBESAT", "192.168.78.2", 8006, 8005,
                                  peripherals=[],
                                  bw_labels=CUBESAT_BW,
                                  heaters=CUBESAT_HEATER,
                                  has_sensors=False)
        self.cubesat.on_telem = self._update_cubesat_telem
        pw.add(self.cubesat, weight=1)

        # ── Top bar: connections + trans period ───────────────────
        top = tk.Frame(root, bg=BG3, padx=4, pady=2)
        top.grid(row=0, column=0, sticky="ew")

        self.ebox.build_connection_bar(top).pack(side="left")

        tmid = tk.Frame(top, bg=BG3)
        tmid.pack(side="left", expand=True, fill="x", padx=8)
        lbl = tk.Label(tmid, text="Retransmit period (s):", font=FONT_S,
                        fg=FG, bg=BG3)
        lbl.pack(side="left")
        self._trans_var = tk.StringVar(value="2.0")
        e = tk.Entry(tmid, textvariable=self._trans_var, width=6,
                      font=FONT, bg=BG, fg=FG, insertbackground=FG,
                      relief="flat", bd=2)
        e.pack(side="left", padx=2)
        btn = tk.Button(tmid, text="Set", font=FONT_S,
                        fg=BG, bg=ACCENT, relief="flat", bd=0,
                        padx=6, cursor="hand2", command=self._set_trans_period)
        btn.pack(side="left", padx=2)

        self.cubesat.build_connection_bar(top).pack(side="right")

    # ── helpers ─────────────────────────────────────────────────────

    def _update_telem_widget(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        sections = {}
        for line in text.split("\n"):
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k.startswith("TS"):
                sec = "Timestamp"
            elif k.startswith("V_SENSE") or k.startswith("ADC_V"):
                sec = "PDU Power"
            elif k.startswith("THERMAL"):
                sec = "Thermal"
            elif k.startswith("PG_"):
                sec = "Power Good"
            elif k.startswith("FLT_"):
                sec = "Faults"
            else:
                sec = "Other"
            sections.setdefault(sec, []).append((k, v))
        for sec_name, items in sections.items():
            widget.insert("end", f" {sec_name}\n", "section")
            for k, v in items:
                try:
                    fv = float(v)
                    v_str = f"{fv:.3f}" if abs(fv) < 100 else f"{fv:.1f}"
                except ValueError:
                    v_str = v
                widget.insert("end", f"  {k:<26s}", "key")
                widget.insert("end", f" {v_str}\n", "val")
        widget.configure(state="disabled")

    def _update_ebox_telem(self, text):
        self._update_telem_widget(self.ebox_telem, text)

    def _update_cubesat_telem(self, text):
        self._update_telem_widget(self.cubesat_telem, text)

    def _set_trans_period(self):
        val = self._trans_var.get().strip()
        cmd = f"SET_TRANS_PERIOD {val}"
        # Send to both panels if connected
        for bp in (self.ebox, self.cubesat):
            if bp.connected:
                bp._send(cmd)


if __name__ == "__main__":
    root = tk.Tk()
    app = SvarogGUI(root)
    root.mainloop()
