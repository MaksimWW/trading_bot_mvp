"""
Telegram Bot для управления торговым ботом
Полная базовая версия с основными командами и интеграцией
"""

import logging
from typing import List

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TELEGRAM_TOKEN
from tinkoff_client import TinkoffClient

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class TradingTelegramBot:
    """Основной класс Telegram бота для торговли"""

    def __init__(self):
        """Инициализация бота"""
        self.token = TELEGRAM_TOKEN
        self.tinkoff_client = TinkoffClient()
        self.application = None
        logger.info("🤖 Инициализация Trading Telegram Bot")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - приветствие"""
        try:
            user_name = update.effective_user.first_name or "Трейдер"
            welcome_message = f"""
🤖 **Добро пожаловать в Trading Bot MVP, {user_name}!**

Я помогу вам с торговлей на российском фондовом рынке.

📋 **Доступные команды:**
• `/help` - список всех команд
• `/status` - состояние системы
• `/price SBER` - цена акции SBER
• `/accounts` - ваши торговые счета

🛡️ **Безопасность:**
⚠️ Сейчас работаем в режиме **песочницы** для безопасного тестирования
💰 Никаких реальных денег не тратится
🧪 Все операции виртуальные

🚀 **Начните с команды** `/status` для проверки подключений!
            """
            await update.message.reply_text(welcome_message, parse_mode="Markdown")
            logger.info(f"Пользователь {user_name} запустил бота")

        except Exception as e:
            logger.error(f"Ошибка в команде start: {e}")
            await update.message.reply_text("❌ Ошибка при запуске. Попробуйте позже.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help - справка"""
        try:
            help_message = """
📋 **Все команды Trading Bot MVP:**

🔍 **Информационные команды:**
• `/start` - приветствие и инструкции
• `/help` - эта справка
• `/status` - состояние системы и подключений

💰 **Рыночные данные:**
• `/price TICKER` - цена акции (например: `/price SBER`)
• `/accounts` - список торговых счетов
• `/news TICKER` - анализ новостей (в разработке)

📊 **Примеры использования:**
• `/price SBER` - цена Сбербанка
• `/price GAZP` - цена Газпрома
• `/price YNDX` - цена Яндекса
• `/news SBER` - новости о Сбербанке

🚀 **Скоро добавим:**
• 📰 Анализ новостей через OpenAI
• 📈 Технические индикаторы (RSI, MACD)
• 🎯 Торговые сигналы и стратегии
• 🤖 Автоматизация сделок

❓ **Нужна помощь?** Напишите любое сообщение для подсказки.

⚠️ **Помните:** Работаем в безопасной песочнице!
            """
            await update.message.reply_text(help_message, parse_mode="Markdown")
            logger.info("Пользователь запросил справку")

        except Exception as e:
            logger.error(f"Ошибка в команде help: {e}")
            await update.message.reply_text("❌ Ошибка при показе справки.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status - статус системы"""
        try:
            await update.message.reply_text("🔄 Проверяю состояние всех систем...")
            logger.info("Запуск проверки статуса системы")

            # Проверяем подключение к Tinkoff API
            tinkoff_status = "❌ Ошибка"
            accounts_count = 0

            try:
                accounts = self.tinkoff_client.get_accounts()
                if accounts:
                    tinkoff_status = "✅ Подключен"
                    accounts_count = len(accounts)
                    logger.info(f"Tinkoff API работает, найдено счетов: {accounts_count}")
                else:
                    logger.warning("Tinkoff API: счета не найдены")
            except Exception as e:
                logger.error(f"Ошибка проверки Tinkoff API: {e}")

            # Формируем сообщение о статусе
            status_message = f"""
🔍 **Состояние Trading Bot MVP**

🔗 **Подключения:**
✅ Telegram Bot API - работает
{tinkoff_status} Tinkoff Invest API
📊 Найдено счетов: {accounts_count}

⚙️ **Настройки:**
🏛️ Режим: Песочница (безопасно)
🛡️ Тип: Тестирование
🔄 Статус: {'Готов к работе' if accounts_count > 0 else 'Требует настройки'}

📈 **Возможности:**
✅ Получение цен акций
✅ Просмотр торговых счетов
⏳ Анализ новостей (в разработке)
⏳ Технические индикаторы (в разработке)

🕐 Последняя проверка: сейчас
            """

            if accounts_count == 0:
                status_message += (
                    "\n⚠️ **Рекомендация:** " "Проверьте настройки Tinkoff API в конфигурации."
                )

            await update.message.reply_text(status_message, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Ошибка в команде status: {e}")
            await update.message.reply_text(
                "❌ Ошибка при проверке статуса системы. Попробуйте позже."
            )

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /price TICKER - получение цены акции"""
        try:
            # Проверяем есть ли тикер в команде
            if not context.args:
                await update.message.reply_text(
                    "📝 Укажите тикер акции. Например: `/price SBER`",
                    parse_mode="Markdown",
                )
                return

            ticker = context.args[0].upper()
            await update.message.reply_text(f"🔍 Ищу цену для {ticker}...")
            logger.info(f"Запрос цены для тикера: {ticker}")

            # Ищем инструмент
            instrument = self.tinkoff_client.search_instrument(ticker)

            if not instrument:
                await update.message.reply_text(f"❌ Акция {ticker} не найдена. Проверьте тикер.")
                logger.warning(f"Инструмент {ticker} не найден")
                return

            # Получаем цену
            price_data = self.tinkoff_client.get_last_price(instrument.figi)

            if not price_data:
                await update.message.reply_text(
                    f"❌ Не удалось получить цену для {ticker}. Попробуйте позже."
                )
                logger.error(f"Не удалось получить цену для {ticker}")
                return

            # Конвертируем цену
            price_rub = price_data.price.units + price_data.price.nano / 1_000_000_000

            price_message = f"""
💰 **{instrument.name}**

📊 **Цена:** {price_rub:.2f} ₽
🎯 **Тикер:** {ticker}
🔗 **FIGI:** `{instrument.figi}`

⏰ Данные актуальны на: сейчас
🏛️ Источник: Tinkoff Invest API (песочница)
            """

            await update.message.reply_text(price_message, parse_mode="Markdown")
            logger.info(f"Цена {ticker} успешно получена: {price_rub:.2f} ₽")

        except Exception as e:
            logger.error(f"Ошибка в команде price: {e}")
            ticker_name = context.args[0].upper() if context.args else "акции"
            await update.message.reply_text(
                f"❌ Ошибка при получении цены {ticker_name}. " f"Попробуйте позже."
            )

    async def _format_news_result(self, ticker: str, news_results: List) -> str:
        """Форматирование результатов новостей"""
        if not news_results:
            return f"""📰 <b>НОВОСТИ ПО {ticker}</b>

🏢 <b>Компания:</b> {ticker}
❌ За последние 24 часа новостей не найдено.

💡 Возможные причины:
- Нет значимых новостей о компании
- Временные проблемы с источниками данных
- Тикер может быть неактивным

🔄 Попробуйте:
- Повторить запрос через несколько минут
- Проверить другие тикеры: GAZP, YNDX, LKOH
- Использовать <code>/price {ticker}</code> для проверки цены

⚠️ <b>Дисклеймер:</b> Анализ предназначен для ознакомления."""

        # Форматируем найденные новости
        sources = list(
            set(news.get("source", "Неизвестно") for news in news_results if news.get("source"))
        )
        sources_text = ", ".join(sources[:3])
        if len(sources) > 3:
            sources_text += f" и ещё {len(sources) - 3}"

        # Добавляем sentiment анализ через OpenAI
        sentiment_block = ""
        try:
            if len(news_results) > 0:
                from openai_analyzer import OpenAIAnalyzer
                
                analyzer = OpenAIAnalyzer()
                sentiment_result = await analyzer.analyze_sentiment(ticker, news_results[:3])
                
                if sentiment_result:
                    emoji_map = {"STRONG_BUY": "💚", "BUY": "🟢", "HOLD": "🟡", "SELL": "🟠", "STRONG_SELL": "🔴"}
                    emoji = emoji_map.get(sentiment_result.get("sentiment_label", "HOLD"), "⚪")
                    score = sentiment_result.get("sentiment_score", 0.0)
                    summary = sentiment_result.get("summary", "Анализ недоступен")
                    
                    sentiment_block = f"""
🤖 <b>АНАЛИЗ НАСТРОЕНИЯ AI:</b>
{emoji} <b>Рекомендация:</b> {sentiment_result.get("sentiment_label", "HOLD")}
📊 <b>Оценка:</b> {score:.2f} (от -1.0 до +1.0)  
📝 <b>Анализ:</b> {summary}
"""
        except Exception as e:
            logger.warning(f"OpenAI анализ недоступен для {ticker}: {e}")

        result_text = f"""📰 <b>НОВОСТИ ПО {ticker}</b>

🏢 <b>Компания:</b> {ticker}
🔍 <b>Найдено новостей:</b> {len(news_results)}
⏰ <b>Период:</b> Последние 24 часа
🌐 <b>Источники:</b> {sources_text}{sentiment_block}

📋 <b>ТОП-{min(3, len(news_results))} НОВОСТЕЙ:</b>

"""
        for i, news in enumerate(news_results[:3], 1):
            title = news.get("title", "Без заголовка")
            summary = news.get("content", news.get("summary", "Описание отсутствует"))
            source = news.get("source", "Неизвестный источник")

            if len(title) > 80:
                title = title[:77] + "..."
            if len(summary) > 150:
                summary = summary[:147] + "..."

            # Экранируем HTML символы
            title_escaped = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            summary_escaped = (
                summary.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )
            source_escaped = source.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            result_text += f"""<b>{i}. {title_escaped}</b>
📝 {summary_escaped}
🌐 {source_escaped}

"""

        if len(news_results) > 3:
            result_text += f"📋 И ещё {len(news_results) - 3} новостей...\n\n"

        result_text += f"""🕐 <b>Время анализа:</b> {ticker} проанализирован

💡 <b>Что дальше?</b>
- <code>/price {ticker}</code> - текущая цена
- <code>/accounts</code> - торговые счета
- <code>/status</code> - состояние системы

⚠️ <b>Дисклеймер:</b> Анализ предназначен для ознакомления. Не является инвестиционной рекомендацией."""

        return result_text

    async def accounts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /accounts - список торговых счетов"""
        try:
            await update.message.reply_text(
                "🔍 Получаю информацию о торговых счетах...", parse_mode="Markdown"
            )
            logger.info("Запрос списка торговых счетов")

            accounts = self.tinkoff_client.get_accounts()

            if not accounts:
                await update.message.reply_text(
                    "❌ **Торговые счета не найдены**\n\n"
                    "Возможные причины:\n"
                    "• Проблема с подключением к Tinkoff API\n"
                    "• Неверный токен API\n"
                    "• Счета не созданы в песочнице\n\n"
                    "💡 Попробуйте команду `/status` для диагностики",
                    parse_mode="Markdown",
                )
                logger.warning("Торговые счета не найдены")
                return

            accounts_message = f"💼 **Ваши торговые счета** ({len(accounts)} шт.)\n\n"

            for i, account in enumerate(accounts, 1):
                account_id = account.id
                account_name = account.name if account.name else f"Счет {i}"
                account_type = account.type.name if hasattr(account, "type") else "UNSPECIFIED"

                accounts_message += f"""
**🏦 Счет {i}:**
📝 Название: {account_name}
🆔 ID: `{account_id}`
📋 Тип: {account_type}
🏛️ Режим: Песочница

---
                """

            accounts_message += f"""

✅ **Всего активных счетов:** {len(accounts)}
🛡️ **Безопасность:** Все операции в песочнице
💡 **Следующий шаг:** Попробуйте `/price SBER`

⚠️ **Помните:** Это тестовые счета, реальные деньги не используются!
            """

            await update.message.reply_text(accounts_message, parse_mode="Markdown")
            logger.info(f"Список счетов успешно отправлен: {len(accounts)} счетов")

        except Exception as e:
            logger.error(f"Ошибка в команде accounts: {e}")
            await update.message.reply_text(
                "❌ **Ошибка при получении счетов**\n\n" "Попробуйте позже или проверьте `/status`",
                parse_mode="Markdown",
            )

    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /news TICKER - анализ новостей"""
        try:
            # Проверяем есть ли тикер в команде
            if not context.args:
                await update.message.reply_text(
                    "📰 <b>Анализ новостей по компании</b>\n\n"
                    "Использование: <code>/news TICKER</code>\n\n"
                    "Примеры:\n"
                    "• <code>/news SBER</code> - новости о Сбербанке\n"
                    "• <code>/news GAZP</code> - новости о Газпроме\n"
                    "• <code>/news YNDX</code> - новости о Яндексе\n\n"
                    "🤖 Анализ выполняется с помощью ИИ\n"
                    "⏱️ Время обработки: 3-7 секунд",
                    parse_mode="HTML",
                )
                return

            ticker = context.args[0].upper()

            # Отправляем сообщение о начале анализа
            loading_msg = await update.message.reply_text(
                f"🔍 Ищу новости о <b>{ticker}</b>...\n" f"🤖 Анализирую через Perplexity AI...",
                parse_mode="HTML",
            )

            try:
                from perplexity_client import PerplexityClient

                perplexity = PerplexityClient()
                news_results = perplexity.search_ticker_news(ticker, hours=24)
                result_text = await self._format_news_result(ticker, news_results)

            except ImportError:
                result_text = f"""❌ <b>PERPLEXITY CLIENT НЕ НАЙДЕН</b>

🔧 Необходимо создать файл <code>perplexity_client.py</code>

💡 Пока что используйте:
- <code>/price {ticker}</code> - текущая цена акции
- <code>/accounts</code> - торговые счета
- <code>/status</code> - состояние систем"""

            except Exception as api_error:
                logger.error(f"Ошибка Perplexity API для {ticker}: {api_error}")
                result_text = f"""❌ <b>ОШИБКА ПОЛУЧЕНИЯ НОВОСТЕЙ {ticker}</b>

🔍 Причина: {str(api_error)}

💡 Попробуйте:
- Повторить запрос через несколько секунд
- Проверить соединение с интернетом
- Использовать <code>/status</code> для диагностики
- Попробовать другой тикер: GAZP, YNDX

🔄 Альтернативы:
- <code>/price {ticker}</code> - текущая цена
- <code>/accounts</code> - торговые счета"""

            await loading_msg.edit_text(result_text, parse_mode="HTML")
            logger.info(f"Команда news выполнена для {ticker}")

        except Exception as e:
            logger.error(f"Ошибка в команде news: {e}")
            ticker_name = context.args[0].upper() if context.args else "акции"
            await update.message.reply_text(
                f"❌ Ошибка при анализе новостей {ticker_name}. " f"Попробуйте позже.",
                parse_mode="HTML",
            )

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка неизвестных сообщений"""
        try:
            message_text = update.message.text
            logger.info(f"Получено неизвестное сообщение: {message_text}")

            response_message = """
❓ **Не понимаю эту команду**

📋 **Попробуйте:**
• `/help` - список всех команд
• `/price SBER` - цена акции Сбербанк
• `/status` - состояние системы
• `/accounts` - ваши торговые счета

💡 **Подсказка:** Все команды начинаются с символа `/`

🚀 Или напишите `/start` для знакомства с ботом.
            """
            await update.message.reply_text(response_message, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Ошибка в обработке неизвестной команды: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте `/help`")

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        logger.info("Настройка обработчиков команд")

        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("price", self.price_command))
        self.application.add_handler(CommandHandler("accounts", self.accounts_command))
        self.application.add_handler(CommandHandler("news", self.news_command))

        # Обработка неизвестных сообщений
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.unknown_command)
        )

        logger.info("Все обработчики команд настроены")

    def run(self):
        """Запуск бота"""
        try:
            if not self.token:
                logger.error("❌ TELEGRAM_TOKEN не найден в " "переменных окружения")
                print("❌ Ошибка: TELEGRAM_TOKEN не настроен " "в .env файле")
                return

            # Создаем приложение
            self.application = Application.builder().token(self.token).build()

            # Настраиваем обработчики
            self.setup_handlers()

            logger.info("🤖 Trading Telegram Bot успешно запущен!")
            logger.info("📱 Бот готов принимать команды от пользователей")
            logger.info("🔗 Режим работы: Песочница Tinkoff Invest")

            print("🤖 Trading Telegram Bot запущен!")
            print("📱 Отправьте /start вашему боту для начала работы")
            print("🛡️ Режим: Безопасная песочница")

            # Запускаем бота
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES, drop_pending_updates=True
            )

        except Exception as e:
            logger.error(f"❌ Критическая ошибка запуска бота: {e}")
            print(f"❌ Ошибка запуска: {e}")
            print("💡 Проверьте TELEGRAM_TOKEN в .env файле")


def main():
    """Главная функция для запуска бота"""
    logger.info("Запуск Trading Telegram Bot")
    bot = TradingTelegramBot()
    bot.run()


if __name__ == "__main__":
    main()
