from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application

from config import DISTRIBUTION_FOLDER, ADMIN_ID
from handlers.utils import check_admin_access


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    ai = context.application.bot_data.get("ai_assistant")
    ai_status = "✅ подключён" if ai else "❌ не подключён (нет DEEPSEEK\\_API\\_KEY)"

    await update.message.reply_text(f"""
🤖 *Привет! Я твой AI-ассистент.*

🧠 *AI-режим:* {ai_status}

Я умею:
• Отвечать на вопросы и вести диалог
• Сохранять заметки по команде ("сохрани это", "запомни")
• Искать по заметкам ("найди про X")
• Создавать категории ("создай категорию рецепты")
• Транскрибировать голосовые, аудио, видео и круглые видео
• Анализировать транскрипты и выделять ключевые пункты
• Сохранять документы и изображения
• Скачивать и транскрибировать видео (Instagram, YouTube, TikTok)

📋 *Команды:*
/help — справка
/clear — сбросить историю диалога с AI
/status — статус бота
/sync — статистика
/log — последние логи
/list — последние файлы
""", parse_mode="Markdown")

    context.application.bot_data["sync_manager"].log_action(
        "START", f"Пользователь {update.effective_user.id} запустил бота"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    await update.message.reply_text("""
📋 *Справка по боту*

*AI-режим (текстовые сообщения):*
• Просто пиши — AI отвечает в диалоге
• "Сохрани это в заметки" — AI сохранит
• "Сохрани в категорию рецепты: [текст]" — сохранит в нужную папку
• "Найди про встречу" — поищет по заметкам
• "Создай категорию идеи" — создаст новую папку

*Медиа:*
• Голосовые / аудио / видео / круглые — транскрибирует, сохраняет и анализирует
• Документы → Распределение/документы/
• Изображения → Распределение/изображения/
• Ссылки на видео (YouTube, Instagram, TikTok) → транскрибирует

*Команды:*
/clear — сбросить историю диалога с AI
/status — статус и путь к данным
/sync — статистика обработанных сообщений
/log — последние 10 записей лога
/list — последние 10 сохранённых файлов
""", parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    await update.message.reply_text(f"""
📊 *Статус бота*

✅ Бот работает
📁 Папка: `{DISTRIBUTION_FOLDER}`
👤 Админ ID: `{ADMIN_ID}`
""", parse_mode="Markdown")


async def sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    msg = context.application.bot_data["sync_manager"].format_stats_message()
    await update.message.reply_text(msg, parse_mode="Markdown")


async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    msg = context.application.bot_data["sync_manager"].format_logs_message(10)
    await update.message.reply_text(msg, parse_mode="Markdown")


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    files = context.application.bot_data["file_saver"].get_recent_files(10)

    if not files:
        await update.message.reply_text("📂 *Файлов пока нет*", parse_mode="Markdown")
        return

    message = "📂 *Последние файлы:*\n\n"
    for f in files:
        message += f"• `{f['folder']}/{f['name']}`\n"

    await update.message.reply_text(message, parse_mode="Markdown")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    ai = context.application.bot_data.get("ai_assistant")
    if ai:
        ai.clear_history(update.effective_user.id)
        await update.message.reply_text("🧹 История диалога с AI сброшена.")
    else:
        await update.message.reply_text("AI-ассистент не подключён.")


def register(application: Application):
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("sync", sync_command))
    application.add_handler(CommandHandler("log", log_command))
    application.add_handler(CommandHandler("list", list_command))
