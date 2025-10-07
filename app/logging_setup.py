import logging
import os
import sys
from datetime import datetime


def setup_logging():
    """Configure global logging with console and daily file handlers.

    Creates logs/<YYYY-MM-DD>.log and sets a consistent format across modules.
    Call once at startup.
    """
    os.makedirs("logs", exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    logfile = os.path.join("logs", f"{today}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logfile, encoding="utf-8"),
        ],
    )

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.INFO)
