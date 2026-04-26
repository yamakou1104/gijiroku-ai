import pytest
from PIL import Image
from tray.icons import create_icon

def test_create_idle_icon():
    icon = create_icon("idle")
    assert isinstance(icon, Image.Image)
    assert icon.size == (64, 64)

def test_create_recording_icon():
    icon = create_icon("recording")
    assert isinstance(icon, Image.Image)
    assert icon.size == (64, 64)

def test_create_processing_icon():
    icon = create_icon("processing")
    assert isinstance(icon, Image.Image)
    assert icon.size == (64, 64)

def test_idle_and_recording_differ():
    idle = create_icon("idle")
    rec = create_icon("recording")
    assert idle.tobytes() != rec.tobytes()

def test_unknown_state_returns_idle():
    icon = create_icon("unknown")
    idle = create_icon("idle")
    assert icon.tobytes() == idle.tobytes()
