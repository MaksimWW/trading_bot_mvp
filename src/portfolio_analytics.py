"""
Portfolio Analytics для торгового бота.

Расчет продвинутых метрик портфеля: Sharpe ratio, Sortino ratio,
максимальная просадка, VaR, корреляционный анализ.
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from statistics import mean, stdev
from typing import Dict, List, Optional

from portfolio_manager import PortfolioManager
from tinkoff_client import TinkoffClient

logger = logging.getLogger(__name__)


@dataclass
class PortfolioMetrics:
    """Структура метрик портфеля."""

    # Доходность
    total_return: float  # Общая доходность %
    annualized_return: float  # Годовая доходность %

    # Риск-метрики
    volatility: float  # Волатильность %
    max_drawdown: float  # Максимальная просадка %
    sharpe_ratio: float  # Коэффициент Шарпа
    sortino_ratio: float  # Коэффициент Сортино

    # VaR метрики
    var_95: float  # Value at Risk 95%
    var_99: float  # Value at Risk 99%

    # Корреляции
    avg_correlation: float  # Средняя корреляция активов
    diversification_ratio: float  # Коэффициент диверсификации

    # Метаданные
    analysis_period_days: int
    positions_count: int
    calculation_timestamp: datetime


class PortfolioAnalytics:
    """Расчет продвинутых метрик портфеля."""

    def __init__(self, portfolio_manager: PortfolioManager = None):
        """Инициализация Portfolio Analytics."""
        self.portfolio_manager = portfolio_manager or PortfolioManager()
        self.tinkoff_client = TinkoffClient()
        self.risk_free_rate = 0.15  # 15% годовых - ключевая ставка ЦБ РФ

        logger.info("Portfolio Analytics инициализирован")

    async def calculate_portfolio_metrics(self, days: int = 30) -> PortfolioMetrics:
        """
        Расчет полных метрик портфеля.

        Args:
            days: Период для анализа в днях

        Returns:
            PortfolioMetrics с полным анализом
        """
        logger.info(f"Начинаем расчет метрик портфеля за {days} дней")

        try:
            # Получаем текущий портфель
            portfolio = self.portfolio_manager.get_portfolio_summary()
            positions = portfolio["positions"]

            if not positions:
                return self._create_empty_metrics(days)

            # Получаем исторические данные для всех позиций
            historical_data = await self._get_historical_data(positions, days)

            if not historical_data:
                return self._create_empty_metrics(days)

            # Рассчитываем метрики
            returns_data = self._calculate_returns(historical_data, positions)
            risk_metrics = self._calculate_risk_metrics(returns_data)
            correlation_metrics = self._calculate_correlation_metrics(historical_data)

            # Объединяем все метрики
            metrics = PortfolioMetrics(
                # Доходность
                total_return=returns_data["total_return"],
                annualized_return=returns_data["annualized_return"],
                # Риск
                volatility=risk_metrics["volatility"],
                max_drawdown=risk_metrics["max_drawdown"],
                sharpe_ratio=risk_metrics["sharpe_ratio"],
                sortino_ratio=risk_metrics["sortino_ratio"],
                # VaR
                var_95=risk_metrics["var_95"],
                var_99=risk_metrics["var_99"],
                # Корреляции
                avg_correlation=correlation_metrics["avg_correlation"],
                diversification_ratio=correlation_metrics["diversification_ratio"],
                # Метаданные
                analysis_period_days=days,
                positions_count=len(positions),
                calculation_timestamp=datetime.now(),
            )

            logger.info(
                f"Метрики портфеля рассчитаны: Sharpe {metrics.sharpe_ratio:.2f}, "
                f"Max DD {metrics.max_drawdown:.1%}"
            )

            return metrics

        except Exception as e:
            logger.error(f"Ошибка расчета метрик портфеля: {e}")
            return self._create_error_metrics(days, str(e))

    async def _get_historical_data(self, positions: List[Dict], days: int) -> Dict[str, List[Dict]]:
        """Получение исторических данных для всех позиций."""
        historical_data = {}

        for position in positions:
            ticker = position["ticker"]
            try:
                # Получаем исторические цены
                prices = self.tinkoff_client.get_price_history(ticker, days + 10)

                if prices and len(prices) >= days:
                    # Берем последние дни (prices уже список float-ов)
                    historical_data[ticker] = prices[-days:]

            except Exception as e:
                logger.warning(f"Не удалось получить данные для {ticker}: {e}")
                continue

        return historical_data

    def _calculate_returns(
        self, historical_data: Dict[str, List[float]], positions: List[Dict]
    ) -> Dict:
        """Расчет доходности портфеля"""
        if not historical_data or not positions:
            return {"total_return": 0.0, "annualized_return": 0.0, "daily_returns": []}

        portfolio_values = self._calculate_portfolio_values(historical_data, positions)
        if len(portfolio_values) < 2:
            return {"total_return": 0.0, "annualized_return": 0.0, "daily_returns": []}

        return self._calculate_return_metrics(portfolio_values)

    def _calculate_portfolio_values(
        self, historical_data: Dict[str, List[float]], positions: List[Dict]
    ) -> List[float]:
        """Расчет стоимости портфеля по дням"""
        min_length = min(len(data) for data in historical_data.values()) if historical_data else 0
        portfolio_values = []

        for day_index in range(min_length):
            daily_value = 0
            for position in positions:
                ticker = position["ticker"]
                if ticker in historical_data and day_index < len(historical_data[ticker]):
                    price = float(historical_data[ticker][day_index])
                    quantity = position["quantity"]
                    daily_value += price * quantity
            portfolio_values.append(daily_value)

        return portfolio_values

    def _calculate_return_metrics(self, portfolio_values: List[float]) -> Dict:
        """Расчет метрик доходности"""
        daily_returns = []
        for i in range(1, len(portfolio_values)):
            if portfolio_values[i - 1] != 0:
                ret = (portfolio_values[i] / portfolio_values[i - 1]) - 1
                daily_returns.append(ret)

        total_return = (
            (portfolio_values[-1] / portfolio_values[0] - 1) * 100
            if portfolio_values[0] != 0
            else 0
        )
        annualized_return = (
            total_return * (365 / len(portfolio_values)) if len(portfolio_values) > 0 else 0
        )

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "daily_returns": daily_returns,
            "portfolio_series": portfolio_values,
        }

    def _calculate_risk_metrics(self, returns_data: Dict) -> Dict:
        """Расчет риск-метрик."""
        daily_returns = returns_data.get("daily_returns", [])

        if not daily_returns or len(daily_returns) < 2:
            return {
                "volatility": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "var_95": 0.0,
                "var_99": 0.0,
            }

        returns_array = daily_returns
        portfolio_series = returns_data.get("portfolio_series")

        # Волатильность (годовая)
        volatility = stdev(returns_array) * math.sqrt(252) * 100 if len(returns_array) > 1 else 0.0

        # Максимальная просадка
        max_drawdown = 0.0
        if portfolio_series is not None and len(daily_returns) > 1:
            # Расчет кумулятивной доходности
            cumulative = []
            cum_product = 1.0
            for ret in daily_returns:
                cum_product *= 1 + ret
                cumulative.append(cum_product)

            # Поиск максимальной просадки
            running_max = cumulative[0]
            max_dd = 0.0
            for value in cumulative:
                if value > running_max:
                    running_max = value
                drawdown = (value - running_max) / running_max
                if drawdown < max_dd:
                    max_dd = drawdown
            max_drawdown = abs(max_dd) * 100

        # Sharpe ratio
        daily_risk_free = (self.risk_free_rate / 100) / 252
        excess_returns = [ret - daily_risk_free for ret in returns_array]
        returns_std = stdev(returns_array) if len(returns_array) > 1 else 0
        sharpe_ratio = mean(excess_returns) * math.sqrt(252) / returns_std if returns_std > 0 else 0

        # Sortino ratio (только негативные отклонения)
        negative_returns = [ret for ret in returns_array if ret < daily_risk_free]
        downside_std = (
            stdev(negative_returns)
            if len(negative_returns) > 1
            else (stdev(returns_array) if len(returns_array) > 1 else 0)
        )
        sortino_ratio = (
            mean(excess_returns) * math.sqrt(252) / downside_std if downside_std > 0 else 0
        )

        # VaR (Value at Risk)
        sorted_returns = sorted(returns_array)
        n = len(sorted_returns)
        var_95_idx = max(0, int(n * 0.05) - 1)
        var_99_idx = max(0, int(n * 0.01) - 1)
        var_95 = sorted_returns[var_95_idx] * 100 if n > 0 else 0.0  # 5% худшие дни
        var_99 = sorted_returns[var_99_idx] * 100 if n > 0 else 0.0  # 1% худшие дни

        return {
            "volatility": volatility,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "var_95": var_95,
            "var_99": var_99,
        }

    def _calculate_correlation_metrics(self, historical_data: Dict[str, List[float]]) -> Dict:
        """Расчет метрик корреляции"""
        if len(historical_data) < 2:
            return {"avg_correlation": 0.0, "diversification_ratio": 1.0}

        returns_data = self._calculate_ticker_returns(historical_data)
        correlations = self._calculate_pairwise_correlations(returns_data)

        avg_correlation = sum(correlations) / len(correlations) if correlations else 0.0
        diversification_ratio = 1.0 / (1.0 + avg_correlation) if avg_correlation > -1 else 1.0

        return {"avg_correlation": avg_correlation, "diversification_ratio": diversification_ratio}

    def _calculate_ticker_returns(
        self, historical_data: Dict[str, List[float]]
    ) -> Dict[str, List[float]]:
        """Расчет доходности по тикерам"""
        returns_data = {}

        for ticker, ticker_data in historical_data.items():
            if len(ticker_data) > 1:
                daily_returns = []
                for i in range(1, len(ticker_data)):
                    prev_price = float(ticker_data[i - 1]) if ticker_data[i - 1] != 0 else 0.0
                    curr_price = float(ticker_data[i])

                    if prev_price != 0:
                        ret = (curr_price / prev_price) - 1
                        daily_returns.append(ret)

                if daily_returns:
                    returns_data[ticker] = daily_returns

        return returns_data

    def _calculate_pairwise_correlations(self, returns_data: Dict[str, List[float]]) -> List[float]:
        """Расчет попарных корреляций"""
        correlations = []
        tickers = list(returns_data.keys())

        for i in range(len(tickers)):
            for j in range(i + 1, len(tickers)):
                ticker1, ticker2 = tickers[i], tickers[j]
                returns1, returns2 = returns_data[ticker1], returns_data[ticker2]

                min_len = min(len(returns1), len(returns2))
                if min_len > 1:
                    r1 = returns1[-min_len:]
                    r2 = returns2[-min_len:]
                    correlation = self._calculate_correlation(r1, r2)
                    if correlation is not None:
                        correlations.append(correlation)

        return correlations

    def _calculate_correlation(self, x: List[float], y: List[float]) -> Optional[float]:
        """Вычисление коэффициента корреляции Пирсона."""
        if len(x) != len(y) or len(x) < 2:
            return None

        n = len(x)
        mean_x = mean(x)
        mean_y = mean(y)

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        sum_sq_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        sum_sq_y = sum((y[i] - mean_y) ** 2 for i in range(n))

        denominator = math.sqrt(sum_sq_x * sum_sq_y)

        if denominator == 0:
            return None

        return numerator / denominator

    def _create_empty_metrics(self, days: int) -> PortfolioMetrics:
        """Создание пустых метрик для портфеля без позиций."""
        return PortfolioMetrics(
            total_return=0.0,
            annualized_return=0.0,
            volatility=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            var_95=0.0,
            var_99=0.0,
            avg_correlation=0.0,
            diversification_ratio=1.0,
            analysis_period_days=days,
            positions_count=0,
            calculation_timestamp=datetime.now(),
        )

    def _create_error_metrics(self, days: int, error_message: str) -> PortfolioMetrics:
        """Создание метрик при ошибке."""
        logger.error(f"Создание error metrics: {error_message}")
        return self._create_empty_metrics(days)

    def format_metrics_for_telegram(self, metrics: PortfolioMetrics) -> str:
        """Форматирование метрик для отправки в Telegram."""
        if metrics.positions_count == 0:
            return f"""
📊 АНАЛИТИКА ПОРТФЕЛЯ

💼 Статус: Портфель пуст
📅 Период анализа: {metrics.analysis_period_days} дней

💡 Рекомендация: Добавьте позиции для начала анализа
- /buy TICKER QUANTITY - покупка акций
- /ai_analysis TICKER - анализ перед покупкой
"""

        # Эмодзи для метрик
        return_emoji = "📈" if metrics.total_return >= 0 else "📉"
        sharpe_emoji = (
            "🟢" if metrics.sharpe_ratio > 1.0 else "🟡" if metrics.sharpe_ratio > 0.5 else "🔴"
        )
        risk_emoji = (
            "🟢" if metrics.max_drawdown < 5 else "🟡" if metrics.max_drawdown < 10 else "🔴"
        )

        text = f"""
📊 АНАЛИТИКА ПОРТФЕЛЯ

💰 ДОХОДНОСТЬ:
{return_emoji} Общая: {metrics.total_return:+.2f}%
📈 Годовая: {metrics.annualized_return:+.2f}%

⚡ РИСК-МЕТРИКИ:
📊 Волатильность: {metrics.volatility:.1f}%
{risk_emoji} Макс. просадка: {metrics.max_drawdown:.1f}%
{sharpe_emoji} Sharpe ratio: {metrics.sharpe_ratio:.2f}
🎯 Sortino ratio: {metrics.sortino_ratio:.2f}

🛡️ VALUE AT RISK:
⚠️ VaR 95%: {metrics.var_95:.2f}%
🚨 VaR 99%: {metrics.var_99:.2f}%

🔗 ДИВЕРСИФИКАЦИЯ:
📊 Средняя корреляция: {metrics.avg_correlation:.2f}
🎯 Коэф. диверсификации: {metrics.diversification_ratio:.2f}

📋 СВОДКА:
- Позиций: {metrics.positions_count}
- Период: {metrics.analysis_period_days} дней
- Расчет: {metrics.calculation_timestamp.strftime('%H:%M:%S %d.%m.%Y')}

💡 Интерпретация:
- Sharpe > 1.0 = отличная доходность с учетом риска
- Max DD < 5% = низкий риск портфеля
- Корреляция < 0.5 = хорошая диверсификация

⚠️ Дисклеймер: Метрики рассчитаны на основе исторических данных
"""

        return text


def main():
    """Функция для тестирования модуля."""
    import asyncio

    async def test_portfolio_analytics():
        print("📊 Тестирование Portfolio Analytics...")

        try:
            analytics = PortfolioAnalytics()

            # Тестируем расчет метрик
            print("🔢 Рассчитываем метрики портфеля...")
            metrics = await analytics.calculate_portfolio_metrics(days=30)

            print("✅ Результат анализа:")
            print(f"Позиций: {metrics.positions_count}")
            print(f"Общая доходность: {metrics.total_return:+.2f}%")
            print(f"Sharpe ratio: {metrics.sharpe_ratio:.2f}")
            print(f"Max drawdown: {metrics.max_drawdown:.1f}%")

            print("\n📱 Форматированный результат для Telegram:")
            telegram_text = analytics.format_metrics_for_telegram(metrics)
            print(telegram_text)

        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")

    asyncio.run(test_portfolio_analytics())


if __name__ == "__main__":
    main()
