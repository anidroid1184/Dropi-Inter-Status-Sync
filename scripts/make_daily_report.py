from __future__ import annotations
import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Any, List, Dict

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from logging_setup import setup_logging
from config import settings
from services.sheets_client import SheetsClient
from oauth2client.service_account import ServiceAccountCredentials


def load_credentials() -> ServiceAccountCredentials:
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return creds


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera/actualiza la hoja diaria Informe_YYYY-MM-DD con 4 columnas: ID TRACKING, STATUS DROPI, STATUS TRACKING, FECHA VERIFICACIÓN"
    )
    parser.add_argument("--start-row", type=int, default=2, help="Fila inicial (1-based)")
    parser.add_argument("--end-row", type=int, default=None, help="Fila final (inclusive)")
    parser.add_argument(
        "--limit", type=int, default=None, help="Máximo de filas a incluir"
    )
    parser.add_argument(
        "--date", type=str, default=None, help="Fecha del informe (YYYY-MM-DD). Si se omite se usa la fecha actual"
    )
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting make_daily_report process")

    creds = load_credentials()
    sheets = SheetsClient(creds, settings.spreadsheet_name)

    # Leer filas de la hoja principal de forma resiliente
    try:
        records: List[Dict[str, Any]] = (
            sheets.read_main_records_resilient()
            if hasattr(sheets, "read_main_records_resilient")
            else sheets.read_main_records()
        )
        if not records:
            logging.warning("No records found in main sheet")
            return 0

        rows: List[List[str]] = []
        processed = 0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for idx, rec in enumerate(records, start=2):
            if idx < args.start_row:
                continue
            if args.end_row is not None and idx > args.end_row:
                break
            if args.limit is not None and processed >= args.limit:
                break

            tracking = str(rec.get("ID TRACKING", "")).strip()
            dropi = str(rec.get("STATUS DROPI", "")).strip()
            web = str(rec.get("STATUS TRACKING", "")).strip()
            if not tracking:
                continue

            rows.append([tracking, dropi, web, now_str])
            processed += 1

        if not rows:
            logging.info("No rows collected for daily report")
            return 0

        # Si el usuario pasa --date, temporalmente cambiamos la fecha para el nombre de la hoja
        if args.date:
            # Hack simple: temporalmente parchear datetime.now() no es práctico; mejor crear una función en SheetsClient.
            # Aquí replicamos la lógica para el nombre y escribimos manualmente en esa hoja.
            sheet_name = f"{settings.daily_report_prefix}{args.date}"
            try:
                try:
                    ws = sheets.spreadsheet.worksheet(sheet_name)
                except Exception:
                    ws = sheets.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                    ws.update("A1:D1", [["ID TRACKING", "STATUS DROPI", "STATUS TRACKING", "FECHA VERIFICACIÓN"]])
                start_row = len(ws.get_all_values()) + 1
                end_row = start_row + len(rows) - 1
                if end_row > ws.row_count:
                    ws.add_rows(end_row - ws.row_count)
                ws.update(f"A{start_row}:D{end_row}", rows)
                logging.info("Daily report updated: %s, rows: %d", sheet_name, len(rows))
                return 0
            except Exception as e:
                logging.error("Error updating date-specific daily report: %s", e)
                return 2
        else:
            sheets.create_or_append_daily_report(rows, prefix=settings.daily_report_prefix)
            return 0

    except Exception as e:
        logging.exception("Error in make_daily_report: %s", e)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
