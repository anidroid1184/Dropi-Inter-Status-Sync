"""
APP SCRAPER COORDINADORA - Sistema de Scraping de Estados Coordinadora

Aplicación independiente para scraping de estados de tracking desde
el portal web de Coordinadora.

Responsabilidades:
- Scraping web de estados de Coordinadora mediante acceso directo a URL
- Procesamiento individual de guías (no soporta batch)
- Extracción del estado crudo exactamente como aparece en la web
- Actualización solo de columna STATUS TRANSPORTADORA con texto sin normalizar
- Logging de operaciones de scraping
- Gestión de reintentos y errores

IMPORTANTE: Este scraper NO normaliza estados. Guarda el texto crudo de la web.
Ejemplos de salida:
  - "Entregado"
  - "En terminal destino"
  - "En tránsito"

La normalización y comparación se realiza en app_comparer.

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
Versión: 2.0.0
"""

from __future__ import annotations
import argparse
import logging
import sys
from typing import List, Tuple

from scraper_config import settings
from scraper_logging import setup_logging
from scraper_sheets import SheetsClient
from scraper_web_coordinadora import CoordinadoraScraper
from scraper_credentials import load_credentials
import time

# Tiempo por defecto entre batches/items cuando --time-test está
# activo (segundos)
TIMEOUT_TEST = int(
    getattr(__import__('os'), 'environ', {}).get('TIMEOUT_TEST', 5)
)


def parse_arguments() -> argparse.Namespace:
    """
    Parsea argumentos de línea de comandos para el scraper.

    Returns:
        argparse.Namespace: Argumentos parseados
    """
    parser = argparse.ArgumentParser(
        description="Scraper de estados Coordinadora",
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
        "--only-empty",
        action="store_true",
        help="Solo procesar filas sin estado web"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular sin escribir cambios"
    )

    parser.add_argument(
        "--time-test",
        dest="time_test",
        action="store_true",
        help=(
            "Activar espera entre batches/items para debugging "
            "(TIMEOUT_TEST)"
        )
    )

    parser.add_argument(
        "--time-test-seconds",
        dest="time_test_seconds",
        type=int,
        default=None,
        help=(
            "Segundos a esperar entre batches/items cuando --time-test "
            "está activo (override de TIMEOUT_TEST)"
        )
    )

    parser.add_argument(
        "--simple",
        dest="use_simple",
        action="store_true",
        help=(
            "Usar scraper simple (requests + BeautifulSoup) en vez "
            "de Playwright"
        ),
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
    scraper: CoordinadoraScraper,
    start_row: int,
    end_row: int | None,
    limit: int | None,
    only_empty: bool,
    dry_run: bool,
    time_test_enabled: bool = False,
    time_test_seconds: int | None = None,
) -> int:
    """
    Ejecuta scraping síncrono de estados de Coordinadora.

    Args:
        sheets: Cliente de Google Sheets
        scraper: Scraper de Coordinadora
        start_row: Fila inicial
        end_row: Fila final
        limit: Límite de filas
        only_empty: Solo procesar vacíos
        dry_run: Modo simulación
        time_test_enabled: Si está activado el modo time-test
        time_test_seconds: Segundos a esperar entre items en time-test

    Returns:
        int: Número de filas procesadas
    """
    logging.info("Iniciando scraping de Coordinadora...")

    records = sheets.read_all_records()
    items = filter_records(records, start_row, end_row, limit, only_empty)

    if not items:
        logging.warning("No hay items para procesar")
        return 0

    processed = 0
    saved_count = 0

    try:
        for idx, tracking in items:
            try:
                # Usar el scraper de Playwright
                status = scraper.get_status(tracking)

                if status and not dry_run:
                    # Guardar inmediatamente el estado
                    sheets.update_cell(idx, "STATUS TRANSPORTADORA", status)
                    saved_count += 1
                    logging.info(
                        f"[{idx}] {tracking}: {status} - ✓ Guardado"
                    )
                else:
                    logging.info(f"[{idx}] {tracking}: {status or 'VACIO'}")

                processed += 1

                # Si la opción de time_test está activada, esperar
                if time_test_enabled:
                    timeout_val = time_test_seconds or TIMEOUT_TEST
                    logging.debug(
                        "--time-test activo: sleeping %s s after item %s",
                        timeout_val,
                        idx,
                    )
                    time.sleep(timeout_val)
            except Exception as e:
                logging.error(f"Error procesando {tracking}: {e}")
                continue

    except KeyboardInterrupt:
        logging.warning("\n⚠️  Interrupción detectada por el usuario")
        logging.info(
            f"✓ Progreso guardado: {saved_count} de {processed} "
            f"filas procesadas"
        )
        raise

    logging.info(
        f"Scraping completado: {processed} filas procesadas, "
        f"{saved_count} guardadas"
    )
    return processed


def main() -> int:
    """
    Función principal de la app de scraping de Coordinadora.

    Returns:
        int: Código de salida (0=éxito, 1=error)
    """
    args = parse_arguments()
    setup_logging()

    logging.info("=== SCRAPER COORDINADORA INICIANDO ===")
    logging.info("Modo: Síncrono (Playwright)")
    logging.info(f"Rango: {args.start_row}-{args.end_row or 'fin'}")
    logging.info(f"BASE_URL: {settings.base_url}")

    try:
        # Inicializar servicios
        credentials = load_credentials()
        sheets = SheetsClient(credentials, settings.spreadsheet_name)

        # Inicializar scraper de Coordinadora con Playwright
        scraper = CoordinadoraScraper(
            headless=settings.headless,
            base_url=settings.base_url
        )

        try:
            # Ejecutar scraping
            processed = scrape_sync(
                sheets,
                scraper,
                args.start_row,
                args.end_row,
                args.limit,
                args.only_empty,
                args.dry_run,
                time_test_enabled=args.time_test,
                time_test_seconds=args.time_test_seconds,
            )
        finally:
            scraper.close()

        logging.info(f"=== SCRAPER COMPLETADO: {processed} filas ===")
        return 0

    except KeyboardInterrupt:
        logging.warning("\n" + "="*60)
        logging.warning("⚠️  PROCESO INTERRUMPIDO POR USUARIO")
        logging.warning("="*60)
        logging.info(
            "✓ Los resultados obtenidos hasta el momento "
            "ya han sido guardados"
        )
        logging.info(
            "💡 Puedes reanudar el proceso ejecutando el comando "
            "con --only-empty"
        )
        logging.warning("="*60)
        return 130  # Exit code estándar para SIGINT

    except Exception as e:
        logging.error("\n" + "="*60)
        logging.error("❌ ERROR FATAL")
        logging.error("="*60)
        logging.exception(f"Error: {e}")
        logging.info(
            "💡 Revisa los logs para más detalles. "
            "Los resultados guardados hasta el momento se mantienen."
        )
        logging.error("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
