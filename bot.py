"""
Telegram бот-помощник для обучения
Сохраняет сообщения, транскрибирует голосовые, принимает файлы.
Транскрибирует видео по ссылкам (Instagram, YouTube, TikTok).
"""

import logging
import os
import re
import tempfile
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN, DISTRIBUTION_FOLDER, ADMIN_ID
from file_saver import FileSaver
from transcriber import transcribe_voice, transcribe_video
from sync_manager import SyncManager


VIDEO_URL_PATTERNS = [
    r'(https?://(www\.)?instagram\.com/(reel|p|reels)/[^\s]+)',
    r'(https?://(www\.)?youtube\.com/watch\?v=[^\s]+)',
    r'(https?://(www\.)?youtu\.be/[^\s]+)',
    r'(https?://(www\.)?youtube\.com/shorts/[^\s]+)',
    r'(https?://(www\.)?tiktok\.com/[^\s]+)',
    r'(https?://(vm\.)?tiktok\.com/[^\s]+)',
]


def extract_video_url(text: str) -> str | None:
    """Извлекает ссылку на видео из текста"""
    for pattern in VIDEO_URL_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


async def download_video_from_url(url: str) -> str | None:
    """Скачивает видео по ссылке через yt-dlp, возвращает путь к файлу"""
    import yt_dlp

    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "video.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'extract_audio': False,
    }

    loop = asyncio.get_event_loop()

    def download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get('ext', 'mp4')
            return os.path.join(temp_dir, f"video.{ext}")

    return await loop.run_in_executor(None, download)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

file_saver = FileSaver(DISTRIBUTION_FOLDER)
sync_manager = SyncManager(DISTRIBUTION_FOLDER)


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом"""
    return user_id == ADMIN_ID


async def check_admin_access(update: Update) -> bool:
    """Проверяет доступ админа, отправляет сообщение если нет доступа"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(
            "❌ Доступ запрещён. Этот бот доступен только администратору."
        )
        return False
    return True


# ============================================================================
# КОМАНДЫ БОТА
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if not await check_admin_access(update):
        return

    welcome_message = """
🤖 *Привет! Я твой бот-помощник для обучения.*

Я умею:
• Сохранять текстовые сообщения
• Транскрибировать голосовые
• Сохранять документы и изображения
• Вести логи работы

Просто отправь мне что-нибудь, и я сохраню это в папку Распределение.

📋 *Команды:*
/help - справка
/status - статус бота
/sync - статистика синхронизации
/log - последние записи логов
/list - последние сохранённые файлы
"""
    await update.message.reply_text(welcome_message, parse_mode="Markdown")
    sync_manager.log_action("START", f"Пользователь {update.effective_user.id} запустил бота")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    if not await check_admin_access(update):
        return

    help_message = """
📋 *Справка по боту*

*Что я умею:*
• Текст → сохраняю в Распределение/сообщения/
• Голосовые → транскрибирую через AssemblyAI
• Документы → сохраняю в Распределение/документы/
• Изображения → сохраняю в Распределение/изображения/

*Команды:*
/start - приветствие
/help - эта справка
/status - показать путь к папке
/sync - статистика синхронизации
/log - последние 10 записей логов
/list - последние сохранённые файлы

*Важно:*
Бот работает только когда твой компьютер включен.
"""
    await update.message.reply_text(help_message, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status"""
    if not await check_admin_access(update):
        return

    status_message = f"""
📊 *Статус бота*

✅ Бот работает
📁 Папка: `{DISTRIBUTION_FOLDER}`
👤 Админ ID: `{ADMIN_ID}`

Отправь любое сообщение для проверки.
"""
    await update.message.reply_text(status_message, parse_mode="Markdown")


async def sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /sync — показать статистику"""
    if not await check_admin_access(update):
        return

    stats_message = sync_manager.format_stats_message()
    await update.message.reply_text(stats_message, parse_mode="Markdown")


async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /log — показать последние логи"""
    if not await check_admin_access(update):
        return

    logs_message = sync_manager.format_logs_message(10)
    await update.message.reply_text(logs_message, parse_mode="Markdown")


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /list — показать последние файлы"""
    if not await check_admin_access(update):
        return

    files = file_saver.get_recent_files(10)

    if not files:
        await update.message.reply_text("📂 *Файлов пока нет*", parse_mode="Markdown")
        return

    message = "📂 *Последние файлы:*\n\n"
    for f in files:
        message += f"• `{f['folder']}/{f['name']}`\n"

    await update.message.reply_text(message, parse_mode="Markdown")


# ============================================================================
# ОБРАБОТЧИКИ СООБЩЕНИЙ
# ============================================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user

    text = message.text
    username = user.username or "unknown"
    user_id = user.id

    video_url = extract_video_url(text)

    if video_url:
        await handle_video_url(message, user, video_url)
        return

    filepath = file_saver.save_message(text, username, user_id)

    sync_manager.log_action("TEXT", f"Сохранено сообщение от {username}")
    sync_manager.mark_as_processed(message.message_id)

    await message.reply_text(f"✅ Сообщение сохранено:\n`{filepath}`", parse_mode="Markdown")


async def handle_video_url(message, user, url: str):
    """Обработка ссылки на видео — скачивание и транскрибация"""
    await message.reply_text(f"🎬 Обнаружена ссылка на видео, скачиваю и транскрибирую...\n`{url[:50]}...`", parse_mode="Markdown")

    try:
        video_path = await download_video_from_url(url)

        if not video_path or not os.path.exists(video_path):
            await message.reply_text("❌ Не удалось скачать видео")
            return

        await message.reply_text("📤 Видео скачано, транскрибирую...")

        transcript = await transcribe_video(video_path)

        filepath = file_saver.save_transcript(transcript, f"url")

        temp_dir = os.path.dirname(video_path)
        for f in os.listdir(temp_dir):
            os.unlink(os.path.join(temp_dir, f))
        os.rmdir(temp_dir)

        sync_manager.log_action("URL_VIDEO", f"Транскрибировано видео по ссылке от {user.username or user.id}")
        sync_manager.mark_as_processed(message.message_id)

        file_saver.save_link(url, "Video transcript")

        short_transcript = transcript[:500] + "..." if len(transcript) > 500 else transcript
        await message.reply_text(
            f"✅ *Транскрипт видео сохранён:*\n`{filepath}`\n\n📝 *Текст:*\n{short_transcript}",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Ошибка обработки видео по ссылке: {e}")
        await message.reply_text(f"❌ Ошибка: {e}")


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик голосовых сообщений"""
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user

    await message.reply_text("🎤 Получил голосовое, транскрибирую...")

    try:
        voice = await message.voice.get_file()

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            temp_path = temp_file.name

        await voice.download_to_drive(temp_path)

        transcript = await transcribe_voice(temp_path)

        filepath = file_saver.save_transcript(transcript, "voice")

        os.unlink(temp_path)

        sync_manager.log_action("VOICE", f"Транскрибировано голосовое от {user.username or user.id}")
        sync_manager.mark_as_processed(message.message_id)

        short_transcript = transcript[:500] + "..." if len(transcript) > 500 else transcript
        await message.reply_text(
            f"✅ *Транскрипт сохранён:*\n`{filepath}`\n\n📝 *Текст:*\n{short_transcript}",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Ошибка транскрибации: {e}")
        await message.reply_text(f"❌ Ошибка транскрибации: {e}")


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик документов"""
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user

    await message.reply_text("📄 Получил документ, сохраняю...")

    try:
        document = await message.document.get_file()
        filename = message.document.file_name or "document"

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        await document.download_to_drive(temp_path)

        filepath = file_saver.save_document(temp_path, filename)

        os.unlink(temp_path)

        sync_manager.log_action("DOCUMENT", f"Сохранён документ {filename} от {user.username or user.id}")
        sync_manager.mark_as_processed(message.message_id)

        await message.reply_text(f"✅ Документ сохранён:\n`{filepath}`", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка сохранения документа: {e}")
        await message.reply_text(f"❌ Ошибка сохранения: {e}")


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик изображений"""
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user

    await message.reply_text("🖼️ Получил изображение, сохраняю...")

    try:
        photo = message.photo[-1]
        file = await photo.get_file()

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_path = temp_file.name

        await file.download_to_drive(temp_path)

        filepath = file_saver.save_image(temp_path, "jpg")

        os.unlink(temp_path)

        sync_manager.log_action("IMAGE", f"Сохранено изображение от {user.username or user.id}")
        sync_manager.mark_as_processed(message.message_id)

        await message.reply_text(f"✅ Изображение сохранено:\n`{filepath}`", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка сохранения изображения: {e}")
        await message.reply_text(f"❌ Ошибка сохранения: {e}")


async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик видео (транскрибация)"""
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user

    await message.reply_text("🎬 Получил видео, транскрибирую (это может занять время)...")

    try:
        video = await message.video.get_file()

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_path = temp_file.name

        await video.download_to_drive(temp_path)

        transcript = await transcribe_video(temp_path)

        filepath = file_saver.save_transcript(transcript, "video")

        os.unlink(temp_path)

        sync_manager.log_action("VIDEO", f"Транскрибировано видео от {user.username or user.id}")
        sync_manager.mark_as_processed(message.message_id)

        short_transcript = transcript[:500] + "..." if len(transcript) > 500 else transcript
        await message.reply_text(
            f"✅ *Транскрипт видео сохранён:*\n`{filepath}`\n\n📝 *Текст:*\n{short_transcript}",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Ошибка транскрибации видео: {e}")
        await message.reply_text(f"❌ Ошибка транскрибации: {e}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Главная функция запуска бота"""

    print("🚀 Запуск бота...")
    sync_manager.log_action("STARTUP", "Бот запущен")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("sync", sync_command))
    application.add_handler(CommandHandler("log", log_command))
    application.add_handler(CommandHandler("list", list_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.VOICE, voice_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.VIDEO, video_handler))

    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
