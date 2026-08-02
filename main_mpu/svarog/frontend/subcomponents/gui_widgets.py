import tkinter as tk
from gui_theme import BG2, BORDER, BG3, FG_DIM, FG, FONT_S


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
    def __init__(self, parent, size=16, **kw):
        super().__init__(parent, width=size, height=size, highlightthickness=0,
                         bg=BG2, **kw)
        self._sz = size
        self.set_duty(0.0)

    def set_duty(self, duty):
        self._duty = max(0.0, min(1.0, duty))
        self.delete("all")
        if self._duty <= 0.0:
            color = "#45475a"
        elif self._duty < 0.33:
            color = "#89b4fa"
        elif self._duty < 0.66:
            color = "#fab387"
        else:
            color = "#f38ba8"
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