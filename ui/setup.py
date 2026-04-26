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
