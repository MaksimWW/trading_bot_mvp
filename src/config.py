import os

from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# API токены
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TINKOFF_TOKEN = os.getenv("TINKOFF_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Настройки Tinkoff API
TINKOFF_SANDBOX = True  # True для песочницы, False для реальной торговли
TINKOFF_APP_NAME = "TradingBotMVP"

# Торговые настройки
MAX_POSITION_SIZE = 0.05  # 5% от депозита на позицию
MAX_DAILY_LOSS = 0.03  # 3% максимальный дневной убыток
DEFAULT_STOP_LOSS = 0.07  # 7% стоп-лосс
DEFAULT_TAKE_PROFIT = 0.10  # 10% тейк-профит
