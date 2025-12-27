"""
Конфигурация бота
Все чувствительные данные загружаются из переменных окружения
"""

import os
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (если он есть)
load_dotenv()


class Config:
    """Класс конфигурации бота"""

    def __init__(self):
        # Telegram Bot Token
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в переменных окружения")

        # Google Custom Search API
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        self.GOOGLE_CX = os.getenv("GOOGLE_CX")  # Custom Search Engine ID

        # Проверяем наличие Google API (но не делаем обязательным)
        self.GOOGLE_SEARCH_ENABLED = bool(self.GOOGLE_API_KEY and self.GOOGLE_CX)

        if not self.GOOGLE_SEARCH_ENABLED:
            import logging
            logging.warning(
                "⚠️ GOOGLE_API_KEY или GOOGLE_CX не установлены! "
                "Поиск через Google будет недоступен. "
                "Установите эти переменные для работы поиска."
            )

        # ID администраторов (список через запятую)
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS: List[int] = []

        if admin_ids_str:
            try:
                self.ADMIN_IDS = [int(uid.strip()) for uid in admin_ids_str.split(",")]
            except ValueError:
                raise ValueError("ADMIN_IDS должны быть числами, разделенными запятыми")

        # Путь к базе данных SQLite
        self.DB_PATH = os.getenv("DB_PATH", "search_cache.db")

        # Настройки поиска
        self.SEARCH_RESULTS_LIMIT = int(os.getenv("SEARCH_RESULTS_LIMIT", "10"))
        self.CACHE_EXPIRE_DAYS = int(os.getenv("CACHE_EXPIRE_DAYS", "7"))

        # YouTube API (для будущего расширения)
        self.YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

        # Google Drive API (для будущего расширения)
        self.GOOGLE_DRIVE_CREDENTIALS = os.getenv("GOOGLE_DRIVE_CREDENTIALS")

    def __repr__(self):
        """Безопасное представление конфигурации (без секретов)"""
        return (
            f"Config(BOT_TOKEN={'***' if self.BOT_TOKEN else 'NOT SET'}, "
            f"GOOGLE_API_KEY={'***' if self.GOOGLE_API_KEY else 'NOT SET'}, "
            f"ADMIN_IDS={self.ADMIN_IDS}, "
            f"DB_PATH={self.DB_PATH})"
        )