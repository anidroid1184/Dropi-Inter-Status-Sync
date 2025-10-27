"""Credentials Manager para APP COMPARER.

Carga credentials.json desde el directorio local de la app.
"""
import os
import logging
from typing import Optional
from oauth2client.service_account import ServiceAccountCredentials


def load_service_account_credentials(path: str) -> Optional[ServiceAccountCredentials]:
    """Carga credenciales de servicio desde un archivo JSON.

    Args:
        path: Ruta al credentials.json

    Returns:
        ServiceAccountCredentials o None si no existe/ocurre error
    """
    if not os.path.exists(path):
        logging.error(f"Credentials not found at: {path}")
        return None

    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(path, scopes)
        logging.info("Service account credentials loaded")
        return creds
    except Exception as e:
        logging.exception(f"Error loading service account credentials: {e}")
        return None
