
"""
Portfolio Manager для торгового бота.

Этот модуль предоставляет функциональность для управления виртуальным портфелем,
отслеживания позиций, расчета P&L и оценки рисков.
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from config import PORTFOLIO_CONFIG
from tinkoff_client import TinkoffClient


logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Класс для представления торговой позиции."""
    ticker: str
    company_name: str
    sector: str
    quantity: int
    avg_price: float
    current_price: float
    purchase_date: str
    last_update: str
    
    @property
    def total_value(self) -> float:
        """Общая стоимость позиции по текущей цене."""
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> float:
        """Общая стоимость покупки позиции."""
        return self.quantity * self.avg_price
    
    @property
    def unrealized_pnl(self) -> float:
        """Нереализованная прибыль/убыток."""
        return self.total_value - self.cost_basis
    
    @property
    def unrealized_pnl_percent(self) -> float:
        """Нереализованная прибыль/убыток в процентах."""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100


@dataclass
class Trade:
    """Класс для представления торговой сделки."""
    trade_id: str
    ticker: str
    action: str  # "BUY" или "SELL"
    quantity: int
    price: float
    timestamp: str
    commission: float = 0.0
    
    @property
    def total_amount(self) -> float:
        """Общая сумма сделки включая комиссию."""
        base_amount = self.quantity * self.price
        if self.action == "BUY":
            return base_amount + self.commission
        else:
            return base_amount - self.commission


class PortfolioManager:
    """Менеджер виртуального торгового портфеля."""
    
    def __init__(self, initial_balance: float = None):
        """
        Инициализация портфеля.
        
        Args:
            initial_balance: Начальный баланс портфеля
        """
        self.initial_balance = initial_balance or PORTFOLIO_CONFIG["initial_balance"]
        self.cash_balance = self.initial_balance
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.creation_date = datetime.now().isoformat()
        
        # Интеграция с Tinkoff для получения цен
        self.tinkoff = TinkoffClient()
        
        # Настройки портфеля
        self.max_position_size = PORTFOLIO_CONFIG["max_position_size"]
        self.max_daily_loss = PORTFOLIO_CONFIG["max_daily_loss"]
        self.max_daily_trades = PORTFOLIO_CONFIG["max_daily_trades"]
        self.default_commission_rate = PORTFOLIO_CONFIG["commission_rate"]
        
        logger.info(f"PortfolioManager инициализирован с балансом {self.initial_balance:,.0f} ₽")
    
    async def buy_stock(self, ticker: str, quantity: int, 
                       price: Optional[float] = None) -> Dict:
        """
        Виртуальная покупка акций.
        
        Args:
            ticker: Тикер акции
            quantity: Количество акций
            price: Цена покупки (если None, используется текущая рыночная цена)
            
        Returns:
            Результат операции покупки
        """
        try:
            # Получаем текущую цену если не указана
            if price is None:
                instrument = await self.tinkoff.search_instrument(ticker)
                if not instrument:
                    return {"success": False, "error": f"Инструмент {ticker} не найден"}
                
                price = await self.tinkoff.get_last_price(instrument["figi"])
                if not price:
                    return {"success": False, "error": f"Не удалось получить цену {ticker}"}
            
            # Расчет комиссии и общей суммы
            commission = quantity * price * self.default_commission_rate
            total_cost = quantity * price + commission
            
            # Проверки перед покупкой
            validation_result = self._validate_purchase(ticker, quantity, price, total_cost)
            if not validation_result["valid"]:
                return {"success": False, "error": validation_result["reason"]}
            
            # Выполнение покупки
            trade_id = f"BUY_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            trade = Trade(
                trade_id=trade_id,
                ticker=ticker,
                action="BUY",
                quantity=quantity,
                price=price,
                timestamp=datetime.now().isoformat(),
                commission=commission
            )
            
            # Обновление баланса
            self.cash_balance -= total_cost
            
            # Обновление или создание позиции
            await self._update_position_after_buy(ticker, quantity, price)
            
            # Запись сделки
            self.trades.append(trade)
            
            logger.info(f"Покупка выполнена: {quantity} {ticker} по {price:.2f} ₽")
            
            return {
                "success": True,
                "trade_id": trade_id,
                "ticker": ticker,
                "action": "BUY",
                "quantity": quantity,
                "price": price,
                "commission": commission,
                "total_cost": total_cost,
                "new_cash_balance": self.cash_balance
            }
            
        except Exception as e:
            logger.error(f"Ошибка при покупке {ticker}: {e}")
            return {"success": False, "error": f"Ошибка покупки: {str(e)}"}
    
    def get_portfolio_summary(self) -> Dict:
        """
        Получение сводки по портфелю.
        
        Returns:
            Подробная информация о портфеле
        """
        try:
            # Базовая информация
            total_portfolio_value = self.cash_balance
            total_cost_basis = 0
            positions_data = []
            
            # Расчет данных по позициям
            for ticker, position in self.positions.items():
                total_portfolio_value += position.total_value
                total_cost_basis += position.cost_basis
                
                positions_data.append({
                    "ticker": ticker,
                    "company_name": position.company_name,
                    "sector": position.sector,
                    "quantity": position.quantity,
                    "avg_price": position.avg_price,
                    "current_price": position.current_price,
                    "total_value": position.total_value,
                    "unrealized_pnl": position.unrealized_pnl,
                    "unrealized_pnl_percent": position.unrealized_pnl_percent,
                    "weight_percent": (position.total_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
                })
            
            # Сортировка позиций по весу (убывание)
            positions_data.sort(key=lambda x: x["weight_percent"], reverse=True)
            
            # Общая прибыль/убыток
            total_unrealized_pnl = total_portfolio_value - self.initial_balance
            total_unrealized_pnl_percent = (total_unrealized_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0
            
            # Диверсификация по секторам
            sector_allocation = self._calculate_sector_allocation(positions_data, total_portfolio_value)
            
            # Статистика сделок
            trades_stats = self._calculate_trades_statistics()
            
            return {
                "portfolio_value": total_portfolio_value,
                "cash_balance": self.cash_balance,
                "invested_amount": total_cost_basis,
                "unrealized_pnl": total_unrealized_pnl,
                "unrealized_pnl_percent": total_unrealized_pnl_percent,
                "positions_count": len(self.positions),
                "positions": positions_data,
                "sector_allocation": sector_allocation,
                "trades_statistics": trades_stats,
                "creation_date": self.creation_date,
                "last_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания сводки портфеля: {e}")
            return {"error": str(e)}
    
    def _validate_purchase(self, ticker: str, quantity: int, 
                          price: float, total_cost: float) -> Dict:
        """Валидация покупки по лимитам риск-менеджмента."""
        # Проверка доступного баланса
        if total_cost > self.cash_balance:
            return {
                "valid": False,
                "reason": f"Недостаточно средств: нужно {total_cost:,.0f} ₽, доступно {self.cash_balance:,.0f} ₽"
            }
        
        # Проверка максимального размера позиции
        max_position_value = self.initial_balance * self.max_position_size
        if total_cost > max_position_value:
            return {
                "valid": False,
                "reason": f"Превышен максимальный размер позиции: {total_cost:,.0f} ₽ > {max_position_value:,.0f} ₽"
            }
        
        # Проверка дневного лимита сделок
        today_trades = len([t for t in self.trades if t.timestamp.startswith(datetime.now().strftime('%Y-%m-%d'))])
        if today_trades >= self.max_daily_trades:
            return {
                "valid": False,
                "reason": f"Превышен дневной лимит сделок: {today_trades}/{self.max_daily_trades}"
            }
        
        return {"valid": True, "reason": "OK"}
    
    async def _update_position_after_buy(self, ticker: str, quantity: int, price: float):
        """Обновление позиции после покупки."""
        from config import get_ticker_info
        
        if ticker in self.positions:
            # Обновляем существующую позицию
            position = self.positions[ticker]
            total_quantity = position.quantity + quantity
            total_cost = position.cost_basis + (quantity * price)
            new_avg_price = total_cost / total_quantity
            
            position.quantity = total_quantity
            position.avg_price = new_avg_price
            position.current_price = price
            position.last_update = datetime.now().isoformat()
        else:
            # Создаем новую позицию
            ticker_info = get_ticker_info(ticker)
            self.positions[ticker] = Position(
                ticker=ticker,
                company_name=ticker_info.get("name", f"Акция {ticker}"),
                sector=ticker_info.get("sector", "Неизвестный"),
                quantity=quantity,
                avg_price=price,
                current_price=price,
                purchase_date=datetime.now().isoformat(),
                last_update=datetime.now().isoformat()
            )
    
    def _calculate_sector_allocation(self, positions_data: List[Dict], 
                                   total_value: float) -> Dict[str, float]:
        """Расчет распределения по секторам."""
        sectors = {}
        for position in positions_data:
            sector = position["sector"]
            if sector not in sectors:
                sectors[sector] = 0
            sectors[sector] += position["weight_percent"]
        
        return sectors
    
    def _calculate_trades_statistics(self) -> Dict:
        """Расчет статистики сделок."""
        if not self.trades:
            return {
                "total_trades": 0,
                "buy_trades": 0,
                "sell_trades": 0,
                "total_commission": 0.0,
                "avg_trade_size": 0.0
            }
        
        buy_trades = [t for t in self.trades if t.action == "BUY"]
        sell_trades = [t for t in self.trades if t.action == "SELL"]
        total_commission = sum(t.commission for t in self.trades)
        total_volume = sum(t.quantity * t.price for t in self.trades)
        
        return {
            "total_trades": len(self.trades),
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "total_commission": total_commission,
            "avg_trade_size": total_volume / len(self.trades) if self.trades else 0.0,
            "total_volume": total_volume
        }


# Глобальный экземпляр портфеля (singleton pattern)
_global_portfolio = None


def get_portfolio_manager() -> PortfolioManager:
    """Получение глобального экземпляра портфеля."""
    global _global_portfolio
    if _global_portfolio is None:
        _global_portfolio = PortfolioManager()
    return _global_portfolio


def main():
    """Функция для тестирования модуля."""
    async def test_portfolio():
        print("🧪 Тестирование PortfolioManager...")
        
        try:
            # Создаем портфель
            portfolio = PortfolioManager(initial_balance=1_000_000)
            
            print(f"💰 Создан портфель с балансом: {portfolio.cash_balance:,.0f} ₽")
            
            # Тестируем покупку
            print("\n📊 Тестируем покупку SBER...")
            buy_result = await portfolio.buy_stock("SBER", 100)
            
            if buy_result["success"]:
                print("✅ Покупка успешна:")
                print(f"   Куплено: {buy_result['quantity']} шт по {buy_result['price']:.2f} ₽")
                print(f"   Комиссия: {buy_result['commission']:.2f} ₽")
                print(f"   Баланс: {buy_result['new_cash_balance']:,.0f} ₽")
            else:
                print(f"❌ Ошибка покупки: {buy_result['error']}")
            
            # Получаем сводку портфеля
            print("\n📋 Сводка портфеля:")
            summary = portfolio.get_portfolio_summary()
            
            print(f"   Общая стоимость: {summary['portfolio_value']:,.0f} ₽")
            print(f"   Наличные: {summary['cash_balance']:,.0f} ₽")
            print(f"   Позиций: {summary['positions_count']}")
            print(f"   P&L: {summary['unrealized_pnl']:+,.0f} ₽ ({summary['unrealized_pnl_percent']:+.2f}%)")
            
            if summary['positions']:
                print("   Позиции:")
                for pos in summary['positions']:
                    print(f"   • {pos['ticker']}: {pos['quantity']} шт, P&L: {pos['unrealized_pnl']:+.0f} ₽")
            
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
    
    asyncio.run(test_portfolio())


if __name__ == "__main__":
    main()
