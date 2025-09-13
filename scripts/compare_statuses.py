from __future__ import annotations
import argparse
import logging
import os
import sys
from typing import Any, List

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from logging_setup import setup_logging
from config import settings
from services.sheets_client import SheetsClient
from oauth2client.service_account import ServiceAccountCredentials
from services.tracker_service import TrackerService


def load_credentials() -> ServiceAccountCredentials:
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return creds


def _flush_batch(sheets: SheetsClient, batch_updates: list[tuple[int, list[Any]]]):
    """Write only the exact cells that changed.

    Groups updates by column index and then splits into consecutive row-blocks,
    updating each block separately.
    """
    if not batch_updates:
        return

    # Build mapping: col_idx -> list[(row, value)]
    by_col: dict[int, list[tuple[int, Any]]] = {}
    for row, arr in batch_updates:
        for col_idx, val in enumerate(arr, start=1):
            if val is None:
                continue
            by_col.setdefault(col_idx, []).append((row, val))

    batched_payload: list[dict] = []
    for col_idx, items in by_col.items():
        # Sort by row
        items.sort(key=lambda x: x[0])
        # Group into consecutive row blocks
        block: list[tuple[int, Any]] = []
        prev_row = None
        def flush_block():
            if not block:
                return
            start_row = block[0][0]
            end_row = block[-1][0]
            values = [[v] for _, v in block]  # single column
            col_letter = chr(ord('A') + col_idx - 1)
            a1 = f"{col_letter}{start_row}:{col_letter}{end_row}"
            batched_payload.append({"range": a1, "values": values})

        for r, v in items:
            if prev_row is None or r == prev_row + 1:
                block.append((r, v))
            else:
                flush_block()
                block = [(r, v)]
            prev_row = r
        flush_block()

    # Send in chunks to respect API limits (e.g., 100 ranges per request)
    if batched_payload:
        CHUNK = 100
        for i in range(0, len(batched_payload), CHUNK):
            chunk = batched_payload[i:i+CHUNK]
            sheets.values_batch_update(chunk)


def main() -> int:
    parser = argparse.ArgumentParser(description="Comparar STATUS DROPI vs STATUS TRACKING y escribir COINCIDEN y ALERTA")
    parser.add_argument("--start-row", type=int, default=2)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Solo calcular, no escribir cambios")
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting compare_statuses process")

    creds = load_credentials()
    sheets = SheetsClient(creds, settings.spreadsheet_name)

    # Ensure headers exist
    required_headers = ["ID DROPI", "ID TRACKING", "STATUS DROPI", "STATUS TRACKING", "COINCIDEN", "ALERTA"]
    sheets.ensure_headers(required_headers)
    headers = sheets.read_headers()

    try:
        records = sheets.read_main_records_resilient() if hasattr(sheets, 'read_main_records_resilient') else sheets.read_main_records()
        # column indices (1-based)
        dropi_col = headers.index("STATUS DROPI") + 1
        track_col = headers.index("STATUS TRACKING") + 1
        coincide_col = headers.index("COINCIDEN") + 1
        alerta_col = headers.index("ALERTA") + 1

        updates: list[tuple[int, list[Any]]] = []
        updated_rows = 0
        for idx, rec in enumerate(records, start=2):
            if idx < args.start_row:
                continue
            if args.end_row is not None and idx > args.end_row:
                break
            # Raw values
            dropi_raw = str(rec.get("STATUS DROPI", "")).strip()
            web_raw = str(rec.get("STATUS TRACKING", "")).strip()
            if not dropi_raw and not web_raw:
                continue

            # Normalized comparisons (avoid treating empty as PENDIENTE)
            dropi_norm = TrackerService.normalize_status(dropi_raw) if dropi_raw else ""
            web_norm = TrackerService.normalize_status(web_raw) if web_raw else ""

            coinciden = "TRUE" if (dropi_norm and web_norm and dropi_norm == web_norm) else "FALSE"
            # Compute alerta using business rule; fill defaults to keep logic stable
            alerta = TrackerService.compute_alert(dropi_norm or "PENDIENTE", web_norm or "PENDIENTE")

            # Build row updates only where values differ from current
            cur_coinciden = str(rec.get("COINCIDEN", "")).strip().upper()
            cur_alerta = str(rec.get("ALERTA", "")).strip().upper()
            row = [None] * max(coincide_col, alerta_col)
            wrote = False
            if cur_coinciden != coinciden:
                row[coincide_col - 1] = coinciden
                wrote = True
            if cur_alerta != alerta:
                row[alerta_col - 1] = alerta
                wrote = True
            if wrote:
                updates.append((idx, row))
                updated_rows += 1
                if updated_rows % 100 == 0:
                    logging.info("compare_statuses progress: %d rows with changes (at row %d)", updated_rows, idx)

        if updates and not args.dry_run:
            _flush_batch(sheets, updates)
        logging.info("compare_statuses done. Rows updated: %d%s", updated_rows, " (dry-run)" if args.dry_run else "")
        return 0
    except Exception as e:
        logging.exception("Error in compare_statuses: %s", e)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
