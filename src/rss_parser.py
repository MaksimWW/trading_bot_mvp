"""
RSS Parser для торгового бота - резервный источник новостей
Используется как fallback при сбоях Perplexity API
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aiohttp
import feedparser

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """Структура новостного элемента"""

    title: str
    content: str
    url: str
    published: datetime
    source: str
    relevance_score: float = 0.0


class RSSParser:
    """RSS парсер для финансовых новостей"""

    def __init__(self):
        self.session = None
        self.feeds = {
            "investing": [
                "https://ru.investing.com/rss/news.rss",
            ],
            "interfax": [
                "https://www.interfax.ru/rss.asp",
            ],
            "tass": [
                "https://tass.ru/rss/v2.xml",
            ],
            "vedomosti": [
                "https://www.vedomosti.ru/rss/news",
            ],
        }

        # Тикеры для поиска в новостях
        self.russian_tickers = {
            "SBER": ["сбербанк", "sberbank", "сбер"],
            "GAZP": ["газпром", "gazprom"],
            "YNDX": ["яндекс", "yandex"],
            "LKOH": ["лукойл", "lukoil"],
            "ROSN": ["роснефть", "rosneft"],
            "NVTK": ["новатэк", "novatek"],
            "GMKN": ["норникель", "nornickel"],
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "Trading Bot RSS Parser 1.0"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        """Получение RSS ленты с retry логикой"""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

            async with self.session.get(url, headers=headers, ssl=False) as response:
                if response.status == 200:
                    content = await response.text()
                    parsed_feed = feedparser.parse(content)

                    if hasattr(parsed_feed, "entries") and len(parsed_feed.entries) > 0:
                        return parsed_feed
                    else:
                        logger.warning(f"Empty or invalid feed: {url}")
                        return None
                else:
                    logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {e}")
            return None

    def extract_ticker_relevance(self, text: str, ticker: str) -> float:
        """Определение релевантности новости для тикера"""
        if not text or not ticker:
            return 0.0

        text_lower = text.lower()
        keywords = self.russian_tickers.get(ticker, [ticker.lower()])

        relevance = 0.0
        for keyword in keywords:
            mentions = len(re.findall(rf"\b{re.escape(keyword)}\b", text_lower))
            relevance += mentions * 0.3

            if keyword in text[:100].lower():
                relevance += 0.5

        return min(relevance, 1.0)

    async def get_ticker_news(self, ticker: str, hours_back: int = 24) -> List[NewsItem]:
        """Получение новостей по тикеру из всех источников"""
        all_news = []

        for source, urls in self.feeds.items():
            source_news = await self._get_news_from_source(source, urls, ticker, hours_back)
            all_news.extend(source_news)

        # Сортировка по релевантности
        all_news.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_news[:10]

    async def _get_news_from_source(
        self, source: str, urls: List[str], ticker: str, hours_back: int
    ) -> List[NewsItem]:
        """Получение новостей из конкретного источника"""
        news_items = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        for feed_url in urls:
            try:
                feed = await self.fetch_feed(feed_url)
                if not feed:
                    continue

                for entry in feed.entries[:20]:
                    news_item = self._process_feed_entry(entry, source, ticker, cutoff_time)
                    if news_item:
                        news_items.append(news_item)

            except Exception as e:
                logger.error(f"Error parsing feed {feed_url}: {e}")

        return news_items

    def _process_feed_entry(
        self, entry, source: str, ticker: str, cutoff_time: datetime
    ) -> Optional[NewsItem]:
        """Обработка одной записи из RSS ленты"""
        title = getattr(entry, "title", "")
        summary = getattr(entry, "summary", "")
        link = getattr(entry, "link", "")
        published_str = getattr(entry, "published", "")

        # Парсинг даты
        try:
            published = feedparser._parse_date(published_str)
            if published:
                published = datetime(*published[:6])
            else:
                published = datetime.now()
        except Exception:
            published = datetime.now()

        if published < cutoff_time:
            return None

        full_text = f"{title} {summary}"
        relevance = self.extract_ticker_relevance(full_text, ticker)

        if relevance > 0.05 or any(
            keyword in full_text.lower() for keyword in ["акции", "биржа", "рынок", "торги"]
        ):
            return NewsItem(
                title=title[:200],
                content=summary[:500],
                url=link,
                published=published,
                source=source,
                relevance_score=relevance,
            )

        return None

    async def test_connection(self) -> Dict[str, bool]:
        """Тестирование доступности RSS источников"""
        results = {}

        for source, urls in self.feeds.items():
            source_available = False
            for url in urls:
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            source_available = True
                            break
                except Exception:
                    continue
            results[source] = source_available

        return results


# Тестирование RSS парсера
async def main():
    """Тестирование RSS парсера"""
    async with RSSParser() as parser:
        print("🧪 Тестирование RSS парсера...")

        # Проверка доступности источников
        print("\n📡 Проверка доступности:")
        status = await parser.test_connection()
        for source, available in status.items():
            icon = "✅" if available else "❌"
            print(f"{icon} {source}")

        # Тест получения новостей
        print("\n📰 Тест новостей по SBER:")
        news = await parser.get_ticker_news("SBER", 48)
        print(f"Найдено: {len(news)} новостей")

        for item in news[:3]:
            print(f"- [{item.source}] {item.title} (релевантность: {item.relevance_score:.2f})")


if __name__ == "__main__":
    asyncio.run(main())
