from __future__ import annotations
import argparse
import os
import sys

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from logging_setup import setup_logging
from app import load_credentials
from services.sheets_client import SheetsClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Show basic info about the main tracking sheet")
    parser.add_argument("--spreadsheet-name", default=None, help="Override spreadsheet name (optional)")
    args = parser.parse_args()

    setup_logging()

    creds = load_credentials()
    from config import settings
    spreadsheet_name = args.spreadsheet_name or settings.spreadsheet_name
    sheets = SheetsClient(creds, spreadsheet_name)

    ws = sheets.sheet()
    all_values = ws.get_all_values()
    total_rows = len(all_values)
    total_cols = len(all_values[0]) if all_values else 0

    print(f"rows={total_rows}")
    print(f"cols={total_cols}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
