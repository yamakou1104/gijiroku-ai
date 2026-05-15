import logging
import threading
import time
from enum import Enum

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
        import pystray

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
        import subprocess
        import sys
        subprocess.Popen([sys.executable, "-c",
            "from config import Config; from ui.setup import SetupWizard; "
            "SetupWizard(Config(), on_complete=lambda: None).run()"
        ])

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
