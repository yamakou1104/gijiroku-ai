import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from recorder.screen import ScreenRecorder


@pytest.fixture
def recorder(tmp_path):
    device = "0" if sys.platform == "darwin" else "Test Microphone"
    return ScreenRecorder(
        output_dir=str(tmp_path),
        mic_device=device,
        segment_duration=1800,
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
def test_build_video_command_windows(recorder):
    cmd = recorder._build_video_command()
    cmd_str = " ".join(cmd)
    assert "gdigrab" in cmd_str
    assert "desktop" in cmd_str


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only")
def test_build_video_command_macos(recorder):
    cmd = recorder._build_video_command()
    cmd_str = " ".join(cmd)
    assert "avfoundation" in cmd_str


def test_is_recording_initially_false(recorder):
    assert recorder.is_recording is False


@patch("recorder.screen.subprocess.Popen")
def test_start_sets_recording_flag(mock_popen, recorder):
    mock_popen.return_value = MagicMock(poll=MagicMock(return_value=None))
    with patch("recorder.screen.shutil.which", return_value="/usr/bin/ffmpeg"):
        recorder.start()
    assert recorder.is_recording is True


@patch("recorder.screen.subprocess.Popen")
def test_start_launches_two_processes(mock_popen, recorder):
    mock_popen.return_value = MagicMock(poll=MagicMock(return_value=None))
    with patch("recorder.screen.shutil.which", return_value="/usr/bin/ffmpeg"):
        recorder.start()
    assert mock_popen.call_count == 2


def test_start_raises_when_ffmpeg_missing(recorder):
    with patch("recorder.screen.shutil.which", return_value=None):
        from exceptions import RecordingError
        with pytest.raises(RecordingError, match="FFmpeg"):
            recorder.start()


@patch("recorder.screen.subprocess.Popen")
def test_audio_failure_kills_video(mock_popen, recorder):
    video_proc = MagicMock(poll=MagicMock(return_value=None), returncode=0)
    mock_popen.side_effect = [video_proc, FileNotFoundError("audio")]
    with patch("recorder.screen.shutil.which", return_value="/usr/bin/ffmpeg"):
        from exceptions import RecordingError
        with pytest.raises(RecordingError):
            recorder.start()
    video_proc.kill.assert_called_once()
