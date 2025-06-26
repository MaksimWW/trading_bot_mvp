
"""
OpenAI Analyzer для анализа тональности финансовых новостей.
"""

import logging

try:
    import openai
    from openai import OpenAI
except ImportError:
    openai = None
    OpenAI = None

from config import OPENAI_API_KEY


logger = logging.getLogger(__name__)


class OpenAIAnalyzer:
    """Анализатор тональности новостей с использованием OpenAI GPT-4."""

    def __init__(self, api_key: str = None):
        """Инициализация OpenAI клиента."""
        if not openai or not OpenAI:
            raise ImportError("Установите openai библиотеку: pip install openai")

        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API ключ не найден")

        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4"
        self.max_tokens = 500
        self.temperature = 0.3

        logger.info("OpenAI Analyzer инициализирован")


def main():
    """Функция для тестирования модуля."""
    print("🧪 Тестирование OpenAI Analyzer...")
    try:
        OpenAIAnalyzer()
        print("✅ OpenAI Analyzer успешно инициализирован")
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")


if __name__ == "__main__":
    main()
