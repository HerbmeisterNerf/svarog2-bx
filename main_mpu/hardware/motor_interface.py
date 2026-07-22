"""SimpleFOC 'Commander' motor controller driver for the Radxa.

Talks to the ST B-G431B-ESC1 (rspro-bldc-foc firmware) over UART, replacing the
old Arduino-Nano/TLE9879 ``SM_/SS_/GS_`` protocol. Ports the command + telemetry
logic from rspro-bldc-foc/control.py into a reusable flight module.

Commander protocol (firmware rspro-bldc-foc/src/main.cpp):
  'M' + subcommand   motor menu   MC0=torque(voltage)  MC1=velocity  MC2=angle
                                  MLU<v>=voltage limit  MLC<c>=current limit
  'T<val>'           set target   (V torque / rad/s velocity / rad angle)
  'Z'                zero position (tare)
  'O1' / 'O0'        open-loop on / off

Telemetry: the firmware streams a machine-parseable line ~20 Hz:
  TEL,<shaft_angle>,<velocity_rad_s>,<current_A>,<torque_Nm>,<target>,<hallbits>
``get_telemetry()`` returns the most recent complete TEL line as a dict.
"""

_MODE_CMD = {
    "torque": "MC0",
    "voltage": "MC0",
    "velocity": "MC1",
    "angle": "MC2",
}

_TEL_FIELDS = ("angle", "velocity", "current", "torque", "target", "hall")


class MotorController:
    """Wraps a RADXA_UART_INTERFACE.UARTInterface with the Commander protocol."""

    def __init__(self, uart, name="motor"):
        self.uart = uart
        self.name = name

    # ------------------------------------------------------------- commands
    def _send(self, cmd):
        if self.uart is not None:
            self.uart.send(cmd + "\n")

    def set_mode(self, mode):
        """mode in {'torque'/'voltage', 'velocity', 'angle'}."""
        cmd = _MODE_CMD.get(mode)
        if cmd is None:
            raise ValueError(f"unknown motor mode: {mode!r}")
        self._send(cmd)

    def set_target(self, value):
        """Target: V (torque), rad/s (velocity) or rad (angle) per current mode."""
        self._send(f"T{value}")

    def stop(self):
        """Command target 0 (motor idles in closed loop, holds position in angle)."""
        self._send("T0")

    def set_limits(self, voltage=None, current=None):
        if voltage is not None:
            self._send(f"MLU{voltage}")
        if current is not None:
            self._send(f"MLC{current}")

    def zero(self):
        """Tare: define the current shaft position as zero."""
        self._send("Z")

    def open_loop(self, on):
        """Sensorless open-loop fallback (runs even if the Hall/align failed)."""
        self._send("O1" if on else "O0")

    def enable(self, mode="velocity"):
        """Bring the motor to a known idle state: set mode, target 0."""
        self.set_mode(mode)
        self.stop()

    # ----------------------------------------------------------- telemetry
    def get_telemetry(self, timeout=1.0):
        """Read the UART burst and return the newest complete TEL line as a dict,
        or None if no valid TEL line arrived within ``timeout``."""
        if self.uart is None:
            return None
        raw = self.uart.receive(max_length=256, timeout=timeout)
        if not raw:
            return None
        # The stream is ~20 Hz; a burst holds several lines. Take the last
        # COMPLETE TEL line (ignore a trailing partial with no newline).
        lines = raw.split("\n")
        for line in reversed(lines[:-1] if not raw.endswith("\n") else lines):
            line = line.strip()
            if not line.startswith("TEL,"):
                continue
            parts = line.split(",")[1:]  # drop the "TEL" tag
            if len(parts) < len(_TEL_FIELDS):
                continue
            try:
                return {
                    "angle": float(parts[0]),
                    "velocity": float(parts[1]),
                    "current": float(parts[2]),
                    "torque": float(parts[3]),
                    "target": float(parts[4]),
                    "hall": parts[5],
                }
            except ValueError:
                continue
        return None

    def get_velocity(self, timeout=1.0):
        """Convenience: shaft velocity in rad/s, or None if unavailable."""
        tel = self.get_telemetry(timeout=timeout)
        return tel["velocity"] if tel else None

    def close(self):
        if self.uart is not None:
            self.uart.close()
            self.uart = None
