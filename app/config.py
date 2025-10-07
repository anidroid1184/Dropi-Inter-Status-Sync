from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Centralized runtime configuration.

    Do not store secrets here. Only IDs, names and flags. Credentials are read
    from credentials.json managed outside of git.
    """
    drive_folder_id: str = os.getenv("DRIVE_FOLDER_ID", "")
    spreadsheet_name: str = os.getenv("SPREADSHEET_NAME", "seguimiento")
    headless: bool = os.getenv("HEADLESS", "true").lower() == "true"
    timezone: str = os.getenv("TZ", "America/Bogota")
    daily_report_prefix: str = os.getenv("DAILY_REPORT_PREFIX", "Informe_")
    # Folder for individual daily report files (CSV export). Supports common typo key.
    individual_report_folder_id: str = (
        os.getenv("DRIVE_FOLER_INDIVIDUAL_FILE")
        or os.getenv("DRIVE_FOLDER_INDIVIDUAL_FILE", "")
    )


settings = Settings()
