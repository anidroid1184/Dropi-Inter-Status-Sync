"""
Configuración de APP COMPARER.

Carga variables de entorno desde el archivo .env local del app.

Responsabilidades:
- Cargar configuración desde .env local
- Validar parámetros requeridos
- Proveer acceso a configuración de forma centralizada

Autor: Sistema de Tracking Dropi-Inter
Fecha: Octubre 2025
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv


# Cargar .env desde el directorio de esta app
app_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(app_dir, '.env')
load_dotenv(env_path)


@dataclass
class ComparerSettings:
    """
    Configuración de la aplicación de comparación.
    
    Attributes:
        spreadsheet_name: Nombre del spreadsheet de Google
        default_batch_size: Tamaño de batch por defecto
        log_level: Nivel de logging
    """
    spreadsheet_name: str
    default_batch_size: int
    log_level: str
    
    @classmethod
    def load(cls) -> ComparerSettings:
        """
        Carga configuración desde variables de entorno.
        
        Returns:
            ComparerSettings: Configuración cargada
            
        Raises:
            ValueError: Si falta alguna variable requerida
        """
        spreadsheet_name = os.getenv("SPREADSHEET_NAME")
        
        if not spreadsheet_name:
            raise ValueError(
                "Variable de entorno SPREADSHEET_NAME es requerida. "
                "Copia .env.example a .env y configúralo."
            )
        
        return cls(
            spreadsheet_name=spreadsheet_name,
            default_batch_size=int(os.getenv("BATCH_SIZE", "5000")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper()
        )


# Instancia global de configuración
settings = ComparerSettings.load()
