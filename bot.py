"""
Telegram бот-помощник. Точка входа.
Сохраняет сообщения, транскрибирует аудио/видео, принимает файлы.
"""

import logging

from telegram import Update
from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN, DISTRIBUTION_FOLDER
from services.file_saver import FileSaver
from services.sync_manager import SyncManager
import handlers.commands as commands
import handlers.messages as messages

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


def main():
    print("🚀 Запуск бота...")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.bot_data["file_saver"] = FileSaver(DISTRIBUTION_FOLDER)
    application.bot_data["sync_manager"] = SyncManager(DISTRIBUTION_FOLDER)

    commands.register(application)
    messages.register(application)

    application.bot_data["sync_manager"].log_action("STARTUP", "Бот запущен")
    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
