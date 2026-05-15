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


def test_upload_large_file_uses_session(tmp_path):
    """Files > 4MB should use session upload."""
    with patch("uploader.onedrive.msal"), \
         patch("uploader.onedrive.requests") as mock_requests:
        from uploader.onedrive import OneDriveUploader, SIMPLE_UPLOAD_LIMIT

        up = OneDriveUploader.__new__(OneDriveUploader)
        up._access_token = "test-token"
        up._token_cache_path = None

        large_file = tmp_path / "large.wav"
        large_file.write_bytes(b"\x00" * (SIMPLE_UPLOAD_LIMIT + 1))

        # Mock session creation
        mock_create_resp = MagicMock()
        mock_create_resp.status_code = 200
        mock_create_resp.json.return_value = {"uploadUrl": "https://upload.example.com/session"}
        mock_create_resp.raise_for_status = MagicMock()

        # Mock chunk upload
        mock_chunk_resp = MagicMock()
        mock_chunk_resp.status_code = 201
        mock_chunk_resp.json.return_value = {"id": "file-id"}

        mock_requests.post.return_value = mock_create_resp
        mock_requests.put.return_value = mock_chunk_resp

        result = up.upload_file(str(large_file), "/test")
        # Should have called POST to create session
        mock_requests.post.assert_called_once()
        # Should have called PUT for chunks
        assert mock_requests.put.call_count >= 1


def test_upload_session_416_invalid_next_range():
    """Invalid nextExpectedRanges format raises UploadError."""
    from exceptions import UploadError

    up = OneDriveUploader.__new__(OneDriveUploader)
    up._access_token = "test-token"
    up._token_cache_path = None

    with patch("uploader.onedrive.requests") as mock_requests, \
         patch("uploader.onedrive.retry") as mock_retry:

        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {"uploadUrl": "https://upload.example.com/s"}
        create_resp.raise_for_status = MagicMock()
        mock_requests.post.return_value = create_resp

        chunk_resp = MagicMock()
        chunk_resp.status_code = 416
        mock_retry.return_value = chunk_resp

        status_resp = MagicMock()
        status_resp.status_code = 200
        status_resp.json.return_value = {"nextExpectedRanges": ["not-a-number"]}
        mock_requests.get.return_value = status_resp

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"\x00" * (5 * 1024 * 1024))
            large_path = f.name
        try:
            with pytest.raises(UploadError, match="不正なnextExpectedRanges"):
                up.upload_file(large_path, "/test")
        finally:
            os.unlink(large_path)


def test_upload_session_416_offset_exceeds_filesize():
    """nextExpectedRanges offset >= file_size raises UploadError."""
    from exceptions import UploadError

    up = OneDriveUploader.__new__(OneDriveUploader)
    up._access_token = "test-token"
    up._token_cache_path = None

    with patch("uploader.onedrive.requests") as mock_requests, \
         patch("uploader.onedrive.retry") as mock_retry:

        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {"uploadUrl": "https://upload.example.com/s"}
        create_resp.raise_for_status = MagicMock()
        mock_requests.post.return_value = create_resp

        chunk_resp = MagicMock()
        chunk_resp.status_code = 416
        mock_retry.return_value = chunk_resp

        status_resp = MagicMock()
        status_resp.status_code = 200
        status_resp.json.return_value = {"nextExpectedRanges": ["99999999-"]}
        mock_requests.get.return_value = status_resp

        import tempfile
        file_size = 5 * 1024 * 1024
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"\x00" * file_size)
            large_path = f.name
        try:
            with pytest.raises(UploadError, match="チャンクアップロード失敗"):
                up.upload_file(large_path, "/test")
        finally:
            os.unlink(large_path)


def test_upload_session_416_negative_offset():
    """Negative nextExpectedRanges offset (e.g. '-5-100') fails parsing and raises UploadError."""
    from exceptions import UploadError

    up = OneDriveUploader.__new__(OneDriveUploader)
    up._access_token = "test-token"
    up._token_cache_path = None

    with patch("uploader.onedrive.requests") as mock_requests, \
         patch("uploader.onedrive.retry") as mock_retry:

        create_resp = MagicMock()
        create_resp.status_code = 200
        create_resp.json.return_value = {"uploadUrl": "https://upload.example.com/s"}
        create_resp.raise_for_status = MagicMock()
        mock_requests.post.return_value = create_resp

        chunk_resp = MagicMock()
        chunk_resp.status_code = 416
        mock_retry.return_value = chunk_resp

        status_resp = MagicMock()
        status_resp.status_code = 200
        status_resp.json.return_value = {"nextExpectedRanges": ["-5-100"]}
        mock_requests.get.return_value = status_resp

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"\x00" * (5 * 1024 * 1024))
            large_path = f.name
        try:
            with pytest.raises(UploadError, match="不正なnextExpectedRanges"):
                up.upload_file(large_path, "/test")
        finally:
            os.unlink(large_path)
