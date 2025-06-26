
"""
Главный модуль торгового бота
Точка входа для запуска Trading Bot MVP с Telegram интерфейсом
"""

import logging
import os
import sys
from dotenv import load_dotenv

from telegram_bot import TradingTelegramBot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/trading_bot.log", encoding="utf-8")
    ]
)

logger = logging.getLogger(__name__)


def mask_token(token: str) -> str:
    """Маскирует токен для безопасного логирования"""
    if not token or len(token) < 8:
        return "***INVALID***"
    return f"***{token[-4:]}"


def check_environment() -> bool:
    """Проверяет наличие необходимых переменных окружения"""
    logger.info("🔍 Проверка переменных окружения...")
    
    # Обязательные токены
    required_tokens = {
        "TELEGRAM_TOKEN": "Telegram Bot API token",
        "TINKOFF_TOKEN": "Tinkoff Invest API token"
    }
    
    # Дополнительные токены
    optional_tokens = {
        "PERPLEXITY_API_KEY": "Perplexity API для новостей",
        "OPENAI_API_KEY": "OpenAI API для анализа новостей"
    }
    
    missing_required = []
    
    # Проверяем обязательные токены
    for token_name, description in required_tokens.items():
        token_value = os.getenv(token_name)
        if token_value:
            logger.info(f"✅ {description}: {mask_token(token_value)}")
        else:
            logger.error(f"❌ {description}: НЕ НАЙДЕН")
            missing_required.append(token_name)
    
    # Проверяем дополнительные токены
    for token_name, description in optional_tokens.items():
        token_value = os.getenv(token_name)
        if token_value:
            logger.info(f"✅ {description}: {mask_token(token_value)}")
        else:
            logger.warning(f"⚠️ {description}: не настроен (опционально)")
    
    if missing_required:
        logger.error(f"❌ Отсутствуют обязательные токены: {', '.join(missing_required)}")
        logger.error("💡 Создайте .env файл на основе .env.example и добавьте токены")
        return False
    
    logger.info("✅ Все обязательные переменные окружения настроены")
    return True


def create_directories():
    """Создает необходимые директории для работы бота"""
    directories = ["logs", "data"]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"📁 Создана директория: {directory}")


def main():
    """Главная функция для запуска торгового бота"""
    try:
        logger.info("🚀 Запуск Trading Bot MVP...")
        logger.info("=" * 50)
        
        # Создаем необходимые директории
        create_directories()
        
        # Загружаем переменные окружения из .env файла
        logger.info("📋 Загрузка переменных окружения...")
        load_dotenv()
        
        # Проверяем наличие необходимых токенов
        if not check_environment():
            logger.error("❌ Не удалось запустить бота: отсутствуют обязательные токены")
            print("\n❌ ОШИБКА: Не настроены API токены!")
            print("💡 Скопируйте .env.example в .env и добавьте ваши токены:")
            print("   • TELEGRAM_TOKEN - токен Telegram бота")
            print("   • TINKOFF_TOKEN - токен Tinkoff Invest API")
            return 1
        
        logger.info("=" * 50)
        logger.info("🤖 Инициализация Trading Telegram Bot...")
        
        # Инициализируем и запускаем бота
        bot = TradingTelegramBot()
        
        logger.info("🎯 Бот успешно инициализирован")
        logger.info("🔗 Подключение к Telegram API...")
        logger.info("📈 Подключение к Tinkoff Invest API...")
        logger.info("=" * 50)
        
        print("🤖 Trading Bot MVP запускается...")
        print("📱 Найдите вашего бота в Telegram и отправьте /start")
        print("🛡️ Режим работы: Безопасная песочница Tinkoff")
        print("⏹️ Для остановки нажмите Ctrl+C")
        print("=" * 50)
        
        # Запускаем бота (блокирующий вызов)
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Получен сигнал остановки (Ctrl+C)")
        print("\n⏹️ Бот остановлен пользователем")
        return 0
        
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта модулей: {e}")
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Проверьте, что все зависимости установлены: pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка запуска: {e}", exc_info=True)
        print(f"❌ Критическая ошибка: {e}")
        print("📋 Подробности в логах: logs/trading_bot.log")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
