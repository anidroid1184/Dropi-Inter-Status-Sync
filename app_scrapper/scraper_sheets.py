"""
Cliente simplificado de Google Sheets para App Scraper.

Responsabilidades:
- Leer registros del spreadsheet
- Actualizar celdas individuales
- Batch updates optimizados para estados

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import gspread
import logging
from typing import List, Dict, Any, Tuple


class SheetsClient:
    """Cliente para operaciones en Google Sheets."""
    
    def __init__(self, credentials, spreadsheet_name: str):
        """
        Inicializa cliente de Sheets.
        
        Args:
            credentials: Credenciales de Google
            spreadsheet_name: Nombre de la hoja de cálculo
        """
        self.gc = gspread.authorize(credentials)
        self.spreadsheet = self.gc.open(spreadsheet_name)
        self.sheet = self.spreadsheet.sheet1
        
    def read_all_records(self) -> List[Dict[str, Any]]:
        """
        Lee todos los registros de la hoja.
        
        Returns:
            List[Dict]: Lista de registros
        """
        try:
            return self.sheet.get_all_records()
        except Exception as e:
            logging.error(f"Error leyendo registros: {e}")
            return []
    
    def update_cell(self, row: int, column_name: str, value: str) -> bool:
        """
        Actualiza una celda específica.
        
        Args:
            row: Número de fila (1-based)
            column_name: Nombre de la columna
            value: Valor a escribir
            
        Returns:
            bool: True si exitoso
        """
        try:
            headers = self.sheet.row_values(1)
            col_idx = headers.index(column_name) + 1
            self.sheet.update_cell(row, col_idx, value)
            return True
        except Exception as e:
            logging.error(f"Error actualizando celda [{row}, {column_name}]: {e}")
            return False
    
    def batch_update_status(self, updates: List[Tuple[int, str]]) -> bool:
        """
        Actualiza múltiples estados en batch.
        Solo actualiza STATUS INTERRAPIDISIMO con el estado crudo de la web.
        
        Args:
            updates: Lista de tuplas (row, status)
            
        Returns:
            bool: True si exitoso
        """
        try:
            headers = self.sheet.row_values(1)
            inter_col = headers.index("STATUS INTERRAPIDISIMO") + 1
            
            # Preparar actualizaciones solo para STATUS INTERRAPIDISIMO
            batch_data = []
            for row, status in updates:
                batch_data.append({
                    "range": f"{self._col_letter(inter_col)}{row}",
                    "values": [[status]]
                })
            
            # Enviar batch
            self.spreadsheet.values_batch_update({
                "valueInputOption": "RAW",
                "data": batch_data
            })
            
            logging.info(f"Batch update exitoso: {len(updates)} filas")
            return True
            
        except Exception as e:
            logging.error(f"Error en batch update: {e}")
            return False
    
    @staticmethod
    def _col_letter(col_num: int) -> str:
        """
        Convierte número de columna a letra (1 -> A, 27 -> AA).
        
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
