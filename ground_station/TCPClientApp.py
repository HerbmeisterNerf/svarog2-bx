import tkinter as tk
from tkinter import messagebox
import pandas as pd

try:
    from PIL import Image, ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

from CommonData import CommonData
from PortCommunication import PortCommunication
from UDPTelemReader import UDPTelemReader
from WatchTelem import WatchTelem
from WatchTelemCubeSat import WatchTelemCubeSat
from WatchCamera import WatchCamera
from SpacePacketComms import (
    SpacePacketComms,
    tc_heater_toggle, tc_bw_pulse,
    tc_mot_enable, tc_mot_disable,
    tc_cam_record, tc_cam_snapshot,
    tc_fw_enable, tc_fw_speed,
    tc_deploy_arm, tc_deploy_fire,
)

# ── Palette ──────────────────────────────────────────────────────────────────
BG        = "#1a1a1a"
PANEL     = "#232323"
HEADER    = "#2b2b2b"
BORDER    = "#3d3d3d"
TELEM_ROW = "#2a2a2a"

ACCENT_EB = "#1e88e5"   # EBOX  — blue
ACCENT_CS = "#9c27b0"   # CubeSat — purple

TEXT      = "#e0e0e0"
TEXT_DIM  = "#888888"
TEXT_VAL  = "#d4d4d4"

COL_ON    = "#43a047"   # green
COL_OFF   = "#e53935"   # red
COL_WARN  = "#f57c00"   # orange

# ── Fonts ─────────────────────────────────────────────────────────────────────
_SANS = "Segoe UI"
_MONO = "Consolas"

F_SM   = (_SANS, 8)
F_SMB  = (_SANS, 8,  "bold")
F_MED  = (_SANS, 9)
F_MEDB = (_SANS, 9,  "bold")
F_VAL  = (_MONO, 8)

EBOX_FIELDS = 35
CS_FIELDS   = 32


def _sep(parent, color=BORDER, pady=4):
    tk.Frame(parent, height=1, bg=color).pack(fill=tk.X, padx=6, pady=pady)


def _section(parent, text, accent=ACCENT_EB):
    f = tk.Frame(parent, bg=HEADER)
    f.pack(fill=tk.X, pady=(8, 2))
    tk.Frame(f, width=3, bg=accent).pack(side=tk.LEFT, fill=tk.Y)
    tk.Label(f, text=text, font=F_SMB, bg=HEADER, fg=TEXT,
             padx=8, pady=4).pack(side=tk.LEFT)


def _btn(parent, text, command, bg="#363636", fg=TEXT, font=F_SM, **kw):
    return tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, font=font,
        activebackground=bg, activeforeground=fg,
        relief=tk.FLAT, bd=0, padx=8, pady=4,
        cursor="hand2", **kw
    )


class TCPClientApp:

    def __init__(self, master):
        CommonData.telemetryParameters = EBOX_FIELDS

        self.master = master
        master.protocol("WM_DELETE_WINDOW", self.exitfunc)
        master.title("BX36 SVAROG2 GROUND SEGMENT")
        master.configure(bg=BG)
        master.resizable(True, True)

        self.tableLabels    = []
        self.tableLabels_cs = []
        self.SaveCam        = tk.IntVar(value=0)
        self._ebox_actions  = False
        self._cs_actions    = False
        self._motor_on      = False
        self._deploy_armed  = False
        self._fw_speed_var  = tk.IntVar(value=0)
        self._cam_btn_refs  = []

        self._load_data_formats()

        outer = tk.Frame(master, bg=BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._left = tk.Frame(outer, bg=PANEL, width=295,
                              highlightthickness=1, highlightbackground=BORDER)
        self._left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4))
        self._left.pack_propagate(False)

        self._center = tk.Frame(outer, bg=PANEL,
                                highlightthickness=1, highlightbackground=BORDER)
        self._center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        self._right = tk.Frame(outer, bg=PANEL, width=315,
                               highlightthickness=1, highlightbackground=BORDER)
        self._right.pack(side=tk.LEFT, fill=tk.Y, padx=(4, 0))
        self._right.pack_propagate(False)

        self._build_ebox_panel(self._left)
        self._build_center_panel(self._center)
        self._build_cs_panel(self._right)

        self._start_threads()
        self._poll_motor_speed()

    # ── data formats ─────────────────────────────────────────────────────────

    def _load_data_formats(self):
        self._df_ebox = pd.read_csv("dataFormat.csv", header=None)
        for i in range(EBOX_FIELDS):
            for j in range(4):
                self._df_ebox.iloc[i, j + 1] = float(self._df_ebox.iloc[i, j + 1])

        self._df_cs = pd.read_csv("dataFormat_cs.csv", header=None)
        for i in range(CS_FIELDS):
            for j in range(4):
                self._df_cs.iloc[i, j + 1] = float(self._df_cs.iloc[i, j + 1])

    # ================================================================ EBOX PANEL

    def _build_ebox_panel(self, parent):
        _section(parent, "EBOX", ACCENT_EB)

        conn = tk.Frame(parent, bg=PANEL)
        conn.pack(fill=tk.X, padx=8, pady=(2, 4))

        tk.Label(conn, text="IP", font=F_SM, bg=PANEL, fg=TEXT_DIM).pack(side=tk.LEFT)
        self._ebox_ip = tk.StringVar(value=CommonData.server_name)
        tk.Entry(conn, textvariable=self._ebox_ip, width=13, font=F_VAL,
                 bg="#2d2d2d", fg=TEXT, insertbackground=TEXT,
                 relief=tk.FLAT, highlightthickness=1,
                 highlightbackground=BORDER).pack(side=tk.LEFT, padx=(4, 6))

        self._eb_conn_btn = _btn(conn, "Connect", self._ebox_connect)
        self._eb_conn_btn.pack(side=tk.LEFT, padx=2)

        self._eb_disc_btn = _btn(conn, "Disconnect", self._ebox_disconnect,
                                 state=tk.DISABLED)
        self._eb_disc_btn.pack(side=tk.LEFT, padx=2)

        self._eb_dot = tk.Label(conn, text="●", font=(_SANS, 13),
                                fg=COL_OFF, bg=PANEL)
        self._eb_dot.pack(side=tk.LEFT, padx=6)

        tog = tk.Frame(parent, bg=PANEL)
        tog.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._eb_telem_btn = _btn(tog, "  Telem OFF  ", self._toggle_ebox_telem,
                                  bg=COL_OFF, fg="white", state=tk.DISABLED)
        self._eb_telem_btn.pack(side=tk.LEFT)

        _sep(parent)

        tbl = tk.Frame(parent, bg=PANEL)
        tbl.pack(fill=tk.X, padx=4)
        self._create_data_table(tbl, self._df_ebox, EBOX_FIELDS,
                                self.tableLabels, cols_per_group=18)

        _sep(parent)

        _section(parent, "EBOX Controls", ACCENT_EB)

        ctrl = tk.Frame(parent, bg=PANEL)
        ctrl.pack(fill=tk.X, padx=8, pady=(2, 6))

        tk.Label(ctrl, text="Actions", font=F_SM, bg=PANEL,
                 fg=TEXT_DIM).grid(row=0, column=0, sticky="w", pady=2)
        self._eb_act_chk = tk.Checkbutton(
            ctrl, command=self._toggle_ebox_actions,
            bg=PANEL, fg=TEXT, selectcolor="#555555",
            activebackground=PANEL, activeforeground=TEXT, relief=tk.FLAT)
        self._eb_act_chk.grid(row=0, column=1, padx=(0, 6))

        self._eb_h_btns = []
        for i, lbl in enumerate(["H1", "H2", "H3", "H4"]):
            b = _btn(ctrl, lbl,
                     lambda n=i + 1: SpacePacketComms.send_ebox_tc(tc_heater_toggle(n)),
                     bg="#333333", state=tk.DISABLED)
            b.grid(row=0, column=2 + i, padx=2, pady=2)
            self._eb_h_btns.append(b)
        for i, lbl in enumerate(["H5", "H6"]):
            b = _btn(ctrl, lbl,
                     lambda n=i + 5: SpacePacketComms.send_ebox_tc(tc_heater_toggle(n)),
                     bg="#333333", state=tk.DISABLED)
            b.grid(row=1, column=2 + i, padx=2, pady=2)
            self._eb_h_btns.append(b)

        self._eb_bw1 = _btn(ctrl, "BW1",
                            lambda: SpacePacketComms.send_ebox_tc(tc_bw_pulse(1)),
                            bg="#333333", state=tk.DISABLED)
        self._eb_bw1.grid(row=1, column=4, padx=2, pady=2)

        self._eb_bw2 = _btn(ctrl, "BW2",
                            lambda: SpacePacketComms.send_ebox_tc(tc_bw_pulse(2)),
                            bg="#333333", state=tk.DISABLED)
        self._eb_bw2.grid(row=1, column=5, padx=2, pady=2)

        self._eb_action_widgets = self._eb_h_btns + [self._eb_bw1, self._eb_bw2]

    def _create_data_table(self, parent, df, n_fields, label_list, cols_per_group):
        label_list.clear()
        for i in range(n_fields):
            grp = i // cols_per_group
            row = i %  cols_per_group
            tk.Label(parent, text=df.iloc[i, 0], font=F_VAL,
                     bg=PANEL, fg=TEXT_DIM, anchor="e"
                     ).grid(row=row, column=grp * 2, padx=(2, 0), pady=1, sticky="e")
            val = tk.Label(parent, text="0.0", font=F_VAL,
                           fg=TEXT_VAL, bg=TELEM_ROW, width=6, anchor="e", padx=3)
            val.grid(row=row, column=grp * 2 + 1, padx=(0, 6), pady=1, sticky="w")
            label_list.append(val)

    # ============================================================== CENTER PANEL

    def _build_center_panel(self, parent):
        _section(parent, "Camera Feed", ACCENT_EB)

        cam_row = tk.Frame(parent, bg=PANEL)
        cam_row.pack(fill=tk.X, padx=8, pady=(4, 2))

        cam_defs = [
            (1, "CAM1\nEB·RZ1"), (2, "CAM2\nEB·RZ2"),
            (3, "CAM3\nEB·RZ3"), (4, "CAM4\nEB·RZ4"),
            (5, "CAM5\nCS·RZ1"), (6, "CAM6\nCS·RZ2"),
        ]
        self._cam_btn_refs = []
        for cam_id, label in cam_defs:
            b = tk.Button(cam_row, text=label, font=(_SANS, 7), width=6, height=2,
                          bg="#2d2d2d", fg=TEXT_DIM,
                          activebackground=ACCENT_EB, activeforeground="white",
                          relief=tk.FLAT, bd=0, padx=2, cursor="hand2",
                          command=lambda c=cam_id: self._select_camera(c))
            b.pack(side=tk.LEFT, padx=2)
            self._cam_btn_refs.append((b, cam_id))

        self._select_camera(1)

        cam_ctrl = tk.Frame(parent, bg=PANEL)
        cam_ctrl.pack(fill=tk.X, padx=8, pady=(0, 4))

        self._cam_btn = _btn(cam_ctrl, "Camera OFF", self._toggle_camera,
                             bg=COL_OFF, fg="white", state=tk.DISABLED)
        self._cam_btn.pack(side=tk.LEFT)

        self._cam_snap_btn = _btn(cam_ctrl, "Snapshot", self._snapshot,
                                  state=tk.DISABLED)
        self._cam_snap_btn.pack(side=tk.LEFT, padx=8)

        _sep(parent, pady=2)

        self._timestamp_var = tk.StringVar(value="—")
        tk.Label(parent, textvariable=self._timestamp_var, font=F_SM,
                 bg=PANEL, fg=TEXT_DIM).pack(anchor="w", padx=10)

        self._img_frame = tk.Frame(parent, bg="#0d0d0d",
                                   highlightthickness=1, highlightbackground=BORDER)
        self._img_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self._img_label = tk.Label(self._img_frame, bg="#0d0d0d",
                                   text="[ No camera feed ]",
                                   font=(_SANS, 10, "italic"), fg="#404040")
        self._img_label.pack(fill=tk.BOTH, expand=True)
        self._img_label.image = None

        _sep(parent, pady=6)

        _section(parent, "Spool Motor  ·  EBOX", ACCENT_EB)

        mot_frame = tk.Frame(parent, bg=PANEL)
        mot_frame.pack(fill=tk.X, padx=10, pady=10)

        self._mot_btn = tk.Button(
            mot_frame, text="ENABLE SPIN MOTOR",
            font=(_SANS, 10, "bold"), width=22, height=2,
            bg="#2d2d2d", fg=TEXT_DIM,
            activebackground="#363636", activeforeground=TEXT,
            relief=tk.FLAT, bd=0, cursor="hand2",
            command=self._toggle_motor, state=tk.DISABLED)
        self._mot_btn.pack(side=tk.LEFT, padx=4)

        spd_frame = tk.Frame(mot_frame, bg=PANEL)
        spd_frame.pack(side=tk.LEFT, padx=16)
        tk.Label(spd_frame, text="SPEED", font=(_SANS, 7),
                 bg=PANEL, fg=TEXT_DIM).pack()
        self._mot_spd_lbl = tk.Label(spd_frame, text="—",
                                     font=(_MONO, 18, "bold"),
                                     bg=PANEL, fg=TEXT, width=5)
        self._mot_spd_lbl.pack()
        tk.Label(spd_frame, text="RPM", font=(_SANS, 7),
                 bg=PANEL, fg=TEXT_DIM).pack()

    def _select_camera(self, cam_id):
        CommonData.selected_camera = cam_id
        for b, cid in self._cam_btn_refs:
            if cid == cam_id:
                b.configure(bg=ACCENT_EB, fg="white")
            else:
                b.configure(bg="#2d2d2d", fg=TEXT_DIM)

    def _snapshot(self):
        c = CommonData.selected_camera
        if c <= 4:
            SpacePacketComms.send_ebox_tc(tc_cam_snapshot(c))
        else:
            SpacePacketComms.send_cs_tc(tc_cam_snapshot(c - 4))

    def _toggle_motor(self):
        if not self._motor_on:
            self._motor_on = True
            self._mot_btn.configure(text="DISABLE SPIN MOTOR",
                                    bg=COL_OFF, fg="white",
                                    activebackground="#b71c1c")
            SpacePacketComms.send_ebox_tc(tc_mot_enable())
        else:
            self._motor_on = False
            self._mot_btn.configure(text="ENABLE SPIN MOTOR",
                                    bg="#363636", fg=TEXT,
                                    activebackground="#404040")
            SpacePacketComms.send_ebox_tc(tc_mot_disable())

    def _poll_motor_speed(self):
        if self.tableLabels:
            try:
                self._mot_spd_lbl.configure(text=self.tableLabels[34]["text"])
            except Exception:
                pass
        self.master.after(1000, self._poll_motor_speed)

    # ============================================================ CUBESAT PANEL

    def _build_cs_panel(self, parent):
        _section(parent, "CubeSat", ACCENT_CS)

        conn = tk.Frame(parent, bg=PANEL)
        conn.pack(fill=tk.X, padx=8, pady=(2, 4))

        tk.Label(conn, text="IP", font=F_SM, bg=PANEL, fg=TEXT_DIM).pack(side=tk.LEFT)
        self._cs_ip = tk.StringVar(value=CommonData.server_name_cs)
        tk.Entry(conn, textvariable=self._cs_ip, width=13, font=F_VAL,
                 bg="#2d2d2d", fg=TEXT, insertbackground=TEXT,
                 relief=tk.FLAT, highlightthickness=1,
                 highlightbackground=BORDER).pack(side=tk.LEFT, padx=(4, 6))

        self._cs_conn_btn = _btn(conn, "Connect", self._cs_connect)
        self._cs_conn_btn.pack(side=tk.LEFT, padx=2)

        self._cs_disc_btn = _btn(conn, "Disconnect", self._cs_disconnect,
                                 state=tk.DISABLED)
        self._cs_disc_btn.pack(side=tk.LEFT, padx=2)

        self._cs_dot = tk.Label(conn, text="●", font=(_SANS, 13),
                                fg=COL_OFF, bg=PANEL)
        self._cs_dot.pack(side=tk.LEFT, padx=6)

        tog = tk.Frame(parent, bg=PANEL)
        tog.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._cs_telem_btn = _btn(tog, "  Telem OFF  ", self._toggle_cs_telem,
                                  bg=COL_OFF, fg="white", state=tk.DISABLED)
        self._cs_telem_btn.pack(side=tk.LEFT)

        _sep(parent)

        tbl = tk.Frame(parent, bg=PANEL)
        tbl.pack(fill=tk.X, padx=4)
        self._create_data_table(tbl, self._df_cs, CS_FIELDS,
                                self.tableLabels_cs, cols_per_group=16)

        _sep(parent)

        _section(parent, "CubeSat Controls", ACCENT_CS)

        ctrl = tk.Frame(parent, bg=PANEL)
        ctrl.pack(fill=tk.X, padx=8, pady=(2, 4))

        tk.Label(ctrl, text="Actions", font=F_SM, bg=PANEL,
                 fg=TEXT_DIM).grid(row=0, column=0, sticky="w", pady=2)
        self._cs_act_chk = tk.Checkbutton(
            ctrl, command=self._toggle_cs_actions,
            bg=PANEL, fg=TEXT, selectcolor="#555555",
            activebackground=PANEL, activeforeground=TEXT, relief=tk.FLAT)
        self._cs_act_chk.grid(row=0, column=1, padx=(0, 4))

        self._cs_h_btns = []
        for i, lbl in enumerate(["H1", "H2"]):
            b = _btn(ctrl, lbl,
                     lambda n=i + 1: SpacePacketComms.send_cs_tc(tc_heater_toggle(n)),
                     bg="#333333", state=tk.DISABLED)
            b.grid(row=0, column=2 + i, padx=2, pady=2)
            self._cs_h_btns.append(b)

        self._cs_bw_btns = []
        for i in range(1, 6):
            b = _btn(ctrl, f"BW{i}",
                     lambda n=i: SpacePacketComms.send_cs_tc(tc_bw_pulse(n)),
                     bg="#333333", state=tk.DISABLED)
            b.grid(row=1, column=i, padx=2, pady=2)
            self._cs_bw_btns.append(b)

        self._cs_action_widgets = self._cs_h_btns + self._cs_bw_btns

        _sep(parent)

        _section(parent, "Flywheel", ACCENT_CS)

        fw = tk.Frame(parent, bg=PANEL)
        fw.pack(fill=tk.X, padx=8, pady=(2, 4))

        self._fw_en_btn = _btn(fw, "Enable FW",
                               lambda: SpacePacketComms.send_cs_tc(tc_fw_enable()),
                               bg="#333333", state=tk.DISABLED)
        self._fw_en_btn.pack(side=tk.LEFT)

        self._fw_slider = tk.Scale(
            fw, from_=0, to=900, orient=tk.HORIZONTAL,
            variable=self._fw_speed_var, font=(_SANS, 7),
            length=170, resolution=10, label="RPM",
            command=self._fw_slider_moved, state=tk.DISABLED,
            bg=PANEL, fg=TEXT, troughcolor="#333333",
            activebackground=ACCENT_CS, highlightthickness=0,
            sliderrelief=tk.FLAT)
        self._fw_slider.pack(side=tk.LEFT, padx=4)

        self._fw_stop_btn = _btn(fw, "Stop",
                                 lambda: SpacePacketComms.send_cs_tc(tc_fw_speed(0)),
                                 bg="#333333", state=tk.DISABLED)
        self._fw_stop_btn.pack(side=tk.LEFT, padx=2)

        _sep(parent)

        _section(parent, "Deployment", ACCENT_CS)

        dep = tk.Frame(parent, bg=PANEL)
        dep.pack(fill=tk.X, padx=8, pady=(4, 10))

        self._arm_btn = tk.Button(
            dep, text="ARM", font=F_MEDB, width=8,
            bg=COL_WARN, fg="white",
            activebackground="#e65100", activeforeground="white",
            relief=tk.FLAT, bd=0, padx=10, pady=6, cursor="hand2",
            command=self._arm_deploy, state=tk.DISABLED)
        self._arm_btn.pack(side=tk.LEFT, padx=(0, 6))

        self._fire_btn = tk.Button(
            dep, text="FIRE", font=F_MEDB, width=8,
            bg=COL_OFF, fg="white",
            activebackground="#b71c1c", activeforeground="white",
            relief=tk.FLAT, bd=0, padx=10, pady=6, cursor="hand2",
            command=self._fire_deploy, state=tk.DISABLED)
        self._fire_btn.pack(side=tk.LEFT, padx=6)

        self._arm_status = tk.Label(dep, text="SAFE", font=F_MEDB,
                                    fg=COL_ON, bg=PANEL)
        self._arm_status.pack(side=tk.LEFT, padx=8)

        self._cs_special_widgets = [self._fw_en_btn, self._fw_slider,
                                    self._fw_stop_btn, self._arm_btn]

    # ================================================================ CONNECTIONS

    def _ebox_connect(self):
        CommonData.server_name = self._ebox_ip.get().strip()
        PortCommunication.connect_ebox(CommonData.server_name)
        self._eb_conn_btn.configure(bg=COL_ON, fg="white", state=tk.DISABLED)
        self._eb_disc_btn.configure(bg=COL_OFF, fg="white", state=tk.NORMAL)
        self._eb_dot.configure(fg=COL_ON)
        self._eb_telem_btn.configure(state=tk.NORMAL)
        self._mot_btn.configure(state=tk.NORMAL, fg=TEXT,
                                bg="#363636", activebackground="#404040")
        self._cam_btn.configure(state=tk.NORMAL)
        self._cam_snap_btn.configure(state=tk.NORMAL)
        print(f"EBOX target set: {CommonData.server_name}")

    def _ebox_disconnect(self):
        CommonData.TCPSTATUS = False
        CommonData.runTelemetry = False
        self._eb_telem_btn.configure(text="  Telem OFF  ", bg=COL_OFF, state=tk.DISABLED)
        self._eb_conn_btn.configure(bg="#363636", fg=TEXT, state=tk.NORMAL)
        self._eb_disc_btn.configure(bg="#363636", fg=TEXT, state=tk.DISABLED)
        self._eb_dot.configure(fg=COL_OFF)
        self._motor_on = False
        self._mot_btn.configure(text="ENABLE SPIN MOTOR", state=tk.DISABLED,
                                fg=TEXT_DIM, bg="#2d2d2d")
        self._cam_btn.configure(state=tk.DISABLED)
        self._cam_snap_btn.configure(state=tk.DISABLED)
        for w in self._eb_action_widgets:
            w.configure(state=tk.DISABLED)
        self._ebox_actions = False
        self._eb_act_chk.deselect()
        PortCommunication.disconnect_ebox()
        print("EBOX disconnected")

    def _cs_connect(self):
        CommonData.server_name_cs = self._cs_ip.get().strip()
        PortCommunication.connect_cubesat(CommonData.server_name_cs)
        self._cs_conn_btn.configure(bg=COL_ON, fg="white", state=tk.DISABLED)
        self._cs_disc_btn.configure(bg=COL_OFF, fg="white", state=tk.NORMAL)
        self._cs_dot.configure(fg=COL_ON)
        self._cs_telem_btn.configure(state=tk.NORMAL)
        print(f"CubeSat target set: {CommonData.server_name_cs}")

    def _cs_disconnect(self):
        CommonData.TCPSTATUS_cs = False
        CommonData.runTelemetry_cs = False
        self._cs_telem_btn.configure(text="  Telem OFF  ", bg=COL_OFF, state=tk.DISABLED)
        self._cs_conn_btn.configure(bg="#363636", fg=TEXT, state=tk.NORMAL)
        self._cs_disc_btn.configure(bg="#363636", fg=TEXT, state=tk.DISABLED)
        self._cs_dot.configure(fg=COL_OFF)
        for w in self._cs_action_widgets + self._cs_special_widgets:
            w.configure(state=tk.DISABLED)
        self._cs_actions = False
        self._cs_act_chk.deselect()
        self._deploy_armed = False
        self._arm_btn.configure(text="ARM", bg=COL_WARN)
        self._fire_btn.configure(state=tk.DISABLED)
        self._arm_status.configure(text="SAFE", fg=COL_ON)
        PortCommunication.disconnect_cubesat()
        print("CubeSat disconnected")

    # ================================================================== TOGGLES

    def _toggle_ebox_telem(self):
        CommonData.runTelemetry = not CommonData.runTelemetry
        if CommonData.runTelemetry:
            self._eb_telem_btn.configure(text="  Telem ON   ", bg=COL_ON,  fg="white")
        else:
            self._eb_telem_btn.configure(text="  Telem OFF  ", bg=COL_OFF, fg="white")

    def _toggle_cs_telem(self):
        CommonData.runTelemetry_cs = not CommonData.runTelemetry_cs
        if CommonData.runTelemetry_cs:
            self._cs_telem_btn.configure(text="  Telem ON   ", bg=COL_ON,  fg="white")
        else:
            self._cs_telem_btn.configure(text="  Telem OFF  ", bg=COL_OFF, fg="white")

    def _toggle_camera(self):
        CommonData.runCamera = not CommonData.runCamera
        if CommonData.runCamera:
            self._cam_btn.configure(text="Camera ON",  bg=COL_ON,  fg="white")
        else:
            self._cam_btn.configure(text="Camera OFF", bg=COL_OFF, fg="white")

    def _toggle_ebox_actions(self):
        self._ebox_actions = not self._ebox_actions
        st = tk.NORMAL if (self._ebox_actions and CommonData.TCPSTATUS) else tk.DISABLED
        for w in self._eb_action_widgets:
            w.configure(state=st)

    def _toggle_cs_actions(self):
        self._cs_actions = not self._cs_actions
        st = tk.NORMAL if (self._cs_actions and CommonData.TCPSTATUS_cs) else tk.DISABLED
        for w in self._cs_action_widgets + self._cs_special_widgets:
            w.configure(state=st)

    # ============================================================== CS SPECIFIC

    def _fw_slider_moved(self, val):
        SpacePacketComms.send_cs_tc(tc_fw_speed(int(float(val))))

    def _arm_deploy(self):
        if not self._deploy_armed:
            self._deploy_armed = True
            self._arm_btn.configure(text="DISARM", bg="#616161")
            self._fire_btn.configure(state=tk.NORMAL)
            self._arm_status.configure(text="ARMED", fg=COL_OFF)
            SpacePacketComms.send_cs_tc(tc_deploy_arm())
        else:
            self._deploy_armed = False
            self._arm_btn.configure(text="ARM", bg=COL_WARN)
            self._fire_btn.configure(state=tk.DISABLED)
            self._arm_status.configure(text="SAFE", fg=COL_ON)

    def _fire_deploy(self):
        if self._deploy_armed:
            if messagebox.askyesno("CONFIRM FIRE",
                                   "FIRE DEPLOYMENT MOTOR?\n\nThis cannot be undone.",
                                   icon="warning"):
                SpacePacketComms.send_cs_tc(tc_deploy_fire())
                self._deploy_armed = False
                self._arm_btn.configure(text="ARM", bg=COL_WARN)
                self._fire_btn.configure(state=tk.DISABLED)
                self._arm_status.configure(text="FIRED", fg=COL_OFF)

    # ================================================================= THREADS

    def _start_threads(self):
        try:
            UDPTelemReader().start()
            WatchTelem(self._df_ebox, self.tableLabels).start()
            WatchTelemCubeSat(self._df_cs, self.tableLabels_cs).start()
            WatchCamera(self._img_frame, self._img_label,
                        self._timestamp_var, self.SaveCam).start()
        except Exception as e:
            print(f"Thread start error: {e}")

    # ==================================================================== EXIT

    def exitfunc(self):
        CommonData.runTelemetry    = False
        CommonData.runTelemetry_cs = False
        CommonData.runCamera       = False
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TCPClientApp(root)
    root.mainloop()
