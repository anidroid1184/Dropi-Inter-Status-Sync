"""
Google Sheets Client para APP COMPARER.

Cliente simplificado para operaciones de lectura/escritura en Google Sheets.

Responsabilidades:
- Leer registros del spreadsheet
- Batch updates para columnas COINCIDEN y ALERTA
- Asegurar que existan columnas necesarias

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import logging
from typing import List, Dict, Tuple, Any

import gspread
from oauth2client.service_account import ServiceAccountCredentials


class SheetsClient:
    """
    Cliente para operaciones con Google Sheets.
    
    Attributes:
        credentials: Credenciales de Google API
        spreadsheet_name: Nombre del spreadsheet
        worksheet: Worksheet activa
    """
    
    def __init__(
        self,
        credentials: ServiceAccountCredentials,
        spreadsheet_name: str
    ):
        """
        Inicializa el cliente de Sheets.
        
        Args:
            credentials: Credenciales de Google API
            spreadsheet_name: Nombre del spreadsheet
        """
        self.credentials = credentials
        self.spreadsheet_name = spreadsheet_name
        
        # Autenticar y abrir spreadsheet
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open(spreadsheet_name)
        self.worksheet = spreadsheet.sheet1
        
        logging.info(f"Conectado a spreadsheet: {spreadsheet_name}")
    
    def read_all_records(self) -> List[Dict[str, Any]]:
        """
        Lee todos los registros del spreadsheet.
        
        Returns:
            List[Dict]: Lista de registros como diccionarios
        """
        records = self.worksheet.get_all_records()
        logging.info(f"Leídos {len(records)} registros")
        return records
    
    def ensure_columns(self, column_names: List[str]) -> None:
        """
        Asegura que existan las columnas especificadas.
        
        Args:
            column_names: Lista de nombres de columnas
        """
        headers = self.worksheet.row_values(1)
        
        for col_name in column_names:
            if col_name not in headers:
                # Agregar columna al final
                col_index = len(headers) + 1
                self.worksheet.update_cell(1, col_index, col_name)
                headers.append(col_name)
                logging.info(f"Columna creada: {col_name}")
    
    def batch_update_comparison(
        self,
        updates: List[Tuple[int, Dict[str, str]]]
    ) -> None:
        """
        Actualiza columna COINCIDEN en batch.
        
        Args:
            updates: Lista de tuplas (row_num, {col_name: value})
        """
        if not updates:
            return
        
        headers = self.worksheet.row_values(1)
        
        # Obtener índice de columna COINCIDEN
        try:
            coinciden_col = headers.index("COINCIDEN") + 1
        except ValueError as e:
            raise ValueError(f"Columna COINCIDEN no encontrada: {e}")
        
        # Construir batch de actualizaciones
        batch_data = []
        
        for row_num, values in updates:
            if "COINCIDEN" in values:
                batch_data.append({
                    "range": f"{self._col_letter(coinciden_col)}{row_num}",
                    "values": [[values["COINCIDEN"]]]
                })
        
        # Ejecutar batch update
        if batch_data:
            self.worksheet.batch_update(batch_data)
            logging.info(f"Batch update ejecutado: {len(batch_data)} celdas")
    
    @staticmethod
    def _col_letter(col_num: int) -> str:
        """
        Convierte número de columna a letra (1 → A, 27 → AA).
        
        Args:
            col_num: Número de columna (1-indexed)
            
        Returns:
            str: Letra de columna
        """
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(col_num % 26 + 65) + result
            col_num //= 26
        return result
