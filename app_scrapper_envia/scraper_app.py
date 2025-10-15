"""
APP SCRAPER ENVIA - Sistema de Scraping de Estados Envía

Aplicación independiente para scraping de estados de tracking desde
el portal web de 17track.net para Envía y actualización en Google Sheets.

Responsabilidades:
- Scraping web de estados de Envía desde 17track.net (sync/async)
- Procesamiento de hasta 40 guías por vez
- Extracción del estado crudo exactamente como aparece en la web
- Actualización solo de columna STATUS ENVIA con texto sin normalizar
- Logging de operaciones de scraping
- Gestión de reintentos y errores

IMPORTANTE: Este scraper NO normaliza estados. Guarda el texto crudo de la web.
Ejemplos de salida:
  - "En tránsito"
  - "Entregado"
  - "En proceso"

La normalización y comparación se realiza en app_comparer.

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
Versión: 2.0.0
"""

from __future__ import annotations
import argparse
import logging
import asyncio
import sys
from datetime import datetime
from typing import List, Tuple

from scraper_config import settings
from scraper_logging import setup_logging
from scraper_sheets import SheetsClient
from scraper_web import EnviaScraper
from scraper_web_async import AsyncEnviaScraper
from scraper_credentials import load_credentials


def parse_arguments() -> argparse.Namespace:
    """
    Parsea argumentos de línea de comandos para el scraper.

    Returns:
        argparse.Namespace: Argumentos parseados
    """
    parser = argparse.ArgumentParser(
        description="Scraper de estados Interrapidísimo",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--start-row",
        type=int,
        default=2,
        help="Fila inicial (1-based, default: 2)"
    )

    parser.add_argument(
        "--end-row",
        type=int,
        default=None,
        help="Fila final (inclusiva, default: todas)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Límite de filas a procesar"
    )

    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Usar scraper asíncrono"
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Páginas concurrentes (default: 3)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Tamaño de batch (default: 5000)"
    )

    parser.add_argument(
        "--only-empty",
        action="store_true",
        help="Solo procesar filas sin estado web"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular sin escribir cambios"
    )

    return parser.parse_args()


def filter_records(
    records: List[dict],
    start_row: int,
    end_row: int | None,
    limit: int | None,
    only_empty: bool
) -> List[Tuple[int, str]]:
    """
    Filtra y prepara registros para procesamiento.

    Args:
        records: Lista de registros del spreadsheet
        start_row: Fila inicial (1-based)
        end_row: Fila final (inclusiva)
        limit: Límite de registros a procesar
        only_empty: Solo procesar si STATUS TRANSPORTADORA está vacío

    Returns:
        List[Tuple[int, str]]: Lista de (row_num, tracking_id)
    """
    items: List[Tuple[int, str]] = []

    for idx, record in enumerate(records, start=2):
        if idx < start_row:
            continue
        if end_row and idx > end_row:
            break
        if limit and len(items) >= limit:
            break

        tracking = str(record.get("ID TRACKING", "")).strip()
        if not tracking:
            continue

        # Verificar si solo procesar filas vacías
        current_status = str(
            record.get("STATUS TRANSPORTADORA", "")
        ).strip()
        if only_empty and current_status:
            continue

        items.append((idx, tracking))

    return items


def scrape_sync(
    sheets: SheetsClient,
    scraper: EnviaScraper,
    start_row: int,
    end_row: int | None,
    limit: int | None,
    only_empty: bool,
    dry_run: bool
) -> int:
    """
    Ejecuta scraping síncrono de estados.

    Args:
        sheets: Cliente de Google Sheets
        scraper: Scraper síncrono
        start_row: Fila inicial
        end_row: Fila final
        limit: Límite de filas
        only_empty: Solo procesar vacíos
        dry_run: Modo simulación

    Returns:
        int: Número de filas procesadas
    """
    logging.info("Iniciando scraping síncrono...")

    records = sheets.read_all_records()
    items = filter_records(records, start_row, end_row, limit, only_empty)

    if not items:
        logging.warning("No hay items para procesar")
        return 0

    processed = 0
    for idx, tracking in items:
        try:
            status = scraper.get_status(tracking)

            if status and not dry_run:
                # Solo guardar el estado crudo en STATUS TRANSPORTADORA
                sheets.update_cell(idx, "STATUS TRANSPORTADORA", status)

            logging.info(f"[{idx}] {tracking}: {status or 'VACIO'}")
            processed += 1

        except Exception as e:
            logging.error(f"Error procesando {tracking}: {e}")
            continue

    logging.info(f"Scraping completado: {processed} filas procesadas")
    return processed


async def scrape_async(
    sheets: SheetsClient,
    start_row: int,
    end_row: int | None,
    limit: int | None,
    concurrency: int,
    batch_size: int,
    only_empty: bool,
    dry_run: bool
) -> int:
    """
    Ejecuta scraping asíncrono de estados.

    Args:
        sheets: Cliente de Google Sheets
        start_row: Fila inicial
        end_row: Fila final
        limit: Límite de filas
        concurrency: Páginas concurrentes
        batch_size: Tamaño de batch
        only_empty: Solo procesar vacíos
        dry_run: Modo simulación

    Returns:
        int: Número de filas procesadas
    """
    logging.info("Iniciando scraping asíncrono...")

    records = sheets.read_all_records()
    items = filter_records(records, start_row, end_row, limit, only_empty)

    if not items:
        logging.warning("No hay items para procesar")
        return 0

    scraper = AsyncEnviaScraper(
        headless=settings.headless,
        max_concurrency=concurrency
    )

    try:
        await scraper.start()

        # Procesar en batches
        total_processed = 0
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            tracking_numbers = [tn for _, tn in batch]

            logging.info(f"Procesando batch: {len(batch)} items")
            results = await scraper.get_status_many(tracking_numbers)
            status_map = dict(results)

            if not dry_run:
                updates = []
                for idx, tn in batch:
                    status = status_map.get(tn, "")
                    if status:
                        updates.append((idx, status))

                # Actualizar en la columna STATUS TRANSPORTADORA
                sheets.batch_update_status(
                    updates,
                    column="STATUS TRANSPORTADORA"
                )

            total_processed += len(batch)
            logging.info(f"Progreso: {total_processed}/{len(items)}")

        logging.info(f"Scraping asíncrono completado: {total_processed} filas")
        return total_processed

    finally:
        await scraper.close()


def main() -> int:
    """
    Función principal de la app de scraping.

    Returns:
        int: Código de salida (0=éxito, 1=error)
    """
    args = parse_arguments()
    setup_logging()

    logging.info("=== SCRAPER APP INICIANDO ===")
    logging.info(f"Modo: {'Asíncrono' if args.use_async else 'Síncrono'}")
    logging.info(f"Rango: {args.start_row}-{args.end_row or 'fin'}")

    try:
        # Inicializar servicios
        credentials = load_credentials()
        sheets = SheetsClient(credentials, settings.spreadsheet_name)

        # Ejecutar scraping
        if args.use_async:
            processed = asyncio.run(
                scrape_async(
                    sheets,
                    args.start_row,
                    args.end_row,
                    args.limit,
                    args.concurrency,
                    args.batch_size,
                    args.only_empty,
                    args.dry_run
                )
            )
        else:
            scraper = EnviaScraper(headless=settings.headless)
            try:
                processed = scrape_sync(
                    sheets,
                    scraper,
                    args.start_row,
                    args.end_row,
                    args.limit,
                    args.only_empty,
                    args.dry_run
                )
            finally:
                scraper.close()

        logging.info(f"=== SCRAPER COMPLETADO: {processed} filas ===")
        return 0

    except KeyboardInterrupt:
        logging.warning("Proceso interrumpido por usuario")
        return 1

    except Exception as e:
        logging.exception(f"Error fatal: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
