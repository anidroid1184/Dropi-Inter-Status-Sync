from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import gspread
import logging
from datetime import datetime
import time


class SheetsClient:
    """Encapsulates operations on the tracking spreadsheet using gspread."""

    def __init__(self, credentials, spreadsheet_name: str):
        self.gc = gspread.authorize(credentials)
        self.spreadsheet = self.gc.open(spreadsheet_name)

    # --- Main sheet helpers ---
    def sheet(self):
        return self.spreadsheet.sheet1

    def read_main_records(self) -> List[Dict[str, Any]]:
        return self.sheet().get_all_records()

    def read_main_records_resilient(self) -> List[Dict[str, Any]]:
        """Read all rows using get_all_values(), avoiding early stop at the first blank row.

        It builds dict records using the header row (row 1). Trailing missing
        cells are filled as empty strings to keep consistent keys.
        """
        sh = self.sheet()
        all_values = sh.get_all_values()
        if not all_values:
            return []
        headers = [h.strip() for h in (all_values[0] if all_values else [])]
        if not headers:
            return []
        records: List[Dict[str, Any]] = []
        for row in all_values[1:]:
            # Ensure row length matches headers length
            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))
            elif len(row) > len(headers):
                row = row[:len(headers)]
            rec = {headers[i]: row[i] for i in range(len(headers))}
            records.append(rec)
        return records

    def read_headers(self) -> List[str]:
        return self.sheet().row_values(1)

    def ensure_headers(self, headers: List[str]) -> None:
        existing = self.read_headers()
        to_add = []
        for h in headers:
            if h not in existing:
                to_add.append(h)
                existing.append(h)
        if to_add:
            # Add missing headers at the end
            for idx, h in enumerate(to_add, start=len(existing) - len(to_add) + 1):
                self.sheet().update_cell(1, idx, h)
            logging.info("Added missing headers: %s", to_add)

    def append_new_rows(self, rows: List[List[Any]]) -> int:
        if not rows:
            return 0
        sh = self.sheet()
        all_values = sh.get_all_values()
        last_row = len(all_values) + 1
        end_row = last_row + len(rows) - 1
        if end_row > sh.row_count:
            extra = end_row - sh.row_count
            logging.info("Adding %d extra rows to accommodate data", extra)
            sh.add_rows(extra)
        sh.update(f"A{last_row}:E{end_row}", rows)
        return len(rows)

    def update_range(self, a1_range: str, values: List[List[Any]]):
        # Simple retry with backoff to handle 429 rate limit bursts
        delay = 1.0
        for attempt in range(5):
            try:
                self.sheet().update(a1_range, values)
                return
            except Exception as e:
                msg = str(e)
                if "429" in msg or "quota" in msg.lower():
                    logging.warning("Sheets update_range throttled (attempt %d): %s", attempt + 1, msg)
                    time.sleep(delay)
                    delay = min(delay * 2, 30)
                    continue
                raise

    def values_batch_update(self, data: List[Dict[str, Any]], value_input_option: str = "RAW"):
        """Perform a single batch update for many disjoint ranges.

        data items: {"range": A1, "values": [[...], ...]}
        """
        body = {
            "valueInputOption": value_input_option,
            "data": data,
        }
        delay = 1.0
        for attempt in range(5):
            try:
                # gspread exposes Spreadsheet.values_batch_update
                return self.spreadsheet.values_batch_update(body)
            except Exception as e:
                msg = str(e)
                if "429" in msg or "quota" in msg.lower():
                    logging.warning("Sheets values_batch_update throttled (attempt %d): %s", attempt + 1, msg)
                    time.sleep(delay)
                    delay = min(delay * 2, 30)
                    continue
                raise

    # --- Daily report helpers ---
    def create_or_append_daily_report(self, _rows: List[List[Any]], prefix: str = "Informe_") -> str:
        """Create or REPLACE the daily report with rows where ALERTA == TRUE.

        Ignores the passed-in rows and instead reads the main sheet to ensure
        the report reflects the current state after post-compare.
        """
        date_name = datetime.now().strftime("%Y-%m-%d")
        sheet_name = f"{prefix}{date_name}"
        try:
            # Read all records from main sheet
            records = self.read_main_records_resilient()
            if not records:
                # Still create/clear the report with just headers
                filtered_rows: List[List[Any]] = []
            else:
                # Find header keys with resilient casing
                sample = records[0]
                def find_key(candidates: List[str]) -> Optional[str]:
                    keys = {k.strip().upper(): k for k in sample.keys()}
                    for cand in candidates:
                        if cand.upper() in keys:
                            return keys[cand.upper()]
                    return None

                k_tracking = find_key(["ID TRACKING"]) or "ID TRACKING"
                k_dropi = find_key(["STATUS DROPI"]) or "STATUS DROPI"
                k_web = find_key(["STATUS TRACKING"]) or "STATUS TRACKING"
                k_alerta = find_key(["ALERTA", "Alerta"]) or "ALERTA"
                k_coinciden = find_key(["COINCIDEN"])  # may be None if not created yet

                filtered_rows = []
                TRUTHY = {"TRUE", "VERDADERO", "SI", "SÍ", "YES", "1"}
                FALSY = {"FALSE", "FALSO", "NO", "0"}
                coinc_false_count = 0
                alerta_truthy_count = 0
                for rec in records:
                    include = False
                    # Condition A: ALERTA is truthy (user's requirement)
                    alerta_raw = rec.get(k_alerta, "")
                    alerta_val_upper = str(alerta_raw).strip().upper()
                    if alerta_val_upper in TRUTHY:
                        include = True
                        alerta_truthy_count += 1
                    # Condition B: OR COINCIDEN == FALSE (safety net when ALERTA not set yet)
                    if not include and k_coinciden:
                        coinc_raw = rec.get(k_coinciden, "")
                        coinc_val = str(coinc_raw).strip().upper()
                        if coinc_val in FALSY:
                            include = True
                            coinc_false_count += 1

                    if include:
                        filtered_rows.append([
                            str(rec.get(k_tracking, "")).strip(),
                            str(rec.get(k_dropi, "")).strip(),
                            str(rec.get(k_web, "")).strip(),
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ])
                # Diagnostics
                logging.info(
                    "Daily report selection: total=%d, coinciden_false=%d, alerta_truthy=%d, final_rows=%d",
                    len(records), coinc_false_count, alerta_truthy_count, len(filtered_rows)
                )

            # Create or open the report sheet
            try:
                ws = self.spreadsheet.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                ws = self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)

            # REPLACE: clear previous content and write fresh headers + rows
            headers = ["ID TRACKING", "STATUS DROPI", "STATUS TRACKING", "FECHA VERIFICACIÓN"]
            ws.clear()
            ws.update("A1:D1", [headers])
            if filtered_rows:
                end_row = 1 + len(filtered_rows)
                if end_row > ws.row_count:
                    ws.add_rows(end_row - ws.row_count)
                ws.update(f"A2:D{end_row}", filtered_rows)
            logging.info("Daily report replaced: %s, rows: %d (ALERTA=TRUE)", sheet_name, len(filtered_rows))
            return sheet_name
        except Exception as e:
            logging.error("Error updating daily report: %s", e)
            return sheet_name
