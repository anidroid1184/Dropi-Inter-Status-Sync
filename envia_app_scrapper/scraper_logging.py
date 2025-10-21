"""
Sistema de logging para App Scraper.
"""

import logging
import os
from datetime import datetime


def setup_logging():
    """Configura el sistema de logging en carpeta local."""
    
    # Logs en la carpeta de la app
    app_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(app_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    log_file = os.path.join(
        logs_dir, 
        f"scraper_{datetime.now().strftime('%Y%m%d')}.log"
    )
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
