"""
Модуль синхронизации и логирования
Ведёт логи действий бота, отмечает обработанные сообщения, предоставляет статистику.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict


class SyncManager:
    """Класс для синхронизации и логирования работы бота"""

    def __init__(self, base_folder: str):
        self.base_folder = Path(base_folder)
        self.log_file = self.base_folder / "bot.log"
        self.processed_file = self.base_folder / "processed.json"
        self.startup_time = datetime.now()

        self.base_folder.mkdir(parents=True, exist_ok=True)
        self.processed_ids = self._load_processed()

        self.messages_count = 0
        self.files_count = 0
        self.transcripts_count = 0

    def _load_processed(self) -> set:
        """Загружает список обработанных сообщений"""
        if self.processed_file.exists():
            with open(self.processed_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("processed_ids", []))
        return set()

    def _save_processed(self):
        """Сохраняет список обработанных сообщений"""
        self.base_folder.mkdir(parents=True, exist_ok=True)
        with open(self.processed_file, "w", encoding="utf-8") as f:
            json.dump({
                "processed_ids": list(self.processed_ids),
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

    def log_action(self, action_type: str, message: str):
        """Записывает действие в лог-файл"""
        self.base_folder.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{action_type}] {message}\n"

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

        if action_type == "TEXT":
            self.messages_count += 1
        elif action_type in ["DOCUMENT", "IMAGE"]:
            self.files_count += 1
        elif action_type in ["VOICE", "VIDEO"]:
            self.transcripts_count += 1

    def mark_as_processed(self, message_id: int):
        """Отмечает сообщение как обработанное"""
        self.processed_ids.add(message_id)
        self._save_processed()

    def is_processed(self, message_id: int) -> bool:
        """Проверяет, было ли сообщение уже обработано"""
        return message_id in self.processed_ids

    def get_sync_stats(self) -> Dict:
        """Возвращает статистику синхронизации"""
        return {
            "startup_time": self.startup_time.strftime("%Y-%m-%d %H:%M:%S"),
            "messages_count": self.messages_count,
            "files_count": self.files_count,
            "transcripts_count": self.transcripts_count,
            "processed_total": len(self.processed_ids)
        }

    def get_last_logs(self, limit: int = 10) -> List[str]:
        """Возвращает последние записи из лога"""
        if not self.log_file.exists():
            return []

        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        return [line.strip() for line in lines[-limit:]]

    def get_uptime(self) -> str:
        """Возвращает время работы бота"""
        delta = datetime.now() - self.startup_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}ч {minutes}мин {seconds}сек"

    def format_stats_message(self) -> str:
        """Форматирует статистику для отправки в Telegram"""
        stats = self.get_sync_stats()

        return f"""📊 *Статус синхронизации*

🕐 *Запущен:* {stats.get('startup_time', 'N/A')}
⏱️ *Аптайм:* {self.get_uptime()}

📨 *Обработано сообщений:* {stats.get('messages_count', 0)}
📁 *Сохранено файлов:* {stats.get('files_count', 0)}
🎙️ *Транскрибировано:* {stats.get('transcripts_count', 0)}

📋 *Всего обработано:* {stats.get('processed_total', 0)} сообщений
"""

    def format_logs_message(self, limit: int = 10) -> str:
        """Форматирует логи для отправки в Telegram"""
        logs = self.get_last_logs(limit)

        if not logs:
            return "📋 *Логи пусты*\n\nБот только что запущен."

        logs_text = "\n".join(logs)

        return f"""📋 *Последние {len(logs)} записей логов:*

```
{logs_text}
```
"""
