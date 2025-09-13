from __future__ import annotations
import argparse
import logging
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
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
        description=(
            "Genera/actualiza la hoja diaria Informe_YYYY-MM-DD con 5 columnas: "
            "ID DROPI, ID TRACKING, STATUS DROPI, STATUS TRACKING, FECHA VERIFICACIÓN"
        )
    )
    parser.add_argument("--start-row", type=int, default=2, help="Fila inicial (1-based)")
    parser.add_argument("--end-row", type=int, default=None, help="Fila final (inclusive)")
    parser.add_argument(
        "--limit", type=int, default=None, help="Máximo de filas a incluir"
    )
    parser.add_argument(
        "--date", type=str, default=None, help="Fecha del informe (YYYY-MM-DD). Si se omite se usa la fecha actual"
    )
    # Ya no se selecciona un solo ID; el reporte incluye ambos IDs
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting make_daily_report process")

    creds = load_credentials()
    sheets = SheetsClient(creds, settings.spreadsheet_name)

    # Leer filas de la hoja principal de forma resiliente
    try:
        tz = ZoneInfo(settings.timezone)
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
        now_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        for idx, rec in enumerate(records, start=2):
            if idx < args.start_row:
                continue
            if args.end_row is not None and idx > args.end_row:
                break
            if args.limit is not None and processed >= args.limit:
                break

            id_dropi = str(rec.get("ID DROPI", "")).strip()
            id_tracking = str(rec.get("ID TRACKING", "")).strip()
            dropi = str(rec.get("STATUS DROPI", "")).strip()
            web = str(rec.get("STATUS TRACKING", "")).strip()
            if not id_dropi and not id_tracking:
                continue

            rows.append([id_dropi, id_tracking, dropi, web, now_str])
            processed += 1

        if not rows:
            logging.info("No rows collected for daily report")
            return 0

        # Resolver nombre de hoja (fecha especificada o actual en zona horaria)
        date_for_sheet = args.date or datetime.now(tz).strftime("%Y-%m-%d")
        sheet_name = f"{settings.daily_report_prefix}{date_for_sheet}"

        # Escribir (reemplazo completo): limpiar hoja existente o crear y luego escribir headers + datos
        headers = ["ID DROPI", "ID TRACKING", "STATUS DROPI", "STATUS TRACKING", "FECHA VERIFICACIÓN"]
        try:
            try:
                ws = sheets.spreadsheet.worksheet(sheet_name)
                # Limpiar contenidos previos para reemplazo total
                ws.clear()
            except Exception:
                ws = sheets.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)

            # Escribir encabezados
            ws.update(range_name="A1:E1", values=[headers])

            # Asegurar espacio suficiente y escribir en bloques para evitar límites de tamaño
            CHUNK = 2000
            total = len(rows)
            if (total + 1) > ws.row_count:
                ws.add_rows(total + 1 - ws.row_count)
            for i in range(0, total, CHUNK):
                part = rows[i:i+CHUNK]
                start_row = 2 + i
                end_row = start_row + len(part) - 1
                ws.update(range_name=f"A{start_row}:E{end_row}", values=part)

            logging.info("Daily report updated: %s, rows: %d", sheet_name, len(rows))
            return 0
        except Exception as e:
            logging.error("Error updating daily report: %s", e)
            return 2

    except Exception as e:
        logging.exception("Error in make_daily_report: %s", e)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
