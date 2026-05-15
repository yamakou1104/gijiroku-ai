import json
import logging
import os
import shutil
import tempfile
import threading

logger = logging.getLogger(__name__)

DEFAULTS = {
    "storage_provider": "google_drive",
    "gemini_api_key": "",
    "mic_device": "",
    "segment_duration": 1800,
    "output_dir": "",
    "google_drive_credentials": "",
    "onedrive_credentials": "",
    "setup_complete": False,
}


class Config:
    def __init__(self, path=None):
        if path is None:
            app_dir = os.path.join(os.path.expanduser("~"), ".gijiroku-ai")
            os.makedirs(app_dir, exist_ok=True)
            path = os.path.join(app_dir, "config.json")
        self._path = path
        self._lock = threading.Lock()
        self._data = dict(DEFAULTS)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._data.update(json.load(f))
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Config file corrupted, backing up: %s", e)
                backup = path + ".bak"
                shutil.copy2(path, backup)
                self._save()
        else:
            self._save()

    def get(self, key):
        with self._lock:
            return self._data.get(key)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value
            self._save()

    def _save(self):
        dir_name = os.path.dirname(self._path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._path)
        except BaseException:
            os.unlink(tmp_path)
            raise
