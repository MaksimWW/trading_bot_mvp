
"""
Генератор торговых сигналов для торгового бота.

Объединяет технический анализ и анализ новостей для создания
итоговых торговых рекомендаций с весовыми коэффициентами.
"""

import logging
from datetime import datetime
from typing import Dict, Optional
import asyncio

from technical_analysis import get_technical_analyzer
from news_analyzer import get_news_analyzer


logger = logging.getLogger(__name__)


class SignalGenerator:
    """Генератор комбинированных торговых сигналов."""
    
    def __init__(self):
        """Инициализация генератора сигналов."""
        self.technical_analyzer = get_technical_analyzer()
        self.news_analyzer = get_news_analyzer()
        
        # Весовые коэффициенты для комбинирования сигналов
        self.weights = {
            'technical': 0.6,  # 60% технический анализ
            'news': 0.4        # 40% анализ новостей
        }
        
        logger.info("SignalGenerator инициализирован")
    
    async def generate_combined_signal(self, ticker: str) -> Dict:
        """
        Генерация комбинированного торгового сигнала.
        
        Args:
            ticker: Тикер акции
            
        Returns:
            Комбинированный сигнал с рекомендациями
        """
        try:
            ticker = ticker.upper()
            logger.info(f"Генерация комбинированного сигнала для {ticker}")
            
            # Параллельное получение технического и новостного анализа
            technical_task = self.technical_analyzer.get_technical_analysis(ticker)
            news_task = self.news_analyzer.analyze_ticker_news(ticker, include_sentiment=True)
            
            technical_result, news_result = await asyncio.gather(
                technical_task, news_task, return_exceptions=True
            )
            
            # Обработка результатов с проверкой на ошибки
            if isinstance(technical_result, Exception):
                logger.error(f"Ошибка технического анализа: {technical_result}")
                technical_result = None
                
            if isinstance(news_result, Exception):
                logger.error(f"Ошибка анализа новостей: {news_result}")
                news_result = None
            
            # Генерация комбинированного сигнала
            combined_signal = self._combine_signals(ticker, technical_result, news_result)
            
            logger.info(f"Комбинированный сигнал {ticker}: {combined_signal['signal']}")
            return combined_signal
            
        except Exception as e:
            logger.error(f"Ошибка генерации сигнала для {ticker}: {e}")
            return self._create_error_signal(ticker, str(e))
    
    def _combine_signals(self, ticker: str, technical_result: Optional[Dict], 
                        news_result: Optional[Dict]) -> Dict:
        """Комбинирование технического и новостного анализа."""
        try:
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
            
            # Получение технического сигнала
            technical_score = 0
            technical_confidence = 0
            if technical_result and technical_result.get('success'):
                tech_signal = technical_result.get('overall_signal', {}).get('signal', 'UNKNOWN')
                technical_score = signal_values.get(tech_signal, 0)
                technical_confidence = technical_result.get('overall_signal', {}).get('confidence', 0)
            
            # Получение новостного сигнала  
            news_score = 0
            news_confidence = 0
            if news_result and news_result.get('success') and news_result.get('sentiment'):
                sentiment_score = news_result['sentiment'].get('sentiment_score', 0)
                news_score = sentiment_score * 2  # Преобразуем [-1,1] в [-2,2]
                news_confidence = news_result['sentiment'].get('confidence', 0)
            
            # Взвешенное комбинирование
            combined_score = (
                technical_score * self.weights['technical'] +
                news_score * self.weights['news']
            )
            
            # Комбинированная уверенность
            combined_confidence = (
                technical_confidence * self.weights['technical'] +
                news_confidence * self.weights['news']
            )
            
            # Преобразование обратно в сигнал
            if combined_score >= 1.2:
                signal = 'STRONG_BUY'
                emoji = '💚'
            elif combined_score >= 0.4:
                signal = 'BUY'  
                emoji = '🟢'
            elif combined_score <= -1.2:
                signal = 'STRONG_SELL'
                emoji = '🔴'
            elif combined_score <= -0.4:
                signal = 'SELL'
                emoji = '🟠'
            else:
                signal = 'HOLD'
                emoji = '🟡'
            
            # Формирование результата
            return {
                'ticker': ticker,
                'company_name': technical_result.get('company_name', f'Акция {ticker}') if technical_result else f'Акция {ticker}',
                'timestamp': datetime.now().isoformat(),
                'success': True,
                'error_message': None,
                
                'combined_signal': {
                    'signal': signal,
                    'emoji': emoji,
                    'score': round(combined_score, 2),
                    'confidence': round(combined_confidence, 2),
                    'description': f'Комбинированный сигнал ({signal})'
                },
                
                'components': {
                    'technical': {
                        'available': technical_result is not None and technical_result.get('success', False),
                        'signal': technical_result.get('overall_signal', {}).get('signal', 'UNKNOWN') if technical_result else 'UNKNOWN',
                        'score': technical_score,
                        'confidence': technical_confidence,
                        'weight': self.weights['technical']
                    },
                    'news': {
                        'available': news_result is not None and news_result.get('success', False) and news_result.get('sentiment'),
                        'signal': self._news_score_to_signal(news_score),
                        'score': news_score,
                        'confidence': news_confidence,
                        'weight': self.weights['news']
                    }
                },
                
                'details': {
                    'technical_analysis': technical_result,
                    'news_analysis': news_result
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка комбинирования сигналов: {e}")
            return self._create_error_signal(ticker, f"Ошибка комбинирования: {str(e)}")
    
    def _news_score_to_signal(self, news_score: float) -> str:
        """Преобразование новостного score в сигнал."""
        if news_score >= 1.2:
            return 'STRONG_BUY'
        elif news_score >= 0.4:
            return 'BUY'
        elif news_score <= -1.2:
            return 'STRONG_SELL'
        elif news_score <= -0.4:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _create_error_signal(self, ticker: str, error_message: str) -> Dict:
        """Создание сигнала с ошибкой."""
        return {
            'ticker': ticker,
            'company_name': f'Акция {ticker}',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'error_message': error_message,
            'combined_signal': {
                'signal': 'UNKNOWN',
                'emoji': '⚪',
                'score': 0.0,
                'confidence': 0.0,
                'description': 'Анализ недоступен'
            }
        }
    
    def format_for_telegram(self, signal_result: Dict) -> str:
        """Форматирование результата для Telegram."""
        if not signal_result['success']:
            return f"❌ *Ошибка генерации сигнала {signal_result['ticker']}*\n\n" \
                   f"Причина: {signal_result['error_message']}"
        
        ticker = signal_result['ticker']
        company_name = signal_result['company_name']
        combined = signal_result['combined_signal']
        components = signal_result['components']
        
        # Заголовок
        text = f"🎯 *ТОРГОВЫЙ СИГНАЛ {ticker}*\n\n"
        text += f"🏢 *Компания:* {company_name}\n\n"
        
        # Основной сигнал
        text += f"{combined['emoji']} *РЕКОМЕНДАЦИЯ: {combined['signal']}*\n"
        text += f"📊 *Итоговая оценка:* {combined['score']:+.2f}\n"
        text += f"🎯 *Уверенность:* {combined['confidence']:.0%}\n\n"
        
        # Компоненты анализа
        text += f"📋 *СОСТАВЛЯЮЩИЕ АНАЛИЗА:*\n\n"
        
        # Технический анализ
        tech = components['technical']
        if tech['available']:
            text += f"📈 *Технический анализ ({tech['weight']:.0%}):*\n"
            text += f"📊 Сигнал: {tech['signal']}\n"
            text += f"📈 Вклад: {tech['score']:+.2f}\n\n"
        else:
            text += f"📈 *Технический анализ:* ❌ Недоступен\n\n"
        
        # Анализ новостей
        news = components['news']
        if news['available']:
            text += f"📰 *Анализ новостей ({news['weight']:.0%}):*\n"
            text += f"📊 Сигнал: {news['signal']}\n"
            text += f"📈 Вклад: {news['score']:+.2f}\n\n"
        else:
            text += f"📰 *Анализ новостей:* ❌ Недоступен\n\n"
        
        # Время и действия
        text += f"🕐 *Время анализа:* {datetime.now().strftime('%H:%M:%S')}\n\n"
        
        text += f"*💡 Детальная информация:*\n"
        text += f"• `/analysis {ticker}` - технический анализ\n"
        text += f"• `/news {ticker}` - анализ новостей\n"
        text += f"• `/price {ticker}` - текущая цена\n\n"
        
        # Дисклеймер
        text += f"⚠️ *Важно:* Комбинированный сигнал учитывает множество факторов, " \
                f"но не гарантирует результат. Принимайте решения обдуманно."
        
        return text


# Глобальный экземпляр генератора
_global_signal_generator = None


def get_signal_generator() -> SignalGenerator:
    """Получение глобального экземпляра генератора сигналов."""
    global _global_signal_generator
    if _global_signal_generator is None:
        _global_signal_generator = SignalGenerator()
    return _global_signal_generator


async def generate_trading_signal(ticker: str) -> Dict:
    """Быстрая функция для генерации торгового сигнала."""
    generator = get_signal_generator()
    return await generator.generate_combined_signal(ticker)


async def get_trading_signal_for_telegram(ticker: str) -> str:
    """Получение отформатированного торгового сигнала для Telegram."""
    generator = get_signal_generator()
    result = await generator.generate_combined_signal(ticker)
    return generator.format_for_telegram(result)


def main():
    """Функция для тестирования модуля."""
    import asyncio
    import json
    
    async def test_signal_generation():
        print("🧪 Тестирование SignalGenerator...")
        
        try:
            generator = SignalGenerator()
            
            print("🎯 Тестируем генерацию сигнала для SBER...")
            result = await generator.generate_combined_signal("SBER")
            
            print("✅ Результат:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            print("\n📱 Форматированный результат для Telegram:")
            telegram_text = generator.format_for_telegram(result)
            print(telegram_text)
            
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
            import traceback
            traceback.print_exc()
    
    print("Тестирование Signal Generator...")
    asyncio.run(test_signal_generation())


if __name__ == "__main__":
    main()
