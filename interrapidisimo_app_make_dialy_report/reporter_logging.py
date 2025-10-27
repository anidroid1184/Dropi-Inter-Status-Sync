"""
Logging Setup para APP MAKE DAILY REPORT.

Configura logging en el directorio local de la app.

Responsabilidades:
- Crear directorio logs/ local si no existe
- Configurar formato de logs
- Rotación de archivos por fecha

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import os
import logging
from datetime import datetime


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configura el sistema de logging para la app de reportes.
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
    """
    # Directorio de logs local a esta app
    app_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(app_dir, "logs")
    
    # Crear directorio si no existe
    os.makedirs(log_dir, exist_ok=True)
    
    # Archivo de log con fecha
    log_file = os.path.join(
        log_dir,
        f"reporter_{datetime.now().strftime('%Y-%m-%d')}.log"
    )
    
    # Configurar formato
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(funcName)s:%(lineno)d - %(message)s"
    )
    
    # Configurar handlers
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logging.info(f"Logging configurado: {log_file}")
