"""
AI-ассистент с поддержкой нескольких провайдеров: Groq и YandexGPT.
Поддерживает function calling: сохранение заметок, поиск, управление категориями.
"""

import asyncio
import logging
import re
from pathlib import Path

from openai import OpenAI

logger = logging.getLogger(__name__)

PROVIDERS = {
    "groq": {
        "label": "Groq (Llama 3.3)",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "yandex": {
        "label": "YandexGPT Lite",
        "model": None,  # формируется динамически через folder_id
        "base_url": "https://ai.api.cloud.yandex.net/v1",
    },
}

_DEFAULT_SYSTEM_PROMPT = """Ты личный AI-ассистент. Работаешь через Telegram.

Твои инструменты:
- save_note — сохранить заметку или мысль в нужную категорию
- search_notes — найти по сохранённым заметкам
- create_category — создать новую категорию для заметок
- list_categories — показать доступные категории
- get_stats — статистика сохранённых заметок

Логика работы:
- Если пользователь говорит "сохрани это", "запомни", "в заметки" — сохраняй через save_note.
- Если цитирует что-то из диалога и просит сохранить — сохраняй именно это.
- Если спрашивает "что я говорил про X" или "найди про Y" — используй search_notes.
- Если просит создать категорию — используй create_category.
- На остальные вопросы отвечай кратко и по делу.
- Язык: русский."""


def _load_system_prompt() -> str:
    """Загружает промпт из system_prompt.txt рядом с ботом, иначе базовый."""
    prompt_path = Path(__file__).resolve().parent.parent / "system_prompt.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    return _DEFAULT_SYSTEM_PROMPT


SYSTEM_PROMPT = _load_system_prompt()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Сохранить заметку, мысль или текст в указанную категорию",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Текст заметки для сохранения"
                    },
                    "category": {
                        "type": "string",
                        "description": "Категория (папка). Если не указана — используй 'сообщения'."
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "Найти заметки по ключевому слову или фразе",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос"
                    },
                    "category": {
                        "type": "string",
                        "description": "Искать только в этой категории. Если не указана — ищет везде."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_category",
            "description": "Создать новую категорию (папку) для заметок",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Название категории (на русском или английском)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Для чего эта категория"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_categories",
            "description": "Показать список доступных категорий для сохранения заметок",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stats",
            "description": "Получить статистику: сколько заметок, транскриптов и файлов сохранено",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

MAX_HISTORY = 20


def _clean_response(text: str) -> str:
    """Убирает артефакты вызова функций которые Llama иногда вставляет в текст."""
    text = re.sub(r'<function=\w+>.*?</function>', '', text, flags=re.DOTALL)
    return text.strip()


class AIAssistant:
    def __init__(self, groq_api_key: str | None = None, yandex_api_key: str | None = None, yandex_folder_id: str | None = None):
        self._groq_api_key = groq_api_key
        self._yandex_api_key = yandex_api_key
        self._yandex_folder_id = yandex_folder_id
        self._histories: dict[int, list] = {}
        self._user_provider: dict[int, str] = {}  # per-user выбор провайдера

    def set_provider(self, user_id: int, provider: str):
        """Переключить провайдера для конкретного пользователя."""
        if provider not in PROVIDERS:
            raise ValueError(f"Неизвестный провайдер: {provider}")
        self._user_provider[user_id] = provider

    def get_provider(self, user_id: int) -> str:
        return self._user_provider.get(user_id, "groq")

    def get_provider_label(self, user_id: int) -> str:
        return PROVIDERS[self.get_provider(user_id)]["label"]

    def available_providers(self) -> list[str]:
        """Список провайдеров, для которых есть ключи."""
        result = []
        if self._groq_api_key:
            result.append("groq")
        if self._yandex_api_key and self._yandex_folder_id:
            result.append("yandex")
        return result

    def _make_client(self, provider: str) -> tuple[OpenAI, str]:
        """Создать клиент и вернуть (client, model_name)."""
        if provider == "groq":
            client = OpenAI(
                api_key=self._groq_api_key,
                base_url=PROVIDERS["groq"]["base_url"],
            )
            return client, PROVIDERS["groq"]["model"]
        if provider == "yandex":
            client = OpenAI(
                api_key=self._yandex_api_key,
                base_url=PROVIDERS["yandex"]["base_url"],
                project=self._yandex_folder_id,
            )
            model = f"gpt://{self._yandex_folder_id}/yandexgpt-lite/latest"
            return client, model
        raise ValueError(f"Неизвестный провайдер: {provider}")

    def get_history(self, user_id: int) -> list:
        return self._histories.setdefault(user_id, [])

    def clear_history(self, user_id: int):
        self._histories.pop(user_id, None)

    def add_context(self, user_id: int, role: str, content: str):
        """Добавить сообщение в историю без запроса к AI (например, транскрипт)."""
        history = self.get_history(user_id)
        history.append({"role": role, "content": content})
        if len(history) > MAX_HISTORY:
            self._histories[user_id] = history[-MAX_HISTORY:]

    async def process_message(self, text: str, user_id: int, file_saver, sync_manager) -> str:
        provider = self.get_provider(user_id)
        history = self.get_history(user_id)
        history.append({"role": "user", "content": text})

        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]
            self._histories[user_id] = history

        try:
            response_text = await self._run_tool_loop(list(history), file_saver, sync_manager, provider)
        except Exception as e:
            logger.error(f"AI error: {e}")
            return f"❌ Ошибка AI: {e}"

        history.append({"role": "assistant", "content": response_text})
        return response_text

    async def _run_tool_loop(self, messages: list, file_saver, sync_manager, provider: str) -> str:
        loop = asyncio.get_running_loop()
        client, model = self._make_client(provider)

        while True:
            msgs_snapshot = list(messages)

            def _call_api():
                return client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + msgs_snapshot,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=1024,
                )

            response = await loop.run_in_executor(None, _call_api)
            choice = response.choices[0]

            if choice.finish_reason == "stop":
                return _clean_response(choice.message.content or "...")

            if choice.finish_reason != "tool_calls":
                break

            messages.append({
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    }
                    for tc in choice.message.tool_calls
                ]
            })

            for tc in choice.message.tool_calls:
                import json
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                result = self._execute_tool(tc.function.name, args, file_saver, sync_manager)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })

        return "Не удалось получить ответ"

    def _execute_tool(self, tool_name: str, args: dict, file_saver, sync_manager) -> str:
        if tool_name == "save_note":
            content = args.get("content", "")
            category = args.get("category", "сообщения")
            filepath = file_saver.save_to_category(content, category)
            sync_manager.log_action("AI_SAVE", f"AI сохранил заметку в категорию '{category}'")
            return f"Заметка сохранена в '{category}': {filepath}"

        if tool_name == "search_notes":
            query = args.get("query", "")
            category = args.get("category")
            return self._search_notes(query, category, file_saver)

        if tool_name == "create_category":
            name = args.get("name", "")
            description = args.get("description", "")
            result = file_saver.create_category(name, description)
            sync_manager.log_action("AI_CATEGORY", f"Создана категория '{name}'")
            return result

        if tool_name == "list_categories":
            categories = file_saver.list_categories()
            return "Категории: " + ", ".join(categories) if categories else "Категорий пока нет"

        if tool_name == "get_stats":
            stats = sync_manager.get_sync_stats()
            return (
                f"Сообщений: {stats['messages_count']}, "
                f"файлов: {stats['files_count']}, "
                f"транскриптов: {stats['transcripts_count']}, "
                f"всего обработано: {stats['processed_total']}"
            )

        return "Неизвестный инструмент"

    def _search_notes(self, query: str, category: str | None, file_saver) -> str:
        base = file_saver.base_folder
        query_lower = query.lower()
        results = []

        search_folders = []
        if category:
            folder = base / category
            if folder.exists():
                search_folders = [folder]
            else:
                return f"Категория '{category}' не найдена"
        else:
            search_folders = [p for p in base.iterdir() if p.is_dir()]

        for folder in search_folders:
            for filepath in sorted(folder.iterdir(), reverse=True):
                if not filepath.is_file() or filepath.suffix not in (".md", ".txt"):
                    continue
                try:
                    content = filepath.read_text(encoding="utf-8")
                    if query_lower in content.lower():
                        results.append(f"📄 [{folder.name}] {filepath.name}:\n{content[:300]}")
                except Exception:
                    continue
                if len(results) >= 5:
                    break
            if len(results) >= 5:
                break

        if not results:
            return f"По запросу «{query}» ничего не найдено"

        return f"Найдено {len(results)} заметок:\n\n" + "\n\n---\n\n".join(results)
