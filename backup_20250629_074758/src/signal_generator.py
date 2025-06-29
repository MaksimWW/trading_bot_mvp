"""
Генератор торговых сигналов для торгового бота.

Объединяет технический анализ и анализ новостей для создания
итоговых торговых рекомендаций с весовыми коэффициентами.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from news_analyzer import get_news_analyzer
from technical_analysis import get_technical_analyzer

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Генератор комбинированных торговых сигналов."""

    def __init__(self):
        """Инициализация генератора сигналов."""
        self.technical_analyzer = get_technical_analyzer()
        self.news_analyzer = get_news_analyzer()

        # Весовые коэффициенты для комбинирования сигналов
        self.weights = {
            "technical": 0.6,  # 60% технический анализ
            "news": 0.4,  # 40% анализ новостей
        }

        logger.info("SignalGenerator инициализирован")

    async def generate_combined_signal(self, ticker: str) -> Dict:
        """
        Генерация комбинированного торгового сигнала.

        Args:
            ticker: Тикер акции

        Returns:
            Комбинированный сигнал с рекомендациями
        """
        try:
            ticker = ticker.upper()
            logger.info(f"Генерация комбинированного сигнала для {ticker}")

            print("DEBUG: Начинаем получение данных...")

            # Параллельное получение технического и новостного анализа
            technical_task = self.technical_analyzer.get_technical_analysis(ticker)
            news_task = self.news_analyzer.analyze_ticker_news(ticker, include_sentiment=True)

            technical_result, news_result = await asyncio.gather(
                technical_task, news_task, return_exceptions=True
            )

            print("DEBUG: Данные получены, проверяем результаты...")

            # Обработка результатов с проверкой на ошибки
            if isinstance(technical_result, Exception):
                print(f"DEBUG: Ошибка технического анализа: {technical_result}")
                logger.error(f"Ошибка технического анализа: {technical_result}")
                technical_result = None

            if isinstance(news_result, Exception):
                print(f"DEBUG: Ошибка анализа новостей: {news_result}")
                logger.error(f"Ошибка анализа новостей: {news_result}")
                news_result = None

            print("DEBUG: Вызываем _combine_signals...")
            # Генерация комбинированного сигнала
            combined_signal = self._combine_signals(ticker, technical_result, news_result)

            print("DEBUG: _combine_signals завершен успешно")
            print(f"DEBUG: Тип результата: {type(combined_signal)}")
            print(
                f"DEBUG: Ключи результата: {list(combined_signal.keys()) if isinstance(combined_signal, dict) else 'НЕ СЛОВАРЬ'}"
            )

            logger.info(
                f"Комбинированный сигнал {ticker}: {combined_signal.get('combined_signal', {}).get('signal', 'UNKNOWN')}"
            )
            return combined_signal

        except Exception as e:
            print(f"DEBUG: Основная ошибка в generate_combined_signal: {e}")
            print(f"DEBUG: Тип ошибки: {type(e)}")
            import traceback

            traceback.print_exc()
            logger.error(f"Ошибка генерации сигнала для {ticker}: {e}")
            return self._create_error_signal(ticker, str(e))

    def _combine_signals(
        self, ticker: str, technical_result: Optional[Dict], news_result: Optional[Dict]
    ) -> Dict:
        """Комбинирование технического и новостного анализа."""
        try:
            # Получение технического и новостного анализа
            tech_data = self._process_technical_analysis(technical_result)
            news_data = self._process_news_analysis(news_result)

            # Взвешенное комбинирование
            combined_score = (
                tech_data["score"] * self.weights["technical"]
                + news_data["score"] * self.weights["news"]
            )

            combined_confidence = (
                tech_data["confidence"] * self.weights["technical"]
                + news_data["confidence"] * self.weights["news"]
            )

            # Преобразование в итоговый сигнал
            signal, emoji = self._get_signal_and_emoji(combined_score)

            # Формирование итогового результата
            return self._create_final_result(
                ticker,
                technical_result,
                news_result,
                signal,
                emoji,
                combined_score,
                combined_confidence,
                tech_data,
                news_data,
            )

        except Exception as e:
            logger.error(f"Ошибка комбинирования сигналов: {e}")
            return self._create_error_signal(ticker, f"Ошибка комбинирования: {str(e)}")

    def _process_technical_analysis(self, technical_result: Optional[Dict]) -> Dict:
        """Обработка результатов технического анализа."""
        signal_values = {
            "STRONG_BUY": 2,
            "BUY": 1,
            "NEUTRAL_BULLISH": 0.5,
            "HOLD": 0,
            "NEUTRAL_BEARISH": -0.5,
            "SELL": -1,
            "STRONG_SELL": -2,
            "UNKNOWN": 0,
        }

        score = 0
        confidence = 0
        signal = "UNKNOWN"

        try:
            print("DEBUG: Обрабатываем технический результат...")
            if technical_result and technical_result.get("success"):
                overall_signal = technical_result.get("overall_signal", {})
                signal = overall_signal.get("signal", "UNKNOWN") if overall_signal else "UNKNOWN"
                score = signal_values.get(signal, 0)
                confidence = overall_signal.get("confidence", 0) if overall_signal else 0
                print(f"DEBUG: Технический сигнал: {signal}, score: {score}")
        except Exception as e:
            print("DEBUG: Ошибка в техническом анализе:", e)
            raise

        return {"signal": signal, "score": score, "confidence": confidence}

    def _process_news_analysis(self, news_result: Optional[Dict]) -> Dict:
        """Обработка результатов анализа новостей."""
        score = 0
        confidence = 0

        try:
            print("DEBUG: Обрабатываем новостной результат...")
            if news_result and news_result.get("success") and news_result.get("sentiment"):
                sentiment = news_result.get("sentiment", {})
                if sentiment:
                    sentiment_score = sentiment.get("sentiment_score", 0)
                    score = sentiment_score * 2  # Преобразуем [-1,1] в [-2,2]
                    confidence = sentiment.get("confidence", 0)
                    print(
                        f"DEBUG: Новостной сигнал: sentiment_score={sentiment_score}, news_score={score}"
                    )
        except Exception as e:
            print("DEBUG: Ошибка в новостном анализе:", e)
            raise

        return {"score": score, "confidence": confidence}

    def _create_final_result(
        self,
        ticker: str,
        technical_result: Optional[Dict],
        news_result: Optional[Dict],
        signal: str,
        emoji: str,
        combined_score: float,
        combined_confidence: float,
        tech_data: Dict,
        news_data: Dict,
    ) -> Dict:
        """Формирование итогового результата."""
        try:
            print("DEBUG: Формируем итоговый результат...")
            print(f"DEBUG: combined_score = {combined_score}")
            print(f"DEBUG: signal = {signal}")

            result = self._create_result(
                ticker,
                technical_result,
                signal,
                emoji,
                combined_score,
                combined_confidence,
                tech_data["signal"],
                tech_data["score"],
                tech_data["confidence"],
                news_result,
                news_data["score"],
                news_data["confidence"],
            )

            print("DEBUG: Результат сформирован успешно")
            return result

        except Exception as e:
            print("DEBUG: Ошибка формирования результата:", e)
            print(f"DEBUG: Переменные: tech_signal={tech_data.get('signal', 'UNDEFINED')}")
            raise

    def _news_score_to_signal(self, news_score: float) -> str:
        """Преобразование новостного score в сигнал."""
        if news_score >= 1.2:
            return "STRONG_BUY"
        elif news_score >= 0.4:
            return "BUY"
        elif news_score <= -1.2:
            return "STRONG_SELL"
        elif news_score <= -0.4:
            return "SELL"
        else:
            return "HOLD"

    def _create_error_signal(self, ticker: str, error_message: str) -> Dict:
        """Создание сигнала с ошибкой."""
        return {
            "ticker": ticker,
            "company_name": f"Акция {ticker}",
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error_message": error_message,
            "combined_signal": {
                "signal": "UNKNOWN",
                "emoji": "⚪",
                "score": 0.0,
                "confidence": 0.0,
                "description": "Анализ недоступен",
            },
        }

    def format_for_telegram(self, signal_result: Dict) -> str:
        """Форматирование результата для Telegram."""
        if not signal_result["success"]:
            return (
                f"❌ *Ошибка генерации сигнала {signal_result['ticker']}*\n\n"
                f"Причина: {signal_result['error_message']}"
            )

        ticker = signal_result["ticker"]
        company_name = signal_result["company_name"]
        combined = signal_result["combined_signal"]
        components = signal_result["components"]

        # Заголовок
        text = f"🎯 *ТОРГОВЫЙ СИГНАЛ {ticker}*\n\n"
        text += f"🏢 *Компания:* {company_name}\n\n"

        # Основной сигнал
        text += f"{combined['emoji']} *РЕКОМЕНДАЦИЯ: {combined['signal']}*\n"
        text += f"📊 *Итоговая оценка:* {combined['score']:+.2f}\n"
        text += f"🎯 *Уверенность:* {combined['confidence']:.0%}\n\n"

        # Компоненты анализа
        text += "📋 *СОСТАВЛЯЮЩИЕ АНАЛИЗА:*\n\n"

        # Технический анализ
        tech = components["technical"]
        if tech["available"]:
            text += f"📈 *Технический анализ ({tech['weight']:.0%}):*\n"
            text += f"📊 Сигнал: {tech['signal']}\n"
            text += f"📈 Вклад: {tech['score']:+.2f}\n\n"
        else:
            text += "📈 *Технический анализ:* ❌ Недоступен\n\n"

        # Анализ новостей
        news = components["news"]
        if news["available"]:
            text += f"📰 *Анализ новостей ({news['weight']:.0%}):*\n"
            text += f"📊 Сигнал: {news['signal']}\n"
            text += f"📈 Вклад: {news['score']:+.2f}\n\n"
        else:
            text += "📰 *Анализ новостей:* ❌ Недоступен\n\n"

        # Время и действия
        text += f"🕐 *Время анализа:* {datetime.now().strftime('%H:%M:%S')}\n\n"

        text += "*💡 Детальная информация:*\n"
        text += f"• `/analysis {ticker}` - технический анализ\n"
        text += f"• `/news {ticker}` - анализ новостей\n"
        text += f"• `/price {ticker}` - текущая цена\n\n"

        # Дисклеймер
        text += (
            "⚠️ *Важно:* Комбинированный сигнал учитывает множество факторов, "
            "но не гарантирует результат. Принимайте решения обдуманно."
        )

        return text

    def _get_signal_and_emoji(self, combined_score: float) -> tuple[str, str]:
        """Преобразование combined_score в сигнал и emoji."""
        if combined_score >= 1.2:
            signal = "STRONG_BUY"
            emoji = "💚"
        elif combined_score >= 0.4:
            signal = "BUY"
            emoji = "🟢"
        elif combined_score <= -1.2:
            signal = "STRONG_SELL"
            emoji = "🔴"
        elif combined_score <= -0.4:
            signal = "SELL"
            emoji = "🟠"
        else:
            signal = "HOLD"
            emoji = "🟡"
        return signal, emoji

    def _create_result(
        self,
        ticker: str,
        technical_result: Optional[Dict],
        signal: str,
        emoji: str,
        combined_score: float,
        combined_confidence: float,
        tech_signal: str,
        technical_score: float,
        technical_confidence: float,
        news_result: Optional[Dict],
        news_score: float,
        news_confidence: float,
    ) -> Dict:
        """Формирование результата."""

        return {
            "ticker": ticker,
            "company_name": (
                technical_result.get("company_name", f"Акция {ticker}")
                if technical_result
                else f"Акция {ticker}"
            ),
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "error_message": None,
            "combined_signal": {
                "signal": signal,
                "emoji": emoji,
                "score": round(combined_score, 2),
                "confidence": round(combined_confidence, 2),
                "description": f"Комбинированный сигнал ({signal})",
            },
            "components": {
                "technical": {
                    "available": technical_result is not None
                    and technical_result.get("success", False),
                    "signal": tech_signal,  # НЕ ИСПОЛЬЗУЙ technical_result.get('overall_signal', {}).get('signal')
                    "score": technical_score,
                    "confidence": technical_confidence,
                    "weight": self.weights["technical"],
                },
                "news": {
                    "available": news_result is not None
                    and news_result.get("success", False)
                    and news_result.get("sentiment"),
                    "signal": self._news_score_to_signal(news_score),
                    "score": news_score,
                    "confidence": news_confidence,
                    "weight": self.weights["news"],
                },
            },
            "details": {
                "technical_analysis": technical_result,
                "news_analysis": news_result,
            },
        }


# Глобальный экземпляр генератора
_global_signal_generator = None


def get_signal_generator() -> SignalGenerator:
    """Получение глобального экземпляра генератора сигналов."""
    global _global_signal_generator
    if _global_signal_generator is None:
        _global_signal_generator = SignalGenerator()
    return _global_signal_generator


async def generate_trading_signal(ticker: str) -> Dict:
    """Быстрая функция для генерации торгового сигнала."""
    generator = get_signal_generator()
    return await generator.generate_combined_signal(ticker)


async def get_trading_signal_for_telegram(ticker: str) -> str:
    """Получение отформатированного торгового сигнала для Telegram."""
    generator = get_signal_generator()
    result = await generator.generate_combined_signal(ticker)
    return generator.format_for_telegram(result)


def main():
    """Функция для тестирования модуля."""
    import asyncio
    import json

    async def test_signal_generation():
        print("🧪 Тестирование SignalGenerator...")

        try:
            generator = SignalGenerator()

            print("🎯 Тестируем генерацию сигнала для SBER...")
            result = await generator.generate_combined_signal("SBER")

            print("✅ Результат:")
            print(json.dumps(result, ensure_ascii=False, indent=2))

            print("\n📱 Форматированный результат для Telegram:")
            telegram_text = generator.format_for_telegram(result)
            print(telegram_text)

        except Exception as e:
            print("❌ Ошибка тестирования:", e)
            import traceback

            traceback.print_exc()

    print("Тестирование Signal Generator...")
    asyncio.run(test_signal_generation())


if __name__ == "__main__":
    main()
