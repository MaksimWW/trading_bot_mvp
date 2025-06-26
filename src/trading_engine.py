
"""
Trading Engine - Система автоматизации торговых решений.

Этот модуль реализует:
- Автоматическое принятие торговых решений
- Мониторинг позиций
- Управление ордерами
- Автоматические отчеты
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from risk_manager import RiskManager, RiskSettings
from technical_analysis import TechnicalAnalyzer
from news_analyzer import NewsAnalyzer

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Режимы торговли."""
    MANUAL = "MANUAL"           # Ручной режим
    SEMI_AUTO = "SEMI_AUTO"     # Полуавтоматический
    AUTO = "AUTO"               # Полностью автоматический
    PAPER = "PAPER"             # Виртуальная торговля


class SignalStrength(Enum):
    """Сила торгового сигнала."""
    VERY_WEAK = "VERY_WEAK"
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


@dataclass
class TradingSignal:
    """Торговый сигнал."""
    ticker: str
    direction: str  # BUY/SELL/HOLD
    strength: SignalStrength
    confidence: float
    technical_score: float
    news_score: float
    combined_score: float
    entry_price: float
    stop_loss: float
    take_profit: float
    reasoning: str
    timestamp: datetime


@dataclass
class TradingPosition:
    """Торговая позиция."""
    ticker: str
    direction: str
    shares: int
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    days_held: int
    status: str  # OPEN/CLOSED/PENDING


class TradingEngine:
    """Главный класс торгового движка."""
    
    def __init__(self, 
                 mode: TradingMode = TradingMode.PAPER,
                 risk_settings: Optional[RiskSettings] = None):
        """
        Инициализация торгового движка.
        
        Args:
            mode: Режим торговли
            risk_settings: Настройки риск-менеджмента
        """
        self.mode = mode
        self.risk_manager = RiskManager(risk_settings)
        self.technical_analyzer = TechnicalAnalyzer()
        self.news_analyzer = NewsAnalyzer()
        
        # Состояние системы
        self.is_running = False
        self.positions: List[TradingPosition] = []
        self.signals_history: List[TradingSignal] = []
        self.daily_stats = {
            "trades_count": 0,
            "pnl": 0.0,
            "successful_trades": 0,
            "failed_trades": 0
        }
        
        # Настройки
        self.watchlist = ["SBER", "GAZP", "YNDX", "LKOH", "NVTK"]
        self.scan_interval = 300  # 5 минут
        self.min_signal_strength = SignalStrength.WEAK
        self.min_confidence = 0.5
        
        logger.info(f"TradingEngine инициализирован в режиме {mode.value}")
    
    async def generate_trading_signal(self, ticker: str) -> Optional[TradingSignal]:
        """
        Генерация торгового сигнала для тикера.
        
        Args:
            ticker: Тикер для анализа
            
        Returns:
            Торговый сигнал или None
        """
        try:
            logger.info(f"Генерируем торговый сигнал для {ticker}")
            
            # Получаем технический анализ
            technical_result = await self.technical_analyzer.analyze_ticker(ticker)
            if not technical_result.get("success", False):
                logger.warning(f"Технический анализ {ticker} не удался")
                return None
            
            technical_score = technical_result.get("combined_signal", 0.0)
            
            # Получаем анализ новостей
            news_result = await self.news_analyzer.analyze_ticker_news(ticker, include_sentiment=True)
            news_score = 0.0
            if news_result.get("success", False) and news_result.get("sentiment"):
                news_score = news_result["sentiment"].get("sentiment_score", 0.0)
            
            # Комбинированный сигнал (техника 60%, новости 40%)
            combined_score = (technical_score * 0.6) + (news_score * 0.4)
            
            # Определяем направление и силу сигнала
            direction, strength = self._interpret_signal(combined_score)
            
            # Рассчитываем уверенность
            confidence = self._calculate_confidence(technical_result, news_result)
            
            # Если сигнал слишком слабый, не создаем
            if strength.value in ["VERY_WEAK", "WEAK"] or confidence < self.min_confidence:
                logger.info(f"{ticker}: сигнал слишком слабый ({strength.value}, confidence: {confidence:.2f})")
                return None
            
            # Получаем текущую цену (заглушка)
            entry_price = 100.0  # В реальности получаем через Tinkoff API
            
            # Рассчитываем уровни
            stop_loss, take_profit = self._calculate_levels(entry_price, direction, strength)
            
            # Формируем обоснование
            reasoning = self._generate_reasoning(technical_result, news_result, combined_score)
            
            signal = TradingSignal(
                ticker=ticker,
                direction=direction,
                strength=strength,
                confidence=confidence,
                technical_score=technical_score,
                news_score=news_score,
                combined_score=combined_score,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasoning=reasoning,
                timestamp=datetime.now()
            )
            
            logger.info(f"Сигнал {ticker}: {direction} ({strength.value}, {confidence:.2f})")
            return signal
            
        except Exception as e:
            logger.error(f"Ошибка генерации сигнала для {ticker}: {e}")
            return None
    
    async def process_signal(self, signal: TradingSignal) -> Dict:
        """
        Обработка торгового сигнала.
        
        Args:
            signal: Торговый сигнал
            
        Returns:
            Результат обработки
        """
        try:
            logger.info(f"Обрабатываем сигнал {signal.ticker}: {signal.direction}")
            
            # Проверяем риск-менеджмент
            risk_analysis = self.risk_manager.calculate_position_size(
                ticker=signal.ticker,
                entry_price=signal.entry_price,
                stop_loss_price=signal.stop_loss,
                account_balance=100000.0,  # Примерный баланс
                confidence_score=signal.confidence
            )
            
            if not risk_analysis.get("approved", False):
                return {
                    "status": "rejected",
                    "reason": risk_analysis.get("reason", "Риск-менеджмент отклонил сделку"),
                    "signal": signal
                }
            
            # В зависимости от режима
            if self.mode == TradingMode.PAPER:
                return await self._execute_paper_trade(signal, risk_analysis)
            elif self.mode == TradingMode.MANUAL:
                return await self._create_manual_recommendation(signal, risk_analysis)
            elif self.mode == TradingMode.AUTO:
                return await self._execute_auto_trade(signal, risk_analysis)
            else:
                return {"status": "unsupported_mode", "mode": self.mode.value}
                
        except Exception as e:
            logger.error(f"Ошибка обработки сигнала {signal.ticker}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def scan_market(self) -> List[TradingSignal]:
        """
        Сканирование рынка на предмет торговых возможностей.
        
        Returns:
            Список сгенерированных сигналов
        """
        logger.info("Начинаем сканирование рынка")
        signals = []
        
        for ticker in self.watchlist:
            try:
                signal = await self.generate_trading_signal(ticker)
                if signal:
                    signals.append(signal)
                    self.signals_history.append(signal)
                
                # Небольшая пауза между запросами
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Ошибка сканирования {ticker}: {e}")
                continue
        
        logger.info(f"Сканирование завершено: найдено {len(signals)} сигналов")
        return signals
    
    async def monitor_positions(self) -> Dict:
        """
        Мониторинг открытых позиций.
        
        Returns:
            Статус позиций
        """
        if not self.positions:
            return {"message": "Нет открытых позиций", "positions": []}
        
        logger.info(f"Мониторим {len(self.positions)} позиций")
        
        position_updates = []
        for position in self.positions:
            try:
                # Получаем текущую цену (заглушка)
                current_price = position.entry_price * (1 + (hash(position.ticker) % 10 - 5) / 100)
                
                # Обновляем позицию
                updated_position = self._update_position(position, current_price)
                position_updates.append(updated_position)
                
                # Проверяем нужно ли закрыть позицию
                close_reason = self._should_close_position(updated_position)
                if close_reason:
                    logger.info(f"Закрываем позицию {position.ticker}: {close_reason}")
                    # Здесь была бы логика закрытия позиции
                
            except Exception as e:
                logger.error(f"Ошибка мониторинга позиции {position.ticker}: {e}")
        
        return {
            "positions_count": len(position_updates),
            "total_pnl": sum(p.unrealized_pnl for p in position_updates),
            "positions": [self._position_to_dict(p) for p in position_updates]
        }
    
    async def generate_daily_report(self) -> Dict:
        """
        Генерация ежедневного отчета.
        
        Returns:
            Ежедневный отчет
        """
        logger.info("Генерируем ежедневный отчет")
        
        # Статистика за день
        today_signals = [s for s in self.signals_history 
                        if s.timestamp.date() == datetime.now().date()]
        
        # Анализ производительности
        total_pnl = sum(p.unrealized_pnl for p in self.positions)
        success_rate = 0.0
        if self.daily_stats["trades_count"] > 0:
            success_rate = (self.daily_stats["successful_trades"] / 
                          self.daily_stats["trades_count"]) * 100
        
        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "mode": self.mode.value,
            "signals": {
                "total": len(today_signals),
                "buy": len([s for s in today_signals if s.direction == "BUY"]),
                "sell": len([s for s in today_signals if s.direction == "SELL"]),
                "avg_confidence": sum(s.confidence for s in today_signals) / len(today_signals) if today_signals else 0
            },
            "positions": {
                "active": len(self.positions),
                "total_pnl": total_pnl,
                "total_pnl_percent": (total_pnl / 100000.0) * 100  # Примерный расчет
            },
            "performance": {
                "trades_count": self.daily_stats["trades_count"],
                "success_rate": success_rate,
                "daily_pnl": self.daily_stats["pnl"]
            },
            "risk_metrics": {
                "portfolio_risk": sum(2.0 for _ in self.positions),  # Заглушка
                "max_drawdown": 0.0,  # Заглушка
                "sharpe_ratio": 0.0   # Заглушка
            }
        }
        
        return report
    
    def _interpret_signal(self, combined_score: float) -> Tuple[str, SignalStrength]:
        """Интерпретация комбинированного сигнала."""
        abs_score = abs(combined_score)
        
        if abs_score >= 0.8:
            strength = SignalStrength.VERY_STRONG
        elif abs_score >= 0.6:
            strength = SignalStrength.STRONG
        elif abs_score >= 0.4:
            strength = SignalStrength.MODERATE
        elif abs_score >= 0.2:
            strength = SignalStrength.WEAK
        else:
            strength = SignalStrength.VERY_WEAK
        
        direction = "BUY" if combined_score > 0.1 else "SELL" if combined_score < -0.1 else "HOLD"
        
        return direction, strength
    
    def _calculate_confidence(self, technical_result: Dict, news_result: Dict) -> float:
        """Расчет уверенности в сигнале."""
        confidence = 0.5  # Базовая уверенность
        
        # Факторы технического анализа
        if technical_result.get("rsi_signal") and technical_result.get("macd_signal"):
            confidence += 0.2  # Согласованность индикаторов
        
        # Факторы новостного анализа
        if news_result.get("sentiment") and news_result["sentiment"].get("confidence", 0) > 0.7:
            confidence += 0.2  # Высокая уверенность в sentiment
        
        # Ограничиваем диапазон
        return max(0.0, min(1.0, confidence))
    
    def _calculate_levels(self, entry_price: float, direction: str, strength: SignalStrength) -> Tuple[float, float]:
        """Расчет уровней стоп-лосса и тейк-профита."""
        # Базовые проценты в зависимости от силы сигнала
        if strength == SignalStrength.VERY_STRONG:
            sl_percent, tp_percent = 0.05, 0.15  # 5% SL, 15% TP
        elif strength == SignalStrength.STRONG:
            sl_percent, tp_percent = 0.06, 0.12
        else:
            sl_percent, tp_percent = 0.07, 0.10  # Консервативные уровни
        
        if direction == "BUY":
            stop_loss = entry_price * (1 - sl_percent)
            take_profit = entry_price * (1 + tp_percent)
        else:  # SELL
            stop_loss = entry_price * (1 + sl_percent)
            take_profit = entry_price * (1 - tp_percent)
        
        return round(stop_loss, 2), round(take_profit, 2)
    
    def _generate_reasoning(self, technical_result: Dict, news_result: Dict, combined_score: float) -> str:
        """Генерация обоснования сигнала."""
        reasons = []
        
        # Технические факторы
        if technical_result.get("rsi_signal") == "BUY":
            reasons.append("RSI показывает перепроданность")
        elif technical_result.get("rsi_signal") == "SELL":
            reasons.append("RSI показывает перекупленность")
        
        if technical_result.get("macd_signal") == "BUY":
            reasons.append("MACD дает сигнал на покупку")
        
        # Новостные факторы
        if news_result.get("sentiment"):
            sentiment = news_result["sentiment"]
            if sentiment.get("sentiment_score", 0) > 0.3:
                reasons.append("Позитивные новости поддерживают рост")
            elif sentiment.get("sentiment_score", 0) < -0.3:
                reasons.append("Негативные новости создают давление")
        
        # Общая оценка
        if abs(combined_score) > 0.6:
            reasons.append(f"Сильный комбинированный сигнал ({combined_score:.2f})")
        
        return "; ".join(reasons) if reasons else "Стандартный технический сигнал"
    
    async def _execute_paper_trade(self, signal: TradingSignal, risk_analysis: Dict) -> Dict:
        """Выполнение виртуальной сделки."""
        position = TradingPosition(
            ticker=signal.ticker,
            direction=signal.direction,
            shares=risk_analysis["shares_count"],
            entry_price=signal.entry_price,
            current_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            unrealized_pnl=0.0,
            unrealized_pnl_percent=0.0,
            days_held=0,
            status="OPEN"
        )
        
        self.positions.append(position)
        self.daily_stats["trades_count"] += 1
        
        return {
            "status": "executed_paper",
            "position": self._position_to_dict(position),
            "message": f"Виртуальная позиция {signal.direction} {signal.ticker} открыта"
        }
    
    async def _create_manual_recommendation(self, signal: TradingSignal, risk_analysis: Dict) -> Dict:
        """Создание рекомендации для ручной торговли."""
        return {
            "status": "manual_recommendation",
            "signal": {
                "ticker": signal.ticker,
                "direction": signal.direction,
                "strength": signal.strength.value,
                "confidence": signal.confidence,
                "reasoning": signal.reasoning
            },
            "recommendation": {
                "shares": risk_analysis["shares_count"],
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "risk_amount": risk_analysis["risk_amount"]
            },
            "message": f"Рекомендация: {signal.direction} {signal.ticker} ({signal.strength.value})"
        }
    
    async def _execute_auto_trade(self, signal: TradingSignal, risk_analysis: Dict) -> Dict:
        """Выполнение автоматической сделки."""
        # В реальности здесь была бы интеграция с брокерским API
        logger.info(f"AUTO TRADE: {signal.direction} {signal.ticker}")
        
        return {
            "status": "executed_auto",
            "order_id": f"AUTO_{signal.ticker}_{datetime.now().timestamp()}",
            "message": f"Автоматическая сделка {signal.direction} {signal.ticker} выполнена"
        }
    
    def _update_position(self, position: TradingPosition, current_price: float) -> TradingPosition:
        """Обновление позиции текущей ценой."""
        position.current_price = current_price
        
        if position.direction == "BUY":
            position.unrealized_pnl = (current_price - position.entry_price) * position.shares
        else:  # SELL
            position.unrealized_pnl = (position.entry_price - current_price) * position.shares
        
        if position.entry_price > 0:
            position.unrealized_pnl_percent = (position.unrealized_pnl / 
                                             (position.entry_price * position.shares)) * 100
        
        return position
    
    def _should_close_position(self, position: TradingPosition) -> Optional[str]:
        """Проверка нужно ли закрыть позицию."""
        # Проверка стоп-лосса
        if position.direction == "BUY" and position.current_price <= position.stop_loss:
            return "Stop-loss triggered"
        elif position.direction == "SELL" and position.current_price >= position.stop_loss:
            return "Stop-loss triggered"
        
        # Проверка тейк-профита
        if position.direction == "BUY" and position.current_price >= position.take_profit:
            return "Take-profit reached"
        elif position.direction == "SELL" and position.current_price <= position.take_profit:
            return "Take-profit reached"
        
        return None
    
    def _position_to_dict(self, position: TradingPosition) -> Dict:
        """Конвертация позиции в словарь."""
        return {
            "ticker": position.ticker,
            "direction": position.direction,
            "shares": position.shares,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "stop_loss": position.stop_loss,
            "take_profit": position.take_profit,
            "unrealized_pnl": round(position.unrealized_pnl, 2),
            "unrealized_pnl_percent": round(position.unrealized_pnl_percent, 2),
            "days_held": position.days_held,
            "status": position.status
        }


def main():
    """Функция для тестирования модуля."""
    import asyncio
    
    async def test_trading_engine():
        print("🧪 Тестирование TradingEngine...")
        
        # Создаем торговый движок
        engine = TradingEngine(mode=TradingMode.PAPER)
        
        # Тест генерации сигнала
        print("\n📊 Тест генерации сигнала:")
        signal = await engine.generate_trading_signal("SBER")
        if signal:
            print(f"  Тикер: {signal.ticker}")
            print(f"  Направление: {signal.direction}")
            print(f"  Сила: {signal.strength.value}")
            print(f"  Уверенность: {signal.confidence:.2f}")
            print(f"  Обоснование: {signal.reasoning}")
        else:
            print("  Сигнал не сгенерирован")
        
        # Тест ежедневного отчета
        print("\n📋 Тест ежедневного отчета:")
        report = await engine.generate_daily_report()
        for key, value in report.items():
            print(f"  {key}: {value}")
        
        print("\n✅ Тестирование TradingEngine завершено!")
    
    asyncio.run(test_trading_engine())


if __name__ == "__main__":
    main()
