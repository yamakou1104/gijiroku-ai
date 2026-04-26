# pipeline.py
import os
from utils.file_manager import FileManager
from utils.notification import notify

class Pipeline:
    def __init__(self, config, transcriber, generator, uploader_factory):
        self._config = config
        self._transcriber = transcriber
        self._generator = generator
        self._uploader_factory = uploader_factory

    def run(self, session_dir, on_status=None):
        def status(msg):
            if on_status:
                on_status(msg)

        fm = FileManager(session_dir)
        segments = fm.list_segments(session_dir, ".wav")

        status("文字起こし中...")
        transcript = self._transcriber.transcribe_all(
            segments,
            segment_duration=self._config.get("segment_duration"),
        )

        transcript_path = os.path.join(session_dir, "transcript.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript)

        status("議事録生成中...")
        minutes = self._generator.generate(transcript)

        minutes_path = os.path.join(session_dir, "minutes.md")
        with open(minutes_path, "w", encoding="utf-8") as f:
            f.write(minutes)

        status("アップロード中...")
        uploader = self._uploader_factory()
        meeting_name = os.path.basename(session_dir)
        uploader.upload_session(session_dir, meeting_name)

        notify("議事録AI", "議事録が完成しました")
