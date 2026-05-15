# tests/test_config.py
import os
import json
import tempfile
import pytest
from config import Config

@pytest.fixture
def config_path(tmp_path):
    return str(tmp_path / "config.json")

def test_default_config_created(config_path):
    cfg = Config(config_path)
    assert os.path.exists(config_path)

def test_default_values(config_path):
    cfg = Config(config_path)
    assert cfg.get("storage_provider") == "google_drive"
    assert cfg.get("gemini_api_key") == ""
    assert cfg.get("mic_device") == ""
    assert cfg.get("segment_duration") == 1800

def test_set_and_get(config_path):
    cfg = Config(config_path)
    cfg.set("gemini_api_key", "test-key-123")
    assert cfg.get("gemini_api_key") == "test-key-123"

def test_persistence(config_path):
    cfg1 = Config(config_path)
    cfg1.set("mic_device", "My Microphone")
    cfg2 = Config(config_path)
    assert cfg2.get("mic_device") == "My Microphone"

def test_get_unknown_key_returns_none(config_path):
    cfg = Config(config_path)
    assert cfg.get("nonexistent") is None


def test_load_corrupted_json(config_path):
    with open(config_path, "w") as f:
        f.write("{invalid json")
    cfg = Config(config_path)
    assert cfg.get("storage_provider") == "google_drive"
    assert os.path.exists(config_path + ".bak")


def test_thread_safe_set(config_path):
    import threading
    cfg = Config(config_path)
    errors = []

    def writer(key, value):
        try:
            for _ in range(50):
                cfg.set(key, value)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=writer, args=("key1", "val1")),
        threading.Thread(target=writer, args=("key2", "val2")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
