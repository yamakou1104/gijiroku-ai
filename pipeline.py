import json
import logging
import os
import tempfile

from exceptions import (
    ConfigurationError,
    GenerationError,
    PipelineError,
    TranscriptionError,
    UploadError,
)
from utils.file_manager import FileManager

logger = logging.getLogger(__name__)

STAGES = ["segments_listed", "transcribed", "generated", "uploaded"]


class Pipeline:
    def __init__(self, config, transcriber, generator, uploader_factory):
        self._config = config
        self._transcriber = transcriber
        self._generator = generator
        self._uploader_factory = uploader_factory

    def run(self, session_dir, on_status=None):
        def status(msg):
            logger.info(msg)
            if on_status:
                on_status(msg)

        if not self._transcriber:
            raise ConfigurationError("Gemini APIキーが設定されていません")
        if not self._generator:
            raise ConfigurationError("議事録生成器が初期化されていません")

        checkpoint = self._load_checkpoint(session_dir)
        completed = checkpoint.get("stage", "")

        fm = FileManager(session_dir)
        segments = fm.list_segments(session_dir, ".wav")
        if not segments:
            raise PipelineError(
                f"録音ファイルが見つかりません: {session_dir}"
            )

        transcript_path = os.path.join(session_dir, "transcript.txt")
        minutes_path = os.path.join(session_dir, "minutes.md")

        if completed not in ("transcribed", "generated", "uploaded"):
            status("文字起こし中...")
            try:
                transcript = self._transcriber.transcribe_all(
                    segments,
                    segment_duration=self._config.get("segment_duration"),
                )
            except Exception as e:
                raise TranscriptionError(f"文字起こし失敗: {e}") from e

            self._atomic_write(transcript_path, transcript)
            self._save_checkpoint(session_dir, "transcribed", transcript_path=transcript_path)
        else:
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript = f.read()

        if completed not in ("generated", "uploaded"):
            status("議事録生成中...")
            try:
                minutes = self._generator.generate(transcript)
            except Exception as e:
                raise GenerationError(f"議事録生成失敗: {e}") from e

            self._atomic_write(minutes_path, minutes)
            self._save_checkpoint(
                session_dir, "generated",
                transcript_path=transcript_path,
                minutes_path=minutes_path,
            )

        if completed != "uploaded":
            status("アップロード中...")
            try:
                uploader = self._uploader_factory()
                meeting_name = os.path.basename(session_dir)
                uploader.upload_session(session_dir, meeting_name)
            except Exception as e:
                logger.error("アップロード失敗（ローカルファイルは保持）: %s", e)
                status(f"アップロード失敗: {e}")
                raise UploadError(
                    f"アップロード失敗。ファイルは {session_dir} に保持されています"
                ) from e

            self._save_checkpoint(
                session_dir, "uploaded",
                transcript_path=transcript_path,
                minutes_path=minutes_path,
            )

        from utils.notification import notify

        try:
            notify("議事録AI", "議事録が完成しました")
        except Exception:
            pass

    def _load_checkpoint(self, session_dir):
        path = os.path.join(session_dir, "pipeline_state.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, ValueError):
                return {}
        return {}

    def _save_checkpoint(self, session_dir, stage, **kwargs):
        from datetime import datetime

        data = {"stage": stage, "timestamp": datetime.now().isoformat()}
        data.update(kwargs)
        path = os.path.join(session_dir, "pipeline_state.json")
        dir_name = os.path.dirname(path)
        fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except BaseException:
            os.unlink(tmp)
            raise

    @staticmethod
    def _atomic_write(path, content):
        dir_name = os.path.dirname(path)
        fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, path)
        except BaseException:
            os.unlink(tmp)
            raise
