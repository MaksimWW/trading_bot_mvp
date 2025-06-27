
import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Мокаем TinkoffClient перед импортом, чтобы избежать проблем с libstdc++.so.6
with patch('tinkoff_client.TinkoffClient'):
    from technical_analysis import TechnicalAnalyzer, analyze_ticker


class TestTechnicalAnalyzer:
    """Тесты для TechnicalAnalyzer."""

    def test_technical_analyzer_init(self):
        """Тест инициализации TechnicalAnalyzer."""
        with patch('technical_analysis.TinkoffClient'):
            analyzer = TechnicalAnalyzer()
            assert analyzer is not None
            assert hasattr(analyzer, "tinkoff_client")

    def test_calculate_rsi_basic(self):
        """Тест базового расчета RSI."""
        with patch('technical_analysis.TinkoffClient'):
            analyzer = TechnicalAnalyzer()
            
            # Тестовые данные - восходящий тренд
            test_prices = [100 + i for i in range(20)]
            rsi = analyzer.calculate_rsi(test_prices)
            
            assert isinstance(rsi, float)
            assert 0 <= rsi <= 100
            # Для восходящего тренда RSI должен быть выше 50
            assert rsi > 50

    def test_calculate_rsi_insufficient_data(self):
        """Тест RSI с недостаточными данными."""
        with patch('technical_analysis.TinkoffClient'):
            analyzer = TechnicalAnalyzer()
            
            # Недостаточно данных
            test_prices = [100, 101, 102]
            rsi = analyzer.calculate_rsi(test_prices)
            
            # Должен вернуть нейтральное значение
            assert rsi == 50.0

    def test_calculate_sma(self):
        """Тест расчета простой скользящей средней."""
        with patch('technical_analysis.TinkoffClient'):
            analyzer = TechnicalAnalyzer()
            test_prices = [100, 101, 102, 103, 104]
            period = 3
            
            sma_values = analyzer.calculate_sma(test_prices, period)
            
            assert isinstance(sma_values, list)
            assert len(sma_values) == len(test_prices) - period + 1
            
            # Проверяем правильность расчета первого значения
            expected_first = (100 + 101 + 102) / 3
            assert abs(sma_values[0] - expected_first) < 0.01

    def test_calculate_sma_insufficient_data(self):
        """Тест SMA с недостаточными данными."""
        with patch('technical_analysis.TinkoffClient'):
            analyzer = TechnicalAnalyzer()
            test_prices = [100, 101]
            period = 5
            
            sma_values = analyzer.calculate_sma(test_prices, period)
            
            assert sma_values == []

    def test_calculate_ema(self):
        """Тест расчета экспоненциальной скользящей средней."""
        with patch('technical_analysis.TinkoffClient'):
            analyzer = TechnicalAnalyzer()
            test_prices = [100, 101, 102, 103, 104, 105]
            period = 3
            
            ema_values = analyzer.calculate_ema(test_prices, period)
            
            assert isinstance(ema_values, list)
            assert len(ema_values) == len(test_prices) - period + 1
            assert all(isinstance(val, float) for val in ema_values)

    def test_calculate_macd(self):
        """Тест расчета MACD."""
        with patch('technical_analysis.TinkoffClient'):
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

    def test_calculate_macd_insufficient_data(self):
        """Тест MACD с недостаточными данными."""
        with patch('technical_analysis.TinkoffClient'):
            analyzer = TechnicalAnalyzer()
            test_prices = [100, 101, 102]  # Слишком мало данных
            
            macd_result = analyzer.calculate_macd(test_prices)
            
            assert macd_result["trend"] == "NEUTRAL"

    def test_calculate_bollinger_bands(self):
        """Тест расчета полос Боллинджера."""
        with patch('technical_analysis.TinkoffClient'):
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

    @pytest.mark.asyncio
    async def test_analyze_ticker_with_mock(self):
        """Тест analyze_ticker с мокированными данными."""
        mock_ticker_data = {
            "price_history": [100 + i for i in range(100)],  # Достаточно данных
            "current_price": 200.0
        }
        
        with patch('technical_analysis.TinkoffClient') as mock_client_class:
            # Создаем мок экземпляра
            mock_client = AsyncMock()
            mock_client.get_ticker_data_for_analysis.return_value = mock_ticker_data
            mock_client_class.return_value = mock_client
            
            analyzer = TechnicalAnalyzer()
            result = await analyzer.analyze_ticker("TEST")
            
            assert isinstance(result, dict)
            assert "ticker" in result
            assert "success" in result
            assert result["ticker"] == "TEST"
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_analyze_ticker_no_data(self):
        """Тест analyze_ticker без данных."""
        with patch('technical_analysis.TinkoffClient') as mock_client_class:
            # Мокаем отсутствие данных
            mock_client = AsyncMock()
            mock_client.get_ticker_data_for_analysis.return_value = None
            mock_client_class.return_value = mock_client
            
            analyzer = TechnicalAnalyzer()
            result = await analyzer.analyze_ticker("NONEXISTENT")
            
            assert isinstance(result, dict)
            assert "success" in result
            assert "ticker" in result
            assert result["ticker"] == "NONEXISTENT"
            assert result["success"] is False
            assert "error" in result

    def test_signal_helpers(self):
        """Тест вспомогательных функций для сигналов."""
        with patch('technical_analysis.TinkoffClient'):
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

    def test_confidence_calculation(self):
        """Тест расчета уверенности в сигнале."""
        with patch('technical_analysis.TinkoffClient'):
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

    def test_module_structure(self):
        """Базовый тест структуры модуля."""
        # Проверяем что файл существует
        module_path = os.path.join(os.path.dirname(__file__), "..", "src", "technical_analysis.py")
        assert os.path.exists(module_path), "technical_analysis.py должен существовать"


class TestModuleFunctions:
    """Тесты для функций модуля."""

    @pytest.mark.asyncio
    async def test_analyze_ticker_function(self):
        """Тест функции analyze_ticker."""
        mock_ticker_data = {
            "price_history": [100 + i for i in range(50)],
            "current_price": 150.0
        }
        
        with patch('technical_analysis.TinkoffClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_ticker_data_for_analysis.return_value = mock_ticker_data
            mock_client_class.return_value = mock_client
            
            result = await analyze_ticker("TEST")
            
            assert isinstance(result, dict)
            assert "success" in result
            assert "ticker" in result


def test_imports():
    """Тест что все необходимые классы и функции можно импортировать."""
    # Проверяем что импорты работают
    assert TechnicalAnalyzer is not None
    assert analyze_ticker is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
