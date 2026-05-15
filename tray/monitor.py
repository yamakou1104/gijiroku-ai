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
