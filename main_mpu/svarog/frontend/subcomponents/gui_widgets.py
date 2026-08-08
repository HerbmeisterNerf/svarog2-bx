import tkinter as tk
from collections import deque
from gui_theme import (BG2, BG3, BORDER, FG, FG_DIM, FONT, FONT_B, FONT_L,
                       FONT_S, ACCENT, TEAL, RED, YELLOW)


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
    def __init__(self, parent, width=56, height=22, **kw):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, bg=BG2, **kw)
        self._wd, self._ht = width, height
        self.set_duty(0.0)

    def set_duty(self, duty):
        duty = max(0.0, min(1.0, duty))
        self.delete("all")
        if duty <= 0.0:
            color = "#45475a"
        elif duty < 0.33:
            color = "#89b4fa"
        elif duty < 0.66:
            color = "#fab387"
        else:
            color = "#f38ba8"
        self.create_rectangle(1, 1, self._wd - 1, self._ht - 1,
                              fill=color, outline=BORDER)
        self.create_text(self._wd / 2, self._ht / 2, text=f"{duty * 100:.0f}",
                         fill=BG2 if duty > 0.0 else FG, font=FONT_S)


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


class RollingGraph(tk.Canvas):
    """Fixed-width rolling graph of a telemetry channel.

    Keeps the last `window` samples, auto-scales vertically, and
    redraws on every push().  Call `push(value)` from the GUI thread.
    """

    PALETTE = [ACCENT, TEAL, RED, "#a6e3a1", "#f9e2af", "#fab387",
               "#cba6f7", "#f5c2e7"]

    def __init__(self, parent, width=180, height=64, window=90,
                 label=None, color=None, target=None, **kw):
        super().__init__(master=parent, width=width, height=height,
                         bg=BG2, highlightthickness=1,
                         highlightbackground=BORDER, **kw)
        self._window = max(2, window)
        self._buf = deque(maxlen=self._window)
        self._color = color if color is not None else self.PALETTE[id(self) % len(self.PALETTE)]
        self._label = label
        self._target = target
        self._draw()

    def clear(self):
        self._buf.clear()
        self._draw()

    def set_data(self, values):
        self._buf = deque(maxlen=self._window)
        for v in values:
            try:
                self._buf.append(float(v))
            except (TypeError, ValueError):
                pass
        self._draw()

    def push(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        self._buf.append(value)
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 10 or h <= 10:
            return
        if self._label:
            self.create_text(2, 2, anchor="nw", text=self._label,
                             fill=FG_DIM, font=FONT_S)
        vals = list(self._buf)
        if not vals:
            return
        lo, hi = min(vals), max(vals)
        if hi - lo < 1e-9:
            hi = lo + 1.0
        pad = 2
        n = len(vals)
        # target reference line (extends the range so it's visible)
        if self._target is not None:
            lo = min(lo, self._target)
            hi = max(hi, self._target)
        for i in range(1, n):
            x0 = pad + (i - 1) * (w - 2 * pad) / float(n - 1)
            x1 = pad + i * (w - 2 * pad) / float(n - 1)
            y0 = h - pad - (vals[i - 1] - lo) / (hi - lo) * (h - 2 * pad)
            y1 = h - pad - (vals[i] - lo) / (hi - lo) * (h - 2 * pad)
            self.create_line(x0, y0, x1, y1, fill=self._color, width=1)
        x = pad + (n - 1) * (w - 2 * pad) / max(n - 1, 1)
        y = h - pad - (vals[-1] - lo) / (hi - lo) * (h - 2 * pad)
        self.create_oval(x - 1, y - 1, x + 1, y + 1, fill=self._color, outline="")
        if self._target is not None:
            ty = h - pad - (self._target - lo) / (hi - lo) * (h - 2 * pad)
            self.create_line(pad, ty, w - pad, ty, dash=(3, 3), fill=FG_DIM)


# ── section classification for telemetry keys ──────────────────────────────

_SECTION_RULES = [
    ("Timestamp",  lambda k: k.startswith("TS")),
    ("PDU Power",  lambda k: k.startswith("V_SENSE") or k.startswith("ADC_V")),
    ("Thermal",    lambda k: k.startswith("THERMAL")),
    ("Heaters",    lambda k: k.startswith("HEAT_")),
    ("Other",      lambda k: True),
]

# Display names for PDU channels (currents + voltages).
DISPLAY_NAMES = {
    "V_SENSE5":  "Current 5V",
    "V_SENSE9":  "Current 9V",
    "V_SENSE12": "Current 12V",
    "ADC_V5":    "Voltage 5V",
    "ADC_V9":    "Voltage 9V",
    "ADC_V12":   "Voltage 12V",
    "ADC_V28":   "Voltage 28V",
}

# Target reference line for voltage graphs.
VOLTAGE_TARGETS = {
    "ADC_V5":  5.0,
    "ADC_V9":  9.0,
    "ADC_V12": 12.0,
    "ADC_V28": 28.0,
}

_NO_GRAPH_PREFIXES = ("TS",)

# Ignored channels: PG_ / FLT_ (power good, faults) are not displayed;
# HEAT_*_DUTY cycle numbers are not plotted (temperatures still are).
_IGNORED_PREFIXES = ("PG_", "FLT_")
_IGNORED_SUFFIXES = ("_DUTY",)


def display_name(key):
    return DISPLAY_NAMES.get(key, key)


def section_of_key(key):
    for name, pred in _SECTION_RULES:
        if pred(key):
            return name
    return "Other"


class TelemetryPanel(tk.Frame):
    """Scrollable telemetry list.

    Each channel is a row with a large value label (left) and a rolling
    RollingGraph (right).  Rows are grouped into labeled sections and the
    whole thing scrolls vertically.
    """

    def __init__(self, parent, title, graph_height=64, graph_window=90,
                 value_font=FONT_L, **kw):
        super().__init__(master=parent, bg=BG2, bd=1, relief="groove", **kw)
        self._graph_window = graph_window
        self._graph_height = graph_height
        self._value_font = value_font
        self._sections = []     # list of (name, LabelFrame)
        self._rows = {}         # key -> [row, value_lbl, graph]
        self._color_idx = 0

        hdr = tk.Frame(self, bg=BG2)
        hdr.pack(fill="x", padx=4, pady=(3, 1))
        tk.Label(hdr, text=title, font=FONT_B, fg=ACCENT, bg=BG2).pack(side="left")

        self._can = tk.Canvas(self, bg=BG2, highlightthickness=0)
        self._sb = tk.Scrollbar(self, orient="vertical", command=self._can.yview)
        self._inner = tk.Frame(self._can, bg=BG2)
        self._win = self._can.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>", self._on_inner_cfg)
        self._can.bind("<Configure>", self._on_canvas_cfg)
        self.bind("<Enter>", self._grab_wheel)
        self.bind("<Leave>", self._release_wheel)
        self._can.bind("<Enter>", self._grab_wheel)
        self._inner.bind("<Enter>", self._grab_wheel)
        self._sb.pack(side="right", fill="y")
        self._can.pack(side="left", fill="both", expand=True)

    def _grab_wheel(self, _e=None):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(seq, self._on_wheel, add="+")

    def _release_wheel(self, _e=None):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.unbind_all(seq)

    def _on_wheel(self, e):
        if e.num == 4:
            self._can.yview_scroll(-3, "units")
        elif e.num == 5:
            self._can.yview_scroll(3, "units")
        else:
            self._can.yview_scroll(-1 if e.delta > 0 else 1, "units")
        return "break"

    def _on_inner_cfg(self, _e):
        self._can.configure(scrollregion=self._can.bbox("all"))

    def _on_canvas_cfg(self, e):
        self._can.itemconfigure(self._win, width=e.width)

    def _get_section(self, name):
        for n, f in self._sections:
            if n == name:
                return f
        f = tk.Frame(self._inner, bg=BG2)
        h = tk.Label(f, text=f" {name} ", font=FONT_B, fg=YELLOW, bg=BG2,
                     anchor="w")
        h.pack(fill="x", padx=2, pady=(3, 0))
        f.pack(fill="x", padx=2, pady=(2, 1))
        self._sections.append((name, f))
        return f

    def update_telem(self, text):
        """text: snapshot block of `KEY=VALUE` lines."""
        by_sec = {}
        for line in text.split("\n"):
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if any(k.startswith(p) for p in _IGNORED_PREFIXES):
                continue
            if any(k.endswith(s) for s in _IGNORED_SUFFIXES):
                continue
            sec = section_of_key(k)
            by_sec.setdefault(sec, []).append((k, v))

        seen_keys = {k for vs in by_sec.values() for k, _ in vs}

        # Drop rows whose key vanished.
        for k in list(self._rows):
            if k not in seen_keys:
                self._rows.pop(k)[0].destroy()

        # Drop sections that no longer appear.
        for name, f in list(self._sections):
            if name not in by_sec:
                f.destroy()
                self._sections.remove((name, f))

        for sec_name, items in by_sec.items():
            secf = self._get_section(sec_name)
            for key, val in items:
                if key not in self._rows:
                    self._rows[key] = self._make_row(
                        secf, key,
                        graph=not any(key.startswith(p) for p in _NO_GRAPH_PREFIXES))
                self._rows[key][1].configure(text=self._fmt(val))
                if self._rows[key][2] is not None:
                    self._rows[key][2].push(val)

    def _make_row(self, secf, key, graph=True):
        row = tk.Frame(secf, bg=BG2)
        name = tk.Label(row, text=f"{display_name(key):<14}", font=FONT_B,
                        fg=TEAL, bg=BG2, anchor="w")
        value = tk.Label(row, text="--", font=self._value_font,
                         fg=FG, bg=BG2, width=10, anchor="e")
        graph_widget = None
        if graph:
            color = RollingGraph.PALETTE[self._color_idx % len(RollingGraph.PALETTE)]
            self._color_idx += 1
            graph_widget = RollingGraph(row, width=220, height=self._graph_height,
                                        window=self._graph_window, color=color,
                                        target=VOLTAGE_TARGETS.get(key))
        name.pack(side="left", padx=(2, 4))
        value.pack(side="left", padx=(0, 4))
        if graph_widget is not None:
            graph_widget.pack(side="left", fill="both", expand=True, padx=(0, 2),
                              pady=2)
        row.pack(fill="x", padx=2, pady=1)
        return row, value, graph_widget

    @staticmethod
    def _fmt(v):
        try:
            fv = float(v)
            if abs(fv) >= 100:
                return f"{fv:8.1f}"
            if fv == int(fv):
                return f"{fv:8d}" if abs(fv) < 1000 else f"{fv:8.1f}"
            return f"{fv:8.3f}"
        except ValueError:
            return f"{v:>10}"

    def set_data(self, key, values):
        if key in self._rows and self._rows[key][2] is not None:
            self._rows[key][2].set_data(values)