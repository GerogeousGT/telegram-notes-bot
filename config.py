"""
Конфигурация Telegram бота-помощника.
Все секреты — через переменные окружения (из корневого .env или системных env vars).
"""

import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
ASSEMBLYAI_KEY = os.environ["ASSEMBLYAI_KEY"]

_BASE_DIR = Path(__file__).resolve().parent
DISTRIBUTION_FOLDER = os.environ.get("DATA_FOLDER", str(_BASE_DIR / "Распределение"))

TRANSCRIPTION_LANGUAGE = "ru"
MAX_FILE_SIZE = 20 * 1024 * 1024
DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"
