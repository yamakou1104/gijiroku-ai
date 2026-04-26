import google.generativeai as genai

class MinutesGenerator:
    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key):
        self._api_key = api_key
        genai.configure(api_key=api_key)

    def _build_generation_prompt(self, transcript):
        return (
            "以下の文字起こしテキストから議事録を生成してください。\n\n"
            "## 出力フォーマット:\n"
            "```\n"
            "# 会議タイトル YYYY-MM-DD\n"
            "\n"
            "## 参加者\n"
            "話者名をカンマ区切りで\n"
            "\n"
            "---\n"
            "\n"
            "## 1. トピック名（開始時刻〜終了時刻）\n"
            "\n"
            "**話者名:** 発言内容\n"
            "\n"
            "（全発言を記録。要約ではなく全量構造化）\n"
            "\n"
            "---\n"
            "\n"
            "## アクションアイテム\n"
            "- [ ] 担当者: タスク内容（期限）\n"
            "```\n\n"
            "## ルール:\n"
            "- 全ての発言を漏れなく記録すること（要約しない）\n"
            "- フィラーは除去済み\n"
            "- Speaker1, Speaker2 等は可能なら文脈から実名に置換\n"
            "- トピックごとにセクション分け + タイムスタンプ付与\n"
            "- 最後にアクションアイテムをまとめる\n"
            "- Markdown形式で出力\n\n"
            "## 文字起こしテキスト:\n\n"
            f"{transcript}"
        )

    def generate(self, transcript):
        model = genai.GenerativeModel(self.MODEL)
        prompt = self._build_generation_prompt(transcript)
        response = model.generate_content(prompt)
        return response.text
