# 議事録生成AI 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 対面/オンライン会議を録音・録画し、Gemini APIで文字起こし＋議事録生成を行い、クラウドストレージに保存するデスクトップアプリを構築する。

**Architecture:** Python + Tkinter のデスクトップアプリ。FFmpegをサブプロセスで呼び出して録音/録画し、30分ごとにセグメント分割。各セグメントをGemini 2.5 Flash APIに送信して文字起こし→議事録生成。完成した議事録とメディアファイルをGoogle Drive / OneDriveにアップロード。

**Tech Stack:** Python 3.10, Tkinter, FFmpeg, google-generativeai, google-api-python-client, msal, plyer

---

## ファイル構成

```
gijiroku-ai/
  ├── DESIGN.md
  ├── requirements.txt
  ├── config.py              ← 設定管理（APIキー、保存先、デバイス）
  ├── main.py                ← エントリーポイント
  ├── ui/
  │    ├── __init__.py
  │    ├── app.py            ← Tkinter メインウィンドウ
  │    └── widgets.py        ← カスタムウィジェット
  ├── recorder/
  │    ├── __init__.py
  │    ├── audio.py          ← 対面モード録音
  │    └── screen.py         ← オンラインモード録画
  ├── uploader/
  │    ├── __init__.py
  │    ├── base.py           ← アップローダー基底クラス
  │    ├── google_drive.py   ← Google Drive連携
  │    └── onedrive.py       ← OneDrive連携
  ├── transcriber/
  │    ├── __init__.py
  │    └── gemini.py         ← Gemini API文字起こし
  ├── generator/
  │    ├── __init__.py
  │    └── minutes.py        ← Gemini API議事録生成
  ├── utils/
  │    ├── __init__.py
  │    ├── notification.py   ← デスクトップ通知
  │    └── file_manager.py   ← ファイル管理
  └── tests/
       ├── __init__.py
       ├── test_config.py
       ├── test_file_manager.py
       ├── test_audio_recorder.py
       ├── test_screen_recorder.py
       ├── test_transcriber.py
       ├── test_generator.py
       ├── test_google_drive.py
       ├── test_onedrive.py
       └── test_ui.py
```

---

## Task 1: プロジェクトスキャフォールディング

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Create: すべてのパッケージの `__init__.py`

- [ ] **Step 1: requirements.txt を作成**

```
google-generativeai>=0.8.0
google-api-python-client>=2.0.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.2.0
msal>=1.28.0
requests>=2.31.0
plyer>=2.1.0
pytest>=8.0.0
```

- [ ] **Step 2: パッケージの __init__.py を作成**

以下のディレクトリにそれぞれ空の `__init__.py` を作成:
- `ui/__init__.py`
- `recorder/__init__.py`
- `uploader/__init__.py`
- `transcriber/__init__.py`
- `generator/__init__.py`
- `utils/__init__.py`
- `tests/__init__.py`

- [ ] **Step 3: config.py のテストを書く**

```python
# tests/test_config.py
import os
import json
import tempfile
import pytest
from config import Config

@pytest.fixture
def config_path(tmp_path):
    return str(tmp_path / "config.json")

def test_default_config_created(config_path):
    cfg = Config(config_path)
    assert os.path.exists(config_path)

def test_default_values(config_path):
    cfg = Config(config_path)
    assert cfg.get("storage_provider") == "google_drive"
    assert cfg.get("gemini_api_key") == ""
    assert cfg.get("mic_device") == ""
    assert cfg.get("segment_duration") == 1800

def test_set_and_get(config_path):
    cfg = Config(config_path)
    cfg.set("gemini_api_key", "test-key-123")
    assert cfg.get("gemini_api_key") == "test-key-123"

def test_persistence(config_path):
    cfg1 = Config(config_path)
    cfg1.set("mic_device", "My Microphone")
    cfg2 = Config(config_path)
    assert cfg2.get("mic_device") == "My Microphone"

def test_get_unknown_key_returns_none(config_path):
    cfg = Config(config_path)
    assert cfg.get("nonexistent") is None
```

- [ ] **Step 4: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL (config module not found)

- [ ] **Step 5: config.py を実装**

```python
# config.py
import json
import os

DEFAULTS = {
    "storage_provider": "google_drive",
    "gemini_api_key": "",
    "mic_device": "",
    "segment_duration": 1800,
    "output_dir": "",
    "google_drive_credentials": "",
    "onedrive_credentials": "",
}

class Config:
    def __init__(self, path=None):
        if path is None:
            app_dir = os.path.join(os.path.expanduser("~"), ".gijiroku-ai")
            os.makedirs(app_dir, exist_ok=True)
            path = os.path.join(app_dir, "config.json")
        self._path = path
        self._data = dict(DEFAULTS)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._data.update(json.load(f))
        else:
            self._save()

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        self._data[key] = value
        self._save()

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
```

- [ ] **Step 6: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_config.py -v`
Expected: All 5 tests PASS

- [ ] **Step 7: 依存パッケージインストール**

Run: `pip install -r requirements.txt`

- [ ] **Step 8: コミット**

```bash
git add requirements.txt config.py ui/__init__.py recorder/__init__.py uploader/__init__.py transcriber/__init__.py generator/__init__.py utils/__init__.py tests/__init__.py tests/test_config.py
git commit -m "feat: project scaffolding with config management"
```

---

## Task 2: ファイル管理ユーティリティ

**Files:**
- Create: `utils/file_manager.py`
- Create: `tests/test_file_manager.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_file_manager.py
import os
import tempfile
import pytest
from utils.file_manager import FileManager

@pytest.fixture
def fm(tmp_path):
    return FileManager(str(tmp_path))

def test_create_session_dir(fm):
    session_dir = fm.create_session("テスト会議")
    assert os.path.isdir(session_dir)
    assert "テスト会議" in os.path.basename(session_dir)

def test_session_dir_has_date_prefix(fm):
    session_dir = fm.create_session("定例会議")
    dirname = os.path.basename(session_dir)
    # YYYY-MM-DD_会議名 の形式
    assert dirname[4] == "-"
    assert dirname[7] == "-"
    assert dirname[10] == "_"

def test_list_segments_empty(fm):
    session_dir = fm.create_session("test")
    segments = fm.list_segments(session_dir, ".wav")
    assert segments == []

def test_list_segments_sorted(fm):
    session_dir = fm.create_session("test")
    for name in ["recording_002.wav", "recording_000.wav", "recording_001.wav"]:
        open(os.path.join(session_dir, name), "w").close()
    segments = fm.list_segments(session_dir, ".wav")
    assert len(segments) == 3
    assert "recording_000.wav" in segments[0]
    assert "recording_002.wav" in segments[2]

def test_segment_offset(fm):
    assert fm.segment_offset(0, 1800) == 0
    assert fm.segment_offset(1, 1800) == 1800
    assert fm.segment_offset(2, 1800) == 3600

def test_format_timestamp():
    from utils.file_manager import FileManager
    assert FileManager.format_timestamp(0) == "00:00"
    assert FileManager.format_timestamp(65) == "01:05"
    assert FileManager.format_timestamp(3661) == "1:01:01"
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_file_manager.py -v`
Expected: FAIL

- [ ] **Step 3: file_manager.py を実装**

```python
# utils/file_manager.py
import os
from datetime import datetime

class FileManager:
    def __init__(self, base_dir):
        self._base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def create_session(self, meeting_name):
        date_str = datetime.now().strftime("%Y-%m-%d")
        dir_name = f"{date_str}_{meeting_name}"
        session_dir = os.path.join(self._base_dir, dir_name)
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def list_segments(self, session_dir, extension):
        files = [
            os.path.join(session_dir, f)
            for f in sorted(os.listdir(session_dir))
            if f.endswith(extension)
        ]
        return files

    def segment_offset(self, index, segment_duration):
        return index * segment_duration

    @staticmethod
    def format_timestamp(seconds):
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
```

- [ ] **Step 4: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_file_manager.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: コミット**

```bash
git add utils/file_manager.py tests/test_file_manager.py
git commit -m "feat: file manager utility for session dirs and segments"
```

---

## Task 3: 対面モード録音（audio.py）

**Files:**
- Create: `recorder/audio.py`
- Create: `tests/test_audio_recorder.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_audio_recorder.py
import os
import pytest
from unittest.mock import patch, MagicMock
from recorder.audio import AudioRecorder

@pytest.fixture
def recorder(tmp_path):
    return AudioRecorder(
        output_dir=str(tmp_path),
        mic_device="Test Microphone",
        segment_duration=1800,
    )

def test_build_command(recorder):
    cmd = recorder._build_command()
    assert "ffmpeg" in cmd[0]
    assert "-f" in cmd
    assert "dshow" in cmd
    assert "1800" in cmd
    assert "recording_%03d.wav" in " ".join(cmd)

def test_build_command_contains_mic_device(recorder):
    cmd = recorder._build_command()
    cmd_str = " ".join(cmd)
    assert "Test Microphone" in cmd_str

def test_is_recording_initially_false(recorder):
    assert recorder.is_recording is False

@patch("recorder.audio.subprocess.Popen")
def test_start_sets_recording_flag(mock_popen, recorder):
    mock_popen.return_value = MagicMock()
    recorder.start()
    assert recorder.is_recording is True

@patch("recorder.audio.subprocess.Popen")
def test_stop_clears_recording_flag(mock_popen, recorder):
    mock_proc = MagicMock()
    mock_popen.return_value = mock_proc
    recorder.start()
    recorder.stop()
    assert recorder.is_recording is False

@patch("recorder.audio.subprocess.Popen")
def test_stop_sends_q_to_ffmpeg(mock_popen, recorder):
    mock_proc = MagicMock()
    mock_popen.return_value = mock_proc
    recorder.start()
    recorder.stop()
    mock_proc.communicate.assert_called_once_with(input=b"q")

def test_list_devices_returns_list():
    with patch("recorder.audio.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stderr="[dshow] \"Microphone (Realtek)\" (audio)\n[dshow] \"Stereo Mix\" (audio)\n"
        )
        devices = AudioRecorder.list_devices()
        assert isinstance(devices, list)
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_audio_recorder.py -v`
Expected: FAIL

- [ ] **Step 3: audio.py を実装**

```python
# recorder/audio.py
import os
import re
import subprocess

class AudioRecorder:
    def __init__(self, output_dir, mic_device, segment_duration=1800):
        self._output_dir = output_dir
        self._mic_device = mic_device
        self._segment_duration = segment_duration
        self._process = None

    @property
    def is_recording(self):
        return self._process is not None

    def _build_command(self):
        output_pattern = os.path.join(self._output_dir, "recording_%03d.wav")
        return [
            "ffmpeg", "-y",
            "-f", "dshow",
            "-i", f"audio={self._mic_device}",
            "-ac", "1",
            "-ar", "16000",
            "-f", "segment",
            "-segment_time", str(self._segment_duration),
            "-reset_timestamps", "1",
            output_pattern,
        ]

    def start(self):
        if self._process is not None:
            return
        cmd = self._build_command()
        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self):
        if self._process is None:
            return
        self._process.communicate(input=b"q")
        self._process = None

    @staticmethod
    def list_devices():
        result = subprocess.run(
            ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True,
            text=True,
        )
        devices = []
        for line in result.stderr.splitlines():
            match = re.search(r'"(.+?)"\s+\(audio\)', line)
            if match:
                devices.append(match.group(1))
        return devices
```

- [ ] **Step 4: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_audio_recorder.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: コミット**

```bash
git add recorder/audio.py tests/test_audio_recorder.py
git commit -m "feat: audio recorder with FFmpeg segment recording"
```

---

## Task 4: オンラインモード録画（screen.py）

**Files:**
- Create: `recorder/screen.py`
- Create: `tests/test_screen_recorder.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_screen_recorder.py
import os
import pytest
from unittest.mock import patch, MagicMock
from recorder.screen import ScreenRecorder

@pytest.fixture
def recorder(tmp_path):
    return ScreenRecorder(
        output_dir=str(tmp_path),
        mic_device="Test Microphone",
        segment_duration=1800,
    )

def test_build_video_command(recorder):
    cmd = recorder._build_video_command()
    cmd_str = " ".join(cmd)
    assert "ffmpeg" in cmd_str
    assert "gdigrab" in cmd_str
    assert "desktop" in cmd_str
    assert ".mp4" in cmd_str

def test_build_audio_command(recorder):
    cmd = recorder._build_audio_command()
    cmd_str = " ".join(cmd)
    assert "ffmpeg" in cmd_str
    assert "dshow" in cmd_str
    assert "recording_%03d.wav" in cmd_str

def test_is_recording_initially_false(recorder):
    assert recorder.is_recording is False

@patch("recorder.screen.subprocess.Popen")
def test_start_sets_recording_flag(mock_popen, recorder):
    mock_popen.return_value = MagicMock()
    recorder.start()
    assert recorder.is_recording is True

@patch("recorder.screen.subprocess.Popen")
def test_stop_clears_flag(mock_popen, recorder):
    mock_proc = MagicMock()
    mock_popen.return_value = mock_proc
    recorder.start()
    recorder.stop()
    assert recorder.is_recording is False

@patch("recorder.screen.subprocess.Popen")
def test_start_launches_two_processes(mock_popen, recorder):
    mock_popen.return_value = MagicMock()
    recorder.start()
    assert mock_popen.call_count == 2
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_screen_recorder.py -v`
Expected: FAIL

- [ ] **Step 3: screen.py を実装**

```python
# recorder/screen.py
import os
import subprocess

class ScreenRecorder:
    def __init__(self, output_dir, mic_device, segment_duration=1800):
        self._output_dir = output_dir
        self._mic_device = mic_device
        self._segment_duration = segment_duration
        self._video_process = None
        self._audio_process = None

    @property
    def is_recording(self):
        return self._video_process is not None

    def _build_video_command(self):
        video_path = os.path.join(self._output_dir, "recording.mp4")
        return [
            "ffmpeg", "-y",
            "-f", "gdigrab",
            "-framerate", "10",
            "-i", "desktop",
            "-f", "dshow",
            "-i", f"audio={self._mic_device}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-c:a", "aac",
            video_path,
        ]

    def _build_audio_command(self):
        audio_pattern = os.path.join(self._output_dir, "recording_%03d.wav")
        return [
            "ffmpeg", "-y",
            "-f", "dshow",
            "-i", f"audio={self._mic_device}",
            "-ac", "1",
            "-ar", "16000",
            "-f", "segment",
            "-segment_time", str(self._segment_duration),
            "-reset_timestamps", "1",
            audio_pattern,
        ]

    def start(self):
        if self._video_process is not None:
            return
        self._video_process = subprocess.Popen(
            self._build_video_command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._audio_process = subprocess.Popen(
            self._build_audio_command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self):
        if self._video_process is None:
            return
        self._video_process.communicate(input=b"q")
        self._audio_process.communicate(input=b"q")
        self._video_process = None
        self._audio_process = None
```

- [ ] **Step 4: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_screen_recorder.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: コミット**

```bash
git add recorder/screen.py tests/test_screen_recorder.py
git commit -m "feat: screen recorder with FFmpeg gdigrab + audio segment"
```

---

## Task 5: Gemini API 文字起こし（transcriber）

**Files:**
- Create: `transcriber/gemini.py`
- Create: `tests/test_transcriber.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_transcriber.py
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
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_transcriber.py -v`
Expected: FAIL

- [ ] **Step 3: gemini.py を実装**

```python
# transcriber/gemini.py
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
```

- [ ] **Step 4: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_transcriber.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: コミット**

```bash
git add transcriber/gemini.py tests/test_transcriber.py
git commit -m "feat: Gemini API transcriber with segment timestamp offset"
```

---

## Task 6: 議事録生成（generator）

**Files:**
- Create: `generator/minutes.py`
- Create: `tests/test_generator.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_generator.py
import pytest
from unittest.mock import patch, MagicMock
from generator.minutes import MinutesGenerator

@pytest.fixture
def gen():
    return MinutesGenerator(api_key="test-key")

@patch("generator.minutes.genai")
def test_generate_returns_markdown(mock_genai, gen):
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(
        text="# 定例会議 2026-04-26\n\n## 参加者\n山本、田中"
    )
    mock_genai.GenerativeModel.return_value = mock_model

    transcript = "[00:00] Speaker1: テスト\n[00:05] Speaker2: テスト2"
    result = gen.generate(transcript)
    assert "# " in result
    assert isinstance(result, str)

def test_build_prompt_includes_format(gen):
    prompt = gen._build_generation_prompt("test transcript")
    assert "アクションアイテム" in prompt
    assert "タイムスタンプ" in prompt

@patch("generator.minutes.genai")
def test_generate_sends_transcript(mock_genai, gen):
    mock_model = MagicMock()
    mock_model.generate_content.return_value = MagicMock(text="# Minutes")
    mock_genai.GenerativeModel.return_value = mock_model

    gen.generate("test transcript")
    call_args = mock_model.generate_content.call_args[0][0]
    assert "test transcript" in call_args
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_generator.py -v`
Expected: FAIL

- [ ] **Step 3: minutes.py を実装**

```python
# generator/minutes.py
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
```

- [ ] **Step 4: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_generator.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: コミット**

```bash
git add generator/minutes.py tests/test_generator.py
git commit -m "feat: minutes generator with Gemini API"
```

---

## Task 7: Google Drive アップローダー

**Files:**
- Create: `uploader/base.py`
- Create: `uploader/google_drive.py`
- Create: `tests/test_google_drive.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_google_drive.py
import os
import pytest
from unittest.mock import patch, MagicMock
from uploader.base import BaseUploader
from uploader.google_drive import GoogleDriveUploader

def test_base_uploader_interface():
    assert hasattr(BaseUploader, "authenticate")
    assert hasattr(BaseUploader, "upload_file")
    assert hasattr(BaseUploader, "create_folder")

@pytest.fixture
def uploader():
    with patch("uploader.google_drive.build"):
        up = GoogleDriveUploader.__new__(GoogleDriveUploader)
        up._service = MagicMock()
        up._root_folder_id = None
        return up

def test_create_folder(uploader):
    mock_create = uploader._service.files.return_value.create
    mock_create.return_value.execute.return_value = {"id": "folder-123"}
    folder_id = uploader.create_folder("テスト会議")
    assert folder_id == "folder-123"

def test_upload_file(uploader, tmp_path):
    test_file = tmp_path / "test.wav"
    test_file.write_bytes(b"\x00" * 100)

    mock_create = uploader._service.files.return_value.create
    mock_create.return_value.execute.return_value = {"id": "file-456"}
    file_id = uploader.upload_file(str(test_file), "parent-123")
    assert file_id == "file-456"

def test_upload_session_calls_upload_for_each_file(uploader, tmp_path):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    (session_dir / "recording_000.wav").write_bytes(b"\x00" * 50)
    (session_dir / "minutes.md").write_text("# Test", encoding="utf-8")

    mock_create = uploader._service.files.return_value.create
    mock_create.return_value.execute.return_value = {"id": "id"}

    uploader.create_folder = MagicMock(return_value="folder-id")
    uploader.upload_file = MagicMock(return_value="file-id")

    uploader.upload_session(str(session_dir), "テスト会議")
    assert uploader.upload_file.call_count == 2
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_google_drive.py -v`
Expected: FAIL

- [ ] **Step 3: base.py を実装**

```python
# uploader/base.py
from abc import ABC, abstractmethod

class BaseUploader(ABC):
    @abstractmethod
    def authenticate(self):
        pass

    @abstractmethod
    def upload_file(self, file_path, parent_folder_id):
        pass

    @abstractmethod
    def create_folder(self, name, parent_folder_id=None):
        pass

    @abstractmethod
    def upload_session(self, session_dir, meeting_name):
        pass
```

- [ ] **Step 4: google_drive.py を実装**

```python
# uploader/google_drive.py
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from uploader.base import BaseUploader

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

class GoogleDriveUploader(BaseUploader):
    def __init__(self, credentials_path, token_path=None):
        self._credentials_path = credentials_path
        self._token_path = token_path or os.path.join(
            os.path.dirname(credentials_path), "gdrive_token.json"
        )
        self._service = None
        self._root_folder_id = None

    def authenticate(self):
        creds = None
        if os.path.exists(self._token_path):
            creds = Credentials.from_authorized_user_file(self._token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self._token_path, "w") as f:
                f.write(creds.to_json())
        self._service = build("drive", "v3", credentials=creds)
        self._ensure_root_folder()

    def _ensure_root_folder(self):
        results = (
            self._service.files()
            .list(
                q="name='議事録AI' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces="drive",
                fields="files(id)",
            )
            .execute()
        )
        files = results.get("files", [])
        if files:
            self._root_folder_id = files[0]["id"]
        else:
            self._root_folder_id = self.create_folder("議事録AI")

    def create_folder(self, name, parent_folder_id=None):
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_folder_id:
            metadata["parents"] = [parent_folder_id]
        folder = self._service.files().create(body=metadata, fields="id").execute()
        return folder["id"]

    def upload_file(self, file_path, parent_folder_id):
        metadata = {
            "name": os.path.basename(file_path),
            "parents": [parent_folder_id],
        }
        media = MediaFileUpload(file_path, resumable=True)
        result = (
            self._service.files()
            .create(body=metadata, media_body=media, fields="id")
            .execute()
        )
        return result["id"]

    def upload_session(self, session_dir, meeting_name):
        parent = self._root_folder_id
        folder_id = self.create_folder(meeting_name, parent)
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            if os.path.isfile(filepath):
                self.upload_file(filepath, folder_id)
        return folder_id
```

- [ ] **Step 5: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_google_drive.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: コミット**

```bash
git add uploader/base.py uploader/google_drive.py tests/test_google_drive.py
git commit -m "feat: Google Drive uploader with OAuth and session upload"
```

---

## Task 8: OneDrive アップローダー

**Files:**
- Create: `uploader/onedrive.py`
- Create: `tests/test_onedrive.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_onedrive.py
import os
import pytest
from unittest.mock import patch, MagicMock
from uploader.onedrive import OneDriveUploader

@pytest.fixture
def uploader():
    up = OneDriveUploader.__new__(OneDriveUploader)
    up._access_token = "test-token"
    return up

@patch("uploader.onedrive.requests.put")
def test_upload_file(mock_put, uploader, tmp_path):
    test_file = tmp_path / "test.wav"
    test_file.write_bytes(b"\x00" * 100)

    mock_put.return_value = MagicMock(status_code=201, json=lambda: {"id": "file-123"})
    file_id = uploader.upload_file(str(test_file), "/議事録AI/テスト")
    assert file_id == "file-123"

@patch("uploader.onedrive.requests.post")
def test_create_folder(mock_post, uploader):
    mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": "folder-456"})
    folder_id = uploader.create_folder("テスト会議", "/議事録AI")
    assert folder_id == "folder-456"

@patch("uploader.onedrive.requests.put")
@patch("uploader.onedrive.requests.post")
def test_upload_session(mock_post, mock_put, uploader, tmp_path):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    (session_dir / "recording_000.wav").write_bytes(b"\x00" * 50)

    mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": "f-id"})
    mock_put.return_value = MagicMock(status_code=201, json=lambda: {"id": "id"})

    uploader.create_folder = MagicMock(return_value="folder-id")
    uploader.upload_file = MagicMock(return_value="file-id")

    uploader.upload_session(str(session_dir), "テスト会議")
    assert uploader.upload_file.call_count == 1
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_onedrive.py -v`
Expected: FAIL

- [ ] **Step 3: onedrive.py を実装**

```python
# uploader/onedrive.py
import os
import json
import requests
import msal
from uploader.base import BaseUploader

GRAPH_URL = "https://graph.microsoft.com/v1.0"
SCOPES = ["Files.ReadWrite"]

class OneDriveUploader(BaseUploader):
    def __init__(self, client_id, authority=None, token_cache_path=None):
        self._client_id = client_id
        self._authority = authority or "https://login.microsoftonline.com/consumers"
        self._token_cache_path = token_cache_path
        self._access_token = None

    def authenticate(self):
        cache = msal.SerializableTokenCache()
        if self._token_cache_path and os.path.exists(self._token_cache_path):
            cache.deserialize(open(self._token_cache_path).read())

        app = msal.PublicClientApplication(
            self._client_id,
            authority=self._authority,
            token_cache=cache,
        )

        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
        else:
            result = None

        if not result:
            flow = app.initiate_device_flow(scopes=SCOPES)
            print(flow["message"])
            result = app.acquire_token_by_device_flow(flow)

        self._access_token = result["access_token"]

        if self._token_cache_path and cache.has_state_changed:
            with open(self._token_cache_path, "w") as f:
                f.write(cache.serialize())

    def _headers(self):
        return {"Authorization": f"Bearer {self._access_token}"}

    def create_folder(self, name, parent_path=None):
        parent = parent_path or "/drive/root:"
        url = f"{GRAPH_URL}/me{parent}:/children"
        body = {
            "name": name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename",
        }
        resp = requests.post(url, headers=self._headers(), json=body)
        resp.raise_for_status()
        return resp.json()["id"]

    def upload_file(self, file_path, parent_path):
        filename = os.path.basename(file_path)
        url = f"{GRAPH_URL}/me/drive/root:{parent_path}/{filename}:/content"
        with open(file_path, "rb") as f:
            resp = requests.put(url, headers=self._headers(), data=f)
        resp.raise_for_status()
        return resp.json()["id"]

    def upload_session(self, session_dir, meeting_name):
        root_path = "/drive/root:/議事録AI"
        self.create_folder("議事録AI")
        folder_path = f"/議事録AI/{meeting_name}"
        self.create_folder(meeting_name, root_path)
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            if os.path.isfile(filepath):
                self.upload_file(filepath, folder_path)
```

- [ ] **Step 4: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_onedrive.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: コミット**

```bash
git add uploader/onedrive.py tests/test_onedrive.py
git commit -m "feat: OneDrive uploader with MSAL device flow auth"
```

---

## Task 9: デスクトップ通知ユーティリティ

**Files:**
- Create: `utils/notification.py`

- [ ] **Step 1: notification.py を実装**

```python
# utils/notification.py
from plyer import notification as plyer_notification

def notify(title, message, timeout=10):
    plyer_notification.notify(
        title=title,
        message=message,
        app_name="議事録AI",
        timeout=timeout,
    )
```

- [ ] **Step 2: 動作確認**

Run: `python -c "from utils.notification import notify; notify('テスト', '通知テスト')"`
Expected: デスクトップ通知が表示される

- [ ] **Step 3: コミット**

```bash
git add utils/notification.py
git commit -m "feat: desktop notification utility"
```

---

## Task 10: Tkinter UI

**Files:**
- Create: `ui/widgets.py`
- Create: `ui/app.py`
- Create: `tests/test_ui.py`

- [ ] **Step 1: widgets.py を実装**

```python
# ui/widgets.py
import tkinter as tk
from tkinter import ttk

class ModeButton(tk.Frame):
    def __init__(self, parent, title, icon_text, description, command=None):
        super().__init__(parent, relief="raised", borderwidth=2, padx=20, pady=20)
        self._command = command

        self._title_label = tk.Label(
            self, text=title, font=("Meiryo UI", 14, "bold")
        )
        self._title_label.pack()

        self._icon_label = tk.Label(
            self, text=icon_text, font=("Segoe UI Emoji", 24)
        )
        self._icon_label.pack(pady=5)

        self._desc_label = tk.Label(
            self, text=description, font=("Meiryo UI", 9), fg="gray"
        )
        self._desc_label.pack()

        self.bind("<Button-1>", self._on_click)
        for child in self.winfo_children():
            child.bind("<Button-1>", self._on_click)

    def _on_click(self, event=None):
        if self._command:
            self._command()


class StatusBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._label = tk.Label(
            self, text="待機中", font=("Meiryo UI", 10), anchor="w"
        )
        self._label.pack(fill="x", padx=10)

        self._rec_indicator = tk.Label(
            self, text="", font=("Meiryo UI", 10), fg="red"
        )
        self._rec_indicator.pack(side="right", padx=10)

    def set_status(self, text):
        self._label.config(text=text)

    def set_recording(self, is_recording):
        self._rec_indicator.config(text="● REC" if is_recording else "")


class StorageSelector(tk.Frame):
    def __init__(self, parent, on_change=None):
        super().__init__(parent)
        self._var = tk.StringVar(value="google_drive")

        tk.Label(self, text="保存先:", font=("Meiryo UI", 10)).pack(side="left")

        self._combo = ttk.Combobox(
            self,
            textvariable=self._var,
            values=["google_drive", "onedrive"],
            state="readonly",
            width=15,
        )
        self._combo.pack(side="left", padx=5)
        if on_change:
            self._combo.bind("<<ComboboxSelected>>", lambda e: on_change(self._var.get()))

    @property
    def value(self):
        return self._var.get()

    @value.setter
    def value(self, val):
        self._var.set(val)
```

- [ ] **Step 2: app.py を実装**

```python
# ui/app.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from ui.widgets import ModeButton, StatusBar, StorageSelector

class App:
    def __init__(self, config, recorder_factory, uploader_factory, transcriber, generator):
        self._config = config
        self._recorder_factory = recorder_factory
        self._uploader_factory = uploader_factory
        self._transcriber = transcriber
        self._generator = generator
        self._recorder = None
        self._session_dir = None
        self._root = None

    def run(self):
        self._root = tk.Tk()
        self._root.title("議事録AI")
        self._root.geometry("450x350")
        self._root.resizable(False, False)

        self._build_ui()
        self._root.mainloop()

    def _build_ui(self):
        title_frame = tk.Frame(self._root)
        title_frame.pack(fill="x", pady=(10, 0))
        tk.Label(
            title_frame, text="議事録AI", font=("Meiryo UI", 18, "bold")
        ).pack(side="left", padx=20)

        self._status_bar = StatusBar(title_frame)
        self._status_bar.pack(side="right", padx=20)

        self._storage_selector = StorageSelector(
            self._root, on_change=self._on_storage_change
        )
        self._storage_selector.pack(pady=10)
        self._storage_selector.value = self._config.get("storage_provider")

        button_frame = tk.Frame(self._root)
        button_frame.pack(pady=10, padx=20, fill="x")

        self._face_btn = ModeButton(
            button_frame,
            title="対面",
            icon_text="\U0001f3a4",
            description="マイク音声のみ",
            command=self._start_face_to_face,
        )
        self._face_btn.pack(side="left", expand=True, fill="both", padx=(0, 5))

        self._online_btn = ModeButton(
            button_frame,
            title="オンライン",
            icon_text="\U0001f3a4\U0001f5a5",
            description="画面+音声",
            command=self._start_online,
        )
        self._online_btn.pack(side="right", expand=True, fill="both", padx=(5, 0))

        self._stop_btn = tk.Button(
            self._root,
            text="■ 停止 → 議事録生成",
            font=("Meiryo UI", 12),
            command=self._stop_and_generate,
            state="disabled",
            bg="#e74c3c",
            fg="white",
            height=2,
        )
        self._stop_btn.pack(fill="x", padx=20, pady=15)

    def _on_storage_change(self, value):
        self._config.set("storage_provider", value)

    def _start_face_to_face(self):
        self._start_recording("face_to_face")

    def _start_online(self):
        self._start_recording("online")

    def _start_recording(self, mode):
        mic = self._config.get("mic_device")
        if not mic:
            messagebox.showwarning("設定エラー", "マイクデバイスが設定されていません。")
            return

        self._recorder, self._session_dir = self._recorder_factory(mode)
        self._recorder.start()

        self._status_bar.set_recording(True)
        self._status_bar.set_status(f"録音中（{'対面' if mode == 'face_to_face' else 'オンライン'}）")
        self._face_btn.configure(state="disabled")
        self._online_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")

    def _stop_and_generate(self):
        if self._recorder is None:
            return

        self._recorder.stop()
        self._status_bar.set_recording(False)
        self._status_bar.set_status("処理中...")
        self._stop_btn.configure(state="disabled")

        threading.Thread(target=self._process_pipeline, daemon=True).start()

    def _process_pipeline(self):
        try:
            from utils.file_manager import FileManager
            fm = FileManager(self._session_dir)
            segments = fm.list_segments(self._session_dir, ".wav")

            self._root.after(0, lambda: self._status_bar.set_status("文字起こし中..."))
            transcript = self._transcriber.transcribe_all(
                segments,
                segment_duration=self._config.get("segment_duration"),
            )

            transcript_path = os.path.join(self._session_dir, "transcript.txt")
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript)

            self._root.after(0, lambda: self._status_bar.set_status("議事録生成中..."))
            minutes = self._generator.generate(transcript)

            minutes_path = os.path.join(self._session_dir, "minutes.md")
            with open(minutes_path, "w", encoding="utf-8") as f:
                f.write(minutes)

            self._root.after(0, lambda: self._status_bar.set_status("アップロード中..."))
            uploader = self._uploader_factory()
            meeting_name = os.path.basename(self._session_dir)
            uploader.upload_session(self._session_dir, meeting_name)

            from utils.notification import notify
            notify("議事録AI", "議事録が完成しました")

            self._root.after(0, self._reset_ui)

        except Exception as e:
            self._root.after(
                0,
                lambda: messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}"),
            )
            self._root.after(0, self._reset_ui)

    def _reset_ui(self):
        self._status_bar.set_status("待機中")
        self._face_btn.configure(state="normal")
        self._online_btn.configure(state="normal")
        self._recorder = None
        self._session_dir = None
```

- [ ] **Step 3: UI テストを書く**

```python
# tests/test_ui.py
import pytest
from unittest.mock import MagicMock
from config import Config

def test_storage_selector_default(tmp_path):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    from ui.widgets import StorageSelector
    selector = StorageSelector(root)
    assert selector.value == "google_drive"
    root.destroy()

def test_storage_selector_set_value(tmp_path):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    from ui.widgets import StorageSelector
    selector = StorageSelector(root)
    selector.value = "onedrive"
    assert selector.value == "onedrive"
    root.destroy()

def test_status_bar(tmp_path):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    from ui.widgets import StatusBar
    bar = StatusBar(root)
    bar.set_status("テスト")
    assert bar._label.cget("text") == "テスト"
    bar.set_recording(True)
    assert "REC" in bar._rec_indicator.cget("text")
    bar.set_recording(False)
    assert bar._rec_indicator.cget("text") == ""
    root.destroy()
```

- [ ] **Step 4: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_ui.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: コミット**

```bash
git add ui/widgets.py ui/app.py tests/test_ui.py
git commit -m "feat: Tkinter UI with mode buttons and status bar"
```

---

## Task 11: メインエントリーポイント + 統合

**Files:**
- Create: `main.py`

- [ ] **Step 1: main.py を実装**

```python
# main.py
import os
import sys
from config import Config
from ui.app import App
from recorder.audio import AudioRecorder
from recorder.screen import ScreenRecorder
from transcriber.gemini import GeminiTranscriber
from generator.minutes import MinutesGenerator
from uploader.google_drive import GoogleDriveUploader
from uploader.onedrive import OneDriveUploader
from utils.file_manager import FileManager

def create_app():
    config = Config()

    output_base = config.get("output_dir")
    if not output_base:
        output_base = os.path.join(os.path.expanduser("~"), "gijiroku-ai-data")
        config.set("output_dir", output_base)
    os.makedirs(output_base, exist_ok=True)

    fm = FileManager(output_base)

    api_key = config.get("gemini_api_key")
    transcriber = GeminiTranscriber(api_key=api_key) if api_key else None
    generator = MinutesGenerator(api_key=api_key) if api_key else None

    def recorder_factory(mode):
        mic = config.get("mic_device")
        segment_duration = config.get("segment_duration")
        session_dir = fm.create_session("会議")

        if mode == "face_to_face":
            recorder = AudioRecorder(
                output_dir=session_dir,
                mic_device=mic,
                segment_duration=segment_duration,
            )
        else:
            recorder = ScreenRecorder(
                output_dir=session_dir,
                mic_device=mic,
                segment_duration=segment_duration,
            )
        return recorder, session_dir

    def uploader_factory():
        provider = config.get("storage_provider")
        if provider == "google_drive":
            creds_path = config.get("google_drive_credentials")
            uploader = GoogleDriveUploader(credentials_path=creds_path)
        else:
            client_id = config.get("onedrive_credentials")
            uploader = OneDriveUploader(client_id=client_id)
        uploader.authenticate()
        return uploader

    app = App(
        config=config,
        recorder_factory=recorder_factory,
        uploader_factory=uploader_factory,
        transcriber=transcriber,
        generator=generator,
    )
    return app

def main():
    app = create_app()
    app.run()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: import 確認**

Run: `python -c "from main import create_app; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 全テスト実行**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: コミット**

```bash
git add main.py
git commit -m "feat: main entry point with full pipeline integration"
```

---

## Task 12: 初回セットアップ画面

**Files:**
- Modify: `ui/app.py`
- Create: `ui/setup.py`

- [ ] **Step 1: setup.py を実装**

```python
# ui/setup.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from recorder.audio import AudioRecorder

class SetupWizard:
    def __init__(self, config, on_complete):
        self._config = config
        self._on_complete = on_complete
        self._root = None

    def run(self):
        self._root = tk.Tk()
        self._root.title("議事録AI - 初回セットアップ")
        self._root.geometry("500x450")
        self._root.resizable(False, False)

        tk.Label(
            self._root, text="初回セットアップ", font=("Meiryo UI", 16, "bold")
        ).pack(pady=15)

        frame = tk.Frame(self._root, padx=30)
        frame.pack(fill="both", expand=True)

        # Step 1: Gemini API key
        tk.Label(frame, text="1. Gemini APIキー", font=("Meiryo UI", 11, "bold")).pack(
            anchor="w", pady=(10, 2)
        )
        tk.Label(frame, text="Google AI Studio から取得", font=("Meiryo UI", 8), fg="gray").pack(anchor="w")
        self._api_key_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._api_key_var, width=50, show="*").pack(
            anchor="w", pady=(0, 5)
        )

        # Step 2: Storage
        tk.Label(frame, text="2. クラウドストレージ", font=("Meiryo UI", 11, "bold")).pack(
            anchor="w", pady=(10, 2)
        )
        self._storage_var = tk.StringVar(value="google_drive")
        storage_frame = tk.Frame(frame)
        storage_frame.pack(anchor="w")
        tk.Radiobutton(
            storage_frame, text="Google Drive", variable=self._storage_var, value="google_drive"
        ).pack(side="left")
        tk.Radiobutton(
            storage_frame, text="OneDrive", variable=self._storage_var, value="onedrive"
        ).pack(side="left", padx=10)

        # Step 3: Microphone
        tk.Label(frame, text="3. マイクデバイス", font=("Meiryo UI", 11, "bold")).pack(
            anchor="w", pady=(10, 2)
        )
        self._mic_var = tk.StringVar()
        self._mic_combo = ttk.Combobox(
            frame, textvariable=self._mic_var, state="readonly", width=45
        )
        self._mic_combo.pack(anchor="w", pady=(0, 5))

        tk.Button(frame, text="マイク一覧を更新", command=self._refresh_mics).pack(
            anchor="w"
        )

        # Save button
        tk.Button(
            self._root,
            text="設定を保存して開始",
            font=("Meiryo UI", 12),
            command=self._save,
            bg="#2ecc71",
            fg="white",
            height=2,
        ).pack(fill="x", padx=30, pady=15)

        self._refresh_mics()
        self._root.mainloop()

    def _refresh_mics(self):
        try:
            devices = AudioRecorder.list_devices()
            self._mic_combo["values"] = devices
            if devices:
                self._mic_combo.current(0)
        except Exception:
            self._mic_combo["values"] = ["(デバイスを検出できません)"]

    def _save(self):
        api_key = self._api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("入力エラー", "Gemini APIキーを入力してください。")
            return

        mic = self._mic_var.get()
        if not mic or mic.startswith("("):
            messagebox.showwarning("入力エラー", "マイクデバイスを選択してください。")
            return

        self._config.set("gemini_api_key", api_key)
        self._config.set("storage_provider", self._storage_var.get())
        self._config.set("mic_device", mic)
        self._config.set("setup_complete", True)

        self._root.destroy()
        self._on_complete()
```

- [ ] **Step 2: main.py を更新してセットアップウィザードを統合**

`main.py` の `main()` を以下に変更:

```python
def main():
    config = Config()

    if not config.get("setup_complete"):
        from ui.setup import SetupWizard
        wizard = SetupWizard(config, on_complete=lambda: _launch_app(config))
        wizard.run()
    else:
        _launch_app(config)

def _launch_app(config):
    app = create_app_with_config(config)
    app.run()
```

`create_app` を `create_app_with_config(config)` にリネームし、引数で `config` を受け取るように変更。

- [ ] **Step 3: 動作確認**

Run: `python main.py`
Expected: 初回はセットアップウィザードが表示される

- [ ] **Step 4: コミット**

```bash
git add ui/setup.py main.py
git commit -m "feat: setup wizard for first-time configuration"
```

---

## 補足事項

### 環境要件
- Python 3.10+
- FFmpeg がPATHに存在すること（確認済み）
- Windows 11

### 開発時の注意
- Gemini API のテストは mock を使用。実際の API テストは API キー設定後に手動で実施
- Google Drive / OneDrive の OAuth 認証は各サービスの開発者コンソールでクレデンシャルを作成する必要がある
- Tkinter テストはヘッドレス環境（CI）では `DISPLAY` 設定が必要な場合がある
