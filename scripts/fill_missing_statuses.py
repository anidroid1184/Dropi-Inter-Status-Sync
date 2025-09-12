from __future__ import annotations
import argparse
import asyncio
import logging
import os
import sys
from contextlib import suppress
from typing import List, Tuple

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import settings
from logging_setup import setup_logging
from services.sheets_client import SheetsClient
from oauth2client.service_account import ServiceAccountCredentials
from web.inter_scraper_async import AsyncInterScraper


async def fill_missing_async(
    sheets: SheetsClient,
    headless: bool,
    start_row: int = 2,
    end_row: int | None = None,
    max_concurrency: int = 3,
    rps: float | None = None,
    retries: int = 2,
    timeout_ms: int = 30000,
    batch_size: int = 200,
    sleep_between_batches: float = 10.0,
) -> None:
    """Find rows with empty STATUS TRACKING and re-scrape only those.

    This does not apply business eligibility filters: if it's empty, we try.
    """
    # Read all rows resiliently
    records = sheets.read_main_records_resilient()
    headers = sheets.read_headers()

    required_headers = ["ID TRACKING", "STATUS TRACKING"]
    for h in required_headers:
        if h not in headers:
            logging.error("Missing required header: %s", h)
            return

    web_col = headers.index("STATUS TRACKING") + 1

    # Gather candidates (row index, tracking)
    items: list[tuple[int, str]] = []
    for idx, rec in enumerate(records, start=2):
        if idx < start_row:
            continue
        if end_row is not None and idx > end_row:
            break
        tn = str(rec.get("ID TRACKING", "")).strip()
        web = str(rec.get("STATUS TRACKING", "")).strip()
        if tn and not web:
            items.append((idx, tn))

    logging.info("Post-pass candidates (empty STATUS TRACKING): %d", len(items))
    if not items:
        logging.info("No empty STATUS TRACKING cells to fill.")
        return

    # Chunk helper
    def chunk(seq, size):
        for i in range(0, len(seq), size):
            yield seq[i : i + size]

    processed_total = 0
    for batch_idx, batch in enumerate(chunk(items, max(1, int(batch_size))), start=1):
        logging.info("Post-pass batch %d with %d items", batch_idx, len(batch))
        scraper = AsyncInterScraper(
            headless=headless,
            max_concurrency=max_concurrency,
            retries=retries,
            timeout_ms=timeout_ms,
            block_resources=False,
        )
        await scraper.start()
        try:
            tn_list = [tn for _, tn in batch]
            results = await scraper.get_status_many(tn_list, rps=rps)
            status_by_tn = {tn: raw for tn, raw in results}

            # Small second pass for blanks in this batch
            missing = [tn for tn in tn_list if not (status_by_tn.get(tn) or "").strip()]
            if missing:
                logging.info("Second pass for %d empties (post-pass batch %d)", len(missing), batch_idx)
                results2 = await scraper.get_status_many(missing, rps=(rps or 0.8))
                for tn, raw in results2:
                    if raw:
                        status_by_tn[tn] = raw

            # Build updates only for non-empty scraped values
            batch_updates: list[tuple[int, list[object]]] = []
            for (row_idx, tn) in batch:
                raw = (status_by_tn.get(tn) or "").strip()
                if raw:
                    row_updates = [None] * web_col
                    row_updates[web_col - 1] = raw
                    batch_updates.append((row_idx, row_updates))

            if batch_updates:
                _flush_batch(sheets, batch_updates)

            processed_total += len(batch)
            logging.info("Post-pass batch %d done. Processed so far: %d", batch_idx, processed_total)
        except Exception as e:
            # If browser crashed (TargetClosedError), try smaller chunks sequentially
            logging.exception("Post-pass batch %d failed, retrying in smaller chunks due to: %s", batch_idx, e)
            try:
                sub_size = max(25, int(len(batch) / 10))
                for sub_idx, sub in enumerate(chunk(batch, sub_size), start=1):
                    logging.info("Retry sub-batch %d.%d with %d items", batch_idx, sub_idx, len(sub))
                    sub_scraper = AsyncInterScraper(
                        headless=headless,
                        max_concurrency=min(2, max_concurrency),
                        retries=max(1, retries),
                        timeout_ms=timeout_ms,
                        block_resources=False,
                    )
                    await sub_scraper.start()
                    try:
                        tn_list = [tn for _, tn in sub]
                        results = await sub_scraper.get_status_many(tn_list, rps=(rps or 0.5))
                        status_by_tn = {tn: raw for tn, raw in results}
                        batch_updates: list[tuple[int, list[object]]] = []
                        for (row_idx, tn) in sub:
                            raw = (status_by_tn.get(tn) or "").strip()
                            if raw:
                                row_updates = [None] * web_col
                                row_updates[web_col - 1] = raw
                                batch_updates.append((row_idx, row_updates))
                        if batch_updates:
                            _flush_batch(sheets, batch_updates)
                    finally:
                        with suppress(Exception):
                            await sub_scraper.close()
            except Exception as e2:
                logging.exception("Sub-batch retry also failed: %s", e2)
        finally:
            with suppress(Exception):
                await scraper.close()

        if sleep_between_batches and processed_total < len(items):
            try:
                await asyncio.sleep(float(sleep_between_batches))
            except Exception:
                pass


def run_coroutine_safely(coro):
    """Runs an async coroutine even if an event loop is already running (e.g., IDE)."""
    result = {"exc": None}

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
        import threading

        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join()
        if result["exc"]:
            raise result["exc"]
    else:
        asyncio.run(coro)


def load_credentials() -> ServiceAccountCredentials:
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return creds


def _flush_batch(sheets: SheetsClient, batch_updates: list[tuple[int, list[object]]]):
    """Write only the exact cells that changed (single-column updates batched).

    This duplicates the logic from app._flush_batch to avoid circular imports.
    """
    if not batch_updates:
        return

    # Build mapping: col_idx -> list[(row, value)]
    by_col: dict[int, list[tuple[int, object]]] = {}
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
        block: list[tuple[int, object]] = []
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
    parser = argparse.ArgumentParser(description="Post-scraping filler: re-scrape empty STATUS TRACKING cells")
    parser.add_argument("--start-row", type=int, default=2)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--max-concurrency", type=int, default=3)
    parser.add_argument("--rps", type=float, default=None)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--timeout-ms", dest="timeout_ms", type=int, default=30000)
    parser.add_argument("--headless", type=lambda v: str(v).lower() in {"1","true","yes"}, default=True)
    parser.add_argument("--batch-size", type=int, default=2000)
    parser.add_argument("--sleep-between-batches", type=float, default=10.0)
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting post-scraping filler process")

    creds = load_credentials()
    sheets = SheetsClient(creds, settings.spreadsheet_name)

    try:
        run_coroutine_safely(
            fill_missing_async(
                sheets,
                args.headless,
                start_row=args.start_row,
                end_row=args.end_row,
                max_concurrency=args.max_concurrency,
                rps=args.rps,
                retries=args.retries,
                timeout_ms=args.timeout_ms,
                batch_size=args.batch_size,
                sleep_between_batches=args.sleep_between_batches,
            )
        )
        return 0
    except Exception as e:
        logging.exception("Fatal error in post-scraping filler: %s", e)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
