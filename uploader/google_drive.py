import logging
import os


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from exceptions import AuthenticationError, UploadError
from uploader.base import BaseUploader
from utils.retry import retry

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveUploader(BaseUploader):
    def __init__(self, credentials_path, token_path=None):
        self._credentials_path = credentials_path
        if token_path is None:
            from utils.resource_path import get_app_data_dir

            token_path = os.path.join(get_app_data_dir(), "gdrive_token.json")
        self._token_path = token_path
        self._service = None
        self._root_folder_id = None

    def authenticate(self):
        creds = None
        if os.path.exists(self._token_path):
            try:
                from utils.crypto import read_and_decrypt
                import json as _json

                creds_data = _json.loads(read_and_decrypt(self._token_path))
                creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
            except (ValueError, Exception) as e:
                logger.warning("Token file corrupted, will re-authenticate: %s", e)
                os.remove(self._token_path)
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning("Token refresh failed, re-authenticating: %s", e)
                    if os.path.exists(self._token_path):
                        os.remove(self._token_path)
                    creds = None

            if not creds or not creds.valid:
                if not os.path.exists(self._credentials_path):
                    raise AuthenticationError(
                        f"認証情報ファイルが見つかりません: {self._credentials_path}"
                    )
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self._credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    raise AuthenticationError(f"Google Drive 認証失敗: {e}") from e

            from utils.crypto import encrypt_and_write

            encrypt_and_write(self._token_path, creds.to_json())

        self._service = build("drive", "v3", credentials=creds)
        self._ensure_root_folder()

    def _ensure_root_folder(self):
        results = retry(
            lambda: self._service.files()
            .list(
                q="name='議事録AI' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces="drive",
                fields="files(id)",
            )
            .execute(),
            max_retries=3,
        )
        files = results.get("files", [])
        if files:
            self._root_folder_id = files[0]["id"]
        else:
            self._root_folder_id = self.create_folder("議事録AI")

    def create_folder(self, name, parent_folder_id=None):
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_folder_id:
            metadata["parents"] = [parent_folder_id]

        folder = retry(
            lambda: self._service.files()
            .create(body=metadata, fields="id")
            .execute(),
            max_retries=3,
        )
        return folder["id"]

    def upload_file(self, file_path, parent_folder_id):
        if not self._service:
            raise UploadError("authenticate() を先に呼び出してください")

        metadata = {
            "name": os.path.basename(file_path),
            "parents": [parent_folder_id],
        }
        media = MediaFileUpload(file_path, resumable=True)

        request = self._service.files().create(
            body=metadata, media_body=media, fields="id"
        )
        response = None
        while response is None:
            status, response = retry(
                lambda: request.next_chunk(),
                max_retries=3,
                retryable_exceptions=(Exception,),
            )
            if status:
                logger.info(
                    "Upload %s: %d%%",
                    os.path.basename(file_path),
                    int(status.progress() * 100),
                )

        logger.info("Uploaded: %s → %s", file_path, response["id"])
        return response["id"]

    def upload_session(self, session_dir, meeting_name):
        if not self._service:
            raise UploadError("authenticate() を先に呼び出してください")

        parent = self._root_folder_id
        folder_id = self.create_folder(meeting_name, parent)
        failed = []
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            if os.path.isfile(filepath):
                try:
                    self.upload_file(filepath, folder_id)
                except Exception as e:
                    logger.error("Failed to upload %s: %s", filename, e)
                    failed.append(filename)
        if failed:
            raise UploadError(
                f"以下のファイルのアップロードに失敗: {', '.join(failed)}"
            )
        return folder_id
