import os
import tkinter as tk
from tkinter import messagebox
import pandas as pd

from CommonData import CommonData
from PortCommunication import PortCommunication
from WatchTelemCubeSat import WatchTelemCubeSat
from SpacePacketComms import (
    SpacePacketComms,
    tc_heater_toggle, tc_bw_pulse,
    tc_fw_enable, tc_fw_speed,
    tc_deploy_arm, tc_deploy_fire,
)

CS_TELEM_COUNT = 32


class CubeSatPanel:
    """Builds the CubeSat control tab inside the given parent frame."""

    def __init__(self, parent):
        self.parent = parent
        self._deploy_armed = False
        self._fw_speed = tk.IntVar(value=0)
        self._tableLabels_cs = []
        self._dataFormat_cs = None
        self._enable_var = tk.IntVar(value=0)

        self._build_connection_row()
        self._build_action_row()
        self._build_flywheel_row()
        self._build_deploy_row()
        self._build_telem_table()
        self._load_data_format()
        self._start_background_threads()

    # ---------------------------------------------------------------- layout

    def _build_connection_row(self):
        f = tk.Frame(self.parent, relief=tk.GROOVE, bd=1)
        f.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)

        tk.Label(f, text="CubeSat IP:", font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
        self._ip_var = tk.StringVar(value=CommonData.server_name_cs)
        tk.Entry(f, textvariable=self._ip_var, width=14,
                 font=("Arial", 8)).pack(side=tk.LEFT, padx=2)

        tk.Label(f, text="Port:", font=("Arial", 8)).pack(side=tk.LEFT)
        self._port_var = tk.StringVar(value=str(CommonData.server_TCP_port_cs))
        tk.Entry(f, textvariable=self._port_var, width=6,
                 font=("Arial", 8)).pack(side=tk.LEFT, padx=2)

        self._conn_btn = tk.Button(f, text="Connect CubeSat", font=("Arial", 8),
                                   command=self._connect, bg="white")
        self._conn_btn.pack(side=tk.LEFT, padx=6)

        self._disc_btn = tk.Button(f, text="Disconnect", font=("Arial", 8),
                                   command=self._disconnect, bg="white",
                                   state=tk.DISABLED)
        self._disc_btn.pack(side=tk.LEFT, padx=2)

        self._status_dot = tk.Frame(f, width=14, height=14, bg="red",
                                    relief=tk.RAISED, bd=1)
        self._status_dot.pack(side=tk.LEFT, padx=6)

        self._telem_btn = tk.Button(f, text="Telem OFF", font=("Arial", 8),
                                    command=self._toggle_telem,
                                    bg="red", fg="white", state=tk.DISABLED)
        self._telem_btn.pack(side=tk.LEFT, padx=4)

    def _build_action_row(self):
        f = tk.Frame(self.parent, relief=tk.GROOVE, bd=1)
        f.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)

        tk.Label(f, text="Enable:", font=("Arial", 8)).grid(row=0, column=0, padx=4)
        tk.Checkbutton(f, variable=self._enable_var,
                       command=self._toggle_actions).grid(row=0, column=1, padx=2)

        self._bw_btns = []
        for i in range(1, 6):
            btn = tk.Button(f, text=f"BW {i}", font=("Arial", 7), width=5,
                            command=lambda n=i: SpacePacketComms.send_cs_tc(tc_bw_pulse(n)),
                            state=tk.DISABLED)
            btn.grid(row=0, column=1 + i, padx=2, pady=2)
            self._bw_btns.append(btn)

        self._h1_btn = tk.Button(f, text="HEAT 1", font=("Arial", 7), width=6,
                                  command=lambda: SpacePacketComms.send_cs_tc(tc_heater_toggle(1)),
                                  state=tk.DISABLED)
        self._h1_btn.grid(row=0, column=7, padx=4, pady=2)

        self._h2_btn = tk.Button(f, text="HEAT 2", font=("Arial", 7), width=6,
                                  command=lambda: SpacePacketComms.send_cs_tc(tc_heater_toggle(2)),
                                  state=tk.DISABLED)
        self._h2_btn.grid(row=0, column=8, padx=2, pady=2)

    def _build_flywheel_row(self):
        f = tk.Frame(self.parent, relief=tk.GROOVE, bd=1)
        f.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)

        tk.Label(f, text="Flywheel:", font=("Arial", 8, "bold")).grid(
            row=0, column=0, padx=6)

        self._fwen_btn = tk.Button(f, text="Enable", font=("Arial", 7),
                                    command=lambda: SpacePacketComms.send_cs_tc(tc_fw_enable()),
                                    state=tk.DISABLED)
        self._fwen_btn.grid(row=0, column=1, padx=4, pady=2)

        self._fw_slider = tk.Scale(
            f, from_=0, to=900, orient=tk.HORIZONTAL,
            variable=self._fw_speed, font=("Arial", 7), length=220,
            resolution=10, label="Speed (RPM)",
            command=self._on_fw_slider, state=tk.DISABLED,
        )
        self._fw_slider.grid(row=0, column=2, padx=6)

        self._fw_stop_btn = tk.Button(f, text="Stop", font=("Arial", 7),
                                       command=lambda: SpacePacketComms.send_cs_tc(tc_fw_speed(0)),
                                       state=tk.DISABLED)
        self._fw_stop_btn.grid(row=0, column=3, padx=4)

    def _build_deploy_row(self):
        f = tk.Frame(self.parent, relief=tk.GROOVE, bd=1)
        f.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)

        tk.Label(f, text="Deployment:", font=("Arial", 8, "bold"),
                 fg="dark red").grid(row=0, column=0, padx=6)

        self._arm_btn = tk.Button(f, text="ARM", font=("Arial", 7), width=8,
                                   command=self._arm_deploy,
                                   state=tk.DISABLED, bg="orange")
        self._arm_btn.grid(row=0, column=1, padx=6, pady=4)

        self._fire_btn = tk.Button(f, text="FIRE", font=("Arial", 7), width=8,
                                    command=self._fire_deploy,
                                    state=tk.DISABLED, bg="red", fg="white")
        self._fire_btn.grid(row=0, column=2, padx=6, pady=4)

        self._arm_status = tk.Label(f, text="SAFE", font=("Arial", 8),
                                     fg="green")
        self._arm_status.grid(row=0, column=3, padx=6)

    def _build_telem_table(self):
        f = tk.Frame(self.parent)
        f.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._telem_frame = f

    # ----------------------------------------------------------------- init

    def _load_data_format(self):
        csv_path = os.path.join(os.path.dirname(__file__), "dataFormat_cs.csv")
        self._dataFormat_cs = pd.read_csv(csv_path, header=None)
        for i in range(CS_TELEM_COUNT):
            for j in range(4):
                self._dataFormat_cs.iloc[i, j + 1] = float(
                    self._dataFormat_cs.iloc[i, j + 1]
                )
        # Build table now that we have data format
        for i in range(CS_TELEM_COUNT):
            lbl = tk.Label(self._telem_frame, font=("Arial", 7),
                           text=self._dataFormat_cs.iloc[i, 0])
            lbl.grid(row=(1 + i % 16), column=(2 * (i // 16)), padx=2, pady=1,
                     sticky="w")
            val = tk.Label(self._telem_frame, font=("Arial", 7),
                           fg="black", text="0.0", bg="grey")
            val.grid(row=(1 + i % 16), column=(1 + 2 * (i // 16)),
                     padx=2, pady=1)
            self._tableLabels_cs.append(val)

    def _start_background_threads(self):
        # UDPTelemReader (started by TCPClientApp) feeds cs_telem_queue automatically.
        # WatchTelemCubeSat consumes it and updates the table labels.
        if self._dataFormat_cs is not None:
            WatchTelemCubeSat(self._dataFormat_cs, self._tableLabels_cs).start()

    # --------------------------------------------------------------- actions

    def _connect(self):
        ip = self._ip_var.get().strip()
        if not ip:
            messagebox.showerror("CS Connection Error", "Enter a CubeSat IP address")
            return
        PortCommunication.connect_cubesat(ip)
        self._conn_btn.configure(bg="green", fg="white", state=tk.DISABLED)
        self._disc_btn.configure(bg="red", fg="white", state=tk.NORMAL)
        self._status_dot.configure(bg="green")
        self._telem_btn.configure(state=tk.NORMAL)

    def _disconnect(self):
        CommonData.runTelemetry_cs = False
        self._telem_btn.configure(text="Telem OFF", bg="red", fg="white",
                                   state=tk.DISABLED)
        PortCommunication.disconnect_cubesat()
        self._conn_btn.configure(bg="white", fg="black", state=tk.NORMAL)
        self._disc_btn.configure(bg="white", fg="black", state=tk.DISABLED)
        self._status_dot.configure(bg="red")
        self._set_actions_enabled(False)

    def _toggle_telem(self):
        CommonData.runTelemetry_cs = not CommonData.runTelemetry_cs
        if CommonData.runTelemetry_cs:
            self._telem_btn.configure(text="Telem ON", bg="green", fg="white")
        else:
            self._telem_btn.configure(text="Telem OFF", bg="red", fg="white")

    def _toggle_actions(self):
        enabled = self._enable_var.get() == 1 and CommonData.TCPSTATUS_cs
        self._set_actions_enabled(enabled)

    def _set_actions_enabled(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        for btn in self._bw_btns:
            btn.configure(state=state)
        self._h1_btn.configure(state=state)
        self._h2_btn.configure(state=state)
        self._fwen_btn.configure(state=state)
        self._fw_slider.configure(state=state)
        self._fw_stop_btn.configure(state=state)
        self._arm_btn.configure(state=state)
        if not enabled:
            self._fire_btn.configure(state=tk.DISABLED)
            self._deploy_armed = False
            self._arm_btn.configure(text="ARM", bg="orange")
            self._arm_status.configure(text="SAFE", fg="green")

    def _on_fw_slider(self, val):
        speed = int(float(val))
        SpacePacketComms.send_cs_tc(tc_fw_speed(speed))

    def _arm_deploy(self):
        if not self._deploy_armed:
            self._deploy_armed = True
            self._arm_btn.configure(text="DISARM", bg="grey")
            self._fire_btn.configure(state=tk.NORMAL)
            self._arm_status.configure(text="ARMED", fg="red")
            SpacePacketComms.send_cs_tc(tc_deploy_arm())
        else:
            self._deploy_armed = False
            self._arm_btn.configure(text="ARM", bg="orange")
            self._fire_btn.configure(state=tk.DISABLED)
            self._arm_status.configure(text="SAFE", fg="green")

    def _fire_deploy(self):
        if self._deploy_armed:
            if messagebox.askyesno(
                "CONFIRM FIRE",
                "FIRE DEPLOYMENT MOTOR?\n\nThis cannot be undone.",
                icon="warning",
            ):
                SpacePacketComms.send_cs_tc(tc_deploy_fire())
                self._deploy_armed = False
                self._arm_btn.configure(text="ARM", bg="orange")
                self._fire_btn.configure(state=tk.DISABLED)
                self._arm_status.configure(text="FIRED", fg="dark red")
