import os
import pytest
from unittest.mock import patch, MagicMock
from recorder.audio import AudioRecorder

@pytest.fixture
def recorder(tmp_path):
    return AudioRecorder(
        output_dir=str(tmp_path),
        mic_device="Test Microphone",
        segment_duration=1800,
    )

def test_build_command(recorder):
    cmd = recorder._build_command()
    assert "ffmpeg" in cmd[0]
    assert "-f" in cmd
    assert "dshow" in cmd
    assert "1800" in cmd
    assert "recording_%03d.wav" in " ".join(cmd)

def test_build_command_contains_mic_device(recorder):
    cmd = recorder._build_command()
    cmd_str = " ".join(cmd)
    assert "Test Microphone" in cmd_str

def test_is_recording_initially_false(recorder):
    assert recorder.is_recording is False

@patch("recorder.audio.subprocess.Popen")
def test_start_sets_recording_flag(mock_popen, recorder):
    mock_popen.return_value = MagicMock()
    recorder.start()
    assert recorder.is_recording is True

@patch("recorder.audio.subprocess.Popen")
def test_stop_clears_recording_flag(mock_popen, recorder):
    mock_proc = MagicMock()
    mock_popen.return_value = mock_proc
    recorder.start()
    recorder.stop()
    assert recorder.is_recording is False

@patch("recorder.audio.subprocess.Popen")
def test_stop_sends_q_to_ffmpeg(mock_popen, recorder):
    mock_proc = MagicMock()
    mock_popen.return_value = mock_proc
    recorder.start()
    recorder.stop()
    mock_proc.communicate.assert_called_once_with(input=b"q")

def test_list_devices_returns_list():
    with patch("recorder.audio.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stderr="[dshow] \"Microphone (Realtek)\" (audio)\n[dshow] \"Stereo Mix\" (audio)\n"
        )
        devices = AudioRecorder.list_devices()
        assert isinstance(devices, list)
