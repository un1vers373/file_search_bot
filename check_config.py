"""
Скрипт для проверки корректности настройки бота
Запустите перед первым запуском: python check_config.py
"""

import os
import sys
from pathlib import Path


def check_env_file():
    """Проверка наличия .env файла"""
    if not Path('.env').exists():
        print("❌ Файл .env не найден!")
        print("   Создайте его на основе .env.example:")
        print("   cp .env.example .env")
        return False
    print("✅ Файл .env найден")
    return True


def check_required_vars():
    """Проверка обязательных переменных окружения"""
    required_vars = {
        'BOT_TOKEN': 'Telegram Bot Token',
        'GOOGLE_API_KEY': 'Google API Key',
        'GOOGLE_CX': 'Google Custom Search Engine ID',
        'ADMIN_IDS': 'Admin User IDs'
    }

    missing = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value == f'your_{var.lower()}_here':
            missing.append(f"   • {var} ({description})")
            print(f"❌ {var} не установлен")
        else:
            # Скрываем секретные данные
            masked = value[:10] + '...' if len(value) > 10 else '***'
            print(f"✅ {var}: {masked}")

    if missing:
        print("\n⚠️  Необходимо установить следующие переменные:")
        print('\n'.join(missing))
        return False

    return True


def check_dependencies():
    """Проверка установленных зависимостей"""
    print("\n📦 Проверка зависимостей...")

    required_packages = {
        'aiogram': 'aiogram',
        'aiohttp': 'aiohttp',
        'dotenv': 'python-dotenv'
    }

    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"✅ {package} установлен")
        except ImportError:
            missing.append(package)
            print(f"❌ {package} не установлен")

    if missing:
        print(f"\n⚠️  Установите недостающие пакеты:")
        print(f"   pip install {' '.join(missing)}")
        return False

    return True


def check_database_access():
    """Проверка возможности создания базы данных"""
    print("\n💾 Проверка доступа к базе данных...")

    try:
        import sqlite3
        db_path = os.getenv('DB_PATH', 'search_cache.db')

        # Пробуем создать соединение
        conn = sqlite3.connect(db_path)
        conn.close()

        print(f"✅ База данных доступна: {db_path}")
        return True

    except Exception as e:
        print(f"❌ Ошибка доступа к базе данных: {e}")
        return False


def check_admin_ids():
    """Проверка формата ADMIN_IDS"""
    print("\n👤 Проверка ID администраторов...")

    admin_ids = os.getenv('ADMIN_IDS', '')
    if not admin_ids:
        print("⚠️  ADMIN_IDS не указаны (админ-команды будут недоступны)")
        return True

    try:
        ids = [int(uid.strip()) for uid in admin_ids.split(',')]
        print(f"✅ Найдено {len(ids)} администратор(ов): {ids}")
        return True
    except ValueError:
        print("❌ ADMIN_IDS содержат некорректные значения")
        print("   Формат: 123456789,987654321")
        return False


def main():
    """Основная функция проверки"""
    print("=" * 60)
    print("🔍 Проверка конфигурации File Search Bot")
    print("=" * 60)
    print()

    # Загружаем переменные окружения
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv не установлен, переменные из .env не загружены")

    checks = [
        ("Файл .env", check_env_file),
        ("Переменные окружения", check_required_vars),
        ("Зависимости", check_dependencies),
        ("База данных", check_database_access),
        ("ID администраторов", check_admin_ids)
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Ошибка при проверке '{name}': {e}")
            results.append(False)
        print()

    print("=" * 60)

    if all(results):
        print("🎉 Все проверки пройдены успешно!")
        print("   Вы можете запустить бота: python bot.py")
        return 0
    else:
        print("⚠️  Обнаружены проблемы с конфигурацией")
        print("   Устраните ошибки и повторите проверку")
        return 1


if __name__ == "__main__":
    sys.exit(main())