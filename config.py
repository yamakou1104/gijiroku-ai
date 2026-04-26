# config.py
import json
import os

DEFAULTS = {
    "storage_provider": "google_drive",
    "gemini_api_key": "",
    "mic_device": "",
    "segment_duration": 1800,
    "output_dir": "",
    "google_drive_credentials": "",
    "onedrive_credentials": "",
}

class Config:
    def __init__(self, path=None):
        if path is None:
            app_dir = os.path.join(os.path.expanduser("~"), ".gijiroku-ai")
            os.makedirs(app_dir, exist_ok=True)
            path = os.path.join(app_dir, "config.json")
        self._path = path
        self._data = dict(DEFAULTS)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._data.update(json.load(f))
        else:
            self._save()

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        self._data[key] = value
        self._save()

    def _save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
