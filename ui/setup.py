# ui/setup.py
import os
import json
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from recorder.audio import AudioRecorder
from utils.resource_path import get_credentials_dir, get_app_data_dir

_FONT_FAMILY = "Hiragino Sans" if sys.platform == "darwin" else _FONT_FAMILY


class SetupWizard:
    def __init__(self, config, on_complete):
        self._config = config
        self._on_complete = on_complete
        self._root = None
        self._device_map = {}
        self._frame = None

    def run(self):
        self._root = tk.Tk()
        self._root.title("議事録AI - 初回セットアップ")
        self._root.geometry("500x550")
        self._root.resizable(False, False)

        tk.Label(
            self._root, text="初回セットアップ", font=(_FONT_FAMILY, 16, "bold")
        ).pack(pady=15)

        frame = tk.Frame(self._root, padx=30)
        frame.pack(fill="both", expand=True)
        self._frame = frame

        # FFmpeg check
        import shutil
        ffmpeg_frame = tk.Frame(frame)
        ffmpeg_frame.pack(anchor="w", fill="x", pady=(5, 10))

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

        # Step 1: Gemini API key
        tk.Label(frame, text="1. Gemini APIキー", font=(_FONT_FAMILY, 11, "bold")).pack(
            anchor="w", pady=(10, 2)
        )
        tk.Label(
            frame,
            text="Google AI Studio (aistudio.google.com) から取得",
            font=(_FONT_FAMILY, 8),
            fg="gray",
        ).pack(anchor="w")
        self._api_key_var = tk.StringVar()
        tk.Entry(frame, textvariable=self._api_key_var, width=50, show="*").pack(
            anchor="w", pady=(0, 5)
        )

        # Step 2: Storage + Auth
        tk.Label(
            frame, text="2. クラウドストレージ連携", font=(_FONT_FAMILY, 11, "bold")
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
            auth_frame, text="未連携", font=(_FONT_FAMILY, 9), fg="gray"
        )
        self._auth_status.pack(side="left", padx=10)

        # Step 3: Microphone
        tk.Label(frame, text="3. マイクデバイス", font=(_FONT_FAMILY, 11, "bold")).pack(
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
            font=(_FONT_FAMILY, 12),
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

            if sys.platform == "darwin" and display_names:
                has_blackhole = any("blackhole" in n.lower() for n in display_names)
                if not has_blackhole:
                    tk.Label(
                        self._frame,
                        text="ヒント: オンラインモードにはBlackHoleが必要です\n"
                             "  brew install blackhole-2ch",
                        font=(_FONT_FAMILY, 8),
                        fg="orange",
                        justify="left",
                    ).pack(anchor="w", pady=(2, 0))
        except Exception:
            self._device_map = {}
            self._mic_combo["values"] = ["(デバイスを検出できません)"]

    def _save(self):
        import shutil
        if not shutil.which("ffmpeg"):
            messagebox.showwarning(
                "FFmpeg未検出",
                "FFmpegがインストールされていません。\n"
                + ("brew install ffmpeg を実行してください。" if sys.platform == "darwin"
                   else "FFmpegをダウンロードしてPATHに追加してください。"),
            )
            return

        api_key = self._api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("入力エラー", "Gemini APIキーを入力してください。")
            return

        mic_display = self._mic_var.get()
        if not mic_display or mic_display.startswith("("):
            messagebox.showwarning("入力エラー", "マイクデバイスを選択してください。")
            return

        mic_value = self._device_map.get(mic_display, mic_display)
        self._config.set("gemini_api_key", api_key)
        self._config.set("storage_provider", self._storage_var.get())
        self._config.set("mic_device", mic_value)
        self._config.set("setup_complete", True)

        self._root.destroy()
        self._on_complete()
