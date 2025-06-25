from tinkoff_invest import SandboxSession, ProductionSession
from tinkoff_invest.models import GetAccountsRequest, GetPortfolioRequest, FindInstrumentRequest, GetLastPricesRequest
from config import TINKOFF_TOKEN, TINKOFF_SANDBOX, TINKOFF_APP_NAME
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TinkoffClient:
    """Клиент для работы с Tinkoff Invest API"""

    def __init__(self):
        self.token = TINKOFF_TOKEN
        self.is_sandbox = TINKOFF_SANDBOX
        self.session = None
        self.connect()

    def connect(self):
        """Подключение к API"""
        try:
            if self.is_sandbox:
                self.session = SandboxSession(self.token)
                logger.info("Подключение к песочнице Tinkoff успешно")
            else:
                self.session = ProductionSession(self.token)
                logger.info("Подключение к боевому API Tinkoff")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к Tinkoff API: {e}")
            return False

    def get_accounts(self):
        """Получение списка счетов"""
        try:
            if not self.session:
                logger.error("Сессия не подключена")
                return None

            request = GetAccountsRequest()
            accounts = self.session.users.get_accounts(request)
            logger.info(f"Найдено счетов: {len(accounts.accounts)}")
            return accounts.accounts
        except Exception as e:
            logger.error(f"Ошибка получения счетов: {e}")
            return None

    def search_instrument(self, ticker):
        """Поиск инструмента по тикеру"""
        try:
            request = FindInstrumentRequest(query=ticker)
            response = self.session.instruments.find_instrument(request)
            if response.instruments:
                logger.info(f"Найден инструмент: {ticker}")
                return response.instruments[0]
            else:
                logger.warning(f"Инструмент {ticker} не найден")
                return None
        except Exception as e:
            logger.error(f"Ошибка поиска инструмента {ticker}: {e}")
            return None

    def get_last_price(self, figi):
        """Получение последней цены по FIGI"""
        try:
            request = GetLastPricesRequest(figi=[figi])
            response = self.session.market_data.get_last_prices(request)
            if response.last_prices:
                price = response.last_prices[0]
                logger.info(f"Цена получена для FIGI {figi}")
                return price
            return None
        except Exception as e:
            logger.error(f"Ошибка получения цены для FIGI {figi}: {e}")
            return None

# Тестовая функция
def test_connection():
    """Тестирование подключения"""
    print("🔄 Тестирование подключения к Tinkoff API...")

    client = TinkoffClient()

    # Тест 1: Получение счетов
    print("\n📊 Тест 1: Получение счетов")
    accounts = client.get_accounts()
    if accounts:
        print(f"✅ Успешно! Найдено счетов: {len(accounts)}")
        for acc in accounts:
            print(f"  - ID счета: {acc.id}")
            print(f"  - Название: {acc.name}")
    else:
        print("❌ Ошибка получения счетов")
        return

    # Тест 2: Поиск инструмента SBER
    print("\n🔍 Тест 2: Поиск акции SBER")
    sber = client.search_instrument("SBER")
    if sber:
        print(f"✅ Успешно! Найдена акция:")
        print(f"  - Название: {sber.name}")
        print(f"  - FIGI: {sber.figi}")
        print(f"  - Тикер: {sber.ticker}")

        # Тест 3: Получение цены
        print("\n💰 Тест 3: Получение цены SBER")
        price = client.get_last_price(sber.figi)
        if price:
            # Конвертируем цену (в копейках) в рубли
            price_rub = price.price.units + price.price.nano / 1_000_000_000
            print(f"✅ Успешно! Цена SBER: {price_rub:.2f} ₽")
        else:
            print("❌ Ошибка получения цены")
    else:
        print("❌ Ошибка поиска SBER")

    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    test_connection()