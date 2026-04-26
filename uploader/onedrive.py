import os
import json
import requests
import msal
from uploader.base import BaseUploader

GRAPH_URL = "https://graph.microsoft.com/v1.0"
SCOPES = ["Files.ReadWrite"]

class OneDriveUploader(BaseUploader):
    def __init__(self, client_id, authority=None, token_cache_path=None):
        self._client_id = client_id
        self._authority = authority or "https://login.microsoftonline.com/consumers"
        self._token_cache_path = token_cache_path
        self._access_token = None

    def authenticate(self):
        cache = msal.SerializableTokenCache()
        if self._token_cache_path and os.path.exists(self._token_cache_path):
            cache.deserialize(open(self._token_cache_path).read())

        app = msal.PublicClientApplication(
            self._client_id,
            authority=self._authority,
            token_cache=cache,
        )

        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
        else:
            result = None

        if not result:
            flow = app.initiate_device_flow(scopes=SCOPES)
            print(flow["message"])
            result = app.acquire_token_by_device_flow(flow)

        self._access_token = result["access_token"]

        if self._token_cache_path and cache.has_state_changed:
            with open(self._token_cache_path, "w") as f:
                f.write(cache.serialize())

    def _headers(self):
        return {"Authorization": f"Bearer {self._access_token}"}

    def create_folder(self, name, parent_path=None):
        parent = parent_path or "/drive/root:"
        url = f"{GRAPH_URL}/me{parent}:/children"
        body = {
            "name": name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "rename",
        }
        resp = requests.post(url, headers=self._headers(), json=body)
        resp.raise_for_status()
        return resp.json()["id"]

    def upload_file(self, file_path, parent_path):
        filename = os.path.basename(file_path)
        url = f"{GRAPH_URL}/me/drive/root:{parent_path}/{filename}:/content"
        with open(file_path, "rb") as f:
            resp = requests.put(url, headers=self._headers(), data=f)
        resp.raise_for_status()
        return resp.json()["id"]

    def upload_session(self, session_dir, meeting_name):
        root_path = "/drive/root:/議事録AI"
        self.create_folder("議事録AI")
        folder_path = f"/議事録AI/{meeting_name}"
        self.create_folder(meeting_name, root_path)
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            if os.path.isfile(filepath):
                self.upload_file(filepath, folder_path)
