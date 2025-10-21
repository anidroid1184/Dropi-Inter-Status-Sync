"""
Configuración de la App Scraper.

Carga configuración desde variables de entorno LOCALES (.env en carpeta app).

Responsabilidades:
- Cargar configuración desde .env local
- Validar parámetros
- Proveer acceso a configuración de forma centralizada

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Cargar .env de la carpeta de la app scraper
app_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(app_dir, '.env')
load_dotenv(env_path)


@dataclass(frozen=True)
class ScraperSettings:
    """Configuración del scraper."""
    
    spreadsheet_name: str = os.getenv("SPREADSHEET_NAME", "seguimiento")
    headless: bool = os.getenv("HEADLESS", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = ScraperSettings()
