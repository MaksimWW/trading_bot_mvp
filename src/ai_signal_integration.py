
"""
AI Signal Integration для торгового бота.

Этот модуль объединяет технические индикаторы и анализ новостей
для создания комплексных торговых сигналов с использованием AI.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from technical_analysis import TechnicalAnalyzer
from news_analyzer import NewsAnalyzer
from config import get_ticker_info


logger = logging.getLogger(__name__)


class SignalStrength(Enum):
    """Уровни силы торгового сигнала."""
    STRONG_SELL = "STRONG_SELL"
    SELL = "SELL"
    WEAK_SELL = "WEAK_SELL"
    HOLD = "HOLD"
    WEAK_BUY = "WEAK_BUY"
    BUY = "BUY"
    STRONG_BUY = "STRONG_BUY"


class RiskLevel(Enum):
    """Уровни риска для позиций."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


@dataclass
class AISignal:
    """Структура AI торгового сигнала."""
    ticker: str
    signal_strength: SignalStrength
    confidence: float  # 0.0 - 1.0
    risk_level: RiskLevel
    
    # Компоненты сигнала
    technical_score: float  # -1.0 to +1.0
    news_sentiment_score: float  # -1.0 to +1.0
    combined_score: float  # -1.0 to +1.0
    
    # Торговые рекомендации
    recommended_position_size: float  # % от портфеля
    entry_strategy: str
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    expected_return: Optional[Tuple[float, float]]  # (min, max) %
    
    # Метаданные
    analysis_timestamp: datetime
    technical_indicators: Dict
    news_summary: str
    ai_reasoning: str


class AISignalIntegration:
    """Главный класс для интеграции AI сигналов."""
    
    def __init__(self):
        """Инициализация AI Signal Integration."""
        self.technical_analyzer = TechnicalAnalyzer()
        self.news_analyzer = NewsAnalyzer()
        
        # Весовые коэффициенты для комбинирования сигналов
        self.technical_weight = 0.6
        self.news_weight = 0.4
        
        # Пороги для определения силы сигналов
        self.signal_thresholds = {
            SignalStrength.STRONG_BUY: 0.7,
            SignalStrength.BUY: 0.3,
            SignalStrength.WEAK_BUY: 0.1,
            SignalStrength.HOLD: -0.1,
            SignalStrength.WEAK_SELL: -0.3,
            SignalStrength.SELL: -0.5,
            SignalStrength.STRONG_SELL: -0.7,
        }
        
        logger.info("AI Signal Integration инициализирован")
    
    async def analyze_ticker(self, ticker: str) -> AISignal:
        """
        Комплексный AI анализ тикера.
        
        Args:
            ticker: Тикер акции для анализа
            
        Returns:
            AISignal с комплексным анализом
        """
        ticker = ticker.upper()
        logger.info(f"Начинаем AI анализ для {ticker}")
        
        try:
            # Параллельно получаем технический анализ и новости
            technical_task = self._get_technical_analysis(ticker)
            news_task = self._get_news_analysis(ticker)
            
            technical_result, news_result = await asyncio.gather(
                technical_task, news_task, return_exceptions=True
            )
            
            # Обрабатываем результаты с учетом возможных ошибок
            technical_score = 0.0
            technical_indicators = {}
            if not isinstance(technical_result, Exception):
                technical_score = technical_result.get("combined_signal", 0.0)
                technical_indicators = technical_result.get("indicators", {})
            else:
                logger.warning(f"Ошибка технического анализа для {ticker}: {technical_result}")
            
            news_sentiment_score = 0.0
            news_summary = "Анализ новостей недоступен"
            if not isinstance(news_result, Exception):
                sentiment = news_result.get("sentiment")
                if sentiment:
                    news_sentiment_score = sentiment.get("sentiment_score", 0.0)
                    news_summary = sentiment.get("summary", "Нет данных")
            else:
                logger.warning(f"Ошибка анализа новостей для {ticker}: {news_result}")
            
            # Создаем комбинированный сигнал
            ai_signal = await self._create_combined_signal(
                ticker=ticker,
                technical_score=technical_score,
                news_sentiment_score=news_sentiment_score,
                technical_indicators=technical_indicators,
                news_summary=news_summary
            )
            
            logger.info(f"AI анализ {ticker} завершен: {ai_signal.signal_strength.value} "
                       f"(confidence: {ai_signal.confidence:.2f})")
            
            return ai_signal
            
        except Exception as e:
            logger.error(f"Ошибка AI анализа для {ticker}: {e}")
            return self._create_error_signal(ticker, str(e))
    
    async def _get_technical_analysis(self, ticker: str) -> Dict:
        """Получение результатов технического анализа."""
        try:
            # Используем существующий метод analyze_ticker
            analysis_result = await self.technical_analyzer.analyze_ticker(ticker)
            
            # Преобразуем в нужный формат
            return {
                "combined_signal": analysis_result.get("combined_signal", 0.0),
                "indicators": {
                    "current_price": analysis_result.get("current_price"),
                    "rsi": analysis_result.get("rsi", {}),
                    "macd": analysis_result.get("macd", {}),
                    "bollinger_bands": analysis_result.get("bollinger_bands", {}),
                    "moving_averages": analysis_result.get("moving_averages", {})
                }
            }
        except Exception as e:
            logger.error(f"Ошибка технического анализа {ticker}: {e}")
            raise
    
    async def _get_news_analysis(self, ticker: str) -> Dict:
        """Получение результатов анализа новостей."""
        try:
            return await self.news_analyzer.analyze_ticker_news(ticker, include_sentiment=True)
        except Exception as e:
            logger.error(f"Ошибка анализа новостей {ticker}: {e}")
            raise
    
    async def _create_combined_signal(
        self,
        ticker: str,
        technical_score: float,
        news_sentiment_score: float,
        technical_indicators: Dict,
        news_summary: str
    ) -> AISignal:
        """Создание комбинированного AI сигнала."""
        
        # Комбинируем сигналы с весовыми коэффициентами
        combined_score = (
            technical_score * self.technical_weight + 
            news_sentiment_score * self.news_weight
        )
        
        # Определяем силу сигнала
        signal_strength = self._determine_signal_strength(combined_score)
        
        # Рассчитываем уверенность на основе согласованности сигналов
        confidence = self._calculate_confidence(technical_score, news_sentiment_score)
        
        # Определяем уровень риска
        risk_level = self._assess_risk_level(combined_score, confidence, technical_indicators)
        
        # Рассчитываем рекомендации по позиции
        position_recommendations = self._calculate_position_recommendations(
            signal_strength, risk_level, confidence, technical_indicators
        )
        
        # Генерируем AI объяснение
        ai_reasoning = self._generate_ai_reasoning(
            ticker, technical_score, news_sentiment_score, combined_score, 
            signal_strength, confidence
        )
        
        return AISignal(
            ticker=ticker,
            signal_strength=signal_strength,
            confidence=confidence,
            risk_level=risk_level,
            technical_score=technical_score,
            news_sentiment_score=news_sentiment_score,
            combined_score=combined_score,
            recommended_position_size=position_recommendations["position_size"],
            entry_strategy=position_recommendations["entry_strategy"],
            stop_loss_price=position_recommendations.get("stop_loss"),
            take_profit_price=position_recommendations.get("take_profit"),
            expected_return=position_recommendations.get("expected_return"),
            analysis_timestamp=datetime.now(),
            technical_indicators=technical_indicators,
            news_summary=news_summary,
            ai_reasoning=ai_reasoning
        )
    
    def _determine_signal_strength(self, combined_score: float) -> SignalStrength:
        """Определение силы сигнала на основе комбинированного скора."""
        if combined_score >= 0.7:
            return SignalStrength.STRONG_BUY
        elif combined_score >= 0.3:
            return SignalStrength.BUY
        elif combined_score >= 0.1:
            return SignalStrength.WEAK_BUY
        elif combined_score >= -0.1:
            return SignalStrength.HOLD
        elif combined_score >= -0.3:
            return SignalStrength.WEAK_SELL
        elif combined_score >= -0.5:
            return SignalStrength.SELL
        else:
            return SignalStrength.STRONG_SELL
    
    def _calculate_confidence(self, technical_score: float, news_score: float) -> float:
        """
        Расчет уверенности на основе согласованности сигналов.
        
        Высокая уверенность когда технический анализ и новости согласуются.
        """
        # Базовая уверенность на основе силы сигналов
        base_confidence = (abs(technical_score) + abs(news_score)) / 2
        
        # Бонус за согласованность сигналов
        agreement_bonus = 0.0
        if (technical_score > 0 and news_score > 0) or (technical_score < 0 and news_score < 0):
            # Сигналы направлены в одну сторону
            agreement_bonus = 0.2
        elif abs(technical_score - news_score) < 0.3:
            # Сигналы близки по значению
            agreement_bonus = 0.1
        
        confidence = min(1.0, base_confidence + agreement_bonus)
        return confidence
    
    def _assess_risk_level(
        self, combined_score: float, confidence: float, technical_indicators: Dict
    ) -> RiskLevel:
        """Оценка уровня риска позиции."""
        
        # Базовый риск на основе силы сигнала
        signal_risk = abs(combined_score)
        
        # Риск на основе уверенности (низкая уверенность = высокий риск)
        confidence_risk = 1.0 - confidence
        
        # Риск на основе волатильности (если доступно)
        volatility_risk = 0.0
        if "bollinger_bands" in technical_indicators:
            bb = technical_indicators["bollinger_bands"]
            if bb.get("bandwidth"):
                # Высокая ширина полос Боллинджера = высокая волатильность
                volatility_risk = min(1.0, bb["bandwidth"] / 0.2)
        
        # Комбинированный риск
        total_risk = (signal_risk * 0.4 + confidence_risk * 0.4 + volatility_risk * 0.2)
        
        if total_risk >= 0.8:
            return RiskLevel.EXTREME
        elif total_risk >= 0.6:
            return RiskLevel.HIGH
        elif total_risk >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_position_recommendations(
        self, signal_strength: SignalStrength, risk_level: RiskLevel, 
        confidence: float, technical_indicators: Dict
    ) -> Dict:
        """Расчет рекомендаций по размеру и управлению позицией."""
        
        recommendations = {}
        
        # Базовый размер позиции на основе силы сигнала
        signal_multipliers = {
            SignalStrength.STRONG_BUY: 0.05,  # 5% портфеля
            SignalStrength.BUY: 0.03,         # 3% портфеля
            SignalStrength.WEAK_BUY: 0.01,    # 1% портфеля
            SignalStrength.HOLD: 0.0,         # 0% (не торгуем)
            SignalStrength.WEAK_SELL: 0.0,    # Продажа существующих позиций
            SignalStrength.SELL: 0.0,
            SignalStrength.STRONG_SELL: 0.0,
        }
        
        base_position_size = signal_multipliers.get(signal_strength, 0.0)
        
        # Корректировка на основе риска и уверенности
        risk_multipliers = {
            RiskLevel.LOW: 1.2,
            RiskLevel.MEDIUM: 1.0,
            RiskLevel.HIGH: 0.7,
            RiskLevel.EXTREME: 0.3,
        }
        
        risk_adjustment = risk_multipliers.get(risk_level, 1.0)
        confidence_adjustment = 0.5 + (confidence * 0.5)  # 0.5 - 1.0
        
        final_position_size = base_position_size * risk_adjustment * confidence_adjustment
        recommendations["position_size"] = min(0.05, final_position_size)  # Максимум 5%
        
        # Стратегия входа
        if signal_strength in [SignalStrength.STRONG_BUY, SignalStrength.BUY]:
            if risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]:
                recommendations["entry_strategy"] = "Покупать сразу полную позицию"
            else:
                recommendations["entry_strategy"] = "Покупать порциями в течение 2-3 дней"
        elif signal_strength == SignalStrength.WEAK_BUY:
            recommendations["entry_strategy"] = "Покупать небольшими порциями при коррекциях"
        else:
            recommendations["entry_strategy"] = "Не рекомендуется открывать позицию"
        
        # Stop-loss и Take-profit (если есть техническая информация)
        if "current_price" in technical_indicators:
            current_price = technical_indicators["current_price"]
            
            if signal_strength in [SignalStrength.STRONG_BUY, SignalStrength.BUY, SignalStrength.WEAK_BUY]:
                # Stop-loss на 7-15% ниже в зависимости от риска
                stop_loss_pct = 0.07 + (0.08 * (list(RiskLevel).index(risk_level) / 3))
                recommendations["stop_loss"] = current_price * (1 - stop_loss_pct)
                
                # Take-profit на 10-25% выше
                take_profit_pct = 0.10 + (0.15 * confidence)
                recommendations["take_profit"] = current_price * (1 + take_profit_pct)
                
                # Ожидаемая доходность
                min_return = 5 + (confidence * 10)
                max_return = 15 + (confidence * 20)
                recommendations["expected_return"] = (min_return, max_return)
        
        return recommendations
    
    def _generate_ai_reasoning(
        self, ticker: str, technical_score: float, news_score: float, 
        combined_score: float, signal_strength: SignalStrength, confidence: float
    ) -> str:
        """Генерация AI объяснения торгового решения."""
        
        reasoning_parts = []
        
        # Анализ технических факторов
        if abs(technical_score) > 0.3:
            tech_direction = "бычьи" if technical_score > 0 else "медвежьи"
            reasoning_parts.append(f"Технические индикаторы показывают {tech_direction} сигналы (score: {technical_score:+.2f})")
        else:
            reasoning_parts.append("Технические индикаторы нейтральны")
        
        # Анализ новостного фона
        if abs(news_score) > 0.2:
            news_direction = "позитивный" if news_score > 0 else "негативный"
            reasoning_parts.append(f"Новостной фон {news_direction} (sentiment: {news_score:+.2f})")
        else:
            reasoning_parts.append("Новостной фон нейтральный")
        
        # Итоговое решение
        reasoning_parts.append(f"Комбинированный AI score: {combined_score:+.2f}")
        reasoning_parts.append(f"Рекомендация: {signal_strength.value} с уверенностью {confidence:.0%}")
        
        return ". ".join(reasoning_parts) + "."
    
    def _create_error_signal(self, ticker: str, error_message: str) -> AISignal:
        """Создание сигнала при ошибке анализа."""
        return AISignal(
            ticker=ticker,
            signal_strength=SignalStrength.HOLD,
            confidence=0.0,
            risk_level=RiskLevel.HIGH,
            technical_score=0.0,
            news_sentiment_score=0.0,
            combined_score=0.0,
            recommended_position_size=0.0,
            entry_strategy="Анализ недоступен из-за ошибки",
            stop_loss_price=None,
            take_profit_price=None,
            expected_return=None,
            analysis_timestamp=datetime.now(),
            technical_indicators={},
            news_summary="Ошибка получения новостей",
            ai_reasoning=f"Анализ невозможен: {error_message}"
        )
    
    def format_signal_for_telegram(self, signal: AISignal) -> str:
        """Форматирование AI сигнала для отправки в Telegram."""
        
        # Эмодзи для различных типов сигналов
        signal_emojis = {
            SignalStrength.STRONG_BUY: "🟢🟢",
            SignalStrength.BUY: "🟢",
            SignalStrength.WEAK_BUY: "🟡",
            SignalStrength.HOLD: "⚪",
            SignalStrength.WEAK_SELL: "🟠",
            SignalStrength.SELL: "🔴",
            SignalStrength.STRONG_SELL: "🔴🔴",
        }
        
        risk_emojis = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡", 
            RiskLevel.HIGH: "🔴",
            RiskLevel.EXTREME: "⚫"
        }
        
        emoji = signal_emojis.get(signal.signal_strength, "⚪")
        risk_emoji = risk_emojis.get(signal.risk_level, "🟡")
        
        text = f"🤖 *AI АНАЛИЗ {signal.ticker}*\n\n"
        
        # Основные результаты
        text += f"📊 *Technical Signal:* {signal.technical_score:+.2f}\n"
        text += f"📰 *News Sentiment:* {signal.news_sentiment_score:+.2f}\n"
        text += f"🧠 *Combined AI Score:* {signal.combined_score:+.2f}\n\n"
        
        # AI рекомендация
        text += f"{emoji} *Рекомендация:* {signal.signal_strength.value}\n"
        text += f"🎯 *Уверенность:* {signal.confidence:.0%}\n"
        text += f"{risk_emoji} *Уровень риска:* {signal.risk_level.value}\n\n"
        
        # Торговые рекомендации
        if signal.recommended_position_size > 0:
            text += f"💡 *AI Рекомендации:*\n"
            text += f"Position Size: {signal.recommended_position_size:.1%} портфеля\n"
            text += f"Entry Strategy: {signal.entry_strategy}\n"
            
            if signal.stop_loss_price:
                text += f"🛡️ Stop Loss: {signal.stop_loss_price:.0f} ₽\n"
            if signal.take_profit_price:
                text += f"🎯 Take Profit: {signal.take_profit_price:.0f} ₽\n"
            if signal.expected_return:
                min_ret, max_ret = signal.expected_return
                text += f"📈 Expected Return: +{min_ret:.0f}-{max_ret:.0f}%\n"
        else:
            text += f"💡 *Рекомендация:* {signal.entry_strategy}\n"
        
        text += f"\n🧠 *AI Reasoning:*\n{signal.ai_reasoning}\n\n"
        
        # Техническая информация
        text += f"📅 *Анализ:* {signal.analysis_timestamp.strftime('%H:%M:%S')}\n"
        text += f"⚠️ *Дисклеймер:* AI анализ для образовательных целей"
        
        return text


# Глобальный экземпляр для использования в других модулях
_global_ai_integration = None


def get_ai_signal_integration() -> AISignalIntegration:
    """Получение глобального экземпляра AI Signal Integration."""
    global _global_ai_integration
    if _global_ai_integration is None:
        _global_ai_integration = AISignalIntegration()
    return _global_ai_integration


# Функция-обертка для быстрого использования
async def analyze_ticker_with_ai(ticker: str) -> AISignal:
    """Быстрая функция для AI анализа тикера."""
    ai_integration = get_ai_signal_integration()
    return await ai_integration.analyze_ticker(ticker)


def main():
    """Функция для тестирования модуля."""
    import asyncio
    
    async def test_ai_analysis():
        print("🤖 Тестирование AI Signal Integration...")
        
        try:
            ai_integration = AISignalIntegration()
            
            # Тестируем анализ для SBER
            print("📊 Тестируем AI анализ SBER...")
            signal = await ai_integration.analyze_ticker("SBER")
            
            print("✅ Результат AI анализа:")
            print(f"Сигнал: {signal.signal_strength.value}")
            print(f"Уверенность: {signal.confidence:.2f}")
            print(f"Комбинированный score: {signal.combined_score:+.2f}")
            print(f"Рекомендуемый размер позиции: {signal.recommended_position_size:.1%}")
            
            print("\n📱 Форматированный результат для Telegram:")
            telegram_text = ai_integration.format_signal_for_telegram(signal)
            print(telegram_text)
            
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
    
    asyncio.run(test_ai_analysis())


if __name__ == "__main__":
    main()
