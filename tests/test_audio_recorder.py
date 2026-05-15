import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from recorder.audio import AudioRecorder


@pytest.fixture
def recorder(tmp_path):
    device = "0" if sys.platform == "darwin" else "Test Microphone"
    return AudioRecorder(
        output_dir=str(tmp_path),
        mic_device=device,
        segment_duration=1800,
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
def test_build_command_windows(recorder):
    cmd = recorder._build_command()
    assert "dshow" in cmd
    assert "1800" in cmd


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only")
def test_build_command_macos(recorder):
    cmd = recorder._build_command()
    assert "avfoundation" in cmd
    assert "none:0" in " ".join(cmd)


def test_is_recording_initially_false(recorder):
    assert recorder.is_recording is False


@patch("recorder.audio.subprocess.Popen")
def test_start_sets_recording_flag(mock_popen, recorder):
    mock_popen.return_value = MagicMock(poll=MagicMock(return_value=None))
    with patch("recorder.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
        recorder.start()
    assert recorder.is_recording is True


@patch("recorder.audio.subprocess.Popen")
def test_stop_clears_recording_flag(mock_popen, recorder):
    mock_proc = MagicMock(poll=MagicMock(return_value=None), returncode=0)
    mock_popen.return_value = mock_proc
    with patch("recorder.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
        recorder.start()
        recorder.stop()
    assert recorder.is_recording is False


def test_start_raises_when_ffmpeg_missing(recorder):
    with patch("recorder.audio.shutil.which", return_value=None):
        from exceptions import RecordingError
        with pytest.raises(RecordingError, match="FFmpeg"):
            recorder.start()


@patch("recorder.audio.subprocess.Popen")
def test_stop_kills_on_timeout(mock_popen, recorder):
    import subprocess
    mock_proc = MagicMock(
        poll=MagicMock(return_value=None),
        returncode=None,
    )

    wait_call_count = [0]

    def wait_side_effect(timeout=None):
        wait_call_count[0] += 1
        if wait_call_count[0] <= 2:
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=timeout or 10)
        mock_proc.returncode = -9

    mock_proc.wait.side_effect = wait_side_effect

    if sys.platform != "darwin":
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=10)

    mock_popen.return_value = mock_proc

    with patch("recorder.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
        recorder.start()
        recorder.stop()
    assert mock_proc.terminate.called or mock_proc.kill.called


def test_list_devices_returns_list():
    with patch("recorder.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
        with patch("recorder.audio.subprocess.run") as mock_run:
            if sys.platform == "darwin":
                mock_run.return_value = MagicMock(
                    stderr=(
                        "[AVFoundation indev] AVFoundation audio devices:\n"
                        "[AVFoundation indev] [0] MacBook Pro Microphone\n"
                        "[AVFoundation indev] [1] BlackHole 2ch\n"
                    )
                )
                devices = AudioRecorder.list_devices()
                assert len(devices) >= 1
                assert isinstance(devices[0], tuple)
            else:
                mock_run.return_value = MagicMock(
                    stderr='[dshow] "Microphone (Realtek)" (audio)\n'
                )
                devices = AudioRecorder.list_devices()
                assert isinstance(devices, list)
