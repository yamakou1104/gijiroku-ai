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
        result = self._recorder_factory(mode)
        if isinstance(result, tuple):
            self._recorder, self._session_dir = result
        else:
            self._recorder = result
            self._session_dir = getattr(result, "session_dir", None)
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
