"""
Telegram бот-помощник. Точка входа.
Сохраняет сообщения, транскрибирует аудио/видео, принимает файлы.
"""

import logging

from telegram import Update
from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN, DISTRIBUTION_FOLDER, DEEPSEEK_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, YANDEX_API_KEY, YANDEX_FOLDER_ID
from services.file_saver import FileSaver
from services.sync_manager import SyncManager
from services.ai_assistant import AIAssistant
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

    has_ai = GROQ_API_KEY or GEMINI_API_KEY or DEEPSEEK_API_KEY or YANDEX_API_KEY
    if has_ai:
        application.bot_data["ai_assistant"] = AIAssistant(
            groq_api_key=GROQ_API_KEY,
            yandex_api_key=YANDEX_API_KEY,
            yandex_folder_id=YANDEX_FOLDER_ID,
        )
        providers = []
        if GROQ_API_KEY:
            providers.append("Groq")
        if YANDEX_API_KEY and YANDEX_FOLDER_ID:
            providers.append("Yandex")
        print(f"🤖 AI-ассистент подключён ({', '.join(providers)})")
    else:
        application.bot_data["ai_assistant"] = None
        print("⚠️  AI ключ не задан — бот работает в режиме сохранения")

    commands.register(application)
    messages.register(application)

    application.bot_data["sync_manager"].log_action("STARTUP", "Бот запущен")
    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
