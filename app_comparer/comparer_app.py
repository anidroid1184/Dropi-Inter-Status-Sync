"""
APP COMPARER - Comparador de Estados Dropi vs Interrapidísimo

Aplicación independiente para comparar estados entre Dropi y Web,
calculando coincidencias.

Responsabilidades:
- Comparar STATUS DROPI vs STATUS TRACKING
- Calcular columna COINCIDEN (TRUE/FALSE)
- Normalización de estados antes de comparar

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
Versión: 2.0.0
"""

from __future__ import annotations
import argparse
import logging
import sys
from typing import List, Tuple, Dict

from comparer_config import settings
from comparer_logging import setup_logging
from comparer_sheets import SheetsClient
from comparer_normalizer import StatusNormalizer
from comparer_credentials import load_credentials


def parse_arguments() -> argparse.Namespace:
    """Parsea argumentos CLI."""
    parser = argparse.ArgumentParser(
        description="Comparador de estados Dropi vs Web"
    )
    
    parser.add_argument(
        "--start-row",
        type=int,
        default=2,
        help="Fila inicial (default: 2)"
    )
    
    parser.add_argument(
        "--end-row",
        type=int,
        default=None,
        help="Fila final (default: todas)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Tamaño de batch (default: 5000)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular sin escribir"
    )
    
    return parser.parse_args()


def compare_statuses(
    sheets: SheetsClient,
    start_row: int,
    end_row: int | None,
    batch_size: int,
    dry_run: bool
) -> Tuple[int, int]:
    """
    Compara estados y actualiza columna COINCIDEN.
    
    Args:
        sheets: Cliente de Sheets
        start_row: Fila inicial
        end_row: Fila final
        batch_size: Tamaño de batch
        dry_run: Modo simulación
        
    Returns:
        Tuple[int, int]: (total_procesado, total_coinciden)
    """
    logging.info("Iniciando comparación de estados...")
    
    records = sheets.read_all_records()
    updates: List[Tuple[int, Dict[str, str]]] = []
    
    total_processed = 0
    total_coinciden = 0
    
    for idx, record in enumerate(records, start=2):
        if idx < start_row:
            continue
        if end_row and idx > end_row:
            break
            
        # Obtener estados raw
        dropi_raw = str(record.get("STATUS DROPI", "")).strip()
        web_raw = str(record.get("STATUS TRACKING", "")).strip()
        
        if not dropi_raw and not web_raw:
            continue
        
        # Normalizar estados
        dropi_norm = StatusNormalizer.normalize(dropi_raw) if dropi_raw else "PENDIENTE"
        web_norm = StatusNormalizer.normalize(web_raw) if web_raw else "PENDIENTE"
        
        # Calcular coincidencia
        coinciden = "TRUE" if (dropi_norm == web_norm) else "FALSE"
        
        if coinciden == "TRUE":
            total_coinciden += 1
        
        # Agregar a batch de actualizaciones
        updates.append((idx, {
            "COINCIDEN": coinciden
        }))
        total_processed += 1
        
        # Flush batch periódicamente
        if len(updates) >= batch_size:
            if not dry_run:
                sheets.batch_update_comparison(updates)
                logging.info(f"Batch actualizado: {len(updates)} filas")
            updates.clear()
    
    # Flush batch final
    if updates and not dry_run:
        sheets.batch_update_comparison(updates)
        logging.info(f"Batch final: {len(updates)} filas")
    
    logging.info(
        f"Comparación completada: {total_processed} filas, "
        f"{total_coinciden} coincidencias"
    )
    return total_processed, total_coinciden


def main() -> int:
    """Función principal."""
    args = parse_arguments()
    setup_logging()
    
    logging.info("=== COMPARER APP INICIANDO ===")
    logging.info(f"Rango: {args.start_row}-{args.end_row or 'fin'}")
    logging.info(f"Batch size: {args.batch_size}")
    
    try:
        # Inicializar servicios
        credentials = load_credentials()
        sheets = SheetsClient(credentials, settings.spreadsheet_name)
        
        # Ejecutar comparación
        processed, coinciden = compare_statuses(
            sheets,
            args.start_row,
            args.end_row,
            args.batch_size,
            args.dry_run
        )
        
        logging.info(f"=== COMPARER COMPLETADO ===")
        logging.info(f"Procesadas: {processed} filas")
        logging.info(f"Coincidencias: {coinciden}")
        
        return 0
        
    except KeyboardInterrupt:
        logging.warning("Proceso interrumpido")
        return 1
        
    except Exception as e:
        logging.exception(f"Error fatal: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
