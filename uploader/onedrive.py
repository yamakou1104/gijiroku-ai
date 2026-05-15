import logging
import os

from urllib.parse import quote

import msal
import requests

from exceptions import AuthenticationError, UploadError
from uploader.base import BaseUploader
from utils.retry import retry

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.microsoft.com/v1.0"
SCOPES = ["Files.ReadWrite"]
SIMPLE_UPLOAD_LIMIT = 4 * 1024 * 1024
CHUNK_SIZE = 3276800


class OneDriveUploader(BaseUploader):
    def __init__(self, client_id, authority=None, token_cache_path=None):
        self._client_id = client_id
        self._authority = authority or "https://login.microsoftonline.com/consumers"
        if token_cache_path is None:
            from utils.resource_path import get_app_data_dir

            token_cache_path = os.path.join(
                get_app_data_dir(), "onedrive_token_cache.json"
            )
        self._token_cache_path = token_cache_path
        self._access_token = None

    def authenticate(self):
        cache = msal.SerializableTokenCache()
        if self._token_cache_path and os.path.exists(self._token_cache_path):
            try:
                from utils.crypto import read_and_decrypt

                cache.deserialize(read_and_decrypt(self._token_cache_path))
            except Exception as e:
                logger.warning("Token cache corrupted: %s", e)

        app = msal.PublicClientApplication(
            self._client_id,
            authority=self._authority,
            token_cache=cache,
        )

        accounts = app.get_accounts()
        result = None
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])

        if not result:
            flow = app.initiate_device_flow(scopes=SCOPES)
            if "user_code" not in flow:
                raise AuthenticationError(
                    f"デバイスフロー開始エラー: {flow.get('error_description', '不明')}"
                )
            print(flow["message"])
            result = app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            raise AuthenticationError(
                f"認証失敗: {result.get('error_description', '不明')}"
            )

        self._access_token = result["access_token"]

        if self._token_cache_path and cache.has_state_changed:
            from utils.crypto import encrypt_and_write

            os.makedirs(os.path.dirname(self._token_cache_path), exist_ok=True)
            encrypt_and_write(self._token_cache_path, cache.serialize())

    def _headers(self):
        return {"Authorization": f"Bearer {self._access_token}"}

    def create_folder(self, name, parent_path=None):
        if parent_path:
            url = f"{GRAPH_URL}/me/drive/root:{quote(parent_path, safe='/')}:/children"
        else:
            url = f"{GRAPH_URL}/me/drive/root/children"
        body = {
            "name": name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename",
        }
        resp = requests.post(
            url, headers=self._headers(), json=body, timeout=(10, 30)
        )
        resp.raise_for_status()
        return resp.json()["id"]

    def upload_file(self, file_path, parent_path):
        file_size = os.path.getsize(file_path)
        if file_size <= SIMPLE_UPLOAD_LIMIT:
            return self._upload_simple(file_path, parent_path)
        return self._upload_session(file_path, parent_path)

    def _upload_simple(self, file_path, parent_path):
        filename = os.path.basename(file_path)
        url = (
            f"{GRAPH_URL}/me/drive/root:"
            f"{quote(parent_path, safe='/')}/{quote(filename)}:/content"
        )
        with open(file_path, "rb") as f:
            resp = requests.put(
                url, headers=self._headers(), data=f, timeout=(10, 300)
            )
        resp.raise_for_status()
        return resp.json()["id"]

    def _upload_session(self, file_path, parent_path):
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        create_url = (
            f"{GRAPH_URL}/me/drive/root:"
            f"{quote(parent_path, safe='/')}/{quote(filename)}:/createUploadSession"
        )
        body = {
            "item": {
                "@microsoft.graph.conflictBehavior": "rename",
                "name": filename,
            }
        }
        resp = requests.post(
            create_url, headers=self._headers(), json=body, timeout=(10, 30)
        )
        resp.raise_for_status()
        upload_url = resp.json()["uploadUrl"]

        with open(file_path, "rb") as f:
            offset = 0
            while offset < file_size:
                chunk_end = min(offset + CHUNK_SIZE, file_size) - 1
                chunk_data = f.read(CHUNK_SIZE)
                headers = {
                    "Content-Range": f"bytes {offset}-{chunk_end}/{file_size}",
                    "Content-Length": str(len(chunk_data)),
                }

                chunk_resp = retry(
                    lambda h=headers, d=chunk_data: requests.put(
                        upload_url,
                        headers=h,
                        data=d,
                        timeout=(10, 300),
                    ),
                    max_retries=5,
                    initial_delay=2,
                    retryable_exceptions=(
                        requests.exceptions.ConnectionError,
                        requests.exceptions.Timeout,
                    ),
                )

                if chunk_resp.status_code == 404:
                    raise UploadError(
                        f"アップロードセッションが期限切れです。再試行してください。"
                    )
                if chunk_resp.status_code == 416:
                    logger.warning("416 Range Not Satisfiable, querying session status")
                    status_resp = requests.get(upload_url, timeout=(10, 30))
                    if status_resp.status_code == 200:
                        next_ranges = status_resp.json().get("nextExpectedRanges", [])
                        if next_ranges:
                            try:
                                next_start = int(next_ranges[0].split("-")[0])
                            except (ValueError, IndexError):
                                raise UploadError("不正なnextExpectedRanges応答")
                            if 0 <= next_start < file_size:
                                f.seek(next_start)
                                offset = next_start
                                logger.info("Resuming upload from byte %d", next_start)
                                continue
                    raise UploadError(
                        f"チャンクアップロード失敗: {chunk_resp.status_code}"
                    )
                if chunk_resp.status_code not in (200, 201, 202):
                    raise UploadError(
                        f"チャンクアップロード失敗: {chunk_resp.status_code} {chunk_resp.text}"
                    )

                progress = int((chunk_end + 1) / file_size * 100)
                logger.info("Upload %s: %d%%", filename, progress)
                offset += CHUNK_SIZE

        return chunk_resp.json().get("id", "")

    def upload_session(self, session_dir, meeting_name):
        root_path = "/議事録AI"
        self.create_folder("議事録AI")
        folder_path = f"/議事録AI/{meeting_name}"
        self.create_folder(meeting_name, root_path)
        failed = []
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            if os.path.isfile(filepath):
                try:
                    self.upload_file(filepath, folder_path)
                except Exception as e:
                    logger.error("Failed to upload %s: %s", filename, e)
                    failed.append(filename)
        if failed:
            raise UploadError(
                f"以下のファイルのアップロードに失敗: {', '.join(failed)}"
            )
        return folder_path
