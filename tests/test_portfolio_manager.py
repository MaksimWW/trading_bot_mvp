"""
Тесты для модуля portfolio_manager.

Проверяет основную функциональность управления портфелем,
создание позиций, расчет P&L и валидацию операций.
"""

import os
import sys

import pytest

# Добавляем src в путь для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from portfolio_manager import PortfolioManager, Position, Trade


def test_portfolio_manager_init():
    """Тест инициализации PortfolioManager."""
    portfolio = PortfolioManager(initial_balance=1000000)

    assert portfolio.initial_balance == 1000000
    assert portfolio.cash_balance == 1000000
    assert len(portfolio.positions) == 0
    assert len(portfolio.trades) == 0
    assert portfolio.max_position_size == 0.05
    assert portfolio.default_commission_rate == 0.0005


def test_position_calculations():
    """Тест расчетов в классе Position."""
    position = Position(
        ticker="SBER",
        company_name="ПАО Сбербанк",
        sector="Банки",
        quantity=100,
        avg_price=300.0,
        current_price=315.0,
        purchase_date="2025-06-28",
        last_update="2025-06-28",
    )

    assert position.total_value == 31500.0  # 100 * 315
    assert position.cost_basis == 30000.0  # 100 * 300
    assert position.unrealized_pnl == 1500.0  # 31500 - 30000
    assert position.unrealized_pnl_percent == 5.0  # (1500 / 30000) * 100


def test_trade_calculations():
    """Тест расчетов в классе Trade."""
    buy_trade = Trade(
        trade_id="BUY_SBER_001",
        ticker="SBER",
        action="BUY",
        quantity=100,
        price=300.0,
        timestamp="2025-06-28T10:00:00",
        commission=15.0,
    )

    sell_trade = Trade(
        trade_id="SELL_SBER_001",
        ticker="SBER",
        action="SELL",
        quantity=50,
        price=310.0,
        timestamp="2025-06-28T11:00:00",
        commission=7.75,
    )

    assert buy_trade.total_amount == 30015.0  # 30000 + 15
    assert sell_trade.total_amount == 15492.25  # 15500 - 7.75


def test_purchase_validation():
    """Тест валидации покупок."""
    portfolio = PortfolioManager(initial_balance=100000)

    # Тест превышения баланса
    result = portfolio._validate_purchase("SBER", 1000, 200.0, 200000.0)
    assert not result["valid"]
    assert "Недостаточно средств" in result["reason"]

    # Тест превышения максимального размера позиции
    result = portfolio._validate_purchase("SBER", 300, 200.0, 60000.0)  # 60k > 5k (5% от 100k)
    assert not result["valid"]
    assert "максимальный размер позиции" in result["reason"]

    # Тест валидной покупки (4000 < 5000 лимит)
    result = portfolio._validate_purchase("SBER", 20, 200.0, 4000.0)
    assert result["valid"]
    assert result["reason"] == "OK"


def test_portfolio_summary():
    """Тест создания сводки портфеля."""
    portfolio = PortfolioManager(initial_balance=1000000)

    # Создаем тестовую позицию
    portfolio.positions["SBER"] = Position(
        ticker="SBER",
        company_name="ПАО Сбербанк",
        sector="Банки",
        quantity=100,
        avg_price=300.0,
        current_price=315.0,
        purchase_date="2025-06-28",
        last_update="2025-06-28",
    )

    # Эмулируем потраченные средства
    portfolio.cash_balance = 970000  # Потратили 30000 на покупку

    summary = portfolio.get_portfolio_summary()

    assert summary["cash_balance"] == 970000
    assert summary["positions_count"] == 1
    assert len(summary["positions"]) == 1
    assert summary["positions"][0]["ticker"] == "SBER"
    assert summary["sector_allocation"]["Банки"] > 0


def test_sector_allocation():
    """Тест расчета секторного распределения."""
    portfolio = PortfolioManager(initial_balance=1000000)

    positions_data = [
        {"sector": "Банки", "weight_percent": 50.0},
        {"sector": "IT", "weight_percent": 30.0},
        {"sector": "Энергетика", "weight_percent": 20.0},
    ]

    sectors = portfolio._calculate_sector_allocation(positions_data, 1000000)

    assert sectors["Банки"] == 50.0
    assert sectors["IT"] == 30.0
    assert sectors["Энергетика"] == 20.0


def test_trades_statistics():
    """Тест расчета статистики сделок."""
    portfolio = PortfolioManager(initial_balance=1000000)

    # Добавляем тестовые сделки
    portfolio.trades = [
        Trade("BUY_001", "SBER", "BUY", 100, 300.0, "2025-06-28", 15.0),
        Trade("SELL_001", "SBER", "SELL", 50, 310.0, "2025-06-28", 7.75),
        Trade("BUY_002", "GAZP", "BUY", 200, 150.0, "2025-06-28", 15.0),
    ]

    stats = portfolio._calculate_trades_statistics()

    assert stats["total_trades"] == 3
    assert stats["buy_trades"] == 2
    assert stats["sell_trades"] == 1
    assert stats["total_commission"] == 37.75
    assert stats["total_volume"] == 75500.0  # 30000 + 15500 + 30000


def test_module_structure():
    """Тест структуры модуля."""
    import portfolio_manager

    # Проверяем наличие основных классов
    assert hasattr(portfolio_manager, "PortfolioManager")
    assert hasattr(portfolio_manager, "Position")
    assert hasattr(portfolio_manager, "Trade")
    assert hasattr(portfolio_manager, "get_portfolio_manager")

    # Проверяем что функции вызываются
    assert callable(portfolio_manager.get_portfolio_manager)


def test_edge_cases():
    """Тест граничных случаев."""
    # Позиция с нулевой стоимостью
    position = Position("TEST", "Test", "Test", 0, 0, 0, "2025-06-28", "2025-06-28")
    assert position.unrealized_pnl_percent == 0.0

    # Портфель без сделок
    portfolio = PortfolioManager(initial_balance=1000000)
    stats = portfolio._calculate_trades_statistics()
    assert stats["total_trades"] == 0
    assert stats["avg_trade_size"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__])
