"""
RSS Parser для торгового бота
Поддержка российских финансовых источников
"""

import asyncio
import html
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import feedparser

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """Структура новостного элемента"""

    title: str
    description: str
    link: str
    published: str
    published_parsed: Optional[datetime]
    source: str
    ticker: Optional[str] = None
    sentiment: Optional[float] = None
    relevance_score: float = 0.0


class RSSParser:
    """RSS Parser с поддержкой множественных источников"""

    def __init__(self):
        """Инициализация RSS парсера"""
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=30)

        # Конфигурация рабочих RSS источников
        self.rss_sources = {
            "interfax": {
                "name": "Интерфакс",
                "urls": [
                    "https://www.interfax.ru/rss.asp",
                ],
                "encoding": "utf-8",
            },
            "tass": {
                "name": "ТАСС",
                "urls": [
                    "https://tass.ru/rss/v2.xml",
                ],
                "encoding": "utf-8",
            },
            "vedomosti": {
                "name": "Ведомости",
                "urls": [
                    "https://www.vedomosti.ru/rss/news",
                ],
                "encoding": "utf-8",
            },
            "investing": {
                "name": "Investing.com",
                "urls": [
                    "https://ru.investing.com/rss/news.rss",
                ],
                "encoding": "utf-8",
            },
        }

        # Маппинг тикеров к поисковым терминам
        self.ticker_keywords = {
            "SBER": ["сбербанк", "sberbank", "sber", "сбер"],
            "GAZP": ["газпром", "gazprom", "газ"],
            "YNDX": ["яндекс", "yandex", "yndx"],
            "LKOH": ["лукойл", "lukoil", "нефть"],
            "ROSN": ["роснефть", "rosneft", "нефть"],
        }

        # Кеш для новостей
        self.news_cache = {}
        self.cache_ttl = 1800  # 30 минут

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def check_sources_availability(self):
        """Проверка доступности RSS источников"""
        print("🧪 Тестирование RSS парсера...")
        print("📡 Проверка доступности:")

        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        working_sources = 0
        for source_key, source_config in self.rss_sources.items():
            try:
                url = source_config["urls"][0]  # Проверяем первый URL
                async with self.session.get(url) as response:
                    if response.status == 200:
                        print(f"✅ {source_key}")
                        working_sources += 1
                    else:
                        print(f"❌ {source_key} (HTTP {response.status})")
            except Exception as e:
                print(f"❌ {source_key} (Ошибка: {str(e)[:50]})")

        print(f"📊 Работает источников: {working_sources}/{len(self.rss_sources)}")
        return working_sources

    async def get_ticker_news(self, ticker: str, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Получение новостей по конкретному тикеру"""
        try:
            cache_key = f"{ticker}_{hours_back}"
            if self._is_cache_valid(cache_key):
                logger.info(f"Возвращаем новости {ticker} из кеша")
                return self.news_cache[cache_key]["data"]

            if not self.session:
                self.session = aiohttp.ClientSession(timeout=self.timeout)

            all_news = await self._fetch_all_news(hours_back)
            ticker_news = self._filter_news_by_ticker(all_news, ticker)

            self.news_cache[cache_key] = {"data": ticker_news, "timestamp": datetime.now()}

            logger.info(f"Найдено {len(ticker_news)} новостей для {ticker}")
            return ticker_news

        except Exception as e:
            logger.error(f"Ошибка получения новостей для {ticker}: {e}")
            return []

    async def get_market_news(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Получение общих рыночных новостей"""
        try:
            cache_key = f"market_{hours_back}"
            if self._is_cache_valid(cache_key):
                return self.news_cache[cache_key]["data"]

            if not self.session:
                self.session = aiohttp.ClientSession(timeout=self.timeout)

            all_news = await self._fetch_all_news(hours_back)
            market_news = self._filter_market_news(all_news)

            self.news_cache[cache_key] = {"data": market_news, "timestamp": datetime.now()}

            logger.info(f"Найдено {len(market_news)} рыночных новостей")
            return market_news

        except Exception as e:
            logger.error(f"Ошибка получения рыночных новостей: {e}")
            return []

    async def _fetch_all_news(self, hours_back: int) -> List[NewsItem]:
        """Получение новостей из всех источников"""
        all_news = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        tasks = []
        for source_key, source_config in self.rss_sources.items():
            for url in source_config["urls"]:
                task = self._fetch_source_news(url, source_config["name"], cutoff_time)
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Ошибка получения новостей: {result}")

        all_news.sort(key=lambda x: x.published_parsed or datetime.min, reverse=True)
        return all_news

    async def _fetch_source_news(
        self, url: str, source_name: str, cutoff_time: datetime
    ) -> List[NewsItem]:
        """Получение новостей из одного RSS источника"""
        try:
            response_data = await self._get_rss_response(url)
            if not response_data:
                return []

            return self._parse_rss_entries(response_data, source_name, cutoff_time)

        except asyncio.TimeoutError:
            logger.warning(f"Таймаут для {url}")
            return []
        except Exception as e:
            logger.error(f"Ошибка получения RSS {url}: {e}")
            return []

    async def _get_rss_response(self, url: str) -> Optional[str]:
        """Получение RSS контента"""
        async with self.session.get(url) as response:
            if response.status != 200:
                logger.warning(f"HTTP {response.status} для {url}")
                return None
            return await response.text()

    def _parse_rss_entries(
        self, content: str, source_name: str, cutoff_time: datetime
    ) -> List[NewsItem]:
        """Парсинг RSS записей"""
        feed = feedparser.parse(content)

        if not feed.entries:
            logger.warning(f"Нет записей в RSS для {source_name}")
            return []

        news_items = []
        for entry in feed.entries:
            try:
                news_item = self._create_news_item(entry, source_name)
                if news_item:
                    news_items.append(news_item)
            except Exception as e:
                logger.warning(f"Ошибка парсинга записи RSS: {e}")
                continue

        logger.info(f"Получено {len(news_items)} новостей из {source_name}")
        return news_items[:20]

    def _create_news_item(self, entry, source_name: str) -> Optional[NewsItem]:
        """Создание объекта новости из RSS записи"""
        published_dt = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published_dt = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            published_dt = datetime(*entry.updated_parsed[:6])

        return NewsItem(
            title=self._clean_text(entry.get("title", "")),
            description=self._clean_text(entry.get("description", "") or entry.get("summary", "")),
            link=entry.get("link", ""),
            published=entry.get("published", ""),
            published_parsed=published_dt,
            source=source_name,
        )

    def _filter_news_by_ticker(
        self, news_list: List[NewsItem], ticker: str
    ) -> List[Dict[str, Any]]:
        """Фильтрация новостей по тикеру"""
        keywords = self.ticker_keywords.get(ticker.upper(), [ticker.lower()])
        filtered_news = []

        for news in news_list:
            relevance_score = self._calculate_relevance(news, keywords)

            if relevance_score > 0.1:
                news_dict = asdict(news)
                news_dict["relevance_score"] = relevance_score
                news_dict["ticker"] = ticker
                filtered_news.append(news_dict)

        filtered_news.sort(key=lambda x: x["relevance_score"], reverse=True)
        return filtered_news

    def _filter_market_news(self, news_list: List[NewsItem]) -> List[Dict[str, Any]]:
        """Фильтрация общерыночных новостей"""
        market_keywords = [
            "рынок",
            "биржа",
            "торги",
            "индекс",
            "ртс",
            "ммвб",
            "moex",
            "экономика",
            "инфляция",
            "цб",
            "центробанк",
            "ставка",
            "рубль",
            "нефть",
            "газ",
            "доллар",
            "евро",
            "санкции",
            "инвестиции",
            "акции",
        ]

        market_news = []
        for news in news_list:
            relevance_score = self._calculate_relevance(news, market_keywords)

            if relevance_score > 0.05:
                news_dict = asdict(news)
                news_dict["relevance_score"] = relevance_score
                market_news.append(news_dict)

        market_news.sort(key=lambda x: x["relevance_score"], reverse=True)
        return market_news[:10]  # Топ-10 рыночных новостей

    def _calculate_relevance(self, news: NewsItem, keywords: List[str]) -> float:
        """Расчет релевантности новости"""
        score = 0.0
        for keyword in keywords:
            keyword_lower = keyword.lower()

            if keyword_lower in news.title.lower():
                score += 0.5

            if keyword_lower in news.description.lower():
                score += 0.3

        return min(score, 1.0)

    def _clean_text(self, text: str) -> str:
        """Очистка текста от HTML тегов и лишних символов"""
        if not text:
            return ""

        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = html.unescape(text)

        return text

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Проверка валидности кеша"""
        if cache_key not in self.news_cache:
            return False

        cached_time = self.news_cache[cache_key]["timestamp"]
        return (datetime.now() - cached_time).seconds < self.cache_ttl

    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()


if __name__ == "__main__":

    async def test_rss_parser():
        async with RSSParser() as parser:
            working_count = await parser.check_sources_availability()

            if working_count > 0:
                print("\n📰 Тест новостей по SBER:")
                sber_news = await parser.get_ticker_news("SBER", 24)
                print(f"Найдено: {len(sber_news)} новостей")

                for i, news in enumerate(sber_news[:2]):
                    title = news["title"][:50] + "..." if len(news["title"]) > 50 else news["title"]
                    print(f"{i+1}. {title} (Релевантность: {news['relevance_score']:.2f})")

                print("\n📈 Тест рыночных новостей:")
                market_news = await parser.get_market_news(12)
                print(f"Найдено: {len(market_news)} новостей")

                for i, news in enumerate(market_news[:3]):
                    title = news["title"][:50] + "..." if len(news["title"]) > 50 else news["title"]
                    print(f"{i+1}. {title} (Источник: {news['source']})")
            else:
                print("❌ Нет рабочих RSS источников")

    asyncio.run(test_rss_parser())
