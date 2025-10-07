"""
Módulo de gestión de credenciales para Google Services.

Este módulo centraliza la carga y configuración de credenciales de servicio
para acceder a Google Sheets y Google Drive API, evitando duplicación de código
y proporcionando un punto único de configuración.

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
from oauth2client.service_account import ServiceAccountCredentials
import logging


class CredentialsManager:
    """
    Gestor centralizado de credenciales para Google Services.

    Esta clase maneja la carga y configuración de credenciales de servicio
    de Google para acceder a las APIs de Sheets y Drive de forma segura.

    Attributes:
        SCOPES (list[str]): Lista de alcances de permisos requeridos para Google APIs
        _credentials: Instancia de credenciales cargadas (cache)
    """

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]

    _credentials: ServiceAccountCredentials | None = None

    @classmethod
    def load_credentials(cls, credentials_path: str = "credentials.json") -> ServiceAccountCredentials:
        """
        Carga las credenciales de servicio de Google desde archivo JSON.

        Este método implementa un patrón singleton para evitar cargar las credenciales
        múltiples veces durante la ejecución de la aplicación.

        Args:
            credentials_path (str): Ruta al archivo JSON de credenciales.
                                  Por defecto "credentials.json"

        Returns:
            ServiceAccountCredentials: Objeto de credenciales configurado con los scopes necesarios

        Raises:
            FileNotFoundError: Si el archivo de credenciales no existe
            ValueError: Si el archivo de credenciales tiene formato inválido

        Example:
            >>> creds = CredentialsManager.load_credentials()
            >>> drive_client = DriveClient(creds)
        """
        if cls._credentials is not None:
            logging.debug("Reutilizando credenciales cargadas previamente")
            return cls._credentials

        try:
            logging.info(f"Cargando credenciales desde: {credentials_path}")
            cls._credentials = ServiceAccountCredentials.from_json_keyfile_name(
                credentials_path, cls.SCOPES
            )
            logging.info("Credenciales cargadas exitosamente")
            return cls._credentials

        except FileNotFoundError as e:
            logging.error(
                f"Archivo de credenciales no encontrado: {credentials_path}")
            raise FileNotFoundError(
                f"No se pudo encontrar el archivo de credenciales: {credentials_path}") from e

        except Exception as e:
            logging.error(f"Error al cargar credenciales: {str(e)}")
            raise ValueError(
                f"Error al procesar credenciales: {str(e)}") from e

    @classmethod
    def get_credentials(cls) -> ServiceAccountCredentials:
        """
        Obtiene las credenciales cargadas o las carga si no existen.

        Método de conveniencia que garantiza que siempre se retornen credenciales válidas.

        Returns:
            ServiceAccountCredentials: Credenciales configuradas y listas para usar

        Example:
            >>> creds = CredentialsManager.get_credentials()
        """
        if cls._credentials is None:
            return cls.load_credentials()
        return cls._credentials

    @classmethod
    def reset_credentials(cls) -> None:
        """
        Resetea las credenciales cargadas forzando una nueva carga en el próximo acceso.

        Útil para casos donde las credenciales pueden haber cambiado durante la ejecución
        o para testing donde se necesita limpiar el estado.
        """
        logging.debug("Reseteando credenciales cargadas")
        cls._credentials = None


# Función de compatibilidad hacia atrás para código existente
def load_credentials() -> ServiceAccountCredentials:
    """
    Función de compatibilidad hacia atrás para código existente.

    Esta función mantiene la interfaz original mientras redirige al nuevo
    sistema de gestión de credenciales centralizado.

    Returns:
        ServiceAccountCredentials: Credenciales de servicio configuradas

    Deprecated:
        Usar CredentialsManager.get_credentials() directamente
    """
    return CredentialsManager.get_credentials()
