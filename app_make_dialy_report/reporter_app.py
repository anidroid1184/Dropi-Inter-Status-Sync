"""
APP MAKE DAILY REPORT - Generador de Reportes Diarios

Aplicación independiente para generar reportes Excel con discrepancias
y subirlos a Google Drive.

Responsabilidades:
- Leer datos de Google Sheets
- Filtrar registros con COINCIDEN=FALSE (discrepancias)
- Generar archivo Excel con formato
- Subir a Google Drive
- Logging de operaciones

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
Versión: 2.0.0
"""

from __future__ import annotations
import argparse
import logging
import sys
from datetime import datetime

from reporter_config import settings
from reporter_logging import setup_logging
from reporter_credentials import load_credentials
from reporter_sheets import SheetsReader
from reporter_drive import DriveUploader
from reporter_excel import ExcelGenerator


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
        "--output-dir",
        type=str,
        default=".",
        help="Directorio de salida para Excel (default: actual)"
    )
    
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Subir a Google Drive después de generar"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular sin generar/subir archivo"
    )
    
    return parser.parse_args()


def generate_report(
    sheets_reader: SheetsReader,
    excel_gen: ExcelGenerator,
    output_dir: str,
    dry_run: bool
) -> str:
    """
    Genera reporte Excel con discrepancias (COINCIDEN=FALSE).
    
    Args:
        sheets_reader: Cliente para leer Sheets
        excel_gen: Generador de Excel
        output_dir: Directorio de salida
        dry_run: Modo simulación
        
    Returns:
        str: Ruta del archivo generado (o vacío si dry-run)
    """
    logging.info("Leyendo datos de Google Sheets...")
    
    # Leer todos los registros
    all_records = sheets_reader.read_all_records()
    
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
        logging.info("[DRY-RUN] Simulación: archivo NO generado")
        return ""
    
    # Generar archivo Excel
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"discrepancias_{date_str}.xlsx"
    
    output_path = excel_gen.generate(
        data=discrepancias,
        output_dir=output_dir,
        filename=filename
    )
    
    logging.info(f"Reporte generado: {output_path}")
    return output_path


def upload_report(
    drive_uploader: DriveUploader,
    file_path: str,
    dry_run: bool
) -> str:
    """
    Sube reporte a Google Drive.
    
    Args:
        drive_uploader: Cliente de Drive
        file_path: Ruta del archivo a subir
        dry_run: Modo simulación
        
    Returns:
        str: ID del archivo en Drive (o vacío si dry-run)
    """
    if not file_path:
        return ""
    
    if dry_run:
        logging.info("[DRY-RUN] Simulación: archivo NO subido")
        return ""
    
    file_id = drive_uploader.upload(file_path)
    logging.info(f"Archivo subido a Drive: {file_id}")
    
    return file_id


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
        
        sheets_reader = SheetsReader(
            credentials,
            settings.spreadsheet_name
        )
        
        excel_gen = ExcelGenerator()
        
        # Generar reporte
        output_path = generate_report(
            sheets_reader,
            excel_gen,
            args.output_dir,
            args.dry_run
        )
        
        # Subir a Drive si se solicitó
        if args.upload and output_path:
            drive_uploader = DriveUploader(
                credentials,
                settings.drive_folder_id
            )
            
            upload_report(
                drive_uploader,
                output_path,
                args.dry_run
            )
        
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
