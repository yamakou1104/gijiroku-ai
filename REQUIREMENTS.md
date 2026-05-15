# 議事録AI 要件定義書

> **作成日**: 2026-05-13  
> **対象バージョン**: v0.1.0（初回リリースに向けた品質確保）  
> **対象プラットフォーム**: macOS (Darwin) / Windows

---

## 目次

1. [Goal 1: macOS対応 — レコーダー (FFmpeg/AVFoundation)](#goal-1-macos対応--レコーダー-ffmpegavfoundation)
2. [Goal 2: macOS対応 — ウィンドウ検出 (会議自動検知)](#goal-2-macos対応--ウィンドウ検出-会議自動検知)
3. [Goal 3: 依存関係とプロジェクト構成の整備](#goal-3-依存関係とプロジェクト構成の整備)
4. [Goal 4: FFmpegのインストールとセットアップ](#goal-4-ffmpegのインストールとセットアップ)
5. [Goal 5: エラーハンドリングとリトライ機構](#goal-5-エラーハンドリングとリトライ機構)
6. [Goal 6: スレッド安全性の確保](#goal-6-スレッド安全性の確保)
7. [Goal 7: OneDrive大容量ファイルアップロード対応](#goal-7-onedrive大容量ファイルアップロード対応)
8. [Goal 8: テスト基盤の修正とカバレッジ向上](#goal-8-テスト基盤の修正とカバレッジ向上)

---

## Goal 1: macOS対応 — レコーダー (FFmpeg/AVFoundation)

### 1.1 背景

現在のレコーダーモジュール (`recorder/audio.py`, `recorder/screen.py`) は Windows 専用の DirectShow (`dshow`) および GDI画面キャプチャ (`gdigrab`) に依存している。macOSでは FFmpeg の `avfoundation` フレームワークを使用する必要がある。

### 1.2 現状の問題

| ファイル | 行番号 | 問題 |
|---------|--------|------|
| `recorder/audio.py` | L21 | `"-f", "dshow"` — macOSに存在しない |
| `recorder/audio.py` | L22 | `"-i", f"audio={self._mic_device}"` — dshow固有のデバイス指定形式 |
| `recorder/audio.py` | L51 | `"-f", "dshow", "-i", "dummy"` — デバイス列挙もdshow固有 |
| `recorder/audio.py` | L57 | `re.search(r'"(.+?)"\s+\(audio\)', line)` — dshow出力形式の正規表現 |
| `recorder/screen.py` | L21 | `"-f", "gdigrab"` — Windows GDI専用 |
| `recorder/screen.py` | L23 | `"-i", "desktop"` — gdigrab固有の入力指定 |
| `recorder/screen.py` | L24-25 | `"-f", "dshow"` — 動画コマンド内の音声入力 |
| `recorder/screen.py` | L36-37 | `"-f", "dshow"` — 音声コマンド |

### 1.3 要件

#### 1.3.1 音声録音（対面モード）

**プラットフォーム分岐を `_build_command()` に追加する。**

- **Windows (現行):**
  ```
  ffmpeg -y -f dshow -i "audio={device_name}" -ac 1 -ar 16000 \
    -f segment -segment_time 1800 -reset_timestamps 1 recording_%03d.wav
  ```

- **macOS (新規):**
  ```
  ffmpeg -y -f avfoundation -i "none:{device_index}" -ac 1 -ar 16000 \
    -f segment -segment_time 1800 -reset_timestamps 1 recording_%03d.wav
  ```

- `sys.platform` で分岐する。
- macOSではデバイスを**インデックス番号**（整数）で指定する（名前ではなく）。
- `-f segment -segment_time` はFFmpegの出力マクサーオプションであり、avfoundationでも同様に動作する。
- AVFoundationのネイティブサンプリングレートは48kHzだが、`-ar 16000` でFFmpegが内部リサンプリングを行う。

#### 1.3.2 画面録画（オンラインモード）

**`_build_video_command()` と `_build_audio_command()` にプラットフォーム分岐を追加する。**

- **Windows (現行):** gdigrab + dshow の2入力
- **macOS (新規):** avfoundation の単一入力で画面+音声を同時キャプチャ
  ```
  ffmpeg -y -f avfoundation -framerate 10 -i "{screen_index}:{audio_index}" \
    -c:v libx264 -preset ultrafast -crf 28 -c:a aac recording.mp4
  ```
- 音声セグメント用コマンドは 1.3.1 と同じ。

#### 1.3.3 デバイス列挙

**`list_devices()` のプラットフォーム分岐:**

- **Windows (現行):**
  ```
  ffmpeg -list_devices true -f dshow -i dummy
  ```
  出力形式: `[dshow] "Microphone Name" (audio)`
  正規表現: `r'"(.+?)"\s+\(audio\)'`

- **macOS (新規):**
  ```
  ffmpeg -f avfoundation -list_devices true -i ""
  ```
  出力形式:
  ```
  [AVFoundation indev @ ...] AVFoundation audio devices:
  [AVFoundation indev @ ...] [0] MacBook Pro Microphone
  [AVFoundation indev @ ...] [1] BlackHole 2ch
  ```
  正規表現: `r'\[(\d+)\]\s+(.+)$'`（`AVFoundation audio devices:` セクション以降のみ）

- macOSでは `list_devices()` が `(index, name)` のタプルリストを返すように変更する。UIにはnameを表示し、コマンドにはindexを使用する。

#### 1.3.4 録音停止方法

- **Windows:** `process.communicate(input=b"q")` — 現行通り
- **macOS:** `process.send_signal(signal.SIGINT)` + `process.wait(timeout=10)` — SIGINTの方がavfoundationではより確実
- フォールバック: タイムアウト時は `process.terminate()` → `process.kill()`

#### 1.3.5 システムオーディオキャプチャ（macOS固有の制約）

**macOSにはシステムオーディオのループバックデバイスが存在しない。** オンラインモード（Zoom/Teams/Meetの音声キャプチャ）には仮想オーディオドライバが必要。

- **推奨:** BlackHole（無料、オープンソース）`brew install blackhole-2ch`
- セットアップウィザードで BlackHole の有無を検出し、未インストール時はセットアップガイドを表示する。
- デバイスリストに BlackHole が表示されたら、そのインデックスを使用してシステムオーディオをキャプチャ可能。

#### 1.3.6 macOS権限

- **マイクアクセス:** macOS はアプリに対してマイクアクセス許可を要求する。初回起動時に許可ダイアログが表示される。
- **画面収録:** オンラインモードでは「システム設定 > プライバシーとセキュリティ > 画面収録」で許可が必要。

### 1.4 修正対象ファイル

| ファイル | 修正内容 |
|---------|---------|
| `recorder/audio.py` | `_build_command()`, `stop()`, `list_devices()` にプラットフォーム分岐追加 |
| `recorder/screen.py` | `_build_video_command()`, `_build_audio_command()`, `stop()` にプラットフォーム分岐追加 |
| `ui/setup.py` | デバイスリスト表示をタプル対応に変更。BlackHole検出ロジック追加 |

### 1.5 受入条件

- [ ] macOS上で `AudioRecorder.list_devices()` がマイクデバイスのリストを返すこと
- [ ] macOS上で対面モード録音（`AudioRecorder.start()` → `stop()`）が正常に動作し、WAVファイルが生成されること
- [ ] macOS上で30分超の録音が正しくセグメント分割されること
- [ ] macOS上でオンラインモード録画（`ScreenRecorder.start()` → `stop()`）が正常に動作し、MP4 + WAVファイルが生成されること
- [ ] `stop()` 後にFFmpegプロセスが残存しないこと
- [ ] Windows上で既存の動作が壊れないこと

---

## Goal 2: macOS対応 — ウィンドウ検出 (会議自動検知)

### 2.1 背景

`tray/monitor.py` は `win32gui.EnumWindows()` を使用してウィンドウタイトルを取得し、Zoom/Teams/Meetの会議を検出している。macOSには `win32gui` が存在しないため、代替手段が必要。

### 2.2 現状の問題

| ファイル | 行番号 | 問題 |
|---------|--------|------|
| `tray/monitor.py` | L1 | `import win32gui` — macOSでImportError |
| `tray/monitor.py` | L14 | `win32gui.EnumWindows(callback, None)` — Windows API |
| `tray/monitor.py` | L20 | `win32gui.IsWindowVisible(hwnd)` — Windows API |
| `tray/monitor.py` | L22 | `win32gui.GetWindowText(hwnd)` — Windows API |
| `tray/app.py` | L7 | `from tray.monitor import MeetingMonitor` — 間接的にwin32guiをインポート |

### 2.3 技術選定

| 方式 | 長所 | 短所 | 採用 |
|------|------|------|------|
| **pyobjc (CGWindowListCopyWindowInfo)** | 高速(平均2.27ms)、ウィンドウタイトル取得可能 | 画面収録権限が必要（タイトル取得のため） | **推奨** |
| osascript (AppleScript) | 追加パッケージ不要 | アクセシビリティ権限が必要、権限未付与時にハング | 不採用 |
| NSWorkspace (pyobjc) | 権限不要 | ウィンドウタイトル取得不可（アプリ名のみ） | フォールバック |
| lsappinfo | 追加パッケージ不要 | ウィンドウタイトル取得不可 | 不採用 |

### 2.4 要件

#### 2.4.1 プラットフォーム分岐アーキテクチャ

`tray/monitor.py` を以下のように再構成する:

```python
import sys

class MeetingMonitor:
    """会議ウィンドウ検出 — プラットフォーム自動切替"""
    
    PATTERNS = ["zoom meeting", "zoom webinar", "microsoft teams", "meet - "]
    
    def detect(self) -> bool:
        titles = self._get_window_titles()
        for title in titles:
            lower = title.lower()
            if any(p in lower for p in self.PATTERNS):
                return True
        return False
    
    def _get_window_titles(self) -> list[str]:
        if sys.platform == "win32":
            return self._get_titles_win32()
        elif sys.platform == "darwin":
            return self._get_titles_macos()
        return []
```

#### 2.4.2 macOSでのウィンドウタイトル取得

```python
import Quartz

def _get_titles_macos(self) -> list[str]:
    options = (Quartz.kCGWindowListOptionOnScreenOnly |
               Quartz.kCGWindowListExcludeDesktopElements)
    windows = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
    titles = []
    for w in windows:
        owner = w.get(Quartz.kCGWindowOwnerName, "")
        name = w.get(Quartz.kCGWindowName, "")
        layer = w.get(Quartz.kCGWindowLayer, -1)
        if layer == 0:
            titles.append(f"{owner}: {name}")
    return titles
```

#### 2.4.3 画面収録権限未付与時のフォールバック

- `kCGWindowName` が空文字列で返される場合、画面収録権限が未付与。
- フォールバック: `NSWorkspace.sharedWorkspace().runningApplications()` でバンドルID検出:
  - Zoom: `us.zoom.xos`
  - Teams: `com.microsoft.teams2`
  - Google Meet: **検出不可**（ブラウザ内で動作するため）
- フォールバック動作中であることをユーザーに通知し、画面収録権限の付与を案内する。

#### 2.4.4 会議検出パターン（macOS固有）

| アプリ | ownerName | windowName 例 | 検出方法 |
|--------|-----------|---------------|---------|
| Zoom | `zoom.us` | `Zoom Meeting` | ownerName or windowName |
| Teams | `Microsoft Teams` | `Microsoft Teams` | ownerName or windowName |
| Google Meet | `Google Chrome` / `Safari` | `Meet - xxx` | windowName のみ（権限必要） |

#### 2.4.5 pystray (メニューバー) macOS対応

- pystrayはmacOSで動作するが、メニューバーアイコンとして表示される。
- `pystray.Icon.run()` はメインスレッドから呼び出す必要がある（AppKit要件）。現行コードで対応済み。
- macOSメニューバーアイコンの推奨サイズ: **44x44ピクセル**（@2x Retina対応）。現行の64x64は自動縮小されるが最適ではない。

#### 2.4.6 アイコン生成（macOS最適化）

`tray/icons.py` の修正:

| 項目 | Windows (現行) | macOS (新規) |
|------|---------------|-------------|
| サイズ | 64x64 | 44x44 |
| CJKフォント | 自動（Windows標準搭載） | `/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc` を明示指定 |
| ダークモード | 非対応 | 非対応（カラーアイコンのためテンプレート化不可） |

### 2.5 修正対象ファイル

| ファイル | 修正内容 |
|---------|---------|
| `tray/monitor.py` | プラットフォーム分岐、macOSはCGWindowListCopyWindowInfo使用 |
| `tray/icons.py` | macOSアイコンサイズ(44x44)、CJKフォント明示指定 |
| `requirements.txt` | `pyobjc-framework-Quartz>=10.0; sys_platform == "darwin"` 追加 |

### 2.6 受入条件

- [ ] macOS上で `MeetingMonitor.detect()` が Zoom/Teams/Meet のウィンドウを正しく検出すること
- [ ] 画面収録権限が未付与の場合、バンドルIDフォールバックでZoom/Teamsを検出できること
- [ ] 画面収録権限が未付与の場合、ユーザーに権限付与を案内する通知が表示されること
- [ ] macOS上でトレイ（メニューバー）アイコンが正しく表示されること
- [ ] アイコンの状態変更（idle/recording/processing）が反映されること
- [ ] macOS上で「録」の文字が正しくレンダリングされること
- [ ] Windows上で既存の動作が壊れないこと

---

## Goal 3: 依存関係とプロジェクト構成の整備

### 3.1 背景

プロジェクトに `pyproject.toml` がなく、`requirements.txt` にはプラットフォーム条件のないWindows専用パッケージ(`pywin32`)が含まれている。仮想環境も未構成。

### 3.2 現状の問題

| 問題 | 影響 |
|------|------|
| `requirements.txt` に `pywin32>=306` が無条件記載 | macOSで `pip install -r requirements.txt` が失敗 |
| `pyproject.toml` が存在しない | パッケージメタデータ、依存関係の条件指定が不可 |
| 仮想環境が未構成 | システムPythonに依存。再現性なし |
| `tray/monitor.py` の `import win32gui` がトップレベル | macOSでインポート時にクラッシュ |
| `pipeline.py` の `from utils.notification import notify` がトップレベル | plyer未インストール時にインポートチェーンが壊れる |

### 3.3 要件

#### 3.3.1 `pyproject.toml` の作成

```toml
[project]
name = "gijiroku-ai"
version = "0.1.0"
description = "会議の録音・文字起こし・議事録生成を自動で行うデスクトップアプリ"
requires-python = ">=3.10"

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

#### 3.3.2 `requirements.txt` の修正

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

#### 3.3.3 インポートチェーンの修正

**壊れているインポートチェーン:**
```
main.py → tray/app.py → tray/monitor.py → import win32gui  [macOSでクラッシュ]
main.py → pipeline.py → utils/notification.py → from plyer import notification  [plyer未インストールでクラッシュ]
```

**修正方針:**

| ファイル | 行 | 修正 |
|---------|-----|------|
| `tray/monitor.py` | L1 | `import win32gui` → プラットフォーム条件付きインポート |
| `pipeline.py` | L4 | `from utils.notification import notify` → `run()` メソッド内での遅延インポートに変更 |
| `utils/notification.py` | L1 | `from plyer import notification` → try/exceptでガード |

**`utils/notification.py` の修正後:**
```python
def notify(title, message, timeout=10):
    try:
        from plyer import notification as plyer_notification
        plyer_notification.notify(
            title=title, message=message,
            app_name="議事録AI", timeout=timeout,
        )
    except Exception:
        print(f"[通知] {title}: {message}")
```

#### 3.3.4 UIフォントのプラットフォーム対応

| プラットフォーム | 日本語フォント | 絵文字フォント |
|---------------|-------------|-------------|
| Windows | `Meiryo UI` | `Segoe UI Emoji` |
| macOS | `Hiragino Sans` | `Apple Color Emoji` |

`ui/widgets.py`, `ui/setup.py`, `ui/app.py` 内の全フォント指定に `sys.platform` 分岐を追加。

#### 3.3.5 ビルドスクリプト（macOS用）

`build.sh` を新規作成（`build.bat` のmacOS版）:

- PyInstaller で `.app` バンドルを生成
- `--hidden-import "pystray._darwin"` を使用
- `--hidden-import "plyer.platforms.macosx.notification"` を使用
- `--add-data "credentials:credentials"` (macOSはセパレータが `:`)
- ffmpegバイナリをバンドル（`ffmpeg`, `ffprobe` — 拡張子なし）

### 3.4 修正対象ファイル

| ファイル | 修正内容 |
|---------|---------|
| `pyproject.toml` | 新規作成 |
| `requirements.txt` | プラットフォーム条件追加 |
| `tray/monitor.py` | インポート修正 |
| `pipeline.py` | notify の遅延インポート |
| `utils/notification.py` | try/exceptガード |
| `ui/widgets.py` | フォント分岐 |
| `ui/setup.py` | フォント分岐 |
| `ui/app.py` | フォント分岐 |
| `build.sh` | 新規作成 |

### 3.5 受入条件

- [ ] macOSで `pip install -r requirements.txt` がエラーなく完了すること
- [ ] macOSで `python main.py --gui` がインポートエラーなく起動すること
- [ ] macOSでUI文字が日本語フォントで正しくレンダリングされること
- [ ] `pip install -e .` で開発用インストールが可能なこと
- [ ] Windows上で既存の動作が壊れないこと

---

## Goal 4: FFmpegのインストールとセットアップ

### 4.1 背景

FFmpegは本アプリケーションの録音・録画の中核であるが、現在のmacOS環境にインストールされていない。

### 4.2 要件

#### 4.2.1 FFmpegのインストール

```bash
# Homebrewのインストール（未インストールの場合）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# FFmpegのインストール
brew install ffmpeg
```

#### 4.2.2 セットアップウィザードへのFFmpeg検出追加

`ui/setup.py` に以下の検出ロジックを追加:

```python
import shutil

def _check_ffmpeg():
    return shutil.which("ffmpeg") is not None
```

- セットアップウィザードの最初のステップでFFmpegの存在を確認する。
- 未インストールの場合、インストール手順を表示する:
  - macOS: `brew install ffmpeg`
  - Windows: FFmpegの公式サイトからダウンロードしてPATHに追加

#### 4.2.3 BlackHole（macOSシステムオーディオ）のセットアップガイド

オンラインモード使用時、macOSではシステムオーディオのキャプチャにBlackHoleが必要。
セットアップウィザードのストレージ選択後に、オンラインモードの説明を追加:

1. BlackHoleのインストール: `brew install blackhole-2ch`
2. Audio MIDI設定で「複数出力装置」を作成
3. システム出力を「複数出力装置」に変更
4. 録音デバイスとしてBlackHoleを選択

### 4.3 受入条件

- [ ] `ffmpeg -version` が正常に出力されること
- [ ] セットアップウィザードがFFmpegの有無を検出し、未インストール時に案内を表示すること

---

## Goal 5: エラーハンドリングとリトライ機構

### 5.1 背景

現在のコードベースにはエラーハンドリングがほぼ皆無であり、ロギング機構も一切存在しない。API呼び出しのリトライ、パイプラインのチェックポイント、プロセスのクリーンアップがすべて欠如している。

### 5.2 カスタム例外階層の定義

```python
# exceptions.py（新規作成）

class GijirokuError(Exception):
    """基底例外クラス"""

class ConfigurationError(GijirokuError):
    """設定不備（APIキー未設定、無効な設定値）"""

class RecordingError(GijirokuError):
    """録音エラー（FFmpeg起動失敗、デバイス未接続）"""

class TranscriptionError(GijirokuError):
    """文字起こしエラー（Gemini APIエラー）"""

class GenerationError(GijirokuError):
    """議事録生成エラー（Gemini APIエラー）"""

class UploadError(GijirokuError):
    """アップロードエラー"""

class AuthenticationError(UploadError):
    """OAuth認証エラー（トークン期限切れ、取り消し）"""

class NetworkError(UploadError):
    """ネットワーク接続エラー"""

class PipelineError(GijirokuError):
    """パイプライン全体のエラー"""
```

### 5.3 ロギング基盤の導入

**`main.py` にロギング設定を追加:**

```python
import logging
from logging.handlers import RotatingFileHandler

def _setup_logging():
    log_dir = os.path.expanduser("~/.gijiroku-ai")
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=5*1024*1024, backupCount=3,
        encoding="utf-8"
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[handler]
    )
```

- 全モジュールで `logger = logging.getLogger(__name__)` を使用する。
- ログファイル: `~/.gijiroku-ai/app.log`（最大5MB、3世代ローテーション）

### 5.4 リトライ機構

**`utils/retry.py`（新規作成）:**

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
                raise
            logger.warning(f"Attempt {attempt+1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)
```

**適用箇所:**

| ファイル | 行 | API呼び出し | リトライ対象の例外 |
|---------|-----|-----------|-----------------|
| `transcriber/gemini.py` | L26 | `genai.upload_file()` | `ResourceExhausted`, `ServiceUnavailable`, `DeadlineExceeded` |
| `transcriber/gemini.py` | L27-30 | `model.generate_content()` | 同上 + `InternalServerError` |
| `generator/minutes.py` | L47 | `model.generate_content()` | 同上 |
| `uploader/google_drive.py` | L39-47 | `.list().execute()` | `HttpError` (500/503) |
| `uploader/google_drive.py` | L61 | `.create().execute()` | `HttpError` (500/503) |
| `uploader/google_drive.py` | L69-74 | `.create().execute()` | `HttpError` (500/503), timeout |
| `uploader/onedrive.py` | L59 | `requests.post()` | 429, 500, 502, 503, 504 |
| `uploader/onedrive.py` | L67 | `requests.put()` | 同上 |

### 5.5 パイプラインのチェックポイント/リジューム

**`pipeline.py` の修正:**

各ステージ完了後に `pipeline_state.json` をセッションディレクトリに書き出す。`run()` 開始時に既存のステートファイルを確認し、完了済みステージをスキップする。

```json
{
  "stage": "transcribed",
  "timestamp": "2026-05-13T14:30:00",
  "transcript_path": "transcript.txt",
  "minutes_path": null
}
```

ステージ:
1. `segments_listed` — セグメント特定完了
2. `transcribed` — `transcript.txt` 生成完了
3. `generated` — `minutes.md` 生成完了
4. `uploaded` — 全ファイルアップロード完了

### 5.6 ファイル別エラーハンドリング要件

#### 5.6.1 `pipeline.py`

| 行 | 問題 | 対応 |
|----|------|------|
| L19 | `list_segments()` の結果が空でも続行 | 空チェック追加。空なら `PipelineError` を送出 |
| L22-25 | `transcribe_all()` のAPI例外未処理 | try/except + `TranscriptionError` にラップ |
| L28-29 | `transcript.txt` の非アトミック書き込み | 一時ファイル + `os.replace` パターン |
| L32 | `generate()` のAPI例外未処理 | try/except + `GenerationError` にラップ |
| L34-36 | `minutes.md` の非アトミック書き込み | 一時ファイル + `os.replace` パターン |
| L39 | `uploader_factory()` の認証例外未処理 | try/except + `AuthenticationError` / `NetworkError` |
| L41 | `upload_session()` の例外未処理 | try/except。アップロード失敗時はローカルファイルパスをユーザーに通知 |
| L43 | `notify()` の例外未処理 | try/except で黙殺（通知失敗でパイプラインを止めない） |
| 全体 | `transcriber`/`generator` が `None` の可能性 | `run()` 冒頭で `None` チェック。`ConfigurationError` を送出 |

#### 5.6.2 `transcriber/gemini.py`

| 行 | 問題 | 対応 |
|----|------|------|
| L9 | 空APIキーの検証なし | `__init__` で非空チェック。`ValueError` 送出 |
| L26 | `genai.upload_file()` の例外未処理 | リトライ付きtry/except |
| L27-30 | `generate_content()` の例外未処理 | リトライ付きtry/except |
| L31 | `response.text` がsafetyフィルターで `ValueError` | `response.candidates` を事前チェック。フィルター時はプレースホルダー文字列を返す |
| L37 | 個別セグメント失敗で全体中断 | セグメント単位でtry/except。失敗セグメントはプレースホルダー挿入して続行 |
| L48 | `line.index("]")` が `ValueError` | `find()` に変更 + 見つからない場合はスキップ |
| L52 | `int(parts[0])` が `ValueError` | try/except + 失敗時は行をそのまま返す |
| 全体 | アップロードしたファイルの削除なし | `genai.delete_file()` を呼び出してクリーンアップ |

#### 5.6.3 `generator/minutes.py`

| 行 | 問題 | 対応 |
|----|------|------|
| L8 | 空APIキーの検証なし | `__init__` で非空チェック |
| L44 | 空トランスクリプトの検証なし | `generate()` 冒頭で非空チェック。空なら `ValueError` |
| L47 | `generate_content()` の例外未処理 | リトライ付きtry/except |
| L48 | `response.text` の `ValueError` | safetyフィルターチェック |
| 全体 | コンテキストウィンドウ超過の考慮なし | `InvalidArgument` をキャッチし、トランスクリプト分割を提案するエラーメッセージ |

#### 5.6.4 `uploader/google_drive.py`

| 行 | 問題 | 対応 |
|----|------|------|
| L24 | トークンファイルの破損で `JSONDecodeError` | catch → 破損ファイル削除 → 再認証フローへ |
| L27 | `creds.refresh()` で `RefreshError` | catch → トークンファイル削除 → 再認証フローへ |
| L29-32 | `InstalledAppFlow` の各種例外 | `FileNotFoundError`, `ValueError` を個別catch |
| L33-34 | トークン書き込みの非アトミック性 | 一時ファイル + `os.replace` |
| L69-74 | `resumable=True` だが実際のリジューム実装なし | 大容量ファイル用に `next_chunk()` ループを実装 |
| L80-83 | 個別ファイルの失敗で残り全スキップ | ファイル単位でtry/except。失敗リストを返す |
| 全体 | `authenticate()` 未呼び出し時の `AttributeError` | `upload_session()` 冒頭で `self._service is not None` を検証 |

#### 5.6.5 `uploader/onedrive.py`

| 行 | 問題 | 対応 |
|----|------|------|
| L23 | `open().read()` のファイルハンドルリーク | `with open() as f:` に変更 |
| L23 | トークンキャッシュ破損で例外 | try/except → 破損時は新規認証 |
| L39 | `flow["message"]` の `KeyError` | `"user_code" not in flow` チェック追加 |
| L39 | `print()` がGUI/トレイアプリで見えない | UIまたは通知経由でデバイスコードを表示 |
| L42 | `result["access_token"]` の `KeyError` | `"access_token" not in result` チェック + `error_description` 表示 |
| L45-46 | トークンキャッシュの非アトミック書き込み | 一時ファイル + `os.replace` |
| L59, L67 | `requests` に `timeout` パラメータなし | `timeout=(10, 300)` を追加 |
| L60 | `raise_for_status()` のエラーメッセージが不親切 | レスポンスJSONの `error.message` を解析 |

#### 5.6.6 `recorder/audio.py`

| 行 | 問題 | 対応 |
|----|------|------|
| L35 | `Popen` で `FileNotFoundError` (FFmpeg未インストール) | try/except + `RecordingError` |
| L39 | `stderr=DEVNULL` でFFmpegエラーが不可視 | `stderr=PIPE` に変更 + 起動後0.5秒で `poll()` 確認 |
| L45 | `communicate()` にタイムアウトなし | `timeout=10` 追加。タイムアウト時は `kill()` |
| L46 | プロセス終了コード未確認 | `returncode` を確認してログ出力 |
| L14 | `is_recording` がプロセス実行状態を反映しない | `poll()` でプロセスの生存確認 |
| L51 | `list_devices()` の `FileNotFoundError` 未処理 | try/except → 空リスト返却 |
| 全体 | プロセスリソースのクリーンアップなし | `atexit` ハンドラ + `__del__` メソッド追加 |

#### 5.6.7 `recorder/screen.py`

| 行 | 問題 | 対応 |
|----|------|------|
| L50-56 | 2番目のPopen失敗時に1番目のプロセスが残存 | try/except + 1番目のプロセスを `kill()` してから再送出 |
| L66-67 | 2つの `communicate()` にタイムアウトなし | `timeout=10` 追加 |
| L66 | 1番目の `communicate()` 失敗時に2番目が呼ばれない | try/finally パターン |

#### 5.6.8 `config.py`

| 行 | 問題 | 対応 |
|----|------|------|
| L25 | `json.load()` で `JSONDecodeError` | catch → 破損ファイルをバックアップ → デフォルトで再作成 |
| L37-38 | 非アトミック書き込み | 一時ファイル + `os.replace` |
| 全体 | スレッド安全性なし | `threading.Lock` 追加 |
| 全体 | 入力バリデーションなし | 既知キーの型チェック追加 |

#### 5.6.9 `tray/app.py`

| 行 | 問題 | 対応 |
|----|------|------|
| L79-82 | `except Exception: pass` で全エラー黙殺 | `logging.exception()` + `notify("議事録AI", "処理中にエラーが発生しました")` |
| L66-67 | `_start_recording()` の例外未処理 | try/except + IDLE状態に戻す + ユーザー通知 |
| L113 | `tick()` の例外でモニタスレッドが死亡 | ループ内try/except + ログ + 続行 |
| L122-125 | `quit()` で `stop()` 失敗時にアイコンが残存 | try/finally パターン |

#### 5.6.10 `ui/app.py`

| 行 | 問題 | 対応 |
|----|------|------|
| L89-90 | `recorder_factory()` / `start()` の例外未処理 | try/except + `messagebox.showerror()` |
| L110, L113 | `self._root.after()` がウィンドウ破壊後に `TclError` | `winfo_exists()` チェック追加 |
| 全体 | `WM_DELETE_WINDOW` ハンドラなし | `protocol("WM_DELETE_WINDOW", self._on_close)` 追加 |
| 全体 | 録音中のウィンドウクローズでプロセスリーク | `_on_close()` で `recorder.stop()` を呼ぶ |
| L44-49 | 録音中にモードボタンが無効化されない | 録音開始時にモードボタンを `state="disabled"` に設定 |

### 5.7 修正対象ファイル

| ファイル | 修正内容 |
|---------|---------|
| `exceptions.py` | 新規作成 — カスタム例外階層 |
| `utils/retry.py` | 新規作成 — リトライユーティリティ |
| `main.py` | ロギング設定追加 |
| `pipeline.py` | チェックポイント、エラーハンドリング、バリデーション |
| `transcriber/gemini.py` | リトライ、セグメント別エラー処理、入力バリデーション |
| `generator/minutes.py` | リトライ、入力バリデーション |
| `uploader/google_drive.py` | トークンリフレッシュ、リトライ、個別ファイルエラー |
| `uploader/onedrive.py` | ファイルハンドルリーク修正、認証エラー処理、timeout追加 |
| `recorder/audio.py` | FFmpeg検出、プロセス監視、タイムアウト付きstop |
| `recorder/screen.py` | 部分起動失敗処理、クリーンアップ |
| `config.py` | 破損復旧、アトミック書き込み、スレッドロック |
| `tray/app.py` | パイプラインエラー通知、モニタスレッド保護 |
| `ui/app.py` | ウィンドウクローズ処理、エラーダイアログ |

### 5.8 受入条件

- [ ] `~/.gijiroku-ai/app.log` にログが出力されること
- [ ] Gemini API一時エラー時に自動リトライが行われること（最大3回）
- [ ] パイプラインが途中失敗してもリジューム可能なこと（チェックポイントファイルの存在確認）
- [ ] 全API呼び出しの失敗がログに記録されること
- [ ] `config.json` が破損しても自動復旧してアプリが起動すること
- [ ] FFmpegが未インストールの場合にユーザーフレンドリーなエラーが表示されること
- [ ] `tray/app.py` のパイプライン失敗時にユーザーに通知が送られること（`except Exception: pass` の解消）
- [ ] ウィンドウクローズ時にFFmpegプロセスがクリーンアップされること
- [ ] OneDrive `requests` 呼び出しに `timeout` が設定されていること
- [ ] トークンファイルの書き込みがアトミックであること

---

## Goal 6: スレッド安全性の確保

### 6.1 背景

`tray/app.py` では複数スレッドが排他制御なしに共有状態を読み書きしている。`ui/app.py` ではウィンドウ破壊後のTkinter操作で `TclError` が発生する可能性がある。

### 6.2 `tray/app.py` のスレッド安全性

#### 6.2.1 共有可変状態の一覧

| 変数 | 書き込み箇所 | 読み取り箇所 | アクセススレッド |
|------|------------|------------|--------------|
| `self._state` | L24, 42, 48, 68, 75, 84 | L36, 40, 46, 50, 53, 57, 62 | モニタスレッド + メニューコールバック |
| `self._recorder` | L25, 66, 74 | L72, 67, 122 | モニタスレッド + メニューコールバック |
| `self._session_dir` | L26, 66, 83 | L80 | モニタスレッド + メニューコールバック |
| `self._grace_deadline` | L27, 43 | L50 | モニタスレッド |
| `self._running` | L29, 92, 121 | L112 | メインスレッド + モニタスレッド |

#### 6.2.2 特定されたレースコンディション

**RC1: `manual_stop()` vs `tick()` — 二重停止**
- モニタスレッドが `tick()` 内のGRACE_PERIOD分岐でstopを実行中に、ユーザーが「停止」をクリック
- `_stop_recording()` が2回実行され、パイプラインが2回起動する可能性

**RC2: `start_face_to_face()` vs `tick()` — 二重録音**
- 両方が同時に `IDLE` を確認し、両方が `_start_recording()` を呼ぶ
- 2つのFFmpegプロセスが起動し、1つがリークする

**RC3: `quit()` vs `tick()` — シャットダウン中の操作**
- `quit()` がrecorderをstopしている最中に `tick()` が新たな録音を開始する可能性

**RC4: `_update_icon()` — pystrayスレッド安全性**
- モニタスレッドから `self._tray_icon.icon = ...` を呼び出すが、pystrayの内部スレッドとの安全性が保証されない

#### 6.2.3 必要な修正

```python
import threading

class TrayApp:
    def __init__(self, ...):
        ...
        self._lock = threading.Lock()
        self._stop_event = threading.Event()  # _running ブールの代替
        self._monitor_thread = None  # スレッド参照を保持

    def tick(self):
        with self._lock:
            # 全状態遷移ロジック（ただしパイプラインは外で実行）
            ...

    def start_face_to_face(self):
        with self._lock:
            if self._state != State.IDLE:
                return
            self._start_recording("face_to_face")

    def manual_stop(self):
        with self._lock:
            if self._state not in (State.RECORDING, State.GRACE_PERIOD):
                return
            self._stop_recording()

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception:
                logging.exception("Error in monitor loop")
            self._stop_event.wait(POLL_INTERVAL_SECONDS)

    def quit(self):
        self._stop_event.set()
        with self._lock:
            if self._recorder:
                self._recorder.stop()
                self._recorder = None
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
        self._tray_icon.stop()  # ロック外で呼ぶ（デッドロック防止）
```

**重要な設計制約:**
- `_run_pipeline()` はロック外で実行する（長時間処理のためロック保持はNG）
- 状態遷移のみをロック内で行い、実際の処理（録音開始、パイプライン実行）はロック外で行う
- `_tray_icon.stop()` はロック外で呼ぶ（pystray内部スレッドとのデッドロック防止）
- `_stop_event.wait(POLL_INTERVAL_SECONDS)` で即座のシャットダウンが可能（`time.sleep` の代替）

### 6.3 `ui/app.py` のスレッド安全性

#### 6.3.1 必要な修正

| 問題 | 修正 |
|------|------|
| `WM_DELETE_WINDOW` ハンドラなし | `self._root.protocol("WM_DELETE_WINDOW", self._on_close)` |
| パイプラインスレッドから `after()` 呼び出し時に `TclError` | `self._root.winfo_exists()` チェック追加 |
| 録音中のウィンドウクローズでプロセスリーク | `_on_close()` で `recorder.stop()` |
| 録音中にモードボタンが再クリック可能 | 録音開始時にモードボタンを `disabled` に変更 |

```python
def _on_close(self):
    if self._recorder and self._recorder.is_recording:
        self._recorder.stop()
    self._root.destroy()

def _process_pipeline(self):
    try:
        ...
        if self._root.winfo_exists():
            self._root.after(0, self._reset_ui)
    except Exception as e:
        if self._root.winfo_exists():
            self._root.after(0, lambda: messagebox.showerror("エラー", str(e)))
```

### 6.4 修正対象ファイル

| ファイル | 修正内容 |
|---------|---------|
| `tray/app.py` | `threading.Lock` + `threading.Event` 追加、全共有状態アクセスの同期化 |
| `ui/app.py` | `WM_DELETE_WINDOW` ハンドラ、`winfo_exists()` チェック、ボタン無効化 |

### 6.5 受入条件

- [ ] `tray/app.py` の全共有可変状態が `threading.Lock` で保護されていること
- [ ] `_running` が `threading.Event` に置き換えられていること
- [ ] `quit()` がモニタスレッドの `join()` を呼んでいること
- [ ] パイプライン実行中にロックが保持されていないこと（デッドロック防止）
- [ ] `ui/app.py` にウィンドウクローズハンドラが実装されていること
- [ ] 録音中にウィンドウを閉じてもFFmpegプロセスが正常終了すること
- [ ] パイプラインスレッド内の `after()` 呼び出しが `winfo_exists()` で保護されていること
- [ ] 録音中にモードボタンがクリック不能であること

---

## Goal 7: OneDrive大容量ファイルアップロード対応

### 7.1 背景

現在の `uploader/onedrive.py` は Microsoft Graph APIのシンプルアップロード（`PUT /content`）を使用しているが、このAPIは **4MBの制限** がある。会議の録音ファイル（数十MB〜数百MB）のアップロードは必ず `413 Request Entity Too Large` で失敗する。

### 7.2 現状の問題

| ファイル | 行 | 問題 |
|---------|-----|------|
| `onedrive.py` | L63-69 | シンプルアップロード（4MB制限） |
| `onedrive.py` | L65 | 日本語ファイル名のURLエンコーディングなし |
| `onedrive.py` | L53 | `parent_path=None` 時のURLダブルコロン (`::`) |
| `onedrive.py` | L23 | ファイルハンドルリーク |
| `onedrive.py` | L39 | `flow["message"]` の `KeyError` 未処理 |
| `onedrive.py` | L42 | `result["access_token"]` の `KeyError` 未処理 |

### 7.3 要件

#### 7.3.1 アップロードセッション方式の実装

4MB超のファイルに対して、Microsoft Graph APIのアップロードセッション方式を使用する。

**プロトコル:**
1. `POST /me/drive/root:/{path}:/createUploadSession` でセッション作成
2. レスポンスの `uploadUrl` に対して、チャンクをPUTで送信
3. 各チャンクは **320KiBの倍数** でなければならない（最後のチャンクを除く）
4. 推奨チャンクサイズ: **3,276,800バイト** (10 × 320KiB ≒ 3.125MiB)
5. 最終チャンク送信後、サーバーは `201 Created` を返す

**重要な制約:**
- チャンクPUT時に `Authorization` ヘッダーを含めてはならない（uploadUrlが事前認証済み）
- `Content-Range: bytes {start}-{end}/{total}` ヘッダーが必要
- セッションは作成から48時間後に期限切れ

**エラー処理:**
| エラー | 対応 |
|--------|------|
| 5xxサーバーエラー | 指数バックオフでリトライ |
| 404 Not Found | セッション期限切れ → 最初から再作成 |
| 416 Range Not Satisfiable | サーバーが既にそのレンジを受信済み → GETでステータス確認して続行 |
| 接続断 | GETでuploadUrlのステータスを確認し、未送信レンジから再開 |

#### 7.3.2 ファイルサイズによる分岐

```python
SIMPLE_UPLOAD_LIMIT = 4 * 1024 * 1024  # 4MB

def upload_file(self, file_path, parent_path):
    file_size = os.path.getsize(file_path)
    if file_size <= SIMPLE_UPLOAD_LIMIT:
        return self._upload_simple(file_path, parent_path)
    else:
        return self._upload_session(file_path, parent_path)
```

#### 7.3.3 URLエンコーディングの修正

```python
from urllib.parse import quote

# 全てのGraph APIパスで日本語文字をパーセントエンコード
url = f"{GRAPH_URL}/me/drive/root:{quote(parent_path)}/{quote(filename)}:/content"
```

#### 7.3.4 認証エラーハンドリングの修正

```python
# initiate_device_flow のエラーチェック
flow = app.initiate_device_flow(scopes=SCOPES)
if "user_code" not in flow:
    raise AuthenticationError(f"デバイスフロー開始エラー: {flow.get('error_description', '不明')}")

# acquire_token_by_device_flow のエラーチェック
result = app.acquire_token_by_device_flow(flow)
if "access_token" not in result:
    raise AuthenticationError(f"認証失敗: {result.get('error_description', '不明')}")
```

#### 7.3.5 ファイルハンドルリークの修正

```python
# 修正前 (L23)
cache.deserialize(open(self._token_cache_path).read())

# 修正後
with open(self._token_cache_path, "r") as f:
    cache.deserialize(f.read())
```

### 7.4 修正対象ファイル

| ファイル | 修正内容 |
|---------|---------|
| `uploader/onedrive.py` | アップロードセッション実装、URLエンコード、認証エラー処理、ファイルハンドル修正 |

### 7.5 受入条件

- [ ] 4MB以下のファイルがシンプルアップロードで成功すること
- [ ] 4MB超のファイル（例: 100MB WAV）がアップロードセッション方式で成功すること
- [ ] 日本語を含むフォルダ名/ファイル名でアップロードが成功すること（`議事録AI/2026-05-13_会議`）
- [ ] チャンクアップロード中のネットワークエラーで自動リトライが行われること
- [ ] アップロード進捗がログに記録されること
- [ ] `initiate_device_flow()` 失敗時に `AuthenticationError` が送出されること
- [ ] `acquire_token_by_device_flow()` 失敗時に `AuthenticationError` が送出されること
- [ ] トークンキャッシュファイルのリード時にファイルハンドルが適切にクローズされること

---

## Goal 8: テスト基盤の修正とカバレッジ向上

### 8.1 背景

15テストファイル中6ファイルがインポートエラーで実行不能。プラットフォーム固有のアサーションがハードコードされており、エラーパスのテストが皆無。

### 8.2 現状の問題

| テストファイル | 状態 | 原因 |
|-------------|------|------|
| `test_monitor.py` | 収集エラー | `import win32gui` 失敗（macOS） |
| `test_tray_app.py` | 収集エラー | `tray/app.py` → `tray/monitor.py` → `win32gui` インポートチェーン |
| `test_google_drive.py` | 収集エラー | `google_auth_oauthlib` 未インストール |
| `test_icons.py` | 収集エラー | `PIL` (Pillow) 未インストール |
| `test_onedrive.py` | 収集エラー | `msal` 未インストール |
| `test_pipeline.py` | 収集エラー | `pipeline.py` → `utils/notification.py` → `plyer` インポートチェーン |

### 8.3 要件

#### 8.3.1 `tests/conftest.py` の作成

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

#### 8.3.2 テストファイル別修正

**`test_monitor.py`:**
- モジュールレベルで `pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="win32gui")` を追加
- macOS用のテストケースを追加（`CGWindowListCopyWindowInfo` をモック）

**`test_tray_app.py`:**
- Goal 3 のインポートチェーン修正（`tray/monitor.py` の条件付きインポート）により、収集エラーが解消される
- 追加テストケース:
  - `test_quit_stops_recorder` — `quit()` がrecorderをstopすること
  - `test_pipeline_error_returns_to_idle` — パイプライン例外後にIDLE状態に戻ること
  - `test_start_face_to_face_noop_when_recording` — 録音中のstart呼び出しが無視されること

**`test_audio_recorder.py`:**
- `test_build_command` と `test_build_command_contains_mic_device` に `@windows_only` デコレータ追加
- macOS用テスト追加:
  ```python
  @macos_only
  def test_build_command_macos():
      rec = AudioRecorder("0", ...)
      cmd = rec._build_command()
      assert "avfoundation" in cmd
      assert "none:0" in " ".join(cmd)
  ```

**`test_screen_recorder.py`:**
- `test_build_video_command` と `test_build_audio_command` に `@windows_only` デコレータ追加
- macOS用テスト追加

**`test_pipeline.py`:**
- Goal 3 のインポートチェーン修正により収集エラー解消
- 追加テストケース:
  - `test_run_with_empty_segments` — セグメントなしで `PipelineError` が送出されること
  - `test_run_transcription_failure` — トランスクリプション失敗時の挙動
  - `test_run_upload_failure_preserves_local_files` — アップロード失敗時もローカルファイルが保持されること
  - `test_run_resumes_from_checkpoint` — チェックポイントからのリジューム

#### 8.3.3 カバレッジゼロのファイルへのテスト追加

**`tests/test_notification.py`（新規）:**
```python
def test_notify_calls_plyer()       # plyer呼び出し確認
def test_notify_handles_import_error()  # plyer未インストール時のフォールバック
def test_notify_handles_runtime_error() # 通知バックエンドエラー時
```

**`tests/test_main.py`（新規）:**
```python
def test_build_components_creates_output_dir()   # 出力ディレクトリ作成
def test_build_components_no_api_key()            # APIキー未設定時
def test_recorder_factory_face_to_face()          # 対面→AudioRecorder
def test_recorder_factory_online()                # オンライン→ScreenRecorder
```

#### 8.3.4 エラーパステストの追加

各モジュールに最低1つのエラーパステストを追加:

| モジュール | テスト名 | テスト内容 |
|----------|---------|-----------|
| `transcriber/gemini.py` | `test_transcribe_segment_api_error` | API例外時にリトライが行われること |
| `transcriber/gemini.py` | `test_transcribe_segment_safety_filter` | safetyフィルター時にプレースホルダーが返ること |
| `generator/minutes.py` | `test_generate_empty_transcript` | 空トランスクリプトで `ValueError` が送出されること |
| `recorder/audio.py` | `test_start_ffmpeg_not_found` | FFmpeg未インストール時に `RecordingError` |
| `recorder/audio.py` | `test_stop_timeout` | FFmpegハング時にタイムアウト後 `kill()` が呼ばれること |
| `config.py` | `test_load_corrupted_json` | 破損JSONからの自動復旧 |
| `uploader/onedrive.py` | `test_upload_large_file_session` | 4MB超ファイルのセッションアップロード |
| `uploader/google_drive.py` | `test_authenticate_refresh_error` | トークンリフレッシュ失敗時の再認証フロー |

### 8.4 修正対象ファイル

| ファイル | 修正内容 |
|---------|---------|
| `tests/conftest.py` | 新規作成 — プラットフォームフィクスチャ |
| `tests/test_monitor.py` | プラットフォームスキップ + macOSテスト追加 |
| `tests/test_tray_app.py` | エラーパス・シャットダウンテスト追加 |
| `tests/test_audio_recorder.py` | プラットフォームスキップ + macOSテスト追加 |
| `tests/test_screen_recorder.py` | プラットフォームスキップ + macOSテスト追加 |
| `tests/test_pipeline.py` | エラーパス・リジュームテスト追加 |
| `tests/test_notification.py` | 新規作成 |
| `tests/test_main.py` | 新規作成 |

### 8.5 受入条件

- [ ] macOS上で `pytest tests/ -v` が収集エラーなしで完了すること
- [ ] Windows専用テストがmacOSで自動スキップされること
- [ ] macOS用テスト（avfoundation、CGWindowList）が存在すること
- [ ] エラーパステストが各モジュールに最低1つ存在すること
- [ ] 新規作成ファイル（`test_notification.py`, `test_main.py`）のテストが全パスすること
- [ ] テストカバレッジが全ソースファイルに対して存在すること（カバレッジゼロのファイルを解消）

---

## ゴール間の依存関係

```
Goal 3 (依存関係整備)
  ├─→ Goal 1 (レコーダーmacOS対応)   ← requirements.txt修正が前提
  ├─→ Goal 2 (ウィンドウ検出macOS対応) ← pyobjcの追加が前提
  └─→ Goal 8 (テスト基盤)             ← インポートチェーン修正が前提

Goal 4 (FFmpegインストール)
  └─→ Goal 1 (レコーダーmacOS対応)   ← FFmpegが必要

Goal 5 (エラーハンドリング)
  └─→ Goal 7 (OneDrive大容量)        ← リトライ機構を共有

Goal 6 (スレッド安全性)
  └─→ (独立して実施可能)
```

**推奨実施順序:**
1. Goal 3 → Goal 4 → Goal 1 → Goal 2（macOS対応一式）
2. Goal 5（エラーハンドリング）
3. Goal 6（スレッド安全性）
4. Goal 7（OneDrive大容量）
5. Goal 8（テスト — 全修正後に実施）

---

## 付録: 全修正対象ファイル一覧

| ファイル | Goal 1 | Goal 2 | Goal 3 | Goal 4 | Goal 5 | Goal 6 | Goal 7 | Goal 8 |
|---------|--------|--------|--------|--------|--------|--------|--------|--------|
| `recorder/audio.py` | **修正** | | | | **修正** | | | |
| `recorder/screen.py` | **修正** | | | | **修正** | | | |
| `tray/monitor.py` | | **修正** | **修正** | | | | | |
| `tray/app.py` | | | | | **修正** | **修正** | | |
| `tray/icons.py` | | **修正** | | | | | | |
| `ui/app.py` | | | **修正** | | **修正** | **修正** | | |
| `ui/setup.py` | **修正** | | **修正** | **修正** | | | | |
| `ui/widgets.py` | | | **修正** | | | | | |
| `pipeline.py` | | | **修正** | | **修正** | | | |
| `config.py` | | | | | **修正** | | | |
| `main.py` | | | | | **修正** | | | |
| `uploader/google_drive.py` | | | | | **修正** | | | |
| `uploader/onedrive.py` | | | | | **修正** | | **修正** | |
| `utils/notification.py` | | | **修正** | | | | | |
| `requirements.txt` | | **修正** | **修正** | | | | | |
| `pyproject.toml` | | | **新規** | | | | | |
| `exceptions.py` | | | | | **新規** | | | |
| `utils/retry.py` | | | | | **新規** | | | |
| `build.sh` | | | **新規** | | | | | |
| `tests/conftest.py` | | | | | | | | **新規** |
| `tests/test_notification.py` | | | | | | | | **新規** |
| `tests/test_main.py` | | | | | | | | **新規** |
| `tests/test_monitor.py` | | | | | | | | **修正** |
| `tests/test_tray_app.py` | | | | | | | | **修正** |
| `tests/test_audio_recorder.py` | | | | | | | | **修正** |
| `tests/test_screen_recorder.py` | | | | | | | | **修正** |
| `tests/test_pipeline.py` | | | | | | | | **修正** |
