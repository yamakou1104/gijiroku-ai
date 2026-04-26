import os
import pytest
from unittest.mock import patch, MagicMock
from recorder.screen import ScreenRecorder

@pytest.fixture
def recorder(tmp_path):
    return ScreenRecorder(
        output_dir=str(tmp_path),
        mic_device="Test Microphone",
        segment_duration=1800,
    )

def test_build_video_command(recorder):
    cmd = recorder._build_video_command()
    cmd_str = " ".join(cmd)
    assert "ffmpeg" in cmd_str
    assert "gdigrab" in cmd_str
    assert "desktop" in cmd_str
    assert ".mp4" in cmd_str

def test_build_audio_command(recorder):
    cmd = recorder._build_audio_command()
    cmd_str = " ".join(cmd)
    assert "ffmpeg" in cmd_str
    assert "dshow" in cmd_str
    assert "recording_%03d.wav" in cmd_str

def test_is_recording_initially_false(recorder):
    assert recorder.is_recording is False

@patch("recorder.screen.subprocess.Popen")
def test_start_sets_recording_flag(mock_popen, recorder):
    mock_popen.return_value = MagicMock()
    recorder.start()
    assert recorder.is_recording is True

@patch("recorder.screen.subprocess.Popen")
def test_stop_clears_flag(mock_popen, recorder):
    mock_proc = MagicMock()
    mock_popen.return_value = mock_proc
    recorder.start()
    recorder.stop()
    assert recorder.is_recording is False

@patch("recorder.screen.subprocess.Popen")
def test_start_launches_two_processes(mock_popen, recorder):
    mock_popen.return_value = MagicMock()
    recorder.start()
    assert mock_popen.call_count == 2
