# 議事録AI 実装仕様書

> **作成日**: 2026-05-15
> **対象**: REQUIREMENTS.md 全8ゴール + 既存バグ修正
> **実施順序**: Phase 0 → Phase 1 → ... → Phase 8（依存関係順）

---

## 目次

- [Phase 0: 既存バグ修正（前提条件）](#phase-0-既存バグ修正前提条件)
- [Phase 1: Goal 3 — 依存関係とプロジェクト構成の整備](#phase-1-goal-3--依存関係とプロジェクト構成の整備)
- [Phase 2: Goal 5 — エラーハンドリングとリトライ機構](#phase-2-goal-5--エラーハンドリングとリトライ機構)
- [Phase 3: Goal 6 — スレッド安全性の確保](#phase-3-goal-6--スレッド安全性の確保)
- [Phase 4: Goal 1 — macOS対応 レコーダー](#phase-4-goal-1--macos対応-レコーダー)
- [Phase 5: Goal 2 — macOS対応 ウィンドウ検出](#phase-5-goal-2--macos対応-ウィンドウ検出)
- [Phase 6: Goal 4 — FFmpegセットアップ統合](#phase-6-goal-4--ffmpegセットアップ統合)
- [Phase 7: Goal 7 — OneDrive大容量ファイルアップロード](#phase-7-goal-7--onedrive大容量ファイルアップロード)
- [Phase 8: Goal 8 — テスト基盤の修正とカバレッジ向上](#phase-8-goal-8--テスト基盤の修正とカバレッジ向上)
- [付録A: 新規作成ファイル一覧](#付録a-新規作成ファイル一覧)
- [付録B: 全修正ファイルマトリクス](#付録b-全修正ファイルマトリクス)

---

## Phase 0: 既存バグ修正（前提条件）

ソースコード精読で発見した、REQUIREMENTS.mdに記載のない既存バグ。全Goalの実装前に修正必須。

---

### BUG-01: `generator/minutes.py:46` — 未定義変数 `prompt` の使用

**現状コード (L44-47):**
```python
def generate(self, transcript):
    model = genai.GenerativeModel(self.MODEL)
    response = model.generate_content(prompt)  # ← "prompt" は未定義
    return response.text
```

**問題:** `prompt` が定義されていない。`self._build_generation_prompt(transcript)` の戻り値を渡すべき。このバグにより `generate()` は常に `NameError` で失敗する。テストが通っているのは `mock_model.generate_content` がモックされているため。

**修正後:**
```python
def generate(self, transcript):
    model = genai.GenerativeModel(self.MODEL)
    prompt = self._build_generation_prompt(transcript)
    response = model.generate_content(prompt)
    return response.text
```

---

### BUG-02: `main.py:97-101` — if/else のインデント構文エラー

**現状コード (L94-107):**
```python
def main():
    config = Config()
    use_gui = "--gui" in sys.argv

    if not config.get("setup_complete"):
        from ui.setup import SetupWizard
        wizard = SetupWizard(config, on_complete=lambda: _launch_gui(config))
        else:                    # ← if use_gui の else のはずだが、インデントが不正
            wizard = SetupWizard(config, on_complete=lambda: _launch_tray(config))
        wizard.run()
    else:
        if use_gui:
            _launch_gui(config)
        else:
            _launch_tray(config)
```

**問題:** `else:` (L100) が `if use_gui:` に対応するはずだが、`use_gui` の判定自体が欠落。L99 は常に GUI モードのコールバックを渡している。

**修正後:**
```python
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
```

---

### BUG-03: `tray/app.py:41-42` — if ブロックのインデント欠落

**現状コード (L40-44):**
```python
elif self._state == State.RECORDING:
    if not self._monitor.detect():
    self._state = State.GRACE_PERIOD          # ← インデント不足。if のボディがない
    self._grace_deadline = time.time() + GRACE_PERIOD_SECONDS
    self._update_icon()
```

**問題:** `if not self._monitor.detect():` の次の行がインデントされていないため `SyntaxError`。

**修正後:**
```python
elif self._state == State.RECORDING:
    if not self._monitor.detect():
        self._state = State.GRACE_PERIOD
        self._grace_deadline = time.time() + GRACE_PERIOD_SECONDS
        self._update_icon()
```

---

### BUG-04: `tray/app.py:117-118` — `_open_settings` のインデント過剰

**現状コード (L116-118):**
```python
def _open_settings(self):
    from ui.setup import SetupWizard
        SetupWizard(self._config, on_complete=lambda: None).run()  # ← 過剰インデント
```

**修正後:**
```python
def _open_settings(self):
    from ui.setup import SetupWizard
    SetupWizard(self._config, on_complete=lambda: None).run()
```

---

### BUG-05: `recorder/screen.py:39` — `-c` は `-ac` の誤り

**現状コード (L33-45):**
```python
def _build_audio_command(self):
    audio_pattern = os.path.join(self._output_dir, "recording_%03d.wav")
    return [
        "ffmpeg", "-y",
        "-f", "dshow",
        "-i", f"audio={self._mic_device}",
        "-c", "1",                     # ← "-ac" の誤り。-c はコーデック指定
        "-ar", "16000",
        ...
    ]
```

**問題:** `-c 1` は「コーデックを `1` にせよ」と解釈され、FFmpeg がエラーになる。`-ac 1`（audio channels = 1）が正しい。`recorder/audio.py:23` では正しく `-ac` を使用している。

**修正後:**
```python
"-ac", "1",
```

---

### BUG-06: `transcriber/gemini.py:44-58` — `_adjust_timestamps` がタイムスタンプ行以外を捨てる

**現状コード (L40-58):**
```python
def _adjust_timestamps(self, text, offset_minutes):
    if offset_minutes == 0:
        return text
    lines = []
    for line in text.splitlines():
        if line.startswith("["):          # ← タイムスタンプ行のみ処理
            bracket_end = line.index("]") # ← ValueError の可能性
            ...
            lines.append(line)
            # ↑ タイムスタンプで始まらない行（空行、コメント等）は全て捨てられる
    return "\n".join(lines)
```

**問題:**
1. `line.startswith("[")` が `False` の行（空行、話者交代のコメント等）は `lines` に追加されず消える。
2. `line.index("]")` は `"]"` が見つからない場合 `ValueError` を送出する。

**修正後:**
```python
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
```

---

## Phase 1: Goal 3 — 依存関係とプロジェクト構成の整備

全てのmacOS対応の前提条件。インポートチェーンの修正、pyproject.toml の作成、フォントの分岐。

---

### 1-01: `pyproject.toml` — 新規作成

**ファイル:** `/pyproject.toml`（新規）

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "gijiroku-ai"
version = "0.1.0"
description = "会議の録音・文字起こし・議事録生成を自動で行うデスクトップアプリ"
requires-python = ">=3.10"
readme = "DESIGN.md"

dependencies = [
    "google-generativeai>=0.8.0",
    "google-api-python-client>=2.0.0",
    "google-auth-oauthlib>=1.0.0",
    "google-auth-httplib2>=0.2.0",
    "msal>=1.28.0",
    "requests>=2.31.0",
    "plyer>=2.1.0",
    "pystray>=0.19.0",
    "Pillow>=10.0.0",
    "pywin32>=306; sys_platform == 'win32'",
    "pyobjc-framework-Quartz>=10.0; sys_platform == 'darwin'",
    "pyobjc-framework-AppKit>=10.0; sys_platform == 'darwin'",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pyinstaller>=6.0.0",
]

[project.scripts]
gijiroku-ai = "main:main"
```

---

### 1-02: `requirements.txt` — プラットフォーム条件追加

**ファイル:** `/requirements.txt`

**現状 (全体):**
```
google-generativeai>=0.8.0
google-api-python-client>=2.0.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.2.0
msal>=1.28.0
requests>=2.31.0
plyer>=2.1.0
pytest>=8.0.0
pystray>=0.19.0
Pillow>=10.0.0
pywin32>=306
pyinstaller>=6.0.0
```

**修正後 (全体置換):**
```
google-generativeai>=0.8.0
google-api-python-client>=2.0.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.2.0
msal>=1.28.0
requests>=2.31.0
plyer>=2.1.0
pystray>=0.19.0
Pillow>=10.0.0
pywin32>=306; sys_platform == "win32"
pyobjc-framework-Quartz>=10.0; sys_platform == "darwin"
pyobjc-framework-AppKit>=10.0; sys_platform == "darwin"
pytest>=8.0.0
pyinstaller>=6.0.0
```

**変更点:**
- L11: `pywin32>=306` → `pywin32>=306; sys_platform == "win32"`（macOS で pip install 失敗を防止）
- L11-12 に追加: `pyobjc-framework-Quartz`, `pyobjc-framework-AppKit`（macOS 専用）
- `pytest`, `pyinstaller` を末尾に移動（開発依存であることを明示）

---

### 1-03: `tray/monitor.py` — 条件付きインポートに変更

**ファイル:** `/tray/monitor.py`

**現状 (全体 — 24行):**
```python
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

**修正後 (全体置換):**
```python
import sys

MEETING_PATTERNS = [
    "zoom meeting",
    "zoom webinar",
    "microsoft teams",
    "meet - ",
]

MEETING_BUNDLE_IDS = [
    "us.zoom.xos",
    "com.microsoft.teams",
    "com.microsoft.teams2",
]


class MeetingMonitor:
    PATTERNS = MEETING_PATTERNS

    def detect(self):
        titles = self._get_window_titles()
        for title in titles:
            lower = title.lower()
            if any(p in lower for p in self.PATTERNS):
                return True
        return False

    def _get_window_titles(self):
        if sys.platform == "win32":
            return self._get_titles_win32()
        elif sys.platform == "darwin":
            return self._get_titles_macos()
        return []

    def _get_titles_win32(self):
        import win32gui

        titles = []

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    titles.append(title)

        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        return titles

    def _get_titles_macos(self):
        try:
            import Quartz

            options = (
                Quartz.kCGWindowListOptionOnScreenOnly
                | Quartz.kCGWindowListExcludeDesktopElements
            )
            windows = Quartz.CGWindowListCopyWindowInfo(
                options, Quartz.kCGNullWindowID
            )
            titles = []
            for w in windows or []:
                owner = w.get(Quartz.kCGWindowOwnerName, "")
                name = w.get(Quartz.kCGWindowName, "")
                layer = w.get(Quartz.kCGWindowLayer, -1)
                if layer == 0:
                    if name:
                        titles.append(f"{owner}: {name}")
                    elif owner:
                        titles.append(owner)
            if not any(
                w.get(Quartz.kCGWindowName) for w in (windows or [])
            ):
                titles.extend(self._get_titles_macos_fallback())
            return titles
        except ImportError:
            return self._get_titles_macos_fallback()

    def _get_titles_macos_fallback(self):
        try:
            from AppKit import NSWorkspace

            titles = []
            for app in NSWorkspace.sharedWorkspace().runningApplications():
                bundle_id = app.bundleIdentifier() or ""
                if bundle_id in MEETING_BUNDLE_IDS:
                    name = app.localizedName() or bundle_id
                    titles.append(name)
            return titles
        except ImportError:
            return []
```

**変更理由:**
- L1: `import win32gui` → `import sys`（macOS で ImportError 解消）
- `_get_titles_win32()` 内で遅延インポート（macOS で win32gui をロードしない）
- `_get_titles_macos()` は Quartz の `CGWindowListCopyWindowInfo` を使用
- 画面収録権限未付与時のフォールバック `_get_titles_macos_fallback()` を追加
- `detect()` をプラットフォーム非依存のパターンマッチに統一

---

### 1-04: `utils/notification.py` — try/except ガード追加

**ファイル:** `/utils/notification.py`

**現状 (全体 — 10行):**
```python
from plyer import notification as plyer_notification


def notify(title, message, timeout=10):
    plyer_notification.notify(
        title=title,
        message=message,
        app_name="議事録AI",
        timeout=timeout,
    )
```

**修正後 (全体置換):**
```python
def notify(title, message, timeout=10):
    try:
        from plyer import notification as plyer_notification

        plyer_notification.notify(
            title=title,
            message=message,
            app_name="議事録AI",
            timeout=timeout,
        )
    except Exception:
        print(f"[通知] {title}: {message}")
```

**変更理由:**
- `from plyer import notification` をトップレベルから関数内に移動（遅延インポート）
- `plyer` 未インストール時も `ImportError` で落ちずにフォールバック
- 通知バックエンドのランタイムエラーも黙殺して `print()` にフォールバック

---

### 1-05: `pipeline.py:4` — notify の遅延インポート

**ファイル:** `/pipeline.py`

**変更箇所:** L4 のインポート文を削除し、`run()` 内で遅延インポート

**現状 (L1-4):**
```python
# pipeline.py
import os
from utils.file_manager import FileManager
from utils.notification import notify
```

**修正後 (L1-3):**
```python
# pipeline.py
import os
from utils.file_manager import FileManager
```

**現状 (L42):**
```python
    notify("議事録AI", "議事録が完成しました")
```

**修正後 (L42):**
```python
    from utils.notification import notify
    notify("議事録AI", "議事録が完成しました")
```

---

### 1-06: `ui/widgets.py` — フォントのプラットフォーム分岐

**ファイル:** `/ui/widgets.py`

**変更:** ファイル先頭にフォント定数を追加し、全ハードコード `"Meiryo UI"` / `"Segoe UI Emoji"` を置換。

**追加コード（L1-2 の後、L3 の前に挿入）:**
```python
import sys

_FONT_FAMILY = "Hiragino Sans" if sys.platform == "darwin" else "Meiryo UI"
_EMOJI_FONT = "Apple Color Emoji" if sys.platform == "darwin" else "Segoe UI Emoji"
```

**置換一覧:**

| 行 | 現状 | 修正後 |
|----|------|--------|
| L11 | `font=("Meiryo UI", 14, "bold")` | `font=(_FONT_FAMILY, 14, "bold")` |
| L15 | `font=("Segoe UI Emoji", 24)` | `font=(_EMOJI_FONT, 24)` |
| L21 | `font=("Meiryo UI", 9)` | `font=(_FONT_FAMILY, 9)` |
| L38 | `font=("Meiryo UI", 10)` | `font=(_FONT_FAMILY, 10)` |
| L43 | `font=("Meiryo UI", 10)` | `font=(_FONT_FAMILY, 10)` |
| L59 | `font=("Meiryo UI", 10)` | `font=(_FONT_FAMILY, 10)` |

---

### 1-07: `ui/setup.py` — フォントのプラットフォーム分岐

**ファイル:** `/ui/setup.py`

**追加コード（L1-2 の後に挿入）:**
```python
import sys

_FONT_FAMILY = "Hiragino Sans" if sys.platform == "darwin" else "Meiryo UI"
```

**置換一覧:**

| 行 | 現状 | 修正後 |
|----|------|--------|
| L24 | `font=("Meiryo UI", 16, "bold")` | `font=(_FONT_FAMILY, 16, "bold")` |
| L31 | `font=("Meiryo UI", 11, "bold")` | `font=(_FONT_FAMILY, 11, "bold")` |
| L37 | `font=("Meiryo UI", 8)` | `font=(_FONT_FAMILY, 8)` |
| L47 | `font=("Meiryo UI", 11, "bold")` | `font=(_FONT_FAMILY, 11, "bold")` |
| L78 | `font=("Meiryo UI", 9)` | `font=(_FONT_FAMILY, 9)` |
| L83 | `font=("Meiryo UI", 11, "bold")` | `font=(_FONT_FAMILY, 11, "bold")` |
| L92 | `font=("Meiryo UI", 12)` | `font=(_FONT_FAMILY, 12)` |

---

### 1-08: `ui/app.py` — フォントのプラットフォーム分岐

**ファイル:** `/ui/app.py`

**追加コード（L1 の後に挿入）:**
```python
import sys

_FONT_FAMILY = "Hiragino Sans" if sys.platform == "darwin" else "Meiryo UI"
```

**置換一覧:**

| 行 | 現状 | 修正後 |
|----|------|--------|
| L29 | `font=("Meiryo UI", 18, "bold")` | `font=(_FONT_FAMILY, 18, "bold")` |
| L66 | `font=("Meiryo UI", 12)` | `font=(_FONT_FAMILY, 12)` |

---

### 1-09: `tray/icons.py` — macOS アイコンサイズとCJKフォント

**ファイル:** `/tray/icons.py`

**現状 (全体 — 25行):**
```python
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

**修正後 (全体置換):**
```python
import sys
from PIL import Image, ImageDraw, ImageFont

ICON_SIZE = 44 if sys.platform == "darwin" else 64

COLORS = {
    "idle": "#607D8B",
    "recording": "#E53935",
    "processing": "#FDD835",
}


def _load_cjk_font(size):
    if sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ]
    else:
        candidates = [
            "C:\\Windows\\Fonts\\meiryo.ttc",
            "C:\\Windows\\Fonts\\msgothic.ttc",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def create_icon(state):
    color = COLORS.get(state, COLORS["idle"])
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = 4
    draw.ellipse(
        [margin, margin, ICON_SIZE - margin, ICON_SIZE - margin],
        fill=color,
    )
    font_size = ICON_SIZE // 4
    font = _load_cjk_font(font_size)
    bbox = draw.textbbox((0, 0), "録", font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (ICON_SIZE - tw) // 2
    y = (ICON_SIZE - th) // 2
    draw.text((x, y), "録", fill="white", font=font)
    return image
```

**変更理由:**
- `ICON_SIZE`: macOS は 44x44（メニューバー最適サイズ）、Windows は 64x64
- `_load_cjk_font()`: macOS はヒラギノ、Windows はメイリオを明示指定（デフォルトフォントだと「録」がレンダリングされない場合がある）
- テキスト描画位置を `textbbox` で正確に計算（ハードコード座標を排除）

---

### 1-10: `build.sh` — macOS ビルドスクリプト新規作成

**ファイル:** `/build.sh`（新規）

```bash
#!/bin/bash
set -e

echo "================================================"
echo "  議事録AI ビルドスクリプト (macOS)"
echo "================================================"

# FFmpegの確認
if ! command -v ffmpeg &> /dev/null; then
    echo "[ERROR] FFmpegが見つかりません。brew install ffmpeg を実行してください。"
    exit 1
fi

FFMPEG_PATH=$(which ffmpeg)
FFPROBE_PATH=$(which ffprobe)
FFMPEG_DIR=$(dirname "$FFMPEG_PATH")

echo "FFmpeg found: $FFMPEG_DIR"

# PyInstallerでビルド
pyinstaller --noconfirm \
    --name "GijirokuAI" \
    --windowed \
    --onedir \
    --icon=NONE \
    --add-data "credentials:credentials" \
    --add-binary "$FFMPEG_PATH:." \
    --add-binary "$FFPROBE_PATH:." \
    --hidden-import "pystray._darwin" \
    --hidden-import "plyer.platforms.macosx.notification" \
    --hidden-import "google.auth.transport.requests" \
    main.py

echo ""
echo "================================================"
echo "  ビルド完了！"
echo "  出力先: dist/GijirokuAI/GijirokuAI"
echo "================================================"
echo ""
echo "配布する前に credentials/ フォルダに"
echo "OAuth認証情報を配置してください。"
echo "（credentials/README.md を参照）"
```

---

### 1-11: `.gitignore` — macOS ビルド成果物追加

**ファイル:** `/.gitignore`

**末尾に追加:**
```
.DS_Store
*.app
venv/
.venv/
```

---

## Phase 2: Goal 5 — エラーハンドリングとリトライ機構

---

### 2-01: `exceptions.py` — カスタム例外階層（新規作成）

**ファイル:** `/exceptions.py`（新規）

```python
class GijirokuError(Exception):
    pass


class ConfigurationError(GijirokuError):
    pass


class RecordingError(GijirokuError):
    pass


class TranscriptionError(GijirokuError):
    pass


class GenerationError(GijirokuError):
    pass


class UploadError(GijirokuError):
    pass


class AuthenticationError(UploadError):
    pass


class NetworkError(UploadError):
    pass


class PipelineError(GijirokuError):
    pass
```

---

### 2-02: `utils/retry.py` — リトライユーティリティ（新規作成）

**ファイル:** `/utils/retry.py`（新規）

```python
import time
import logging

logger = logging.getLogger(__name__)


def retry(func, max_retries=3, initial_delay=2, backoff_factor=2,
          max_delay=60, retryable_exceptions=(Exception,)):
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            return func()
        except retryable_exceptions as e:
            if attempt == max_retries:
                logger.error("All %d retries exhausted: %s", max_retries, e)
                raise
            logger.warning(
                "Attempt %d/%d failed: %s. Retrying in %ds...",
                attempt + 1, max_retries, e, delay,
            )
            time.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)
```

---

### 2-03: `main.py` — ロギング基盤の導入 + バグ修正

**ファイル:** `/main.py`

**全体置換:**
```python
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from config import Config
from recorder.audio import AudioRecorder
from recorder.screen import ScreenRecorder
from transcriber.gemini import GeminiTranscriber
from generator.minutes import MinutesGenerator
from uploader.google_drive import GoogleDriveUploader
from uploader.onedrive import OneDriveUploader
from utils.file_manager import FileManager
from pipeline import Pipeline

logger = logging.getLogger(__name__)


def _setup_logging():
    log_dir = os.path.expanduser("~/.gijiroku-ai")
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler()],
    )


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
        from utils.resource_path import get_credentials_dir

        provider = config.get("storage_provider")
        if provider == "google_drive":
            creds_path = config.get("google_drive_credentials")
            if not creds_path:
                creds_path = os.path.join(
                    get_credentials_dir(), "google_client_secrets.json"
                )
            uploader = GoogleDriveUploader(credentials_path=creds_path)
        else:
            client_id = config.get("onedrive_credentials")
            if not client_id:
                import json

                od_config_path = os.path.join(
                    get_credentials_dir(), "onedrive_config.json"
                )
                with open(od_config_path) as f:
                    client_id = json.load(f)["client_id"]
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
    _setup_logging()
    logger.info("議事録AI starting")

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

**変更理由:**
- `_setup_logging()` 追加: RotatingFileHandler で `~/.gijiroku-ai/app.log` にログ出力
- BUG-02 修正: `main()` の if/else インデント修正
- `logger.info("議事録AI starting")` でアプリ起動をログ記録

---

### 2-04: `config.py` — JSON 破損復旧、アトミック書き込み、スレッドロック

**ファイル:** `/config.py`

**全体置換:**
```python
import json
import logging
import os
import shutil
import tempfile
import threading

logger = logging.getLogger(__name__)

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
        self._lock = threading.Lock()
        self._data = dict(DEFAULTS)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._data.update(json.load(f))
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Config file corrupted, backing up: %s", e)
                backup = path + ".bak"
                shutil.copy2(path, backup)
                self._save()
        else:
            self._save()

    def get(self, key):
        with self._lock:
            return self._data.get(key)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value
            self._save()

    def _save(self):
        dir_name = os.path.dirname(self._path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._path)
        except BaseException:
            os.unlink(tmp_path)
            raise
```

**変更点:**
- `threading.Lock` 追加 → `get()`, `set()` をスレッドセーフに
- `json.load()` に `try/except JSONDecodeError` → 破損時はバックアップ作成してデフォルト復元
- `_save()` をアトミック書き込みに変更（`tempfile.mkstemp` + `os.replace`）
- `logging` モジュール追加

---

### 2-05: `pipeline.py` — エラーハンドリング、バリデーション、チェックポイント

**ファイル:** `/pipeline.py`

**全体置換:**
```python
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
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

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
```

---

### 2-06: `transcriber/gemini.py` — リトライ、バリデーション、ファイルクリーンアップ

**ファイル:** `/transcriber/gemini.py`

**全体置換:**
```python
import logging

import google.generativeai as genai

from utils.retry import retry

logger = logging.getLogger(__name__)


class GeminiTranscriber:
    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key):
        if not api_key:
            raise ValueError("Gemini APIキーが空です")
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
        audio_file = None
        try:
            audio_file = retry(
                lambda: genai.upload_file(audio_path),
                max_retries=3,
                retryable_exceptions=(Exception,),
            )
            response = retry(
                lambda: model.generate_content([
                    self._build_transcription_prompt(),
                    audio_file,
                ]),
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
                    genai.delete_file(audio_file.name)
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
```

---

### 2-07: `generator/minutes.py` — リトライ、バリデーション、バグ修正

**ファイル:** `/generator/minutes.py`

**全体置換:**
```python
import logging

import google.generativeai as genai

from utils.retry import retry

logger = logging.getLogger(__name__)


class MinutesGenerator:
    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key):
        if not api_key:
            raise ValueError("Gemini APIキーが空です")
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
        if not transcript or not transcript.strip():
            raise ValueError("文字起こしテキストが空です")

        model = genai.GenerativeModel(self.MODEL)
        prompt = self._build_generation_prompt(transcript)

        response = retry(
            lambda: model.generate_content(prompt),
            max_retries=3,
            retryable_exceptions=(Exception,),
        )

        if not response.candidates:
            logger.warning("Safety filter triggered during minutes generation")
            return "# 議事録生成失敗\n\nセーフティフィルターにより生成がブロックされました。"

        return response.text
```

---

### 2-08: `recorder/audio.py` — FFmpeg 検出、stderr キャプチャ、タイムアウト付き stop

**ファイル:** `/recorder/audio.py`

**Phase 2 での変更分（macOS対応は Phase 4 で実施）:**

**全体置換:**
```python
import logging
import os
import re
import shutil
import subprocess
import sys

from exceptions import RecordingError

logger = logging.getLogger(__name__)


class AudioRecorder:
    def __init__(self, output_dir, mic_device, segment_duration=1800):
        self._output_dir = output_dir
        self._mic_device = mic_device
        self._segment_duration = segment_duration
        self._process = None

    @property
    def is_recording(self):
        if self._process is None:
            return False
        if self._process.poll() is not None:
            self._process = None
            return False
        return True

    def _build_command(self):
        output_pattern = os.path.join(self._output_dir, "recording_%03d.wav")
        if sys.platform == "darwin":
            return [
                "ffmpeg", "-y",
                "-f", "avfoundation",
                "-i", f"none:{self._mic_device}",
                "-ac", "1",
                "-ar", "16000",
                "-f", "segment",
                "-segment_time", str(self._segment_duration),
                "-reset_timestamps", "1",
                output_pattern,
            ]
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
        if not shutil.which("ffmpeg"):
            raise RecordingError(
                "FFmpegが見つかりません。インストールしてください。"
            )
        cmd = self._build_command()
        logger.info("Starting audio recording: %s", " ".join(cmd))
        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise RecordingError(f"FFmpeg起動失敗: {e}") from e

    def stop(self):
        if self._process is None:
            return
        import signal

        try:
            if sys.platform == "darwin":
                self._process.send_signal(signal.SIGINT)
                self._process.wait(timeout=10)
            else:
                self._process.communicate(input=b"q", timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg did not stop gracefully, terminating")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("FFmpeg did not terminate, killing")
                self._process.kill()
                self._process.wait()
        except Exception as e:
            logger.error("Error stopping recorder: %s", e)
            self._process.kill()
            self._process.wait()
        finally:
            if self._process and self._process.returncode is not None:
                logger.info("FFmpeg exited with code %d", self._process.returncode)
            self._process = None

    @staticmethod
    def list_devices():
        if not shutil.which("ffmpeg"):
            return []
        try:
            if sys.platform == "darwin":
                result = subprocess.run(
                    ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                    capture_output=True,
                    text=True,
                )
                devices = []
                in_audio_section = False
                for line in result.stderr.splitlines():
                    if "audio devices" in line.lower():
                        in_audio_section = True
                        continue
                    if "video devices" in line.lower():
                        in_audio_section = False
                        continue
                    if in_audio_section:
                        match = re.search(r"\[(\d+)\]\s+(.+)$", line)
                        if match:
                            devices.append((match.group(1), match.group(2).strip()))
                return devices
            else:
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
        except Exception as e:
            logger.error("Failed to list audio devices: %s", e)
            return []
```

---

### 2-09: `recorder/screen.py` — プロセス保護、タイムアウト、macOS 対応

**ファイル:** `/recorder/screen.py`

**全体置換:**
```python
import logging
import os
import shutil
import subprocess
import sys

from exceptions import RecordingError

logger = logging.getLogger(__name__)


class ScreenRecorder:
    def __init__(self, output_dir, mic_device, segment_duration=1800):
        self._output_dir = output_dir
        self._mic_device = mic_device
        self._segment_duration = segment_duration
        self._video_process = None
        self._audio_process = None

    @property
    def is_recording(self):
        if self._video_process is None:
            return False
        if self._video_process.poll() is not None:
            self._video_process = None
            return False
        return True

    def _build_video_command(self):
        video_path = os.path.join(self._output_dir, "recording.mp4")
        if sys.platform == "darwin":
            return [
                "ffmpeg", "-y",
                "-f", "avfoundation",
                "-framerate", "10",
                "-i", f"1:{self._mic_device}",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-c:a", "aac",
                video_path,
            ]
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
        if sys.platform == "darwin":
            return [
                "ffmpeg", "-y",
                "-f", "avfoundation",
                "-i", f"none:{self._mic_device}",
                "-ac", "1",
                "-ar", "16000",
                "-f", "segment",
                "-segment_time", str(self._segment_duration),
                "-reset_timestamps", "1",
                audio_pattern,
            ]
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
        if not shutil.which("ffmpeg"):
            raise RecordingError(
                "FFmpegが見つかりません。インストールしてください。"
            )
        logger.info("Starting screen recording")
        try:
            self._video_process = subprocess.Popen(
                self._build_video_command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise RecordingError(f"FFmpeg起動失敗: {e}") from e

        try:
            self._audio_process = subprocess.Popen(
                self._build_audio_command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            logger.error("Audio process failed to start, killing video process")
            self._video_process.kill()
            self._video_process.wait()
            self._video_process = None
            raise RecordingError(f"音声プロセス起動失敗: {e}") from e

    def stop(self):
        if self._video_process is None:
            return
        import signal

        for name, proc in [("video", self._video_process), ("audio", self._audio_process)]:
            if proc is None:
                continue
            try:
                if sys.platform == "darwin":
                    proc.send_signal(signal.SIGINT)
                    proc.wait(timeout=10)
                else:
                    proc.communicate(input=b"q", timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("%s process did not stop, terminating", name)
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            except Exception as e:
                logger.error("Error stopping %s: %s", name, e)
                proc.kill()
                proc.wait()

        self._video_process = None
        self._audio_process = None
```

---

### 2-10: `uploader/google_drive.py` — トークン破損回復、リトライ、per-file エラー処理

**ファイル:** `/uploader/google_drive.py`

**全体置換:**
```python
import logging
import os
import tempfile

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from exceptions import AuthenticationError, UploadError
from uploader.base import BaseUploader
from utils.retry import retry

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveUploader(BaseUploader):
    def __init__(self, credentials_path, token_path=None):
        self._credentials_path = credentials_path
        if token_path is None:
            from utils.resource_path import get_app_data_dir

            token_path = os.path.join(get_app_data_dir(), "gdrive_token.json")
        self._token_path = token_path
        self._service = None
        self._root_folder_id = None

    def authenticate(self):
        creds = None
        if os.path.exists(self._token_path):
            try:
                creds = Credentials.from_authorized_user_file(
                    self._token_path, SCOPES
                )
            except (ValueError, Exception) as e:
                logger.warning("Token file corrupted, will re-authenticate: %s", e)
                os.remove(self._token_path)
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning("Token refresh failed, re-authenticating: %s", e)
                    if os.path.exists(self._token_path):
                        os.remove(self._token_path)
                    creds = None

            if not creds or not creds.valid:
                if not os.path.exists(self._credentials_path):
                    raise AuthenticationError(
                        f"認証情報ファイルが見つかりません: {self._credentials_path}"
                    )
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self._credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    raise AuthenticationError(f"Google Drive 認証失敗: {e}") from e

            dir_name = os.path.dirname(self._token_path)
            fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(creds.to_json())
                os.replace(tmp, self._token_path)
            except BaseException:
                os.unlink(tmp)
                raise

        self._service = build("drive", "v3", credentials=creds)
        self._ensure_root_folder()

    def _ensure_root_folder(self):
        results = retry(
            lambda: self._service.files()
            .list(
                q="name='議事録AI' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces="drive",
                fields="files(id)",
            )
            .execute(),
            max_retries=3,
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

        folder = retry(
            lambda: self._service.files()
            .create(body=metadata, fields="id")
            .execute(),
            max_retries=3,
        )
        return folder["id"]

    def upload_file(self, file_path, parent_folder_id):
        if not self._service:
            raise UploadError("authenticate() を先に呼び出してください")

        metadata = {
            "name": os.path.basename(file_path),
            "parents": [parent_folder_id],
        }
        media = MediaFileUpload(file_path, resumable=True)

        request = self._service.files().create(
            body=metadata, media_body=media, fields="id"
        )
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(
                    "Upload %s: %d%%",
                    os.path.basename(file_path),
                    int(status.progress() * 100),
                )

        logger.info("Uploaded: %s → %s", file_path, response["id"])
        return response["id"]

    def upload_session(self, session_dir, meeting_name):
        if not self._service:
            raise UploadError("authenticate() を先に呼び出してください")

        parent = self._root_folder_id
        folder_id = self.create_folder(meeting_name, parent)
        failed = []
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            if os.path.isfile(filepath):
                try:
                    self.upload_file(filepath, folder_id)
                except Exception as e:
                    logger.error("Failed to upload %s: %s", filename, e)
                    failed.append(filename)
        if failed:
            raise UploadError(
                f"以下のファイルのアップロードに失敗: {', '.join(failed)}"
            )
        return folder_id
```

---

### 2-11: `uploader/onedrive.py` — ファイルハンドル修正、タイムアウト、認証ガード

**ファイル:** `/uploader/onedrive.py`

**Phase 2 での変更分（大容量アップロードは Phase 7 で実施）:**

**全体置換:**
```python
import json
import logging
import os
import tempfile
from urllib.parse import quote

import msal
import requests

from exceptions import AuthenticationError, NetworkError, UploadError
from uploader.base import BaseUploader
from utils.retry import retry

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.microsoft.com/v1.0"
SCOPES = ["Files.ReadWrite"]
SIMPLE_UPLOAD_LIMIT = 4 * 1024 * 1024
CHUNK_SIZE = 3276800


class OneDriveUploader(BaseUploader):
    def __init__(self, client_id, authority=None, token_cache_path=None):
        self._client_id = client_id
        self._authority = authority or "https://login.microsoftonline.com/consumers"
        if token_cache_path is None:
            from utils.resource_path import get_app_data_dir

            token_cache_path = os.path.join(
                get_app_data_dir(), "onedrive_token_cache.json"
            )
        self._token_cache_path = token_cache_path
        self._access_token = None

    def authenticate(self):
        cache = msal.SerializableTokenCache()
        if self._token_cache_path and os.path.exists(self._token_cache_path):
            try:
                with open(self._token_cache_path, "r") as f:
                    cache.deserialize(f.read())
            except Exception as e:
                logger.warning("Token cache corrupted: %s", e)

        app = msal.PublicClientApplication(
            self._client_id,
            authority=self._authority,
            token_cache=cache,
        )

        accounts = app.get_accounts()
        result = None
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])

        if not result:
            flow = app.initiate_device_flow(scopes=SCOPES)
            if "user_code" not in flow:
                raise AuthenticationError(
                    f"デバイスフロー開始エラー: {flow.get('error_description', '不明')}"
                )
            print(flow["message"])
            result = app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            raise AuthenticationError(
                f"認証失敗: {result.get('error_description', '不明')}"
            )

        self._access_token = result["access_token"]

        if self._token_cache_path and cache.has_state_changed:
            dir_name = os.path.dirname(self._token_cache_path)
            os.makedirs(dir_name, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(cache.serialize())
                os.replace(tmp, self._token_cache_path)
            except BaseException:
                os.unlink(tmp)
                raise

    def _headers(self):
        return {"Authorization": f"Bearer {self._access_token}"}

    def create_folder(self, name, parent_path=None):
        if parent_path:
            url = f"{GRAPH_URL}/me/drive/root:{quote(parent_path, safe='/')}:/children"
        else:
            url = f"{GRAPH_URL}/me/drive/root/children"
        body = {
            "name": name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename",
        }
        resp = requests.post(
            url, headers=self._headers(), json=body, timeout=(10, 30)
        )
        resp.raise_for_status()
        return resp.json()["id"]

    def upload_file(self, file_path, parent_path):
        file_size = os.path.getsize(file_path)
        if file_size <= SIMPLE_UPLOAD_LIMIT:
            return self._upload_simple(file_path, parent_path)
        return self._upload_session(file_path, parent_path)

    def _upload_simple(self, file_path, parent_path):
        filename = os.path.basename(file_path)
        url = (
            f"{GRAPH_URL}/me/drive/root:"
            f"{quote(parent_path, safe='/')}/{quote(filename)}:/content"
        )
        with open(file_path, "rb") as f:
            resp = requests.put(
                url, headers=self._headers(), data=f, timeout=(10, 300)
            )
        resp.raise_for_status()
        return resp.json()["id"]

    def _upload_session(self, file_path, parent_path):
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        create_url = (
            f"{GRAPH_URL}/me/drive/root:"
            f"{quote(parent_path, safe='/')}/{quote(filename)}:/createUploadSession"
        )
        body = {
            "item": {
                "@microsoft.graph.conflictBehavior": "rename",
                "name": filename,
            }
        }
        resp = requests.post(
            create_url, headers=self._headers(), json=body, timeout=(10, 30)
        )
        resp.raise_for_status()
        upload_url = resp.json()["uploadUrl"]

        with open(file_path, "rb") as f:
            offset = 0
            while offset < file_size:
                chunk_end = min(offset + CHUNK_SIZE, file_size) - 1
                chunk_data = f.read(CHUNK_SIZE)
                headers = {
                    "Content-Range": f"bytes {offset}-{chunk_end}/{file_size}",
                    "Content-Length": str(len(chunk_data)),
                }

                chunk_resp = retry(
                    lambda: requests.put(
                        upload_url,
                        headers=headers,
                        data=chunk_data,
                        timeout=(10, 300),
                    ),
                    max_retries=5,
                    initial_delay=2,
                    retryable_exceptions=(
                        requests.exceptions.ConnectionError,
                        requests.exceptions.Timeout,
                    ),
                )

                if chunk_resp.status_code not in (200, 201, 202):
                    raise UploadError(
                        f"チャンクアップロード失敗: {chunk_resp.status_code} {chunk_resp.text}"
                    )

                progress = int((chunk_end + 1) / file_size * 100)
                logger.info("Upload %s: %d%%", filename, progress)
                offset += CHUNK_SIZE

        return chunk_resp.json().get("id", "")

    def upload_session(self, session_dir, meeting_name):
        root_path = "/議事録AI"
        self.create_folder("議事録AI")
        folder_path = f"/議事録AI/{meeting_name}"
        self.create_folder(meeting_name, root_path)
        failed = []
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            if os.path.isfile(filepath):
                try:
                    self.upload_file(filepath, folder_path)
                except Exception as e:
                    logger.error("Failed to upload %s: %s", filename, e)
                    failed.append(filename)
        if failed:
            raise UploadError(
                f"以下のファイルのアップロードに失敗: {', '.join(failed)}"
            )
```

---

### 2-12: `tray/app.py` — エラー通知、ログ出力（`except Exception: pass` 解消）

**ファイル:** `/tray/app.py`

**この変更は Phase 3 と統合して実施する（スレッド安全性と同時に書き換え）。**

Phase 2 での要件:
- L81-82 の `except Exception: pass` → `logging.exception()` + `notify()` に変更
- 全状態遷移にログ出力追加

---

## Phase 3: Goal 6 — スレッド安全性の確保

---

### 3-01: `tray/app.py` — 全面書き換え（Lock + Event + エラー処理統合）

**ファイル:** `/tray/app.py`

**全体置換:**
```python
import logging
import threading
import time
from enum import Enum

import pystray

from tray.icons import create_icon
from tray.monitor import MeetingMonitor

logger = logging.getLogger(__name__)

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
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._state = State.IDLE
        self._recorder = None
        self._session_dir = None
        self._grace_deadline = 0
        self._tray_icon = None
        self._monitor_thread = None

    @property
    def state(self):
        with self._lock:
            return self._state

    def tick(self):
        with self._lock:
            if self._state == State.IDLE:
                if self._monitor.detect():
                    self._start_recording_locked("online")

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
                    self._stop_recording_locked()
                    return "run_pipeline"

            elif self._state == State.PROCESSING:
                pass

        return None

    def start_face_to_face(self):
        with self._lock:
            if self._state != State.IDLE:
                return
            self._start_recording_locked("face_to_face")

    def manual_stop(self):
        session_dir = None
        with self._lock:
            if self._state not in (State.RECORDING, State.GRACE_PERIOD):
                return
            self._stop_recording_locked()
            session_dir = self._session_dir

        if session_dir:
            self._run_pipeline()

    def _start_recording_locked(self, mode):
        self._recorder, self._session_dir = self._recorder_factory(mode)
        self._recorder.start()
        self._state = State.RECORDING
        logger.info("Recording started: mode=%s, dir=%s", mode, self._session_dir)
        self._update_icon()

    def _stop_recording_locked(self):
        if self._recorder:
            self._recorder.stop()
            self._recorder = None
        self._state = State.PROCESSING
        logger.info("Recording stopped, processing")
        self._update_icon()

    def _run_pipeline(self):
        with self._lock:
            session_dir = self._session_dir
            self._state = State.PROCESSING
            self._update_icon()

        try:
            self._pipeline.run(session_dir)
            logger.info("Pipeline completed for %s", session_dir)
        except Exception:
            logger.exception("Pipeline failed for %s", session_dir)
            try:
                from utils.notification import notify

                notify("議事録AI", "処理中にエラーが発生しました")
            except Exception:
                pass

        with self._lock:
            self._session_dir = None
            self._state = State.IDLE
            self._update_icon()

    def _update_icon(self):
        if self._tray_icon:
            self._tray_icon.icon = create_icon(self._state.value)

    def run(self):
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._monitor_thread.start()

        menu = pystray.Menu(
            pystray.MenuItem(
                "対面モードで録音開始", lambda: self.start_face_to_face()
            ),
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
        while not self._stop_event.is_set():
            try:
                action = self.tick()
                if action == "run_pipeline":
                    self._run_pipeline()
            except Exception:
                logger.exception("Error in monitor loop")
            self._stop_event.wait(POLL_INTERVAL_SECONDS)

    def _open_settings(self):
        from ui.setup import SetupWizard

        SetupWizard(self._config, on_complete=lambda: None).run()

    def quit(self):
        self._stop_event.set()
        with self._lock:
            if self._recorder:
                self._recorder.stop()
                self._recorder = None
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
        if self._tray_icon:
            self._tray_icon.stop()
```

**変更理由:**
- `threading.Lock` で全共有状態（`_state`, `_recorder`, `_session_dir`, `_grace_deadline`）を保護
- `threading.Event` (`_stop_event`) で即座のシャットダウンが可能に（`time.sleep` の代替）
- `quit()` が `_monitor_thread.join()` でスレッド終了を待機
- `_run_pipeline()` はロック外で実行（デッドロック防止）
- `except Exception: pass` → `logger.exception()` + `notify()` に変更
- BUG-03, BUG-04 も修正済み

---

### 3-02: `ui/app.py` — WM_DELETE_WINDOW、winfo_exists、ボタン無効化

**ファイル:** `/ui/app.py`

**全体置換:**
```python
import logging
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from ui.widgets import ModeButton, StatusBar, StorageSelector

logger = logging.getLogger(__name__)

_FONT_FAMILY = "Hiragino Sans" if sys.platform == "darwin" else "Meiryo UI"


class App:
    def __init__(self, config, recorder_factory, pipeline):
        self._config = config
        self._recorder_factory = recorder_factory
        self._pipeline = pipeline
        self._recorder = None
        self._session_dir = None
        self._root = None

    def run(self):
        self._root = tk.Tk()
        self._root.title("議事録AI")
        self._root.geometry("450x350")
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._root.mainloop()

    def _build_ui(self):
        title_frame = tk.Frame(self._root)
        title_frame.pack(fill="x", pady=(10, 0))
        tk.Label(
            title_frame, text="議事録AI", font=(_FONT_FAMILY, 18, "bold")
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
            font=(_FONT_FAMILY, 12),
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

        try:
            self._recorder, self._session_dir = self._recorder_factory(mode)
            self._recorder.start()
        except Exception as e:
            messagebox.showerror("録音エラー", f"録音を開始できませんでした:\n{e}")
            return

        self._status_bar.set_recording(True)
        self._status_bar.set_status(
            f"録音中（{'対面' if mode == 'face_to_face' else 'オンライン'}）"
        )
        self._stop_btn.configure(state="normal")
        self._face_btn.configure(state="disabled")
        self._online_btn.configure(state="disabled")

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
            def on_status(msg):
                if self._root and self._root.winfo_exists():
                    self._root.after(0, lambda: self._status_bar.set_status(msg))

            self._pipeline.run(self._session_dir, on_status=on_status)
            if self._root and self._root.winfo_exists():
                self._root.after(0, self._reset_ui)

        except Exception as e:
            logger.exception("Pipeline failed")
            if self._root and self._root.winfo_exists():
                self._root.after(
                    0,
                    lambda: messagebox.showerror(
                        "エラー", f"処理中にエラーが発生しました:\n{e}"
                    ),
                )
                self._root.after(0, self._reset_ui)

    def _reset_ui(self):
        self._status_bar.set_status("待機中")
        self._stop_btn.configure(state="disabled")
        self._face_btn.configure(state="normal")
        self._online_btn.configure(state="normal")
        self._recorder = None
        self._session_dir = None

    def _on_close(self):
        if self._recorder and self._recorder.is_recording:
            self._recorder.stop()
        self._root.destroy()
```

---

## Phase 4: Goal 1 — macOS対応 レコーダー

Phase 2 の `recorder/audio.py` と `recorder/screen.py` の書き換えに既にプラットフォーム分岐を含めている。

追加で必要な作業:

### 4-01: `ui/setup.py` — デバイスリストのタプル対応

**変更箇所:** `_refresh_mics()` メソッド

**現状 (L213-220):**
```python
def _refresh_mics(self):
    try:
        devices = AudioRecorder.list_devices()
        self._mic_combo["values"] = devices
        if devices:
            self._mic_combo.current(0)
    except Exception:
        self._mic_combo["values"] = ["(デバイスを検出できません)"]
```

**修正後:**
```python
def _refresh_mics(self):
    try:
        raw_devices = AudioRecorder.list_devices()
        if sys.platform == "darwin":
            self._device_map = {name: idx for idx, name in raw_devices}
            display_names = [name for _, name in raw_devices]
        else:
            self._device_map = {d: d for d in raw_devices}
            display_names = raw_devices

        self._mic_combo["values"] = display_names
        if display_names:
            self._mic_combo.current(0)
    except Exception:
        self._device_map = {}
        self._mic_combo["values"] = ["(デバイスを検出できません)"]
```

**`_save()` メソッド内も修正:**

`mic` 保存時にデバイスインデックスを使用:

```python
mic_display = self._mic_var.get()
if not mic_display or mic_display.startswith("("):
    messagebox.showwarning("入力エラー", "マイクデバイスを選択してください。")
    return

mic_value = self._device_map.get(mic_display, mic_display)
self._config.set("mic_device", mic_value)
```

---

## Phase 5: Goal 2 — macOS対応 ウィンドウ検出

Phase 1 の `tray/monitor.py` 書き換えに全て含まれている。追加作業なし。

---

## Phase 6: Goal 4 — FFmpegセットアップ統合

### 6-01: `ui/setup.py` — FFmpeg 検出ステップの追加

**変更箇所:** `run()` メソッド内、Step 1 の前に FFmpeg チェックを追加。

**追加コード（Step 1 の Label の前）:**
```python
# Step 0: FFmpeg check
ffmpeg_frame = tk.Frame(frame)
ffmpeg_frame.pack(anchor="w", fill="x", pady=(5, 10))

import shutil
if shutil.which("ffmpeg"):
    tk.Label(
        ffmpeg_frame,
        text="FFmpeg: インストール済み",
        font=(_FONT_FAMILY, 9),
        fg="green",
    ).pack(anchor="w")
else:
    tk.Label(
        ffmpeg_frame,
        text="FFmpeg: 未インストール（必須）",
        font=(_FONT_FAMILY, 9),
        fg="red",
    ).pack(anchor="w")
    if sys.platform == "darwin":
        install_msg = "ターミナルで以下を実行:\n  brew install ffmpeg"
    else:
        install_msg = "FFmpegをダウンロードしてPATHに追加してください"
    tk.Label(
        ffmpeg_frame,
        text=install_msg,
        font=(_FONT_FAMILY, 8),
        fg="gray",
        justify="left",
    ).pack(anchor="w")
```

**`_save()` メソッドに FFmpeg チェックを追加:**
```python
if not shutil.which("ffmpeg"):
    messagebox.showwarning(
        "FFmpeg未検出",
        "FFmpegがインストールされていません。\n"
        + ("brew install ffmpeg を実行してください。" if sys.platform == "darwin"
           else "FFmpegをダウンロードしてPATHに追加してください。"),
    )
    return
```

### 6-02: BlackHole 検出（macOS 専用）

**`_refresh_mics()` の末尾に追加（macOS のみ）:**
```python
if sys.platform == "darwin" and display_names:
    has_blackhole = any("blackhole" in n.lower() for n in display_names)
    if not has_blackhole:
        tk.Label(
            frame,
            text="ヒント: オンラインモードにはBlackHoleが必要です\n"
                 "  brew install blackhole-2ch",
            font=(_FONT_FAMILY, 8),
            fg="orange",
            justify="left",
        ).pack(anchor="w", pady=(2, 0))
```

---

## Phase 7: Goal 7 — OneDrive大容量ファイルアップロード

Phase 2 の `uploader/onedrive.py` 書き換えに全て含まれている:
- `_upload_session()` メソッド: チャンクアップロード実装
- `_upload_simple()` メソッド: 4MB以下のシンプルアップロード
- `upload_file()`: ファイルサイズで自動分岐
- URL エンコーディング: `urllib.parse.quote` 使用
- ファイルハンドルリーク修正: `with open()` 使用
- `user_code` / `access_token` のバリデーション追加
- `timeout` パラメータ追加

追加作業なし。

---

## Phase 8: Goal 8 — テスト基盤の修正とカバレッジ向上

---

### 8-01: `tests/conftest.py` — 新規作成

```python
import sys
import pytest

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

windows_only = pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
macos_only = pytest.mark.skipif(not IS_MACOS, reason="macOS-only test")


@pytest.fixture
def platform_audio_format():
    return "dshow" if IS_WINDOWS else "avfoundation"


@pytest.fixture
def platform_screen_format():
    return "gdigrab" if IS_WINDOWS else "avfoundation"
```

---

### 8-02: `tests/test_audio_recorder.py` — プラットフォームスキップ + macOS テスト + エラーパス

**全体置換:**
```python
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from recorder.audio import AudioRecorder


@pytest.fixture
def recorder(tmp_path):
    device = "0" if sys.platform == "darwin" else "Test Microphone"
    return AudioRecorder(
        output_dir=str(tmp_path),
        mic_device=device,
        segment_duration=1800,
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
def test_build_command_windows(recorder):
    cmd = recorder._build_command()
    assert "dshow" in cmd
    assert "1800" in cmd


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only")
def test_build_command_macos(recorder):
    cmd = recorder._build_command()
    assert "avfoundation" in cmd
    assert "none:0" in " ".join(cmd)


def test_is_recording_initially_false(recorder):
    assert recorder.is_recording is False


@patch("recorder.audio.subprocess.Popen")
def test_start_sets_recording_flag(mock_popen, recorder):
    mock_popen.return_value = MagicMock(poll=MagicMock(return_value=None))
    with patch("recorder.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
        recorder.start()
    assert recorder.is_recording is True


@patch("recorder.audio.subprocess.Popen")
def test_stop_clears_recording_flag(mock_popen, recorder):
    mock_proc = MagicMock(poll=MagicMock(return_value=None), returncode=0)
    mock_popen.return_value = mock_proc
    with patch("recorder.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
        recorder.start()
        recorder.stop()
    assert recorder.is_recording is False


def test_start_raises_when_ffmpeg_missing(recorder):
    with patch("recorder.audio.shutil.which", return_value=None):
        from exceptions import RecordingError
        with pytest.raises(RecordingError, match="FFmpeg"):
            recorder.start()


@patch("recorder.audio.subprocess.Popen")
def test_stop_kills_on_timeout(mock_popen, recorder):
    import subprocess
    mock_proc = MagicMock(
        poll=MagicMock(return_value=None),
        returncode=None,
    )
    if sys.platform == "darwin":
        mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=10)
    else:
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=10)
    mock_proc.terminate = MagicMock()
    mock_proc.kill = MagicMock()
    # After kill, wait should succeed
    def wait_after_kill(timeout=None):
        mock_proc.returncode = -9
    mock_proc.kill.side_effect = lambda: None
    mock_popen.return_value = mock_proc

    with patch("recorder.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
        recorder.start()
        recorder.stop()
    assert mock_proc.terminate.called or mock_proc.kill.called


def test_list_devices_returns_list():
    with patch("recorder.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
        with patch("recorder.audio.subprocess.run") as mock_run:
            if sys.platform == "darwin":
                mock_run.return_value = MagicMock(
                    stderr=(
                        "[AVFoundation indev] AVFoundation audio devices:\n"
                        "[AVFoundation indev] [0] MacBook Pro Microphone\n"
                        "[AVFoundation indev] [1] BlackHole 2ch\n"
                    )
                )
                devices = AudioRecorder.list_devices()
                assert len(devices) >= 1
                assert isinstance(devices[0], tuple)
            else:
                mock_run.return_value = MagicMock(
                    stderr='[dshow] "Microphone (Realtek)" (audio)\n'
                )
                devices = AudioRecorder.list_devices()
                assert isinstance(devices, list)
```

---

### 8-03: `tests/test_screen_recorder.py` — プラットフォームスキップ + エラーパス

**全体置換:**
```python
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from recorder.screen import ScreenRecorder


@pytest.fixture
def recorder(tmp_path):
    device = "0" if sys.platform == "darwin" else "Test Microphone"
    return ScreenRecorder(
        output_dir=str(tmp_path),
        mic_device=device,
        segment_duration=1800,
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
def test_build_video_command_windows(recorder):
    cmd = recorder._build_video_command()
    cmd_str = " ".join(cmd)
    assert "gdigrab" in cmd_str
    assert "desktop" in cmd_str


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only")
def test_build_video_command_macos(recorder):
    cmd = recorder._build_video_command()
    cmd_str = " ".join(cmd)
    assert "avfoundation" in cmd_str


def test_is_recording_initially_false(recorder):
    assert recorder.is_recording is False


@patch("recorder.screen.subprocess.Popen")
def test_start_sets_recording_flag(mock_popen, recorder):
    mock_popen.return_value = MagicMock(poll=MagicMock(return_value=None))
    with patch("recorder.screen.shutil.which", return_value="/usr/bin/ffmpeg"):
        recorder.start()
    assert recorder.is_recording is True


@patch("recorder.screen.subprocess.Popen")
def test_start_launches_two_processes(mock_popen, recorder):
    mock_popen.return_value = MagicMock(poll=MagicMock(return_value=None))
    with patch("recorder.screen.shutil.which", return_value="/usr/bin/ffmpeg"):
        recorder.start()
    assert mock_popen.call_count == 2


def test_start_raises_when_ffmpeg_missing(recorder):
    with patch("recorder.screen.shutil.which", return_value=None):
        from exceptions import RecordingError
        with pytest.raises(RecordingError, match="FFmpeg"):
            recorder.start()


@patch("recorder.screen.subprocess.Popen")
def test_audio_failure_kills_video(mock_popen, recorder):
    video_proc = MagicMock(poll=MagicMock(return_value=None), returncode=0)
    mock_popen.side_effect = [video_proc, FileNotFoundError("audio")]
    with patch("recorder.screen.shutil.which", return_value="/usr/bin/ffmpeg"):
        from exceptions import RecordingError
        with pytest.raises(RecordingError):
            recorder.start()
    video_proc.kill.assert_called_once()
```

---

### 8-04: `tests/test_monitor.py` — プラットフォームスキップ + macOS テスト

**全体置換:**
```python
import sys
import pytest
from unittest.mock import patch, MagicMock
from tray.monitor import MeetingMonitor


@pytest.fixture
def monitor():
    return MeetingMonitor()


@pytest.mark.skipif(sys.platform != "win32", reason="win32gui required")
def test_no_meeting_windows_win32(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        mock_gui.EnumWindows.side_effect = lambda cb, _: None
        assert monitor.detect() is False


@pytest.mark.skipif(sys.platform != "win32", reason="win32gui required")
def test_detect_zoom_win32(monitor):
    with patch("tray.monitor.win32gui") as mock_gui:
        def enum_windows(callback, _):
            callback(1, None)
        mock_gui.EnumWindows.side_effect = enum_windows
        mock_gui.GetWindowText.return_value = "Zoom Meeting"
        mock_gui.IsWindowVisible.return_value = True
        assert monitor.detect() is True


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only")
def test_detect_zoom_macos(monitor):
    mock_windows = [
        {
            "kCGWindowOwnerName": "zoom.us",
            "kCGWindowName": "Zoom Meeting",
            "kCGWindowLayer": 0,
        }
    ]
    with patch("tray.monitor.Quartz") as mock_quartz:
        mock_quartz.kCGWindowListOptionOnScreenOnly = 1
        mock_quartz.kCGWindowListExcludeDesktopElements = 16
        mock_quartz.kCGNullWindowID = 0
        mock_quartz.kCGWindowOwnerName = "kCGWindowOwnerName"
        mock_quartz.kCGWindowName = "kCGWindowName"
        mock_quartz.kCGWindowLayer = "kCGWindowLayer"
        mock_quartz.CGWindowListCopyWindowInfo.return_value = mock_windows
        assert monitor.detect() is True


def test_detect_with_mocked_titles(monitor):
    with patch.object(monitor, "_get_window_titles", return_value=["Zoom Meeting"]):
        assert monitor.detect() is True


def test_no_detect_with_normal_windows(monitor):
    with patch.object(monitor, "_get_window_titles", return_value=["Notepad", "Terminal"]):
        assert monitor.detect() is False


def test_detect_teams(monitor):
    with patch.object(monitor, "_get_window_titles", return_value=["Microsoft Teams"]):
        assert monitor.detect() is True


def test_detect_google_meet(monitor):
    with patch.object(
        monitor, "_get_window_titles",
        return_value=["Google Chrome: Meet - abc-defg-hij"],
    ):
        assert monitor.detect() is True
```

---

### 8-05: `tests/test_pipeline.py` — エラーパステスト追加

**既存テストを維持しつつ追加:**

```python
# 既存テストの末尾に追加

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
```

---

### 8-06: `tests/test_notification.py` — 新規作成

```python
from unittest.mock import patch, MagicMock


def test_notify_calls_plyer():
    with patch("plyer.notification.notify") as mock_notify:
        from utils.notification import notify
        notify("タイトル", "メッセージ")
        mock_notify.assert_called_once()


def test_notify_handles_import_error(capsys):
    with patch.dict("sys.modules", {"plyer": None, "plyer.notification": None}):
        import importlib
        import utils.notification
        importlib.reload(utils.notification)
        utils.notification.notify("タイトル", "メッセージ")
        captured = capsys.readouterr()
        assert "タイトル" in captured.out


def test_notify_handles_runtime_error(capsys):
    with patch("plyer.notification.notify", side_effect=RuntimeError("no backend")):
        from utils.notification import notify
        notify("タイトル", "メッセージ")
        captured = capsys.readouterr()
        assert "タイトル" in captured.out
```

---

### 8-07: `tests/test_config.py` — エラーパス追加

**既存テスト末尾に追加:**
```python
def test_load_corrupted_json(config_path):
    with open(config_path, "w") as f:
        f.write("{invalid json")
    cfg = Config(config_path)
    assert cfg.get("storage_provider") == "google_drive"
    assert os.path.exists(config_path + ".bak")


def test_thread_safe_set(config_path):
    import threading
    cfg = Config(config_path)
    errors = []

    def writer(key, value):
        try:
            for _ in range(50):
                cfg.set(key, value)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=writer, args=("key1", "val1")),
        threading.Thread(target=writer, args=("key2", "val2")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
```

---

### 8-08: `tests/test_tray_app.py` — エラーパス + シャットダウンテスト追加

**既存テスト末尾に追加:**
```python
def test_quit_stops_recorder():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING

    app.quit()
    app._recorder_factory.return_value[0].stop.assert_called()


def test_pipeline_error_returns_to_idle():
    app = make_tray_app()
    app._state = State.PROCESSING
    app._session_dir = "/tmp/test"
    app._pipeline.run.side_effect = Exception("test error")

    app._run_pipeline()
    assert app.state == State.IDLE


def test_start_face_to_face_noop_when_recording():
    app = make_tray_app()
    app._monitor.detect.return_value = True
    app.tick()
    assert app.state == State.RECORDING

    app.start_face_to_face()
    assert app._recorder_factory.call_count == 1
```

---

## 付録A: 新規作成ファイル一覧

| ファイル | Phase | 内容 |
|---------|-------|------|
| `pyproject.toml` | Phase 1 | パッケージメタデータ、依存関係 |
| `build.sh` | Phase 1 | macOS PyInstaller ビルドスクリプト |
| `exceptions.py` | Phase 2 | カスタム例外階層 |
| `utils/retry.py` | Phase 2 | リトライユーティリティ |
| `tests/conftest.py` | Phase 8 | プラットフォームフィクスチャ |
| `tests/test_notification.py` | Phase 8 | 通知ユーティリティテスト |

---

## 付録B: 全修正ファイルマトリクス

| ファイル | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 6 | Phase 8 |
|---------|---------|---------|---------|---------|---------|---------|---------|
| `main.py` | BUG-02 | | **全体** | | | | |
| `config.py` | | | **全体** | | | | |
| `pipeline.py` | | L4 | **全体** | | | | |
| `exceptions.py` | | | **新規** | | | | |
| `utils/retry.py` | | | **新規** | | | | |
| `utils/notification.py` | | **全体** | | | | | |
| `recorder/audio.py` | | | **全体** | | (含む) | | |
| `recorder/screen.py` | BUG-05 | | **全体** | | (含む) | | |
| `transcriber/gemini.py` | BUG-06 | | **全体** | | | | |
| `generator/minutes.py` | BUG-01 | | **全体** | | | | |
| `uploader/google_drive.py` | | | **全体** | | | | |
| `uploader/onedrive.py` | | | **全体** | | | | |
| `tray/app.py` | BUG-03,04 | | | **全体** | | | |
| `tray/monitor.py` | | **全体** | | | | | |
| `tray/icons.py` | | **全体** | | | | | |
| `ui/app.py` | | L1-3 | | **全体** | | | |
| `ui/setup.py` | | fonts | | | **修正** | **修正** | |
| `ui/widgets.py` | | **fonts** | | | | | |
| `requirements.txt` | | **全体** | | | | | |
| `pyproject.toml` | | **新規** | | | | | |
| `build.sh` | | **新規** | | | | | |
| `.gitignore` | | **追加** | | | | | |
| `tests/conftest.py` | | | | | | | **新規** |
| `tests/test_audio_recorder.py` | | | | | | | **全体** |
| `tests/test_screen_recorder.py` | | | | | | | **全体** |
| `tests/test_monitor.py` | | | | | | | **全体** |
| `tests/test_pipeline.py` | | | | | | | **追加** |
| `tests/test_tray_app.py` | | | | | | | **追加** |
| `tests/test_config.py` | | | | | | | **追加** |
| `tests/test_notification.py` | | | | | | | **新規** |

---

## 受入条件チェックリスト（全ゴール統合）

### macOS 起動
- [ ] `pip install -r requirements.txt` がエラーなく完了
- [ ] `python main.py --gui` がインポートエラーなく起動
- [ ] UI 文字が日本語フォントで正しくレンダリング

### レコーダー
- [ ] macOS で `AudioRecorder.list_devices()` がマイクデバイスを返す
- [ ] macOS で対面モード録音が WAV ファイルを生成
- [ ] macOS でオンラインモード録画が MP4 + WAV を生成
- [ ] `stop()` 後に FFmpeg プロセスが残存しない
- [ ] Windows で既存の動作が壊れない

### ウィンドウ検出
- [ ] macOS で Zoom/Teams/Meet を検出
- [ ] 画面収録権限未付与時にバンドルID フォールバックが動作
- [ ] メニューバーアイコンが正しく表示

### エラーハンドリング
- [ ] `~/.gijiroku-ai/app.log` にログ出力
- [ ] Gemini API エラー時に自動リトライ（最大3回）
- [ ] パイプライン途中失敗後にリジューム可能
- [ ] `config.json` 破損時に自動復旧
- [ ] FFmpeg 未インストール時にユーザーフレンドリーなエラー
- [ ] OneDrive `requests` に `timeout` 設定済み

### スレッド安全性
- [ ] `tray/app.py` の全共有状態が `Lock` で保護
- [ ] `quit()` がモニタスレッドの `join()` を実行
- [ ] 録音中のウィンドウクローズで FFmpeg が正常終了

### OneDrive
- [ ] 4MB 超ファイルがセッションアップロードで成功
- [ ] 日本語フォルダ/ファイル名でアップロード成功

### テスト
- [ ] macOS で `pytest tests/ -v` が収集エラーなしで完了
- [ ] Windows 専用テストが macOS でスキップ
- [ ] エラーパステストが各モジュールに存在
