import threading
from LiveUpdatesTelemetry import update_data_table_colours

CS_TELEM_COUNT = 32  # display fields: CubeSat packet indices 2..33


class LiveUpdatesTelemetryCubeSat(threading.Thread):
    """Parses a CubeSat CSV telemetry string and updates the GUI table labels."""

    def __init__(self, dataFormat, tableLabels, telem_str):
        super().__init__(daemon=True)
        self.dataFormat = dataFormat
        self.tableLabels = tableLabels
        self.telem_str = telem_str

    def run(self):
        try:
            data = self._parse(self.telem_str)
            if data:
                self._update_table(data)
        except Exception as e:
            print(f"CubeSat telem error: {e}")

    def _parse(self, s):
        parts = s.split(",")
        if len(parts) < 34:
            return None
        try:
            # Skip index 0 (package_count) and 1 (timestamp); display indices 2..33
            return [float(parts[i]) for i in range(2, 34)]
        except (ValueError, IndexError):
            return None

    def _update_table(self, data):
        for i in range(min(CS_TELEM_COUNT, len(data))):
            colourBG, colourFG = update_data_table_colours(i, data, self.dataFormat)
            self.tableLabels[i].configure(
                text=round(data[i], 2), bg=colourBG, fg=colourFG
            )
