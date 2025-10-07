"""
Paquete de utilidades del sistema de tracking Dropi-Inter.

Este paquete contiene módulos utilitarios que proporcionan funcionalidades
comunes utilizadas en todo el sistema, incluyendo gestión de credenciales,
operaciones batch, constantes del sistema y utilidades de retry.

Módulos disponibles:
    - credentials_manager: Gestión centralizada de credenciales Google
    - batch_operations: Operaciones batch optimizadas para Google Sheets
    - constants: Constantes del sistema centralizadas
    - checkpoints: Gestión de puntos de control para procesamiento
    - retry: Utilidades de reintentos con backoff exponencial

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from .credentials_manager import CredentialsManager, load_credentials
from .batch_operations import BatchOperations, _flush_batch
from .constants import (
    ColumnHeaders,
    BatchConfig,
    StatusValues,
    LogConfig,
    ValidationConstants
)

__all__ = [
    # Gestión de credenciales
    "CredentialsManager",
    "load_credentials",

    # Operaciones batch
    "BatchOperations",
    "_flush_batch",

    # Constantes del sistema
    "ColumnHeaders",
    "BatchConfig",
    "StatusValues",
    "LogConfig",
    "ValidationConstants",
]
