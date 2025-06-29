import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from rss_parser import RSSParser

logger = logging.getLogger(__name__)


class NewsAnalyzerWithFallback:
    """Анализатор новостей с RSS fallback"""

    def __init__(self):
        self.rss_parser = None
        self.cache = {}
        self.cache_ttl = 3600
        self.stats = {"rss_fallback_used": 0, "cache_used": 0, "last_fallback_time": None}

    async def _init_rss_parser(self):
        """Инициализация RSS парсера"""
        if not self.rss_parser:
            self.rss_parser = RSSParser()
            await self.rss_parser.__aenter__()

    async def _cleanup_rss_parser(self):
        """Очистка RSS парсера"""
        if self.rss_parser:
            await self.rss_parser.__aexit__(None, None, None)
            self.rss_parser = None

    def _get_cache_key(self, ticker: str, hours_back: int) -> str:
        """Генерация ключа кеша"""
        return f"news_{ticker}_{hours_back}_{int(time.time() // 1800)}"

    async def get_ticker_news_rss(self, ticker: str, hours_back: int = 24) -> List[Dict]:
        """Получение новостей через RSS"""
        try:
            logger.info(f"📡 Trying RSS fallback for {ticker}")

            await self._init_rss_parser()
            news_items = await self.rss_parser.get_ticker_news(ticker, hours_back)

            if news_items:
                news_data = [
                    {
                        "title": item.title,
                        "content": item.content,
                        "url": item.url,
                        "published": item.published.isoformat(),
                        "source": f"RSS_{item.source}",
                        "relevance_score": item.relevance_score,
                    }
                    for item in news_items
                ]

                self.stats["rss_fallback_used"] += 1
                self.stats["last_fallback_time"] = datetime.now().isoformat()

                logger.info(f"✅ RSS success: {len(news_data)} articles found")
                return news_data
            else:
                logger.warning(f"⚠️ RSS returned empty results for {ticker}")
                return []

        except Exception as e:
            logger.error(f"❌ RSS error for {ticker}: {e}")
            return []
        finally:
            await self._cleanup_rss_parser()

    async def analyze_ticker_news(self, ticker: str, hours_back: int = 24) -> Dict:
        """Анализ новостей по тикеру с RSS fallback"""
        start_time = time.time()

        try:
            # Получение новостей через RSS
            news_data = await self.get_ticker_news_rss(ticker, hours_back)

            if not news_data:
                return {
                    "ticker": ticker,
                    "sentiment_score": 0.0,
                    "sentiment_label": "NEUTRAL",
                    "news_count": 0,
                    "news_summary": "Новости не найдены",
                    "data_source": "rss",
                    "analysis_time": time.time() - start_time,
                    "reliability": "LOW",
                    "error": "No news found",
                }

            # Простой анализ настроения на основе ключевых слов
            positive_words = ["рост", "прибыль", "увеличение", "положительный", "успех", "развитие"]
            negative_words = ["падение", "убыток", "снижение", "кризис", "проблемы", "риск"]

            sentiment_score = 0.0
            total_words = 0

            for news in news_data:
                text = f"{news['title']} {news['content']}".lower()

                pos_count = sum(1 for word in positive_words if word in text)
                neg_count = sum(1 for word in negative_words if word in text)

                sentiment_score += (pos_count - neg_count) * 0.1
                total_words += len(text.split())

            # Нормализация
            if total_words > 0:
                sentiment_score = max(-1.0, min(1.0, sentiment_score))

            # Определение метки
            if sentiment_score > 0.3:
                sentiment_label = "BUY"
            elif sentiment_score < -0.3:
                sentiment_label = "SELL"
            else:
                sentiment_label = "HOLD"

            analysis_time = time.time() - start_time

            result = {
                "ticker": ticker,
                "sentiment_score": sentiment_score,
                "sentiment_label": sentiment_label,
                "news_count": len(news_data),
                "news_summary": f"Найдено {len(news_data)} новостей через RSS",
                "data_source": "rss",
                "analysis_time": analysis_time,
                "reliability": "MEDIUM" if len(news_data) > 2 else "LOW",
                "fallback_used": True,
            }

            logger.info(
                f"✅ RSS Analysis complete for {ticker}: {sentiment_label} ({sentiment_score:.2f})"
            )
            return result

        except Exception as e:
            logger.error(f"❌ RSS Analysis failed for {ticker}: {e}")
            return {
                "ticker": ticker,
                "sentiment_score": 0.0,
                "sentiment_label": "ERROR",
                "news_count": 0,
                "news_summary": f"Ошибка анализа: {str(e)}",
                "data_source": "error",
                "analysis_time": time.time() - start_time,
                "reliability": "NONE",
                "error": str(e),
            }

    def format_telegram_response(self, analysis_result: Dict) -> str:
        """Форматирование результата для Telegram"""
        ticker = analysis_result["ticker"]
        sentiment = analysis_result["sentiment_label"]
        score = analysis_result["sentiment_score"]
        news_count = analysis_result["news_count"]
        reliability = analysis_result["reliability"]

        sentiment_emoji = {"BUY": "📈", "SELL": "📉", "HOLD": "➡️", "ERROR": "❌"}.get(
            sentiment, "❓"
        )

        reliability_emoji = {"MEDIUM": "🟡", "LOW": "🟠", "NONE": "⚫"}.get(reliability, "❓")

        message = f"📰 АНАЛИЗ НОВОСТЕЙ: {ticker} (RSS)\n\n"
        message += f"{sentiment_emoji} Настроение: {sentiment}\n"
        message += f"📊 Сила сигнала: {score:+.2f}\n"
        message += f"📈 Новостей: {news_count}\n"
        message += f"{reliability_emoji} Надежность: {reliability}\n"
        message += f"📡 Источник: RSS резерв\n\n"
        message += f"💬 {analysis_result.get('news_summary', 'Резюме недоступно')}\n\n"
        message += "⚠️ Использован резервный RSS источник"

        return message


# Функция совместимости
async def get_news_analyzer():
    """Фабричная функция для создания анализатора"""
    return NewsAnalyzerWithFallback()


# Тестирование
async def main():
    analyzer = NewsAnalyzerWithFallback()
    result = await analyzer.analyze_ticker_news("SBER")
    print(analyzer.format_telegram_response(result))


if __name__ == "__main__":
    asyncio.run(main())
