import os
from datetime import datetime

class FileManager:
    def __init__(self, base_dir):
        self._base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def create_session(self, meeting_name):
        date_str = datetime.now().strftime("%Y-%m-%d")
        dir_name = f"{date_str}_{meeting_name}"
        session_dir = os.path.join(self._base_dir, dir_name)
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def list_segments(self, session_dir, extension):
        files = [
            os.path.join(session_dir, f)
            for f in sorted(os.listdir(session_dir))
            if f.endswith(extension)
        ]
        return files

    def segment_offset(self, index, segment_duration):
        return index * segment_duration

    @staticmethod
    def format_timestamp(seconds):
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
