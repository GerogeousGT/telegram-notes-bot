"""
Модуль транскрибации через AssemblyAI
Использует httpx вместо aiohttp для стабильной работы на Windows.
"""

import httpx
import asyncio
from config import ASSEMBLYAI_KEY

ASSEMBLY_BASE_URL = "https://api.assemblyai.com/v2"


async def upload_file(file_path: str) -> str:
    """Загружает файл на сервер AssemblyAI"""
    upload_url = f"{ASSEMBLY_BASE_URL}/upload"

    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                upload_url,
                headers={"authorization": ASSEMBLYAI_KEY},
                content=f.read()
            )

            if response.status_code != 200:
                raise Exception(f"Ошибка загрузки файла: {response.text}")

            return response.json()["upload_url"]


async def start_transcription(audio_url: str, language_code: str = "ru") -> str:
    """Запускает транскрибацию аудио"""
    transcript_url = f"{ASSEMBLY_BASE_URL}/transcript"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            transcript_url,
            headers={
                "authorization": ASSEMBLYAI_KEY,
                "content-type": "application/json"
            },
            json={
                "audio_url": audio_url,
                "speech_models": ["universal-3-pro", "universal-2"],
                "language_code": language_code,
            }
        )

        if response.status_code != 200:
            raise Exception(f"Ошибка запуска транскрибации: {response.text}")

        return response.json()["id"]


async def get_transcription_result(transcript_id: str) -> dict:
    """Получает результат транскрибации"""
    result_url = f"{ASSEMBLY_BASE_URL}/transcript/{transcript_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            result_url,
            headers={"authorization": ASSEMBLYAI_KEY}
        )
        return response.json()


TRANSCRIPTION_TIMEOUT_SEC = 360  # 6 минут максимум


async def wait_for_transcription(transcript_id: str, poll_interval: int = 3) -> str:
    """Ожидает завершения транскрибации с таймаутом"""
    max_attempts = TRANSCRIPTION_TIMEOUT_SEC // poll_interval
    for _ in range(max_attempts):
        result = await get_transcription_result(transcript_id)
        status = result["status"]

        if status == "completed":
            return result["text"]
        if status == "error":
            raise Exception(f"Ошибка транскрибации: {result.get('error', 'Unknown error')}")

        await asyncio.sleep(poll_interval)

    raise Exception(f"Таймаут транскрибации после {TRANSCRIPTION_TIMEOUT_SEC} секунд")


async def transcribe_voice(file_path: str, language: str = "ru") -> str:
    """Транскрибирует голосовое сообщение"""
    try:
        print(f"📤 Загрузка файла: {file_path}")
        audio_url = await upload_file(file_path)

        print("🎙️ Запуск транскрибации...")
        transcript_id = await start_transcription(audio_url, language)

        print("⏳ Ожидание результата...")
        transcript = await wait_for_transcription(transcript_id)

        print("✅ Транскрибация завершена!")
        return transcript

    except Exception as e:
        print(f"❌ Ошибка транскрибации: {e}")
        raise


async def transcribe_video(file_path: str, language: str = "ru") -> str:
    """Транскрибирует видео файл"""
    return await transcribe_voice(file_path, language)
