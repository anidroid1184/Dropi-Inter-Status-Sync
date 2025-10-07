"""
Módulo de configuración y setup de servicios.

Este módulo maneja la configuración inicial de la aplicación,
incluyendo la configuración de argumentos, logging, y la
inicialización de servicios principales.

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import argparse
import logging
from typing import NamedTuple

from ..logging_setup import setup_logging
from ..config import settings
from ..utils.credentials_manager import CredentialsManager
from ..services.drive_client import DriveClient
from ..services.sheets_client import SheetsClient
from ..web.inter_scraper import InterScraper
from ..utils.constants import BatchConfig


class AppConfig(NamedTuple):
    """
    Configuración de la aplicación parseada desde argumentos CLI.

    Attributes:
        start_row (int): Fila inicial para procesamiento (1-based)
        end_row (int | None): Fila final para procesamiento (inclusiva)
        limit (int | None): Límite de filas a procesar
        dry_run (bool): Ejecutar sin escribir cambios
        skip_drive (bool): Omitir ingesta desde Drive
        use_async (bool): Usar scraper asíncrono con Playwright
        max_concurrency (int): Páginas browser concurrentes máximas
        batch_size (int): Tamaño de batch para scraping asíncrono
        post_compare (bool): Ejecutar comparación después del scraping
        compare_batch_size (int): Tamaño de batch para comparación
    """
    start_row: int
    end_row: int | None
    limit: int | None
    dry_run: bool
    skip_drive: bool
    use_async: bool
    max_concurrency: int
    batch_size: int
    post_compare: bool
    compare_batch_size: int


class ServiceContainer(NamedTuple):
    """
    Contenedor de servicios inicializados de la aplicación.

    Attributes:
        drive (DriveClient): Cliente para Google Drive
        sheets (SheetsClient): Cliente para Google Sheets
        scraper (InterScraper): Scraper para Interrapidísimo
    """
    drive: DriveClient
    sheets: SheetsClient
    scraper: InterScraper


def parse_command_line_arguments() -> AppConfig:
    """
    Parsea argumentos de línea de comandos y retorna configuración.

    Configura y ejecuta el parser de argumentos CLI, validando
    valores y estableciendo valores por defecto apropiados.

    Returns:
        AppConfig: Configuración parseada de la aplicación

    Raises:
        SystemExit: Si los argumentos son inválidos
    """
    parser = argparse.ArgumentParser(
        description="Sistema de tracking Interrapidísimo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s --start-row 100 --limit 50
  %(prog)s --async --max-concurrency 5 --batch-size 1000
  %(prog)s --dry-run --post-compare
        """
    )

    # Argumentos de rango de procesamiento
    parser.add_argument(
        "--start-row",
        type=int,
        default=2,
        help="Fila inicial para procesamiento (1-based, default: 2)"
    )

    parser.add_argument(
        "--end-row",
        type=int,
        default=None,
        help="Fila final para procesamiento (inclusiva, default: todas)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Límite máximo de filas a procesar (default: sin límite)"
    )

    # Argumentos de modo de ejecución
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecutar sin escribir cambios (modo simulación)"
    )

    parser.add_argument(
        "--skip-drive",
        action="store_true",
        help="Omitir ingesta desde Drive, solo actualizar estados existentes"
    )

    # Argumentos de scraping asíncrono
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Usar scraper asíncrono Playwright con concurrencia"
    )

    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=BatchConfig.DEFAULT_MAX_CONCURRENCY,
        help=f"Páginas browser concurrentes máximas "
        f"(default: {BatchConfig.DEFAULT_MAX_CONCURRENCY})"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=BatchConfig.ASYNC_BATCH_SIZE,
        help=f"Tamaño de batch para scraping asíncrono "
        f"(default: {BatchConfig.ASYNC_BATCH_SIZE})"
    )

    # Argumentos de post-procesamiento
    parser.add_argument(
        "--post-compare",
        action="store_true",
        help="Ejecutar comparación (COINCIDEN/ALERTA) después del scraping"
    )

    parser.add_argument(
        "--compare-batch-size",
        type=int,
        default=BatchConfig.COMPARE_BATCH_SIZE,
        help=f"Tamaño de batch para comparación "
        f"(default: {BatchConfig.COMPARE_BATCH_SIZE})"
    )

    args = parser.parse_args()

    # Validaciones básicas
    if args.start_row < 1:
        parser.error("--start-row debe ser >= 1")

    if args.end_row is not None and args.end_row < args.start_row:
        parser.error("--end-row debe ser >= --start-row")

    if args.limit is not None and args.limit < 1:
        parser.error("--limit debe ser >= 1")

    if args.max_concurrency < 1:
        parser.error("--max-concurrency debe ser >= 1")

    if args.batch_size < 1:
        parser.error("--batch-size debe ser >= 1")

    logging.info("Configuración CLI parseada exitosamente")
    logging.info(f"Rango: filas {args.start_row}-{args.end_row or 'fin'}")
    if args.limit:
        logging.info(f"Límite: {args.limit} filas")
    logging.info(f"Modo: {'asíncrono' if args.use_async else 'síncrono'}")

    return AppConfig(
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
        dry_run=args.dry_run,
        skip_drive=args.skip_drive,
        use_async=args.use_async,
        max_concurrency=args.max_concurrency,
        batch_size=args.batch_size,
        post_compare=args.post_compare,
        compare_batch_size=args.compare_batch_size
    )


def initialize_application() -> None:
    """
    Inicializa el sistema de logging y configuración básica.

    Configura el logging según las especificaciones del sistema
    y registra el inicio de la aplicación.
    """
    setup_logging()
    logging.info("=== INICIO DEL SISTEMA DE TRACKING DROPI-INTER ===")
    logging.info(f"Versión: 2.0.0 (Refactorizada)")
    logging.info(f"Modo headless: {settings.headless}")
    logging.info(f"Spreadsheet: {settings.spreadsheet_name}")


def create_service_container() -> ServiceContainer:
    """
    Crea e inicializa todos los servicios principales de la aplicación.

    Establece conexiones con Google Drive, Google Sheets, y 
    configura el scraper de Interrapidísimo con las credenciales apropiadas.

    Returns:
        ServiceContainer: Contenedor con todos los servicios inicializados

    Raises:
        Exception: Si hay errores al inicializar algún servicio
    """
    try:
        logging.info("Inicializando servicios principales...")

        # Cargar credenciales
        credentials = CredentialsManager.get_credentials()
        logging.info("Credenciales Google cargadas exitosamente")

        # Inicializar clientes Google
        drive_client = DriveClient(credentials)
        sheets_client = SheetsClient(credentials, settings.spreadsheet_name)
        logging.info("Clientes Google Drive y Sheets inicializados")

        # Inicializar scraper
        scraper = InterScraper(headless=settings.headless)
        logging.info(
            f"Scraper Interrapidísimo inicializado (headless: {settings.headless})")

        container = ServiceContainer(
            drive=drive_client,
            sheets=sheets_client,
            scraper=scraper
        )

        logging.info("Todos los servicios inicializados correctamente")
        return container

    except Exception as e:
        logging.error(f"Error inicializando servicios: {str(e)}")
        raise
