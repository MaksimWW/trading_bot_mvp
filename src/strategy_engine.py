"""
Strategy Engine для автоматических торговых стратегий.

Этот модуль реализует базовую архитектуру для создания и выполнения
автоматических торговых стратегий с интеграцией в существующую систему.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ai_signal_integration import AISignalIntegration
from news_analyzer import get_news_analyzer
from portfolio_manager import PortfolioManager
from technical_analysis import get_technical_analyzer
from strategy_state_manager import get_strategy_state_manager

logger = logging.getLogger(__name__)


class StrategyStatus(Enum):
    """Статусы стратегий."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class StrategyEvent:
    """Базовый класс для событий стратегий."""

    def __init__(self, strategy_id: str, event_type: str, data: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.now()


class TradingSignal:
    """Торговый сигнал от стратегии."""

    def __init__(
        self,
        ticker: str,
        action: str,
        confidence: float,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
    ):
        self.ticker = ticker
        self.action = action  # BUY, SELL, HOLD
        self.confidence = confidence  # 0.0 to 1.0
        self.quantity = quantity
        self.price = price
        self.timestamp = datetime.now()
        self.strategy_id = None

    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для логирования."""
        return {
            "ticker": self.ticker,
            "action": self.action,
            "confidence": self.confidence,
            "quantity": self.quantity,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "strategy_id": self.strategy_id,
        }


class BaseStrategy(ABC):
    """Базовый класс для всех торговых стратегий."""

    def __init__(self, strategy_id: str, name: str, config: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.name = name
        self.config = config
        self.status = StrategyStatus.INACTIVE
        self.created_at = datetime.now()
        self.last_execution = None
        self.signals_generated = 0
        self.performance_metrics = {}

        # Инициализация компонентов
        self.portfolio_manager = PortfolioManager()
        self.technical_analyzer = get_technical_analyzer()
        self.news_analyzer = get_news_analyzer()
        self.ai_signal = AISignalIntegration()

        logger.info(f"Инициализирована стратегия {self.name} (ID: {self.strategy_id})")

    @abstractmethod
    async def generate_signal(self, ticker: str) -> Optional[TradingSignal]:
        """Генерация торгового сигнала для тикера."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Описание стратегии."""
        pass

    def get_supported_tickers(self) -> List[str]:
        """Поддерживаемые тикеры."""
        return self.config.get("supported_tickers", ["SBER", "GAZP", "YNDX"])

    def start(self):
        """Запуск стратегии."""
        self.status = StrategyStatus.ACTIVE
        logger.info(f"Стратегия {self.name} запущена")

    def stop(self):
        """Остановка стратегии."""
        self.status = StrategyStatus.STOPPED
        logger.info(f"Стратегия {self.name} остановлена")

    def pause(self):
        """Пауза стратегии."""
        self.status = StrategyStatus.PAUSED
        logger.info(f"Стратегия {self.name} приостановлена")

    def get_status_info(self) -> Dict[str, Any]:
        """Получение статуса стратегии."""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "signals_generated": self.signals_generated,
            "supported_tickers": self.get_supported_tickers(),
            "description": self.get_description(),
        }


class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean Reversion стратегия.

    Покупает при RSI < 30 (oversold), продает при RSI > 70 (overbought).
    """

    def __init__(self, strategy_id: str = "rsi_mean_reversion"):
        config = {
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "rsi_period": 14,
            "supported_tickers": ["SBER", "GAZP", "YNDX", "LKOH"],
            "position_size_pct": 0.02,  # 2% от портфеля
        }
        super().__init__(strategy_id, "RSI Mean Reversion", config)

    def get_description(self) -> str:
        """Описание стратегии."""
        return (
            f"Покупка при RSI < {self.config['rsi_oversold']}, "
            f"продажа при RSI > {self.config['rsi_overbought']}"
        )

    async def generate_signal(self, ticker: str) -> Optional[TradingSignal]:
        """Генерация сигнала на основе RSI."""
        try:
            # Получаем технический анализ
            tech_data = await self.technical_analyzer.analyze_ticker(ticker)

            if not tech_data or not tech_data.get("success"):
                logger.warning(f"Не удалось получить технические данные для {ticker}")
                return None

            rsi_data = tech_data.get("rsi", {})
            rsi_value = rsi_data.get("value", 50)

            # Логика стратегии
            action = "HOLD"
            confidence = 0.5

            if rsi_value < self.config["rsi_oversold"]:
                action = "BUY"
                confidence = min(0.9, (self.config["rsi_oversold"] - rsi_value) / 20)
            elif rsi_value > self.config["rsi_overbought"]:
                action = "SELL"
                confidence = min(0.9, (rsi_value - self.config["rsi_overbought"]) / 20)

            # Создаем сигнал
            signal = TradingSignal(ticker=ticker, action=action, confidence=confidence)
            signal.strategy_id = self.strategy_id

            # Обновляем метрики
            self.last_execution = datetime.now()
            if action != "HOLD":
                self.signals_generated += 1

            logger.info(
                f"RSI стратегия {ticker}: RSI={rsi_value:.1f}, сигнал={action}, уверенность={confidence:.2f}"
            )

            return signal

        except Exception as e:
            logger.error(f"Ошибка в RSI стратегии для {ticker}: {e}")
            self.status = StrategyStatus.ERROR
            return None


class MACDTrendFollowingStrategy(BaseStrategy):
    """
    MACD Trend Following стратегия.

    Следует трендам на основе сигналов MACD.
    """

    def __init__(self, strategy_id: str = "macd_trend_following"):
        config = {
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "supported_tickers": ["SBER", "GAZP", "YNDX", "LKOH", "ROSN"],
            "position_size_pct": 0.03,  # 3% от портфеля
        }
        super().__init__(strategy_id, "MACD Trend Following", config)

    def get_description(self) -> str:
        """Описание стратегии."""
        return "Следование трендам на основе сигналов MACD (пересечения линий)"

    async def generate_signal(self, ticker: str) -> Optional[TradingSignal]:
        """Генерация сигнала на основе MACD."""
        try:
            # Получаем технический анализ
            tech_data = await self.technical_analyzer.analyze_ticker(ticker)

            if not tech_data or not tech_data.get("success"):
                logger.warning(f"Не удалось получить технические данные для {ticker}")
                return None

            macd_data = tech_data.get("macd", {})
            macd_value = macd_data.get("macd_line", 0)
            signal_line = macd_data.get("signal_line", 0)
            histogram = macd_data.get("histogram", 0)

            # Логика стратегии
            action = "HOLD"
            confidence = 0.5

            # MACD пересекает сигнальную линию снизу вверх = BUY
            if macd_value > signal_line and histogram > 0:
                action = "BUY"
                confidence = min(0.8, abs(histogram) / 10)
            # MACD пересекает сигнальную линию сверху вниз = SELL
            elif macd_value < signal_line and histogram < 0:
                action = "SELL"
                confidence = min(0.8, abs(histogram) / 10)

            # Создаем сигнал
            signal = TradingSignal(ticker=ticker, action=action, confidence=confidence)
            signal.strategy_id = self.strategy_id

            # Обновляем метрики
            self.last_execution = datetime.now()
            if action != "HOLD":
                self.signals_generated += 1

            logger.info(
                f"MACD стратегия {ticker}: MACD={macd_value:.3f}, сигнал={action}, уверенность={confidence:.2f}"
            )

            return signal

        except Exception as e:
            logger.error(f"Ошибка в MACD стратегии для {ticker}: {e}")
            self.status = StrategyStatus.ERROR
            return None


class StrategyEngine:
    """
    Основной движок для управления торговыми стратегиями.
    """

    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_strategies: Dict[str, BaseStrategy] = {}
        self.signal_history: List[TradingSignal] = []
        self.portfolio_manager = PortfolioManager()

        # Инициализация стандартных стратегий
        self._initialize_default_strategies()

        # Восстанавливаем состояние стратегий
        self._restore_strategy_state()

        logger.info("StrategyEngine инициализирован")

    def _initialize_default_strategies(self):
        """Инициализация стандартных стратегий."""
        # RSI стратегия
        rsi_strategy = RSIMeanReversionStrategy()
        self.strategies[rsi_strategy.strategy_id] = rsi_strategy

        # MACD стратегия
        macd_strategy = MACDTrendFollowingStrategy()
        self.strategies[macd_strategy.strategy_id] = macd_strategy

        logger.info(f"Инициализировано {len(self.strategies)} стратегий")

    def get_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Получение всех доступных стратегий."""
        return {
            strategy_id: strategy.get_status_info()
            for strategy_id, strategy in self.strategies.items()
        }

    def get_active_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Получение активных стратегий."""
        return {
            strategy_id: strategy.get_status_info()
            for strategy_id, strategy in self.active_strategies.items()
        }

    def start_strategy(self, strategy_id: str, tickers: List[str]) -> Dict[str, Any]:
        """
        Запустить стратегию для указанных тикеров.
        
        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров
            
        Returns:
            Результат запуска стратегии
        """
        if strategy_id not in self.strategies:
            return {
                "success": False,
                "message": f"Стратегия {strategy_id} не найдена",
                "available_strategies": list(self.strategies.keys())
            }
        
        strategy = self.strategies[strategy_id]
        
        try:
            # Обновляем active_tickers стратегии
            if not hasattr(strategy, 'active_tickers'):
                strategy.active_tickers = []
            
            # Добавляем новые тикеры
            for ticker in tickers:
                if ticker not in strategy.active_tickers:
                    strategy.active_tickers.append(ticker)
            
            # Сохраняем состояние через State Manager
            state_manager = get_strategy_state_manager()
            state_manager.start_strategy(strategy_id, tickers)
            
            logger.info(f"Стратегия {strategy.name} запущена")
            logger.info(f"Стратегия {strategy_id} запущена для тикеров: {tickers}")
            
            return {
                "success": True,
                "message": f"Стратегия {strategy.name} запущена для {len(tickers)} тикеров",
                "strategy_name": strategy.name,
                "tickers": tickers,
                "total_active_tickers": len(strategy.active_tickers)
            }
            
        except Exception as e:
            logger.error(f"Ошибка запуска стратегии {strategy_id}: {e}")
            return {
                "success": False,
                "message": f"Ошибка: {str(e)}"
            }

    def stop_strategy(self, strategy_id: str) -> bool:
        """Остановка стратегии."""
        if strategy_id not in self.active_strategies:
            logger.warning(f"Стратегия {strategy_id} не активна")
            return False

        strategy = self.active_strategies[strategy_id]
        strategy.stop()
        del self.active_strategies[strategy_id]

        logger.info(f"Стратегия {strategy_id} остановлена")
        return True

    def stop_all_strategies(self):
        """Остановка всех стратегий."""
        strategy_ids = list(self.active_strategies.keys())
        for strategy_id in strategy_ids:
            self.stop_strategy(strategy_id)

        logger.info("Все стратегии остановлены")

    async def generate_signals_for_ticker(self, ticker: str) -> List[TradingSignal]:
        """Генерация сигналов для тикера от всех активных стратегий."""
        signals = []

        for strategy_id, strategy in self.active_strategies.items():
            if ticker in strategy.get_supported_tickers():
                try:
                    signal = await strategy.generate_signal(ticker)
                    if signal:
                        signals.append(signal)
                        self.signal_history.append(signal)

                        # Ограничиваем историю сигналов
                        if len(self.signal_history) > 1000:
                            self.signal_history = self.signal_history[-1000:]

                except Exception as e:
                    logger.error(f"Ошибка генерации сигнала {strategy_id} для {ticker}: {e}")

        return signals

    async def execute_strategy_signals(
        self, ticker: str, auto_execute: bool = False
    ) -> Dict[str, Any]:
        """
        Выполнение стратегических сигналов для тикера.

        Returns:
            Отчет о сгенерированных сигналах и рекомендациях
        """
        signals = await self.generate_signals_for_ticker(ticker)

        if not signals:
            return {
                "ticker": ticker,
                "signals_count": 0,
                "recommendation": "HOLD",
                "confidence": 0.0,
                "message": "Нет активных стратегий для данного тикера",
            }

        # Агрегация сигналов
        buy_signals = [s for s in signals if s.action == "BUY"]
        sell_signals = [s for s in signals if s.action == "SELL"]

        # Расчет итогового сигнала
        if buy_signals:
            avg_buy_confidence = sum(s.confidence for s in buy_signals) / len(buy_signals)
            if avg_buy_confidence > 0.6:
                final_recommendation = "BUY"
                final_confidence = avg_buy_confidence
            else:
                final_recommendation = "HOLD"
                final_confidence = avg_buy_confidence
        elif sell_signals:
            avg_sell_confidence = sum(s.confidence for s in sell_signals) / len(sell_signals)
            if avg_sell_confidence > 0.6:
                final_recommendation = "SELL"
                final_confidence = avg_sell_confidence
            else:
                final_recommendation = "HOLD"
                final_confidence = avg_sell_confidence
        else:
            final_recommendation = "HOLD"
            final_confidence = 0.5

        # Автоматическое исполнение (если включено)
        executed_trades = []
        if auto_execute and final_recommendation in ["BUY", "SELL"] and final_confidence > 0.7:
            # TODO: Реализовать автоматическое исполнение сделок
            pass

        return {
            "ticker": ticker,
            "signals_count": len(signals),
            "signals": [s.to_dict() for s in signals],
            "recommendation": final_recommendation,
            "confidence": final_confidence,
            "buy_signals": len(buy_signals),
            "sell_signals": len(sell_signals),
            "executed_trades": executed_trades,
            "timestamp": datetime.now().isoformat(),
        }

    def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        """Получение метрик производительности стратегии."""
        if strategy_id not in self.strategies:
            return {"error": f"Стратегия {strategy_id} не найдена"}

        strategy = self.strategies[strategy_id]

        # Фильтруем сигналы этой стратегии
        strategy_signals = [s for s in self.signal_history if s.strategy_id == strategy_id]

        # Базовые метрики
        total_signals = len(strategy_signals)
        buy_signals = len([s for s in strategy_signals if s.action == "BUY"])
        sell_signals = len([s for s in strategy_signals if s.action == "SELL"])
        avg_confidence = (
            sum(s.confidence for s in strategy_signals) / total_signals if total_signals > 0 else 0
        )

        return {
            "strategy_id": strategy_id,
            "name": strategy.name,
            "total_signals": total_signals,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "avg_confidence": round(avg_confidence, 3),
            "status": strategy.status.value,
            "last_execution": (
                strategy.last_execution.isoformat() if strategy.last_execution else None
            ),
        }


# Глобальный экземпляр движка стратегий
_global_strategy_engine = None


def get_strategy_engine() -> StrategyEngine:
    """Получение глобального экземпляра движка стратегий."""
    global _global_strategy_engine
    if _global_strategy_engine is None:
        _global_strategy_engine = StrategyEngine()
    return _global_strategy_engine


async def test_strategy_engine():
    """Функция для тестирования Strategy Engine."""
    print("🧪 Тестирование Strategy Engine...")

    try:
        # Создаем движок
        engine = get_strategy_engine()

        # Получаем список стратегий
        print("\n📊 Доступные стратегии:")
        strategies = engine.get_all_strategies()
        for strategy_id, info in strategies.items():
            print(f"  • {info['name']} (ID: {strategy_id})")
            print(f"    Статус: {info['status']}")
            print(f"    Описание: {info['description']}")

        # Запускаем RSI стратегию
        print("\n🚀 Запуск RSI стратегии...")
        success = engine.start_strategy("rsi_mean_reversion", ["SBER"])
        print(f"Результат: {'✅ Успешно' if success else '❌ Ошибка'}")

        # Генерируем сигналы для SBER
        print("\n📈 Генерация сигналов для SBER...")
        result = await engine.execute_strategy_signals("SBER")

        print(f"Тикер: {result['ticker']}")
        print(f"Сигналов: {result['signals_count']}")
        print(f"Рекомендация: {result['recommendation']}")
        print(f"Уверенность: {result['confidence']:.2f}")

        # Статистика по стратегии
        print("\n📊 Производительность RSI стратегии:")
        perf = engine.get_strategy_performance("rsi_mean_reversion")
        for key, value in perf.items():
            print(f"  {key}: {value}")

        print("\n✅ Тестирование завершено успешно!")

    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Главная функция для тестирования."""
    print("🤖 Strategy Engine для торгового бота")
    print("=" * 50)

    # Запуск тестирования
    asyncio.run(test_strategy_engine())


if __name__ == "__main__":
    main()
