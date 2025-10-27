"""
Google Drive Uploader para APP MAKE DAILY REPORT.

Cliente para subir archivos Excel a Google Drive.

Responsabilidades:
- Subir archivos a carpeta específica en Drive
- Logging de operaciones

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import os
import logging

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials


class DriveUploader:
    """
    Cliente para subir archivos a Google Drive.
    
    Attributes:
        credentials: Credenciales de Google API
        folder_id: ID de carpeta destino en Drive
        service: Servicio de Drive API
    """
    
    def __init__(
        self,
        credentials: ServiceAccountCredentials,
        folder_id: str
    ):
        """
        Inicializa el uploader de Drive.
        
        Args:
            credentials: Credenciales de Google API
            folder_id: ID de carpeta destino
        """
        self.credentials = credentials
        self.folder_id = folder_id
        
        # Construir servicio de Drive
        self.service = build('drive', 'v3', credentials=credentials)
        
        logging.info(f"Drive service inicializado para folder: {folder_id}")
    
    def upload(self, file_path: str) -> str:
        """
        Sube un archivo a Google Drive.
        
        Args:
            file_path: Ruta del archivo local a subir
            
        Returns:
            str: ID del archivo en Drive
            
        Raises:
            FileNotFoundError: Si el archivo no existe
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        filename = os.path.basename(file_path)
        
        # Metadata del archivo
        file_metadata = {
            'name': filename,
            'parents': [self.folder_id]
        }
        
        # Media upload
        mimetype = (
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        )
        media = MediaFileUpload(
            file_path,
            mimetype=mimetype,
            resumable=True
        )
        
        # Subir
        logging.info(f"Subiendo {filename} a Drive...")
        
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        web_link = file.get('webViewLink')
        
        logging.info(f"Archivo subido: {file_id}")
        logging.info(f"Link: {web_link}")
        
        return file_id
