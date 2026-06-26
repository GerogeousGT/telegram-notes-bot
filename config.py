"""
Конфигурация бота. Все секреты — через переменные окружения.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Валидация обязательных переменных — падаем сразу с понятным сообщением
_required = ["TELEGRAM_BOT_TOKEN", "ADMIN_ID", "ASSEMBLYAI_KEY"]
# DEEPSEEK_API_KEY опциональный — без него AI-режим отключён, бот работает как раньше
_missing = [k for k in _required if not os.environ.get(k)]
if _missing:
    print(f"ОШИБКА: не заданы переменные окружения: {', '.join(_missing)}")
    print("Скопируй .env.example → .env и заполни значения")
    sys.exit(1)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
ASSEMBLYAI_KEY = os.environ["ASSEMBLYAI_KEY"]

_BASE_DIR = Path(__file__).resolve().parent
DISTRIBUTION_FOLDER = os.environ.get("DATA_FOLDER", str(_BASE_DIR / "Распределение"))

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.environ.get("YANDEX_FOLDER_ID")

TRANSCRIPTION_LANGUAGE = "ru"
MAX_FILE_SIZE = 20 * 1024 * 1024
DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"
