"""
Risk Manager - Система управления рисками для торгового бота.

Этот модуль реализует:
- Расчет размеров позиций
- Управление стоп-лоссами и тейк-профитами
- Контроль дневных лимитов
- Оценка рисков портфеля
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Уровни риска для торговых решений."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


@dataclass
class RiskSettings:
    """Настройки управления рисками."""

    # Основные лимиты
    max_position_size_percent: float = 5.0  # Максимум 5% депозита на позицию
    max_daily_loss_percent: float = 3.0  # Максимум 3% дневной убыток
    max_portfolio_risk_percent: float = 15.0  # Максимум 15% риска портфеля
    max_trades_per_day: int = 5  # Максимум 5 сделок в день

    # Стоп-лоссы и тейк-профиты
    default_stop_loss_percent: float = 7.0  # 7% стоп-лосс по умолчанию
    default_take_profit_percent: float = 10.0  # 10% тейк-профит по умолчанию
    trailing_stop_percent: float = 3.0  # 3% трейлинг стоп

    # Корреляционные лимиты
    max_correlation_exposure: float = 30.0  # Максимум 30% в коррелированных активах
    sector_concentration_limit: float = 25.0  # Максимум 25% в одном секторе


@dataclass
class PositionRisk:
    """Оценка риска для позиции."""

    ticker: str
    current_price: float
    position_size: float
    stop_loss_price: float
    take_profit_price: float
    risk_amount: float
    risk_percent: float
    risk_level: RiskLevel
    confidence_score: float


class RiskManager:
    """Главный класс управления рисками."""

    def __init__(self, settings: Optional[RiskSettings] = None):
        """
        Инициализация менеджера рисков.

        Args:
            settings: Настройки риск-менеджмента
        """
        self.settings = settings or RiskSettings()
        self.daily_trades_count = 0
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()

        logger.info("RiskManager инициализирован")

    def calculate_position_size(
        self,
        ticker: str,
        entry_price: float,
        stop_loss_price: float,
        account_balance: float,
        confidence_score: float = 0.5,
    ) -> Dict:
        """
        Расчет размера позиции на основе риск-менеджмента.

        Args:
            ticker: Тикер акции
            entry_price: Цена входа
            stop_loss_price: Цена стоп-лосса
            account_balance: Баланс счета
            confidence_score: Уверенность в сигнале (0.0-1.0)

        Returns:
            Словарь с рекомендациями по позиции
        """
        try:
            # Проверяем дневные лимиты
            if not self._check_daily_limits():
                return self._create_rejected_position("Превышены дневные лимиты")

            # Базовый размер позиции (% от депозита)
            base_position_percent = self.settings.max_position_size_percent

            # Корректировка на уверенность в сигнале
            confidence_multiplier = 0.5 + (confidence_score * 0.5)  # 0.5-1.0
            adjusted_position_percent = base_position_percent * confidence_multiplier

            # Расчет риска на акцию
            price_risk_percent = abs(entry_price - stop_loss_price) / entry_price * 100

            # Максимальная позиция исходя из риска
            max_position_by_risk = (
                self.settings.max_position_size_percent / max(price_risk_percent, 1.0)
            ) * 100

            # Итоговый размер позиции
            final_position_percent = min(adjusted_position_percent, max_position_by_risk)
            final_position_amount = account_balance * (final_position_percent / 100)

            # Количество акций
            shares_count = int(final_position_amount / entry_price)
            actual_position_amount = shares_count * entry_price

            # Расчет риска
            risk_per_share = abs(entry_price - stop_loss_price)
            total_risk_amount = shares_count * risk_per_share
            risk_percent = (total_risk_amount / account_balance) * 100

            # Оценка уровня риска
            risk_level = self._assess_risk_level(risk_percent, price_risk_percent)

            result = {
                "approved": True,
                "ticker": ticker,
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price,
                "shares_count": shares_count,
                "position_amount": actual_position_amount,
                "position_percent": (actual_position_amount / account_balance) * 100,
                "risk_amount": total_risk_amount,
                "risk_percent": risk_percent,
                "risk_level": risk_level.value,
                "confidence_used": confidence_score,
                "recommendation": self._generate_position_recommendation(
                    risk_level, risk_percent, confidence_score
                ),
            }

            logger.info(f"Позиция {ticker}: {shares_count} акций, риск {risk_percent:.1f}%")
            return result

        except Exception as e:
            logger.error(f"Ошибка расчета позиции для {ticker}: {e}")
            return self._create_rejected_position(f"Ошибка расчета: {str(e)}")

    def calculate_stop_loss_take_profit(
        self, ticker: str, entry_price: float, signal_direction: str, volatility_factor: float = 1.0
    ) -> Dict:
        """
        Расчет уровней стоп-лосса и тейк-профита.

        Args:
            ticker: Тикер акции
            entry_price: Цена входа
            signal_direction: Направление сигнала (BUY/SELL)
            volatility_factor: Коэффициент волатильности (1.0 = нормальная)

        Returns:
            Уровни стоп-лосса и тейк-профита
        """
        try:
            # Базовые проценты с учетом волатильности
            stop_loss_percent = self.settings.default_stop_loss_percent * volatility_factor
            take_profit_percent = self.settings.default_take_profit_percent * volatility_factor

            if signal_direction.upper() == "BUY":
                stop_loss_price = entry_price * (1 - stop_loss_percent / 100)
                take_profit_price = entry_price * (1 + take_profit_percent / 100)
            else:  # SELL
                stop_loss_price = entry_price * (1 + stop_loss_percent / 100)
                take_profit_price = entry_price * (1 - take_profit_percent / 100)

            # Трейлинг стоп
            trailing_stop_distance = entry_price * (self.settings.trailing_stop_percent / 100)

            result = {
                "ticker": ticker,
                "entry_price": entry_price,
                "direction": signal_direction,
                "stop_loss_price": round(stop_loss_price, 2),
                "take_profit_price": round(take_profit_price, 2),
                "stop_loss_percent": stop_loss_percent,
                "take_profit_percent": take_profit_percent,
                "trailing_stop_distance": round(trailing_stop_distance, 2),
                "risk_reward_ratio": take_profit_percent / stop_loss_percent,
            }

            logger.info(f"{ticker} SL/TP: {stop_loss_price:.2f} / {take_profit_price:.2f}")
            return result

        except Exception as e:
            logger.error(f"Ошибка расчета SL/TP для {ticker}: {e}")
            return {"error": str(e)}

    def assess_portfolio_risk(self, positions: list) -> Dict:
        """
        Оценка риска портфеля.

        Args:
            positions: Список текущих позиций

        Returns:
            Анализ риска портфеля
        """
        try:
            if not positions:
                return {
                    "total_risk_percent": 0.0,
                    "risk_level": "LOW",
                    "positions_count": 0,
                    "sector_exposure": {},
                    "recommendations": ["Портфель пуст - можно открывать позиции"],
                }

            # Суммарный риск портфеля
            total_risk = sum(pos.get("risk_percent", 0) for pos in positions)

            # Анализ секторального распределения
            sector_exposure = self._analyze_sector_exposure(positions)

            # Корреляционный анализ
            correlation_risk = self._assess_correlation_risk(positions)

            # Общий уровень риска
            portfolio_risk_level = self._assess_portfolio_risk_level(
                total_risk, sector_exposure, correlation_risk
            )

            # Рекомендации
            recommendations = self._generate_portfolio_recommendations(
                total_risk, sector_exposure, portfolio_risk_level
            )

            result = {
                "total_risk_percent": round(total_risk, 2),
                "risk_level": portfolio_risk_level.value,
                "positions_count": len(positions),
                "sector_exposure": sector_exposure,
                "correlation_risk": correlation_risk,
                "max_allowed_risk": self.settings.max_portfolio_risk_percent,
                "risk_utilization": round(
                    (total_risk / self.settings.max_portfolio_risk_percent) * 100, 1
                ),
                "recommendations": recommendations,
            }

            return result

        except Exception as e:
            logger.error(f"Ошибка оценки портфеля: {e}")
            return {"error": str(e)}

    def _check_daily_limits(self) -> bool:
        """Проверка дневных лимитов."""
        current_date = datetime.now().date()

        # Сброс счетчиков в новый день
        if current_date != self.last_reset_date:
            self.daily_trades_count = 0
            self.daily_pnl = 0.0
            self.last_reset_date = current_date

        # Проверка лимитов
        if self.daily_trades_count >= self.settings.max_trades_per_day:
            logger.warning(f"Превышен лимит сделок в день: {self.daily_trades_count}")
            return False

        max_loss = self.settings.max_daily_loss_percent
        if self.daily_pnl < -max_loss:
            logger.warning(f"Превышен дневной убыток: {self.daily_pnl:.1f}%")
            return False

        return True

    def _assess_risk_level(self, risk_percent: float, price_risk_percent: float) -> RiskLevel:
        """Оценка уровня риска позиции."""
        if risk_percent <= 1.0 and price_risk_percent <= 3.0:
            return RiskLevel.LOW
        elif risk_percent <= 2.5 and price_risk_percent <= 5.0:
            return RiskLevel.MEDIUM
        elif risk_percent <= 4.0 and price_risk_percent <= 8.0:
            return RiskLevel.HIGH
        else:
            return RiskLevel.EXTREME

    def _create_rejected_position(self, reason: str) -> Dict:
        """Создание отклоненной позиции."""
        return {
            "approved": False,
            "reason": reason,
            "shares_count": 0,
            "position_amount": 0.0,
            "risk_amount": 0.0,
            "recommendation": f"Позиция отклонена: {reason}",
        }

    def _generate_position_recommendation(
        self, risk_level: RiskLevel, risk_percent: float, confidence_score: float
    ) -> str:
        """Генерация рекомендации по позиции."""
        if risk_level == RiskLevel.LOW:
            return f"✅ Низкий риск ({risk_percent:.1f}%) - рекомендуется к открытию"
        elif risk_level == RiskLevel.MEDIUM:
            return f"🟡 Средний риск ({risk_percent:.1f}%) - осторожно, но допустимо"
        elif risk_level == RiskLevel.HIGH:
            return f"🟠 Высокий риск ({risk_percent:.1f}%) - требует внимания"
        else:
            return f"🔴 Экстремальный риск ({risk_percent:.1f}%) - не рекомендуется"

    def _analyze_sector_exposure(self, positions: list) -> Dict:
        """Анализ секторального распределения."""
        # Заглушка - в реальности нужно получать сектора через API
        return {"Финансы": 40.0, "Энергетика": 30.0, "Технологии": 20.0, "Другие": 10.0}

    def _assess_correlation_risk(self, positions: list) -> float:
        """Оценка корреляционного риска."""
        # Упрощенная оценка - в реальности нужна корреляционная матрица
        return min(len(positions) * 10.0, 50.0)  # Примерный расчет

    def _assess_portfolio_risk_level(
        self, total_risk: float, sector_exposure: Dict, correlation_risk: float
    ) -> RiskLevel:
        """Оценка общего уровня риска портфеля."""
        if total_risk <= 5.0:
            return RiskLevel.LOW
        elif total_risk <= 10.0:
            return RiskLevel.MEDIUM
        elif total_risk <= 15.0:
            return RiskLevel.HIGH
        else:
            return RiskLevel.EXTREME

    def _generate_portfolio_recommendations(
        self, total_risk: float, sector_exposure: Dict, risk_level: RiskLevel
    ) -> list:
        """Генерация рекомендаций по портфелю."""
        recommendations = []

        if total_risk > self.settings.max_portfolio_risk_percent * 0.8:
            recommendations.append("⚠️ Высокая загрузка по риску - рассмотрите сокращение позиций")

        for sector, exposure in sector_exposure.items():
            if exposure > self.settings.sector_concentration_limit:
                recommendations.append(
                    f"📊 Высокая концентрация в секторе {sector}: {exposure:.1f}%"
                )

        if risk_level == RiskLevel.LOW:
            recommendations.append("✅ Портфель имеет консервативный профиль риска")
        elif risk_level == RiskLevel.EXTREME:
            recommendations.append("🚨 Критически высокий уровень риска портфеля!")

        return recommendations or ["Риск портфеля в пределах нормы"]


def main():
    """Функция для тестирования модуля."""
    print("🧪 Тестирование RiskManager...")

    # Создаем менеджер рисков
    risk_manager = RiskManager()

    # Тест расчета позиции
    print("\n📊 Тест расчета позиции:")
    position = risk_manager.calculate_position_size(
        ticker="SBER",
        entry_price=100.0,
        stop_loss_price=93.0,
        account_balance=100000.0,
        confidence_score=0.7,
    )

    for key, value in position.items():
        print(f"  {key}: {value}")

    # Тест расчета SL/TP
    print("\n🎯 Тест расчета стоп-лосса и тейк-профита:")
    sl_tp = risk_manager.calculate_stop_loss_take_profit(
        ticker="SBER", entry_price=100.0, signal_direction="BUY", volatility_factor=1.2
    )

    for key, value in sl_tp.items():
        print(f"  {key}: {value}")

    print("\n✅ Тестирование RiskManager завершено!")


if __name__ == "__main__":
    main()
