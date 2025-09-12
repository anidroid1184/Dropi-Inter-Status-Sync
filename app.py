from __future__ import annotations
import argparse
import io
import logging
import os
import csv
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import threading

import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

from config import settings
from logging_setup import setup_logging
from services.drive_client import DriveClient
from services.sheets_client import SheetsClient
from services.tracker_service import TrackerService
from web.inter_scraper import InterScraper
from web.inter_scraper_async import AsyncInterScraper
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


def update_statuses(sheets: SheetsClient, scraper: InterScraper, start_row: int = 2, end_row: int | None = None, limit: int | None = None):
    # Use resilient reader to avoid stopping at first blank row
    records = sheets.read_main_records_resilient()
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
        if end_row is not None and idx > end_row:
            break
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

        # Queue update ONLY if we have a non-empty status to avoid overwriting with blanks
        if web_status:
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


async def update_statuses_async(
    sheets: SheetsClient,
    headless: bool,
    start_row: int = 2,
    end_row: int | None = None,
    limit: int | None = None,
    max_concurrency: int = 3,
    rps: float | None = None,
    retries: int = 2,
    timeout_ms: int = 30000,
    batch_size: int = 5000,
    sleep_between_batches: float = 20.0,
    only_empty: bool = False,
):
    # Use resilient reader to avoid stopping at first blank row
    records = sheets.read_main_records_resilient()
    headers = sheets.read_headers()

    # Ensure required headers
    required_headers = ["ID DROPI", "ID TRACKING", "STATUS DROPI", "STATUS TRACKING", "Alerta"]
    sheets.ensure_headers(required_headers)
    headers = sheets.read_headers()

    tracking_col = headers.index("ID TRACKING") + 1
    dropi_col = headers.index("STATUS DROPI") + 1
    web_col = headers.index("STATUS TRACKING") + 1

    batch_updates = []
    differences = []

    processed = 0
    status_log_path = _init_status_log()

    # Build list of items to process
    items: list[tuple[int, str, str, str]] = []  # (row, tracking_number, dropi_raw, dropi_norm)
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
        web_norm = str(record.get("STATUS TRACKING", "")).strip()
        if only_empty and web_norm:
            continue

        # Skip if terminal or ineligible
        if TrackerService.terminal(dropi, web_norm or ""):
            logging.info("Terminal status, skip: %s", tracking_number)
            continue
        if not TrackerService.can_query(dropi):
            logging.info("Not eligible to query (DROPi=%s): %s", dropi, tracking_number)
            continue

        items.append((idx, tracking_number, dropi_raw, dropi))
        processed += 1

    if not items:
        logging.info("No eligible rows to process")
        return

    # Process in batches to keep browser fresh and reduce blanks over long runs
    def chunk(seq, size):
        for i in range(0, len(seq), size):
            yield seq[i:i+size]

    processed_total = 0
    for batch_idx, batch in enumerate(chunk(items, max(1, int(batch_size))), start=1):
        logging.info("Processing batch %d with %d items", batch_idx, len(batch))
        scraper = AsyncInterScraper(
            headless=headless,
            max_concurrency=max_concurrency,
            retries=retries,
            timeout_ms=timeout_ms,
        )
        await scraper.start()
        try:
            tn_list = [tn for _, tn, _, _ in batch]
            results = await scraper.get_status_many(tn_list, rps=rps)
            status_by_tn = {tn: raw for tn, raw in results}

            # Optional second pass for empties in this batch (quick re-try burst)
            missing = [tn for tn in tn_list if not (status_by_tn.get(tn) or "").strip()]
            if missing:
                logging.info("Second pass for %d empty results in batch %d", len(missing), batch_idx)
                results2 = await scraper.get_status_many(missing, rps=(rps or 0.8))
                for tn, raw in results2:
                    if raw:
                        status_by_tn[tn] = raw

            for (idx, tn, dropi_raw, dropi) in batch:
                web_status_raw = status_by_tn.get(tn, "")
                exp = TrackerService.explain_normalization(web_status_raw)
                web_status = exp["status"]
                via = exp.get("via", "")
                new_status = ""
                if via not in {"mapping", "override"}:
                    new_status = (web_status_raw or "").strip()
                _update_status_catalog(web_status_raw or "", via)

                alerta = TrackerService.compute_alert(dropi, web_status)

                _append_status_log(
                    status_log_path,
                    tn,
                    dropi_raw,
                    dropi,
                    web_status_raw or "",
                    web_status,
                    alerta,
                    via,
                    new_status,
                )

                if web_status:
                    row_updates = [None] * web_col
                    row_updates[web_col - 1] = web_status
                    batch_updates.append((idx, row_updates))

                if dropi != web_status:
                    differences.append([
                        tn,
                        dropi,
                        web_status,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ])

            if batch_updates:
                _flush_batch(sheets, batch_updates)
                batch_updates.clear()

            processed_total += len(batch)
            logging.info("Batch %d done. Processed so far: %d", batch_idx, processed_total)
        finally:
            await scraper.close()

        # Pause between batches to be gentle with target site and Sheets API
        if sleep_between_batches and processed_total < len(items):
            try:
                await asyncio.sleep(float(sleep_between_batches))
            except Exception:
                pass

    if differences:
        sheets.create_or_append_daily_report(differences, prefix=settings.daily_report_prefix)

    logging.info("Statuses updated (async). Processed rows: %d, differences: %d", len(items), len(differences))


def _flush_batch(sheets: SheetsClient, batch_updates: list[tuple[int, list[Any]]] ):
    """Write only the exact cells that changed.

    Groups updates by column index and then splits into consecutive row-blocks,
    updating each block separately. This avoids clearing cells in rows that are
    not part of the batch.
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



def main():
    parser = argparse.ArgumentParser(description="Interrapidísimo tracking updater")
    parser.add_argument("--start-row", type=int, default=2, help="Start processing from this row (1-based)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows to process")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing changes")
    parser.add_argument("--skip-drive", action="store_true", help="Skip Drive source ingestion and only update statuses from the existing sheet")
    parser.add_argument("--async", dest="use_async", action="store_true", help="Use async Playwright scraper with concurrency")
    parser.add_argument("--max-concurrency", type=int, default=3, help="Max concurrent browser pages when using --async")
    parser.add_argument("--rps", type=float, default=None, help="Limit of requests per second when using --async (pacing task launches)")
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
            if args.use_async:
                # Safe async runner: if there is an active loop (e.g. IDE), run the coroutine in a
                # dedicated thread with its own loop; otherwise use asyncio.run.
                def _run_coro_in_thread(coro):
                    result = {
                        "exc": None,
                    }

                    def _runner():
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(coro)
                        except Exception as e:
                            result["exc"] = e
                        finally:
                            try:
                                loop.close()
                            except Exception:
                                pass

                    try:
                        running = asyncio.get_running_loop()
                    except RuntimeError:
                        running = None

                    if running and running.is_running():
                        t = threading.Thread(target=_runner, daemon=True)
                        t.start()
                        t.join()
                        if result["exc"]:
                            raise result["exc"]
                    else:
                        asyncio.run(coro)

                _run_coro_in_thread(update_statuses_async(
                    sheets,
                    settings.headless,
                    start_row=args.start_row,
                    limit=args.limit,
                    max_concurrency=args.max_concurrency,
                    rps=args.rps,
                ))
            else:
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
