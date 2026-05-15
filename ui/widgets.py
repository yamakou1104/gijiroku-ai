# ui/widgets.py
import sys
import tkinter as tk
from tkinter import ttk

if sys.platform == "darwin":
    _FONT_FAMILY = "Hiragino Sans"
    _EMOJI_FONT = "Apple Color Emoji"
else:
    _FONT_FAMILY = _FONT_FAMILY
    _EMOJI_FONT = _EMOJI_FONT

class ModeButton(tk.Frame):
    def __init__(self, parent, title, icon_text, description, command=None):
        super().__init__(parent, relief="raised", borderwidth=2, padx=20, pady=20)
        self._command = command

        self._title_label = tk.Label(
            self, text=title, font=(_FONT_FAMILY, 14, "bold")
        )
        self._title_label.pack()

        self._icon_label = tk.Label(
            self, text=icon_text, font=(_EMOJI_FONT, 24)
        )
        self._icon_label.pack(pady=5)

        self._desc_label = tk.Label(
            self, text=description, font=(_FONT_FAMILY, 9), fg="gray"
        )
        self._desc_label.pack()

        self.bind("<Button-1>", self._on_click)
        for child in self.winfo_children():
            child.bind("<Button-1>", self._on_click)

    def _on_click(self, event=None):
        if self._command:
            self._command()


class StatusBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._label = tk.Label(
            self, text="待機中", font=(_FONT_FAMILY, 10), anchor="w"
        )
        self._label.pack(fill="x", padx=10)

        self._rec_indicator = tk.Label(
            self, text="", font=(_FONT_FAMILY, 10), fg="red"
        )
        self._rec_indicator.pack(side="right", padx=10)

    def set_status(self, text):
        self._label.config(text=text)

    def set_recording(self, is_recording):
        self._rec_indicator.config(text="● REC" if is_recording else "")


class StorageSelector(tk.Frame):
    def __init__(self, parent, on_change=None):
        super().__init__(parent)
        self._var = tk.StringVar(value="google_drive")

        tk.Label(self, text="保存先:", font=(_FONT_FAMILY, 10)).pack(side="left")

        self._combo = ttk.Combobox(
            self,
            textvariable=self._var,
            values=["google_drive", "onedrive"],
            state="readonly",
            width=15,
        )
        self._combo.pack(side="left", padx=5)
        if on_change:
            self._combo.bind("<<ComboboxSelected>>", lambda e: on_change(self._var.get()))

    @property
    def value(self):
        return self._var.get()

    @value.setter
    def value(self, val):
        self._var.set(val)
