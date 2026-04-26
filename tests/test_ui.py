# tests/test_ui.py
import pytest
from unittest.mock import MagicMock
from config import Config

def test_storage_selector_default(tmp_path):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    from ui.widgets import StorageSelector
    selector = StorageSelector(root)
    assert selector.value == "google_drive"
    root.destroy()

def test_storage_selector_set_value(tmp_path):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    from ui.widgets import StorageSelector
    selector = StorageSelector(root)
    selector.value = "onedrive"
    assert selector.value == "onedrive"
    root.destroy()

def test_status_bar(tmp_path):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    from ui.widgets import StatusBar
    bar = StatusBar(root)
    bar.set_status("テスト")
    assert bar._label.cget("text") == "テスト"
    bar.set_recording(True)
    assert "REC" in bar._rec_indicator.cget("text")
    bar.set_recording(False)
    assert bar._rec_indicator.cget("text") == ""
    root.destroy()
