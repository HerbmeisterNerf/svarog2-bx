#!/usr/bin/env python3
"""
SVAROG ground-station GUI (Tkinter).
Pure-GUI assembly only; networking lives in subcomponents/gui_network.py.
Two panels: EBOX (172.16.18.191) and CUBESAT (192.168.78.2).
"""
import os, sys, time, datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "subcomponents"))

from gui_theme import (BG, BG2, BG3, FG, FG_DIM, ACCENT, RED, ORANGE,
                       YELLOW, TEAL, FONT, FONT_B, FONT_S)
from gui_widgets import LED, HeaterIndicator, TelemetryPanel
from gui_network import BoardConnector
from gui_video import VideoWindow


class BoardPanel(tk.Frame):
    def __init__(self, parent, name, ip, cmd_port, telem_port,
                 bw_labels=None, heaters=None):
        super().__init__(parent, bg=BG, bd=1, relief="groove")
        self.name = name
        self.bw_labels = bw_labels or {}
        self.heaters = heaters or []

        self.link = BoardConnector(name, ip, cmd_port, telem_port)
        self.link.on_telem = self._on_telem
        self.link.on_log = self._log
        self.link.on_status = self._on_status
        self.link.on_async_disconnect = self._on_async_disconnect

        self.build_compact_header(self).pack(fill="x")
        self._build_controls()
        self.after(100, self._poll_queues)

    def build_compact_header(self, parent):
        bar = tk.Frame(parent, bg=BG3, padx=6, pady=4)
        self.compact_led = LED(bar, size=10, on="#a6e3a1", off="#f38ba8")
        self.compact_led.pack(side="left", padx=(0, 4))
        self._label(bar, self.name, font=FONT_B, fg=ACCENT, bg=BG3).pack(side="left")
        return bar

    # ── widget helpers ──────────────────────────────────────────────

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

    def _btn_sm(self, parent, text, cmd, fg=FG, bg=BG3):
        return tk.Button(parent, text=text, command=cmd, font=FONT_S,
                         fg=fg, bg=bg, activebackground=FG_DIM,
                         activeforeground=FG, relief="flat", bd=0,
                         padx=5, pady=1, cursor="hand2")

    def build_connection_bar(self, parent):
        conn = tk.Frame(parent, bg=BG3, padx=6, pady=2)
        self.led = LED(conn, size=10, on="#a6e3a1", off="#f38ba8")
        self.led.pack(side="left", padx=(0, 4))
        self._label(conn, self.name, font=FONT_B, fg=ACCENT, bg=BG3).pack(side="left")
        self._label(conn, "IP", font=FONT_S).pack(side="left", padx=(6, 0))
        self.ip_var = tk.StringVar(value=self.link.default_ip)
        self._entry(conn, self.ip_var, 12).pack(side="left", padx=1)
        self._label(conn, "CMD", font=FONT_S).pack(side="left", padx=(4, 0))
        self.cmd_port_var = tk.StringVar(value=str(self.link.default_cmd))
        self._entry(conn, self.cmd_port_var, 5).pack(side="left", padx=1)
        self._label(conn, "TELEM", font=FONT_S).pack(side="left", padx=(4, 0))
        self.telem_port_var = tk.StringVar(value=str(self.link.default_telem))
        self._entry(conn, self.telem_port_var, 5).pack(side="left", padx=1)
        self.connect_btn = self._btn(conn, "Connect", self._toggle_connect,
                                     font=FONT_S, padx=5, pady=1)
        self.connect_btn.pack(side="left", padx=4)
        self.status_var = tk.StringVar(value="Disconnected")
        sl = self._label(conn, textvariable=self.status_var, fg=RED, font=FONT_S)
        sl.pack(side="left")
        self._btn_sm(conn, "STATUS", lambda: self.link.send("STATUS"),
                     bg=ACCENT, fg=BG).pack(side="left", padx=2)
        return conn

    def _build_controls(self):
        body = tk.Frame(self, bg=BG2, padx=4, pady=4)
        body.pack(fill="both", expand=True)
        ctrl = tk.Frame(body, bg=BG2)
        ctrl.pack(fill="both", expand=True)

        # ── Burnwires ──────────────────────────────────────────────
        if self.bw_labels:
            bw_f = tk.LabelFrame(ctrl, text=" Burnwires ", font=FONT_B,
                                 fg=FG, bg=BG2, bd=1, relief="groove")
            bw_f.pack(fill="x", pady=(0, 4))
            for en_name, display in self.bw_labels.items():
                row = tk.Frame(bw_f, bg=BG2)
                row.pack(fill="x", padx=4, pady=1)
                self._btn_sm(row, display,
                             lambda n=en_name: self.link.send(f"BW {n} 3000"),
                             bg=ORANGE, fg=BG).pack(side="left")

        # ── Heaters ────────────────────────────────────────────────
        if self.heaters:
            ht_f = tk.LabelFrame(ctrl, text=" Heaters ", font=FONT_B,
                                 fg=FG, bg=BG2, bd=1, relief="groove")
            ht_f.pack(fill="x", pady=(0, 4))
            self._heater_indicators = {}
            for display, en_name in self.heaters:
                row = tk.Frame(ht_f, bg=BG2)
                row.pack(fill="x", padx=4, pady=2)
                self._label(row, display, font=FONT_B).pack(side="left")
                ind = HeaterIndicator(row, width=64, height=26)
                ind.pack(side="left", padx=4)
                self._heater_indicators[en_name] = ind

        # ── Advanced toggle ────────────────────────────────────────
        self._advanced_open = False
        self._advanced_btn = tk.Button(ctrl, text="[ + ] Advanced", font=FONT_S,
                                       fg=FG_DIM, bg=BG3, relief="flat",
                                       bd=0, padx=8, cursor="hand2",
                                       command=self._toggle_advanced)
        self._advanced_btn.pack(fill="x", padx=4, pady=(0, 4))
        self._advanced_frame = tk.Frame(ctrl, bg=BG3, bd=1, relief="groove")
        self._advanced_frame.pack(fill="x", pady=(0, 4))
        self._advanced_frame.pack_forget()

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
                             lambda n=en_name: self.link.send(f"BW {n} {self.bw_ms_var.get()}")).pack(side="left", padx=2)
                self._btn_sm(r, "ON", lambda n=en_name: self.link.send(f"EN {n} 1")).pack(side="left", padx=1)
                self._btn_sm(r, "OFF", lambda n=en_name: self.link.send(f"EN {n} 0")).pack(side="left", padx=1)

        if self.heaters:
            self._label(self._advanced_frame, " Heater override ", font=FONT_S,
                        bg=BG3).pack(padx=4, pady=(4, 0))
            for display, en_name in self.heaters:
                r = tk.Frame(self._advanced_frame, bg=BG3)
                r.pack(fill="x", padx=4, pady=1)
                self._label(r, display, font=FONT_S, bg=BG3).pack(side="left")
                self._btn_sm(r, "ON", lambda n=en_name: self.link.send(f"EN {n} 1")).pack(side="left", padx=1)
                self._btn_sm(r, "OFF", lambda n=en_name: self.link.send(f"EN {n} 0")).pack(side="left", padx=1)

        # ── Motor ──────────────────────────────────────────────────
        mot = tk.LabelFrame(ctrl, text=" Motor ", font=FONT_B,
                            fg=FG, bg=BG2, bd=1, relief="groove")
        mot.pack(fill="x", pady=(0, 4))
        for lbl, var_name, default, prefix in [
            ("Mode TC0-3:", "mot_mode", "1", "MOTOR TC"),
            ("Speed T:",    "mot_speed", "0", "MOTOR T"),
            ("Current C:",  "mot_cur", "1.0", "MOTOR C"),
        ]:
            r = tk.Frame(mot, bg=BG2)
            r.pack(fill="x", padx=4, pady=1)
            self._label(r, lbl, font=FONT_S).pack(side="left")
            v = tk.StringVar(value=default)
            setattr(self, var_name, v)
            self._entry(r, v, 6).pack(side="left", padx=2)
            self._btn_sm(r, "Set",
                         lambda p=prefix, vv=v: self.link.send(f"{p}{vv.get()}")).pack(side="left", padx=2)
        mot_presets = tk.Frame(mot, bg=BG2)
        mot_presets.pack(fill="x", padx=4, pady=(2, 2))
        for preset in ("TC1", "T0", "T80", "T-80"):
            self._btn_sm(mot_presets, preset,
                         lambda p=preset: self.link.send(f"MOTOR {p}")).pack(side="left", padx=1)
        mot_btns = tk.Frame(mot, bg=BG2)
        mot_btns.pack(fill="x", padx=4, pady=(2, 2))
        self._btn_sm(mot_btns, "PING", lambda: self.link.send("MOTOR PING")).pack(side="left", padx=1)
        self._btn_sm(mot_btns, "RAW", self._raw_motor).pack(side="left", padx=1)

        # ── Command entry ──────────────────────────────────────────
        cmd_f = tk.Frame(ctrl, bg=BG2)
        cmd_f.pack(fill="x", pady=(0, 4))
        self.cmd_var = tk.StringVar()
        e = tk.Entry(cmd_f, textvariable=self.cmd_var, font=FONT,
                     bg=BG, fg=FG, insertbackground=FG, relief="flat")
        e.pack(side="left", fill="x", expand=True, ipady=3)
        e.bind("<Return>", lambda ev: self._send_cmd())
        self._btn(cmd_f, "Send", self._send_cmd).pack(side="left", padx=2)

        # ── Log ────────────────────────────────────────────────────
        log = tk.LabelFrame(ctrl, text=" Log ", font=FONT_B,
                            fg=FG, bg=BG2, bd=1, relief="groove")
        log.pack(fill="both", expand=True)
        self.resp_text = tk.Text(log, font=FONT_S, bg=BG, fg=FG,
                                 insertbackground=FG, relief="flat",
                                 state="disabled", bd=0, padx=4, pady=2, height=2)
        self.resp_text.tag_config("cmd", foreground=ACCENT)
        self.resp_text.tag_config("ok", foreground="#a6e3a1")
        self.resp_text.tag_config("err", foreground=RED)
        self.resp_text.pack(fill="both", expand=True)

    # ── advanced toggle ────────────────────────────────────────────

    def _toggle_advanced(self):
        self._advanced_open = not self._advanced_open
        if self._advanced_open:
            self._advanced_frame.pack(fill="x", pady=(0, 4), before=self._advanced_btn)
            self._advanced_btn.configure(text="[ - ] Advanced")
        else:
            self._advanced_frame.pack_forget()
            self._advanced_btn.configure(text="[ + ] Advanced")

    # ── connection (GUI mirrors BoardConnector state) ───────────────

    def _toggle_connect(self):
        self.link.toggle_connect(self.ip_var.get(),
                                 int(self.cmd_port_var.get()),
                                 int(self.telem_port_var.get()))

    def _on_status(self, connected):
        if connected:
            self.status_var.set(f"Connected  {self.ip_var.get()}")
            self.connect_btn.configure(text="Disconnect", bg=RED)
        else:
            self.status_var.set("Disconnected")
            self.connect_btn.configure(text="Connect", bg=ACCENT)
        led = getattr(self, "led", None)
        if led is not None:
            led.set(connected)
        if getattr(self, "compact_led", None):
            self.compact_led.set(connected)

    def _on_async_disconnect(self):
        self.after(0, self.link.disconnect)

    # ── commands ───────────────────────────────────────────────────

    def _send_cmd(self):
        cmd = self.cmd_var.get().strip()
        if not cmd:
            return
        self.cmd_var.set("")
        self.link.send(cmd)

    def _raw_motor(self):
        raw = simpledialog.askstring("MOTOR RAW", "Raw command:", parent=self)
        if raw:
            self.link.send(f"MOTOR RAW {raw}")

    # ── telemetry render ───────────────────────────────────────────

    def _on_telem(self, text):
        self._update_heater_indicators(text)

    def _update_heater_indicators(self, text):
        inds = getattr(self, "_heater_indicators", {})
        for line in text.split("\n"):
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            for en_name, ind in inds.items():
                if k == f"{en_name}_DUTY":
                    try:
                        ind.set_duty(float(v) / 100.0)
                    except ValueError:
                        pass
                    break

    def _log(self, text, tag=None):
        self.resp_text.configure(state="normal")
        self.resp_text.insert("end", text + "\n", tag)
        self.resp_text.see("end")
        self.resp_text.configure(state="disabled")

    def _poll_queues(self):
        self.link.poll()
        self.after(100, self._poll_queues)


# ═══════════════════════════════════════════════════════════════════════════

class TelemLogger:
    """Appends every received telemetry block to a per-GUI-startup log file."""

    def __init__(self, base_dir=None):
        base_dir = base_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(base_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(base_dir, f"telem_{stamp}.log")
        self._fh = open(self.path, "a", encoding="utf-8")

    def write(self, board, text):
        now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._fh.write(f"[{now} {board}]\n{text.rstrip()}\n\n")
        self._fh.flush()

    def close(self):
        try:
            self._fh.close()
        except Exception:
            pass


EBOX_BW     = {"BW_1": "Spinbrake"}
EBOX_HEATER = [("HEAT_1", "HEAT_1"), ("HEAT_2", "HEAT_2"),
               ("HEAT_3", "HEAT_3"), ("HEAT_4", "HEAT_4")]

CUBESAT_BW     = {"BW_2": "BW Set 1 (P2)", "BW_4": "BW Set 2 (P4)"}
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

        self._logger = TelemLogger()

        pw = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        pw.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        # Pane 0: EBOX Telemetry
        self.ebox_telem = self._make_telem_pane(pw, "EBOX Telemetry")
        # Pane 1: CUBESAT Telemetry
        self.cubesat_telem = self._make_telem_pane(pw, "CUBESAT Telemetry")
        # Pane 2: EBOX Controls
        self.ebox = BoardPanel(pw, "EBOX", "172.16.18.191", 8006, 8005,
                               bw_labels=EBOX_BW, heaters=EBOX_HEATER)
        self.ebox.link.on_telem = self._update_ebox_telem
        pw.add(self.ebox, weight=1)
        # Pane 3: CUBESAT Controls
        self.cubesat = BoardPanel(pw, "CUBESAT", "172.16.18.191", 8016, 8015,
                                  bw_labels=CUBESAT_BW, heaters=CUBESAT_HEATER)
        self.cubesat.link.on_telem = self._update_cubesat_telem
        pw.add(self.cubesat, weight=1)

        # ── Top bar: connections + trans period ───────────────────
        top = tk.Frame(root, bg=BG3, padx=4, pady=2)
        top.grid(row=0, column=0, sticky="ew")
        self.ebox.build_connection_bar(top).pack(side="left")

        tmid = tk.Frame(top, bg=BG3)
        tmid.pack(side="left", expand=True, fill="x", padx=8)
        tk.Button(tmid, text="CAMERA", font=FONT_B,
                  fg=BG, bg=TEAL, relief="flat", bd=0,
                  padx=10, cursor="hand2",
                  command=self._open_camera).pack(side="left", padx=(0, 8))
        tk.Label(tmid, text="Retransmit period (s):", font=FONT_S,
                 fg=FG, bg=BG3).pack(side="left")
        self._trans_var = tk.StringVar(value="2.0")
        e = tk.Entry(tmid, textvariable=self._trans_var, width=6,
                     font=FONT, bg=BG, fg=FG, insertbackground=FG,
                     relief="flat", bd=2)
        e.pack(side="left", padx=2)
        tk.Button(tmid, text="Set", font=FONT_S,
                  fg=BG, bg=ACCENT, relief="flat", bd=0,
                  padx=6, cursor="hand2", command=self._set_trans_period).pack(side="left", padx=2)

        self.cubesat.build_connection_bar(top).pack(side="right")

    def _make_telem_pane(self, pw, title, graph_height=80):
        pane = TelemetryPanel(pw, title, graph_height=graph_height)
        pw.add(pane, weight=1)
        return pane

    # ── telemetry formatting ───────────────────────────────────────

    def _update_ebox_telem(self, text):
        self._update_telem_widget(self.ebox_telem, text)
        self._logger.write("EBOX", text)
        self.ebox._update_heater_indicators(text)

    def _update_cubesat_telem(self, text):
        self._update_telem_widget(self.cubesat_telem, text)
        self._logger.write("CUBESAT", text)
        self.cubesat._update_heater_indicators(text)

    def _update_telem_widget(self, widget, text):
        widget.update_telem(text)

    def _set_trans_period(self):
        val = self._trans_var.get().strip()
        cmd = f"SET_TRANS_PERIOD {val}"
        for bp in (self.ebox, self.cubesat):
            if bp.link.connected:
                bp.link.send(cmd)

    def _open_camera(self):
        win = getattr(self, "_cam_win", None)
        if win is not None and win.winfo_exists():
            win.lift()
            win.focus_force()
            return
        self._cam_win = VideoWindow(self.root, links={
            "ebox": self.ebox.link,
            "cubesat": self.cubesat.link,
        })


if __name__ == "__main__":
    root = tk.Tk()
    app = SvarogGUI(root)
    root.mainloop()