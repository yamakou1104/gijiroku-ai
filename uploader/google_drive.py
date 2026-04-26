import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from uploader.base import BaseUploader

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
            creds = Credentials.from_authorized_user_file(self._token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self._token_path, "w") as f:
                f.write(creds.to_json())
        self._service = build("drive", "v3", credentials=creds)
        self._ensure_root_folder()

    def _ensure_root_folder(self):
        results = (
            self._service.files()
            .list(
                q="name='議事録AI' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces="drive",
                fields="files(id)",
            )
            .execute()
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
        folder = self._service.files().create(body=metadata, fields="id").execute()
        return folder["id"]

    def upload_file(self, file_path, parent_folder_id):
        metadata = {
            "name": os.path.basename(file_path),
            "parents": [parent_folder_id],
        }
        media = MediaFileUpload(file_path, resumable=True)
        result = (
            self._service.files()
            .create(body=metadata, media_body=media, fields="id")
            .execute()
        )
        return result["id"]

    def upload_session(self, session_dir, meeting_name):
        parent = self._root_folder_id
        folder_id = self.create_folder(meeting_name, parent)
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            if os.path.isfile(filepath):
                self.upload_file(filepath, folder_id)
        return folder_id
