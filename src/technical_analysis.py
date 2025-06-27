"""
Настоящий модуль технического анализа с реальными индикаторами.

Заменяет заглушки на настоящие расчеты RSI, MACD, Moving Averages
на основе реальных исторических данных от Tinkoff API.
"""

import logging
import math
from datetime import datetime
from typing import Dict, List

from tinkoff_client import TinkoffClient

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Анализатор технических индикаторов на основе реальных данных."""

    def __init__(self):
        """Инициализация анализатора."""
        self.tinkoff_client = TinkoffClient()
        logger.info("TechnicalAnalyzer инициализирован с реальными данными")

    def calculate_sma(self, prices: List[float], period: int) -> List[float]:
        """
        Расчет простой скользящей средней (SMA).

        Args:
            prices: Список цен
            period: Период для расчета

        Returns:
            Список значений SMA
        """
        if len(prices) < period:
            return []

        sma_values = []

        for i in range(period - 1, len(prices)):
            # Берем последние period значений
            window = prices[i - period + 1 : i + 1]
            sma = sum(window) / period
            sma_values.append(sma)

        return sma_values

    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """
        Расчет экспоненциальной скользящей средней (EMA).

        Args:
            prices: Список цен
            period: Период для расчета

        Returns:
            Список значений EMA
        """
        if len(prices) < period:
            return []

        # Коэффициент сглаживания
        multiplier = 2 / (period + 1)

        ema_values = []

        # Первое значение EMA = SMA
        sma_first = sum(prices[:period]) / period
        ema_values.append(sma_first)

        # Остальные значения по формуле EMA
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)

        return ema_values

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """
        Расчет RSI (Relative Strength Index).

        Args:
            prices: Список цен закрытия
            period: Период для расчета (по умолчанию 14)

        Returns:
            Значение RSI от 0 до 100
        """
        if len(prices) < period + 1:
            logger.warning(f"Недостаточно данных для RSI: {len(prices)} < {period + 1}")
            return 50.0  # Нейтральное значение

        try:
            # Вычисляем изменения цен
            deltas = []
            for i in range(1, len(prices)):
                delta = prices[i] - prices[i - 1]
                deltas.append(delta)

            # Разделяем на приросты и убытки
            gains = [delta if delta > 0 else 0 for delta in deltas]
            losses = [-delta if delta < 0 else 0 for delta in deltas]

            # Берем последние period значений
            recent_gains = gains[-period:]
            recent_losses = losses[-period:]

            # Средний прирост и убыток
            avg_gain = sum(recent_gains) / period
            avg_loss = sum(recent_losses) / period

            # Избегаем деления на ноль
            if avg_loss == 0:
                return 100.0 if avg_gain > 0 else 50.0

            # Расчет RS и RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            # Ограничиваем значения в диапазоне 0-100
            rsi = max(0, min(100, rsi))

            logger.debug(
                f"RSI рассчитан: {rsi:.2f} (avg_gain: {avg_gain:.4f}, avg_loss: {avg_loss:.4f})"
            )
            return rsi

        except Exception as e:
            logger.error(f"Ошибка расчета RSI: {e}")
            return 50.0

    def calculate_macd(
        self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Dict:
        """
        Расчет MACD (Moving Average Convergence Divergence).

        Args:
            prices: Список цен
            fast: Период быстрой EMA
            slow: Период медленной EMA
            signal: Период сигнальной линии

        Returns:
            Словарь с компонентами MACD
        """
        if len(prices) < slow + signal:
            logger.warning(f"Недостаточно данных для MACD: {len(prices)} < {slow + signal}")
            return {"macd_line": 0.0, "signal_line": 0.0, "histogram": 0.0, "trend": "NEUTRAL"}

        try:
            # Рассчитываем EMA
            ema_fast = self.calculate_ema(prices, fast)
            ema_slow = self.calculate_ema(prices, slow)

            if not ema_fast or not ema_slow:
                return {"macd_line": 0.0, "signal_line": 0.0, "histogram": 0.0, "trend": "NEUTRAL"}

            # Выравниваем массивы (EMA slow начинается позже)
            offset = slow - fast
            ema_fast_aligned = ema_fast[offset:]

            # MACD линия = EMA(fast) - EMA(slow)
            macd_values = []
            for i in range(len(ema_slow)):
                macd = ema_fast_aligned[i] - ema_slow[i]
                macd_values.append(macd)

            # Сигнальная линия = EMA от MACD
            signal_values = self.calculate_ema(macd_values, signal)

            if not signal_values:
                return {
                    "macd_line": macd_values[-1] if macd_values else 0.0,
                    "signal_line": 0.0,
                    "histogram": 0.0,
                    "trend": "NEUTRAL",
                }

            # Последние значения
            macd_line = macd_values[-1]
            signal_line = signal_values[-1]
            histogram = macd_line - signal_line

            # Определяем тренд
            trend = self._determine_macd_trend(histogram, macd_values, signal_values)

            result = {
                "macd_line": macd_line,
                "signal_line": signal_line,
                "histogram": histogram,
                "trend": trend,
            }

            logger.debug(f"MACD рассчитан: {result}")
            return result

        except Exception as e:
            logger.error(f"Ошибка расчета MACD: {e}")
            return {"macd_line": 0.0, "signal_line": 0.0, "histogram": 0.0, "trend": "NEUTRAL"}

    def _determine_macd_trend(
        self, histogram: float, macd_values: List[float], signal_values: List[float]
    ) -> str:
        """Определение тренда MACD."""
        if len(signal_values) >= 2:
            prev_histogram = macd_values[-2] - signal_values[-2]
            if histogram > 0 and prev_histogram <= 0:
                return "BULLISH_CROSSOVER"
            elif histogram < 0 and prev_histogram >= 0:
                return "BEARISH_CROSSOVER"
            elif histogram > 0:
                return "BULLISH"
            else:
                return "BEARISH"
        else:
            return "BULLISH" if histogram > 0 else "BEARISH"

    def calculate_bollinger_bands(
        self, prices: List[float], period: int = 20, std_dev: float = 2
    ) -> Dict:
        """
        Расчет полос Боллинджера.

        Args:
            prices: Список цен
            period: Период для SMA
            std_dev: Количество стандартных отклонений

        Returns:
            Словарь с значениями полос
        """
        if len(prices) < period:
            return {
                "upper_band": 0.0,
                "middle_band": 0.0,
                "lower_band": 0.0,
                "bandwidth": 0.0,
                "position": "MIDDLE",
            }

        try:
            # Простая скользящая средняя (средняя полоса)
            sma_values = self.calculate_sma(prices, period)

            if not sma_values:
                return {
                    "upper_band": 0.0,
                    "middle_band": 0.0,
                    "lower_band": 0.0,
                    "bandwidth": 0.0,
                    "position": "MIDDLE",
                }

            middle_band = sma_values[-1]

            # Стандартное отклонение для последнего периода
            recent_prices = prices[-period:]
            mean = sum(recent_prices) / len(recent_prices)

            variance = sum((price - mean) ** 2 for price in recent_prices) / len(recent_prices)
            std_deviation = math.sqrt(variance)

            # Верхняя и нижняя полосы
            upper_band = middle_band + (std_dev * std_deviation)
            lower_band = middle_band - (std_dev * std_deviation)

            # Ширина полосы
            bandwidth = (upper_band - lower_band) / middle_band * 100

            # Позиция текущей цены относительно полос
            current_price = prices[-1]
            if current_price > upper_band:
                position = "ABOVE_UPPER"
            elif current_price < lower_band:
                position = "BELOW_LOWER"
            elif current_price > middle_band:
                position = "UPPER_HALF"
            else:
                position = "LOWER_HALF"

            result = {
                "upper_band": upper_band,
                "middle_band": middle_band,
                "lower_band": lower_band,
                "bandwidth": bandwidth,
                "position": position,
            }

            logger.debug(f"Bollinger Bands рассчитаны: {result}")
            return result

        except Exception as e:
            logger.error(f"Ошибка расчета Bollinger Bands: {e}")
            return {
                "upper_band": 0.0,
                "middle_band": 0.0,
                "lower_band": 0.0,
                "bandwidth": 0.0,
                "position": "MIDDLE",
            }

    async def analyze_ticker(self, ticker: str) -> Dict:
        """
        Полный технический анализ тикера на основе реальных данных.

        Args:
            ticker: Тикер акции

        Returns:
            Полный анализ с реальными индикаторами
        """
        try:
            logger.info(f"Начинаем технический анализ {ticker} с реальными данными")

            # Получаем реальные данные от Tinkoff API
            ticker_data = await self.tinkoff_client.get_ticker_data_for_analysis(ticker)

            if not ticker_data:
                logger.error(f"Не удалось получить данные для {ticker}")
                return self._create_error_result(ticker, "Данные недоступны")

            prices = ticker_data["price_history"]
            current_price = ticker_data["current_price"]

            if len(prices) < 50:
                logger.warning(f"Недостаточно данных для анализа {ticker}: {len(prices)} точек")
                return self._create_limited_result(ticker, current_price, len(prices))

            # Расчет реальных индикаторов
            rsi = self.calculate_rsi(prices, 14)
            macd = self.calculate_macd(prices, 12, 26, 9)
            bollinger = self.calculate_bollinger_bands(prices, 20, 2)

            # Moving averages
            sma_20 = self.calculate_sma(prices, 20)
            sma_50 = self.calculate_sma(prices, 50)
            ema_12 = self.calculate_ema(prices, 12)
            ema_26 = self.calculate_ema(prices, 26)

            # Текущие значения MA
            current_sma_20 = sma_20[-1] if sma_20 else current_price
            current_sma_50 = sma_50[-1] if sma_50 else current_price
            current_ema_12 = ema_12[-1] if ema_12 else current_price
            current_ema_26 = ema_26[-1] if ema_26 else current_price

            # Определение трендов
            price_vs_sma20 = "ABOVE" if current_price > current_sma_20 else "BELOW"
            price_vs_sma50 = "ABOVE" if current_price > current_sma_50 else "BELOW"
            sma_trend = "BULLISH" if current_sma_20 > current_sma_50 else "BEARISH"

            # Общий сигнал на основе реальных данных
            signal_score = self._calculate_signal_score(
                rsi, macd, price_vs_sma20, price_vs_sma50, bollinger
            )

            signal_label = self._get_signal_label(signal_score)

            # Формируем результат
            result = {
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "data_quality": "REAL_DATA",
                "data_points": len(prices),
                # Текущие данные
                "current_price": current_price,
                "price_range_30d": {
                    "min": min(prices[-30:]) if len(prices) >= 30 else min(prices),
                    "max": max(prices[-30:]) if len(prices) >= 30 else max(prices),
                },
                # RSI
                "rsi": {
                    "value": rsi,
                    "level": self._get_rsi_level(rsi),
                    "signal": self._get_rsi_signal(rsi),
                },
                # MACD
                "macd": macd,
                # Moving Averages
                "moving_averages": {
                    "sma_20": current_sma_20,
                    "sma_50": current_sma_50,
                    "ema_12": current_ema_12,
                    "ema_26": current_ema_26,
                    "price_vs_sma20": price_vs_sma20,
                    "price_vs_sma50": price_vs_sma50,
                    "trend": sma_trend,
                },
                # Bollinger Bands
                "bollinger_bands": bollinger,
                # Итоговый сигнал
                "signal": {
                    "score": signal_score,
                    "label": signal_label,
                    "confidence": self._calculate_confidence(rsi, macd, len(prices)),
                },
                # Для совместимости с существующим кодом
                "combined_signal": signal_score,
                "rsi_signal": self._get_rsi_signal(rsi),
                "macd_signal": macd.get("trend", "NEUTRAL"),
                "trend_direction": "UP" if signal_score > 0 else "DOWN",
                "confidence": self._calculate_confidence(rsi, macd, len(prices)),
                "analysis_timestamp": datetime.now().isoformat(),
                # Метаданные
                "analysis_type": "REAL_TECHNICAL_ANALYSIS",
                "calculation_method": "TINKOFF_HISTORICAL_DATA",
            }

            logger.info(
                f"Технический анализ {ticker} завершен: {signal_label} (score: {signal_score:.2f})"
            )
            return result

        except Exception as e:
            logger.error(f"Ошибка анализа {ticker}: {e}")
            return self._create_error_result(ticker, str(e))

    def _calculate_signal_score(
        self, rsi: float, macd: Dict, price_vs_sma20: str, price_vs_sma50: str, bollinger: Dict
    ) -> float:
        """Расчет общего сигнала на основе всех индикаторов."""
        score = 0.0

        score += self._calculate_rsi_component(rsi)
        score += self._calculate_macd_component(macd)
        score += self._calculate_ma_component(price_vs_sma20, price_vs_sma50)
        score += self._calculate_bollinger_component(bollinger)

        # Нормализуем в диапазон -1 до 1
        score = max(-1.0, min(1.0, score))
        return score

    def _calculate_rsi_component(self, rsi: float) -> float:
        """Расчет RSI компонента сигнала (30% веса)."""
        if rsi < 30:
            return 0.3  # Перепроданность - покупка
        elif rsi > 70:
            return -0.3  # Перекупленность - продажа
        else:
            # Нейтральная зона с небольшим bias
            return (50 - rsi) / 100 * 0.15

    def _calculate_macd_component(self, macd: Dict) -> float:
        """Расчет MACD компонента сигнала (25% веса)."""
        macd_signal = macd.get("trend", "NEUTRAL")
        macd_scores = {
            "BULLISH_CROSSOVER": 0.25,
            "BEARISH_CROSSOVER": -0.25,
            "BULLISH": 0.15,
            "BEARISH": -0.15,
        }
        return macd_scores.get(macd_signal, 0.0)

    def _calculate_ma_component(self, price_vs_sma20: str, price_vs_sma50: str) -> float:
        """Расчет Moving Averages компонента сигнала (25% веса)."""
        if price_vs_sma20 == "ABOVE" and price_vs_sma50 == "ABOVE":
            return 0.25  # Цена выше обеих MA
        elif price_vs_sma20 == "BELOW" and price_vs_sma50 == "BELOW":
            return -0.25  # Цена ниже обеих MA
        elif price_vs_sma20 == "ABOVE":
            return 0.1  # Цена выше короткой MA
        return 0.0

    def _calculate_bollinger_component(self, bollinger: Dict) -> float:
        """Расчет Bollinger Bands компонента сигнала (20% веса)."""
        bb_position = bollinger.get("position", "MIDDLE")
        bb_scores = {
            "BELOW_LOWER": 0.2,  # Перепроданность
            "ABOVE_UPPER": -0.2,  # Перекупленность
            "UPPER_HALF": 0.05,  # Слабый бычий сигнал
            "LOWER_HALF": -0.05,  # Слабый медвежий сигнал
        }
        return bb_scores.get(bb_position, 0.0)

    def _get_signal_label(self, score: float) -> str:
        """Конвертация численного сигнала в текстовую метку."""
        if score >= 0.6:
            return "STRONG_BUY"
        elif score >= 0.2:
            return "BUY"
        elif score <= -0.6:
            return "STRONG_SELL"
        elif score <= -0.2:
            return "SELL"
        else:
            return "HOLD"

    def _get_rsi_level(self, rsi: float) -> str:
        """Определение уровня RSI."""
        if rsi >= 70:
            return "OVERBOUGHT"
        elif rsi <= 30:
            return "OVERSOLD"
        elif rsi >= 60:
            return "STRONG"
        elif rsi <= 40:
            return "WEAK"
        else:
            return "NEUTRAL"

    def _get_rsi_signal(self, rsi: float) -> str:
        """Торговый сигнал на основе RSI."""
        if rsi <= 30:
            return "BUY"
        elif rsi >= 70:
            return "SELL"
        else:
            return "HOLD"

    def _calculate_confidence(self, rsi: float, macd: Dict, data_points: int) -> float:
        """Расчет уверенности в сигнале."""
        confidence = 0.5  # Базовая уверенность

        # Больше данных = больше уверенности
        if data_points >= 100:
            confidence += 0.2
        elif data_points >= 50:
            confidence += 0.1

        # Экстремальные значения RSI увеличивают уверенность
        if rsi <= 25 or rsi >= 75:
            confidence += 0.2
        elif rsi <= 35 or rsi >= 65:
            confidence += 0.1

        # MACD кроссоверы увеличивают уверенность
        macd_trend = macd.get("trend", "NEUTRAL")
        if "CROSSOVER" in macd_trend:
            confidence += 0.2

        return min(1.0, confidence)

    def _create_error_result(self, ticker: str, error_message: str) -> Dict:
        """Создание результата с ошибкой."""
        return {
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": error_message,
            "data_quality": "ERROR",
            "analysis_type": "FAILED",
            # Для совместимости
            "combined_signal": 0.0,
            "rsi_signal": "HOLD",
            "macd_signal": "NEUTRAL",
            "trend_direction": "NEUTRAL",
            "confidence": 0.0,
            "analysis_timestamp": datetime.now().isoformat(),
        }

    def _create_limited_result(self, ticker: str, current_price: float, data_points: int) -> Dict:
        """Создание результата с ограниченными данными."""
        return {
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "data_quality": "LIMITED",
            "data_points": data_points,
            "current_price": current_price,
            "warning": "Недостаточно данных для полного анализа",
            "signal": {"score": 0.0, "label": "INSUFFICIENT_DATA", "confidence": 0.1},
            # Для совместимости
            "combined_signal": 0.0,
            "rsi_signal": "HOLD",
            "macd_signal": "NEUTRAL",
            "trend_direction": "NEUTRAL",
            "confidence": 0.1,
            "analysis_timestamp": datetime.now().isoformat(),
        }


# Глобальный экземпляр анализатора
_analyzer = None


def get_technical_analyzer() -> TechnicalAnalyzer:
    """Получение глобального экземпляра технического анализатора."""
    global _analyzer
    if _analyzer is None:
        _analyzer = TechnicalAnalyzer()
    return _analyzer


# Функции-обертки для совместимости с существующим кодом
async def analyze_ticker(ticker: str) -> Dict:
    """Анализ тикера с реальными данными."""
    analyzer = get_technical_analyzer()
    return await analyzer.analyze_ticker(ticker)


async def analyze_ticker_technical(ticker: str) -> Dict:
    """Быстрая функция для технического анализа тикера."""
    return await analyze_ticker(ticker)


async def get_ticker_analysis_for_telegram(ticker: str) -> str:
    """Получение отформатированного технического анализа для Telegram."""
    result = await analyze_ticker(ticker)

    if not result.get("success"):
        return f"❌ *Ошибка анализа {ticker}*\n\n{result.get('error', 'Неизвестная ошибка')}"

    # Форматированный вывод
    current_price = result.get("current_price", 0)
    rsi_data = result.get("rsi", {})
    signal_data = result.get("signal", {})
    macd_data = result.get("macd", {})

    text = f"📊 *ТЕХНИЧЕСКИЙ АНАЛИЗ {ticker}*\n\n"
    text += f"💰 *Текущая цена:* {current_price:.2f} ₽\n"
    text += f"📅 *Данных:* {result.get('data_points', 0)} точек\n\n"

    # Общий сигнал
    signal_label = signal_data.get("label", "UNKNOWN")
    signal_score = signal_data.get("score", 0)
    confidence = signal_data.get("confidence", 0)

    if signal_label == "STRONG_BUY":
        emoji = "🟢"
    elif signal_label == "BUY":
        emoji = "🟢"
    elif signal_label == "STRONG_SELL":
        emoji = "🔴"
    elif signal_label == "SELL":
        emoji = "🔴"
    else:
        emoji = "🟡"

    text += f"{emoji} *СИГНАЛ: {signal_label}*\n"
    text += f"🎯 *Оценка:* {signal_score:+.2f}\n"
    text += f"🎯 *Уверенность:* {confidence:.0%}\n\n"

    # RSI
    rsi_value = rsi_data.get("value", 50)
    rsi_level = rsi_data.get("level", "NEUTRAL")
    text += f"📈 *RSI:* {rsi_value:.1f} ({rsi_level})\n"

    # MACD
    macd_trend = macd_data.get("trend", "NEUTRAL")
    text += f"📊 *MACD:* {macd_trend}\n"

    # Moving Averages
    ma_data = result.get("moving_averages", {})
    ma_trend = ma_data.get("trend", "NEUTRAL")
    text += f"📈 *MA Тренд:* {ma_trend}\n\n"

    # Bollinger Bands
    bb_data = result.get("bollinger_bands", {})
    bb_position = bb_data.get("position", "MIDDLE")
    text += f"📊 *Bollinger:* {bb_position}\n\n"

    text += f"⏰ *Время анализа:* {datetime.now().strftime('%H:%M:%S')}"

    return text


def main():
    """Функция для тестирования модуля."""
    import asyncio

    async def test():
        print("🧪 Тестирование реального TechnicalAnalyzer...")

        analyzer = TechnicalAnalyzer()
        result = await analyzer.analyze_ticker("SBER")

        print("Результат анализа:")
        for key, value in result.items():
            if key not in ["price_history"]:  # Не выводим весь массив цен
                print(f"  {key}: {value}")

        print("✅ Тестирование завершено!")

    asyncio.run(test())


if __name__ == "__main__":
    main()
