"""
Gestión de credenciales para App Scraper.

Responsabilidades:
- Cargar credentials.json desde directorio local de la app
- Autenticar con Google APIs
- Proveer credenciales válidas

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import os
from oauth2client.service_account import ServiceAccountCredentials


def load_credentials(credentials_path: str = None):
    """
    Carga credenciales de Google desde credentials.json LOCAL.
    
    Args:
        credentials_path: Ruta al archivo de credenciales
                         (default: credentials.json en carpeta de la app)
    
    Returns:
        ServiceAccountCredentials: Credenciales configuradas
    """
    if credentials_path is None:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_path = os.path.join(app_dir, "credentials.json")
    
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"Archivo de credenciales no encontrado: {credentials_path}\n"
            "Copia tu credentials.json a la carpeta app_scrapper/"
        )
    
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    return ServiceAccountCredentials.from_json_keyfile_name(
        credentials_path,
        scope
    )
