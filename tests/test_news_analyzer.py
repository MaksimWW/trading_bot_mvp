
import pytest
import sys
import os

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from news_analyzer import NewsAnalyzer, get_news_analyzer
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_news_analyzer_init():
    """Тест инициализации NewsAnalyzer."""
    analyzer = NewsAnalyzer()
    assert analyzer is not None


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_get_news_analyzer():
    """Тест получения глобального экземпляра анализатора."""
    analyzer = get_news_analyzer()
    assert analyzer is not None
    assert isinstance(analyzer, NewsAnalyzer)


def test_module_structure():
    """Базовый тест структуры модуля."""
    # Проверяем что файл существует
    module_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'news_analyzer.py')
    assert os.path.exists(module_path), "news_analyzer.py должен существовать"
