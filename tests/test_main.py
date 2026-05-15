import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from config import Config


@pytest.fixture
def config(tmp_path):
    cfg = Config(str(tmp_path / "config.json"))
    cfg.set("gemini_api_key", "test-key")
    cfg.set("output_dir", str(tmp_path / "output"))
    cfg.set("mic_device", "TestMic")
    return cfg


def test_build_components_creates_output_dir(config, tmp_path):
    from main import _build_components
    with patch("main.GeminiTranscriber"), \
         patch("main.MinutesGenerator"):
        recorder_factory, pipeline = _build_components(config)
    output_dir = config.get("output_dir")
    assert os.path.isdir(output_dir)


def test_build_components_no_api_key(tmp_path):
    from main import _build_components
    cfg = Config(str(tmp_path / "config.json"))
    cfg.set("output_dir", str(tmp_path / "output"))
    recorder_factory, pipeline = _build_components(cfg)
    assert pipeline._transcriber is None
    assert pipeline._generator is None


def test_recorder_factory_face_to_face(config, tmp_path):
    from main import _build_components
    with patch("main.GeminiTranscriber"), \
         patch("main.MinutesGenerator"):
        recorder_factory, pipeline = _build_components(config)
    with patch("main.AudioRecorder") as MockAudio:
        mock_instance = MagicMock()
        MockAudio.return_value = mock_instance
        recorder, session_dir = recorder_factory("face_to_face")
        assert recorder == mock_instance
        assert os.path.isdir(session_dir)


def test_recorder_factory_online(config, tmp_path):
    from main import _build_components
    with patch("main.GeminiTranscriber"), \
         patch("main.MinutesGenerator"):
        recorder_factory, pipeline = _build_components(config)
    with patch("main.ScreenRecorder") as MockScreen:
        mock_instance = MagicMock()
        MockScreen.return_value = mock_instance
        recorder, session_dir = recorder_factory("online")
        assert recorder == mock_instance
        assert os.path.isdir(session_dir)


def test_setup_logging():
    from main import _setup_logging
    _setup_logging()
    import logging
    logger = logging.getLogger("test_main")
    assert logger is not None
