import os
import pytest
from unittest.mock import patch, MagicMock
from transcriber.gemini import GeminiTranscriber


@pytest.fixture
def mock_client():
    with patch("transcriber.gemini.genai") as mock_genai:
        mock_c = MagicMock()
        mock_genai.Client.return_value = mock_c
        yield mock_c


@pytest.fixture
def transcriber(mock_client):
    return GeminiTranscriber(api_key="test-key")


def test_init_sets_api_key(mock_client):
    t = GeminiTranscriber(api_key="test-key")
    assert t._api_key == "test-key"
    assert t._client == mock_client


def test_transcribe_segment_sends_audio(transcriber, tmp_path):
    wav_file = tmp_path / "test.wav"
    wav_file.write_bytes(b"\x00" * 100)

    mock_file = MagicMock()
    mock_file.name = "test-file"
    transcriber._client.files.upload.return_value = mock_file
    transcriber._client.models.generate_content.return_value = MagicMock(
        text="Speaker1: こんにちは", candidates=[MagicMock()]
    )

    result = transcriber.transcribe_segment(str(wav_file))
    assert "こんにちは" in result
    transcriber._client.models.generate_content.assert_called_once()


def test_transcribe_all_combines_segments(transcriber, tmp_path):
    for i in range(3):
        (tmp_path / f"recording_{i:03d}.wav").write_bytes(b"\x00" * 100)

    mock_file = MagicMock()
    mock_file.name = "test-file"
    transcriber._client.files.upload.return_value = mock_file
    transcriber._client.models.generate_content.return_value = MagicMock(
        text="[00:00] Speaker1: テスト発言", candidates=[MagicMock()]
    )

    segments = [str(tmp_path / f"recording_{i:03d}.wav") for i in range(3)]
    result = transcriber.transcribe_all(segments, segment_duration=1800)
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_prompt(transcriber):
    prompt = transcriber._build_transcription_prompt()
    assert "話者" in prompt or "speaker" in prompt.lower()
    assert "タイムスタンプ" in prompt or "timestamp" in prompt.lower()


def test_transcribe_segment_safety_filter(transcriber):
    mock_file = MagicMock()
    mock_file.name = "test-file"
    transcriber._client.files.upload.return_value = mock_file

    mock_response = MagicMock()
    mock_response.candidates = []
    transcriber._client.models.generate_content.return_value = mock_response

    result = transcriber.transcribe_segment("/tmp/test.wav")
    assert "セーフティフィルター" in result


def test_transcribe_segment_api_error(transcriber):
    transcriber._client.files.upload.side_effect = RuntimeError("API error")

    with pytest.raises(RuntimeError, match="API error"):
        transcriber.transcribe_segment("/tmp/test.wav")


def test_adjust_timestamps_with_offset(transcriber):
    text = "[00:30] Speaker1: こんにちは\n[01:00] Speaker2: はい"
    result = transcriber._adjust_timestamps(text, offset_minutes=30)
    assert "[30:30]" in result
    assert "[31:00]" in result


def test_adjust_timestamps_wraps_to_hours(transcriber):
    text = "[50:00] Speaker1: テスト"
    result = transcriber._adjust_timestamps(text, offset_minutes=30)
    assert "[1:20:00]" in result


def test_adjust_timestamps_zero_offset_unchanged(transcriber):
    text = "[05:30] Speaker1: テスト"
    result = transcriber._adjust_timestamps(text, offset_minutes=0)
    assert result == text


def test_adjust_timestamps_non_timestamp_lines_preserved(transcriber):
    text = "Some text without timestamps\n[invalid] not a time"
    result = transcriber._adjust_timestamps(text, offset_minutes=30)
    assert "Some text without timestamps" in result
    assert "[invalid] not a time" in result
