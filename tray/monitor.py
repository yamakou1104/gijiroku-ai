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
