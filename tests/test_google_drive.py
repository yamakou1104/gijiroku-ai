import os
import pytest
from unittest.mock import patch, MagicMock
from uploader.base import BaseUploader
from uploader.google_drive import GoogleDriveUploader

def test_base_uploader_interface():
    assert hasattr(BaseUploader, "authenticate")
    assert hasattr(BaseUploader, "upload_file")
    assert hasattr(BaseUploader, "create_folder")

@pytest.fixture
def uploader():
    with patch("uploader.google_drive.build"):
        up = GoogleDriveUploader.__new__(GoogleDriveUploader)
        up._service = MagicMock()
        up._root_folder_id = None
        return up

def test_create_folder(uploader):
    mock_create = uploader._service.files.return_value.create
    mock_create.return_value.execute.return_value = {"id": "folder-123"}
    folder_id = uploader.create_folder("テスト会議")
    assert folder_id == "folder-123"

def test_upload_file(uploader, tmp_path):
    test_file = tmp_path / "test.wav"
    test_file.write_bytes(b"\x00" * 100)

    mock_create = uploader._service.files.return_value.create
    mock_create.return_value.execute.return_value = {"id": "file-456"}
    file_id = uploader.upload_file(str(test_file), "parent-123")
    assert file_id == "file-456"

def test_upload_session_calls_upload_for_each_file(uploader, tmp_path):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    (session_dir / "recording_000.wav").write_bytes(b"\x00" * 50)
    (session_dir / "minutes.md").write_text("# Test", encoding="utf-8")

    mock_create = uploader._service.files.return_value.create
    mock_create.return_value.execute.return_value = {"id": "id"}

    uploader.create_folder = MagicMock(return_value="folder-id")
    uploader.upload_file = MagicMock(return_value="file-id")

    uploader.upload_session(str(session_dir), "テスト会議")
    assert uploader.upload_file.call_count == 2
