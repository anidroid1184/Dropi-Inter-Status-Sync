"""
Constantes del sistema de tracking Dropi-Inter.

Este módulo centraliza todas las constantes utilizadas en la aplicación,
incluyendo headers de columnas, configuraciones de batch, y valores por defecto.
Esto evita la duplicación de valores mágicos y facilita el mantenimiento.

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
from typing import List


class ColumnHeaders:
    """
    Definiciones de headers de columnas para Google Sheets.

    Centraliza todos los nombres de columnas utilizados en las hojas de cálculo
    para evitar inconsistencias y duplicación de strings.
    """

    # Headers principales del sistema
    ID_DROPI = "ID DROPI"
    ID_TRACKING = "ID TRACKING"
    STATUS_DROPI = "STATUS DROPI"
    STATUS_TRACKING = "STATUS TRACKING"
    STATUS_INTERRAPIDISIMO = "STATUS INTERRAPIDISIMO"
    ALERTA = "ALERTA"
    COINCIDEN = "COINCIDEN"
    FECHA_VERIFICACION = "FECHA VERIFICACIÓN"

    # Conjuntos de headers para diferentes operaciones
    BASIC_HEADERS: List[str] = [
        ID_DROPI,
        ID_TRACKING,
        STATUS_DROPI,
        STATUS_TRACKING,
        ALERTA,
        STATUS_INTERRAPIDISIMO
    ]

    EXTENDED_HEADERS: List[str] = [
        ID_DROPI,
        ID_TRACKING,
        STATUS_DROPI,
        STATUS_TRACKING,
        COINCIDEN,
        ALERTA,
        STATUS_INTERRAPIDISIMO
    ]

    REPORT_HEADERS: List[str] = [
        ID_TRACKING,
        STATUS_DROPI,
        STATUS_TRACKING,
        FECHA_VERIFICACION
    ]


class BatchConfig:
    """
    Configuraciones para operaciones batch y procesamiento masivo.

    Centraliza los valores de configuración para optimizar el rendimiento
    y respetar los límites de las APIs externas.
    """

    # Tamaños de batch para diferentes operaciones
    DEFAULT_BATCH_SIZE = 200           # Batch por defecto para actualizaciones
    ASYNC_BATCH_SIZE = 5000           # Batch para scraping asíncrono
    COMPARE_BATCH_SIZE = 5000         # Batch para comparación de estados
    API_CHUNK_SIZE = 100              # Chunk para API de Google Sheets

    # Configuraciones de concurrencia
    DEFAULT_MAX_CONCURRENCY = 3       # Páginas browser concurrentes
    DEFAULT_TIMEOUT_MS = 30000        # Timeout por defecto en ms

    # Configuraciones de reintentos y delays
    DEFAULT_RETRIES = 2               # Reintentos por defecto
    BATCH_SLEEP_SECONDS = 20.0        # Pausa entre batches

    # Rate limiting
    DEFAULT_RPS = 0.8                 # Requests por segundo por defecto


class StatusValues:
    """
    Valores estándar para estados y alertas del sistema.

    Define los valores canónicos utilizados para estados de tracking
    y valores de alerta en todo el sistema.
    """

    # Estados normalizados del sistema
    ENTREGADO = "ENTREGADO"
    EN_TRANSITO = "EN_TRANSITO"
    PENDIENTE = "PENDIENTE"
    DEVOLUCION = "DEVOLUCION"
    EN_AGENCIA = "EN_AGENCIA"
    GUIA_GENERADA = "GUIA_GENERADA"

    # Valores de alerta
    ALERT_TRUE = "TRUE"
    ALERT_FALSE = "FALSE"

    # Valores de coincidencia
    COINCIDE_TRUE = "TRUE"
    COINCIDE_FALSE = "FALSE"

    # Estados que permiten consulta web
    QUERYABLE_STATES = {
        GUIA_GENERADA,
        PENDIENTE,
        "EN_PROCESAMIENTO",
        "EN_BODEGA_TRANSPORTADORA",
        EN_TRANSITO,
        "EN_BODEGA_DESTINO",
        "EN_REPARTO",
        "INTENTO_DE_ENTREGA",
        "NOVEDAD",
        "REEXPEDICION",
        "REENVIO",
        EN_AGENCIA,
    }

    # Estados terminales
    TERMINAL_STATES = {ENTREGADO, DEVOLUCION}


class LogConfig:
    """
    Configuración para sistema de logging y auditoría.

    Define las configuraciones estándar para logging de eventos,
    archivos de auditoría y seguimiento de operaciones.
    """

    # Nombres de archivos y directorios
    LOGS_DIR = "logs"
    STATUS_LOG_PREFIX = "statuses_"
    STATUS_CATALOG_FILE = "status_catalog.json"

    # Headers para archivos CSV de auditoría
    STATUS_LOG_HEADERS = [
        "timestamp",
        "tracking_number",
        "dropi_raw",
        "dropi_norm",
        "web_raw",
        "web_norm",
        "alerta",
        "via",
        "new_status",
    ]

    # Formatos de fecha y tiempo
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    FILE_DATE_FORMAT = "%Y%m%d"


class ValidationConstants:
    """
    Constantes para validación de datos y reglas de negocio.

    Define valores utilizados en validaciones, filtros y 
    reglas de negocio del sistema.
    """

    # Valores considerados como verdaderos en comparaciones
    TRUTHY_VALUES = {"TRUE", "VERDADERO", "SI", "SÍ", "YES", "1"}

    # Valores considerados como falsos en comparaciones
    FALSY_VALUES = {"FALSE", "FALSO", "NO", "0"}

    # Extensiones de archivo soportadas
    SUPPORTED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}

    # Configuraciones de validación
    MIN_TRACKING_LENGTH = 3           # Longitud mínima número tracking
    MAX_TRACKING_LENGTH = 50          # Longitud máxima número tracking
