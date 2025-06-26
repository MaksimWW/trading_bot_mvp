
"""
Клиент для работы с Perplexity API
Поиск финансовых новостей в реальном времени
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerplexityError(Exception):
    """Кастомное исключение для ошибок Perplexity API"""
    pass


class PerplexityClient:
    """Клиент для работы с Perplexity API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация клиента

        Args:
            api_key: API ключ Perplexity (если не указан, берется из переменных окружения)
        """
        import os

        # Используем переданный ключ или берем из окружения
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")

        if not self.api_key:
            raise ValueError("API ключ Perplexity не найден. Установите PERPLEXITY_API_KEY")

        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar"
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 1

        # Поддерживаемые тикеры
        self.supported_tickers = {
            'SBER': 'Сбербанк Сбер',
            'GAZP': 'Газпром',
            'YNDX': 'Яндекс Yandex',
            'LKOH': 'Лукойл',
            'NVTK': 'Новатэк',
            'ROSN': 'Роснефть',
            'MGNT': 'Магнит',
            'MTSS': 'МТС',
            'AFLT': 'Аэрофлот'
        }

        logger.info("PerplexityClient инициализирован")

    def search_ticker_news(self, ticker: str, hours: int = 24) -> List[Dict]:
        """
        Поиск новостей по тикеру за последние N часов

        Args:
            ticker: Тикер акции (например, SBER, GAZP, YNDX)
            hours: Количество часов для поиска (по умолчанию 24)

        Returns:
            Список словарей с новостями в формате:
            {
                "title": str,
                "content": str,
                "source": str,
                "url": str,
                "timestamp": str,
                "type": str
            }
        """
        if not ticker:
            raise ValueError("Тикер не может быть пустым")

        ticker_upper = ticker.upper()
        if ticker_upper not in self.supported_tickers:
            logger.warning(f"Тикер {ticker_upper} не в списке поддерживаемых")

        logger.info(f"Поиск новостей для тикера {ticker_upper} за последние {hours} часов")

        query = self._build_search_query(ticker_upper, hours)

        for attempt in range(self.max_retries):
            try:
                response = self._make_request(query)
                news_data = self._parse_response(response, ticker_upper)

                logger.info(f"Найдено {len(news_data)} новостей для {ticker_upper}")
                return news_data

            except PerplexityError as e:
                logger.warning(f"Попытка {attempt + 1}/{self.max_retries} не удалась: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Увеличиваем задержку
                else:
                    logger.error(f"Все попытки исчерпаны для {ticker_upper}")
                    raise

        return []

    def _build_search_query(self, ticker: str, hours: int) -> str:
        """
        Построение оптимального поискового запроса

        Args:
            ticker: Тикер акции
            hours: Количество часов

        Returns:
            Поисковый запрос
        """
        company = self.supported_tickers.get(ticker, ticker)

        query = f"""
        Найди последние финансовые новости за {hours} часов о компании {company} ({ticker}).
        Интересуют: финансовые результаты, котировки акций, важные корпоративные события,
        слияния и поглощения, регуляторные решения, аналитические прогнозы.
        Фокус на российском рынке, но включи международные новости если они влияют на компанию.
        Предоставь конкретные источники и ссылки.
        """

        logger.debug(f"Построен запрос для {ticker}: {query[:100]}...")
        return query

    def _prepare_headers(self) -> Dict[str, str]:
        """Подготовка заголовков для запроса"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _prepare_payload(self, query: str) -> Dict:
        """Подготовка данных для запроса"""
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ],
            "return_citations": True,
            "temperature": 0.1,
            "max_tokens": 2000
        }

    def _handle_response_errors(self, response) -> None:
        """Обработка ошибок ответа API"""
        if response.status_code == 401:
            raise PerplexityError("❌ Неверный API ключ Perplexity (401)")
        elif response.status_code == 429:
            raise PerplexityError("⏰ Превышен лимит запросов Perplexity API (429)")
        elif response.status_code >= 400:
            error_msg = f"Ошибка API {response.status_code}"
            try:
                error_detail = response.json().get("error", {}).get("message", response.text)
                error_msg += f": {error_detail}"
            except Exception:
                error_msg += f": {response.text}"
            raise PerplexityError(error_msg)

    def _make_request(self, query: str) -> Dict:
        """
        Выполнение запроса к Perplexity API

        Args:
            query: Поисковый запрос

        Returns:
            Ответ API в формате словаря

        Raises:
            PerplexityError: При ошибках API
        """
        headers = self._prepare_headers()
        payload = self._prepare_payload(query)

        try:
            logger.debug(f"Отправка запроса к {self.base_url}/chat/completions")

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            self._handle_response_errors(response)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            raise PerplexityError(f"⏰ Таймаут запроса ({self.timeout}s)")
        except requests.exceptions.ConnectionError:
            raise PerplexityError("🌐 Ошибка подключения к Perplexity API")
        except requests.exceptions.RequestException as e:
            raise PerplexityError(f"📡 Ошибка запроса: {str(e)}")
        except json.JSONDecodeError:
            raise PerplexityError("📄 Некорректный JSON ответ от API")

    def _parse_response(self, response: Dict, ticker: str) -> List[Dict]:
        """
        Парсинг ответа Perplexity API в унифицированный формат

        Args:
            response: Ответ от API
            ticker: Тикер для которого искали новости

        Returns:
            Список новостей в унифицированном формате
        """
        try:
            # Извлекаем основной контент
            choices = response.get("choices", [])
            if not choices:
                logger.warning("Пустой список choices в ответе")
                return []

            message = choices[0].get("message", {})
            content = message.get("content", "")
            citations = response.get("citations", [])

            if not content:
                logger.warning("Пустой контент в ответе Perplexity")
                return []

            news_items = []
            current_time = datetime.now().isoformat()

            # Основная новость из контента
            main_news = {
                "title": f"Обзор новостей {ticker} от Perplexity",
                "content": content,
                "source": "Perplexity AI",
                "url": "",
                "timestamp": current_time,
                "type": "aggregated"
            }
            news_items.append(main_news)

            # Добавляем отдельные источники из citations
            for i, citation in enumerate(citations[:5]):  # Ограничиваем 5 источниками
                if isinstance(citation, str) and citation.startswith("http"):
                    citation_news = {
                        "title": f"Источник {i+1}: {self._extract_domain(citation)}",
                        "content": f"Источник информации по {ticker}",
                        "source": self._extract_domain(citation),
                        "url": citation,
                        "timestamp": current_time,
                        "type": "citation"
                    }
                    news_items.append(citation_news)

            logger.info(f"Обработано {len(news_items)} новостных элементов для {ticker}")
            return news_items

        except Exception as e:
            logger.error(f"Ошибка парсинга ответа для {ticker}: {e}")
            return []

    def _extract_domain(self, url: str) -> str:
        """Извлечение домена из URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or "Неизвестный источник"
        except Exception:
            return "Неизвестный источник"

    def test_connection(self) -> bool:
        """
        Тестирование подключения к Perplexity API

        Returns:
            True если подключение успешное, False иначе
        """
        try:
            logger.info("🔄 Тестирование подключения к Perplexity API...")

            # Простой тестовый запрос
            test_news = self.search_ticker_news("SBER", hours=1)

            if test_news:
                logger.info("✅ Подключение к Perplexity API успешно!")
                logger.info(f"Получено {len(test_news)} тестовых новостей")
                return True
            else:
                logger.warning("⚠️ Подключение есть, но новости не найдены")
                return True  # API работает, просто нет новостей

        except PerplexityError as e:
            logger.error(f"❌ Ошибка Perplexity API: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при тестировании: {e}")
            return False


def _check_api_key() -> str:
    """Проверка наличия API ключа"""
    import os
    
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        print("❌ PERPLEXITY_API_KEY не найден в переменных окружения!")
        print("💡 Добавьте ключ в .env файл:")
        print("   PERPLEXITY_API_KEY=your_api_key_here")
        return None
    return api_key

def _initialize_client(api_key: str) -> PerplexityClient:
    """Инициализация и тестирование клиента"""
    print("🔧 Инициализация клиента...")
    client = PerplexityClient(api_key)
    print("✅ Клиент инициализирован")

    print("\n🔌 Тестирование подключения...")
    if client.test_connection():
        print("✅ Тест подключения прошел успешно!")
        return client
    else:
        print("❌ Тест подключения не прошел!")
        return None

def _test_ticker_news(client: PerplexityClient, ticker: str) -> None:
    """Тестирование поиска новостей для одного тикера"""
    print(f"\n📰 Тестирование поиска новостей для {ticker}...")
    try:
        news = client.search_ticker_news(ticker, hours=24)

        if news:
            print(f"✅ Найдено {len(news)} новостей для {ticker}!")

            # Показываем первую новость
            first_news = news[0]
            print(f"   📋 Заголовок: {first_news['title']}")
            print(f"   🏢 Источник: {first_news['source']}")
            print(f"   📄 Содержание: {first_news['content'][:150]}...")
            print(f"   🔗 URL: {first_news.get('url', 'Нет URL')}")
            print(f"   📅 Время: {first_news['timestamp']}")
            print(f"   🏷️ Тип: {first_news['type']}")

            if len(news) > 1:
                print(f"   📊 Всего элементов: {len(news)} (основной + {len(news)-1} источников)")
        else:
            print(f"⚠️ Новости для {ticker} не найдены")

    except PerplexityError as e:
        print(f"❌ Ошибка для {ticker}: {e}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка для {ticker}: {e}")

def main():
    """Функция для тестирования клиента"""
    from dotenv import load_dotenv

    # Загружаем переменные окружения
    load_dotenv()

    print("🚀 Тестирование Perplexity API клиента...")
    print("=" * 50)

    # Проверяем наличие API ключа
    api_key = _check_api_key()
    if not api_key:
        return

    try:
        # Инициализация и тестирование клиента
        client = _initialize_client(api_key)
        if not client:
            return

        # Тест поиска новостей для разных тикеров
        test_tickers = ["SBER", "GAZP", "YNDX"]
        for ticker in test_tickers:
            _test_ticker_news(client, ticker)

        print("\n🎉 Тестирование завершено!")
        print("=" * 50)

    except Exception as e:
        print(f"❌ Критическая ошибка при тестировании: {e}")


if __name__ == "__main__":
    main()
