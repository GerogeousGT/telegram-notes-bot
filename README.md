# Telegram AI Assistant Bot

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)
![Groq](https://img.shields.io/badge/AI-Groq%20%2F%20Yandex-orange)
![AssemblyAI](https://img.shields.io/badge/STT-AssemblyAI-purple)
![License](https://img.shields.io/badge/license-MIT-green)

Личный AI-ассистент в Telegram. Ведёт диалог, транскрибирует голосовые и видео, сохраняет заметки по команде, ищет по ним и управляет категориями — всё через естественный язык. Поддерживает переключение между AI-моделями прямо из чата.

## Проблема

Голосовые заметки, мысли на ходу, ссылки, цитаты из разговоров — всё это теряется или оседает в разных местах. Нужен один инструмент, который всегда под рукой (Telegram), понимает голос и текст, и сохраняет только то, что ты явно попросил сохранить.

## Решение

Бот работает в режиме постоянного диалога. Ты пишешь или говоришь — он отвечает. Хочешь сохранить — говоришь "сохрани это". Хочешь найти — говоришь "найди про встречу". Хочешь новую категорию — говоришь "создай категорию идеи".

## Возможности

### AI-диалог

| Действие | Пример фразы |
|---|---|
| Обычный диалог | Любой текст или голосовое |
| Сохранить заметку | "Сохрани это в заметки" |
| Сохранить в категорию | "Сохрани в категорию клиенты: Иван, +7 999 123-45-67" |
| Поиск по заметкам | "Найди про встречу с Иваном" |
| Создать категорию | "Создай категорию идеи" |
| Список категорий | "Какие у меня категории?" |

### Медиа

| Тип | Что происходит |
|---|---|
| Текст | AI отвечает в диалоге |
| Голосовое / аудио | Транскрибирует → показывает текст → AI отвечает |
| Видео / круглое видео | Транскрибирует → показывает текст → AI отвечает |
| Ссылка на YouTube / Instagram / TikTok | Скачивает и транскрибирует |
| Документ | Сохраняет файл + подпись рядом |
| Фото | Сохраняет + подпись рядом |

> Без `DEEPSEEK_API_KEY` бот работает в режиме сохранения: всё входящее автоматически сохраняется в файлы.

## Стек

- **Python 3.10+** + `python-telegram-bot 21`
- **Groq API** (Llama 3.3 70b) — AI-диалог и function calling, модель по умолчанию
- **Yandex AI Studio** (YandexGPT Lite) — альтернативная модель, переключается командой `/model`
- **AssemblyAI** — транскрибация речи
- **yt-dlp** — скачивание видео по ссылкам
- **VPS** (Ubuntu) + **systemd** — деплой и автозапуск

## Структура

```
telegram-notes-bot/
├── bot.py                  — точка входа
├── config.py               — конфигурация из .env
├── handlers/
│   ├── commands.py         — /start /help /clear /status /sync /log /list /model
│   ├── messages.py         — обработка всех типов сообщений
│   └── utils.py            — проверка доступа
├── services/
│   ├── ai_assistant.py     — мульти-провайдер AI (Groq / Yandex), history, function calling
│   ├── file_saver.py       — сохранение файлов, управление категориями
│   ├── transcriber.py      — транскрибация через AssemblyAI
│   └── sync_manager.py     — логи и статистика
└── scripts/
    ├── restart-bot.ps1     — перезапуск на VPS
    └── sync-bot.ps1        — синхронизация данных с VPS (rclone copy)
```

## Быстрый старт

```bash
git clone https://github.com/GerogeousGT/telegram-notes-bot.git
cd telegram-notes-bot
pip install -r requirements.txt
cp .env.example .env
# заполни .env своими ключами
python bot.py
```

## Переменные окружения

| Переменная | Обязательная | Описание |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | да | Токен от @BotFather |
| `ADMIN_ID` | да | Telegram User ID (только ты получаешь доступ) |
| `ASSEMBLYAI_KEY` | да | [assemblyai.com](https://www.assemblyai.com) |
| `GROQ_API_KEY` | нет | [console.groq.com](https://console.groq.com) — модель по умолчанию (Llama 3.3) |
| `YANDEX_API_KEY` | нет | Создать в [aistudio.yandex.ru](https://aistudio.yandex.ru) |
| `YANDEX_FOLDER_ID` | нет | ID каталога в Яндекс Cloud Console (нужен вместе с `YANDEX_API_KEY`) |
| `DEEPSEEK_API_KEY` | нет | [platform.deepseek.com](https://platform.deepseek.com) — бесплатный tier |
| `DATA_FOLDER` | нет | Путь к папке с данными (по умолчанию `./Распределение`) |

## Команды

| Команда | Действие |
|---|---|
| `/start` | Статус и список возможностей |
| `/help` | Справка |
| `/clear` | Сбросить историю диалога с AI |
| `/status` | Путь к папке данных |
| `/sync` | Статистика обработанных сообщений |
| `/log` | Последние 10 записей лога |
| `/list` | Последние 10 сохранённых файлов |
| `/model` | Переключить AI-модель (Groq / YandexGPT) |

## Деплой на VPS

```powershell
# Скопировать изменённые файлы на VPS
scp config.py vps:/home/deploy/bots/telegram-bot/
scp services/ai_assistant.py vps:/home/deploy/bots/telegram-bot/services/
scp handlers/commands.py vps:/home/deploy/bots/telegram-bot/handlers/
scp bot.py vps:/home/deploy/bots/telegram-bot/

# Перезапустить бота (только через systemctl — не руками!)
ssh vps "systemctl restart telegram-bot"

# Проверить статус
ssh vps "systemctl status telegram-bot"

# Скопировать данные с VPS на локальный диск (файлы на сервере сохраняются)
.\scripts\sync-bot.ps1
```

Бот управляется через systemd-сервис `telegram-bot.service` с `Restart=always`.

> **Важно:** никогда не запускать бота руками через `nohup python3 bot.py &` — systemd уже держит процесс, ручной старт создаёт дубль и вызывает Telegram Conflict. Единственная команда перезапуска: `systemctl restart telegram-bot`.
