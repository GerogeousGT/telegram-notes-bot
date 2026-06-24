import logging
import os
import re
import shutil
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters, Application

from services.transcriber import transcribe_voice, transcribe_video
from services.document_reader import extract_text, is_supported
from handlers.utils import check_admin_access

logger = logging.getLogger(__name__)

VIDEO_URL_PATTERNS = [
    r'(https?://(www\.)?instagram\.com/(reel|p|reels)/[^\s]+)',
    r'(https?://(www\.)?youtube\.com/watch\?v=[^\s]+)',
    r'(https?://(www\.)?youtu\.be/[^\s]+)',
    r'(https?://(www\.)?youtube\.com/shorts/[^\s]+)',
    r'(https?://(www\.)?tiktok\.com/[^\s]+)',
    r'(https?://(vm\.)?tiktok\.com/[^\s]+)',
]


def extract_video_url(text: str) -> str | None:
    for pattern in VIDEO_URL_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


async def download_video_from_url(url: str) -> str | None:
    """Скачивает видео через yt-dlp, возвращает путь к файлу"""
    import yt_dlp

    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "video.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }

    import asyncio
    loop = asyncio.get_running_loop()  # fix: get_event_loop() deprecated в Python 3.10+

    def download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get('ext', 'mp4')
            return os.path.join(temp_dir, f"video.{ext}")

    return await loop.run_in_executor(None, download)


# ============================================================================
# ХЕНДЛЕРЫ
# ============================================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user
    fs = context.application.bot_data["file_saver"]
    sm = context.application.bot_data["sync_manager"]
    ai = context.application.bot_data.get("ai_assistant")

    video_url = extract_video_url(message.text)
    if video_url:
        await _handle_video_url(message, user, video_url, fs, sm, ai, context)
        return

    if ai:
        await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
        response = await ai.process_message(message.text, user.id, fs, sm)
        sm.log_action("AI_CHAT", f"AI ответил пользователю {user.username or user.id}")
        sm.mark_as_processed(message.message_id)
        await message.reply_text(response)
    else:
        filepath = fs.save_message(message.text, user.username or "unknown", user.id)
        sm.log_action("TEXT", f"Сохранено сообщение от {user.username or user.id}")
        sm.mark_as_processed(message.message_id)
        await message.reply_text(f"✅ Сообщение сохранено:\n`{filepath}`", parse_mode="Markdown")


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user
    fs = context.application.bot_data["file_saver"]
    sm = context.application.bot_data["sync_manager"]
    ai = context.application.bot_data.get("ai_assistant")

    await message.reply_text("🎤 Транскрибирую...")

    try:
        voice_file = await message.voice.get_file()
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            temp_path = tmp.name
        await voice_file.download_to_drive(temp_path)

        transcript = await transcribe_voice(temp_path)
        os.unlink(temp_path)

        sm.log_action("VOICE", f"Транскрибировано голосовое от {user.username or user.id}")
        sm.mark_as_processed(message.message_id)

        short = transcript[:500] + "..." if len(transcript) > 500 else transcript
        await message.reply_text(f"📝 {short}")

        if ai:
            await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
            response = await ai.process_message(
                f"[голосовое сообщение, расшифровано]: {transcript}",
                user.id, fs, sm
            )
            await message.reply_text(response)
        else:
            filepath = fs.save_transcript(transcript, "voice")
            await message.reply_text(f"✅ Сохранено:\n`{filepath}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка транскрибации голосового: {e}")
        await message.reply_text(f"❌ Ошибка транскрибации: {e}")


async def audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Аудио-файлы (музыка, записи) — fix: раньше игнорировались"""
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user
    fs = context.application.bot_data["file_saver"]
    sm = context.application.bot_data["sync_manager"]
    ai = context.application.bot_data.get("ai_assistant")

    await message.reply_text("🎵 Транскрибирую...")

    try:
        audio_file = await message.audio.get_file()
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            temp_path = tmp.name
        await audio_file.download_to_drive(temp_path)

        transcript = await transcribe_voice(temp_path)
        os.unlink(temp_path)

        sm.log_action("AUDIO", f"Транскрибовано аудио от {user.username or user.id}")
        sm.mark_as_processed(message.message_id)

        short = transcript[:500] + "..." if len(transcript) > 500 else transcript
        await message.reply_text(f"📝 {short}")

        if ai:
            await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
            response = await ai.process_message(
                f"[аудио, расшифровано]: {transcript}",
                user.id, fs, sm
            )
            await message.reply_text(response)
        else:
            filepath = fs.save_transcript(transcript, "audio")
            await message.reply_text(f"✅ Сохранено:\n`{filepath}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка транскрибации аудио: {e}")
        await message.reply_text(f"❌ Ошибка: {e}")


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user
    fs = context.application.bot_data["file_saver"]
    sm = context.application.bot_data["sync_manager"]
    ai = context.application.bot_data.get("ai_assistant")

    filename = message.document.file_name or "document"
    await message.reply_text(f"📄 Получил `{filename}`, сохраняю...", parse_mode="Markdown")

    try:
        doc_file = await message.document.get_file()

        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            temp_path = tmp.name
        await doc_file.download_to_drive(temp_path)

        filepath = fs.save_document(temp_path, filename)

        sm.log_action("DOCUMENT", f"Сохранён документ {filename} от {user.username or user.id}")
        sm.mark_as_processed(message.message_id)

        reply = f"✅ Сохранён:\n`{filepath}`"
        if message.caption:
            fs.save_sidecar(filepath, message.caption)

        await message.reply_text(reply, parse_mode="Markdown")

        if ai and is_supported(filename):
            await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
            try:
                text = extract_text(temp_path)
                if text:
                    prompt = f"[документ: {filename}]\n\n{text}"
                    if message.caption:
                        prompt = f"{message.caption}\n\n[документ: {filename}]\n\n{text}"
                    response = await ai.process_message(prompt, user.id, fs, sm)
                    await message.reply_text(response)
                else:
                    await message.reply_text("⚠️ Не удалось извлечь текст из документа.")
            except Exception as e:
                await message.reply_text(f"⚠️ Документ сохранён, но прочитать не удалось: {e}")

        os.unlink(temp_path)
    except Exception as e:
        logger.error(f"Ошибка сохранения документа: {e}")
        await message.reply_text(f"❌ Ошибка: {e}")


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user
    fs = context.application.bot_data["file_saver"]
    sm = context.application.bot_data["sync_manager"]

    await message.reply_text("🖼️ Получил изображение, сохраняю...")

    try:
        photo = message.photo[-1]
        file = await photo.get_file()

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            temp_path = tmp.name
        await file.download_to_drive(temp_path)

        filepath = fs.save_image(temp_path, "jpg")
        os.unlink(temp_path)

        sm.log_action("IMAGE", f"Сохранено изображение от {user.username or user.id}")
        sm.mark_as_processed(message.message_id)

        reply = f"✅ Изображение сохранено:\n`{filepath}`"

        if message.caption:
            caption_path = fs.save_sidecar(filepath, message.caption)
            reply += f"\n📝 Подпись рядом:\n`{caption_path}`"

        await message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка сохранения изображения: {e}")
        await message.reply_text(f"❌ Ошибка сохранения: {e}")


async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user
    fs = context.application.bot_data["file_saver"]
    sm = context.application.bot_data["sync_manager"]

    await message.reply_text("🎬 Получил видео, транскрибирую (это может занять время)...")

    try:
        video_file = await message.video.get_file()
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            temp_path = tmp.name
        await video_file.download_to_drive(temp_path)

        transcript = await transcribe_video(temp_path)
        filepath = fs.save_transcript(transcript, "video")
        os.unlink(temp_path)

        sm.log_action("VIDEO", f"Транскрибировано видео от {user.username or user.id}")
        sm.mark_as_processed(message.message_id)

        short = transcript[:500] + "..." if len(transcript) > 500 else transcript
        await message.reply_text(
            f"✅ *Транскрипт видео сохранён:*\n`{filepath}`\n\n📝 *Текст:*\n{short}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка транскрибации видео: {e}")
        await message.reply_text(f"❌ Ошибка транскрибации: {e}")


async def video_note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Круглые видео — fix: раньше игнорировались"""
    if not await check_admin_access(update):
        return

    message = update.message
    user = update.effective_user
    fs = context.application.bot_data["file_saver"]
    sm = context.application.bot_data["sync_manager"]
    ai = context.application.bot_data.get("ai_assistant")

    await message.reply_text("🎬 Транскрибирую...")

    try:
        vn_file = await message.video_note.get_file()
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            temp_path = tmp.name
        await vn_file.download_to_drive(temp_path)

        transcript = await transcribe_video(temp_path)
        os.unlink(temp_path)

        sm.log_action("VIDEO_NOTE", f"Транскрибована видео-заметка от {user.username or user.id}")
        sm.mark_as_processed(message.message_id)

        short = transcript[:500] + "..." if len(transcript) > 500 else transcript
        await message.reply_text(f"📝 {short}")

        if ai:
            await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
            response = await ai.process_message(
                f"[видео-заметка, расшифрована]: {transcript}",
                user.id, fs, sm
            )
            await message.reply_text(response)
        else:
            filepath = fs.save_transcript(transcript, "video_note")
            await message.reply_text(f"✅ Сохранено:\n`{filepath}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка транскрибации видео-заметки: {e}")
        await message.reply_text(f"❌ Ошибка: {e}")


async def _handle_video_url(message, user, url: str, fs, sm, ai=None, context=None):
    """Скачивает видео по ссылке, транскрибирует и отправляет в AI-диалог"""
    await message.reply_text(
        f"🎬 Скачиваю видео...\n`{url[:60]}...`",
        parse_mode="Markdown"
    )

    temp_dir = None
    try:
        video_path = await download_video_from_url(url)
        temp_dir = os.path.dirname(video_path) if video_path else None

        if not video_path or not os.path.exists(video_path):
            await message.reply_text("❌ Не удалось скачать видео")
            return

        await message.reply_text("📤 Транскрибирую...")

        transcript = await transcribe_video(video_path)

        sm.log_action("URL_VIDEO", f"Транскрибировано видео по ссылке от {user.username or user.id}")
        sm.mark_as_processed(message.message_id)

        with open(video_path, "rb") as vf:
            await message.reply_video(vf)

        short = transcript[:500] + "..." if len(transcript) > 500 else transcript
        await message.reply_text(f"📝 {short}")

        if ai and context:
            await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
            response = await ai.process_message(
                f"[видео по ссылке {url}, расшифровано]: {transcript}",
                user.id, fs, sm
            )
            await message.reply_text(response)
        else:
            filepath = fs.save_transcript(transcript, "url")
            fs.save_link(url, "Video transcript")
            await message.reply_text(f"✅ Сохранено:\n`{filepath}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка обработки видео по ссылке: {e}")
        await message.reply_text(f"❌ Ошибка: {e}")
    finally:
        # fix: shutil.rmtree вместо ручного удаления — безопасно если yt-dlp создал субпапки
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def register(application: Application):
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.VOICE, voice_handler))
    application.add_handler(MessageHandler(filters.AUDIO, audio_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.VIDEO, video_handler))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, video_note_handler))
