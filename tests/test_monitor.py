import sys
import pytest
from unittest.mock import patch, MagicMock
from tray.monitor import MeetingMonitor


@pytest.fixture
def monitor():
    return MeetingMonitor()


@pytest.mark.skipif(sys.platform != "win32", reason="win32gui required")
def test_no_meeting_windows_win32(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        mock_gui.EnumWindows.side_effect = lambda cb, _: None
        assert monitor.detect() is False


@pytest.mark.skipif(sys.platform != "win32", reason="win32gui required")
def test_detect_zoom_win32(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        def enum_windows(callback, _):
            callback(1, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.return_value = "Zoom Meeting"
        mock_gui.IsWindowVisible.return_value = True
        assert monitor.detect() is True


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only")
def test_detect_zoom_macos(monitor):
    with patch.object(
        monitor, "_get_titles_macos",
        return_value=["zoom.us: Zoom Meeting"],
    ):
        assert monitor.detect() is True


def test_detect_with_mocked_titles(monitor):
    with patch.object(monitor, "_get_window_titles", return_value=["Zoom Meeting"]):
        assert monitor.detect() is True


def test_no_detect_with_normal_windows(monitor):
    with patch.object(monitor, "_get_window_titles", return_value=["Notepad", "Terminal"]):
        assert monitor.detect() is False


def test_detect_teams(monitor):
    with patch.object(monitor, "_get_window_titles", return_value=["Microsoft Teams"]):
        assert monitor.detect() is True


def test_detect_google_meet(monitor):
    with patch.object(
        monitor, "_get_window_titles",
        return_value=["Google Chrome: Meet - abc-defg-hij"],
    ):
        assert monitor.detect() is True
