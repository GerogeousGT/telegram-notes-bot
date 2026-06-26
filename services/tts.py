"""
TTS через Yandex SpeechKit v3 (нейросетевые голоса — качество как у Алисы).
Возвращает OGG Opus байты — Telegram принимает напрямую.
"""

import asyncio
import base64
import json
import logging
import re

import httpx

logger = logging.getLogger(__name__)

TTS_V3_URL = "https://tts.api.cloud.yandex.net/tts/v3/utteranceSynthesis"
MAX_TEXT_LEN = 4500


def _strip_markdown(text: str) -> str:
    """Убирает markdown-разметку — SpeechKit читает звёздочки вслух."""
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', text)
    text = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', text, flags=re.DOTALL)
    return text.strip()


class TTSService:
    def __init__(self, api_key: str, folder_id: str):
        self._api_key = api_key
        self._folder_id = folder_id

    async def synthesize(self, text: str) -> bytes | None:
        if not text or not text.strip():
            return None

        text = _strip_markdown(text)[:MAX_TEXT_LEN]

        def _call():
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    TTS_V3_URL,
                    headers={
                        "Authorization": f"Api-Key {self._api_key}",
                        "x-folder-id": self._folder_id,
                    },
                    json={
                        "text": text,
                        "outputAudioSpec": {
                            "containerAudio": {
                                "containerAudioType": "OGG_OPUS"
                            }
                        },
                        "hints": [
                            {"voice": "masha"},
                            {"speed": 1.0},
                        ],
                        "loudnessNormalizationType": "LUFS",
                    },
                )
                resp.raise_for_status()

                # v3 возвращает NDJSON: каждая строка — JSON с чанком аудио в base64
                audio = b""
                for line in resp.text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        chunk_b64 = obj.get("result", {}).get("audioChunk", {}).get("data", "")
                        if chunk_b64:
                            audio += base64.b64decode(chunk_b64)
                    except Exception:
                        continue
                return audio if audio else None

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, _call)
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None
