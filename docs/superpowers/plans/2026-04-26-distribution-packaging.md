# 配布用パッケージング 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 議事録AIをエンドユーザーが .exe をダブルクリックするだけで使えるようにパッケージングする。OAuth認証情報を同梱し、セットアップ画面でワンクリック認証できるようにする。

**Architecture:** `utils/resource_path.py` でPyInstaller環境/開発環境を自動判定してリソースパスを解決。`credentials/` にOAuth認証情報を同梱。セットアップ画面にGoogle Drive / OneDrive認証ボタンを追加。PyInstallerで全依存＋FFmpegを1つの .exe にバンドル。

**Tech Stack:** PyInstaller, 既存モジュール群

---

## ファイル構成（追加・変更分）

```
gijiroku-ai/
  ├── credentials/
  │    ├── README.md               ← 開発者向けOAuth設定手順
  │    └── .gitkeep
  ├── utils/
  │    └── resource_path.py        ← リソースパス解決（新規）
  ├── ui/
  │    └── setup.py                ← 認証ボタン追加（変更）
  ├── uploader/
  │    └── google_drive.py         ← credentials_path デフォルト化（変更）
  ├── main.py                      ← credentials パス設定（変更）
  ├── gijiroku-ai.spec             ← PyInstaller spec（新規）
  ├── build.bat                    ← ビルドスクリプト（新規）
  └── requirements.txt             ← pyinstaller 追加（変更）
```

---

## Task 1: リソースパス解決ユーティリティ

**Files:**
- Create: `utils/resource_path.py`
- Create: `tests/test_resource_path.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_resource_path.py
import os
import sys
import pytest
from unittest.mock import patch
from utils.resource_path import get_resource_path, get_credentials_dir, get_app_data_dir

def test_get_resource_path_dev_mode():
    if hasattr(sys, "_MEIPASS"):
        pytest.skip("Running in PyInstaller bundle")
    path = get_resource_path("credentials")
    assert os.path.isabs(path)

def test_get_resource_path_frozen():
    with patch.object(sys, "_MEIPASS", "/fake/bundle", create=True):
        path = get_resource_path("credentials")
        assert path.startswith("/fake/bundle")

def test_get_credentials_dir():
    creds = get_credentials_dir()
    assert creds.endswith("credentials")

def test_get_app_data_dir():
    app_dir = get_app_data_dir()
    assert ".gijiroku-ai" in app_dir
```

- [ ] **Step 2: テスト実行 → 失敗を確認**

Run: `python -m pytest tests/test_resource_path.py -v`

- [ ] **Step 3: resource_path.py を実装**

```python
# utils/resource_path.py
import os
import sys

def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)

def get_credentials_dir():
    return get_resource_path("credentials")

def get_app_data_dir():
    app_dir = os.path.join(os.path.expanduser("~"), ".gijiroku-ai")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir
```

- [ ] **Step 4: テスト実行 → 全パス確認**

- [ ] **Step 5: コミット**

```bash
git add utils/resource_path.py tests/test_resource_path.py
git commit -m "feat: resource path utility for PyInstaller compatibility"
```

---

## Task 2: OAuth認証情報ディレクトリ + 開発者ガイド

**Files:**
- Create: `credentials/.gitkeep`
- Create: `credentials/README.md`

- [ ] **Step 1: credentials ディレクトリと開発者ガイドを作成**

```markdown
# OAuth認証情報の設定（開発者向け）

配布用の .exe をビルドする前に、以下のOAuth認証情報を設定してください。

## Google Drive

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成（例: 「議事録AI」）
3. 「APIとサービス」→「ライブラリ」→「Google Drive API」を有効化
4. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuthクライアントID」
5. アプリケーションの種類: 「デスクトップアプリ」
6. 作成後、JSONをダウンロード
7. ダウンロードしたファイルを `credentials/google_client_secrets.json` として保存

### OAuth同意画面の設定
- ユーザーの種類: 「外部」
- アプリ名: 「議事録AI」
- スコープ: `https://www.googleapis.com/auth/drive.file`
- テストユーザーに配布先のGmailアドレスを追加（本番公開前）

## OneDrive

1. [Azure Portal](https://portal.azure.com/) → 「Azure Active Directory」→「アプリの登録」
2. 「新規登録」
   - 名前: 「議事録AI」
   - サポートされるアカウントの種類: 「個人用Microsoftアカウント」
   - リダイレクトURI: 不要（デバイスコードフロー使用）
3. 登録後、「概要」ページの「アプリケーション (クライアント) ID」をコピー
4. `credentials/onedrive_config.json` を作成:

```json
{
  "client_id": "ここにクライアントIDを貼り付け"
}
```

## 確認

設定完了後、以下のファイルが存在することを確認:
- `credentials/google_client_secrets.json`
- `credentials/onedrive_config.json`
```

- [ ] **Step 2: .gitignore に認証情報ファイルを追加**

`.gitignore` を作成:

```
credentials/google_client_secrets.json
credentials/onedrive_config.json
__pycache__/
*.pyc
*.pyo
build/
dist/
*.spec
```

- [ ] **Step 3: コミット**

```bash
git add credentials/.gitkeep credentials/README.md .gitignore
git commit -m "docs: OAuth credentials setup guide for developers"
```

---

## Task 3: セットアップ画面にOAuth認証ボタンを追加

**Files:**
- Modify: `ui/setup.py`

- [ ] **Step 1: ui/setup.py を書き換え**

セットアップ画面を拡張して:
- Google Drive: 「Google Driveと連携」ボタン → クリックでブラウザが開いてOAuth認証
- OneDrive: 「OneDriveと連携」ボタン → デバイスコードフロー
- 認証状態を表示（✓ 連携済み / 未連携）
- ウィンドウサイズを500x550に拡大

```python
# ui/setup.py
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from recorder.audio import AudioRecorder
from utils.resource_path import get_credentials_dir, get_app_data_dir


class SetupWizard:
    def __init__(self, config, on_complete):
        self._config = config
        self._on_complete = on_complete
        self._root = None

    def run(self):
        self._root = tk.Tk()
        self._root.title("議事録AI - 初回セットアップ")
        self._root.geometry("500x550")
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
        tk.Label(
            frame,
            text="Google AI Studio (aistudio.google.com) から取得",
            font=("Meiryo UI", 8),
            fg="gray",
        ).pack(anchor="w")
        self._api_key_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._api_key_var, width=50, show="*").pack(
            anchor="w", pady=(0, 5)
        )

        # Step 2: Storage + Auth
        tk.Label(
            frame, text="2. クラウドストレージ連携", font=("Meiryo UI", 11, "bold")
        ).pack(anchor="w", pady=(10, 2))

        self._storage_var = tk.StringVar(value="google_drive")
        storage_frame = tk.Frame(frame)
        storage_frame.pack(anchor="w", fill="x")

        tk.Radiobutton(
            storage_frame,
            text="Google Drive",
            variable=self._storage_var,
            value="google_drive",
        ).pack(side="left")
        tk.Radiobutton(
            storage_frame,
            text="OneDrive",
            variable=self._storage_var,
            value="onedrive",
        ).pack(side="left", padx=10)

        auth_frame = tk.Frame(frame)
        auth_frame.pack(anchor="w", fill="x", pady=(5, 0))

        self._auth_btn = tk.Button(
            auth_frame,
            text="クラウドストレージと連携する",
            command=self._authenticate_storage,
        )
        self._auth_btn.pack(side="left")

        self._auth_status = tk.Label(
            auth_frame, text="未連携", font=("Meiryo UI", 9), fg="gray"
        )
        self._auth_status.pack(side="left", padx=10)

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
        self._check_existing_auth()
        self._root.mainloop()

    def _check_existing_auth(self):
        app_data = get_app_data_dir()
        gdrive_token = os.path.join(app_data, "gdrive_token.json")
        onedrive_cache = os.path.join(app_data, "onedrive_token_cache.json")
        if os.path.exists(gdrive_token) or os.path.exists(onedrive_cache):
            self._auth_status.config(text="✓ 連携済み", fg="green")

    def _authenticate_storage(self):
        provider = self._storage_var.get()
        self._auth_btn.config(state="disabled", text="認証中...")

        def auth_thread():
            try:
                if provider == "google_drive":
                    self._auth_google_drive()
                else:
                    self._auth_onedrive()
                self._root.after(
                    0,
                    lambda: self._auth_status.config(text="✓ 連携済み", fg="green"),
                )
            except Exception as e:
                self._root.after(
                    0,
                    lambda: messagebox.showerror("認証エラー", f"認証に失敗しました:\n{e}"),
                )
            finally:
                self._root.after(
                    0,
                    lambda: self._auth_btn.config(
                        state="normal", text="クラウドストレージと連携する"
                    ),
                )

        threading.Thread(target=auth_thread, daemon=True).start()

    def _auth_google_drive(self):
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials

        creds_dir = get_credentials_dir()
        secrets_path = os.path.join(creds_dir, "google_client_secrets.json")
        if not os.path.exists(secrets_path):
            raise FileNotFoundError(
                "google_client_secrets.json が見つかりません。\n"
                "credentials/README.md を参照してください。"
            )

        app_data = get_app_data_dir()
        token_path = os.path.join(app_data, "gdrive_token.json")

        scopes = ["https://www.googleapis.com/auth/drive.file"]
        flow = InstalledAppFlow.from_client_secrets_file(secrets_path, scopes)
        creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())

        self._config.set("google_drive_credentials", secrets_path)
        self._config.set("google_drive_token", token_path)

    def _auth_onedrive(self):
        import msal

        creds_dir = get_credentials_dir()
        config_path = os.path.join(creds_dir, "onedrive_config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                "onedrive_config.json が見つかりません。\n"
                "credentials/README.md を参照してください。"
            )

        with open(config_path, "r") as f:
            od_config = json.load(f)

        app_data = get_app_data_dir()
        cache_path = os.path.join(app_data, "onedrive_token_cache.json")

        cache = msal.SerializableTokenCache()
        app = msal.PublicClientApplication(
            od_config["client_id"],
            authority="https://login.microsoftonline.com/consumers",
            token_cache=cache,
        )

        flow = app.initiate_device_flow(scopes=["Files.ReadWrite"])
        self._root.after(
            0,
            lambda: messagebox.showinfo(
                "OneDrive認証",
                f"以下のURLをブラウザで開き、コードを入力してください:\n\n"
                f"URL: {flow['verification_uri']}\n"
                f"コード: {flow['user_code']}",
            ),
        )
        app.acquire_token_by_device_flow(flow)

        with open(cache_path, "w") as f:
            f.write(cache.serialize())

        self._config.set("onedrive_credentials", od_config["client_id"])
        self._config.set("onedrive_token_cache", cache_path)

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

- [ ] **Step 2: 全テスト実行**

Run: `python -m pytest tests/ --ignore=tests/test_ui.py -v`
Expected: All PASS

- [ ] **Step 3: コミット**

```bash
git add ui/setup.py
git commit -m "feat: add OAuth auth buttons to setup wizard"
```

---

## Task 4: Google Drive / OneDrive アップローダーのパス統合

**Files:**
- Modify: `uploader/google_drive.py`
- Modify: `uploader/onedrive.py`
- Modify: `main.py`

- [ ] **Step 1: google_drive.py のトークンパスを app_data_dir に統一**

`GoogleDriveUploader.__init__` のデフォルト token_path を `~/.gijiroku-ai/gdrive_token.json` に変更:

```python
def __init__(self, credentials_path, token_path=None):
    self._credentials_path = credentials_path
    if token_path is None:
        from utils.resource_path import get_app_data_dir
        token_path = os.path.join(get_app_data_dir(), "gdrive_token.json")
    self._token_path = token_path
    self._service = None
    self._root_folder_id = None
```

- [ ] **Step 2: onedrive.py のキャッシュパスを app_data_dir に統一**

`OneDriveUploader.__init__` のデフォルト token_cache_path を `~/.gijiroku-ai/onedrive_token_cache.json` に変更:

```python
def __init__(self, client_id, authority=None, token_cache_path=None):
    self._client_id = client_id
    self._authority = authority or "https://login.microsoftonline.com/consumers"
    if token_cache_path is None:
        from utils.resource_path import get_app_data_dir
        token_cache_path = os.path.join(get_app_data_dir(), "onedrive_token_cache.json")
    self._token_cache_path = token_cache_path
    self._access_token = None
```

- [ ] **Step 3: main.py の uploader_factory を credentials_dir ベースに更新**

`_build_components` 内の `uploader_factory` を変更:

```python
def uploader_factory():
    from utils.resource_path import get_credentials_dir
    provider = config.get("storage_provider")
    if provider == "google_drive":
        creds_path = config.get("google_drive_credentials")
        if not creds_path:
            creds_path = os.path.join(get_credentials_dir(), "google_client_secrets.json")
        uploader = GoogleDriveUploader(credentials_path=creds_path)
    else:
        client_id = config.get("onedrive_credentials")
        if not client_id:
            import json
            od_config_path = os.path.join(get_credentials_dir(), "onedrive_config.json")
            with open(od_config_path) as f:
                client_id = json.load(f)["client_id"]
        uploader = OneDriveUploader(client_id=client_id)
    uploader.authenticate()
    return uploader
```

- [ ] **Step 4: 既存テスト実行**

Run: `python -m pytest tests/ --ignore=tests/test_ui.py -v`
Expected: All PASS

- [ ] **Step 5: コミット**

```bash
git add uploader/google_drive.py uploader/onedrive.py main.py
git commit -m "feat: unify OAuth token paths to app data dir"
```

---

## Task 5: PyInstaller ビルド設定

**Files:**
- Create: `build.bat`
- Modify: `requirements.txt`

- [ ] **Step 1: requirements.txt に pyinstaller 追加**

末尾に追加:
```
pyinstaller>=6.0.0
```

- [ ] **Step 2: pyinstaller インストール**

Run: `pip install pyinstaller`

- [ ] **Step 3: build.bat を作成**

```bat
@echo off
echo ================================================
echo   議事録AI ビルドスクリプト
echo ================================================

REM FFmpegの場所を確認
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] FFmpegが見つかりません。PATHにFFmpegを追加してください。
    exit /b 1
)

REM FFmpegのパスを取得
for /f "delims=" %%i in ('where ffmpeg') do set FFMPEG_PATH=%%i
for %%i in ("%FFMPEG_PATH%") do set FFMPEG_DIR=%%~dpi

echo FFmpeg found: %FFMPEG_DIR%

REM PyInstallerでビルド
pyinstaller --noconfirm ^
    --name "GijirokuAI" ^
    --windowed ^
    --onedir ^
    --icon=NONE ^
    --add-data "credentials;credentials" ^
    --add-binary "%FFMPEG_DIR%ffmpeg.exe;." ^
    --add-binary "%FFMPEG_DIR%ffprobe.exe;." ^
    --hidden-import "pystray._win32" ^
    --hidden-import "plyer.platforms.win.notification" ^
    --hidden-import "google.auth.transport.requests" ^
    --hidden-import "win32gui" ^
    --hidden-import "win32api" ^
    --hidden-import "win32con" ^
    main.py

if %errorlevel% neq 0 (
    echo [ERROR] ビルドに失敗しました。
    exit /b 1
)

echo.
echo ================================================
echo   ビルド完了！
echo   出力先: dist\GijirokuAI\GijirokuAI.exe
echo ================================================
echo.
echo 配布する前に credentials/ フォルダに
echo OAuth認証情報を配置してください。
echo （credentials/README.md を参照）
```

- [ ] **Step 4: テストビルド実行**

Run: `build.bat`
Expected: `dist\GijirokuAI\GijirokuAI.exe` が生成される

- [ ] **Step 5: コミット**

```bash
git add build.bat requirements.txt
git commit -m "feat: PyInstaller build script for .exe distribution"
```

---

## 補足: 配布前チェックリスト（開発者向け）

1. `credentials/google_client_secrets.json` を配置
2. `credentials/onedrive_config.json` を配置（OneDrive対応する場合）
3. `build.bat` を実行
4. `dist/GijirokuAI/` フォルダをZIP圧縮して配布
5. エンドユーザーは GijirokuAI.exe をダブルクリック → セットアップ画面で設定
