from __future__ import annotations
from typing import Optional, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
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
