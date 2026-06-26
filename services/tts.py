"""
TTS через Yandex SpeechKit. Возвращает OGG Opus байты — Telegram принимает напрямую.
"""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
MAX_TEXT_LEN = 4500  # лимит SpeechKit


class TTSService:
    def __init__(self, api_key: str, folder_id: str):
        self._api_key = api_key
        self._folder_id = folder_id

    async def synthesize(self, text: str) -> bytes | None:
        if not text or not text.strip():
            return None

        text = text[:MAX_TEXT_LEN]

        def _call():
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    TTS_URL,
                    headers={"Authorization": f"Api-Key {self._api_key}"},
                    data={
                        "text": text,
                        "lang": "ru-RU",
                        "voice": "masha",
                        "format": "oggopus",
                        "folderId": self._folder_id,
                        "speed": "1.0",
                    },
                )
                resp.raise_for_status()
                return resp.content

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, _call)
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None
