
"""
Daily Report System для торгового бота
Анализ итогов торгового дня и подготовка к следующему дню
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class DayTradingStats:
    """Статистика торгового дня"""
    trades_executed: int
    total_volume: float
    realized_pnl: float
    unrealized_pnl: float
    commission_paid: float
    biggest_winner: Optional[str]
    biggest_loser: Optional[str]
    win_rate: float

class DailyReportGenerator:
    """Генератор ежедневных отчетов"""
    
    def __init__(self, portfolio_manager, news_analyzer, technical_analyzer, rss_parser):
        self.portfolio_manager = portfolio_manager
        self.news_analyzer = news_analyzer
        self.technical_analyzer = technical_analyzer
        self.rss_parser = rss_parser
        self.logger = logging.getLogger(__name__)
        
    async def generate_daily_report(self, user_id: str) -> str:
        """
        Создает полный ежедневный отчет
        """
        try:
            report_date = datetime.now().strftime("%d.%m.%Y")
            
            # Получаем базовые данные
            trading_stats = await self._calculate_trading_stats(user_id)
            portfolio_summary = await self._get_portfolio_summary(user_id)
            
            # Формируем базовый отчет
            report = self._format_basic_report(report_date, trading_stats, portfolio_summary)
            
            self.logger.info(f"Daily report generated for user {user_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")
            return "❌ Ошибка при создании ежедневного отчета"
    
    async def _calculate_trading_stats(self, user_id: str) -> DayTradingStats:
        """Рассчитывает статистику торгов за день"""
        try:
            # Получаем сделки за сегодня
            today = datetime.now().date()
            trades = self.portfolio_manager.get_trades_by_date(user_id, today)
            
            if not trades:
                return DayTradingStats(
                    trades_executed=0,
                    total_volume=0,
                    realized_pnl=0,
                    unrealized_pnl=0,
                    commission_paid=0,
                    biggest_winner=None,
                    biggest_loser=None,
                    win_rate=0
                )
            
            # Анализируем сделки
            total_volume = sum(trade.get('volume', 0) for trade in trades)
            realized_pnl = sum(trade.get('pnl', 0) for trade in trades if trade.get('type') == 'sell')
            commission_paid = sum(trade.get('commission', 0) for trade in trades)
            
            # Нереализованная прибыль из портфеля
            portfolio = self.portfolio_manager.get_portfolio(user_id)
            unrealized_pnl = portfolio.get('unrealized_pnl', 0)
            
            return DayTradingStats(
                trades_executed=len(trades),
                total_volume=total_volume,
                realized_pnl=realized_pnl,
                unrealized_pnl=unrealized_pnl,
                commission_paid=commission_paid,
                biggest_winner=None,
                biggest_loser=None,
                win_rate=0
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating trading stats: {e}")
            return DayTradingStats(0, 0, 0, 0, 0, None, None, 0)
    
    async def _get_portfolio_summary(self, user_id: str) -> Dict:
        """Получает сводку по портфелю"""
        try:
            portfolio = self.portfolio_manager.get_portfolio(user_id)
            analytics = self.portfolio_manager.get_portfolio_analytics(user_id)
            
            return {
                'total_value': portfolio.get('total_value', 0),
                'cash_balance': portfolio.get('cash_balance', 0),
                'positions_count': len(portfolio.get('positions', [])),
                'total_pnl': analytics.get('total_return', 0),
                'daily_pnl_percent': analytics.get('daily_return', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting portfolio summary: {e}")
            return {}
    
    def _format_basic_report(self, date: str, trading_stats: DayTradingStats, portfolio_summary: Dict) -> str:
        """Форматирует базовый отчет"""
        
        # Заголовок
        report = f"📊 **ЕЖЕДНЕВНЫЙ ОТЧЕТ за {date}**\n\n"
        
        # Секция торговли
        report += "💼 **ТОРГОВАЯ АКТИВНОСТЬ:**\n"
        report += f"🔄 Сделок исполнено: {trading_stats.trades_executed}\n"
        report += f"💰 Общий объем: {trading_stats.total_volume:,.0f} ₽\n"
        report += f"📈 Реализованный P&L: {trading_stats.realized_pnl:+.2f} ₽\n"
        report += f"📊 Нереализованный P&L: {trading_stats.unrealized_pnl:+.2f} ₽\n"
        report += f"💸 Комиссии: {trading_stats.commission_paid:.2f} ₽\n"
        
        if trading_stats.trades_executed == 0:
            report += "😴 Сегодня сделок не было\n"
        
        report += "\n"
        
        # Секция портфеля
        report += "🏦 **ПОРТФЕЛЬ:**\n"
        report += f"💎 Общая стоимость: {portfolio_summary.get('total_value', 0):,.0f} ₽\n"
        report += f"💵 Свободные средства: {portfolio_summary.get('cash_balance', 0):,.0f} ₽\n"
        report += f"📁 Позиций в портфеле: {portfolio_summary.get('positions_count', 0)}\n"
        
        daily_pnl = portfolio_summary.get('daily_pnl_percent', 0)
        pnl_emoji = "📈" if daily_pnl >= 0 else "📉"
        report += f"{pnl_emoji} Изменение за день: {daily_pnl:+.2f}%\n"
        
        report += "\n"
        
        # Заключение
        total_pnl = (trading_stats.realized_pnl + trading_stats.unrealized_pnl)
        if total_pnl > 0:
            report += "🎉 **Успешный торговый день!**\n"
        elif total_pnl < -1000:
            report += "⚠️ **Сложный день, анализируем ошибки**\n"
        else:
            report += "💼 **Стабильный день, продолжаем работу**\n"
        
        report += f"⏰ Отчет создан: {datetime.now().strftime('%H:%M')}\n"
        report += "📱 Для анализа конкретного актива: /analysis TICKER"
        
        return report


def get_daily_report_generator(portfolio_manager, news_analyzer, technical_analyzer, rss_parser):
    """Фабричная функция для создания генератора отчетов"""
    return DailyReportGenerator(portfolio_manager, news_analyzer, technical_analyzer, rss_parser)
