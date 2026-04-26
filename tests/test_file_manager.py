import os
import tempfile
import pytest
from utils.file_manager import FileManager

@pytest.fixture
def fm(tmp_path):
    return FileManager(str(tmp_path))

def test_create_session_dir(fm):
    session_dir = fm.create_session("テスト会議")
    assert os.path.isdir(session_dir)
    assert "テスト会議" in os.path.basename(session_dir)

def test_session_dir_has_date_prefix(fm):
    session_dir = fm.create_session("定例会議")
    dirname = os.path.basename(session_dir)
    assert dirname[4] == "-"
    assert dirname[7] == "-"
    assert dirname[10] == "_"

def test_list_segments_empty(fm):
    session_dir = fm.create_session("test")
    segments = fm.list_segments(session_dir, ".wav")
    assert segments == []

def test_list_segments_sorted(fm):
    session_dir = fm.create_session("test")
    for name in ["recording_002.wav", "recording_000.wav", "recording_001.wav"]:
        open(os.path.join(session_dir, name), "w").close()
    segments = fm.list_segments(session_dir, ".wav")
    assert len(segments) == 3
    assert "recording_000.wav" in segments[0]
    assert "recording_002.wav" in segments[2]

def test_segment_offset(fm):
    assert fm.segment_offset(0, 1800) == 0
    assert fm.segment_offset(1, 1800) == 1800
    assert fm.segment_offset(2, 1800) == 3600

def test_format_timestamp():
    from utils.file_manager import FileManager
    assert FileManager.format_timestamp(0) == "00:00"
    assert FileManager.format_timestamp(65) == "01:05"
    assert FileManager.format_timestamp(3661) == "1:01:01"
