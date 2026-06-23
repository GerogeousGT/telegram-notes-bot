"""
Модуль сохранения файлов в папку Распределение
Сохраняет сообщения, транскрипты, документы, изображения и ссылки.
"""

import shutil
from datetime import datetime
from pathlib import Path


class FileSaver:
    """Класс для сохранения файлов в структурированные папки"""

    def __init__(self, base_folder: str):
        self.base_folder = Path(base_folder)
        self.ensure_folders()

    def ensure_folders(self):
        """Создаёт структуру папок"""
        folders = ["сообщения", "транскрипты", "документы", "изображения", "ссылки"]

        for folder in folders:
            folder_path = self.base_folder / folder
            folder_path.mkdir(parents=True, exist_ok=True)

        print(f"📁 Папка Распределение готова: {self.base_folder}")

    def get_timestamp(self) -> str:
        """Возвращает текущую дату-время для имени файла"""
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def save_to_file(self, folder: str, filename: str, content: str) -> str:
        """Сохраняет текст в файл"""
        filepath = self.base_folder / folder / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)  # на случай, если папку удалили после sync

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return str(filepath)

    def save_message(self, text: str, username: str, user_id: int) -> str:
        """Сохраняет текстовое сообщение в файл"""
        filename = f"{self.get_timestamp()}.md"

        content = f"""# Сообщение из Telegram

**Дата:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Пользователь:** @{username} [ID: {user_id}]
**Тип:** Текст

---

## Содержимое

{text}

---
"""

        return self.save_to_file("сообщения", filename, content)

    def save_transcript(self, transcript: str, source_type: str) -> str:
        """Сохраняет транскрипт в файл"""
        filename = f"{self.get_timestamp()}_{source_type}.md"

        content = f"""# Транскрипт из Telegram

**Дата:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Источник:** {source_type}

---

## Содержимое

{transcript}

---
"""

        return self.save_to_file("транскрипты", filename, content)

    def save_document(self, source_path: str, original_name: str) -> str:
        """Сохраняет документ в папку документы"""
        filename = f"{self.get_timestamp()}_{original_name}"
        dest_path = self.base_folder / "документы" / filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source_path, dest_path)

        return str(dest_path)

    def save_image(self, source_path: str, extension: str = "jpg") -> str:
        """Сохраняет изображение в папку изображения"""
        filename = f"image_{self.get_timestamp()}.{extension}"
        dest_path = self.base_folder / "изображения" / filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source_path, dest_path)

        return str(dest_path)

    def save_link(self, url: str, title: str = "") -> str:
        """Сохраняет ссылку в файл"""
        filename = f"{self.get_timestamp()}.md"

        content = f"""# Ссылка из Telegram

**Дата:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**URL:** {url}
**Заголовок:** {title or "Не определён"}

---
"""

        return self.save_to_file("ссылки", filename, content)

    def get_recent_files(self, limit: int = 10) -> list:
        """Возвращает список последних сохранённых файлов"""
        all_files = []

        for folder in ["сообщения", "транскрипты", "документы", "изображения", "ссылки"]:
            folder_path = self.base_folder / folder
            if folder_path.exists():
                for file in folder_path.iterdir():
                    if file.is_file():
                        all_files.append({
                            "path": str(file),
                            "name": file.name,
                            "folder": folder,
                            "modified": file.stat().st_mtime
                        })

        all_files.sort(key=lambda x: x["modified"], reverse=True)

        return all_files[:limit]
