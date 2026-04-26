import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from transcriber.gemini import GeminiTranscriber

@pytest.fixture
def transcriber():
    return GeminiTranscriber(api_key="test-key")

def test_init_sets_api_key(transcriber):
    assert transcriber._api_key == "test-key"

@patch("transcriber.gemini.genai")
def test_transcribe_segment_sends_audio(mock_genai, transcriber, tmp_path):
    wav_file = tmp_path / "test.wav"
    wav_file.write_bytes(b"\x00" * 100)

    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="Speaker1: こんにちは")
    mock_genai.GenerativeModel.return_value = mock_model

    result = transcriber.transcribe_segment(str(wav_file))
    assert "こんにちは" in result
    mock_model.generate_content.assert_called_once()

@patch("transcriber.gemini.genai")
def test_transcribe_all_combines_segments(mock_genai, transcriber, tmp_path):
    for i in range(3):
        (tmp_path / f"recording_{i:03d}.wav").write_bytes(b"\x00" * 100)

    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(
        text="[00:00] Speaker1: テスト発言"
    )
    mock_genai.GenerativeModel.return_value = mock_model

    segments = [str(tmp_path / f"recording_{i:03d}.wav") for i in range(3)]
    result = transcriber.transcribe_all(segments, segment_duration=1800)
    assert isinstance(result, str)
    assert len(result) > 0

def test_build_prompt(transcriber):
    prompt = transcriber._build_transcription_prompt()
    assert "話者" in prompt or "speaker" in prompt.lower()
    assert "タイムスタンプ" in prompt or "timestamp" in prompt.lower()
