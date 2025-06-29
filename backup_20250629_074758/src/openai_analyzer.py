"""
OpenAI Analyzer для анализа тональности финансовых новостей.
"""

import asyncio
import logging
from typing import Dict, List, Optional

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

    async def analyze_sentiment(self, ticker: str, news_list: List[Dict]) -> Optional[Dict]:
        """
        Анализ тональности новостей для торговых решений.

        Args:
            ticker: Тикер акции
            news_list: Список новостей

        Returns:
            Результат анализа или None при ошибке
        """
        if not self.client:
            logger.warning("OpenAI клиент не инициализирован")
            return None

        if not news_list:
            logger.warning(f"Нет новостей для анализа {ticker}")
            return None

        try:
            # Формируем текст новостей для анализа
            news_text = ""
            for i, news in enumerate(news_list[:3], 1):
                title = news.get("title", "Без заголовка")
                content = news.get("content", news.get("summary", "Нет описания"))

                news_text += f"{i}. {title}\n"
                news_text += f"   Содержание: {content[:200]}...\n\n"

            prompt = f"""
Проанализируйте следующие новости о компании {ticker} и определите их влияние на цену акций.

Новости:
{news_text}

Верните результат в формате JSON:
{{
    "sentiment_score": число от -1.0 до +1.0,
    "sentiment_label": "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL",
    "summary": "Краткое объяснение влияния новостей (1-2 предложения)"
}}
"""

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": "Вы - финансовый аналитик российского рынка."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            content = response.choices[0].message.content.strip()

            # Парсим JSON ответ с обработкой ошибок
            import json
            import re

            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Если не JSON, попробуем извлечь JSON из текста
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    # Создаем базовый результат если JSON не найден
                    logger.warning(f"OpenAI вернул не JSON для {ticker}: {content[:100]}")
                    result = {
                        "sentiment_score": 0.0,
                        "sentiment_label": "HOLD",
                        "summary": "Анализ недоступен - некорректный формат ответа",
                    }

            # Валидация результата
            score = max(-1.0, min(1.0, float(result.get("sentiment_score", 0.0))))
            label = result.get("sentiment_label", "HOLD")
            summary = result.get("summary", "Анализ недоступен")

            return {
                "sentiment_score": score,
                "sentiment_label": label,
                "summary": summary,
                "ticker": ticker,
                "analyzed_news_count": len(news_list),
            }

        except Exception as e:
            logger.error(f"Ошибка анализа OpenAI для {ticker}: {e}")
            return None


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
