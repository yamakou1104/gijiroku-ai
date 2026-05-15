# tests/test_tray_app.py
import pytest
from unittest.mock import MagicMock, patch
from tray.app import TrayApp, State

def make_tray_app():
    config = MagicMock()
    config.get.side_effect = lambda key: {
        "mic_device": "Test Mic",
        "segment_duration": 1800,
    }.get(key)
    mock_recorder = MagicMock()
    recorder_factory = MagicMock(return_value=(mock_recorder, "/tmp/session"))
    pipeline = MagicMock()
    monitor = MagicMock()
    return TrayApp(
        config=config,
        recorder_factory=recorder_factory,
        pipeline=pipeline,
        monitor=monitor,
    )

def test_initial_state_is_idle():
    app = make_tray_app()
    assert app.state == State.IDLE

def test_meeting_detected_starts_recording():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING
    app._recorder_factory.assert_called_once_with("online")

def test_meeting_lost_enters_grace_period():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING

    app._monitor.detect.return_value = False
    app.tick()
    assert app.state == State.GRACE_PERIOD

def test_meeting_returns_during_grace_period():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()

    app._monitor.detect.return_value = False
    app.tick()
    assert app.state == State.GRACE_PERIOD

    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING

def test_grace_period_expires_starts_processing():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()

    app._monitor.detect.return_value = False
    app.tick()
    assert app.state == State.GRACE_PERIOD

    app._grace_deadline = 0
    app.tick()
    assert app.state == State.PROCESSING

def test_processing_completes_returns_to_idle():
    app = make_tray_app()
    app._state = State.PROCESSING
    app._session_dir = "/tmp/test"
    app._pipeline.run.return_value = None

    app._run_pipeline()
    assert app.state == State.IDLE

def test_manual_face_to_face_starts_recording():
    app = make_tray_app()
    app.start_face_to_face()
    assert app.state == State.RECORDING
    app._recorder_factory.assert_called_once_with("face_to_face")

def test_manual_stop_from_recording():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING

    app.manual_stop()
    assert app.state == State.IDLE


def test_quit_stops_recorder():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING

    app.quit()
    app._recorder_factory.return_value[0].stop.assert_called()


def test_pipeline_error_returns_to_idle():
    app = make_tray_app()
    app._state = State.PROCESSING
    app._session_dir = "/tmp/test"
    app._pipeline.run.side_effect = Exception("test error")

    app._run_pipeline()
    assert app.state == State.IDLE


def test_start_face_to_face_noop_when_recording():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING

    app.start_face_to_face()
    assert app._recorder_factory.call_count == 1


def test_run_pipeline_returns_early_when_session_dir_is_none():
    app = make_tray_app()
    app._state = State.PROCESSING
    app._session_dir = None
    app._run_pipeline()
    assert app.state == State.IDLE
    app._pipeline.run.assert_not_called()


def test_run_pipeline_clears_session_dir_preventing_duplicate():
    app = make_tray_app()
    app._state = State.PROCESSING
    app._session_dir = "/tmp/test"
    app._pipeline.run.return_value = None
    app._run_pipeline()
    assert app.state == State.IDLE

    app._state = State.PROCESSING
    app._run_pipeline()
    assert app.state == State.IDLE
    assert app._pipeline.run.call_count == 1
