from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application

from config import DISTRIBUTION_FOLDER, ADMIN_ID
from handlers.utils import check_admin_access


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    await update.message.reply_text("""
🤖 *Привет! Я твой бот-помощник.*

Я умею:
• Сохранять текстовые сообщения
• Транскрибировать голосовые, аудио, видео и круглые видео
• Сохранять документы и изображения (вместе с подписью)
• Скачивать и транскрибировать видео по ссылкам (Instagram, YouTube, TikTok)
• Вести логи работы

📋 *Команды:*
/help - справка
/status - статус бота
/sync - статистика синхронизации
/log - последние записи логов
/list - последние сохранённые файлы
""", parse_mode="Markdown")

    context.application.bot_data["sync_manager"].log_action(
        "START", f"Пользователь {update.effective_user.id} запустил бота"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    await update.message.reply_text("""
📋 *Справка по боту*

*Что принимает бот:*
• Текст → Распределение/сообщения/
• Голосовые / аудио → транскрибирует → Распределение/транскрипты/
• Видео / круглые видео → транскрибирует → Распределение/транскрипты/
• Документы → Распределение/документы/
• Изображения → Распределение/изображения/
• Ссылки на видео (YouTube, Instagram, TikTok) → скачивает и транскрибирует

*Подписи* к фото/документам сохраняются отдельно как текст.

*Команды:*
/start /help /status /sync /log /list
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


def register(application: Application):
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("sync", sync_command))
    application.add_handler(CommandHandler("log", log_command))
    application.add_handler(CommandHandler("list", list_command))
