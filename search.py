"""
Модуль для поиска через Google Custom Search API
В будущем можно добавить поддержку YouTube и Google Drive
"""

import aiohttp
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class SearchEngine:
    """Класс для работы с поисковыми API"""

    def __init__(self, config):
        self.config = config
        self.google_search_url = "https://www.googleapis.com/customsearch/v1"

    async def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Выполнить поиск через Google Custom Search API

        Args:
            query: поисковый запрос
            num_results: количество результатов (максимум 10 за запрос)

        Returns:
            Список результатов поиска
        """
        try:
            results = await self._google_search(query, num_results)
            return results

        except Exception as e:
            logger.error(f"Ошибка при поиске: {e}")
            return []

    async def _google_search(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Поиск через Google Custom Search API

        Args:
            query: поисковый запрос
            num_results: количество результатов

        Returns:
            Список результатов
        """
        params = {
            'key': self.config.GOOGLE_API_KEY,
            'cx': self.config.GOOGLE_CX,
            'q': query,
            'num': min(num_results, 10)  # Google API позволяет максимум 10
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.google_search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_google_results(data)
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка Google API: {response.status}, {error_text}")
                        return []

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка HTTP запроса: {e}")
            return []
        except Exception as e:
            logger.error(f"Неожиданная ошибка при поиске: {e}")
            return []

    def _parse_google_results(self, data: Dict) -> List[Dict]:
        """
        Парсинг результатов от Google Custom Search API

        Args:
            data: JSON ответ от API

        Returns:
            Список обработанных результатов
        """
        results = []

        if 'items' not in data:
            logger.warning("В ответе API отсутствуют результаты")
            return results

        for item in data['items']:
            result = {
                'title': item.get('title', 'Без названия'),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'displayLink': item.get('displayLink', ''),
            }

            # Добавляем информацию об изображении, если есть
            if 'pagemap' in item and 'cse_image' in item['pagemap']:
                images = item['pagemap']['cse_image']
                if images:
                    result['image'] = images[0].get('src', '')

            results.append(result)

        logger.info(f"Обработано {len(results)} результатов из Google API")
        return results

    async def youtube_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Поиск видео на YouTube (для будущей реализации)

        Args:
            query: поисковый запрос
            max_results: максимальное количество результатов

        Returns:
            Список видео
        """
        if not self.config.YOUTUBE_API_KEY:
            logger.warning("YouTube API ключ не настроен")
            return []

        # TODO: Реализовать поиск через YouTube Data API v3
        # Пример: https://www.googleapis.com/youtube/v3/search

        logger.info("YouTube поиск пока не реализован")
        return []

    async def drive_search(self, query: str) -> List[Dict]:
        """
        Поиск файлов в Google Drive (для будущей реализации)

        Args:
            query: поисковый запрос

        Returns:
            Список файлов
        """
        if not self.config.GOOGLE_DRIVE_CREDENTIALS:
            logger.warning("Google Drive credentials не настроены")
            return []

        # TODO: Реализовать поиск через Google Drive API v3
        # Требуется OAuth2 аутентификация

        logger.info("Google Drive поиск пока не реализован")
        return []


class MultiSearchEngine(SearchEngine):
    """
    Расширенный поисковый движок с поддержкой нескольких источников
    Для будущего использования
    """

    async def search_all(self, query: str) -> Dict[str, List[Dict]]:
        """
        Поиск по всем доступным источникам

        Args:
            query: поисковый запрос

        Returns:
            Словарь с результатами по каждому источнику
        """
        results = {
            'google': [],
            'youtube': [],
            'drive': []
        }

        # Параллельный поиск по всем источникам
        import asyncio

        google_task = self.search(query)
        youtube_task = self.youtube_search(query)
        drive_task = self.drive_search(query)

        google_results, youtube_results, drive_results = await asyncio.gather(
            google_task,
            youtube_task,
            drive_task,
            return_exceptions=True
        )

        # Обработка результатов с учетом возможных ошибок
        if not isinstance(google_results, Exception):
            results['google'] = google_results

        if not isinstance(youtube_results, Exception):
            results['youtube'] = youtube_results

        if not isinstance(drive_results, Exception):
            results['drive'] = drive_results

        return results