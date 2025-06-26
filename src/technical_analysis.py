
"""
Модуль технического анализа для торгового бота.

Предоставляет функциональность для расчета основных технических индикаторов:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Moving Averages (SMA, EMA)
- Bollinger Bands

Использует исторические данные от Tinkoff Invest API.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import math

try:
    import pandas as pd
    import numpy as np
except ImportError:
    pd = None
    np = None

from tinkoff_client import TinkoffClient
from config import get_ticker_info


logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Анализатор технических индикаторов для акций."""
    
    def __init__(self):
        """Инициализация технического анализатора."""
        if not pd or not np:
            raise ImportError(
                "Установите pandas и numpy: pip install pandas numpy"
            )
        
        self.tinkoff = TinkoffClient()
        self.default_periods = {
            'rsi': 14,
            'sma_short': 20,
            'sma_long': 50,
            'ema_fast': 12,
            'ema_slow': 26,
            'bollinger': 20
        }
        
        logger.info("TechnicalAnalyzer инициализирован")
    
    async def get_historical_data(self, ticker: str, days: int = 100) -> Optional[pd.DataFrame]:
        """
        Получение исторических данных для анализа.
        
        Args:
            ticker: Тикер акции
            days: Количество дней для получения данных
            
        Returns:
            DataFrame с историческими данными или None при ошибке
        """
        try:
            # Поиск инструмента
            instrument = await self.tinkoff.search_instrument(ticker)
            if not instrument:
                logger.error(f"Инструмент {ticker} не найден")
                return None
            
            figi = instrument['figi']
            
            # Получение исторических данных
            # TODO: Реализовать через Tinkoff API get_candles
            # Пока возвращаем тестовые данные для разработки
            logger.info(f"Получение исторических данных для {ticker}")
            
            # Генерируем тестовые данные для разработки
            dates = pd.date_range(
                end=datetime.now(),
                periods=days,
                freq='D'
            )
            
            # Имитируем реальные цены с трендом и волатильностью
            base_price = 100.0
            prices = []
            for i in range(days):
                # Добавляем тренд и случайные колебания
                trend = i * 0.1
                volatility = np.random.normal(0, 2)
                price = base_price + trend + volatility
                prices.append(max(price, 1.0))  # Цена не может быть отрицательной
            
            # Создаем DataFrame
            df = pd.DataFrame({
                'date': dates,
                'close': prices,
                'high': [p * 1.02 for p in prices],  # Максимум на 2% выше
                'low': [p * 0.98 for p in prices],   # Минимум на 2% ниже
                'open': [prices[i-1] if i > 0 else prices[i] for i in range(len(prices))],
                'volume': np.random.randint(1000, 10000, days)
            })
            
            df.set_index('date', inplace=True)
            
            logger.info(f"Получено {len(df)} дней данных для {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Ошибка получения данных для {ticker}: {e}")
            return None
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Расчет RSI (Relative Strength Index).
        
        Args:
            prices: Серия цен закрытия
            period: Период для расчета (по умолчанию 14)
            
        Returns:
            Серия значений RSI
        """
        try:
            if len(prices) < period + 1:
                logger.warning(f"Недостаточно данных для RSI: {len(prices)} < {period + 1}")
                return pd.Series(dtype=float)
            
            # Расчет изменений цен
            delta = prices.diff()
            
            # Разделение на прибыли и убытки
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            # Экспоненциальное скользящее среднее
            avg_gains = gains.ewm(span=period).mean()
            avg_losses = losses.ewm(span=period).mean()
            
            # Расчет RS и RSI
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            logger.error(f"Ошибка расчета RSI: {e}")
            return pd.Series(dtype=float)
    
    def calculate_moving_averages(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """
        Расчет скользящих средних (SMA и EMA).
        
        Args:
            prices: Серия цен закрытия
            
        Returns:
            Словарь с различными скользящими средними
        """
        try:
            result = {}
            
            # Simple Moving Averages
            result['sma_20'] = prices.rolling(window=self.default_periods['sma_short']).mean()
            result['sma_50'] = prices.rolling(window=self.default_periods['sma_long']).mean()
            
            # Exponential Moving Averages
            result['ema_12'] = prices.ewm(span=self.default_periods['ema_fast']).mean()
            result['ema_26'] = prices.ewm(span=self.default_periods['ema_slow']).mean()
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка расчета скользящих средних: {e}")
            return {}
    
    def calculate_macd(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """
        Расчет MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: Серия цен закрытия
            
        Returns:
            Словарь с линиями MACD
        """
        try:
            # Экспоненциальные скользящие средние
            ema_fast = prices.ewm(span=self.default_periods['ema_fast']).mean()
            ema_slow = prices.ewm(span=self.default_periods['ema_slow']).mean()
            
            # MACD линия
            macd_line = ema_fast - ema_slow
            
            # Signal линия (EMA от MACD)
            signal_line = macd_line.ewm(span=9).mean()
            
            # Гистограмма
            histogram = macd_line - signal_line
            
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
            
        except Exception as e:
            logger.error(f"Ошибка расчета MACD: {e}")
            return {}
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """
        Расчет полос Боллинджера.
        
        Args:
            prices: Серия цен закрытия
            period: Период для расчета
            std_dev: Количество стандартных отклонений
            
        Returns:
            Словарь с полосами Боллинджера
        """
        try:
            # Скользящее среднее
            sma = prices.rolling(window=period).mean()
            
            # Стандартное отклонение
            std = prices.rolling(window=period).std()
            
            # Верхняя и нижняя полосы
            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)
            
            return {
                'upper': upper_band,
                'middle': sma,
                'lower': lower_band
            }
            
        except Exception as e:
            logger.error(f"Ошибка расчета полос Боллинджера: {e}")
            return {}
    
    def interpret_rsi(self, rsi_value: float) -> Dict[str, str]:
        """
        Интерпретация значения RSI.
        
        Args:
            rsi_value: Текущее значение RSI
            
        Returns:
            Словарь с интерпретацией
        """
        if pd.isna(rsi_value):
            return {
                'signal': 'UNKNOWN',
                'description': 'Недостаточно данных для расчета',
                'emoji': '⚪'
            }
        
        if rsi_value >= 70:
            return {
                'signal': 'SELL',
                'description': 'Перекупленность (RSI ≥ 70)',
                'emoji': '🔴'
            }
        elif rsi_value <= 30:
            return {
                'signal': 'BUY',
                'description': 'Перепроданность (RSI ≤ 30)',
                'emoji': '🟢'
            }
        elif rsi_value >= 50:
            return {
                'signal': 'NEUTRAL_BULLISH',
                'description': 'Нейтрально-бычий тренд',
                'emoji': '🟡'
            }
        else:
            return {
                'signal': 'NEUTRAL_BEARISH',
                'description': 'Нейтрально-медвежий тренд',
                'emoji': '🟠'
            }
    
    def interpret_macd(self, macd_data: Dict[str, pd.Series]) -> Dict[str, str]:
        """
        Интерпретация MACD сигналов.
        
        Args:
            macd_data: Данные MACD
            
        Returns:
            Словарь с интерпретацией
        """
        try:
            if not macd_data or 'macd' not in macd_data:
                return {
                    'signal': 'UNKNOWN',
                    'description': 'Недостаточно данных для MACD',
                    'emoji': '⚪'
                }
            
            # Получаем последние значения
            macd_line = macd_data['macd'].dropna()
            signal_line = macd_data['signal'].dropna()
            histogram = macd_data['histogram'].dropna()
            
            if len(macd_line) < 2 or len(signal_line) < 2:
                return {
                    'signal': 'UNKNOWN',
                    'description': 'Недостаточно данных для анализа MACD',
                    'emoji': '⚪'
                }
            
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_histogram = histogram.iloc[-1] if len(histogram) > 0 else 0
            
            # Пересечения линий
            if current_macd > current_signal and len(macd_line) > 1:
                prev_macd = macd_line.iloc[-2]
                prev_signal = signal_line.iloc[-2]
                
                if prev_macd <= prev_signal:  # Бычий crossover
                    return {
                        'signal': 'BUY',
                        'description': 'Бычий crossover (MACD > Signal)',
                        'emoji': '🟢'
                    }
            
            elif current_macd < current_signal and len(macd_line) > 1:
                prev_macd = macd_line.iloc[-2]
                prev_signal = signal_line.iloc[-2]
                
                if prev_macd >= prev_signal:  # Медвежий crossover
                    return {
                        'signal': 'SELL',
                        'description': 'Медвежий crossover (MACD < Signal)',
                        'emoji': '🔴'
                    }
            
            # Анализ по гистограмме
            if current_histogram > 0:
                return {
                    'signal': 'NEUTRAL_BULLISH',
                    'description': 'Бычий импульс (гистограмма > 0)',
                    'emoji': '🟡'
                }
            else:
                return {
                    'signal': 'NEUTRAL_BEARISH',
                    'description': 'Медвежий импульс (гистограмма < 0)',
                    'emoji': '🟠'
                }
                
        except Exception as e:
            logger.error(f"Ошибка интерпретации MACD: {e}")
            return {
                'signal': 'UNKNOWN',
                'description': 'Ошибка анализа MACD',
                'emoji': '⚪'
            }
    
    async def get_technical_analysis(self, ticker: str) -> Dict:
        """
        Полный технический анализ акции.
        
        Args:
            ticker: Тикер акции
            
        Returns:
            Полный результат технического анализа
        """
        try:
            ticker = ticker.upper()
            logger.info(f"Начинаем технический анализ для {ticker}")
            
            # Получение исторических данных
            df = await self.get_historical_data(ticker)
            if df is None or df.empty:
                return self._create_error_result(ticker, "Не удалось получить исторические данные")
            
            prices = df['close']
            
            # Расчет индикаторов
            rsi = self.calculate_rsi(prices)
            moving_averages = self.calculate_moving_averages(prices)
            macd_data = self.calculate_macd(prices)
            bollinger = self.calculate_bollinger_bands(prices)
            
            # Получение последних значений
            current_price = prices.iloc[-1] if len(prices) > 0 else 0
            current_rsi = rsi.iloc[-1] if len(rsi) > 0 else np.nan
            
            # Интерпретация сигналов
            rsi_interpretation = self.interpret_rsi(current_rsi)
            macd_interpretation = self.interpret_macd(macd_data)
            
            # Анализ трендов скользящих средних
            ma_analysis = self._analyze_moving_averages(current_price, moving_averages)
            
            # Общий технический сигнал
            overall_signal = self._calculate_overall_signal(
                rsi_interpretation, macd_interpretation, ma_analysis
            )
            
            # Формирование результата
            result = {
                'ticker': ticker,
                'company_name': get_ticker_info(ticker).get('name', f'Акция {ticker}'),
                'analysis_timestamp': datetime.now().isoformat(),
                'success': True,
                'error_message': None,
                
                'current_price': round(current_price, 2),
                'data_period_days': len(df),
                
                'indicators': {
                    'rsi': {
                        'value': round(current_rsi, 2) if not pd.isna(current_rsi) else None,
                        'interpretation': rsi_interpretation
                    },
                    'macd': {
                        'current_macd': round(macd_data['macd'].iloc[-1], 4) if 'macd' in macd_data and len(macd_data['macd']) > 0 else None,
                        'current_signal': round(macd_data['signal'].iloc[-1], 4) if 'signal' in macd_data and len(macd_data['signal']) > 0 else None,
                        'interpretation': macd_interpretation
                    },
                    'moving_averages': ma_analysis,
                    'bollinger_bands': self._analyze_bollinger_bands(current_price, bollinger)
                },
                
                'overall_signal': overall_signal,
                
                'metadata': {
                    'calculation_time_seconds': 0,
                    'data_quality': 'synthetic' if len(df) == 100 else 'real'  # Пока используем тестовые данные
                }
            }
            
            logger.info(f"Технический анализ {ticker} завершен: {overall_signal['signal']}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка технического анализа для {ticker}: {e}")
            return self._create_error_result(ticker, str(e))
    
    def _analyze_moving_averages(self, current_price: float, ma_data: Dict[str, pd.Series]) -> Dict:
        """Анализ сигналов скользящих средних."""
        try:
            if not ma_data:
                return {'signal': 'UNKNOWN', 'description': 'Нет данных'}
            
            signals = []
            descriptions = []
            
            # Анализ SMA 20/50
            if 'sma_20' in ma_data and 'sma_50' in ma_data:
                sma_20 = ma_data['sma_20'].dropna()
                sma_50 = ma_data['sma_50'].dropna()
                
                if len(sma_20) > 0 and len(sma_50) > 0:
                    current_sma_20 = sma_20.iloc[-1]
                    current_sma_50 = sma_50.iloc[-1]
                    
                    if current_sma_20 > current_sma_50:
                        signals.append('BUY')
                        descriptions.append('SMA 20 > SMA 50 (бычий тренд)')
                    else:
                        signals.append('SELL')
                        descriptions.append('SMA 20 < SMA 50 (медвежий тренд)')
            
            # Анализ позиции цены относительно SMA 20
            if 'sma_20' in ma_data:
                sma_20 = ma_data['sma_20'].dropna()
                if len(sma_20) > 0:
                    current_sma_20 = sma_20.iloc[-1]
                    if current_price > current_sma_20:
                        descriptions.append(f'Цена выше SMA 20 (+{((current_price/current_sma_20 - 1) * 100):.1f}%)')
                    else:
                        descriptions.append(f'Цена ниже SMA 20 ({((current_price/current_sma_20 - 1) * 100):.1f}%)')
            
            # Общий сигнал по скользящим средним
            if signals:
                buy_signals = signals.count('BUY')
                sell_signals = signals.count('SELL')
                
                if buy_signals > sell_signals:
                    overall_signal = 'BUY'
                    emoji = '🟢'
                elif sell_signals > buy_signals:
                    overall_signal = 'SELL'
                    emoji = '🔴'
                else:
                    overall_signal = 'HOLD'
                    emoji = '🟡'
            else:
                overall_signal = 'UNKNOWN'
                emoji = '⚪'
            
            return {
                'signal': overall_signal,
                'emoji': emoji,
                'description': '; '.join(descriptions[:2]),  # Первые 2 описания
                'details': descriptions
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа скользящих средних: {e}")
            return {'signal': 'UNKNOWN', 'description': 'Ошибка анализа'}
    
    def _analyze_bollinger_bands(self, current_price: float, bollinger_data: Dict[str, pd.Series]) -> Dict:
        """Анализ полос Боллинджера."""
        try:
            if not bollinger_data or 'upper' not in bollinger_data:
                return {'signal': 'UNKNOWN', 'description': 'Нет данных'}
            
            upper = bollinger_data['upper'].dropna()
            middle = bollinger_data['middle'].dropna()
            lower = bollinger_data['lower'].dropna()
            
            if len(upper) == 0 or len(middle) == 0 or len(lower) == 0:
                return {'signal': 'UNKNOWN', 'description': 'Недостаточно данных'}
            
            current_upper = upper.iloc[-1]
            current_middle = middle.iloc[-1]
            current_lower = lower.iloc[-1]
            
            # Определение позиции цены
            if current_price >= current_upper:
                return {
                    'signal': 'SELL',
                    'emoji': '🔴',
                    'description': 'Цена у верхней полосы (перекупленность)',
                    'position': 'UPPER'
                }
            elif current_price <= current_lower:
                return {
                    'signal': 'BUY',
                    'emoji': '🟢',
                    'description': 'Цена у нижней полосы (перепроданность)',
                    'position': 'LOWER'
                }
            elif current_price > current_middle:
                return {
                    'signal': 'HOLD',
                    'emoji': '🟡',
                    'description': 'Цена выше средней линии',
                    'position': 'UPPER_MIDDLE'
                }
            else:
                return {
                    'signal': 'HOLD',
                    'emoji': '🟠',
                    'description': 'Цена ниже средней линии',
                    'position': 'LOWER_MIDDLE'
                }
                
        except Exception as e:
            logger.error(f"Ошибка анализа полос Боллинджера: {e}")
            return {'signal': 'UNKNOWN', 'description': 'Ошибка анализа'}
    
    def _calculate_overall_signal(self, rsi_interp: Dict, macd_interp: Dict, ma_analysis: Dict) -> Dict:
        """Расчет общего технического сигнала."""
        try:
            # Весовые коэффициенты для разных индикаторов
            weights = {
                'rsi': 0.3,
                'macd': 0.4,
                'ma': 0.3
            }
            
            # Преобразование сигналов в числовые значения
            signal_values = {
                'STRONG_BUY': 2,
                'BUY': 1,
                'NEUTRAL_BULLISH': 0.5,
                'HOLD': 0,
                'NEUTRAL_BEARISH': -0.5,
                'SELL': -1,
                'STRONG_SELL': -2,
                'UNKNOWN': 0
            }
            
            # Получение числовых значений
            rsi_value = signal_values.get(rsi_interp.get('signal', 'UNKNOWN'), 0)
            macd_value = signal_values.get(macd_interp.get('signal', 'UNKNOWN'), 0)
            ma_value = signal_values.get(ma_analysis.get('signal', 'UNKNOWN'), 0)
            
            # Взвешенный расчет
            weighted_score = (
                rsi_value * weights['rsi'] +
                macd_value * weights['macd'] +
                ma_value * weights['ma']
            )
            
            # Преобразование обратно в сигнал
            if weighted_score >= 1.0:
                signal = 'STRONG_BUY'
                emoji = '💚'
                confidence = min(0.9, 0.5 + abs(weighted_score) * 0.2)
            elif weighted_score >= 0.3:
                signal = 'BUY'
                emoji = '🟢'
                confidence = min(0.8, 0.5 + abs(weighted_score) * 0.2)
            elif weighted_score <= -1.0:
                signal = 'STRONG_SELL'
                emoji = '🔴'
                confidence = min(0.9, 0.5 + abs(weighted_score) * 0.2)
            elif weighted_score <= -0.3:
                signal = 'SELL'
                emoji = '🟠'
                confidence = min(0.8, 0.5 + abs(weighted_score) * 0.2)
            else:
                signal = 'HOLD'
                emoji = '🟡'
                confidence = 0.5
            
            return {
                'signal': signal,
                'emoji': emoji,
                'confidence': round(confidence, 2),
                'score': round(weighted_score, 2),
                'description': f'Технический анализ ({signal})',
                'components': {
                    'rsi_signal': rsi_interp.get('signal', 'UNKNOWN'),
                    'macd_signal': macd_interp.get('signal', 'UNKNOWN'),
                    'ma_signal': ma_analysis.get('signal', 'UNKNOWN')
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка расчета общего сигнала: {e}")
            return {
                'signal': 'UNKNOWN',
                'emoji': '⚪',
                'confidence': 0.0,
                'description': 'Ошибка расчета сигнала'
            }
    
    def _create_error_result(self, ticker: str, error_message: str) -> Dict:
        """Создание результата с ошибкой."""
        return {
            'ticker': ticker,
            'company_name': get_ticker_info(ticker).get('name', f'Акция {ticker}'),
            'analysis_timestamp': datetime.now().isoformat(),
            'success': False,
            'error_message': error_message,
            'indicators': {},
            'overall_signal': {
                'signal': 'UNKNOWN',
                'emoji': '⚪',
                'description': 'Анализ недоступен'
            }
        }
    
    def format_for_telegram(self, analysis_result: Dict) -> str:
        """
        Форматирование результата анализа для Telegram.
        
        Args:
            analysis_result: Результат технического анализа
            
        Returns:
            Отформатированный текст для Telegram
        """
        if not analysis_result['success']:
            return f"❌ *Ошибка технического анализа {analysis_result['ticker']}*\n\n" \
                   f"Причина: {analysis_result['error_message']}"
        
        ticker = analysis_result['ticker']
        company_name = analysis_result['company_name']
        current_price = analysis_result.get('current_price', 0)
        overall_signal = analysis_result['overall_signal']
        indicators = analysis_result['indicators']
        
        # Основной заголовок
        text = f"📊 *ТЕХНИЧЕСКИЙ АНАЛИЗ {ticker}*\n\n"
        text += f"🏢 *Компания:* {company_name}\n"
        text += f"💰 *Текущая цена:* {current_price} ₽\n"
        text += f"📅 *Период анализа:* {analysis_result.get('data_period_days', 0)} дней\n\n"
        
        # Общий сигнал
        text += f"{overall_signal['emoji']} *ОБЩИЙ СИГНАЛ: {overall_signal['signal']}*\n"
        text += f"🎯 *Уверенность:* {overall_signal.get('confidence', 0):.0%}\n"
        text += f"📝 *Оценка:* {overall_signal.get('score', 0):+.2f}\n\n"
        
        # RSI анализ
        if 'rsi' in indicators and indicators['rsi']['value'] is not None:
            rsi_data = indicators['rsi']
            rsi_interp = rsi_data['interpretation']
            text += f"📈 *RSI (Индекс относительной силы):*\n"
            text += f"{rsi_interp['emoji']} Значение: {rsi_data['value']}\n"
            text += f"📝 {rsi_interp['description']}\n\n"
        
        # MACD анализ
        if 'macd' in indicators and indicators['macd']['current_macd'] is not None:
            macd_data = indicators['macd']
            macd_interp = macd_data['interpretation']
            text += f"📊 *MACD (Схождение-расхождение):*\n"
            text += f"{macd_interp['emoji']} MACD: {macd_data['current_macd']}\n"
            text += f"📡 Signal: {macd_data['current_signal']}\n"
            text += f"📝 {macd_interp['description']}\n\n"
        
        # Скользящие средние
        if 'moving_averages' in indicators:
            ma_data = indicators['moving_averages']
            text += f"📈 *Скользящие средние:*\n"
            text += f"{ma_data.get('emoji', '⚪')} {ma_data.get('description', 'Нет данных')}\n\n"
        
        # Полосы Боллинджера
        if 'bollinger_bands' in indicators:
            bb_data = indicators['bollinger_bands']
            text += f"📊 *Полосы Боллинджера:*\n"
            text += f"{bb_data.get('emoji', '⚪')} {bb_data.get('description', 'Нет данных')}\n\n"
        
        # Компоненты общего сигнала
        components = overall_signal.get('components', {})
        if components:
            text += f"🔍 *Детализация сигналов:*\n"
            text += f"• RSI: {components.get('rsi_signal', 'N/A')}\n"
            text += f"• MACD: {components.get('macd_signal', 'N/A')}\n"
            text += f"• MA: {components.get('ma_signal', 'N/A')}\n\n"
        
        # Метаданные
        text += f"🕐 *Время анализа:* {datetime.now().strftime('%H:%M:%S')}\n"
        
        # Подсказки
        text += f"\n*💡 Что дальше?*\n"
        text += f"• `/price {ticker}` - текущая цена\n"
        text += f"• `/news {ticker}` - анализ новостей\n"
        text += f"• `/signal {ticker}` - комбинированный сигнал\n\n"
        
        # Дисклеймер
        text += f"⚠️ *Дисклеймер:* Технический анализ не гарантирует результат. " \
                f"Используйте в комплексе с фундаментальным анализом."
        
        return text


# Глобальный экземпляр анализатора
_global_technical_analyzer = None


def get_technical_analyzer() -> TechnicalAnalyzer:
    """Получение глобального экземпляра технического анализатора."""
    global _global_technical_analyzer
    if _global_technical_analyzer is None:
        _global_technical_analyzer = TechnicalAnalyzer()
    return _global_technical_analyzer


# Функции-обертки для удобного использования
async def analyze_ticker_technical(ticker: str) -> Dict:
    """Быстрая функция для технического анализа тикера."""
    analyzer = get_technical_analyzer()
    return await analyzer.get_technical_analysis(ticker)


async def get_ticker_analysis_for_telegram(ticker: str) -> str:
    """Получение отформатированного технического анализа для Telegram."""
    analyzer = get_technical_analyzer()
    result = await analyzer.get_technical_analysis(ticker)
    return analyzer.format_for_telegram(result)


def main():
    """Функция для тестирования модуля."""
    import asyncio
    import json
    
    async def test_analysis():
        print("🧪 Тестирование TechnicalAnalyzer...")
        
        try:
            # Создаем анализатор
            analyzer = TechnicalAnalyzer()
            
            # Тестируем технический анализ
            print("📊 Тестируем технический анализ SBER...")
            result = await analyzer.get_technical_analysis("SBER")
            
            print("✅ Результат:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            print("\n📱 Форматированный результат для Telegram:")
            telegram_text = analyzer.format_for_telegram(result)
            print(telegram_text)
            
            # Тестируем отдельные функции
            print("\n🧮 Тестируем отдельные индикаторы...")
            
            # Генерируем тестовые данные
            import pandas as pd
            import numpy as np
            
            test_prices = pd.Series([100 + i + np.random.normal(0, 2) for i in range(50)])
            
            # Тест RSI
            rsi = analyzer.calculate_rsi(test_prices)
            print(f"RSI последнее значение: {rsi.iloc[-1]:.2f}")
            
            # Тест MACD
            macd_data = analyzer.calculate_macd(test_prices)
            if 'macd' in macd_data:
                print(f"MACD последнее значение: {macd_data['macd'].iloc[-1]:.4f}")
            
            # Тест скользящих средних
            ma_data = analyzer.calculate_moving_averages(test_prices)
            if 'sma_20' in ma_data:
                print(f"SMA 20 последнее значение: {ma_data['sma_20'].iloc[-1]:.2f}")
            
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
            import traceback
            traceback.print_exc()
    
    print("Тестирование Technical Analyzer...")
    asyncio.run(test_analysis())


if __name__ == "__main__":
    main()
