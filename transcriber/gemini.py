import google.generativeai as genai


class GeminiTranscriber:
    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key):
        self._api_key = api_key
        genai.configure(api_key=api_key)

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
        model = genai.GenerativeModel(self.MODEL)
        audio_file = genai.upload_file(audio_path)
        response = model.generate_content([
            self._build_transcription_prompt(),
            audio_file,
        ])
        return response.text

    def transcribe_all(self, segment_paths, segment_duration=1800):
        all_text = []
        for i, path in enumerate(segment_paths):
            offset_minutes = (i * segment_duration) // 60
            text = self.transcribe_segment(path)
            adjusted = self._adjust_timestamps(text, offset_minutes)
            all_text.append(adjusted)
        return "\n\n".join(all_text)

    def _adjust_timestamps(self, text, offset_minutes):
        if offset_minutes == 0:
            return text
        lines = []
        for line in text.splitlines():
            if line.startswith("["):
                bracket_end = line.index("]")
                ts = line[1:bracket_end]
                parts = ts.split(":")
                if len(parts) == 2:
                    m, s = int(parts[0]), int(parts[1])
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
