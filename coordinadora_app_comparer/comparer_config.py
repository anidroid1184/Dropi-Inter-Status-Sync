from dataclasses import dataclass
import os
from dotenv import load_dotenv


# Cargar .env desde el directorio de esta app
app_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(app_dir, '.env')
load_dotenv(env_path)


@dataclass
class ComparerSettings:
    spreadsheet_name: str
    credentials_path: str


def load_settings() -> ComparerSettings:
    spreadsheet_name = os.getenv("SPREADSHEET_NAME", "seguimiento")
    credentials_path = os.path.join(app_dir, "credentials.json")
    return ComparerSettings(
        spreadsheet_name=spreadsheet_name,
        credentials_path=credentials_path
    )

