"""
Модуль для скачивания видео из различных социальных сетей
Использует yt-dlp для универсального скачивания
"""

import os
import logging
from typing import Optional, Dict
import yt_dlp

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Класс для скачивания видео с различных платформ"""

    def __init__(self, download_path: str = "/tmp"):
        self.download_path = download_path

        # Создаём папку для загрузок если её нет
        os.makedirs(download_path, exist_ok=True)

    def is_supported_url(self, url: str) -> bool:
        """
        Проверка поддерживается ли URL

        Args:
            url: ссылка на видео

        Returns:
            True если поддерживается
        """
        supported_domains = [
            'instagram.com',
            'tiktok.com',
            # 'youtube.com',  # Временно отключен из-за блокировок
            # 'youtu.be',
            'twitter.com',
            'x.com',
            'facebook.com',
            'fb.watch',
            'reddit.com',
            'vimeo.com'
        ]

        return any(domain in url.lower() for domain in supported_domains)

    async def download_video(self, url: str) -> Optional[Dict]:
        """
        Скачать видео по URL

        Args:
            url: ссылка на видео

        Returns:
            Словарь с информацией о файле или None при ошибке
        """
        try:
            # Настройки для yt-dlp
            ydl_opts = {
                'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
                'outtmpl': os.path.join(self.download_path, '%(id)s.%(ext)s'),
                'quiet': False,  # Включаем вывод для отладки
                'no_warnings': False,
                'extract_flat': False,
                'nocheckcertificate': True,
                'ignoreerrors': False,
                'no_color': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }

            # Извлекаем информацию о видео
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Получаю информацию о видео: {url}")
                info = ydl.extract_info(url, download=True)

                if info:
                    filename = ydl.prepare_filename(info)
                    file_size = os.path.getsize(filename)

                    # Проверяем размер файла
                    if file_size > 50 * 1024 * 1024:  # 50 MB
                        logger.warning(f"Файл слишком большой: {file_size} bytes")
                        if os.path.exists(filename):
                            os.remove(filename)
                        return None

                    result = {
                        'filepath': filename,
                        'title': info.get('title', 'video'),
                        'duration': info.get('duration', 0),
                        'thumbnail': info.get('thumbnail'),
                        'uploader': info.get('uploader', 'Unknown'),
                        'filesize': file_size,
                        'platform': self._detect_platform(url)
                    }

                    logger.info(f"Видео успешно скачано: {filename}")
                    return result
                else:
                    logger.error("Не удалось получить информацию о видео")
                    return None

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Ошибка скачивания: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            return None

    def _detect_platform(self, url: str) -> str:
        """Определить платформу по URL"""
        url_lower = url.lower()

        if 'instagram.com' in url_lower:
            return 'Instagram'
        elif 'tiktok.com' in url_lower:
            return 'TikTok'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'YouTube'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'Twitter/X'
        elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
            return 'Facebook'
        elif 'reddit.com' in url_lower:
            return 'Reddit'
        elif 'vimeo.com' in url_lower:
            return 'Vimeo'
        else:
            return 'Unknown'

    def cleanup_file(self, filepath: str):
        """
        Удалить скачанный файл

        Args:
            filepath: путь к файлу
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Файл удалён: {filepath}")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла: {e}")