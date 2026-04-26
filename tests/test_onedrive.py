import os
import pytest
from unittest.mock import patch, MagicMock
from uploader.onedrive import OneDriveUploader

@pytest.fixture
def uploader():
    up = OneDriveUploader.__new__(OneDriveUploader)
    up._access_token = "test-token"
    return up

@patch("uploader.onedrive.requests.put")
def test_upload_file(mock_put, uploader, tmp_path):
    test_file = tmp_path / "test.wav"
    test_file.write_bytes(b"\x00" * 100)

    mock_put.return_value = MagicMock(status_code=201, json=lambda: {"id": "file-123"})
    file_id = uploader.upload_file(str(test_file), "/議事録AI/テスト")
    assert file_id == "file-123"

@patch("uploader.onedrive.requests.post")
def test_create_folder(mock_post, uploader):
    mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": "folder-456"})
    folder_id = uploader.create_folder("テスト会議", "/議事録AI")
    assert folder_id == "folder-456"

@patch("uploader.onedrive.requests.put")
@patch("uploader.onedrive.requests.post")
def test_upload_session(mock_post, mock_put, uploader, tmp_path):
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    (session_dir / "recording_000.wav").write_bytes(b"\x00" * 50)

    mock_post.return_value = MagicMock(status_code=201, json=lambda: {"id": "f-id"})
    mock_put.return_value = MagicMock(status_code=201, json=lambda: {"id": "id"})

    uploader.create_folder = MagicMock(return_value="folder-id")
    uploader.upload_file = MagicMock(return_value="file-id")

    uploader.upload_session(str(session_dir), "テスト会議")
    assert uploader.upload_file.call_count == 1
