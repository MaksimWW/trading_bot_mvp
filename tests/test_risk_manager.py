"""Test module for risk manager functionality."""

from src.risk_manager import main


def test_main_function_exists():
    """Test that main function exists and is callable."""
    assert callable(main)


def test_main_function_runs():
    """Test that main function runs without errors."""
    result = main()
    assert result is None  # main() returns None
