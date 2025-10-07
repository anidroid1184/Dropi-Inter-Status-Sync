from __future__ import annotations
import argparse
import asyncio
import logging
import threading
import os
import sys

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import settings
from logging_setup import setup_logging
from services.sheets_client import SheetsClient
from services.drive_client import DriveClient
from app import load_credentials, update_statuses_async


def run_coroutine_safely(coro):
    """Runs an async coroutine even if an event loop is already running (e.g., IDE).
    If an event loop is active, runs in a dedicated thread with its own loop.
    """
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
        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join()
        if result["exc"]:
            raise result["exc"]
    else:
        asyncio.run(coro)


def main() -> int:
    parser = argparse.ArgumentParser(description="Interrapidísimo scraping process (modular)")
    parser.add_argument("--start-row", type=int, default=2)
    parser.add_argument("--end-row", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-concurrency", type=int, default=3)
    parser.add_argument("--rps", type=float, default=None)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--timeout-ms", dest="timeout_ms", type=int, default=30000)
    parser.add_argument("--headless", type=lambda v: str(v).lower() in {"1","true","yes"}, default=settings.headless)
    parser.add_argument("--batch-size", dest="batch_size", type=int, default=500, help="Items per browser batch (default 500)")
    parser.add_argument("--only-empty", dest="only_empty", action="store_true", help="Process only rows where STATUS TRACKING is empty")
    parser.add_argument("--sleep-between-batches", dest="sleep_between_batches", type=float, default=5.0, help="Seconds to sleep between batches (default 5.0). Set 0 to disable.")
    parser.add_argument("--skip-drive", action="store_true", help="Do not ingest new rows from Drive here; this runner only updates statuses")
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting Interrapidísimo modular process")

    creds = load_credentials()
    sheets = SheetsClient(creds, settings.spreadsheet_name)

    # This modular runner focuses only on status updates
    try:
        run_coroutine_safely(update_statuses_async(
            sheets,
            args.headless,
            start_row=args.start_row,
            end_row=args.end_row,
            limit=args.limit,
            max_concurrency=args.max_concurrency,
            rps=args.rps,
            retries=args.retries,
            timeout_ms=args.timeout_ms,
            batch_size=args.batch_size,
            sleep_between_batches=args.sleep_between_batches,
            only_empty=args.only_empty,
        ))
        return 0
    except Exception as e:
        logging.exception("Fatal error in inter_process: %s", e)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
