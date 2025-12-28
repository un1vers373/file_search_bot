"""
Telegram бот для поиска файлов и полезных ссылок
Использует aiogram 3.x
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from db import Database
from search import SearchEngine
from downloader import VideoDownloader

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
config = Config()
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()
search_engine = SearchEngine(config)
video_downloader = VideoDownloader()


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    return user_id in config.ADMIN_IDS


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    api_status = "✅ подключен" if config.GOOGLE_SEARCH_ENABLED else "⚠️ не настроен"

    welcome_text = (
        "👋 Привет! Я бот для поиска файлов и полезных ссылок.\n\n"
        f"🔌 Google Search API: {api_status}\n"
        f"🆔 Ваш Telegram ID: <code>{message.from_user.id}</code>\n\n"
        "📝 Доступные команды:\n"
        "/search <запрос> — поиск по ключевым словам\n"
        "/stats — статистика использования (только для админов)\n"
        "/clear_cache — очистить кеш (только для админов)\n"
        "/help — показать эту справку\n\n"
        "🎥 <b>Скачивание видео:</b>\n"
        "Просто отправьте ссылку на видео из:\n"
        "• Instagram (Reels, posts)\n"
        "• TikTok\n"
        "• YouTube\n"
        "• Twitter/X\n"
        "• Facebook\n\n"
    )

    if config.GOOGLE_SEARCH_ENABLED:
        welcome_text += "Пример: /search python tutorial"
    else:
        welcome_text += (
            "⚠️ Поиск недоступен. Администратор должен настроить:\n"
            "• GOOGLE_API_KEY\n"
            "• GOOGLE_CX"
        )

    await message.answer(welcome_text, parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "ℹ️ Справка по использованию бота\n\n"
        "🔍 <b>Поиск:</b>\n"
        "/search <запрос> — искать информацию по запросу\n\n"
        "Бот сначала ищет в локальном кеше, затем обращается к Google Custom Search API.\n\n"
        "📊 <b>Админ-команды:</b>\n"
        "/stats — показать статистику\n"
        "/clear_cache — очистить кеш поиска\n\n"
        "💡 Совет: чем конкретнее запрос, тем лучше результаты!"
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(Command("search"))
async def cmd_search(message: Message):
    """Обработчик команды /search"""
    # Проверяем доступность Google API
    if not config.GOOGLE_SEARCH_ENABLED:
        await message.answer(
            "⚠️ Поиск временно недоступен.\n\n"
            "Администратор должен настроить Google Custom Search API:\n"
            "1. Получить GOOGLE_API_KEY\n"
            "2. Получить GOOGLE_CX (Search Engine ID)\n"
            "3. Установить эти переменные окружения\n\n"
            "Подробности: https://developers.google.com/custom-search"
        )
        return

    # Извлекаем текст запроса после команды
    query = message.text.replace("/search", "").strip()

    if not query:
        await message.answer(
            "❌ Пожалуйста, укажите поисковый запрос.\n"
            "Пример: /search python asyncio"
        )
        return

    # Отправляем сообщение о начале поиска
    status_msg = await message.answer("🔍 Ищу информацию...")

    try:
        # Проверяем кеш
        cached_results = db.get_cached_results(query)

        if cached_results:
            logger.info(f"Найдены результаты в кеше для запроса: {query}")
            results = cached_results
            source = "📦 Из кеша"
        else:
            logger.info(f"Выполняю поиск через API для запроса: {query}")
            # Выполняем поиск через API
            results = await search_engine.search(query)

            if results:
                # Сохраняем результаты в кеш
                db.cache_results(query, results)

            source = "🌐 Из интернета"

        # Формируем ответ
        if results:
            response = f"{source}\n\n🔎 Результаты поиска по запросу: <b>{query}</b>\n\n"

            for idx, result in enumerate(results[:10], 1):  # Ограничиваем 10 результатами
                title = result.get('title', 'Без названия')
                link = result.get('link', '#')
                snippet = result.get('snippet', '')

                response += f"{idx}. <b>{title}</b>\n"
                response += f"🔗 {link}\n"
                if snippet:
                    response += f"📄 {snippet[:150]}...\n"
                response += "\n"

            # Telegram имеет лимит на длину сообщения (4096 символов)
            if len(response) > 4000:
                # Разбиваем на несколько сообщений
                parts = [response[i:i + 4000] for i in range(0, len(response), 4000)]
                await status_msg.delete()
                for part in parts:
                    await message.answer(part, parse_mode="HTML", disable_web_page_preview=True)
            else:
                await status_msg.edit_text(response, parse_mode="HTML", disable_web_page_preview=True)

            # Сохраняем статистику
            db.save_search_stats(message.from_user.id, query, len(results))

        else:
            await status_msg.edit_text(
                f"❌ По запросу <b>{query}</b> ничего не найдено.\n"
                "Попробуйте изменить формулировку.",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        await status_msg.edit_text(
            "⚠️ Произошла ошибка при поиске. Попробуйте позже."
        )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Обработчик команды /stats (только для админов)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    try:
        stats = db.get_stats()

        response = "📊 <b>Статистика бота</b>\n\n"
        response += f"🔢 Всего запросов: {stats['total_searches']}\n"
        response += f"👥 Уникальных пользователей: {stats['unique_users']}\n"
        response += f"💾 Записей в кеше: {stats['cached_queries']}\n\n"

        if stats['top_queries']:
            response += "🔥 <b>Топ-5 запросов:</b>\n"
            for idx, (query, count) in enumerate(stats['top_queries'], 1):
                response += f"{idx}. {query} — {count} раз(а)\n"

        await message.answer(response, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await message.answer("⚠️ Ошибка при получении статистики.")


@dp.message(Command("clear_cache"))
async def cmd_clear_cache(message: Message):
    """Обработчик команды /clear_cache (только для админов)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    try:
        db.clear_cache()
        await message.answer("✅ Кеш успешно очищен!")
        logger.info(f"Кеш очищен администратором {message.from_user.id}")

    except Exception as e:
        logger.error(f"Ошибка при очистке кеша: {e}")
        await message.answer("⚠️ Ошибка при очистке кеша.")


@dp.message()
async def handle_messages(message: Message):
    """Обработчик всех остальных сообщений"""

    # Проверяем, является ли сообщение ссылкой на видео
    if message.text and ('http://' in message.text or 'https://' in message.text):
        url = message.text.strip()

        # Проверяем поддерживаемые платформы
        if video_downloader.is_supported_url(url):
            status_msg = await message.answer("⏳ Загружаю видео...")

            try:
                # Скачиваем видео
                video_info = await video_downloader.download_video(url)

                if video_info:
                    filepath = video_info['filepath']

                    # Проверяем размер файла
                    if video_info['filesize'] > 50 * 1024 * 1024:  # 50 MB
                        await status_msg.edit_text(
                            "❌ Видео слишком большое (больше 50 MB).\n"
                            "Telegram не позволяет отправлять такие большие файлы."
                        )
                        video_downloader.cleanup_file(filepath)
                        return

                    # Отправляем видео
                    await status_msg.edit_text("📤 Отправляю видео...")

                    caption = (
                        f"🎥 <b>{video_info['title']}</b>\n"
                        f"📱 Платформа: {video_info['platform']}\n"
                        f"👤 Автор: {video_info['uploader']}\n"
                        f"📊 Размер: {video_info['filesize'] / (1024 * 1024):.1f} MB"
                    )

                    with open(filepath, 'rb') as video_file:
                        await message.answer_video(
                            video_file,
                            caption=caption,
                            parse_mode="HTML"
                        )

                    await status_msg.delete()

                    # Удаляем файл после отправки
                    video_downloader.cleanup_file(filepath)

                    logger.info(f"Видео успешно отправлено: {url}")
                else:
                    await status_msg.edit_text(
                        "❌ Не удалось скачать видео.\n"
                        "Возможные причины:\n"
                        "• Видео приватное\n"
                        "• Видео удалено\n"
                        "• Проблемы с сервером\n"
                        "• Видео слишком большое"
                    )

            except Exception as e:
                logger.error(f"Ошибка при обработке видео: {e}")
                await status_msg.edit_text(
                    "⚠️ Произошла ошибка при скачивании видео.\n"
                    "Попробуйте другую ссылку."
                )

            return

    # Если это не ссылка на видео
    await message.answer(
        "Используйте /search <запрос> для поиска или отправьте ссылку на видео для скачивания.\n\n"
        "Поддерживаемые платформы:\n"
        "🎥 Instagram, TikTok, YouTube, Twitter/X, Facebook"
    )


async def main():
    """Главная функция запуска бота"""
    logger.info("Запуск бота...")

    # Инициализация базы данных
    db.init_db()

    try:
        # Запуск polling
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")