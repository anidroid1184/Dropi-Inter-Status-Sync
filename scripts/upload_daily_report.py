from __future__ import annotations
import argparse
import csv
import io
import logging
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from logging_setup import setup_logging
from config import settings
from services.sheets_client import SheetsClient
from services.drive_client import DriveClient
from oauth2client.service_account import ServiceAccountCredentials


def load_credentials() -> ServiceAccountCredentials:
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return creds


def sheet_to_csv_bytes(values: List[List[str]]) -> bytes:
    """Serialize a 2D list of values to UTF-8 CSV bytes (RFC4180-ish)."""
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    for row in values:
        writer.writerow(row)
    data = buf.getvalue().encode("utf-8")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exporta la hoja Informe_YYYY-MM-DD a CSV y la sube a Drive con el mismo nombre (Informe_YYYY-MM-DD.csv)"
    )
    parser.add_argument("--date", type=str, default=None, help="Fecha del informe (YYYY-MM-DD). Si se omite, usa la fecha local de TZ")
    parser.add_argument("--replace", action="store_true", help="Si existe un archivo con el mismo nombre en la carpeta, reemplazarlo")
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting upload_daily_report process")

    if not settings.individual_report_folder_id:
        logging.error("Missing individual report folder id. Set DRIVE_FOLER_INDIVIDUAL_FILE in .env")
        return 2

    creds = load_credentials()
    sheets = SheetsClient(creds, settings.spreadsheet_name)
    drive = DriveClient(creds)

    tz = ZoneInfo(settings.timezone)
    date_for_sheet = args.date or datetime.now(tz).strftime("%Y-%m-%d")
    sheet_name = f"{settings.daily_report_prefix}{date_for_sheet}"

    try:
        # Fetch worksheet and values
        try:
            ws = sheets.spreadsheet.worksheet(sheet_name)
        except Exception:
            logging.error("Worksheet not found: %s", sheet_name)
            return 2
        values = ws.get_all_values()
        if not values:
            logging.error("Worksheet %s is empty", sheet_name)
            return 2

        # Build CSV
        csv_bytes = sheet_to_csv_bytes(values)
        file_name = f"{sheet_name}.csv"
        file_id = drive.upload_bytes(
            folder_id=settings.individual_report_folder_id,
            name=file_name,
            data=csv_bytes,
            mime_type="text/csv",
            replace=args.replace or True,
        )
        if not file_id:
            logging.error("Upload failed for %s", file_name)
            return 2
        logging.info("Uploaded report to Drive: %s (id=%s)", file_name, file_id)
        return 0
    except Exception as e:
        logging.exception("Error in upload_daily_report: %s", e)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
