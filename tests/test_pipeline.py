# tests/test_pipeline.py
import os
import pytest
from unittest.mock import MagicMock, patch
from pipeline import Pipeline

@pytest.fixture
def pipeline(tmp_path):
    config = MagicMock()
    config.get.side_effect = lambda key: {
        "segment_duration": 1800,
        "storage_provider": "google_drive",
    }.get(key)

    transcriber = MagicMock()
    transcriber.transcribe_all.return_value = "[00:00] Speaker1: テスト"

    generator = MagicMock()
    generator.generate.return_value = "# 会議 2026-04-26\n\n**Speaker1:** テスト"

    uploader_factory = MagicMock(return_value=MagicMock())

    return Pipeline(
        config=config,
        transcriber=transcriber,
        generator=generator,
        uploader_factory=uploader_factory,
    )

def test_run_creates_transcript(pipeline, tmp_path):
    session_dir = str(tmp_path / "session")
    os.makedirs(session_dir)
    (tmp_path / "session" / "recording_000.wav").write_bytes(b"\x00" * 100)

    pipeline.run(session_dir)

    assert os.path.exists(os.path.join(session_dir, "transcript.txt"))

def test_run_creates_minutes(pipeline, tmp_path):
    session_dir = str(tmp_path / "session")
    os.makedirs(session_dir)
    (tmp_path / "session" / "recording_000.wav").write_bytes(b"\x00" * 100)

    pipeline.run(session_dir)

    assert os.path.exists(os.path.join(session_dir, "minutes.md"))

def test_run_calls_uploader(pipeline, tmp_path):
    session_dir = str(tmp_path / "session")
    os.makedirs(session_dir)
    (tmp_path / "session" / "recording_000.wav").write_bytes(b"\x00" * 100)

    pipeline.run(session_dir)

    pipeline._uploader_factory.return_value.upload_session.assert_called_once()

def test_run_calls_on_status(pipeline, tmp_path):
    session_dir = str(tmp_path / "session")
    os.makedirs(session_dir)
    (tmp_path / "session" / "recording_000.wav").write_bytes(b"\x00" * 100)

    statuses = []
    pipeline.run(session_dir, on_status=lambda s: statuses.append(s))

    assert "文字起こし中..." in statuses
    assert "議事録生成中..." in statuses
    assert "アップロード中..." in statuses


def test_run_with_empty_segments(tmp_path):
    from exceptions import PipelineError
    config = MagicMock()
    config.get.return_value = 1800
    pipeline = Pipeline(
        config=config,
        transcriber=MagicMock(),
        generator=MagicMock(),
        uploader_factory=MagicMock(),
    )
    session_dir = str(tmp_path / "empty_session")
    os.makedirs(session_dir)

    with pytest.raises(PipelineError, match="録音ファイルが見つかりません"):
        pipeline.run(session_dir)


def test_run_with_no_transcriber(tmp_path):
    from exceptions import ConfigurationError
    config = MagicMock()
    pipeline = Pipeline(
        config=config,
        transcriber=None,
        generator=MagicMock(),
        uploader_factory=MagicMock(),
    )
    session_dir = str(tmp_path / "session")
    os.makedirs(session_dir)

    with pytest.raises(ConfigurationError, match="APIキー"):
        pipeline.run(session_dir)


def test_run_upload_failure_preserves_files(tmp_path):
    from exceptions import UploadError
    config = MagicMock()
    config.get.side_effect = lambda key: {"segment_duration": 1800}.get(key)

    transcriber = MagicMock()
    transcriber.transcribe_all.return_value = "test transcript"
    generator = MagicMock()
    generator.generate.return_value = "# Minutes"

    mock_uploader = MagicMock()
    mock_uploader.upload_session.side_effect = Exception("network error")

    pipeline = Pipeline(
        config=config,
        transcriber=transcriber,
        generator=generator,
        uploader_factory=MagicMock(return_value=mock_uploader),
    )
    session_dir = str(tmp_path / "session")
    os.makedirs(session_dir)
    (tmp_path / "session" / "recording_000.wav").write_bytes(b"\x00" * 100)

    with pytest.raises(UploadError):
        pipeline.run(session_dir)

    assert os.path.exists(os.path.join(session_dir, "transcript.txt"))
    assert os.path.exists(os.path.join(session_dir, "minutes.md"))


def test_run_resumes_from_checkpoint(tmp_path):
    """Test that pipeline resumes from transcribed checkpoint."""
    import json
    config = MagicMock()
    config.get.side_effect = lambda key: {"segment_duration": 1800}.get(key)

    transcriber = MagicMock()
    generator = MagicMock()
    generator.generate.return_value = "# Minutes"

    mock_uploader = MagicMock()
    uploader_factory = MagicMock(return_value=mock_uploader)

    pipeline = Pipeline(
        config=config,
        transcriber=transcriber,
        generator=generator,
        uploader_factory=uploader_factory,
    )
    session_dir = str(tmp_path / "session")
    os.makedirs(session_dir)
    (tmp_path / "session" / "recording_000.wav").write_bytes(b"\x00" * 100)

    # Write transcript and checkpoint
    transcript_path = os.path.join(session_dir, "transcript.txt")
    with open(transcript_path, "w") as f:
        f.write("test transcript")

    checkpoint_path = os.path.join(session_dir, "pipeline_state.json")
    with open(checkpoint_path, "w") as f:
        json.dump({"stage": "transcribed", "transcript_path": transcript_path}, f)

    pipeline.run(session_dir)

    # Transcriber should NOT have been called (resumed past transcription)
    transcriber.transcribe_all.assert_not_called()
    # Generator should have been called
    generator.generate.assert_called_once()


def test_run_transcription_failure(tmp_path):
    """Test that transcription failure raises TranscriptionError."""
    from exceptions import TranscriptionError
    config = MagicMock()
    config.get.side_effect = lambda key: {"segment_duration": 1800}.get(key)

    transcriber = MagicMock()
    transcriber.transcribe_all.side_effect = RuntimeError("API down")
    generator = MagicMock()

    pipeline = Pipeline(
        config=config,
        transcriber=transcriber,
        generator=generator,
        uploader_factory=MagicMock(),
    )
    session_dir = str(tmp_path / "session")
    os.makedirs(session_dir)
    (tmp_path / "session" / "recording_000.wav").write_bytes(b"\x00" * 100)

    with pytest.raises(TranscriptionError, match="文字起こし失敗"):
        pipeline.run(session_dir)


def test_run_nonexistent_session_dir(tmp_path):
    from exceptions import PipelineError
    config = MagicMock()
    pipeline = Pipeline(
        config=config,
        transcriber=MagicMock(),
        generator=MagicMock(),
        uploader_factory=MagicMock(),
    )
    bad_dir = str(tmp_path / "does_not_exist")

    with pytest.raises(PipelineError, match="セッションディレクトリが存在しません"):
        pipeline.run(bad_dir)


def test_run_generation_failure(tmp_path):
    from exceptions import GenerationError
    config = MagicMock()
    config.get.side_effect = lambda key: {"segment_duration": 1800}.get(key)

    transcriber = MagicMock()
    transcriber.transcribe_all.return_value = "test transcript"
    generator = MagicMock()
    generator.generate.side_effect = RuntimeError("model error")

    pipeline = Pipeline(
        config=config,
        transcriber=transcriber,
        generator=generator,
        uploader_factory=MagicMock(),
    )
    session_dir = str(tmp_path / "session")
    os.makedirs(session_dir)
    (tmp_path / "session" / "recording_000.wav").write_bytes(b"\x00" * 100)

    with pytest.raises(GenerationError, match="議事録生成失敗"):
        pipeline.run(session_dir)
