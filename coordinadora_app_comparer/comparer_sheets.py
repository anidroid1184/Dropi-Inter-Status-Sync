"""
Google Sheets Client para APP COMPARER (Coordinadora).

Cliente simplificado para operaciones de lectura/escritura en Google Sheets.
"""
import logging
from typing import List, Dict, Tuple, Any

import gspread
from oauth2client.service_account import ServiceAccountCredentials


class SheetsClient:
    """Cliente para operaciones con Google Sheets."""

    def __init__(
        self,
        credentials: ServiceAccountCredentials,
        spreadsheet_name: str
    ):
        self.credentials = credentials
        self.spreadsheet_name = spreadsheet_name

        gc = gspread.authorize(credentials)
        self.spreadsheet = gc.open(spreadsheet_name)
        self.worksheet = self.spreadsheet.sheet1

        logging.info(f"Conectado a spreadsheet: {spreadsheet_name}")

    def read_all_records(self) -> List[Dict[str, Any]]:
        records = self.worksheet.get_all_records()
        logging.info(f"Leídos {len(records)} registros")
        return records

    def ensure_columns(self, column_names: List[str]) -> None:
        headers = self.worksheet.row_values(1)

        for col_name in column_names:
            if col_name not in headers:
                col_index = len(headers) + 1
                self.worksheet.update_cell(1, col_index, col_name)
                headers.append(col_name)
                logging.info(f"Columna creada: {col_name}")

    def batch_update_comparison(
        self,
        updates: List[Tuple[int, Dict[str, str]]]
    ) -> None:
        if not updates:
            return

        headers = self.worksheet.row_values(1)

        try:
            coinciden_col = headers.index("COINCIDEN") + 1
        except ValueError as e:
            raise ValueError(f"Columna COINCIDEN no encontrada: {e}")

        batch_data = []
        for row_num, values in updates:
            if "COINCIDEN" in values:
                batch_data.append({
                    "range": f"{self._col_letter(coinciden_col)}{row_num}",
                    "values": [[values["COINCIDEN"]]]
                })

        if batch_data:
            self.worksheet.batch_update(batch_data)
            logging.info(f"Batch update ejecutado: {len(batch_data)} celdas")

    @staticmethod
    def _col_letter(col_num: int) -> str:
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(col_num % 26 + 65) + result
            col_num //= 26
        return result

        return result
