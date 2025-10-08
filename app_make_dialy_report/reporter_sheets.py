"""
Google Sheets Manager para APP MAKE DAILY REPORT.

Cliente para leer datos y crear nuevas hojas con discrepancias.

Responsabilidades:
- Leer todos los registros del spreadsheet
- Crear nuevas hojas (sheets) con discrepancias
- Formatear hojas de reporte

Autor: Sistema de Tracking Dropi-Inter
Fecha: Enero 2025
Versión: 2.0.0
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials


class SheetsManager:
    """
    Cliente para gestionar Google Sheets (lectura y escritura).
    
    Attributes:
        credentials: Credenciales de Google API
        spreadsheet_name: Nombre del spreadsheet
        spreadsheet: Objeto spreadsheet de gspread
        worksheet: Worksheet principal (sheet1)
    """
    
    def __init__(
        self,
        credentials: ServiceAccountCredentials,
        spreadsheet_name: str
    ):
        """
        Inicializa el gestor de Sheets.
        
        Args:
            credentials: Credenciales de Google API
            spreadsheet_name: Nombre del spreadsheet
        """
        self.credentials = credentials
        self.spreadsheet_name = spreadsheet_name
        
        # Autenticar y abrir spreadsheet
        gc = gspread.authorize(credentials)
        self.spreadsheet = gc.open(spreadsheet_name)
        self.worksheet = self.spreadsheet.sheet1
        
        logging.info(f"Conectado a spreadsheet: {spreadsheet_name}")
    
    def read_all_records(self) -> List[Dict[str, Any]]:
        """
        Lee todos los registros del spreadsheet principal.
        
        Returns:
            List[Dict]: Lista de registros como diccionarios
        """
        records = self.worksheet.get_all_records()
        logging.info(f"Leídos {len(records)} registros")
        return records
    
    def create_report_sheet(
        self,
        data: List[Dict[str, Any]],
        sheet_name: str = None
    ) -> str:
        """
        Crea una nueva hoja con datos de discrepancias.
        
        Si ya existe una hoja con el mismo nombre, la elimina y crea una nueva.
        
        Args:
            data: Lista de diccionarios con datos de discrepancias
            sheet_name: Nombre de la hoja (default: discrepancias_YYYY-MM-DD)
            
        Returns:
            str: Nombre de la hoja creada
        """
        if not data:
            logging.warning("No hay datos para crear hoja")
            return ""
        
        # Generar nombre de hoja
        if not sheet_name:
            date_str = datetime.now().strftime("%Y-%m-%d")
            sheet_name = f"discrepancias_{date_str}"
        
        logging.info(f"Creando hoja: {sheet_name}")
        
        # Eliminar hoja si ya existe
        try:
            existing_sheet = self.spreadsheet.worksheet(sheet_name)
            self.spreadsheet.del_worksheet(existing_sheet)
            logging.info(f"Hoja existente eliminada: {sheet_name}")
        except gspread.exceptions.WorksheetNotFound:
            pass  # No existe, continuamos
        
        # Crear nueva hoja
        new_sheet = self.spreadsheet.add_worksheet(
            title=sheet_name,
            rows=len(data) + 1,  # +1 para headers
            cols=len(data[0].keys()) if data else 10
        )
        
        # Preparar datos
        headers = list(data[0].keys())
        rows = [headers]
        
        for record in data:
            row = [record.get(col, "") for col in headers]
            rows.append(row)
        
        # Escribir datos en batch
        new_sheet.update(f"A1:Z{len(rows)}", rows)
        
        # Formatear headers
        self._format_headers(new_sheet, len(headers))
        
        logging.info(
            f"Hoja creada exitosamente: {sheet_name} "
            f"({len(data)} registros)"
        )
        
        return sheet_name
    
    @staticmethod
    def _format_headers(sheet: gspread.Worksheet, num_cols: int) -> None:
        """
        Aplica formato a la fila de headers.
        
        Args:
            sheet: Worksheet a formatear
            num_cols: Número de columnas
        """
        try:
            # Formato de headers: fondo azul, texto blanco, negrita
            sheet.format("A1:Z1", {
                "backgroundColor": {
                    "red": 0.26,
                    "green": 0.45,
                    "blue": 0.77
                },
                "textFormat": {
                    "bold": True,
                    "foregroundColor": {
                        "red": 1.0,
                        "green": 1.0,
                        "blue": 1.0
                    }
                },
                "horizontalAlignment": "CENTER"
            })
            
            # Congelar fila de headers
            sheet.freeze(rows=1)
            
            logging.debug("Headers formateados correctamente")
            
        except Exception as e:
            logging.warning(f"No se pudo formatear headers: {e}")


# Mantener alias para compatibilidad
SheetsReader = SheetsManager
