"""
Улучшенный клиент для работы с Tinkoff Invest API
Включает получение исторических данных для технического анализа
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from tinkoff.invest import Client
from tinkoff.invest.constants import INVEST_GRPC_API_SANDBOX
from tinkoff.invest.schemas import CandleInterval

from config import TINKOFF_SANDBOX, TINKOFF_TOKEN

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Candle:
    """Класс для представления свечи."""

    open: float
    high: float
    low: float
    close: float
    volume: int
    time: datetime

    def __post_init__(self):
        """Валидация данных свечи после инициализации."""
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            logger.warning(
                f"Некорректные данные свечи: high={self.high}, low={self.low}, open={self.open}, close={self.close}"
            )


class TinkoffClient:
    """Улучшенный клиент для работы с Tinkoff Invest API"""

    def __init__(self):
        self.token = TINKOFF_TOKEN
        self.is_sandbox = TINKOFF_SANDBOX

        # Валидация токена
        if not self.token:
            raise ValueError("TINKOFF_TOKEN не установлен в переменных окружения")

        logger.info(
            f"TinkoffClient инициализирован. Режим: {'Песочница' if self.is_sandbox else 'Продакшен'}"
        )

    def _get_client_target(self):
        """Получение целевого URL для подключения к API."""
        return INVEST_GRPC_API_SANDBOX if self.is_sandbox else None

    def get_accounts(self):
        """Получение списка счетов"""
        try:
            target = self._get_client_target()

            with Client(self.token, target=target) as client:
                accounts = client.users.get_accounts()
                logger.info(f"Найдено счетов: {len(accounts.accounts)}")
                return accounts.accounts

        except Exception as e:
            logger.error(f"Ошибка получения счетов: {e}")
            return None

    def search_instrument(self, ticker: str) -> Optional[Dict]:
        """Поиск инструмента по тикеру"""
        try:
            target = self._get_client_target()

            with Client(self.token, target=target) as client:
                # Поиск акций по тикеру
                shares = client.instruments.shares()

                # Сначала ищем точное совпадение тикера
                for share in shares.instruments:
                    if share.ticker.upper() == ticker.upper():
                        if share.api_trade_available_flag:  # Только торгуемые
                            instrument = {
                                "figi": share.figi,
                                "ticker": share.ticker,
                                "name": share.name,
                                "currency": share.currency,
                                "lot": share.lot,
                                "class_code": share.class_code,
                            }
                            logger.info(f"Найден инструмент: {share.name} ({share.figi})")
                            return instrument

                # Если точного совпадения нет, ищем по части названия
                for share in shares.instruments:
                    if (
                        ticker.upper() in share.name.upper()
                        or ticker.upper() in share.ticker.upper()
                    ):
                        if share.api_trade_available_flag:
                            instrument = {
                                "figi": share.figi,
                                "ticker": share.ticker,
                                "name": share.name,
                                "currency": share.currency,
                                "lot": share.lot,
                                "class_code": share.class_code,
                            }
                            logger.info(f"Найден инструмент: {share.name} ({share.figi})")
                            return instrument

                logger.warning(f"Инструмент {ticker} не найден среди торгуемых акций")
                return None

        except Exception as e:
            logger.error(f"Ошибка поиска инструмента {ticker}: {e}")
            return None

    def get_last_price(self, figi):
        """Получение последней цены по FIGI"""
        try:
            target = self._get_client_target()

            with Client(self.token, target=target) as client:
                response = client.market_data.get_last_prices(figi=[figi])
                if response.last_prices:
                    price = response.last_prices[0]
                    logger.debug(f"Цена получена для FIGI {figi}")
                    return price
                return None

        except Exception as e:
            logger.error(f"Ошибка получения цены для FIGI {figi}: {e}")
            return None

    def get_historical_candles(
        self,
        figi: str,
        days: int = 100,
        interval: CandleInterval = CandleInterval.CANDLE_INTERVAL_DAY,
    ) -> List[Candle]:
        """
        Получение исторических свечей для инструмента.

        Args:
            figi: Идентификатор инструмента
            days: Количество дней назад для получения данных
            interval: Интервал свечей

        Returns:
            Список объектов Candle
        """
        try:
            target = self._get_client_target()

            # Рассчитываем временной диапазон
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)

            logger.info(
                f"Получение свечей для FIGI {figi} с {from_date.date()} по {to_date.date()}"
            )

            with Client(self.token, target=target) as client:
                response = client.market_data.get_candles(
                    figi=figi, from_=from_date, to=to_date, interval=interval
                )

                candles = []
                for candle_data in response.candles:
                    try:
                        # Конвертируем цены из Quotation в float
                        open_price = self._quotation_to_float(candle_data.open)
                        high_price = self._quotation_to_float(candle_data.high)
                        low_price = self._quotation_to_float(candle_data.low)
                        close_price = self._quotation_to_float(candle_data.close)
                        volume = candle_data.volume
                        time = candle_data.time

                        candle = Candle(
                            open=open_price,
                            high=high_price,
                            low=low_price,
                            close=close_price,
                            volume=volume,
                            time=time,
                        )
                        candles.append(candle)

                    except Exception as e:
                        logger.warning(f"Ошибка обработки свечи: {e}")
                        continue

                logger.info(f"Получено {len(candles)} свечей для {figi}")
                return candles

        except Exception as e:
            logger.error(f"Ошибка получения исторических данных для {figi}: {e}")
            return []

    def get_price_history(self, ticker: str, days: int = 100) -> List[float]:
        """
        Получение истории цен закрытия для тикера.

        Args:
            ticker: Тикер инструмента
            days: Количество дней назад

        Returns:
            Список цен закрытия
        """
        try:
            # Поиск инструмента
            instrument = self.search_instrument(ticker)
            if not instrument:
                logger.error(f"Инструмент {ticker} не найден")
                return []

            # Получение свечей
            candles = self.get_historical_candles(instrument["figi"], days)

            # Извлечение цен закрытия
            prices = [candle.close for candle in candles]

            logger.info(f"Извлечено {len(prices)} цен для {ticker}")
            return prices

        except Exception as e:
            logger.error(f"Ошибка получения истории цен для {ticker}: {e}")
            return []

    async def get_ticker_data_for_analysis(self, ticker: str) -> Optional[Dict]:
        """
        Получение комплексных данных тикера для технического анализа.

        Args:
            ticker: Тикер инструмента

        Returns:
            Словарь с данными для анализа или None при ошибке
        """
        try:
            logger.info(f"Получение данных для анализа {ticker}")

            # Поиск инструмента
            instrument = self.search_instrument(ticker)
            if not instrument:
                logger.error(f"Инструмент {ticker} не найден")
                return None

            # Получение текущей цены
            last_price_data = self.get_last_price(instrument["figi"])
            if not last_price_data:
                logger.error(f"Не удалось получить текущую цену для {ticker}")
                return None

            current_price = self._quotation_to_float(last_price_data.price)

            # Получение исторических данных (больше данных для лучшего анализа)
            price_history = self.get_price_history(ticker, days=200)

            if not price_history:
                logger.error(f"Не удалось получить историю цен для {ticker}")
                return None

            # Получение детальных свечей за последние 30 дней
            candles = self.get_historical_candles(instrument["figi"], days=30)

            # Расчет дополнительных метрик
            volatility = self._calculate_volatility(
                price_history[-30:] if len(price_history) >= 30 else price_history
            )
            price_change_1d = self._calculate_price_change(price_history, 1)
            price_change_7d = self._calculate_price_change(price_history, 7)
            price_change_30d = self._calculate_price_change(price_history, 30)

            result = {
                "ticker": ticker,
                "figi": instrument["figi"],
                "name": instrument["name"],
                "current_price": current_price,
                "price_history": price_history,
                "candles": candles,
                "market_data": {
                    "volatility_30d": volatility,
                    "price_change_1d": price_change_1d,
                    "price_change_7d": price_change_7d,
                    "price_change_30d": price_change_30d,
                    "data_points": len(price_history),
                    "last_update": datetime.now().isoformat(),
                },
                "instrument_info": {
                    "currency": instrument.get("currency", "RUB"),
                    "lot": instrument.get("lot", 1),
                    "min_price_increment": instrument.get("min_price_increment", None),
                },
            }

            logger.info(
                f"Данные для анализа {ticker} успешно получены: {len(price_history)} точек истории"
            )
            return result

        except Exception as e:
            logger.error(f"Ошибка получения данных для анализа {ticker}: {e}")
            return None

    def _quotation_to_float(self, quotation) -> float:
        """Конвертация объекта Quotation в float."""
        try:
            if hasattr(quotation, "units") and hasattr(quotation, "nano"):
                return float(quotation.units) + float(quotation.nano) / 1_000_000_000
            else:
                # Если это уже число
                return float(quotation)
        except Exception as e:
            logger.warning(f"Ошибка конвертации quotation в float: {e}")
            return 0.0

    def _calculate_volatility(self, prices: List[float]) -> float:
        """Расчет волатильности (стандартное отклонение)."""
        try:
            if len(prices) < 2:
                return 0.0

            # Расчет дневных изменений
            returns = []
            for i in range(1, len(prices)):
                if prices[i - 1] != 0:
                    daily_return = (prices[i] - prices[i - 1]) / prices[i - 1]
                    returns.append(daily_return)

            if not returns:
                return 0.0

            # Стандартное отклонение
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = (variance**0.5) * 100  # В процентах

            return round(volatility, 2)

        except Exception as e:
            logger.warning(f"Ошибка расчета волатильности: {e}")
            return 0.0

    def _calculate_price_change(self, prices: List[float], days: int) -> float:
        """Расчет изменения цены за N дней в процентах."""
        try:
            if len(prices) < days + 1:
                return 0.0

            current_price = prices[-1]
            past_price = prices[-days - 1]

            if past_price == 0:
                return 0.0

            change_percent = ((current_price - past_price) / past_price) * 100
            return round(change_percent, 2)

        except Exception as e:
            logger.warning(f"Ошибка расчета изменения цены: {e}")
            return 0.0


# Функция-обертка для совместимости
async def get_ticker_price_history(ticker: str, days: int = 100) -> List[float]:
    """
    Получение истории цен для тикера.

    Args:
        ticker: Тикер инструмента
        days: Количество дней

    Returns:
        Список цен закрытия
    """
    client = TinkoffClient()
    return client.get_price_history(ticker, days)


def test_connection():
    """Тестирование подключения и новых функций"""
    print("🔄 Тестирование улучшенного TinkoffClient...")

    try:
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
            print("✅ Успешно! Найдена акция:")
            print(f"  - Название: {sber.name}")
            print(f"    - FIGI: {sber.figi}")
            print(f"  - Тикер: {sber.ticker}")

            # Тест 3: Получение текущей цены
            print("\n💰 Тест 3: Получение текущей цены SBER")
            price = client.get_last_price(sber.figi)
            if price:
                price_rub = client._quotation_to_float(price.price)
                print(f"✅ Успешно! Цена SBER: {price_rub:.2f} ₽")

                # Тест 4: Получение исторических данных
                print("\n📈 Тест 4: Получение исторических свечей")
                candles = client.get_historical_candles(sber.figi, days=30)
                if candles:
                    print(f"✅ Получено {len(candles)} свечей за 30 дней")
                    print(f"  - Первая свеча: {candles[0].time.date()} - {candles[0].close:.2f} ₽")
                    print(
                        f"  - Последняя свеча: {candles[-1].time.date()} - {candles[-1].close:.2f} ₽"
                    )
                else:
                    print("❌ Не удалось получить исторические данные")

                # Тест 5: Получение истории цен
                print("\n📊 Тест 5: Получение истории цен")
                price_history = client.get_price_history("SBER", days=50)
                if price_history:
                    print(f"✅ Получено {len(price_history)} точек истории цен")
                    print(f"  - Минимальная цена: {min(price_history):.2f} ₽")
                    print(f"  - Максимальная цена: {max(price_history):.2f} ₽")
                    print(f"  - Средняя цена: {sum(price_history)/len(price_history):.2f} ₽")
                else:
                    print("❌ Не удалось получить историю цен")
            else:
                print("❌ Ошибка получения цены")
        else:
            print("❌ Ошибка поиска SBER")

        print("\n🎉 Тестирование завершено!")

    except Exception as e:
        print(f"❌ Критическая ошибка при тестировании: {e}")


async def test_analysis_data():
    """Тестирование получения данных для анализа"""
    print("🧪 Тестирование получения данных для анализа...")

    try:
        client = TinkoffClient()

        # Тестируем получение данных для анализа
        ticker_data = await client.get_ticker_data_for_analysis("SBER")

        if ticker_data:
            print("✅ Данные для анализа получены успешно:")
            print(f"  - Тикер: {ticker_data['ticker']}")
            print(f"  - Текущая цена: {ticker_data['current_price']:.2f} ₽")
            print(f"  - Точек истории: {len(ticker_data['price_history'])}")
            print(f"  - Волатильность 30д: {ticker_data['market_data']['volatility_30d']:.2f}%")
            print(f"  - Изменение за день: {ticker_data['market_data']['price_change_1d']:+.2f}%")
            print(f"  - Изменение за неделю: {ticker_data['market_data']['price_change_7d']:+.2f}%")
        else:
            print("❌ Не удалось получить данные для анализа")

    except Exception as e:
        print(f"❌ Ошибка тестирования анализа: {e}")


if __name__ == "__main__":
    import asyncio

    # Запускаем обычные тесты
    test_connection()

    # Запускаем асинхронные тесты
    print("\n" + "=" * 50)
    asyncio.run(test_analysis_data())