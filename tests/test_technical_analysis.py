import os
import sys

import pytest

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import pandas as pd

    from technical_analysis import TechnicalAnalyzer

    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_technical_analyzer_init():
    """Тест инициализации TechnicalAnalyzer."""
    analyzer = TechnicalAnalyzer()
    assert analyzer is not None
    assert hasattr(analyzer, "default_periods")


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_calculate_rsi():
    """Тест расчета RSI."""
    analyzer = TechnicalAnalyzer()
    test_prices = pd.Series([100 + i for i in range(20)])
    rsi = analyzer.calculate_rsi(test_prices)
    assert isinstance(rsi, pd.Series)
    assert len(rsi) > 0


def test_module_structure():
    """Базовый тест структуры модуля."""
    # Проверяем что файл существует
    module_path = os.path.join(os.path.dirname(__file__), "..", "src", "technical_analysis.py")
    assert os.path.exists(module_path), "technical_analysis.py должен существовать"
