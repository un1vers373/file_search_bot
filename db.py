"""
Модуль для работы с базой данных SQLite
Кеширование результатов поиска и статистика
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""

    def __init__(self, db_path: str = "search_cache.db"):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для работы с соединением БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Таблица для кеширования результатов поиска
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    results TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(query)
                )
            """)

            # Таблица для статистики поисковых запросов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    query TEXT NOT NULL,
                    results_count INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Индексы для ускорения поиска
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query 
                ON search_cache(query)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_query 
                ON search_stats(user_id, query)
            """)

            conn.commit()
            logger.info("База данных инициализирована")

    def get_cached_results(self, query: str, expire_days: int = 7) -> Optional[List[Dict]]:
        """
        Получить результаты из кеша

        Args:
            query: поисковый запрос
            expire_days: срок жизни кеша в днях

        Returns:
            Список результатов или None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Нормализуем запрос (приводим к нижнему регистру)
            normalized_query = query.lower().strip()

            # Проверяем кеш с учетом срока давности
            expire_date = datetime.now() - timedelta(days=expire_days)

            cursor.execute("""
                SELECT results FROM search_cache
                WHERE LOWER(query) = ? AND created_at > ?
            """, (normalized_query, expire_date))

            row = cursor.fetchone()

            if row:
                try:
                    results = json.loads(row['results'])
                    logger.info(f"Найдены результаты в кеше для запроса: {query}")
                    return results
                except json.JSONDecodeError:
                    logger.error(f"Ошибка декодирования JSON для запроса: {query}")
                    return None

            return None

    def cache_results(self, query: str, results: List[Dict]):
        """
        Сохранить результаты в кеш

        Args:
            query: поисковый запрос
            results: список результатов поиска
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Нормализуем запрос
            normalized_query = query.lower().strip()
            results_json = json.dumps(results, ensure_ascii=False)

            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO search_cache (query, results)
                    VALUES (?, ?)
                """, (normalized_query, results_json))

                conn.commit()
                logger.info(f"Результаты сохранены в кеш для запроса: {query}")

            except sqlite3.Error as e:
                logger.error(f"Ошибка при сохранении в кеш: {e}")

    def save_search_stats(self, user_id: int, query: str, results_count: int):
        """
        Сохранить статистику поискового запроса

        Args:
            user_id: ID пользователя Telegram
            query: поисковый запрос
            results_count: количество найденных результатов
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO search_stats (user_id, query, results_count)
                    VALUES (?, ?, ?)
                """, (user_id, query, results_count))

                conn.commit()
                logger.info(f"Статистика сохранена: user={user_id}, query={query}")

            except sqlite3.Error as e:
                logger.error(f"Ошибка при сохранении статистики: {e}")

    def get_stats(self) -> Dict:
        """
        Получить общую статистику использования бота

        Returns:
            Словарь со статистикой
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Общее количество запросов
            cursor.execute("SELECT COUNT(*) as total FROM search_stats")
            total_searches = cursor.fetchone()['total']

            # Количество уникальных пользователей
            cursor.execute("SELECT COUNT(DISTINCT user_id) as unique FROM search_stats")
            unique_users = cursor.fetchone()['unique']

            # Количество записей в кеше
            cursor.execute("SELECT COUNT(*) as cached FROM search_cache")
            cached_queries = cursor.fetchone()['cached']

            # Топ-5 популярных запросов
            cursor.execute("""
                SELECT query, COUNT(*) as count
                FROM search_stats
                GROUP BY query
                ORDER BY count DESC
                LIMIT 5
            """)
            top_queries = [(row['query'], row['count']) for row in cursor.fetchall()]

            return {
                'total_searches': total_searches,
                'unique_users': unique_users,
                'cached_queries': cached_queries,
                'top_queries': top_queries
            }

    def clear_cache(self):
        """Очистить весь кеш результатов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM search_cache")
            conn.commit()
            logger.info("Кеш очищен")

    def clear_old_cache(self, days: int = 30):
        """
        Очистить устаревший кеш

        Args:
            days: удалить записи старше указанного количества дней
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            expire_date = datetime.now() - timedelta(days=days)

            cursor.execute("""
                DELETE FROM search_cache
                WHERE created_at < ?
            """, (expire_date,))

            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"Удалено {deleted_count} устаревших записей из кеша")
            return deleted_count