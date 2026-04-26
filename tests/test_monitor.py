import pytest
from unittest.mock import patch, MagicMock
from tray.monitor import MeetingMonitor

@pytest.fixture
def monitor():
    return MeetingMonitor()

def test_no_meeting_windows(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        windows = []
        def enum_cb(callback, _):
            for hwnd, title in windows:
                callback(hwnd, None)
        mock_gui.EnumWindows.side_effect = enum_cb
        mock_gui.GetWindowText.return_value = "Notepad"
        mock_gui.IsWindowVisible.return_value = True

        assert monitor.detect() is False

def test_detect_zoom_meeting(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        titles = {"Zoom Meeting"}
        call_count = [0]
        def enum_windows(callback, _):
            for i, title in enumerate(titles):
                callback(i, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.side_effect = lambda hwnd: list(titles)[hwnd]
        mock_gui.IsWindowVisible.return_value = True

        assert monitor.detect() is True

def test_detect_teams(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        def enum_windows(callback, _):
            callback(0, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.return_value = "Microsoft Teams"
        mock_gui.IsWindowVisible.return_value = True

        assert monitor.detect() is True

def test_detect_google_meet(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        def enum_windows(callback, _):
            callback(0, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.return_value = "Meet - abc-defg-hij - Google Chrome"
        mock_gui.IsWindowVisible.return_value = True

        assert monitor.detect() is True

def test_ignore_invisible_windows(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        def enum_windows(callback, _):
            callback(0, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.return_value = "Zoom Meeting"
        mock_gui.IsWindowVisible.return_value = False

        assert monitor.detect() is False

def test_detect_zoom_webinar(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        def enum_windows(callback, _):
            callback(0, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.return_value = "Zoom Webinar"
        mock_gui.IsWindowVisible.return_value = True

        assert monitor.detect() is True
