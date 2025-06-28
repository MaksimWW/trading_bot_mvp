"""
Strategy Executor - Автоматическое исполнение торговых сигналов.

Этот модуль обеспечивает автоматическое исполнение сделок на основе сигналов
от торговых стратегий с контролем рисков и position sizing.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from config import PORTFOLIO_CONFIG, STRATEGY_CONFIG
from portfolio_manager import PortfolioManager
from risk_manager import RiskManager
from strategy_engine import TradingSignal, get_strategy_engine

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Режимы автоматического исполнения."""

    DISABLED = "disabled"
    MANUAL_APPROVAL = "manual_approval"
    AUTOMATIC = "automatic"


class ExecutionStatus(Enum):
    """Статусы исполнения сигналов."""

    PENDING = "pending"
    EXECUTED = "executed"
    REJECTED = "rejected"
    FAILED = "failed"


class ExecutionRecord:
    """Запись об исполнении торгового сигнала."""

    def __init__(self, signal: TradingSignal, ticker: str):
        self.signal = signal
        self.ticker = ticker
        self.timestamp = datetime.now()
        self.status = ExecutionStatus.PENDING
        self.execution_price = None
        self.quantity = None
        self.commission = None
        self.error_message = None
        self.portfolio_impact = None

    def to_dict(self) -> Dict:
        """Конвертация в словарь для логирования."""
        return {
            "ticker": self.ticker,
            "signal_action": self.signal.action,
            "signal_confidence": self.signal.confidence,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "execution_price": self.execution_price,
            "quantity": self.quantity,
            "commission": self.commission,
            "error_message": self.error_message,
        }


class StrategyExecutor:
    """Автоматическое исполнение торговых стратегий."""

    def __init__(self):
        """Инициализация Strategy Executor."""
        self.portfolio_manager = PortfolioManager()
        self.risk_manager = RiskManager()
        self.strategy_engine = get_strategy_engine()

        # Настройки исполнения
        self.execution_mode = ExecutionMode.DISABLED
        self.min_confidence_threshold = 0.7
        self.max_position_size_pct = 0.05  # 5% максимум на позицию
        self.enabled_tickers = set()

        # История исполнений
        self.execution_history: List[ExecutionRecord] = []
        self.daily_executions = 0
        self.last_reset_date = datetime.now().date()

        logger.info("StrategyExecutor инициализирован")

    def enable_auto_trading(self, mode: ExecutionMode = ExecutionMode.AUTOMATIC) -> bool:
        """
        Включение автоматической торговли.

        Args:
            mode: Режим исполнения

        Returns:
            True если успешно включено
        """
        try:
            self.execution_mode = mode
            logger.info(f"Автоматическая торговля включена: {mode.value}")
            return True
        except Exception as e:
            logger.error(f"Ошибка включения автоматической торговли: {e}")
            return False

    def disable_auto_trading(self) -> bool:
        """Отключение автоматической торговли."""
        try:
            self.execution_mode = ExecutionMode.DISABLED
            logger.info("Автоматическая торговля отключена")
            return True
        except Exception as e:
            logger.error(f"Ошибка отключения автоматической торговли: {e}")
            return False

    def add_ticker_for_execution(self, ticker: str) -> bool:
        """
        Добавить тикер для автоматического исполнения.

        Args:
            ticker: Тикер акции

        Returns:
            True если успешно добавлен
        """
        try:
            ticker = ticker.upper()
            self.enabled_tickers.add(ticker)
            logger.info(f"Тикер {ticker} добавлен для автоматического исполнения")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления тикера {ticker}: {e}")
            return False

    def remove_ticker_from_execution(self, ticker: str) -> bool:
        """Удалить тикер из автоматического исполнения."""
        try:
            ticker = ticker.upper()
            self.enabled_tickers.discard(ticker)
            logger.info(f"Тикер {ticker} удален из автоматического исполнения")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления тикера {ticker}: {e}")
            return False

    def calculate_position_size(self, ticker: str, signal: TradingSignal) -> int:
        """
        Расчет размера позиции на основе сигнала и риск-менеджмента.

        Args:
            ticker: Тикер акции
            signal: Торговый сигнал

        Returns:
            Количество акций для покупки/продажи
        """
        try:
            # Получаем текущую стоимость портфеля
            portfolio_data = self.portfolio_manager.get_portfolio_summary()
            total_value = portfolio_data.get("total_value", 1000000)  # Default 1M

            # Базовый размер позиции
            base_position_pct = 0.02  # 2% базовый размер

            # Корректировка на основе уверенности сигнала
            confidence_multiplier = signal.confidence
            adjusted_position_pct = base_position_pct * confidence_multiplier

            # Ограничение максимальным размером
            final_position_pct = min(adjusted_position_pct, self.max_position_size_pct)

            # Расчет суммы в рублях
            position_value = total_value * final_position_pct

            # Получение текущей цены акции
            from tinkoff_client import TinkoffClient

            tinkoff = TinkoffClient()

            # Поиск инструмента
            instrument = asyncio.run(tinkoff.search_instrument(ticker))
            if not instrument:
                logger.error(f"Инструмент {ticker} не найден")
                return 0

            # Получение цены
            price = asyncio.run(tinkoff.get_last_price(instrument["figi"]))
            if not price or price <= 0:
                logger.error(f"Не удалось получить цену для {ticker}")
                return 0

            # Расчет количества акций
            quantity = int(position_value / price)

            logger.info(
                f"Position sizing для {ticker}: {quantity} акций "
                f"(цена: {price:.2f}₽, размер: {final_position_pct:.1%})"
            )

            return max(1, quantity)  # Минимум 1 акция

        except Exception as e:
            logger.error(f"Ошибка расчета размера позиции для {ticker}: {e}")
            return 0

    async def execute_signal(self, ticker: str, signal: TradingSignal) -> ExecutionRecord:
        """
        Исполнение торгового сигнала.

        Args:
            ticker: Тикер акции
            signal: Торговый сигнал

        Returns:
            Запись об исполнении
        """
        execution_record = ExecutionRecord(signal, ticker)

        try:
            # Проверка режима исполнения
            if self.execution_mode == ExecutionMode.DISABLED:
                execution_record.status = ExecutionStatus.REJECTED
                execution_record.error_message = "Автоматическое исполнение отключено"
                return execution_record

            # Проверка тикера в разрешенных
            if ticker not in self.enabled_tickers:
                execution_record.status = ExecutionStatus.REJECTED
                execution_record.error_message = (
                    f"Тикер {ticker} не включен в автоматическое исполнение"
                )
                return execution_record

            # Проверка минимальной уверенности
            if signal.confidence < self.min_confidence_threshold:
                execution_record.status = ExecutionStatus.REJECTED
                execution_record.error_message = (
                    f"Низкая уверенность сигнала: {signal.confidence:.2f}"
                )
                return execution_record

            # Проверка дневных лимитов
            if not self._check_daily_limits():
                execution_record.status = ExecutionStatus.REJECTED
                execution_record.error_message = "Превышены дневные лимиты"
                return execution_record

            # Расчет размера позиции
            quantity = self.calculate_position_size(ticker, signal)
            if quantity <= 0:
                execution_record.status = ExecutionStatus.REJECTED
                execution_record.error_message = "Не удалось рассчитать размер позиции"
                return execution_record

            execution_record.quantity = quantity

            # Исполнение сделки
            if signal.action.upper() == "BUY":
                result = await self.portfolio_manager.buy_stock(ticker, quantity)
            elif signal.action.upper() == "SELL":
                result = await self.portfolio_manager.sell_stock(ticker, quantity)
            else:
                execution_record.status = ExecutionStatus.REJECTED
                execution_record.error_message = f"Неизвестное действие: {signal.action}"
                return execution_record

            # Обработка результата
            if result.get("success", False):
                execution_record.status = ExecutionStatus.EXECUTED
                execution_record.execution_price = result.get("price")
                execution_record.commission = result.get("commission")
                execution_record.portfolio_impact = result.get("total_cost")

                # Обновление счетчиков
                self.daily_executions += 1

                logger.info(
                    f"Сигнал исполнен: {signal.action} {quantity} {ticker} "
                    f"по цене {execution_record.execution_price:.2f}₽"
                )
            else:
                execution_record.status = ExecutionStatus.FAILED
                execution_record.error_message = result.get("error", "Неизвестная ошибка")

        except Exception as e:
            execution_record.status = ExecutionStatus.FAILED
            execution_record.error_message = str(e)
            logger.error(f"Ошибка исполнения сигнала для {ticker}: {e}")

        # Сохранение в историю
        self.execution_history.append(execution_record)

        return execution_record

    def _check_daily_limits(self) -> bool:
        """Проверка дневных лимитов торговли."""
        try:
            # Сброс счетчика если новый день
            current_date = datetime.now().date()
            if current_date != self.last_reset_date:
                self.daily_executions = 0
                self.last_reset_date = current_date

            # Проверка лимита сделок
            max_daily_trades = PORTFOLIO_CONFIG.get("max_daily_trades", 5)
            if self.daily_executions >= max_daily_trades:
                logger.warning(f"Достигнут дневной лимит сделок: {max_daily_trades}")
                return False

            return True

        except Exception as e:
            logger.error(f"Ошибка проверки дневных лимитов: {e}")
            return False

    def get_execution_status(self) -> Dict:
        """Получение статуса автоматического исполнения."""
        try:
            recent_executions = [
                exec_record.to_dict()
                for exec_record in self.execution_history[-10:]  # Последние 10
            ]

            return {
                "execution_mode": self.execution_mode.value,
                "enabled_tickers": list(self.enabled_tickers),
                "min_confidence_threshold": self.min_confidence_threshold,
                "daily_executions": self.daily_executions,
                "max_daily_trades": PORTFOLIO_CONFIG.get("max_daily_trades", 5),
                "total_executions": len(self.execution_history),
                "recent_executions": recent_executions,
            }

        except Exception as e:
            logger.error(f"Ошибка получения статуса исполнения: {e}")
            return {"error": str(e)}

    async def process_strategy_signals(self, ticker: str) -> List[ExecutionRecord]:
        """
        Обработка сигналов от всех активных стратегий.

        Args:
            ticker: Тикер для получения сигналов

        Returns:
            Список записей об исполнении
        """
        execution_records = []

        try:
            # Получение агрегированных сигналов от Strategy Engine
            signal_data = await self.strategy_engine.execute_strategy_signals(ticker)

            # Извлекаем данные из словаря
            action = signal_data.get("recommendation", "HOLD")
            confidence = signal_data.get("confidence", 0.0)
            signals_count = signal_data.get("signals_count", 0)
            message = signal_data.get("message", "")

            logger.info(
                f"Получен сигнал для {ticker}: {action} "
                f"(уверенность: {confidence:.2f}, сигналов: {signals_count})"
            )

            # Создаем объект TradingSignal из полученных данных
            if action != "HOLD" and confidence > 0:
                trading_signal = TradingSignal(ticker=ticker, action=action, confidence=confidence)

                execution_record = await self.execute_signal(ticker, trading_signal)
                execution_records.append(execution_record)
            else:
                logger.info(
                    f"Сигнал {action} для {ticker} не требует исполнения "
                    f"(уверенность: {confidence:.2f})"
                )

        except Exception as e:
            logger.error(f"Ошибка обработки сигналов для {ticker}: {e}")

        return execution_records


# Глобальный экземпляр Strategy Executor
_global_executor = None


def get_strategy_executor() -> StrategyExecutor:
    """Получение глобального экземпляра Strategy Executor."""
    global _global_executor
    if _global_executor is None:
        _global_executor = StrategyExecutor()
    return _global_executor


def main():
    """Функция для тестирования модуля."""

    async def test_executor():
        print("🧪 Тестирование StrategyExecutor...")

        try:
            # Создание executor
            executor = StrategyExecutor()

            # Включение автоматической торговли
            executor.enable_auto_trading(ExecutionMode.AUTOMATIC)
            executor.add_ticker_for_execution("SBER")
            executor.min_confidence_threshold = 0.6  # Снижаем для тестирования

            print("✅ Настройки:")
            status = executor.get_execution_status()
            print(f"  Режим: {status['execution_mode']}")
            print(f"  Тикеры: {status['enabled_tickers']}")
            print(f"  Мин. уверенность: {status['min_confidence_threshold']}")

            # Тестирование получения сигналов (без исполнения)
            print("\n📊 Тестирование получения сигналов...")
            execution_records = await executor.process_strategy_signals("SBER")

            print(f"✅ Получено записей об исполнении: {len(execution_records)}")
            for record in execution_records:
                print(
                    f"  {record.ticker}: {record.signal.action} " f"(статус: {record.status.value})"
                )
                if record.error_message:
                    print(f"    Ошибка: {record.error_message}")

        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")

    asyncio.run(test_executor())


if __name__ == "__main__":
    main()
