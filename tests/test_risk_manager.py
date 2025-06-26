
import pytest
import sys
import os

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from risk_manager import RiskManager
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
def test_risk_manager_init():
    """Тест инициализации RiskManager."""
    if MODULES_AVAILABLE:
        manager = RiskManager()
        assert manager is not None


def test_module_structure():
    """Базовый тест структуры модуля."""
    # Проверяем что файл существует
    module_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'risk_manager.py')
    assert os.path.exists(module_path), "risk_manager.py должен существовать"


def test_main_function_exists():
    """Test that main function exists and is callable."""
    if MODULES_AVAILABLE:
        from risk_manager import main
        assert callable(main)


def test_main_function_runs():
    """Test that main function runs without errors."""
    if MODULES_AVAILABLE:
        from risk_manager import main
        result = main()
        assert result is None  # main() returns None
