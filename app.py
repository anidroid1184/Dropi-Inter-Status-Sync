from __future__ import annotations
import argparse
import io
import logging
import os
import csv
import json
from datetime import datetime
from typing import List, Dict, Any

import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

from config import settings
from logging_setup import setup_logging
from services.drive_client import DriveClient
from services.sheets_client import SheetsClient
from services.tracker_service import TrackerService
from web.inter_scraper import InterScraper
from utils.checkpoints import load_checkpoint, save_checkpoint


def _init_status_log() -> str:
    """Prepare a CSV file to log per-tracking results for auditing."""
    os.makedirs("logs", exist_ok=True)
    path = os.path.join("logs", f"statuses_{datetime.now().strftime('%Y%m%d')}.csv")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "tracking_number",
                "dropi_raw",
                "dropi_norm",
                "web_raw",
                "web_norm",
                "alerta",
                "via",
                "new_status",
            ])
    return path


def _append_status_log(path: str, tracking_number: str, dropi_raw: str, dropi_norm: str, web_raw: str, web_norm: str, alerta: str, via: str, new_status: str) -> None:
    try:
        with open(path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                tracking_number,
                dropi_raw,
                dropi_norm,
                web_raw,
                web_norm,
                alerta,
                via,
                new_status,
            ])
    except Exception as e:
        logging.error("Error writing status log: %s", e)


def _append_event_log(path: str, event: str, details: str = "") -> None:
    try:
        with open(path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "",  # tracking_number empty for events
                event,
                details,
                "",
                "",
                "",
                "event",
                "",
            ])
    except Exception as e:
        logging.error("Error writing event log: %s", e)


def _update_status_catalog(web_raw: str, via: str) -> None:
    """Persist a catalog of all distinct raw statuses observed to logs/status_catalog.json."""
    if not web_raw:
        return
    os.makedirs("logs", exist_ok=True)
    catalog_path = os.path.join("logs", "status_catalog.json")
    data = {"items": {}}
    try:
        if os.path.exists(catalog_path):
            with open(catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {"items": {}}
    except Exception:
        # reset if corrupt
        data = {"items": {}}
    items = data.setdefault("items", {})
    key = web_raw.strip()
    rec = items.get(key, {"count": 0, "last_seen": None, "via": via})
    rec["count"] = int(rec.get("count", 0)) + 1
    rec["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec["via"] = via or rec.get("via") or ""
    items[key] = rec
    try:
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error("Error writing status_catalog.json: %s", e)


def load_credentials() -> ServiceAccountCredentials:
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return creds


def read_source_data(drive: DriveClient, file_id: str) -> List[Dict[str, Any]]:
    content = drive.download_bytes(file_id)
    if not content:
        return []
    df = pd.read_excel(io.BytesIO(content), dtype={"NÚMERO GUIA": str})
    df.columns = [c.strip().upper() for c in df.columns]
    if "NÚMERO GUIA" not in df.columns:
        logging.error("Excel missing 'NÚMERO GUIA' column")
        return []
    df = df[df["NÚMERO GUIA"].notna()]
    processed = []
    seen = set()
    for _, row in df.iterrows():
        guia = str(row.get("NÚMERO GUIA", "")).strip()
        if not guia or guia in seen:
            continue
        seen.add(guia)
        processed.append(
            {
                "ID DROPI": row.get("ID", ""),
                "ID TRACKING": guia,
                "STATUS DROPI": row.get("ESTATUS", ""),
            }
        )
    logging.info("Processed source rows: %d", len(processed))
    return processed


def update_tracking_sheet(sheets: SheetsClient, source_data: List[Dict[str, Any]]) -> int:
    sheet = sheets.sheet()
    existing_records = sheet.get_all_records()
    existing_guias = {str(r.get("ID TRACKING", "")).strip() for r in existing_records if r.get("ID TRACKING")}
    new_rows = TrackerService.prepare_new_rows(source_data, existing_guias)
    added = sheets.append_new_rows(new_rows)
    return added


def update_statuses(sheets: SheetsClient, scraper: InterScraper, start_row: int = 2, limit: int | None = None):
    records = sheets.read_main_records()
    headers = sheets.read_headers()

    # Ensure required headers
    required_headers = ["ID DROPI", "ID TRACKING", "STATUS DROPI", "STATUS TRACKING", "Alerta"]
    sheets.ensure_headers(required_headers)
    headers = sheets.read_headers()

    tracking_col = headers.index("ID TRACKING") + 1
    dropi_col = headers.index("STATUS DROPI") + 1
    web_col = headers.index("STATUS TRACKING") + 1
    # alert_col = headers.index("Alerta") + 1  # Disabled: do not modify this column for now

    batch_updates = []
    differences = []

    processed = 0
    status_log_path = _init_status_log()
    for idx, record in enumerate(records, start=2):
        if idx < start_row:
            continue
        if limit is not None and processed >= limit:
            break

        tracking_number = str(record.get("ID TRACKING", "")).strip()
        if not tracking_number:
            continue

        dropi_raw = str(record.get("STATUS DROPI", "")).strip()
        dropi = TrackerService.normalize_status(dropi_raw)

        web_raw = str(record.get("STATUS TRACKING", "")).strip()
        web_norm = TrackerService.normalize_status(web_raw) if web_raw else None

        if TrackerService.terminal(dropi, web_norm or ""):
            logging.info("Terminal status, skip: %s", tracking_number)
            continue
        if not TrackerService.can_query(dropi):
            logging.info("Not eligible to query (DROPi=%s): %s", dropi, tracking_number)
            continue

        logging.info("Querying tracking: %s", tracking_number)
        web_status_raw = scraper.get_status(tracking_number)
        exp = TrackerService.explain_normalization(web_status_raw)
        web_status = exp["status"]
        via = exp.get("via", "")
        # If not recognized by mappings/overrides, log as new_status so it can be added later
        new_status = ""
        if via not in {"mapping", "override"}:
            new_status = (web_status_raw or "").strip()
        # Update status catalog regardless
        _update_status_catalog(web_status_raw or "", via)

        alerta = TrackerService.compute_alert(dropi, web_status)

        # Audit log for each tracking processed (including computed alerta, but we won't write it to the sheet yet)
        _append_status_log(
            status_log_path,
            tracking_number,
            dropi_raw,
            dropi,
            web_status_raw or "",
            web_status,
            alerta,
            via,
            new_status,
        )

        # Queue update for this row: ONLY STATUS TRACKING column
        row_updates = [None] * web_col
        row_updates[web_col - 1] = web_status
        batch_updates.append((idx, row_updates))

        if dropi != web_status:
            differences.append([
                tracking_number,
                dropi,
                web_status,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ])

        processed += 1

        # Periodically flush in batches of 200 rows
        if len(batch_updates) >= 200:
            _flush_batch(sheets, batch_updates)
            save_checkpoint({"last_row": idx, "last_tracking": tracking_number, "date": datetime.now().isoformat()})
            batch_updates.clear()

    if batch_updates:
        _flush_batch(sheets, batch_updates)

    # Daily report
    if differences:
        sheets.create_or_append_daily_report(differences, prefix=settings.daily_report_prefix)

    logging.info("Statuses updated. Processed rows: %d, differences: %d", processed, len(differences))


def _flush_batch(sheets: SheetsClient, batch_updates: list[tuple[int, list[Any]]]):
    # Determine the minimal and maximal 1-based column indices that have any update,
    # so we don't overwrite earlier columns unintentionally.
    def non_none_indices(arr: list[Any]) -> list[int]:
        return [i for i, v in enumerate(arr, start=1) if v is not None]

    updated_indices = []
    for _, arr in batch_updates:
        updated_indices.extend(non_none_indices(arr))
    if not updated_indices:
        return

    min_col_idx = min(updated_indices)
    max_col_idx = max(updated_indices)

    # Build values matrix only for [min_col_idx, max_col_idx] inclusive
    min_row = min(r for r, _ in batch_updates)
    max_row = max(r for r, _ in batch_updates)
    values: list[list[Any]] = []
    for r in range(min_row, max_row + 1):
        match = next((arr for rr, arr in batch_updates if rr == r), None)
        if match is None:
            # Fill with blanks across the slice width
            values.append([""] * (max_col_idx - min_col_idx + 1))
        else:
            # Slice the row to only the updated range and replace None with ""
            slice_vals = []
            for idx in range(min_col_idx - 1, max_col_idx):
                v = match[idx] if idx < len(match) else None
                slice_vals.append("" if v is None else v)
            values.append(slice_vals)

    start_col_letter = chr(ord('A') + min_col_idx - 1)
    end_col_letter = chr(ord('A') + max_col_idx - 1)
    a1 = f"{start_col_letter}{min_row}:{end_col_letter}{max_row}"
    sheets.update_range(a1, values)



def main():
    parser = argparse.ArgumentParser(description="Interrapidísimo tracking updater")
    parser.add_argument("--start-row", type=int, default=2, help="Start processing from this row (1-based)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows to process")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing changes")
    parser.add_argument("--skip-drive", action="store_true", help="Skip Drive source ingestion and only update statuses from the existing sheet")
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting app")

    creds = load_credentials()
    drive = DriveClient(creds)
    sheets = SheetsClient(creds, settings.spreadsheet_name)
    scraper = InterScraper(headless=settings.headless)

    try:
        if not args.skip_drive:
            latest = drive.latest_file(settings.drive_folder_id)
            if not latest:
                logging.error("No latest file available")
                return 1
            source = read_source_data(drive, latest["id"])
            added = update_tracking_sheet(sheets, source)
            logging.info("New rows added: %d", added)
            if added:
                # Log event 'Añadido al drive' with count
                status_log_path = _init_status_log()
                _append_event_log(status_log_path, "Añadido al drive", str(added))
        else:
            logging.info("--skip-drive enabled: skipping source ingestion from Drive")

        if not args.dry_run:
            update_statuses(sheets, scraper, start_row=args.start_row, limit=args.limit)
        else:
            logging.info("Dry-run mode: skipping status updates")
        return 0
    except Exception as e:
        logging.exception("Fatal error: %s", e)
        return 2
    finally:
        scraper.close()


if __name__ == "__main__":
    raise SystemExit(main())
