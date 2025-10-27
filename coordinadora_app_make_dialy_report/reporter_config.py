"""
Configuración de APP MAKE DAILY REPORT (Coordinadora).

Carga variables de entorno desde el archivo .env local del app.
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
class ReporterSettings:
    """Configuración de la aplicación de reportes.
    
    Attributes:
        spreadsheet_name: Nombre del spreadsheet de Google
        log_level: Nivel de logging
    """
    spreadsheet_name: str
    log_level: str
    
    @classmethod
    def load(cls) -> ReporterSettings:
        """Carga configuración desde variables de entorno.
        
        Returns:
            ReporterSettings: Configuración cargada
            
        Raises:
            ValueError: Si falta alguna variable requerida
        """
        spreadsheet_name = os.getenv("SPREADSHEET_NAME", "seguimiento")
        
        if not spreadsheet_name:
            raise ValueError(
                "Variable de entorno SPREADSHEET_NAME es requerida. "
                "Copia .env.example a .env y configúralo."
            )
        
        return cls(
            spreadsheet_name=spreadsheet_name,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper()
        )


# Instancia global de configuración
settings = ReporterSettings.load()
