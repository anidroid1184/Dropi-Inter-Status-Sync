"""
Credentials Manager para APP MAKE DAILY REPORT.

Carga credentials.json desde el directorio local de la app.

Responsabilidades:
- Buscar credentials.json en directorio de la app
- Autenticar con Google APIs
- Proveer credenciales válidas

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import os
import logging

from oauth2client.service_account import ServiceAccountCredentials


def load_credentials() -> ServiceAccountCredentials:
    """
    Carga credenciales de Google desde archivo local credentials.json.
    
    Returns:
        ServiceAccountCredentials: Credenciales autenticadas
        
    Raises:
        FileNotFoundError: Si no se encuentra credentials.json
    """
    # Buscar credentials.json en el directorio de esta app
    app_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(app_dir, "credentials.json")
    
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"No se encontró credentials.json en {app_dir}\n"
            "Esta app es independiente y necesita su propio "
            "archivo credentials.json\n"
            "Por favor copia el archivo de credenciales de Google "
            "a este directorio."
        )
    
    # Scopes necesarios
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Autenticar
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        credentials_path,
        scopes
    )
    
    logging.info("Credenciales cargadas correctamente")
    return credentials
