
import pytest
import sys
import os


def test_technical_analysis_functions():
    """Тест математических функций технического анализа без API зависимостей."""
    # Простой тест RSI алгоритма
    def simple_rsi(prices, period=14):
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    # Тестовые данные - восходящий тренд
    test_prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112, 114, 113, 115]
    
    rsi = simple_rsi(test_prices, 14)
    
    # RSI должен быть в правильном диапазоне
    assert 0 <= rsi <= 100
    assert isinstance(rsi, float)
    # Для восходящего тренда RSI должен быть выше 50
    assert rsi > 50


def test_sma_calculation():
    """Тест простой скользящей средней."""
    def simple_sma(prices, period):
        if len(prices) < period:
            return []
        return [sum(prices[i-period+1:i+1])/period for i in range(period-1, len(prices))]
    
    test_prices = [1, 2, 3, 4, 5]
    sma = simple_sma(test_prices, 3)
    
    expected = [2.0, 3.0, 4.0]  # (1+2+3)/3, (2+3+4)/3, (3+4+5)/3
    assert sma == expected


def test_ema_calculation():
    """Тест экспоненциальной скользящей средней."""
    def simple_ema(prices, period):
        if len(prices) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema_values = []
        
        # Первое значение EMA = SMA
        sma_first = sum(prices[:period]) / period
        ema_values.append(sma_first)
        
        # Остальные значения по формуле EMA
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)
        
        return ema_values
    
    test_prices = [1, 2, 3, 4, 5, 6]
    ema = simple_ema(test_prices, 3)
    
    assert len(ema) == len(test_prices) - 3 + 1
    assert all(isinstance(val, float) for val in ema)


def test_macd_basic_logic():
    """Тест базовой логики MACD без сложных вычислений."""
    def macd_trend_logic(fast_ema, slow_ema):
        """Определяет тренд MACD на основе EMA."""
        if fast_ema > slow_ema:
            return "BULLISH"
        elif fast_ema < slow_ema:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    # Тестируем логику
    assert macd_trend_logic(12.0, 10.0) == "BULLISH"
    assert macd_trend_logic(8.0, 10.0) == "BEARISH"
    assert macd_trend_logic(10.0, 10.0) == "NEUTRAL"


def test_bollinger_bands_logic():
    """Тест логики полос Боллинджера."""
    def bb_position(price, middle, upper, lower):
        """Определение позиции цены относительно полос Боллинджера."""
        if price > upper:
            return "ABOVE_UPPER"
        elif price < lower:
            return "BELOW_LOWER"
        elif price > middle:
            return "UPPER_HALF"
        else:
            return "LOWER_HALF"
    
    # Тестируем логику
    assert bb_position(105, 100, 110, 90) == "UPPER_HALF"
    assert bb_position(115, 100, 110, 90) == "ABOVE_UPPER"
    assert bb_position(85, 100, 110, 90) == "BELOW_LOWER"
    assert bb_position(95, 100, 110, 90) == "LOWER_HALF"


def test_signal_scoring_logic():
    """Тест логики подсчета сигналов."""
    def get_signal_label(score):
        """Конвертация численного сигнала в текстовую метку."""
        if score >= 0.6:
            return "STRONG_BUY"
        elif score >= 0.2:
            return "BUY"
        elif score <= -0.6:
            return "STRONG_SELL"
        elif score <= -0.2:
            return "SELL"
        else:
            return "HOLD"
    
    # Тестируем разные сигналы
    assert get_signal_label(0.8) == "STRONG_BUY"
    assert get_signal_label(0.3) == "BUY"
    assert get_signal_label(0.0) == "HOLD"
    assert get_signal_label(-0.3) == "SELL"
    assert get_signal_label(-0.8) == "STRONG_SELL"


def test_rsi_interpretation():
    """Тест интерпретации RSI значений."""
    def get_rsi_level(rsi):
        """Определение уровня RSI."""
        if rsi >= 70:
            return "OVERBOUGHT"
        elif rsi <= 30:
            return "OVERSOLD"
        elif rsi >= 60:
            return "STRONG"
        elif rsi <= 40:
            return "WEAK"
        else:
            return "NEUTRAL"
    
    def get_rsi_signal(rsi):
        """Торговый сигнал на основе RSI."""
        if rsi <= 30:
            return "BUY"
        elif rsi >= 70:
            return "SELL"
        else:
            return "HOLD"
    
    # Тестируем интерпретацию
    assert get_rsi_level(75) == "OVERBOUGHT"
    assert get_rsi_level(25) == "OVERSOLD"
    assert get_rsi_level(50) == "NEUTRAL"
    
    assert get_rsi_signal(25) == "BUY"
    assert get_rsi_signal(75) == "SELL"
    assert get_rsi_signal(50) == "HOLD"


def test_confidence_calculation():
    """Тест расчета уверенности в сигнале."""
    def calculate_confidence(rsi, has_crossover, data_points):
        """Упрощенный расчет уверенности."""
        confidence = 0.5  # Базовая уверенность
        
        # Больше данных = больше уверенности
        if data_points >= 100:
            confidence += 0.2
        elif data_points >= 50:
            confidence += 0.1
        
        # Экстремальные значения RSI увеличивают уверенность
        if rsi <= 25 or rsi >= 75:
            confidence += 0.2
        
        # Кроссоверы увеличивают уверенность
        if has_crossover:
            confidence += 0.2
        
        return min(1.0, confidence)
    
    # Тестируем расчет уверенности
    high_conf = calculate_confidence(75, True, 100)
    assert high_conf > 0.8
    
    low_conf = calculate_confidence(50, False, 20)
    assert low_conf <= 0.6


def test_project_structure():
    """Тест что файлы проекта существуют."""
    project_files = [
        'src/technical_analysis.py',
        'src/tinkoff_client.py', 
        'src/telegram_bot.py',
        'src/main.py',
        'src/signal_generator.py'
    ]
    
    for file_path in project_files:
        assert os.path.exists(file_path), f"File {file_path} should exist"


def test_requirements_file():
    """Тест что файл requirements.txt существует и содержит нужные пакеты."""
    assert os.path.exists('requirements.txt'), "requirements.txt should exist"
    
    with open('requirements.txt', 'r') as f:
        content = f.read()
    
    # Проверяем наличие основных пакетов (pytest не обязателен)
    required_packages = ['tinkoff-investments', 'python-telegram-bot']
    for package in required_packages:
        assert package in content, f"Package {package} should be in requirements.txt"


def test_mathematical_edge_cases():
    """Тест граничных случаев в математических функциях."""
    def safe_divide(a, b):
        """Безопасное деление с проверкой на ноль."""
        if b == 0:
            return 0.0
        return a / b
    
    def normalize_score(score):
        """Нормализация сигнала в диапазон -1 до 1."""
        return max(-1.0, min(1.0, score))
    
    # Тестируем граничные случаи
    assert safe_divide(10, 0) == 0.0
    assert safe_divide(10, 2) == 5.0
    
    assert normalize_score(2.0) == 1.0
    assert normalize_score(-2.0) == -1.0
    assert normalize_score(0.5) == 0.5


def test_data_validation():
    """Тест валидации входных данных."""
    def validate_price_data(prices):
        """Валидация данных о ценах."""
        if not prices:
            return False, "Empty price data"
        
        if len(prices) < 2:
            return False, "Insufficient price data"
        
        if not all(isinstance(p, (int, float)) and p > 0 for p in prices):
            return False, "Invalid price values"
        
        return True, "Valid data"
    
    # Тестируем валидацию
    valid, msg = validate_price_data([100, 101, 102])
    assert valid is True
    
    invalid, msg = validate_price_data([])
    assert invalid is False
    
    invalid, msg = validate_price_data([100])
    assert invalid is False
    
    invalid, msg = validate_price_data([100, -50, 102])
    assert invalid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
