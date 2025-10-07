from __future__ import annotations
from typing import Optional, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io
import logging


class DriveClient:
    """Thin wrapper around Google Drive API operations used by the app."""

    def __init__(self, credentials):
        self.service = build("drive", "v3", credentials=credentials)

    def latest_file(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """Return the newest file metadata from a folder, or None if empty."""
        try:
            query = f"'{folder_id}' in parents"
            results = (
                self.service.files()
                .list(
                    q=query,
                    orderBy="createdTime desc",
                    fields="files(id, name, createdTime, mimeType)",
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                )
                .execute()
            )
            files = results.get("files", [])
            if not files:
                logging.error("No files found in Drive folder")
                return None
            latest = files[0]
            logging.info(
                "Latest Drive file: %s (ID: %s)", latest.get("name"), latest.get("id")
            )
            return latest
        except Exception as e:
            logging.error("Drive list error: %s", e)
            return None

    def download_bytes(self, file_id: str) -> Optional[bytes]:
        """Download a Drive file content into memory and return bytes."""
        try:
            # First, get metadata to decide whether to export or download
            meta = self.service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
            mime = meta.get("mimeType", "")

            if mime == "application/vnd.google-apps.spreadsheet":
                # Export Google Sheet to XLSX
                request = self.service.files().export(fileId=file_id, mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                data = request.execute()  # returns bytes
                return data

            # Default: binary download
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            return fh.read()
        except Exception as e:
            logging.error("Drive download error: %s", e)
            return None

    def _find_files_by_name_in_folder(self, folder_id: str, name: str) -> list[dict[str, Any]]:
        try:
            q = (
                f"name = '{name.replace("'", "\\'")}' and '{folder_id}' in parents and trashed = false"
            )
            results = (
                self.service.files()
                .list(q=q, fields="files(id, name)", includeItemsFromAllDrives=True, supportsAllDrives=True)
                .execute()
            )
            return results.get("files", [])
        except Exception as e:
            logging.error("Drive search error: %s", e)
            return []

    def upload_bytes(self, folder_id: str, name: str, data: bytes, mime_type: str = "text/csv", replace: bool = True) -> Optional[str]:
        """Upload a new file to Drive. If replace=True, remove existing files with the same name in the folder.

        Returns the new file ID on success, None on failure.
        """
        try:
            if replace:
                existing = self._find_files_by_name_in_folder(folder_id, name)
                for f in existing:
                    try:
                        self.service.files().delete(fileId=f["id"]).execute()
                        logging.info("Deleted existing file in folder: %s (%s)", f.get("name"), f.get("id"))
                    except Exception as de:
                        logging.warning("Failed deleting existing file %s: %s", f.get("id"), de)

            media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
            body = {"name": name, "parents": [folder_id], "mimeType": mime_type}
            created = (
                self.service.files()
                .create(body=body, media_body=media, fields="id, name", supportsAllDrives=True)
                .execute()
            )
            fid = created.get("id")
            logging.info("Uploaded file to Drive: %s (%s)", created.get("name"), fid)
            return fid
        except Exception as e:
            logging.error("Drive upload error: %s", e)
            return None
