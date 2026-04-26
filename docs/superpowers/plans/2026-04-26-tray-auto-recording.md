# タスクトレイ常駐 + 自動録音 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 会議アプリ（Zoom / Teams / Google Meet）のウィンドウを自動検知して録音を開始・停止し、議事���を自動生成するシステムトレイ常駐アプリを構築する。

**Architecture:** `tray/monitor.py` が5秒間隔でウィンドウタイトルを監視。検知結果を `tray/app.py` の状態マシン（IDLE → RECORDING → GRACE_PERIOD → PROCESSING → IDLE）が処理��る。パイプライン処理（文字起こし→議事録生成→アップロード）は `pipeline.py` に抽出して tray/app.py と ui/app.py の両方から共用する。

**Tech Stack:** pystray, Pillow, pywin32 (win32gui), 既存モジュール群

---

## ファイル構成

```
gijiroku-ai/
  ├─�� tray/
  │    ├── __init__.py
  │    ├── monitor.py      ← ウィンドウタイトル監視（新規）
  │    ├── icons.py        ← アイコン生成（新規）
  │    └── app.py          ← トレイアプリ + 状態マシン（新規）
  ├── pipeline.py          ← パイプライン処理を ui/app.py から抽出（新規）
  ├── main.py              ← エントリーポイント変更（修正）
  ├── requirements.txt     ← パッケージ追加（修正）
  └── tests/
       ├── test_monitor.py
       ├── test_icons.py
       ├── test_tray_app.py
       └── test_pipeline.py
```

---

## Task 1: 依存パッケージ追���

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: requirements.txt にパッケージを追加**

`requirements.txt` の末尾に以下を追加:

```
pystray>=0.19.0
Pillow>=10.0.0
pywin32>=306
```

- [ ] **Step 2: インストール**

Run: `pip install pystray Pillow pywin32`

- [ ] **Step 3: tray/__init__.py を作成**

空ファイルを `tray/__init__.py` に作成。

- [ ] **Step 4: コミット**

```bash
git add requirements.txt tray/__init__.py
git commit -m "feat: add tray dependencies (pystray, Pillow, pywin32)"
```

---

## Task 2: ウィンドウタイトル監視（tray/monitor.py）

**Files:**
- Create: `tray/monitor.py`
- Create: `tests/test_monitor.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_monitor.py
import pytest
from unittest.mock import patch, MagicMock
from tray.monitor import MeetingMonitor

@pytest.fixture
def monitor():
    return MeetingMonitor()

def test_no_meeting_windows(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        windows = []
        def enum_cb(callback, _):
            for hwnd, title in windows:
                callback(hwnd, None)
        mock_gui.EnumWindows.side_effect = enum_cb
        mock_gui.GetWindowText.return_value = "Notepad"
        mock_gui.IsWindowVisible.return_value = True

        assert monitor.detect() is False

def test_detect_zoom_meeting(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        titles = {"Zoom Meeting"}
        call_count = [0]
        def enum_windows(callback, _):
            for i, title in enumerate(titles):
                callback(i, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.side_effect = lambda hwnd: list(titles)[hwnd]
        mock_gui.IsWindowVisible.return_value = True

        assert monitor.detect() is True

def test_detect_teams(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        def enum_windows(callback, _):
            callback(0, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.return_value = "Microsoft Teams"
        mock_gui.IsWindowVisible.return_value = True

        assert monitor.detect() is True

def test_detect_google_meet(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        def enum_windows(callback, _):
            callback(0, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.return_value = "Meet - abc-defg-hij - Google Chrome"
        mock_gui.IsWindowVisible.return_value = True

        assert monitor.detect() is True

def test_ignore_invisible_windows(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        def enum_windows(callback, _):
            callback(0, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.return_value = "Zoom Meeting"
        mock_gui.IsWindowVisible.return_value = False

        assert monitor.detect() is False

def test_detect_zoom_webinar(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        def enum_windows(callback, _):
            callback(0, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.return_value = "Zoom Webinar"
        mock_gui.IsWindowVisible.return_value = True

        assert monitor.detect() is True
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_monitor.py -v`
Expected: FAIL

- [ ] **Step 3: monitor.py を実装**

```python
# tray/monitor.py
import win32gui

MEETING_PATTERNS = [
    "zoom meeting",
    "zoom webinar",
    "microsoft teams",
    "meet - ",
]

class MeetingMonitor:
    def detect(self):
        self._found = False
        try:
            win32gui.EnumWindows(self._check_window, None)
        except Exception:
            pass
        return self._found

    def _check_window(self, hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).lower()
        for pattern in MEETING_PATTERNS:
            if pattern in title:
                self._found = True
```

- [ ] **Step 4: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_monitor.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: コミット**

```bash
git add tray/monitor.py tests/test_monitor.py
git commit -m "feat: meeting window monitor with title pattern matching"
```

---

## Task 3: アイコン生成（tray/icons.py）

**Files:**
- Create: `tray/icons.py`
- Create: `tests/test_icons.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_icons.py
import pytest
from PIL import Image
from tray.icons import create_icon

def test_create_idle_icon():
    icon = create_icon("idle")
    assert isinstance(icon, Image.Image)
    assert icon.size == (64, 64)

def test_create_recording_icon():
    icon = create_icon("recording")
    assert isinstance(icon, Image.Image)
    assert icon.size == (64, 64)

def test_create_processing_icon():
    icon = create_icon("processing")
    assert isinstance(icon, Image.Image)
    assert icon.size == (64, 64)

def test_idle_and_recording_differ():
    idle = create_icon("idle")
    rec = create_icon("recording")
    assert idle.tobytes() != rec.tobytes()

def test_unknown_state_returns_idle():
    icon = create_icon("unknown")
    idle = create_icon("idle")
    assert icon.tobytes() == idle.tobytes()
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_icons.py -v`
Expected: FAIL

- [ ] **Step 3: icons.py を実装**

```python
# tray/icons.py
from PIL import Image, ImageDraw

ICON_SIZE = 64

COLORS = {
    "idle": "#607D8B",
    "recording": "#E53935",
    "processing": "#FDD835",
}

def create_icon(state):
    color = COLORS.get(state, COLORS["idle"])
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = 4
    draw.ellipse(
        [margin, margin, ICON_SIZE - margin, ICON_SIZE - margin],
        fill=color,
    )
    draw.text(
        (ICON_SIZE // 2 - 6, ICON_SIZE // 2 - 8),
        "録",
        fill="white",
    )
    return image
```

- [ ] **Step 4: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_icons.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: コミット**

```bash
git add tray/icons.py tests/test_icons.py
git commit -m "feat: tray icon generator for idle/recording/processing states"
```

---

## Task 4: パイプライン処理の抽出（pipeline.py）

**Files:**
- Create: `pipeline.py`
- Create: `tests/test_pipeline.py`
- Modify: `ui/app.py` (パイプライン処理をpipeline.pyに置き換え)

- [ ] **Step 1: テストを書く**

```python
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
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: FAIL

- [ ] **Step 3: pipeline.py を実装**

```python
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
```

- [ ] **Step 4: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: ui/app.py を pipeline.py を使うよう修正**

`ui/app.py` の `_process_pipeline` メソッドを `Pipeline` クラスを使うよう書き換える。

変更前 (`ui/app.py` の `__init__` と `_process_pipeline`):

`__init__` に `pipeline` パラメータを追加:

```python
class App:
    def __init__(self, config, recorder_factory, uploader_factory, transcriber, generator, pipeline):
        self._config = config
        self._recorder_factory = recorder_factory
        self._pipeline = pipeline
        self._recorder = None
        self._session_dir = None
        self._root = None
```

`_process_pipeline` を書き換え:

```python
    def _process_pipeline(self):
        try:
            def on_status(msg):
                self._root.after(0, lambda: self._status_bar.set_status(msg))

            self._pipeline.run(self._session_dir, on_status=on_status)
            self._root.after(0, self._reset_ui)

        except Exception as e:
            self._root.after(
                0,
                lambda: messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}"),
            )
            self._root.after(0, self._reset_ui)
```

不要になった import (`from utils.file_manager import FileManager`, `from utils.notification import notify`) と `self._uploader_factory`, `self._transcriber`, `self._generator` を削除。

- [ ] **Step 6: 既存テスト実行 → 全パス確認**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: コミット**

```bash
git add pipeline.py tests/test_pipeline.py ui/app.py
git commit -m "refactor: extract pipeline from ui/app into shared pipeline.py"
```

---

## Task 5: トレイアプリケーション（tray/app.py）

**Files:**
- Create: `tray/app.py`
- Create: `tests/test_tray_app.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_tray_app.py
import pytest
from unittest.mock import MagicMock, patch
from tray.app import TrayApp, State

def make_tray_app():
    config = MagicMock()
    config.get.side_effect = lambda key: {
        "mic_device": "Test Mic",
        "segment_duration": 1800,
    }.get(key)
    recorder_factory = MagicMock()
    pipeline = MagicMock()
    monitor = MagicMock()
    return TrayApp(
        config=config,
        recorder_factory=recorder_factory,
        pipeline=pipeline,
        monitor=monitor,
    )

def test_initial_state_is_idle():
    app = make_tray_app()
    assert app.state == State.IDLE

def test_meeting_detected_starts_recording():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING
    app._recorder_factory.assert_called_once_with("online")

def test_meeting_lost_enters_grace_period():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING

    app._monitor.detect.return_value = False
    app.tick()
    assert app.state == State.GRACE_PERIOD

def test_meeting_returns_during_grace_period():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()

    app._monitor.detect.return_value = False
    app.tick()
    assert app.state == State.GRACE_PERIOD

    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING

def test_grace_period_expires_starts_processing():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()

    app._monitor.detect.return_value = False
    app.tick()
    assert app.state == State.GRACE_PERIOD

    app._grace_deadline = 0
    app.tick()
    assert app.state == State.PROCESSING

def test_processing_completes_returns_to_idle():
    app = make_tray_app()
    app._state = State.PROCESSING
    app._session_dir = "/tmp/test"
    app._pipeline.run.return_value = None

    app.tick()
    assert app.state == State.IDLE

def test_manual_face_to_face_starts_recording():
    app = make_tray_app()
    app.start_face_to_face()
    assert app.state == State.RECORDING
    app._recorder_factory.assert_called_once_with("face_to_face")

def test_manual_stop_from_recording():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING

    app.manual_stop()
    assert app.state == State.PROCESSING
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_tray_app.py -v`
Expected: FAIL

- [ ] **Step 3: tray/app.py を実装**

```python
# tray/app.py
import time
import threading
from enum import Enum
import pystray
from tray.icons import create_icon
from tray.monitor import MeetingMonitor

GRACE_PERIOD_SECONDS = 300
POLL_INTERVAL_SECONDS = 5

class State(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    GRACE_PERIOD = "grace_period"
    PROCESSING = "processing"

class TrayApp:
    def __init__(self, config, recorder_factory, pipeline, monitor=None):
        self._config = config
        self._recorder_factory = recorder_factory
        self._pipeline = pipeline
        self._monitor = monitor or MeetingMonitor()
        self._state = State.IDLE
        self._recorder = None
        self._session_dir = None
        self._grace_deadline = 0
        self._tray_icon = None
        self._running = False

    @property
    def state(self):
        return self._state

    def tick(self):
        if self._state == State.IDLE:
            if self._monitor.detect():
                self._start_recording("online")

        elif self._state == State.RECORDING:
            if not self._monitor.detect():
                self._state = State.GRACE_PERIOD
                self._grace_deadline = time.time() + GRACE_PERIOD_SECONDS
                self._update_icon()

        elif self._state == State.GRACE_PERIOD:
            if self._monitor.detect():
                self._state = State.RECORDING
                self._update_icon()
            elif time.time() >= self._grace_deadline:
                self._stop_recording()

        elif self._state == State.PROCESSING:
            self._run_pipeline()

    def start_face_to_face(self):
        if self._state != State.IDLE:
            return
        self._start_recording("face_to_face")

    def manual_stop(self):
        if self._state in (State.RECORDING, State.GRACE_PERIOD):
            self._stop_recording()

    def _start_recording(self, mode):
        self._recorder, self._session_dir = self._recorder_factory(mode)
        self._recorder.start()
        self._state = State.RECORDING
        self._update_icon()

    def _stop_recording(self):
        if self._recorder:
            self._recorder.stop()
            self._recorder = None
        self._state = State.PROCESSING
        self._update_icon()

    def _run_pipeline(self):
        try:
            self._pipeline.run(self._session_dir)
        except Exception:
            pass
        self._session_dir = None
        self._state = State.IDLE
        self._update_icon()

    def _update_icon(self):
        if self._tray_icon:
            self._tray_icon.icon = create_icon(self._state.value)

    def run(self):
        self._running = True
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()

        menu = pystray.Menu(
            pystray.MenuItem("対面モードで録音開始", lambda: self.start_face_to_face()),
            pystray.MenuItem("録音停止", lambda: self.manual_stop()),
            pystray.MenuItem("設定", lambda: self._open_settings()),
            pystray.MenuItem("終了", lambda: self.quit()),
        )

        self._tray_icon = pystray.Icon(
            name="gijiroku-ai",
            icon=create_icon("idle"),
            title="議事録AI",
            menu=menu,
        )
        self._tray_icon.run()

    def _monitor_loop(self):
        while self._running:
            self.tick()
            time.sleep(POLL_INTERVAL_SECONDS)

    def _open_settings(self):
        from ui.setup import SetupWizard
        SetupWizard(self._config, on_complete=lambda: None).run()

    def quit(self):
        self._running = False
        if self._recorder:
            self._recorder.stop()
        if self._tray_icon:
            self._tray_icon.stop()
```

- [ ] **Step 4: テスト実行 → 全パス確認**

Run: `python -m pytest tests/test_tray_app.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: コミット**

```bash
git add tray/app.py tests/test_tray_app.py
git commit -m "feat: tray app with state machine and auto-recording"
```

---

## Task 6: main.py の統合

**Files:**
- Modify: `main.py`

- [ ] **Step 1: main.py を���き換え**

```python
# main.py
import os
import sys
from config import Config
from recorder.audio import AudioRecorder
from recorder.screen import ScreenRecorder
from transcriber.gemini import GeminiTranscriber
from generator.minutes import MinutesGenerator
from uploader.google_drive import GoogleDriveUploader
from uploader.onedrive import OneDriveUploader
from utils.file_manager import FileManager
from pipeline import Pipeline


def _build_components(config):
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

    pipeline = Pipeline(
        config=config,
        transcriber=transcriber,
        generator=generator,
        uploader_factory=uploader_factory,
    )

    return recorder_factory, pipeline


def _launch_tray(config):
    from tray.app import TrayApp
    recorder_factory, pipeline = _build_components(config)
    app = TrayApp(
        config=config,
        recorder_factory=recorder_factory,
        pipeline=pipeline,
    )
    app.run()


def _launch_gui(config):
    from ui.app import App
    recorder_factory, pipeline = _build_components(config)
    app = App(
        config=config,
        recorder_factory=recorder_factory,
        pipeline=pipeline,
    )
    app.run()


def main():
    config = Config()
    use_gui = "--gui" in sys.argv

    if not config.get("setup_complete"):
        from ui.setup import SetupWizard
        if use_gui:
            wizard = SetupWizard(config, on_complete=lambda: _launch_gui(config))
        else:
            wizard = SetupWizard(config, on_complete=lambda: _launch_tray(config))
        wizard.run()
    else:
        if use_gui:
            _launch_gui(config)
        else:
            _launch_tray(config)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: import 確認**

Run: `python -c "from main import _build_components; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 全テスト実行**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: コミット**

```bash
git add main.py
git commit -m "feat: integrate tray mode as default, --gui for Tkinter UI"
```

---

## 補足事項

### 起動方法
- `python main.py` → トレイ常駐モード（デフォルト）
- `python main.py --gui` → 従来のTkinter GUI

### テスト時���注意
- `win32gui` は Windows 専用。テストでは全てモックする
- `pystray.Icon.run()` はブロッキング呼び出し。テストでは呼ばない
- パイプラインテストでは `notify()` がデスクトップ通知を出すため、CI環境では注意
