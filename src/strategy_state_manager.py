"""
Strategy State Manager - управление состоянием стратегий между процессами.

Этот модуль обеспечивает сохранение и восстановление состояния стратегий
между различными процессами и перезапусками бота.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class StrategyStateManager:
    """Менеджер состояния стратегий для persistence между процессами."""

    def __init__(self, state_file: str = "strategy_state.json"):
        """
        Инициализация менеджера состояния.

        Args:
            state_file: Путь к файлу состояния
        """
        self.state_file = Path(state_file)
        self.state = self._load_state()
        logger.info("Strategy State Manager инициализирован")

    def _load_state(self) -> Dict:
        """Загрузить состояние из файла."""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                logger.info(f"Состояние загружено из {self.state_file}")
                return state
            else:
                logger.info("strategy_state.json не найден, создаем новое состояние")
                return self._create_empty_state()
        except Exception as e:
            logger.error(f"Ошибка загрузки состояния: {e}")
            return self._create_empty_state()

    def _create_empty_state(self) -> Dict:
        """Создать пустое состояние."""
        return {"strategies": {}, "last_updated": datetime.now().isoformat(), "version": "1.0"}

    def _save_state(self):
        """Сохранить состояние в файл."""
        try:
            self.state["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            logger.info("Состояние стратегий сохранено")
        except Exception as e:
            logger.error("Ошибка сохранения состояния")

    def start_strategy(self, strategy_id: str, tickers: List[str]):
        """
        Запустить стратегию для указанных тикеров.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров
        """
        if strategy_id not in self.state["strategies"]:
            self.state["strategies"][strategy_id] = {
                "active_tickers": [],
                "started_at": datetime.now().isoformat(),
                "status": "active",
            }

        # Добавляем новые тикеры
        current_tickers = set(self.state["strategies"][strategy_id]["active_tickers"])
        current_tickers.update(tickers)
        self.state["strategies"][strategy_id]["active_tickers"] = list(current_tickers)
        self.state["strategies"][strategy_id]["last_updated"] = datetime.now().isoformat()

        self._save_state()
        logger.info(f"Стратегия {strategy_id} запущена для {tickers}")

    def stop_strategy(self, strategy_id: str, tickers: List[str] = None):
        """
        Остановить стратегию для указанных тикеров или полностью.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров для остановки (None = все)
        """
        if strategy_id not in self.state["strategies"]:
            logger.warning(f"Стратегия {strategy_id} не найдена")
            return

        if tickers is None:
            # Остановить полностью
            self.state["strategies"][strategy_id]["active_tickers"] = []
            self.state["strategies"][strategy_id]["status"] = "stopped"
        else:
            # Остановить для конкретных тикеров
            current_tickers = set(self.state["strategies"][strategy_id]["active_tickers"])
            current_tickers.difference_update(tickers)
            self.state["strategies"][strategy_id]["active_tickers"] = list(current_tickers)

        self.state["strategies"][strategy_id]["last_updated"] = datetime.now().isoformat()
        self._save_state()
        logger.info(f"Стратегия {strategy_id} остановлена для {tickers or 'всех тикеров'}")

    def get_active_tickers(self, strategy_id: str) -> List[str]:
        """
        Получить активные тикеры для стратегии.

        Args:
            strategy_id: Идентификатор стратегии

        Returns:
            Список активных тикеров
        """
        if strategy_id not in self.state["strategies"]:
            return []

        return self.state["strategies"][strategy_id].get("active_tickers", [])

    def get_all_active_strategies(self) -> Dict[str, List[str]]:
        """
        Получить все активные стратегии и их тикеры.

        Returns:
            Словарь {strategy_id: [tickers]}
        """
        active_strategies = {}

        for strategy_id, strategy_data in self.state["strategies"].items():
            if strategy_data.get("status") != "stopped":
                active_tickers = strategy_data.get("active_tickers", [])
                if active_tickers:
                    active_strategies[strategy_id] = active_tickers

        return active_strategies

    def is_strategy_active(self, strategy_id: str, ticker: str = None) -> bool:
        """
        Проверить активна ли стратегия.

        Args:
            strategy_id: Идентификатор стратегии
            ticker: Конкретный тикер (опционально)

        Returns:
            True если стратегия активна
        """
        if strategy_id not in self.state["strategies"]:
            return False

        strategy_data = self.state["strategies"][strategy_id]
        if strategy_data.get("status") == "stopped":
            return False

        active_tickers = strategy_data.get("active_tickers", [])

        if ticker is None:
            return len(active_tickers) > 0
        else:
            return ticker in active_tickers

    def get_state_summary(self) -> Dict:
        """Получить сводку текущего состояния."""
        total_strategies = len(self.state["strategies"])
        active_strategies = len(
            [
                s
                for s in self.state["strategies"].values()
                if s.get("status") != "stopped" and s.get("active_tickers")
            ]
        )

        all_tickers = set()
        for strategy_data in self.state["strategies"].values():
            if strategy_data.get("status") != "stopped":
                all_tickers.update(strategy_data.get("active_tickers", []))

        return {
            "total_strategies": total_strategies,
            "active_strategies": active_strategies,
            "unique_tickers": len(all_tickers),
            "last_updated": self.state.get("last_updated"),
            "strategies": {
                strategy_id: {
                    "tickers_count": len(data.get("active_tickers", [])),
                    "status": data.get("status", "unknown"),
                    "tickers": data.get("active_tickers", []),
                }
                for strategy_id, data in self.state["strategies"].items()
            },
        }

    def clear_all_strategies(self):
        """Очистить все стратегии (для отладки)."""
        self.state["strategies"] = {}
        self._save_state()
        logger.info("Все стратегии очищены")


# Глобальный экземпляр
_global_state_manager = None


def get_strategy_state_manager() -> StrategyStateManager:
    """Получить глобальный экземпляр State Manager."""
    global _global_state_manager
    if _global_state_manager is None:
        _global_state_manager = StrategyStateManager()
    return _global_state_manager


def main():
    """Функция для тестирования модуля."""
    print("🧪 Тестирование Strategy State Manager...")

    try:
        manager = get_strategy_state_manager()
        print(f"✅ State Manager инициализирован")

        # Получаем сводку
        summary = manager.get_state_summary()
        print(f"📊 Текущее состояние:")
        print(f"   - Всего стратегий: {summary['total_strategies']}")
        print(f"   - Активных: {summary['active_strategies']}")
        print(f"   - Уникальных тикеров: {summary['unique_tickers']}")

        if summary["strategies"]:
            print(f"📋 Детали стратегий:")
            for strategy_id, data in summary["strategies"].items():
                print(f"   - {strategy_id}: {data['tickers_count']} тикеров ({data['status']})")
                if data["tickers"]:
                    print(f"     Тикеры: {', '.join(data['tickers'])}")

        print("🎯 Strategy State Manager готов к использованию!")

    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")


if __name__ == "__main__":
    main()

"""Portfolio Coordinator - координирует запуск и остановку стратегий."""

import asyncio
import logging
from typing import Dict, List

from src.strategy_state_manager import get_strategy_state_manager

logger = logging.getLogger(__name__)


class PortfolioCoordinator:
    """
    Координатор портфеля.

    Отвечает за запуск и остановку стратегий на основе внешних сигналов.
    """

    def __init__(self):
        """Инициализация координатора."""
        self.strategy_state_manager = get_strategy_state_manager()
        self.is_running = False
        logger.info("Portfolio Coordinator инициализирован")

    async def start(self):
        """Запуск координатора."""
        if self.is_running:
            logger.info("Portfolio Coordinator уже включен")
            return

        self.is_running = True
        logger.info("Portfolio Coordinator запущен")

    async def stop(self):
        """Остановка координатора."""
        if not self.is_running:
            logger.info("Синхронизация отключена")
            return

        self.is_running = False
        logger.info("Portfolio Coordinator остановлен")

    def start_strategy(self, strategy_id: str, tickers: List[str]):
        """
        Запустить стратегию для указанных тикеров.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров
        """
        self.strategy_state_manager.start_strategy(strategy_id, tickers)
        logger.info(f"Запущена стратегия {strategy_id} для тикеров: {tickers}")

    def stop_strategy(self, strategy_id: str, tickers: List[str] = None):
        """
        Остановить стратегию для указанных тикеров.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров (если None - остановить все)
        """
        self.strategy_state_manager.stop_strategy(strategy_id, tickers)
        if tickers:
            logger.info(f"Остановлена стратегия {strategy_id} для тикеров: {tickers}")
        else:
            logger.info(f"Остановлена стратегия {strategy_id} для всех тикеров")

    def get_active_strategies(self) -> Dict[str, List[str]]:
        """
        Получить все активные стратегии и их тикеры.

        Returns:
            Словарь, где ключ - strategy_id, значение - список тикеров
        """
        return self.strategy_state_manager.get_all_active_strategies()

    def is_strategy_active(self, strategy_id: str, ticker: str = None) -> bool:
        """
        Проверить, активна ли стратегия для указанного тикера.

        Args:
            strategy_id: Идентификатор стратегии
            ticker: Тикер (если None - проверить общую активность стратегии)

        Returns:
            True, если стратегия активна для тикера (или в общем, если ticker=None)
        """
        return self.strategy_state_manager.is_strategy_active(strategy_id, ticker)

    def get_strategy_state_summary(self) -> Dict:
        """Получить сводку состояния стратегий."""
        return self.strategy_state_manager.get_state_summary()


# Singleton instance
_portfolio_coordinator = None


def get_portfolio_coordinator() -> PortfolioCoordinator:
    """Получить экземпляр Portfolio Coordinator (Singleton)."""
    global _portfolio_coordinator
    if _portfolio_coordinator is None:
        _portfolio_coordinator = PortfolioCoordinator()
    return _portfolio_coordinator


async def main():
    """Тестирование Portfolio Coordinator."""
    logging.basicConfig(level=logging.INFO)  # Настройка логирования

    coordinator = get_portfolio_coordinator()
    await coordinator.start()

    # Эмуляция запуска и остановки стратегий
    coordinator.start_strategy("strategy_1", ["AAPL", "MSFT"])
    coordinator.start_strategy("strategy_2", ["GOOGL"])

    print("Активные стратегии:", coordinator.get_active_strategies())

    await asyncio.sleep(5)  # Пауза

    coordinator.stop_strategy("strategy_1", ["AAPL"])
    print("Активные стратегии после остановки:", coordinator.get_active_strategies())

    await coordinator.stop()


if __name__ == "__main__":
    asyncio.run(main())

"""Portfolio Coordinator - координирует запуск и остановку стратегий."""

import asyncio
import logging
from typing import Dict, List

from src.strategy_state_manager import get_strategy_state_manager

logger = logging.getLogger(__name__)


class PortfolioCoordinator:
    """
    Координатор портфеля.

    Отвечает за запуск и остановку стратегий на основе внешних сигналов.
    """

    def __init__(self):
        """Инициализация координатора."""
        self.strategy_state_manager = get_strategy_state_manager()
        self.is_running = False
        logger.info("Portfolio Coordinator инициализирован")

    async def start(self):
        """Запуск координатора."""
        if self.is_running:
            logger.info("Portfolio Coordinator уже включен")
            return

        self.is_running = True
        logger.info("Portfolio Coordinator запущен")

    async def stop(self):
        """Остановка координатора."""
        if not self.is_running:
            logger.info("Синхронизация отключена")
            return

        self.is_running = False
        logger.info("Portfolio Coordinator остановлен")

    def start_strategy(self, strategy_id: str, tickers: List[str]):
        """
        Запустить стратегию для указанных тикеров.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров
        """
        self.strategy_state_manager.start_strategy(strategy_id, tickers)
        logger.info(f"Запущена стратегия {strategy_id} для тикеров: {tickers}")

    def stop_strategy(self, strategy_id: str, tickers: List[str] = None):
        """
        Остановить стратегию для указанных тикеров.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров (если None - остановить все)
        """
        self.strategy_state_manager.stop_strategy(strategy_id, tickers)
        if tickers:
            logger.info(f"Остановлена стратегия {strategy_id} для тикеров: {tickers}")
        else:
            logger.info(f"Остановлена стратегия {strategy_id} для всех тикеров")

    def get_active_strategies(self) -> Dict[str, List[str]]:
        """
        Получить все активные стратегии и их тикеры.

        Returns:
            Словарь, где ключ - strategy_id, значение - список тикеров
        """
        return self.strategy_state_manager.get_all_active_strategies()

    def is_strategy_active(self, strategy_id: str, ticker: str = None) -> bool:
        """
        Проверить, активна ли стратегия для указанного тикера.

        Args:
            strategy_id: Идентификатор стратегии
            ticker: Тикер (если None - проверить общую активность стратегии)

        Returns:
            True, если стратегия активна для тикера (или в общем, если ticker=None)
        """
        return self.strategy_state_manager.is_strategy_active(strategy_id, ticker)

    def get_strategy_state_summary(self) -> Dict:
        """Получить сводку состояния стратегий."""
        return self.strategy_state_manager.get_state_summary()


# Singleton instance
_portfolio_coordinator = None


def get_portfolio_coordinator() -> PortfolioCoordinator:
    """Получить экземпляр Portfolio Coordinator (Singleton)."""
    global _portfolio_coordinator
    if _portfolio_coordinator is None:
        _portfolio_coordinator = PortfolioCoordinator()
    return _portfolio_coordinator


async def main():
    """Тестирование Portfolio Coordinator."""
    logging.basicConfig(level=logging.INFO)  # Настройка логирования

    coordinator = get_portfolio_coordinator()
    await coordinator.start()

    # Эмуляция запуска и остановки стратегий
    coordinator.start_strategy("strategy_1", ["AAPL", "MSFT"])
    coordinator.start_strategy("strategy_2", ["GOOGL"])

    print("Активные стратегии:", coordinator.get_active_strategies())

    await asyncio.sleep(5)  # Пауза

    coordinator.stop_strategy("strategy_1", ["AAPL"])
    print("Активные стратегии после остановки:", coordinator.get_active_strategies())

    await coordinator.stop()


if __name__ == "__main__":
    asyncio.run(main())

"""Portfolio Coordinator - координирует запуск и остановку стратегий."""

import asyncio
import logging
from typing import Dict, List

from src.strategy_state_manager import get_strategy_state_manager

logger = logging.getLogger(__name__)


class PortfolioCoordinator:
    """
    Координатор портфеля.

    Отвечает за запуск и остановку стратегий на основе внешних сигналов.
    """

    def __init__(self):
        """Инициализация координатора."""
        self.strategy_state_manager = get_strategy_state_manager()
        self.is_running = False
        logger.info("Portfolio Coordinator инициализирован")

    async def start(self):
        """Запуск координатора."""
        if self.is_running:
            logger.info("Portfolio Coordinator уже включен")
            return

        self.is_running = True
        logger.info("Portfolio Coordinator запущен")

    async def stop(self):
        """Остановка координатора."""
        if not self.is_running:
            logger.info("Синхронизация отключена")
            return

        self.is_running = False
        logger.info("Portfolio Coordinator остановлен")

    def start_strategy(self, strategy_id: str, tickers: List[str]):
        """
        Запустить стратегию для указанных тикеров.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров
        """
        self.strategy_state_manager.start_strategy(strategy_id, tickers)
        logger.info(f"Запущена стратегия {strategy_id} для тикеров: {tickers}")

    def stop_strategy(self, strategy_id: str, tickers: List[str] = None):
        """
        Остановить стратегию для указанных тикеров.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров (если None - остановить все)
        """
        self.strategy_state_manager.stop_strategy(strategy_id, tickers)
        if tickers:
            logger.info(f"Остановлена стратегия {strategy_id} для тикеров: {tickers}")
        else:
            logger.info(f"Остановлена стратегия {strategy_id} для всех тикеров")

    def get_active_strategies(self) -> Dict[str, List[str]]:
        """
        Получить все активные стратегии и их тикеры.

        Returns:
            Словарь, где ключ - strategy_id, значение - список тикеров
        """
        return self.strategy_state_manager.get_all_active_strategies()

    def is_strategy_active(self, strategy_id: str, ticker: str = None) -> bool:
        """
        Проверить, активна ли стратегия для указанного тикера.

        Args:
            strategy_id: Идентификатор стратегии
            ticker: Тикер (если None - проверить общую активность стратегии)

        Returns:
            True, если стратегия активна для тикера (или в общем, если ticker=None)
        """
        return self.strategy_state_manager.is_strategy_active(strategy_id, ticker)

    def get_strategy_state_summary(self) -> Dict:
        """Получить сводку состояния стратегий."""
        return self.strategy_state_manager.get_state_summary()


# Singleton instance
_portfolio_coordinator = None


def get_portfolio_coordinator() -> PortfolioCoordinator:
    """Получить экземпляр Portfolio Coordinator (Singleton)."""
    global _portfolio_coordinator
    if _portfolio_coordinator is None:
        _portfolio_coordinator = PortfolioCoordinator()
    return _portfolio_coordinator


async def main():
    """Тестирование Portfolio Coordinator."""
    logging.basicConfig(level=logging.INFO)  # Настройка логирования

    coordinator = get_portfolio_coordinator()
    await coordinator.start()

    # Эмуляция запуска и остановки стратегий
    coordinator.start_strategy("strategy_1", ["AAPL", "MSFT"])
    coordinator.start_strategy("strategy_2", ["GOOGL"])

    print("Активные стратегии:", coordinator.get_active_strategies())

    await asyncio.sleep(5)  # Пауза

    coordinator.stop_strategy("strategy_1", ["AAPL"])
    print("Активные стратегии после остановки:", coordinator.get_active_strategies())

    await coordinator.stop()


if __name__ == "__main__":
    asyncio.run(main())

"""Portfolio Coordinator - координирует запуск и остановку стратегий."""

import asyncio
import logging
from typing import Dict, List

from src.strategy_state_manager import get_strategy_state_manager

logger = logging.getLogger(__name__)


class PortfolioCoordinator:
    """
    Координатор портфеля.

    Отвечает за запуск и остановку стратегий на основе внешних сигналов.
    """

    def __init__(self):
        """Инициализация координатора."""
        self.strategy_state_manager = get_strategy_state_manager()
        self.is_running = False
        logger.info("Portfolio Coordinator инициализирован")

    async def start(self):
        """Запуск координатора."""
        if self.is_running:
            logger.info("Portfolio Coordinator уже включен")
            return

        self.is_running = True
        logger.info("Portfolio Coordinator запущен")

    async def stop(self):
        """Остановка координатора."""
        if not self.is_running:
            logger.info("Синхронизация отключена")
            return

        self.is_running = False
        logger.info("Portfolio Coordinator остановлен")

    def start_strategy(self, strategy_id: str, tickers: List[str]):
        """
        Запустить стратегию для указанных тикеров.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров
        """
        self.strategy_state_manager.start_strategy(strategy_id, tickers)
        logger.info(f"Запущена стратегия {strategy_id} для тикеров: {tickers}")

    def stop_strategy(self, strategy_id: str, tickers: List[str] = None):
        """
        Остановить стратегию для указанных тикеров.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров (если None - остановить все)
        """
        self.strategy_state_manager.stop_strategy(strategy_id, tickers)
        if tickers:
            logger.info(f"Остановлена стратегия {strategy_id} для тикеров: {tickers}")
        else:
            logger.info(f"Остановлена стратегия {strategy_id} для всех тикеров")

    def get_active_strategies(self) -> Dict[str, List[str]]:
        """
        Получить все активные стратегии и их тикеры.

        Returns:
            Словарь, где ключ - strategy_id, значение - список тикеров
        """
        return self.strategy_state_manager.get_all_active_strategies()

    def is_strategy_active(self, strategy_id: str, ticker: str = None) -> bool:
        """
        Проверить, активна ли стратегия для указанного тикера.

        Args:
            strategy_id: Идентификатор стратегии
            ticker: Тикер (если None - проверить общую активность стратегии)

        Returns:
            True, если стратегия активна для тикера (или в общем, если ticker=None)
        """
        return self.strategy_state_manager.is_strategy_active(strategy_id, ticker)

    def get_strategy_state_summary(self) -> Dict:
        """Получить сводку состояния стратегий."""
        return self.strategy_state_manager.get_state_summary()


# Singleton instance
_portfolio_coordinator = None


def get_portfolio_coordinator() -> PortfolioCoordinator:
    """Получить экземпляр Portfolio Coordinator (Singleton)."""
    global _portfolio_coordinator
    if _portfolio_coordinator is None:
        _portfolio_coordinator = PortfolioCoordinator()
    return _portfolio_coordinator


async def main():
    """Тестирование Portfolio Coordinator."""
    logging.basicConfig(level=logging.INFO)  # Настройка логирования

    coordinator = get_portfolio_coordinator()
    await coordinator.start()

    # Эмуляция запуска и остановки стратегий
    coordinator.start_strategy("strategy_1", ["AAPL", "MSFT"])
    coordinator.start_strategy("strategy_2", ["GOOGL"])

    print("Активные стратегии:", coordinator.get_active_strategies())

    await asyncio.sleep(5)  # Пауза

    coordinator.stop_strategy("strategy_1", ["AAPL"])
    print("Активные стратегии после остановки:", coordinator.get_active_strategies())

    await coordinator.stop()


if __name__ == "__main__":
    asyncio.run(main())

"""Portfolio Coordinator - координирует запуск и остановку стратегий."""

import asyncio
import logging
from typing import Dict, List

from src.strategy_state_manager import get_strategy_state_manager

logger = logging.getLogger(__name__)


class PortfolioCoordinator:
    """
    Координатор портфеля.

    Отвечает за запуск и остановку стратегий на основе внешних сигналов.
    """

    def __init__(self):
        """Инициализация координатора."""
        self.strategy_state_manager = get_strategy_state_manager()
        self.is_running = False
        logger.info("Portfolio Coordinator инициализирован")

    async def start(self):
        """Запуск координатора."""
        if self.is_running:
            logger.info("Portfolio Coordinator уже включен")
            return

        self.is_running = True
        logger.info("Portfolio Coordinator запущен")

    async def stop(self):
        """Остановка координатора."""
        if not self.is_running:
            logger.info("Синхронизация отключена")
            return

        self.is_running = False
        logger.info("Portfolio Coordinator остановлен")

    def start_strategy(self, strategy_id: str, tickers: List[str]):
        """
        Запустить стратегию для указанных тикеров.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров
        """
        self.strategy_state_manager.start_strategy(strategy_id, tickers)
        logger.info(f"Запущена стратегия {strategy_id} для тикеров: {tickers}")

    def stop_strategy(self, strategy_id: str, tickers: List[str] = None):
        """
        Остановить стратегию для указанных тикеров.

        Args:
            strategy_id: Идентификатор стратегии
            tickers: Список тикеров (если None - остановить все)
        """
        self.strategy_state_manager.stop_strategy(strategy_id, tickers)
        if tickers:
            logger.info(f"Остановлена стратегия {strategy_id} для тикеров: {tickers}")
        else:
            logger.info(f"Остановлена стратегия {strategy_id} для всех тикеров")

    def get_active_strategies(self) -> Dict[str, List[str]]:
        """
        Получить все активные стратегии и их тикеры.

        Returns:
            Словарь, где ключ - strategy_id, значение - список тикеров
        """
        return self.strategy_state_manager.get_all_active_strategies()

    def is_strategy_active(self, strategy_id: str, ticker: str = None) -> bool:
        """
        Проверить, активна ли стратегия для указанного тикера.

        Args:
            strategy_id: Идентификатор стратегии
            ticker: Тикер (если None - проверить общую активность стратегии)

        Returns:
            True, если стратегия активна для тикера (или в общем, если ticker=None)
        """
        return self.strategy_state_manager.is_strategy_active(strategy_id, ticker)

    def get_strategy_state_summary(self) -> Dict:
        """Получить сводку состояния стратегий."""
        return self.strategy_state_manager.get_state_summary()


# Singleton instance
_portfolio_coordinator = None


def get_portfolio_coordinator() -> PortfolioCoordinator:
    """Получить экземпляр Portfolio Coordinator (Singleton)."""
    global _portfolio_coordinator
    if _portfolio_coordinator is None:
        _portfolio_coordinator = PortfolioCoordinator()
    return _portfolio_coordinator


async def main():
    """Тестирование Portfolio Coordinator."""
    logging.basicConfig(level=logging.INFO)  # Настройка логирования

    coordinator = get_portfolio_coordinator()
    await coordinator.start()

    # Эмуляция запуска и остановки стратегий
    coordinator.start_strategy("strategy_1", ["AAPL", "MSFT"])
    coordinator.start_strategy("strategy_2", ["GOOGL"])

    print("Активные стратегии:", coordinator.get_active_strategies())

    await asyncio.sleep(5)  # Пауза

    coordinator.stop_strategy("strategy_1", ["AAPL"])
    print("Активные стратегии после остановки:", coordinator.get_active_strategies())

    await coordinator.stop()


if __name__ == "__main__":
    asyncio.run(main())