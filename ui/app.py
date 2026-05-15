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
