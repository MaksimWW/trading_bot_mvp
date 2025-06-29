"""
Morning Brief System для торгового бота
Утренний анализ рынка с использованием RSS и существующих компонентов
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import feedparser  # Импорт RSS parser

logger = logging.getLogger(__name__)


@dataclass
class MorningBriefData:
    """Структура данных для утреннего брифинга"""

    date: str
    market_sentiment: float  # -1.0 to 1.0
    top_news: List[Dict[str, Any]]
    technical_signals: Dict[str, Dict[str, Any]]
    trading_recommendations: List[Dict[str, Any]]
    market_overview: str
    risk_alerts: List[str]
    portfolio_status: Optional[Dict[str, Any]] = None


class RSSParser:
    """Асинхронный RSS парсер"""

    def __init__(self, urls: List[str]):
        self.urls = urls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def fetch_feed(self, url: str) -> feedparser.FeedParserDict:
        """Асинхронное получение и парсинг RSS ленты"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, feedparser.parse, url)

    async def get_market_news(self, hours: int) -> List[Dict[str, Any]]:
        """Получение рыночных новостей из RSS лент"""
        news = []
        for url in self.urls:
            feed = await self.fetch_feed(url)
            for entry in feed.entries:
                published_time = datetime(*entry.published_parsed[:6])
                time_diff = datetime.now() - published_time

                if time_diff <= timedelta(hours=hours):
                    news_item = {
                        "title": entry.title,
                        "description": entry.summary,
                        "link": entry.link,
                        "source": url,
                        "published": published_time.isoformat(),
                        "ticker": None,  # Общие рыночные новости
                        "relevance_score": 0.5,
                    }
                    news.append(news_item)
        return news

    async def get_ticker_news(self, ticker: str, hours: int) -> List[Dict[str, Any]]:
        """Получение новостей по конкретному тикеру"""
        # Mock Functionality - Replace with real implementation when available.
        news = []
        # Create some mock news
        news_item_1 = {
            "title": f"Анализ акций {ticker}",
            "description": f"Акции {ticker} показывают признаки роста.",
            "link": "http://example.com/news1",
            "source": "Example News",
            "published": datetime.now().isoformat(),
            "ticker": ticker,
            "relevance_score": 0.7,
        }
        news_item_2 = {
            "title": f"Прогноз для {ticker}",
            "description": f"Эксперты прогнозируют умеренный рост акций {ticker}.",
            "link": "http://example.com/news2",
            "source": "Expert Insights",
            "published": datetime.now().isoformat(),
            "ticker": ticker,
            "relevance_score": 0.6,
        }
        news.append(news_item_1)
        news.append(news_item_2)

        return news


class MorningBriefGenerator:
    """Генератор утренних брифингов для трейдеров"""

    def __init__(self):
        """Инициализация компонентов системы"""
        # Импорты будут добавлены после создания RSS parser
        self.top_tickers = ["SBER", "GAZP", "YNDX", "LKOH", "ROSN"]
        self.overnight_hours = 12  # Анализ за последние 12 часов
        self.rss_urls = [
            "https://www.finanz.ru/rss/news_all.xml",
            "https://www.vedomosti.ru/rss/articles",
        ]
        self.rss_parser = RSSParser(self.rss_urls)

    async def generate_morning_brief(self, user_id: Optional[str] = None) -> MorningBriefData:
        """
        Генерация полного утреннего брифинга

        Args:
            user_id: ID пользователя для персонализации (опционально)

        Returns:
            MorningBriefData: Структурированные данные брифинга
        """
        logger.info("Начинаю генерацию утреннего брифинга...")

        try:
            # Получаем новости за ночь через RSS
            async with self.rss_parser as parser:
                # Получаем общие рыночные новости
                market_news = await parser.get_market_news(self.overnight_hours)

                # Получаем новости по топ тикерам
                ticker_news = []
                for ticker in self.top_tickers:
                    news = await parser.get_ticker_news(ticker, self.overnight_hours)
                    ticker_news.extend(news[:2])  # Топ-2 новости по каждому тикеру

                # Объединяем все новости
                all_news = market_news + ticker_news

                # Рассчитываем общее настроение рынка
                market_sentiment = self._calculate_market_sentiment(all_news)

                # Генерируем технические сигналы (заглушка)
                technical_signals = self._generate_mock_technical_signals()

                # Формируем рекомендации
                recommendations = self._generate_recommendations(all_news, technical_signals)

                # Создаем обзор рынка
                market_overview = self._generate_market_overview(all_news, market_sentiment)

                # Проверяем риски
                risk_alerts = self._check_risk_alerts(all_news, market_sentiment)

                brief_data = MorningBriefData(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    market_sentiment=market_sentiment,
                    top_news=all_news[:10],  # Топ-10 новостей
                    technical_signals=technical_signals,
                    trading_recommendations=recommendations,
                    market_overview=market_overview,
                    risk_alerts=risk_alerts,
                    portfolio_status=None,
                )

                logger.info("Утренний брифинг успешно сгенерирован")
                return brief_data

        except Exception as e:
            logger.error(f"Ошибка генерации утреннего брифинга: {e}")
            raise

    def _calculate_market_sentiment(self, news_list: List[Dict]) -> float:
        """Расчет общего настроения рынка на основе новостей"""
        if not news_list:
            return 0.0

        # Простой расчет на основе ключевых слов
        positive_words = ["рост", "увеличение", "прибыль", "доходы", "успех", "развитие"]
        negative_words = ["падение", "снижение", "убытки", "кризис", "проблемы", "санкции"]

        sentiment_score = 0.0
        for news in news_list:
            text = f"{news.get('title', '')} {news.get('description', '')}".lower()

            for word in positive_words:
                if word in text:
                    sentiment_score += 0.1

            for word in negative_words:
                if word in text:
                    sentiment_score -= 0.1

        # Нормализуем к диапазону [-1, 1]
        max_sentiment = len(news_list) * 0.3
        normalized = sentiment_score / max_sentiment if max_sentiment > 0 else 0
        return max(-1.0, min(1.0, normalized))

    def _generate_mock_technical_signals(self) -> Dict[str, Dict[str, Any]]:
        """Временная заглушка для технических сигналов"""
        signals = {}
        for ticker in self.top_tickers:
            signals[ticker] = {
                "rsi": 50.0,
                "rsi_signal": "NEUTRAL",
                "macd": "NEUTRAL",
                "bollinger": "NEUTRAL",
                "overall_signal": "NEUTRAL",
                "confidence": 0.5,
            }
        return signals

    def _generate_recommendations(
        self, news_list: List[Dict], technical_signals: Dict
    ) -> List[Dict[str, Any]]:
        """Генерация торговых рекомендаций"""
        recommendations = []

        # Анализируем новости по тикерам
        ticker_sentiment = {}
        for news in news_list:
            ticker = news.get("ticker")
            if ticker:
                relevance = news.get("relevance_score", 0)
                if ticker not in ticker_sentiment:
                    ticker_sentiment[ticker] = []
                ticker_sentiment[ticker].append(relevance)

        # Создаем рекомендации для тикеров с новостями
        for ticker, scores in ticker_sentiment.items():
            avg_score = sum(scores) / len(scores) if scores else 0

            if avg_score > 0.3:
                action = "BUY"
                priority = avg_score
            elif avg_score < -0.3:
                action = "SELL"
                priority = abs(avg_score)
            else:
                action = "HOLD"
                priority = 0.1

            recommendations.append(
                {
                    "ticker": ticker,
                    "action": action,
                    "priority": priority,
                    "reasoning": f"Новостной анализ (релевантность: {avg_score:.2f})",
                }
            )

        # Сортируем по приоритету
        recommendations.sort(key=lambda x: x["priority"], reverse=True)
        return recommendations[:5]

    def _generate_market_overview(self, news_list: List[Dict], sentiment: float) -> str:
        """Генерация обзора рынка"""
        news_count = len(news_list)

        if sentiment > 0.2:
            sentiment_text = "позитивным настроем"
        elif sentiment < -0.2:
            sentiment_text = "негативными настроениями"
        else:
            sentiment_text = "нейтральным фоном"

        overview = f"Утренний обзор показывает {sentiment_text} на рынке. "
        overview += (
            f"Проанализировано {news_count} новостей за последние {self.overnight_hours} часов. "
        )

        if news_list:
            top_sources = set([news.get("source", "N/A") for news in news_list[:5]])
            overview += "Основные источники: " + ", ".join(list(top_sources)[:3]) + "."

        return overview

    def _check_risk_alerts(self, news_list: List[Dict], sentiment: float) -> List[str]:
        """Проверка рисковых ситуаций"""
        alerts = []

        if sentiment < -0.5:
            alerts.append("🚨 Крайне негативное настроение рынка")

        if len(news_list) < 3:
            alerts.append("⚠️ Недостаточно данных для анализа")

        # Проверяем наличие критических слов в новостях
        critical_words = ["санкции", "кризис", "обвал", "дефолт"]
        for news in news_list[:5]:
            text = f"{news.get('title', '')} {news.get('description', '')}".lower()
            for word in critical_words:
                if word in text:
                    alerts.append(f"⚠️ Обнаружены упоминания: {word}")
                    break

        return alerts

    async def format_morning_brief_for_telegram(self, brief_data: MorningBriefData) -> str:
        """Форматирование утреннего брифинга для отправки в Telegram"""

        # Эмодзи для настроения рынка
        sentiment_emoji = (
            "📈"
            if brief_data.market_sentiment > 0.2
            else "📉" if brief_data.market_sentiment < -0.2 else "➡️"
        )

        text = f"""🌅 *УТРЕННИЙ БРИФИНГ* - {brief_data.date}

{sentiment_emoji} *Настроение рынка:* {brief_data.market_sentiment:.2f} """

        if brief_data.market_sentiment > 0.2:
            text += "(Позитивное)"
        elif brief_data.market_sentiment < -0.2:
            text += "(Негативное)"
        else:
            text += "(Нейтральное)"

        text += f"\n\n📝 *ОБЗОР:*\n{brief_data.market_overview}"

        if brief_data.risk_alerts:
            text += "\n\n⚠️ *ПРЕДУПРЕЖДЕНИЯ:*\n"
            for alert in brief_data.risk_alerts:
                text += f"• {alert}\n"

        text += f"\n\n🕐 Обновлено: {datetime.now().strftime('%H:%M')}"

        return text


# Удобная функция для получения утреннего брифинга в формате Telegram
async def get_morning_brief_for_telegram(user_id: Optional[str] = None) -> str:
    """Удобная функция для получения утреннего брифинга в формате Telegram"""
    try:
        generator = MorningBriefGenerator()
        brief = await generator.generate_morning_brief(user_id)
        return await generator.format_morning_brief_for_telegram(brief)
    except Exception as e:
        logger.error(f"Ошибка генерации утреннего брифинга: {e}")
        return f"❌ Ошибка генерации утреннего брифинга: {str(e)}"


if __name__ == "__main__":
    # Тестирование системы
    async def test_morning_brief():
        generator = MorningBriefGenerator()
        brief = await generator.generate_morning_brief()
        formatted = await generator.format_morning_brief_for_telegram(brief)
        print(formatted)

    asyncio.run(test_morning_brief())
