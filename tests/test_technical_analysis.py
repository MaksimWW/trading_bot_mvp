
import os
import sys
import pytest
import asyncio

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from technical_analysis import TechnicalAnalyzer
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_technical_analyzer_init():
    """Тест инициализации TechnicalAnalyzer."""
    analyzer = TechnicalAnalyzer()
    assert analyzer is not None
    assert hasattr(analyzer, "tinkoff_client")
    assert analyzer.tinkoff_client is not None


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_calculate_rsi():
    """Тест расчета RSI."""
    analyzer = TechnicalAnalyzer()
    # Используем обычный список вместо pandas.Series
    test_prices = [100 + i for i in range(20)]
    rsi = analyzer.calculate_rsi(test_prices)
    
    # RSI должен возвращать float значение
    assert isinstance(rsi, float)
    assert 0 <= rsi <= 100
    
    # Для восходящего тренда RSI должен быть выше 50
    assert rsi > 50


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_calculate_sma():
    """Тест расчета простой скользящей средней."""
    analyzer = TechnicalAnalyzer()
    test_prices = [100, 101, 102, 103, 104]
    period = 3
    
    sma_values = analyzer.calculate_sma(test_prices, period)
    
    assert isinstance(sma_values, list)
    assert len(sma_values) == len(test_prices) - period + 1
    
    # Проверяем правильность расчета
    expected_first = (100 + 101 + 102) / 3
    assert abs(sma_values[0] - expected_first) < 0.01


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_calculate_ema():
    """Тест расчета экспоненциальной скользящей средней."""
    analyzer = TechnicalAnalyzer()
    test_prices = [100, 101, 102, 103, 104, 105]
    period = 3
    
    ema_values = analyzer.calculate_ema(test_prices, period)
    
    assert isinstance(ema_values, list)
    assert len(ema_values) == len(test_prices) - period + 1
    assert all(isinstance(val, float) for val in ema_values)


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_calculate_macd():
    """Тест расчета MACD."""
    analyzer = TechnicalAnalyzer()
    # Создаем достаточно данных для MACD (нужно минимум 35 точек)
    test_prices = [100 + (i * 0.5) for i in range(50)]
    
    macd_result = analyzer.calculate_macd(test_prices)
    
    assert isinstance(macd_result, dict)
    assert "macd_line" in macd_result
    assert "signal_line" in macd_result
    assert "histogram" in macd_result
    assert "trend" in macd_result
    
    assert isinstance(macd_result["macd_line"], float)
    assert isinstance(macd_result["signal_line"], float)
    assert isinstance(macd_result["histogram"], float)
    assert macd_result["trend"] in ["BULLISH", "BEARISH", "BULLISH_CROSSOVER", "BEARISH_CROSSOVER", "NEUTRAL"]


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_calculate_bollinger_bands():
    """Тест расчета полос Боллинджера."""
    analyzer = TechnicalAnalyzer()
    test_prices = [100 + i for i in range(25)]
    
    bb_result = analyzer.calculate_bollinger_bands(test_prices)
    
    assert isinstance(bb_result, dict)
    assert "upper_band" in bb_result
    assert "middle_band" in bb_result
    assert "lower_band" in bb_result
    assert "bandwidth" in bb_result
    assert "position" in bb_result
    
    # Верхняя полоса должна быть больше средней, средняя больше нижней
    assert bb_result["upper_band"] > bb_result["middle_band"]
    assert bb_result["middle_band"] > bb_result["lower_band"]


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
@pytest.mark.asyncio
async def test_analyze_ticker_error_handling():
    """Тест обработки ошибок в analyze_ticker."""
    analyzer = TechnicalAnalyzer()
    
    # Тестируем с несуществующим тикером
    result = await analyzer.analyze_ticker("NONEXISTENT")
    
    assert isinstance(result, dict)
    assert "success" in result
    assert "ticker" in result
    assert result["ticker"] == "NONEXISTENT"
    
    # При ошибке success должен быть False
    if not result.get("success", True):
        assert "error" in result


def test_signal_helpers():
    """Тест вспомогательных функций для сигналов."""
    analyzer = TechnicalAnalyzer()
    
    # Тест _get_signal_label
    assert analyzer._get_signal_label(0.7) == "STRONG_BUY"
    assert analyzer._get_signal_label(0.3) == "BUY"
    assert analyzer._get_signal_label(0.0) == "HOLD"
    assert analyzer._get_signal_label(-0.3) == "SELL"
    assert analyzer._get_signal_label(-0.7) == "STRONG_SELL"
    
    # Тест _get_rsi_level
    assert analyzer._get_rsi_level(75) == "OVERBOUGHT"
    assert analyzer._get_rsi_level(25) == "OVERSOLD"
    assert analyzer._get_rsi_level(50) == "NEUTRAL"
    
    # Тест _get_rsi_signal
    assert analyzer._get_rsi_signal(25) == "BUY"
    assert analyzer._get_rsi_signal(75) == "SELL"
    assert analyzer._get_rsi_signal(50) == "HOLD"


def test_module_structure():
    """Базовый тест структуры модуля."""
    # Проверяем что файл существует
    module_path = os.path.join(os.path.dirname(__file__), "..", "src", "technical_analysis.py")
    assert os.path.exists(module_path), "technical_analysis.py должен существовать"


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_confidence_calculation():
    """Тест расчета уверенности в сигнале."""
    analyzer = TechnicalAnalyzer()
    
    # Создаем тестовые данные MACD
    test_macd = {
        "trend": "BULLISH_CROSSOVER",
        "histogram": 0.5
    }
    
    confidence = analyzer._calculate_confidence(75, test_macd, 100)
    
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0
    
    # С экстремальным RSI и кроссовером уверенность должна быть высокой
    assert confidence > 0.7


if __name__ == "__main__":
    pytest.main([__file__])
