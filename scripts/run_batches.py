from __future__ import annotations
import argparse
import asyncio
import logging
import math
import os
import sys
from typing import Optional

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from logging_setup import setup_logging
from services.sheets_client import SheetsClient
from app import load_credentials, update_statuses_async


def bool_arg(v: str) -> bool:
    return str(v).lower() in {"1", "true", "yes", "y"}


def run_coro(coro) -> None:
    """Run a coroutine safely whether or not an event loop is already active."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # Run in a dedicated thread/loop
        import threading
        exc: list[BaseException] = []
        def _runner():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(coro)
            except BaseException as e:
                exc.append(e)
            finally:
                try:
                    new_loop.close()
                except Exception:
                    pass
        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join()
        if exc:
            raise exc[0]
    else:
        asyncio.run(coro)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Interrapidísimo scraping in sequential batches with a second pass to fill blanks")
    parser.add_argument("--start-row", type=int, default=2, help="Fila inicial (1-based, usual 2)")
    parser.add_argument("--end-row", type=int, default=None, help="Fila final (incluida). Si no se pasa, usa tamaño total de la hoja")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Tamaño de cada lote (default 1000)")

    parser.add_argument("--max-concurrency", type=int, default=3)
    parser.add_argument("--rps", type=float, default=1.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout-ms", dest="timeout_ms", type=int, default=35000)
    parser.add_argument("--headless", type=bool_arg, default=True)
    parser.add_argument("--sleep-between", type=float, default=10.0, help="Segundos entre lotes")
    parser.add_argument("--second-pass", type=bool_arg, default=True, help="Hacer segunda pasada solo para celdas vacías dentro de cada lote")
    parser.add_argument("--second-pass-rps", type=float, default=None, help="RPS para la segunda pasada (si no se pasa, usa --rps o 0.8)")
    parser.add_argument("--second-pass-retries", type=int, default=None, help="Retrintentos para segunda pasada (si no se pasa, usa --retries")
    parser.add_argument("--second-pass-timeout-ms", type=int, default=None, help="Timeout ms para segunda pasada (si no se pasa, usa --timeout-ms")

    args = parser.parse_args()

    setup_logging()
    logging.info("Starting run_batches orchestrator")

    creds = load_credentials()
    from config import settings
    sheets = SheetsClient(creds, settings.spreadsheet_name)

    # Determine total rows
    ws = sheets.sheet()
    total_rows = len(ws.get_all_values())

    start = max(2, int(args.start_row))
    end = int(args.end_row) if args.end_row else total_rows
    chunk = max(1, int(args.chunk_size))

    # Build batches (inclusive ranges)
    batches: list[tuple[int, int]] = []
    cur = start
    while cur <= end:
        last = min(cur + chunk - 1, end)
        batches.append((cur, last))
        cur = last + 1

    logging.info("Total rows=%d, planning %d batches of up to %d rows", total_rows, len(batches), chunk)

    for i, (b_start, b_end) in enumerate(batches, start=1):
        logging.info("Batch %d/%d: rows %d..%d", i, len(batches), b_start, b_end)
        # Primera pasada normal del lote
        run_coro(update_statuses_async(
            sheets,
            args.headless,
            start_row=b_start,
            end_row=b_end,
            limit=None,  # bounded by end_row
            max_concurrency=args.max_concurrency,
            rps=args.rps,
            retries=args.retries,
            timeout_ms=args.timeout_ms,
        ))
        # Segunda pasada para solo vacíos (si está activada)
        if args.second_pass:
            sp_rps = args.second_pass_rps if args.second_pass_rps is not None else (args.rps if args.rps is not None else 0.8)
            sp_retries = args.second_pass_retries if args.second_pass_retries is not None else args.retries
            sp_timeout = args.second_pass_timeout_ms if args.second_pass_timeout_ms is not None else args.timeout_ms
            logging.info("Second pass for batch %d on empty cells only (rps=%.2f, retries=%d, timeout=%dms)", i, float(sp_rps), int(sp_retries), int(sp_timeout))
            run_coro(update_statuses_async(
                sheets,
                args.headless,
                start_row=b_start,
                end_row=b_end,
                limit=None,
                max_concurrency=args.max_concurrency,
                rps=sp_rps,
                retries=sp_retries,
                timeout_ms=sp_timeout,
                only_empty=True,
            ))
        # Sleep between batches to be gentle
        if i < len(batches) and args.sleep_between and args.sleep_between > 0:
            logging.info("Sleeping %.1f seconds before next batch", args.sleep_between)
            try:
                import time
                time.sleep(float(args.sleep_between))
            except Exception:
                pass

    logging.info("All batches completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
