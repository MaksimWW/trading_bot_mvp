
"""
Portfolio Coordinator - Умная координация множественных торговых стратегий.

Этот модуль обеспечивает интеллектуальное управление портфелем стратегий,
включая распределение капитала, агрегацию сигналов и ребалансировку.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from config import get_ticker_info
from portfolio_analytics import PortfolioAnalytics
from portfolio_manager import get_portfolio_manager
from strategy_engine import TradingSignal, get_strategy_engine
from strategy_executor import get_strategy_executor

logger = logging.getLogger(__name__)

# Поддерживаемые тикеры
SUPPORTED_TICKERS = ["SBER", "GAZP", "YNDX", "LKOH", "ROSN", "NVTK", "GMKN"]


class StrategyWeight(Enum):
    """Методы расчета весов стратегий."""

    EQUAL = "equal"
    PERFORMANCE_BASED = "performance_based"
    RISK_ADJUSTED = "risk_adjusted"
    CUSTOM = "custom"


@dataclass
class StrategyAllocation:
    """Распределение стратегии в портфеле."""

    strategy_id: str
    ticker: str
    weight: float
    target_allocation: float
    current_allocation: float
    performance_score: float
    risk_score: float
    last_rebalance: datetime


@dataclass
class PortfolioStatus:
    """Статус портфеля стратегий."""

    total_strategies: int
    active_strategies: int
    total_allocation: float
    cash_allocation: float
    last_rebalance: datetime
    performance_score: float
    risk_score: float


class PortfolioCoordinator:
    """Координатор портфеля множественных торговых стратегий."""

    def __init__(self):
        """Инициализация координатора портфеля."""
        from strategy_engine import get_strategy_engine
        self.strategy_engine = get_strategy_engine()
        self.strategy_executor = get_strategy_executor()
        self.portfolio_manager = get_portfolio_manager()
        self.portfolio_analytics = PortfolioAnalytics()

        # Стратегии и их распределение
        self.strategy_allocations: Dict[str, StrategyAllocation] = {}
        self.weight_method = StrategyWeight.EQUAL
        self.rebalance_threshold = 0.05  # 5% отклонение для ребалансировки
        self.max_strategy_weight = 0.4  # 40% максимум на стратегию
        self.min_strategy_weight = 0.1  # 10% минимум на активную стратегию

        # Настройки координации
        self.enabled = False
        self.last_coordination = None
        self.coordination_interval = timedelta(hours=6)  # Координация каждые 6 часов
        
        # Активные стратегии и статус координации
        self.active_strategies = {}
        self.coordination_status = "INITIALIZED"
        self._last_weight_calculation = None

        logger.info("Portfolio Coordinator инициализирован")

    def enable_coordination(self, weight_method: StrategyWeight = StrategyWeight.EQUAL):
        """Включить координацию портфеля."""
        self.enabled = True
        self.weight_method = weight_method
        self.last_coordination = datetime.now()
        logger.info(f"Portfolio coordination включена с методом {weight_method.value}")

    def disable_coordination(self):
        """Отключить координацию портфеля."""
        self.enabled = False
        logger.info("Portfolio coordination отключена")

    def add_strategy_to_portfolio(
        self, strategy_id: str, ticker: str, target_weight: float = None
    ) -> bool:
        """
        Добавить стратегию в портфель.

        Args:
            strategy_id: ID стратегии (rsi_mean_reversion, macd_trend_following)
            ticker: Тикер для стратегии
            target_weight: Целевой вес (если None, рассчитывается автоматически)

        Returns:
            True если стратегия добавлена успешно
        """
        try:
            ticker_info = get_ticker_info(ticker)
            if not ticker_info:
                logger.error(f"Тикер {ticker} не поддерживается")
                return False

            # Проверяем есть ли уже такая стратегия
            allocation_key = f"{strategy_id}_{ticker}"
            if allocation_key in self.strategy_allocations:
                logger.warning(f"Стратегия {allocation_key} уже в портфеле")
                return False

            # Рассчитываем целевой вес
            if target_weight is None:
                target_weight = self._calculate_auto_weight()

            # Создаем распределение стратегии
            allocation = StrategyAllocation(
                strategy_id=strategy_id,
                ticker=ticker,
                weight=target_weight,
                target_allocation=target_weight,
                current_allocation=0.0,
                performance_score=0.0,
                risk_score=0.5,  # Нейтральный риск изначально
                last_rebalance=datetime.now(),
            )

            self.strategy_allocations[allocation_key] = allocation

            # Перерасчет весов всех стратегий
            self._rebalance_weights()

            logger.info(f"Стратегия {allocation_key} добавлена с весом {target_weight:.2%}")
            return True

        except Exception as e:
            logger.error(f"Ошибка добавления стратегии {strategy_id} для {ticker}: {e}")
            return False

    def remove_strategy_from_portfolio(self, strategy_id: str, ticker: str) -> bool:
        """Удалить стратегию из портфеля."""
        try:
            allocation_key = f"{strategy_id}_{ticker}"
            if allocation_key not in self.strategy_allocations:
                logger.warning(f"Стратегия {allocation_key} не найдена в портфеле")
                return False

            del self.strategy_allocations[allocation_key]

            # Перерасчет весов оставшихся стратегий
            if self.strategy_allocations:
                self._rebalance_weights()

            logger.info(f"Стратегия {allocation_key} удалена из портфеля")
            return True

        except Exception as e:
            logger.error(f"Ошибка удаления стратегии {strategy_id} для {ticker}: {e}")
            return False

    async def coordinate_portfolio(self):
        """Основной метод координации портфеля стратегий."""
        logger.info("🚀 НАЧАЛО coordinate_portfolio")
        
        try:
            logger.info("📊 Шаг 1: Вызываем _sync_with_strategy_engine")
            await self._sync_with_strategy_engine()
            logger.info("✅ Шаг 1 завершен")
            
            logger.info("📊 Шаг 2: Вызываем _calculate_portfolio_weights")
            await self._calculate_portfolio_weights()
            logger.info("✅ Шаг 2 завершен")
            
            logger.info("📊 Шаг 3: Вызываем _update_coordination_status")
            self._update_coordination_status()
            logger.info("✅ Шаг 3 завершен")
            
            logger.info(f"📈 Координация завершена. Стратегий: {len(self.active_strategies)}")
            
            return {
                "success": True,
                "strategies_count": len(self.active_strategies),
                "total_weight": sum(getattr(s, 'weight', 0.0) for s in self.active_strategies.values()),
                "coordination_status": self.coordination_status if isinstance(self.coordination_status, str) else self.coordination_status.value,
                "last_coordination": self.last_coordination.isoformat() if self.last_coordination else None
            }
            
        except Exception as e:
            logger.error(f"❌ ОШИБКА в coordinate_portfolio: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                "success": False,
                "error": str(e),
                "strategies_count": 0
            }

    async def _gather_strategy_signals(self) -> Dict[str, TradingSignal]:
        """Собрать сигналы от всех стратегий в портфеле."""
        signals = {}

        for allocation_key, allocation in self.strategy_allocations.items():
            try:
                # Получаем сигнал от конкретной стратегии
                ticker_signals = await self.strategy_engine.execute_strategy_signals(
                    allocation.ticker
                )

                # Создаем TradingSignal из результата
                if isinstance(ticker_signals, dict):
                    recommendation = ticker_signals.get("recommendation", "HOLD")
                    confidence = ticker_signals.get("confidence", 0.0)

                    if recommendation != "HOLD" and confidence > 0:
                        trading_signal = TradingSignal(
                            ticker=allocation.ticker, action=recommendation, confidence=confidence
                        )
                        trading_signal.strategy_id = allocation.strategy_id
                        signals[allocation_key] = trading_signal

            except Exception as e:
                logger.error(f"Ошибка получения сигнала для {allocation_key}: {e}")

        logger.info(f"Собрано {len(signals)} сигналов от стратегий")
        return signals

    async def _sync_with_strategy_engine(self):
        """Синхронизация с Strategy Engine для получения активных стратегий."""
        logger.info("🔄 Начинаем синхронизацию с Strategy Engine")
        
        try:
            logger.info("📊 Получаем Strategy Engine instance")
            strategy_engine = get_strategy_engine()
            logger.info(f"✅ Strategy Engine получен: {type(strategy_engine)}")
            
            logger.info("📋 Получаем список стратегий")
            strategies = strategy_engine.get_all_strategies()
            logger.info(f"📊 Найдено стратегий: {len(strategies)}")
            
            for strategy_id, strategy in strategies.items():
                logger.info(f"🎯 Обрабатываем стратегию: {strategy_id}")
            
            # Получаем все стратегии и проверяем их active_tickers
            all_strategies = self.strategy_engine.strategies
            active_strategies = {}
            
            for strategy_id, strategy_obj in all_strategies.items():
                active_tickers = getattr(strategy_obj, 'active_tickers', [])
                logger.info(f"Проверка стратегии {strategy_id}: {len(active_tickers)} тикеров ({active_tickers})")
                if active_tickers:
                    self.active_strategies[strategy_id] = strategy_obj
                    logger.info(f"Стратегия {strategy_id} добавлена как активная")
                    logger.info(f"🔍 DEBUG: self.active_strategies размер: {len(self.active_strategies)}")
                    logger.info(f"🔍 DEBUG: self.active_strategies keys: {list(self.active_strategies.keys())}")
            
            logger.info(f"Strategy Engine содержит {len(self.active_strategies)} активных стратегий")
            
            for strategy_id, strategy_obj in self.active_strategies.items():
                # Получаем активные тикеры из стратегии
                if hasattr(strategy_obj, 'active_tickers'):
                    active_tickers = strategy_obj.active_tickers
                else:
                    active_tickers = ['SBER']  # Fallback
                
                # Добавляем каждый тикер в портфель
                for ticker in active_tickers:
                    allocation_key = f"{strategy_id}_{ticker}"
                    
                    # Добавляем стратегию в портфель если её нет
                    if allocation_key not in self.strategy_allocations:
                        success = self.add_strategy_to_portfolio(strategy_id, ticker)
                        if success:
                            logger.info(f"Auto-sync: добавлена стратегия {allocation_key}")
            
            logger.info(f"Синхронизация завершена. Стратегий в портфеле: {len(self.strategy_allocations)}")
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации с Strategy Engine: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def _calculate_portfolio_weights(self):
        """Расчет и обновление весов стратегий в портфеле."""
        logger.info("⚖️ Начинаем расчет весов портфеля")
        
        try:
            if not self.strategy_allocations:
                logger.info("Нет стратегий для расчета весов")
                return
            
            # Получаем сигналы от всех стратегий
            strategy_signals = await self._gather_strategy_signals()
            logger.info(f"Получено {len(strategy_signals)} сигналов")
            
            # Обновляем метрики производительности
            await self._update_performance_metrics()
            
            # Проверяем необходимость ребалансировки
            if self._check_rebalance_needed():
                logger.info("Требуется ребалансировка портфеля")
                await self._execute_rebalancing()
            
            # Агрегируем сигналы по тикерам
            aggregated_signals = self._aggregate_signals(strategy_signals)
            
            # Генерируем рекомендации
            recommendations = self._generate_recommendations(aggregated_signals)
            
            logger.info(f"Веса портфеля обновлены. Рекомендаций: {len(recommendations)}")
            
            # Сохраняем информацию о расчете весов
            self._last_weight_calculation = {
                "timestamp": datetime.now(),
                "strategies_count": len(self.strategy_allocations),
                "signals_count": len(strategy_signals),
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Ошибка расчета весов портфеля: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def _update_coordination_status(self):
        """Обновление статуса координации портфеля."""
        logger.info("📋 Обновляем статус координации")
        
        try:
            self.last_coordination = datetime.now()
            
            # Определяем статус координации
            if not self.enabled:
                coordination_status = "DISABLED"
            elif len(self.strategy_allocations) == 0:
                coordination_status = "NO_STRATEGIES"
            elif len(self.strategy_allocations) == 1:
                coordination_status = "SINGLE_STRATEGY"
            else:
                coordination_status = "ACTIVE"
            
            # Сохраняем статус
            self.coordination_status = coordination_status
            
            # Инициализируем active_strategies если не существует
            if not hasattr(self, 'active_strategies'):
                self.active_strategies = {}
            
            # Обновляем список активных стратегий
            for allocation_key, allocation in self.strategy_allocations.items():
                if allocation.weight > 0:
                    self.active_strategies[allocation_key] = allocation
            
            logger.info(f"Статус координации обновлен: {coordination_status}")
            
        except Exception as e:
            logger.error(f"Ошибка обновления статуса координации: {e}")

    def _aggregate_signals(self, strategy_signals: Dict[str, TradingSignal]) -> Dict[str, float]:
        """
        Агрегировать сигналы от множественных стратегий.

        Args:
            strategy_signals: Сигналы от стратегий

        Returns:
            Агрегированные сигналы по тикерам
        """
        ticker_aggregated = {}

        for allocation_key, signal in strategy_signals.items():
            allocation = self.strategy_allocations[allocation_key]
            ticker = allocation.ticker

            if ticker not in ticker_aggregated:
                ticker_aggregated[ticker] = {
                    "weighted_confidence": 0.0,
                    "total_weight": 0.0,
                    "signals_count": 0,
                }

            # Взвешиваем сигнал по весу стратегии
            signal_value = signal.confidence if signal.action == "BUY" else -signal.confidence
            weighted_confidence = signal_value * allocation.weight
            ticker_aggregated[ticker]["weighted_confidence"] += weighted_confidence
            ticker_aggregated[ticker]["total_weight"] += allocation.weight
            ticker_aggregated[ticker]["signals_count"] += 1

        # Нормализуем агрегированные сигналы
        final_signals = {}
        for ticker, data in ticker_aggregated.items():
            if data["total_weight"] > 0:
                final_signals[ticker] = data["weighted_confidence"] / data["total_weight"]
            else:
                final_signals[ticker] = 0.0

        logger.info(f"Агрегированы сигналы для {len(final_signals)} тикеров")
        return final_signals

    async def _update_performance_metrics(self):
        """Обновить метрики производительности стратегий."""
        try:
            # Получаем сводку портфеля
            portfolio_summary = self.portfolio_manager.get_portfolio_summary()
            total_value = portfolio_summary.get("portfolio_value", 1000000)

            for allocation_key, allocation in self.strategy_allocations.items():
                # Обновляем текущее распределение
                positions = portfolio_summary.get("positions", [])
                ticker_position = next(
                    (pos for pos in positions if pos["ticker"] == allocation.ticker), None
                )

                if ticker_position and total_value > 0:
                    allocation.current_allocation = ticker_position["total_value"] / total_value
                    allocation.performance_score = ticker_position.get("unrealized_pnl_percent", 0.0)
                else:
                    allocation.current_allocation = 0.0
                    allocation.performance_score = 0.0

        except Exception as e:
            logger.error(f"Ошибка обновления performance метрик: {e}")

    def _check_rebalance_needed(self) -> bool:
        """Проверить нужна ли ребалансировка."""
        for allocation in self.strategy_allocations.values():
            deviation = abs(allocation.current_allocation - allocation.target_allocation)
            if deviation > self.rebalance_threshold:
                logger.info(
                    f"Ребалансировка нужна: отклонение {deviation:.2%} > {self.rebalance_threshold:.2%}"
                )
                return True
        return False

    async def _execute_rebalancing(self):
        """Выполнить ребалансировку портфеля."""
        logger.info("Выполняем ребалансировку портфеля")

        # Здесь будет логика ребалансировки через portfolio_manager
        # Пока заглушка, в будущем можно добавить реальную логику

        for allocation in self.strategy_allocations.values():
            allocation.last_rebalance = datetime.now()

    def _generate_recommendations(self, aggregated_signals: Dict[str, float]) -> List[str]:
        """Генерировать рекомендации на основе агрегированных сигналов."""
        recommendations = []

        for ticker, signal_strength in aggregated_signals.items():
            if signal_strength > 0.6:
                recommendations.append(
                    f"STRONG BUY рекомендация для {ticker} (сигнал: {signal_strength:.2f})"
                )
            elif signal_strength > 0.3:
                recommendations.append(
                    f"BUY рекомендация для {ticker} (сигнал: {signal_strength:.2f})"
                )
            elif signal_strength < -0.6:
                recommendations.append(
                    f"STRONG SELL рекомендация для {ticker} (сигнал: {signal_strength:.2f})"
                )
            elif signal_strength < -0.3:
                recommendations.append(
                    f"SELL рекомендация для {ticker} (сигнал: {signal_strength:.2f})"
                )
            else:
                recommendations.append(
                    f"HOLD рекомендация для {ticker} (сигнал: {signal_strength:.2f})"
                )

        return recommendations

    def _calculate_auto_weight(self) -> float:
        """Рассчитать автоматический вес для новой стратегии."""
        current_strategies = len(self.strategy_allocations)

        if current_strategies == 0:
            return 1.0

        if self.weight_method == StrategyWeight.EQUAL:
            return 1.0 / (current_strategies + 1)
        else:
            # Для других методов - равный вес пока
            return 1.0 / (current_strategies + 1)

    def _rebalance_weights(self):
        """Перерасчет весов всех стратегий."""
        if not self.strategy_allocations:
            return

        if self.weight_method == StrategyWeight.EQUAL:
            equal_weight = 1.0 / len(self.strategy_allocations)
            for allocation in self.strategy_allocations.values():
                allocation.weight = equal_weight
                allocation.target_allocation = equal_weight

    def get_portfolio_status(self) -> PortfolioStatus:
        """Получить статус портфеля."""
        total_strategies = len(self.strategy_allocations)
        active_strategies = sum(1 for a in self.strategy_allocations.values() if a.weight > 0)

        total_allocation = sum(a.current_allocation for a in self.strategy_allocations.values())
        cash_allocation = max(0, 1.0 - total_allocation)

        avg_performance = (
            sum(a.performance_score for a in self.strategy_allocations.values())
            / max(1, total_strategies)
        )
        avg_risk = (
            sum(a.risk_score for a in self.strategy_allocations.values()) / max(1, total_strategies)
        )

        last_rebalance = max(
            (a.last_rebalance for a in self.strategy_allocations.values()),
            default=datetime.now(),
        )

        return PortfolioStatus(
            total_strategies=total_strategies,
            active_strategies=active_strategies,
            total_allocation=total_allocation,
            cash_allocation=cash_allocation,
            last_rebalance=last_rebalance,
            performance_score=avg_performance,
            risk_score=avg_risk,
        )

    def get_strategy_allocations(self) -> Dict[str, StrategyAllocation]:
        """Получить распределения всех стратегий."""
        return self.strategy_allocations.copy()

    def get_coordination_status(self) -> Dict:
        """Получить статус координации."""
        return {
            "enabled": self.enabled,
            "weight_method": self.weight_method.value,
            "strategies_count": len(self.strategy_allocations),
            "last_coordination": (
                self.last_coordination.isoformat() if self.last_coordination else None
            ),
            "rebalance_threshold": self.rebalance_threshold,
            "coordination_interval_hours": self.coordination_interval.total_seconds() / 3600,
        }


# Глобальный экземпляр координатора (singleton pattern)
_global_coordinator = None


def get_portfolio_coordinator() -> PortfolioCoordinator:
    """Получить глобальный экземпляр координатора портфеля."""
    global _global_coordinator
    if _global_coordinator is None:
        _global_coordinator = PortfolioCoordinator()
    return _global_coordinator


def main():
    """Функция для тестирования модуля."""

    async def test_coordinator():
        print("🧪 Тестирование Portfolio Coordinator...")

        try:
            coordinator = get_portfolio_coordinator()

            # Включаем координацию
            coordinator.enable_coordination(StrategyWeight.EQUAL)

            # Добавляем стратегии
            print("📊 Добавляем стратегии в портфель...")
            result1 = coordinator.add_strategy_to_portfolio("rsi_mean_reversion", "SBER")
            result2 = coordinator.add_strategy_to_portfolio("macd_trend_following", "SBER")

            print(f"RSI стратегия добавлена: {result1}")
            print(f"MACD стратегия добавлена: {result2}")

            # Получаем статус портфеля
            status = coordinator.get_portfolio_status()
            print(f"\n📋 Статус портфеля:")
            print(f"Всего стратегий: {status.total_strategies}")
            print(f"Активных стратегий: {status.active_strategies}")
            print(f"Средняя производительность: {status.performance_score:.2%}")

            # Тестируем координацию (базовую)
            print(f"\n🔄 Тестируем координацию портфеля...")
            coordination_result = await coordinator.coordinate_portfolio()
            print(f"Результат координации: {coordination_result}")

            # Получаем статус координации
            coord_status = coordinator.get_coordination_status()
            print(f"\n⚙️ Статус координации: {coord_status}")

        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
            import traceback

            traceback.print_exc()

    asyncio.run(test_coordinator())


if __name__ == "__main__":
    main()
