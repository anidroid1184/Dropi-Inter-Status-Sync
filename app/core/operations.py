"""
Módulo de operaciones principales del sistema de tracking.

Este módulo contiene las funciones principales para procesar datos de Drive,
ejecutar scraping de estados y coordinar las operaciones de actualización
de la hoja de cálculo principal.

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import logging
import asyncio
import threading
from typing import List, Dict, Any

from .app_setup import AppConfig, ServiceContainer
from ..services.tracker_service import TrackerService
from ..utils.constants import ColumnHeaders, LogConfig, BatchConfig
from ..utils.batch_operations import BatchOperations
from ..web.inter_scraper_async import AsyncInterScraper


def process_drive_data(
    config: AppConfig,
    container: ServiceContainer
) -> int:
    """
    Procesa datos desde Google Drive y actualiza la hoja de tracking.

    Descarga el archivo más reciente desde el folder de Drive configurado,
    lee los datos del Excel, y agrega filas nuevas a la hoja de tracking
    evitando duplicados.

    Args:
        config (AppConfig): Configuración de la aplicación
        container (ServiceContainer): Contenedor de servicios

    Returns:
        int: Número de filas nuevas agregadas

    Raises:
        Exception: Si hay errores procesando datos de Drive
    """
    if config.skip_drive:
        logging.info("Omitiendo procesamiento de Drive según configuración")
        return 0

    try:
        logging.info("Iniciando procesamiento de datos desde Drive...")

        # Obtener archivo más reciente
        latest_file = container.drive.latest_file(settings.drive_folder_id)
        if not latest_file:
            logging.error("No se encontró archivo más reciente en Drive")
            return 0

        logging.info(f"Procesando archivo: {latest_file['name']}")

        # Leer datos del archivo Excel
        source_data = _read_source_data(container.drive, latest_file["id"])
        if not source_data:
            logging.warning("No se encontraron datos válidos en el archivo")
            return 0

        # Actualizar hoja de tracking
        added_rows = _update_tracking_sheet(container.sheets, source_data)

        if added_rows > 0:
            # Registrar evento en log de auditoría
            _log_drive_ingestion_event(added_rows)

        logging.info(
            f"Procesamiento de Drive completado: {added_rows} filas agregadas")
        return added_rows

    except Exception as e:
        logging.error(f"Error procesando datos de Drive: {str(e)}")
        raise


def execute_status_scraping(
    config: AppConfig,
    container: ServiceContainer
) -> None:
    """
    Ejecuta el scraping de estados según la configuración.

    Determina si usar scraping síncrono o asíncrono basado en la
    configuración y ejecuta el proceso correspondiente.

    Args:
        config (AppConfig): Configuración de la aplicación
        container (ServiceContainer): Contenedor de servicios
    """
    if config.dry_run:
        logging.info("Modo dry-run activado: omitiendo scraping de estados")
        return

    try:
        if config.use_async:
            logging.info("Ejecutando scraping asíncrono...")
            _execute_async_scraping(config, container)
        else:
            logging.info("Ejecutando scraping síncrono...")
            _execute_sync_scraping(config, container)

        logging.info("Scraping de estados completado exitosamente")

    except Exception as e:
        logging.error(f"Error durante scraping de estados: {str(e)}")
        raise


def execute_post_compare_analysis(
    config: AppConfig,
    container: ServiceContainer
) -> None:
    """
    Ejecuta análisis de comparación post-scraping si está configurado.

    Compara estados de Dropi vs Tracking y actualiza columnas COINCIDEN
    y ALERTA en toda la hoja después del scraping.

    Args:
        config (AppConfig): Configuración de la aplicación
        container (ServiceContainer): Contenedor de servicios
    """
    if not config.post_compare:
        logging.info("Análisis post-comparación omitido según configuración")
        return

    try:
        logging.info("Iniciando análisis de comparación post-scraping...")

        from ..app import compare_statuses_batched  # Import local para evitar circular

        # Comparar toda la hoja independientemente del rango de scraping
        compare_statuses_batched(
            container.sheets,
            start_row=2,  # Siempre desde fila 2 (después de headers)
            end_row=None,  # Hasta el final
            batch_size=config.compare_batch_size,
        )

        logging.info("Análisis de comparación completado exitosamente")

    except Exception as e:
        logging.error(f"Error en análisis post-comparación: {str(e)}")
        raise


def generate_daily_report(container: ServiceContainer) -> None:
    """
    Genera el reporte diario basado en el estado actual de la hoja.

    Crea o reemplaza el reporte diario con todas las filas que tienen
    alertas activas, proporcionando una vista consolidada de problemas.

    Args:
        container (ServiceContainer): Contenedor de servicios
    """
    try:
        logging.info("Generando reporte diario...")

        report_name = container.sheets.create_or_append_daily_report(
            [],
            prefix=settings.daily_report_prefix
        )

        logging.info(f"Reporte diario generado exitosamente: {report_name}")

    except Exception as e:
        logging.error(f"Error generando reporte diario: {str(e)}")
        raise


# ==================== FUNCIONES AUXILIARES PRIVADAS ====================

def _read_source_data(
    drive_client,
    file_id: str
) -> List[Dict[str, Any]]:
    """Lee y procesa datos del archivo Excel desde Drive."""
    import pandas as pd
    import io

    content = drive_client.download_bytes(file_id)
    if not content:
        return []

    # Leer Excel con pandas
    df = pd.read_excel(
        io.BytesIO(content),
        dtype={ColumnHeaders.ID_TRACKING: str}
    )

    # Normalizar nombres de columnas
    df.columns = [col.strip().upper() for col in df.columns]

    # Validar columna requerida
    if ColumnHeaders.ID_TRACKING not in df.columns:
        logging.error(
            f"Columna requerida '{ColumnHeaders.ID_TRACKING}' no encontrada")
        return []

    # Filtrar filas válidas
    df = df[df[ColumnHeaders.ID_TRACKING].notna()]

    # Procesar y deduplicar
    processed_data = []
    seen_guias = set()

    for _, row in df.iterrows():
        guia = str(row.get(ColumnHeaders.ID_TRACKING, "")).strip()
        if not guia or guia in seen_guias:
            continue

        seen_guias.add(guia)
        processed_data.append({
            ColumnHeaders.ID_DROPI: row.get("ID", ""),
            ColumnHeaders.ID_TRACKING: guia,
            ColumnHeaders.STATUS_DROPI: row.get("ESTATUS", ""),
        })

    logging.info(f"Procesadas {len(processed_data)} filas desde Excel")
    return processed_data


def _update_tracking_sheet(
    sheets_client,
    source_data: List[Dict[str, Any]]
) -> int:
    """Actualiza la hoja de tracking con datos nuevos."""
    existing_records = sheets_client.read_main_records()
    existing_guias = {
        str(record.get(ColumnHeaders.ID_TRACKING, "")).strip()
        for record in existing_records
        if record.get(ColumnHeaders.ID_TRACKING)
    }

    new_rows = TrackerService.prepare_new_rows(source_data, existing_guias)
    added_count = sheets_client.append_new_rows(new_rows)

    return added_count


def _log_drive_ingestion_event(count: int) -> None:
    """Registra evento de ingesta de Drive en log de auditoría."""
    from ..app import _init_status_log, _append_event_log

    status_log_path = _init_status_log()
    _append_event_log(status_log_path, "Añadido al drive", str(count))


def _execute_sync_scraping(
    config: AppConfig,
    container: ServiceContainer
) -> None:
    """Ejecuta scraping síncrono usando InterScraper."""
    from ..app import update_statuses  # Import local para evitar circular

    update_statuses(
        container.sheets,
        container.scraper,
        start_row=config.start_row,
        end_row=config.end_row,
        limit=config.limit
    )


def _execute_async_scraping(
    config: AppConfig,
    container: ServiceContainer
) -> None:
    """Ejecuta scraping asíncrono usando AsyncInterScraper."""
    from ..app import update_statuses_async  # Import local para evitar circular

    # Usar runner de corrutina thread-safe
    def _run_coroutine_safely(coro):
        """Ejecuta corrutina de forma thread-safe."""
        result_container = {"exception": None}

        def _runner():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(coro)
            except Exception as e:
                result_container["exception"] = e
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        try:
            # Verificar si hay loop activo
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop and running_loop.is_running():
            # Ejecutar en thread separado si hay loop activo
            thread = threading.Thread(target=_runner, daemon=True)
            thread.start()
            thread.join()

            if result_container["exception"]:
                raise result_container["exception"]
        else:
            # Ejecutar directamente si no hay loop activo
            asyncio.run(coro)

    # Ejecutar scraping asíncrono
    _run_coroutine_safely(
        update_statuses_async(
            container.sheets,
            settings.headless,
            start_row=config.start_row,
            end_row=config.end_row,
            limit=config.limit,
            max_concurrency=config.max_concurrency,
            batch_size=config.batch_size,
        )
    )
