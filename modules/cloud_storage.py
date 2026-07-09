"""JARVIS v6.0 — Google Drive and OneDrive cloud storage."""
from __future__ import annotations
import os
from pathlib import Path

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from google.oauth2.credentials import Credentials
    _GDRIVE = True
except ImportError:
    _GDRIVE = False

try:
    import requests; _REQUESTS = True
except ImportError:
    _REQUESTS = False


class GoogleDrive:
    def __init__(self):
        self._svc = None
        if not _GDRIVE:
            return
        creds_path = os.getenv("GOOGLE_CREDENTIALS_JSON","")
        if not creds_path or not Path(creds_path).exists():
            return
        try:
            creds = Credentials.from_authorized_user_file(creds_path)
            self._svc = build("drive","v3",credentials=creds)
        except Exception:
            pass

    def _check(self) -> str | None:
        if not _GDRIVE: return "google-api-python-client not installed."
        if not self._svc: return "GOOGLE_CREDENTIALS_JSON not configured."
        return None

    def list_files(self, folder_id: str = "root", limit: int = 20) -> list[dict]:
        err = self._check()
        if err: return [{"error": err}]
        try:
            q = f"'{folder_id}' in parents and trashed=false"
            r = self._svc.files().list(q=q, pageSize=limit,
                fields="files(id,name,mimeType,size)").execute()
            return r.get("files",[])
        except Exception as e: return [{"error": str(e)}]

    def download(self, file_id: str, dest: str) -> str:
        err = self._check()
        if err: return err
        try:
            import io
            req = self._svc.files().get_media(fileId=file_id)
            buf = io.BytesIO()
            dl = MediaIoBaseDownload(buf, req)
            done = False
            while not done: _, done = dl.next_chunk()
            Path(dest).write_bytes(buf.getvalue())
            return f"Downloaded to {dest}"
        except Exception as e: return f"Download error: {e}"

    def upload(self, local_path: str, folder_id: str = "root",
               confirmed: bool = False) -> str:
        err = self._check()
        if err: return err
        try:
            name = Path(local_path).name
            meta = {"name": name, "parents": [folder_id]}
            media = MediaFileUpload(local_path)
            f = self._svc.files().create(body=meta, media_body=media,
                                          fields="id").execute()
            return f"Uploaded '{name}' → Drive ID {f['id']}"
        except Exception as e: return f"Upload error: {e}"

    def get_quota(self) -> str:
        err = self._check()
        if err: return err
        try:
            r = self._svc.about().get(fields="storageQuota").execute()
            q = r.get("storageQuota",{})
            used = int(q.get("usage",0))
            total = int(q.get("limit",0))
            return (f"Drive: {used/1e9:.1f}GB used / "
                    f"{total/1e9:.1f}GB total")
        except Exception as e: return f"Quota error: {e}"


def search_drive(query: str, limit: int = 10) -> list[dict]:
    gd = GoogleDrive()
    err = gd._check()
    if err: return [{"error": err}]
    try:
        r = gd._svc.files().list(
            q=f"name contains '{query}' and trashed=false",
            pageSize=limit, fields="files(id,name,mimeType)").execute()
        return r.get("files",[])
    except Exception as e: return [{"error": str(e)}]
