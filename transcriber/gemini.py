import logging

from google import genai

from utils.retry import retry

logger = logging.getLogger(__name__)


class GeminiTranscriber:
    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key):
        if not api_key:
            raise ValueError("Gemini APIキーが空です")
        self._api_key = api_key
        self._client = genai.Client(api_key=api_key)

    def _build_transcription_prompt(self):
        return (
            "この音声ファイルを文字起こししてください。\n"
            "以下のルールに従ってください:\n"
            "1. 話者を識別し、Speaker1, Speaker2... のラベルを付けてください\n"
            "2. 各発言にタイムスタンプを [MM:SS] 形式で付けてください\n"
            "3. フィラー（「えーと」「あのー」等）は除去してください\n"
            "4. 口語を読みやすい文体に整えてください（内容は変えない）\n"
            "5. 出力形式:\n"
            "   [MM:SS] Speaker1: 発言内容\n"
            "   [MM:SS] Speaker2: 発言内容\n"
        )

    def transcribe_segment(self, audio_path):
        audio_file = None
        try:
            audio_file = retry(
                lambda: self._client.files.upload(file=audio_path),
                max_retries=3,
                retryable_exceptions=(Exception,),
            )
            response = retry(
                lambda: self._client.models.generate_content(
                    model=self.MODEL,
                    contents=[
                        self._build_transcription_prompt(),
                        audio_file,
                    ],
                ),
                max_retries=3,
                retryable_exceptions=(Exception,),
            )
            if not response.candidates:
                logger.warning("Safety filter triggered for %s", audio_path)
                return f"[文字起こし不可: セーフティフィルターにより除外 — {audio_path}]"
            return response.text
        finally:
            if audio_file:
                try:
                    self._client.files.delete(name=audio_file.name)
                except Exception:
                    logger.warning("Failed to delete uploaded file: %s", audio_path)

    def transcribe_all(self, segment_paths, segment_duration=1800):
        all_text = []
        for i, path in enumerate(segment_paths):
            offset_minutes = (i * segment_duration) // 60
            logger.info("Transcribing segment %d/%d: %s", i + 1, len(segment_paths), path)
            try:
                text = self.transcribe_segment(path)
                adjusted = self._adjust_timestamps(text, offset_minutes)
                all_text.append(adjusted)
            except Exception as e:
                logger.error("Segment %d failed: %s", i, e)
                all_text.append(f"[セグメント {i} の文字起こしに失敗: {e}]")
        return "\n\n".join(all_text)

    def _adjust_timestamps(self, text, offset_minutes):
        if offset_minutes == 0:
            return text
        lines = []
        for line in text.splitlines():
            if line.startswith("["):
                bracket_end = line.find("]")
                if bracket_end == -1:
                    lines.append(line)
                    continue
                ts = line[1:bracket_end]
                parts = ts.split(":")
                if len(parts) == 2:
                    try:
                        m, s = int(parts[0]), int(parts[1])
                    except ValueError:
                        lines.append(line)
                        continue
                    total = m + offset_minutes
                    h = total // 60
                    m = total % 60
                    if h > 0:
                        new_ts = f"[{h}:{m:02d}:{s:02d}]"
                    else:
                        new_ts = f"[{m:02d}:{s:02d}]"
                    line = new_ts + line[bracket_end + 1:]
            lines.append(line)
        return "\n".join(lines)
