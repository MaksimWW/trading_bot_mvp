import os

from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# API токены
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TINKOFF_TOKEN = os.getenv("TINKOFF_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Настройки Tinkoff API
TINKOFF_SANDBOX = True  # True для песочницы, False для реальной торговли
TINKOFF_APP_NAME = "TradingBotMVP"

# Торговые настройки
MAX_POSITION_SIZE = 0.05  # 5% от депозита на позицию
MAX_DAILY_LOSS = 0.03  # 3% максимальный дневной убыток
DEFAULT_STOP_LOSS = 0.07  # 7% стоп-лосс
DEFAULT_TAKE_PROFIT = 0.10  # 10% тейк-профит

# ==== PORTFOLIO CONFIGURATION ====
PORTFOLIO_CONFIG = {
    # Виртуальный депозит для симуляции
    "initial_balance": 1_000_000,  # 1 млн рублей
    # Риск-менеджмент (используем существующие переменные)
    "max_position_size": MAX_POSITION_SIZE,  # 5% от депозита
    "max_daily_loss": MAX_DAILY_LOSS,  # 3% максимальный дневной убыток
    "default_stop_loss": DEFAULT_STOP_LOSS,  # 7% стоп-лосс
    "default_take_profit": DEFAULT_TAKE_PROFIT,  # 10% тейк-профит
    # Новые настройки
    "max_daily_trades": 5,  # Максимум 5 сделок в день
    "commission_rate": 0.0005,  # 0.05% комиссия брокера
    # Торговые часы МСК
    "market_open": "10:00",
    "market_close": "19:00",
    "force_close_time": "18:50",
    # Настройки портфеля
    "auto_save": True,
    "save_interval": 300,  # 5 минут
    "max_positions": 20,
    "min_trade_amount": 1000,  # 1,000 ₽
}

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Настройки Strategy Engine
STRATEGY_CONFIG = {
    "max_active_strategies": 5,
    "signal_history_limit": 1000,
    "auto_execution_enabled": False,
    "default_position_size_pct": 0.02,  # 2% от портфеля
    "risk_management": {
        "max_daily_trades": 10,
        "max_position_risk": 0.05,  # 5% от депозита на позицию
        "min_confidence_threshold": 0.6,
    },
}


# Функция для получения информации о тикерах
def get_ticker_info(ticker):
    """Получение информации о тикере."""
    ticker_data = {
        "SBER": {
            "name": "ПАО Сбербанк",
            "sector": "Банки",
            "description": "Крупнейший банк России",
        },
        "GAZP": {
            "name": "ПАО Газпром",
            "sector": "Энергетика",
            "description": "Крупнейшая газовая компания",
        },
        "YNDX": {"name": "Яндекс", "sector": "IT", "description": "Технологическая компания"},
        "LKOH": {"name": "ЛУКОЙЛ", "sector": "Нефтегаз", "description": "Нефтяная компания"},
        "NVTK": {"name": "НОВАТЭК", "sector": "Нефтегаз", "description": "Газовая компания"},
        "ROSN": {"name": "Роснефть", "sector": "Нефтегаз", "description": "Нефтяная компания"},
        "GMKN": {
            "name": "ГМК Норильский никель",
            "sector": "Металлургия",
            "description": "Горно-металлургическая компания",
        },
    }

    return ticker_data.get(
        ticker.upper(),
        {
            "name": f"Акция {ticker}",
            "sector": "Неизвестный",
            "description": "Информация отсутствует",
        },
    )
