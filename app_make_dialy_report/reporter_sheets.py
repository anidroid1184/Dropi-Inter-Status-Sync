"""
Google Sheets Reader para APP MAKE DAILY REPORT.

Cliente simplificado para leer datos de Google Sheets.

Responsabilidades:
- Leer todos los registros del spreadsheet
- Proveer datos estructurados

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any

import gspread
from oauth2client.service_account import ServiceAccountCredentials


class SheetsReader:
    """
    Cliente para leer datos de Google Sheets.
    
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
        Inicializa el lector de Sheets.
        
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
