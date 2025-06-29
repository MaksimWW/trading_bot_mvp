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

    async def check_sources_availability(self):
        """Проверка доступности RSS источников"""
        print("🧪 Тестирование RSS парсера...")
        print("📡 Проверка доступности:")

        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        for source_key, source_config in self.rss_sources.items():
            try:
                url = source_config['urls'][0]  # Проверяем первый URL
                async with self.session.get(url) as response:
                    if response.status == 200:
                        print(f"✅ {source_key}")
                    else:
                        print(f"❌ {source_key} (HTTP {response.status})")
            except Exception as e:
                print(f"❌ {source_key} (Ошибка: {str(e)[:50]})")

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
"""
RSS Parser для торгового бота
Поддержка российских финансовых источников
"""

import asyncio
import aiohttp
import feedparser
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import re
import html

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

        # Конфигурация RSS источников
        self.rss_sources = {
            'rbc': {
                'name': 'РБК',
                'urls': [
                    'https://rssexport.rbc.ru/rbcnews/news/20/full.rss',
                ],
                'encoding': 'utf-8'
            },
            'finam': {
                'name': 'Финам',
                'urls': [
                    'https://www.finam.ru/net/analysis/conews/rsspoint',
                ],
                'encoding': 'utf-8'
            },
        }

        # Маппинг тикеров к поисковым терминам
        self.ticker_keywords = {
            'SBER': ['сбербанк', 'sberbank', 'sber', 'сбер'],
            'GAZP': ['газпром', 'gazprom', 'газ'],
            'YNDX': ['яндекс', 'yandex', 'yndx'],
            'LKOH': ['лукойл', 'lukoil', 'нефть'],
            'ROSN': ['роснефть', 'rosneft', 'нефть'],
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

        for source_key, source_config in self.rss_sources.items():
            try:
                url = source_config['urls'][0]  # Проверяем первый URL
                async with self.session.get(url) as response:
                    if response.status == 200:
                        print(f"✅ {source_key}")
                    else:
                        print(f"❌ {source_key} (HTTP {response.status})")
            except Exception as e:
                print(f"❌ {source_key} (Ошибка: {str(e)[:50]})")

    async def get_ticker_news(self, ticker: str, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Получение новостей по конкретному тикеру
        """
        try:
            # Проверяем кеш
            cache_key = f"{ticker}_{hours_back}"
            if self._is_cache_valid(cache_key):
                logger.info(f"Возвращаем новости {ticker} из кеша")
                return self.news_cache[cache_key]['data']

            if not self.session:
                self.session = aiohttp.ClientSession(timeout=self.timeout)

            # Получаем все новости
            all_news = await self._fetch_all_news(hours_back)

            # Фильтруем по тикеру
            ticker_news = self._filter_news_by_ticker(all_news, ticker)

            # Кешируем результат
            self.news_cache[cache_key] = {
                'data': ticker_news,
                'timestamp': datetime.now()
            }

            logger.info(f"Найдено {len(ticker_news)} новостей для {ticker}")
            return ticker_news

        except Exception as e:
            logger.error(f"Ошибка получения новостей для {ticker}: {e}")
            return []

    async def get_market_news(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Получение общих рыночных новостей
        """
        try:
            cache_key = f"market_{hours_back}"
            if self._is_cache_valid(cache_key):
                return self.news_cache[cache_key]['data']

            if not self.session:
                self.session = aiohttp.ClientSession(timeout=self.timeout)

            all_news = await self._fetch_all_news(hours_back)

            # Фильтруем общерыночные новости
            market_news = self._filter_market_news(all_news)

            self.news_cache[cache_key] = {
                'data': market_news,
                'timestamp': datetime.now()
            }

            logger.info(f"Найдено {len(market_news)} рыночных новостей")
            return market_news

        except Exception as e:
            logger.error(f"Ошибка получения рыночных новостей: {e}")
            return []

    async def _fetch_all_news(self, hours_back: int) -> List[NewsItem]:
        """Получение новостей из всех источников"""
        all_news = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        # Собираем задачи для параллельного выполнения
        tasks = []
        for source_key, source_config in self.rss_sources.items():
            for url in source_config['urls']:
                task = self._fetch_source_news(url, source_config['name'], cutoff_time)
                tasks.append(task)

        # Выполняем все запросы параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Обрабатываем результаты
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Ошибка получения новостей: {result}")

        # Сортируем по времени публикации
        all_news.sort(key=lambda x: x.published_parsed or datetime.min, reverse=True)

        return all_news

    async def _fetch_source_news(self, url: str, source_name: str, cutoff_time: datetime) -> List[NewsItem]:
        """Получение новостей из одного RSS источника"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} для {url}")
                    return []

                content = await response.text()

                # Парсим RSS
                feed = feedparser.parse(content)

                if not feed.entries:
                    logger.warning(f"Нет записей в RSS {url}")
                    return []

                news_items = []
                for entry in feed.entries:
                    try:
                        # Парсим дату публикации
                        published_dt = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published_dt = datetime(*entry.published_parsed[:6])
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            published_dt = datetime(*entry.updated_parsed[:6])

                        # Пропускаем старые новости
                        if published_dt and published_dt < cutoff_time:
                            continue

                        # Создаем объект новости
                        news_item = NewsItem(
                            title=self._clean_text(entry.get('title', '')),
                            description=self._clean_text(entry.get('description', '') or entry.get('summary', '')),
                            link=entry.get('link', ''),
                            published=entry.get('published', ''),
                            published_parsed=published_dt,
                            source=source_name
                        )

                        news_items.append(news_item)

                    except Exception as e:
                        logger.warning(f"Ошибка парсинга записи RSS: {e}")
                        continue

                logger.info(f"Получено {len(news_items)} новостей из {source_name}")
                return news_items

        except asyncio.TimeoutError:
            logger.warning(f"Таймаут для {url}")
            return []
        except Exception as e:
            logger.error(f"Ошибка получения RSS {url}: {e}")
            return []

    def _filter_news_by_ticker(self, news_list: List[NewsItem], ticker: str) -> List[Dict[str, Any]]:
        """Фильтрация новостей по тикеру"""
        keywords = self.ticker_keywords.get(ticker.upper(), [ticker.lower()])
        filtered_news = []

        for news in news_list:
            relevance_score = self._calculate_relevance(news, keywords)

            if relevance_score > 0.1:  # Порог релевантности
                news_dict = asdict(news)
                news_dict['relevance_score'] = relevance_score
                news_dict['ticker'] = ticker
                filtered_news.append(news_dict)

        # Сортируем по релевантности
        filtered_news.sort(key=lambda x: x['relevance_score'], reverse=True)
        return filtered_news

    def _filter_market_news(self, news_list: List[NewsItem]) -> List[Dict[str, Any]]:
        """Фильтрация общерыночных новостей"""
        market_keywords = [
            'рынок', 'биржа', 'торги', 'индекс', 'ртс', 'ммвб', 'moex',
            'экономика', 'инфляция', 'цб', 'центробанк', 'ставка', 'рубль',
            'нефть', 'газ', 'доллар', 'евро', 'санкции', 'инвестиции'
        ]

        market_news = []
        for news in news_list:
            relevance_score = self._calculate_relevance(news, market_keywords)

            if relevance_score > 0.05:  # Более низкий порог для рыночных новостей
                news_dict = asdict(news)
                news_dict['relevance_score'] = relevance_score
                market_news.append(news_dict)

        market_news.sort(key=lambda x: x['relevance_score'], reverse=True)
        return market_news

    def _calculate_relevance(self, news: NewsItem, keywords: List[str]) -> float:
        """Расчет релевантности новости"""
        text = f"{news.title} {news.description}".lower()

        score = 0.0
        for keyword in keywords:
            keyword_lower = keyword.lower()

            # Проверяем заголовок (высокий вес)
            if keyword_lower in news.title.lower():
                score += 0.5

            # Проверяем описание (средний вес)
            if keyword_lower in news.description.lower():
                score += 0.3

        return min(score, 1.0)  # Ограничиваем максимальным значением 1.0

    def _clean_text(self, text: str) -> str:
        """Очистка текста от HTML тегов и лишних символов"""
        if not text:
            return ""

        # Удаляем HTML теги
        text = re.sub(r'<[^>]+>', '', text)

        # Удаляем лишние пробелы
        text = re.sub(r'\s+', ' ', text).strip()

        # Декодируем HTML entities
        text = html.unescape(text)

        return text

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Проверка валидности кеша"""
        if cache_key not in self.news_cache:
            return False

        cached_time = self.news_cache[cache_key]['timestamp']
        return (datetime.now() - cached_time).seconds < self.cache_ttl

    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()

if __name__ == "__main__":
    # Тестирование RSS парсера
    async def test_rss_parser():
        async with RSSParser() as parser:
            await parser.check_sources_availability()

            print("📰 Тест новостей по SBER:")
            sber_news = await parser.get_ticker_news("SBER", 24)
            print(f"Найдено: {len(sber_news)} новостей")

            for i, news in enumerate(sber_news[:2]):
                title = news['title'][:50] + "..." if len(news['title']) > 50 else news['title']
                print(f"{i+1}. {title} (Релевантность: {news['relevance_score']:.2f})")

            print("\n📈 Тест рыночных новостей:")
            market_news = await parser.get_market_news(12)
            print(f"Найдено: {len(market_news)} новостей")

            for i, news in enumerate(market_news[:2]):
                title = news['title'][:50] + "..." if len(news['title']) > 50 else news['title']
                print(f"{i+1}. {title} (Источник: {news['source']})")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_rss_parser())