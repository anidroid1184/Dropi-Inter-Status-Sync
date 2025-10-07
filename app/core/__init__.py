"""
Módulo core del sistema de tracking Dropi-Inter.

Este paquete contiene los componentes centrales de la aplicación,
incluyendo configuración, inicialización de servicios y operaciones principales.

Módulos:
    - app_setup: Configuración y setup inicial de la aplicación  
    - operations: Operaciones principales de procesamiento

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from .app_setup import (
    AppConfig,
    ServiceContainer,
    parse_command_line_arguments,
    initialize_application,
    create_service_container
)

from .operations import (
    process_drive_data,
    execute_status_scraping,
    execute_post_compare_analysis,
    generate_daily_report
)

__all__ = [
    # Configuración y setup
    "AppConfig",
    "ServiceContainer",
    "parse_command_line_arguments",
    "initialize_application",
    "create_service_container",

    # Operaciones principales
    "process_drive_data",
    "execute_status_scraping",
    "execute_post_compare_analysis",
    "generate_daily_report",
]
