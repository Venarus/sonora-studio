"""
SONORA Studio - Structured Logging System
"""

import logging
import sys
from pathlib import Path
from app.config import DOCUMENTS_DIR

LOGS_DIR = DOCUMENTS_DIR / "Logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "sonora_studio.log"

# Create root logger
logger = logging.getLogger("SONORA")
logger.setLevel(logging.DEBUG)

# File handler
try:
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
except Exception as e:
    print(f"Log dosyası oluşturulamadı: {e}")

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


def get_logger(name: str):
    return logger.getChild(name)
