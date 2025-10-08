"""
APP MAKE DAILY REPORT - Generador de Reportes Diarios

Aplicación independiente para generar reportes de discrepancias
como nueva hoja en el mismo spreadsheet de Google Sheets.

Responsabilidades:
- Leer datos de Google Sheets
- Filtrar registros con COINCIDEN=FALSE (discrepancias)
- Crear nueva hoja en el spreadsheet con las discrepancias
- Formatear la nueva hoja
- Logging de operaciones

IMPORTANTE: NO genera archivos Excel ni sube a Drive.
Crea una nueva hoja (sheet) dentro del mismo archivo de Google Sheets.

Columnas incluidas en el reporte:
- GUIA
- STATUS DROPI
- STATUS INTERRAPIDISIMO (texto crudo de la web)
- COINCIDEN (siempre FALSE en el reporte)
- ... y todas las demás columnas del spreadsheet

Autor: Sistema de Tracking Dropi-Inter
Fecha: Enero 2025
Versión: 2.0.0
"""

from __future__ import annotations
import argparse
import logging
import sys

from reporter_config import settings
from reporter_logging import setup_logging
from reporter_credentials import load_credentials
from reporter_sheets import SheetsManager


def parse_arguments() -> argparse.Namespace:
    """
    Parsea argumentos de línea de comandos.
    
    Returns:
        argparse.Namespace: Argumentos parseados
    """
    parser = argparse.ArgumentParser(
        description="Generador de reportes diarios de discrepancias"
    )
    
    parser.add_argument(
        "--sheet-name",
        type=str,
        default=None,
        help="Nombre de la hoja a crear (default: discrepancias_YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular sin crear hoja"
    )
    
    return parser.parse_args()


def generate_report(
    sheets_manager: SheetsManager,
    sheet_name: str | None,
    dry_run: bool
) -> str:
    """
    Genera reporte creando nueva hoja con discrepancias (COINCIDEN=FALSE).
    
    Args:
        sheets_manager: Cliente para gestionar Sheets
        sheet_name: Nombre de la hoja a crear (None = auto)
        dry_run: Modo simulación
        
    Returns:
        str: Nombre de la hoja creada (o vacío si dry-run)
    """
    logging.info("Leyendo datos de Google Sheets...")
    
    # Leer todos los registros
    all_records = sheets_manager.read_all_records()
    
    # Filtrar solo discrepancias (COINCIDEN=FALSE)
    discrepancias = [
        r for r in all_records 
        if r.get("COINCIDEN", "").upper() == "FALSE"
    ]
    
    logging.info(f"Total registros: {len(all_records)}")
    logging.info(f"Discrepancias detectadas: {len(discrepancias)}")
    
    if not discrepancias:
        logging.warning("No hay discrepancias para reportar")
        return ""
    
    if dry_run:
        logging.info("[DRY-RUN] Simulación: hoja NO creada")
        logging.info(f"Se crearían {len(discrepancias)} registros")
        return ""
    
    # Crear nueva hoja con discrepancias
    created_sheet = sheets_manager.create_report_sheet(
        data=discrepancias,
        sheet_name=sheet_name
    )
    
    logging.info(f"Hoja de reporte creada: {created_sheet}")
    return created_sheet


def main() -> int:
    """
    Función principal de la app de reportes.
    
    Returns:
        int: Código de salida (0=éxito, 1=error)
    """
    args = parse_arguments()
    setup_logging()
    
    logging.info("=== REPORTER APP INICIANDO ===")
    
    try:
        # Inicializar servicios
        credentials = load_credentials()
        
        sheets_manager = SheetsManager(
            credentials,
            settings.spreadsheet_name
        )
        
        # Generar reporte (crear nueva hoja)
        created_sheet = generate_report(
            sheets_manager,
            args.sheet_name,
            args.dry_run
        )
        
        if created_sheet:
            logging.info(f"✓ Reporte creado en hoja: {created_sheet}")
        
        logging.info("=== REPORTER COMPLETADO ===")
        return 0
        
    except KeyboardInterrupt:
        logging.warning("Proceso interrumpido por usuario")
        return 1
        
    except Exception as e:
        logging.exception(f"Error fatal: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
