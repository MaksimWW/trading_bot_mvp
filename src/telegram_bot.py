"""
Telegram Bot для управления торговым ботом
Полная базовая версия с основными командами и интеграцией
"""

import logging
from datetime import datetime
from typing import Dict, List

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TELEGRAM_TOKEN
from portfolio_manager import PortfolioManager
from risk_manager import RiskManager
from tinkoff_client import TinkoffClient
from portfolio_coordinator import get_portfolio_coordinator

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
        self.portfolio_manager = PortfolioManager()
        self.application = None

        # Portfolio Coordinator
        from portfolio_coordinator import get_portfolio_coordinator
        self.portfolio_coordinator = get_portfolio_coordinator()

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
            logger.info("Пользователь {user_name} запустил бота")
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
• `/analysis TICKER` - технический анализ акции
• `/signal TICKER` - комбинированный торговый сигнал
⚖️ **Управление рисками:**
• `/risk TICKER` - анализ рисков позиции

💼 **Управление портфелем:**
• `/portfolio` - просмотр текущего портфеля
• `/analytics` - продвинутая аналитика портфеля (Sharpe, VaR, корреляции)
• `/buy TICKER QUANTITY` - покупка акций
📊 **Координация портфеля:**
• `/portfolio_strategies` - активные стратегии портфеля
• `/strategy_weights` - управление весами стратегий
• `/coordinate_portfolio` - запуск координации портфеля
• `/portfolio_performance` - производительность портфеля

🤖 **Автоматизация и стратегии:**
• `/strategies` - список автоматических стратегий
• `/start_strategy ID` - запуск стратегии
• `/stop_strategy ID` - остановка стратегии
• `/scan` - сканирование рынка на сигналы
📊 **Примеры использования:**
• `/price SBER` - цена Сбербанка
• `/price GAZP` - цена Газпрома
• `/price YNDX` - цена Яндекса
• `/news SBER` - новости о Сбербанке
• `/analysis SBER` - технический анализ Сбербанка
• `/risk SBER` - анализ рисков позиции Сбербанка
• `/portfolio` - анализ всего портфеля
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
            price_data = self.tinkoff_client.get_last_price(instrument["figi"])
            if not price_data:
                await update.message.reply_text(
                    f"❌ Не удалось получить цену для {ticker}. Попробуйте позже."
                )
                logger.error(f"Не удалось получить цену для {ticker}")
                return
            # Конвертируем цену
            price_rub = price_data.price.units + price_data.price.nano / 1_000_000_000
            price_message = f"""
💰 **{instrument["name"]}**
📊 **Цена:** {price_rub:.2f} ₽
🎯 **Тикер:** {ticker}
🔗 **FIGI:** `{instrument["figi"]}`
⏰ Данные актуальны на: сейчас
"""
            await update.message.reply_text(price_message, parse_mode="Markdown")
            logger.info(f"Цена {ticker} успешно получена: {price_rub:.2f} ₽")
        except Exception as e:
            logger.error(f"Ошибка в команде price: {e}")
            ticker_name = context.args[0].upper() if context.args else "акции"
            await update.message.reply_text(
                f"❌ Ошибка при получении цены {ticker_name}. Попробуйте позже."
            )

    async def _get_sentiment_analysis(self, ticker: str, news_results: List) -> str:
        """Получение блока sentiment анализа"""
        try:
            if len(news_results) > 0:
                from openai_analyzer import OpenAIAnalyzer

                analyzer = OpenAIAnalyzer()
                result = await analyzer.analyze_sentiment(ticker, news_results[:3])
                if result:
                    emoji_map = {
                        "STRONG_BUY": "💚",
                        "BUY": "🟢",
                        "HOLD": "🟡",
                        "SELL": "🟠",
                        "STRONG_SELL": "🔴",
                    }
                    emoji = emoji_map.get(result.get("sentiment_label", "HOLD"), "⚪")
                    score = result.get("sentiment_score", 0.0)
                    summary = result.get("summary", "Анализ недоступен")
                    return f"""
🤖 **АНАЛИЗ НАСТРОЕНИЯ AI:**
{emoji} **Рекомендация:** {result.get("sentiment_label", "HOLD")}
📊 **Оценка:** {score:.2f} (от -1.0 до +1.0)
📝 **Анализ:** {summary}
"""
        except Exception as e:
            logger.warning(f"OpenAI анализ недоступен для {ticker}: {e}")
        return ""

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
        sentiment_block = await self._get_sentiment_analysis(ticker, news_results)
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
                f"🔍 Ищу новости о <b>{ticker}</b>...\n" "🤖 Анализирую через Perplexity AI...",
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
                f"❌ Ошибка при анализе новостей {ticker_name}. Попробуйте позже.",
                parse_mode="HTML",
            )

    async def _parse_risk_params(self, args, loading_msg, ticker):
        """Parse entry price and stop loss from command arguments."""
        entry_price = None
        stop_loss_price = None

        if len(args) >= 2:
            try:
                entry_price = float(args[1])
            except ValueError:
                await loading_msg.edit_text(
                    "❌ Неверный формат цены входа: {args[1]}\n"
                    "Используйте число, например: `/risk SBER 100`",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return None, None

        if len(args) >= 3:
            try:
                stop_loss_price = float(args[2])
            except ValueError:
                await loading_msg.edit_text(
                    "❌ Неверный формат стоп-лосса: {args[2]}\n"
                    "Используйте число, например: `/risk SBER 100 93`",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return None, None

        return entry_price, stop_loss_price

    async def _get_current_price(self, ticker, loading_msg):
        """Get current price for ticker if not provided."""
        instrument = self.tinkoff_client.search_instrument(ticker)
        if not instrument:
            await loading_msg.edit_text(
                f"❌ Акция с тикером *{ticker}* не найдена.\n\n"
                "Попробуйте: SBER, GAZP, YNDX, LKOH, NVTK, ROSN",
                parse_mode=ParseMode.MARKDOWN,
            )
            return None

        price_data = self.tinkoff_client.get_last_price(instrument["figi"])
        if not price_data:
            await loading_msg.edit_text(
                f"❌ Не удалось получить цену для {ticker}", parse_mode=ParseMode.MARKDOWN
            )
            return None

        return price_data.price.units + price_data.price.nano / 1_000_000_000

    def _format_risk_result(
        self, ticker, position_analysis, sl_tp_analysis, entry_price, stop_loss_price
    ):
        """Format risk analysis result text."""
        if not position_analysis.get("approved", False):
            result_text = f"❌ *АНАЛИЗ РИСКОВ {ticker}*\n\n"
            result_text += "🚫 *Позиция отклонена*\n"
            result_text += (
                f"📝 Причина: {position_analysis.get('reason', 'Неизвестная ошибка')}\n\n"
            )
            result_text += "💡 Рекомендации:\n"
            result_text += "• Снизьте размер позиции\n"
            result_text += "• Используйте более близкий стоп-лосс\n"
            result_text += "• Дождитесь лучших условий"
            return result_text

        risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "EXTREME": "🔴"}
        emoji = risk_emoji.get(position_analysis["risk_level"], "⚪")

        result_text = f"⚖️ *АНАЛИЗ РИСКОВ {ticker}*\n\n"
        result_text += "💰 *Параметры позиции:*\n"
        result_text += f"📈 Цена входа: {entry_price:.2f} ₽\n"
        result_text += f"🛑 Стоп-лосс: {stop_loss_price:.2f} ₽\n"
        result_text += f"🎯 Тейк-профит: {sl_tp_analysis['take_profit_price']:.2f} ₽\n\n"

        result_text += "📊 *Рекомендуемая позиция:*\n"
        result_text += f"🔢 Количество акций: {position_analysis['shares_count']}\n"
        result_text += f"💵 Сумма позиции: {position_analysis['position_amount']:,.0f} ₽\n"
        result_text += f"📈 Доля портфеля: {position_analysis['position_percent']:.1f}%\n\n"

        result_text += "⚖️ *Анализ рисков:*\n"
        result_text += f"{emoji} Уровень риска: {position_analysis['risk_level']}\n"
        result_text += f"💸 Потенциальный убыток: {position_analysis['risk_amount']:,.0f} ₽\n"
        result_text += f"📉 Риск от депозита: {position_analysis['risk_percent']:.2f}%\n"
        result_text += f"⚖️ Риск/Доходность: 1:{sl_tp_analysis['risk_reward_ratio']:.1f}\n\n"

        result_text += "💡 *Рекомендация:*\n"
        result_text += f"{position_analysis['recommendation']}\n\n"

        result_text += "📋 *Дополнительно:*\n"
        result_text += f"• Трейлинг стоп: {sl_tp_analysis['trailing_stop_distance']:.2f} ₽\n"
        result_text += "• Волатильность: Нормальная\n"
        result_text += "• Ликвидность: Высокая\n\n"

        result_text += "*🛠️ Дополнительные команды:*\n"
        result_text += f"• `/price {ticker}` - текущая цена\n"
        result_text += f"• `/analysis {ticker}` - технический анализ\n"
        result_text += f"• `/news {ticker}` - анализ новостей\n\n"

        result_text += "⚠️ *Внимание:* Анализ основан на примерном депозите 100,000 ₽. "
        result_text += "Скорректируйте размер позиции под ваш реальный депозит."

        return result_text

    async def risk_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /risk TICKER."""
        if not context.args:
            await update.message.reply_text(
                "⚖️ *Анализ рисков позиции*\n\n"
                "Использование: `/risk TICKER [ЦЕНА_ВХОДА] [СТОП_ЛОСС]`\n\n"
                "Примеры:\n"
                "• `/risk SBER` - анализ риска по текущей цене\n"
                "• `/risk SBER 100 93` - анализ с заданными параметрами\n\n"
                "📊 Анализ включает:\n"
                "• Рекомендуемый размер позиции\n"
                "• Расчет стоп-лосса и тейк-профита\n"
                "• Оценка уровня риска\n"
                "• Соотношение риск/доходность",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        ticker = context.args[0].upper()
        loading_msg = await update.message.reply_text(
            f"🔍 Анализирую риски для *{ticker}*...\n"
            "📊 Получаю данные и рассчитываю параметры...",
            parse_mode=ParseMode.MARKDOWN,
        )

        try:
            entry_price, stop_loss_price = await self._parse_risk_params(
                context.args, loading_msg, ticker
            )
            if entry_price is None and len(context.args) >= 2:
                return  # Error already handled

            if entry_price is None:
                entry_price = await self._get_current_price(ticker, loading_msg)
                if entry_price is None:
                    return  # Error already handled

            risk_manager = RiskManager()

            if stop_loss_price is None:
                sl_tp = risk_manager.calculate_stop_loss_take_profit(
                    ticker=ticker, entry_price=entry_price, signal_direction="BUY"
                )
                stop_loss_price = sl_tp["stop_loss_price"]

            account_balance = 100000.0
            position_analysis = risk_manager.calculate_position_size(
                ticker=ticker,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                account_balance=account_balance,
                confidence_score=0.6,
            )

            sl_tp_analysis = risk_manager.calculate_stop_loss_take_profit(
                ticker=ticker, entry_price=entry_price, signal_direction="BUY"
            )

            result_text = self._format_risk_result(
                ticker, position_analysis, sl_tp_analysis, entry_price, stop_loss_price
            )

            await loading_msg.edit_text(result_text, parse_mode=ParseMode.MARKDOWN)
            logger.info(
                f"Анализ рисков {ticker} завершен: риск {position_analysis.get('risk_percent', 0):.2f}%"
            )

        except Exception as e:
            error_msg = f"❌ *Ошибка анализа рисков {ticker}*\n\n"
            error_msg += f"Причина: {str(e)}\n\n"
            error_msg += "💡 Попробуйте:\n"
            error_msg += "• Проверить правильность тикера\n"
            error_msg += "- Использовать `/risk SBER 100 93` с параметрами\n"
            error_msg += "- Повторить запрос через несколько секунд"

            await loading_msg.edit_text(error_msg, parse_mode=ParseMode.MARKDOWN)
            logger.error(f"Risk command error for {ticker}: {e}")

    def _format_portfolio_summary(self, summary: Dict) -> str:
        """Форматирование сводки портфеля для Telegram."""
        from datetime import datetime

        text = "💼 **ПОРТФЕЛЬ**\n\n"
        text += f"💰 **Баланс:** {summary['cash_balance']:,.0f} ₽\n"
        text += f"📈 **Стоимость позиций:** {summary['portfolio_value'] - summary['cash_balance']:,.0f} ₽\n"
        text += f"💎 **Общая стоимость:** {summary['portfolio_value']:,.0f} ₽\n"
        text += f"📊 **P&L:** {summary['unrealized_pnl']:+,.0f} ₽ ({summary['unrealized_pnl_percent']:+.2f}%)\n\n"

        if summary["positions"]:
            text += "📋 **ПОЗИЦИИ:**\n"
            for pos in summary["positions"]:
                pnl_emoji = "🟢" if pos["unrealized_pnl"] >= 0 else "🔴"
                text += f"{pnl_emoji} **{pos['ticker']}**: {pos['quantity']} шт × {pos['current_price']:.2f} ₽\n"
                text += f"   P&L: {pos['unrealized_pnl']:+,.0f} ₽ ({pos['unrealized_pnl_percent']:+.2f}%) | Вес: {pos['weight_percent']:.1f}%\n\n"
        else:
            text += "📋 **Позиций нет**\n\n"

        text += f"🕐 **Обновлено:** {datetime.now().strftime('%H:%M:%S')}"
        return text

    async def portfolio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /portfolio."""
        loading_msg = await update.message.reply_text(
            "💼 Обновляю данные портфеля...", parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Обновляем цены и получаем сводку
            await self.portfolio_manager.update_portfolio_prices()
            summary = self.portfolio_manager.get_portfolio_summary()

            if "error" in summary:
                await loading_msg.edit_text(
                    f"❌ Ошибка получения портфеля: {summary['error']}",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

            # Форматируем ответ
            portfolio_text = self._format_portfolio_summary(summary)

            await loading_msg.edit_text(portfolio_text, parse_mode=ParseMode.MARKDOWN)

            logger.info("Сводка портфеля отправлена")

        except Exception as e:
            await loading_msg.edit_text(
                f"❌ Ошибка при получении портфеля: {str(e)}", parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Portfolio command error: {e}")

    async def analytics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /analytics."""
        loading_msg = await update.message.reply_text(
            "📊 Рассчитываю продвинутые метрики портфеля...\n"
            "🔢 Анализирую доходность и риски...\n"
            "📈 Вычисляю Sharpe ratio и VaR...",
            parse_mode=ParseMode.MARKDOWN,
        )

        try:
            # Импортируем Portfolio Analytics
            from portfolio_analytics import PortfolioAnalytics

            analytics = PortfolioAnalytics(self.portfolio_manager)

            # Определяем период анализа
            days = 30
            if context.args and context.args[0].isdigit():
                days = min(90, max(7, int(context.args[0])))

            # Рассчитываем метрики
            metrics = await analytics.calculate_portfolio_metrics(days=days)

            # Форматируем результат для Telegram
            result_text = analytics.format_metrics_for_telegram(metrics)

            await loading_msg.edit_text(result_text, parse_mode=None)

            logger.info(
                f"Аналитика портфеля отправлена: {metrics.positions_count} позиций, "
                f"Sharpe {metrics.sharpe_ratio:.2f}"
            )

        except Exception as e:
            error_msg = "❌ *Ошибка расчета аналитики портфеля*\n\n"
            error_msg += f"Причина: {str(e)}\n\n"
            error_msg += "💡 Попробуйте:\n"
            error_msg += "• Убедиться что есть позиции в портфеле\n"
            error_msg += "- Проверить настройки риск-менеджмента\n"
            error_msg += "- Повторить запрос через несколько секунд\n"
            error_msg += "- Использовать `/portfolio` для проверки позиций"

            await loading_msg.edit_text(error_msg, parse_mode=ParseMode.MARKDOWN)
            logger.error(f"Analytics command error: {e}")

    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /buy TICKER QUANTITY."""
        if len(context.args) < 2:
            await update.message.reply_text(
                "💰 *Покупка акций (виртуальная)*\n\n"
                "Использование: `/buy TICKER QUANTITY`\n\n"
                "Примеры:\n"
                "• `/buy SBER 100` - купить 100 акций Сбербанка\n"
                "• `/buy GAZP 50` - купить 50 акций Газпрома\n\n"
                "💡 Покупка осуществляется по текущей рыночной цене",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        ticker = context.args[0].upper()
        try:
            quantity = int(context.args[1])
        except ValueError:
            await update.message.reply_text(
                "❌ Количество акций должно быть числом", parse_mode=ParseMode.MARKDOWN
            )
            return

        if quantity <= 0:
            await update.message.reply_text(
                "❌ Количество акций должно быть положительным числом",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        loading_msg = await update.message.reply_text(
            f"💰 Покупаю {quantity} акций {ticker}...", parse_mode=ParseMode.MARKDOWN
        )

        try:
            result = await self.portfolio_manager.buy_stock(ticker, quantity)

            if result["success"]:
                buy_text = f"""
💰 *ПОКУПКАВЫПОЛНЕНА*

🎯 *Акция:* {ticker}
📊 *Количество:* {result['quantity']} шт
💵 *Цена:* {result['price']:.2f} ₽
💸 *Комиссия:* {result['commission']:.2f} ₽
💳 *Общая сумма:* {result['total_cost']:,.0f} ₽

💰 *Баланс после покупки:* {result['new_cash_balance']:,.0f} ₽

🎉 Акции добавлены в ваш виртуальный портфель!

💡 Используйте `/portfolio` для просмотра портфеля
                """
            else:
                buy_text = f"""
❌ *ОШИБКА ПОКУПКИ*

🎯 *Акция:* {ticker}
📊 *Количество:* {quantity} шт

❌ *Причина:* {result['error']}

💡 *Советы:*
- Проверьте достаточность средств
- Убедитесь в правильности тикера
- Используйте `/portfolio` для проверки баланса
                """

            await loading_msg.edit_text(buy_text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await loading_msg.edit_text(
                f"❌ Ошибка при покупке {ticker}: {str(e)}", parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Buy command error for {ticker}: {e}")

    async def sell_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /sell TICKER QUANTITY."""
        if len(context.args) < 2:
            await update.message.reply_text(
                "📈 *Продажа акций (виртуальная)*\n\n"
                "Использование: `/sell TICKER QUANTITY`\n\n"
                "Примеры:\n"
                "• `/sell SBER 25` - продать 25 акций Сбербанка\n"
                "• `/sell GAZP 30` - продать 30 акций Газпрома\n\n"
                "💡 Продажа осуществляется по текущей рыночной цене\n"
                "📊 Используйте `/portfolio` для просмотра позиций",
                parse_mode=ParseMode.MARKDOWN,
            )

    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /analysis TICKER - технический анализ акции"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "📊 **Технический анализ акции**\n\n"
                    "Использование: `/analysis TICKER`\n\n"
                    "Примеры:\n"
                    "• `/analysis SBER` - анализ Сбербанка\n"
                    "• `/analysis GAZP` - анализ Газпрома\n"
                    "• `/analysis YNDX` - анализ Яндекса\n\n"
                    "📈 Показывает: RSI, MACD, Bollinger Bands, торговые сигналы",
                    parse_mode="HTML",
                )
                return

            ticker = context.args[0].upper()
            loading_msg = await update.message.reply_text(
                f"📊 Выполняю технический анализ {ticker}...", parse_mode="HTML"
            )

            try:
                from technical_analysis import get_ticker_analysis_for_telegram

                result_text = await get_ticker_analysis_for_telegram(ticker)

                await loading_msg.edit_text(result_text, parse_mode="HTML")
                logger.info(f"Технический анализ {ticker} выполнен успешно")

            except Exception as e:
                await loading_msg.edit_text(
                    f"❌ Ошибка технического анализа {ticker}: {str(e)[:100]}...\n\n"
                    "💡 Попробуйте:\n"
                    "• Проверить тикер акции\n"
                    "- Повторить запрос через несколько секунд\n"
                    "- Использовать /status для проверки систем",
                    parse_mode="HTML",
                )
                logger.error(f"Ошибка analysis_command для {ticker}: {e}")

        except Exception as e:
            await update.message.reply_text(
                "❌ Произошла неожиданная ошибка при анализе. Попробуйте позже.", parse_mode="HTML"
            )
            logger.error(f"Критическая ошибка analysis_command: {e}")

    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /signal TICKER - комбинированный торговый сигнал"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "🎯 **Комбинированный торговый сигнал**\n\n"
                    "Использование: `/signal TICKER`\n\n"
                    "Примеры:\n"
                    "• `/signal SBER` - сигнал по Сбербанку\n"
                    "• `/signal GAZP` - сигнал по Газпрому\n"
                    "• `/signal YNDX` - сигнал по Яндексу\n\n"
                    "🧠 Объединяет: технический анализ (60%) + анализ новостей (40%)",
                    parse_mode="Markdown",
                )
                return

            ticker = context.args[0].upper()
            loading_msg = await update.message.reply_text(
                f"🎯 Генерирую торговый сигнал для {ticker}...\n"
                f"🔄 Анализирую технические данные и новости...",
                parse_mode="Markdown",
            )

            try:
                from ai_signal_integration import AISignalIntegration

                ai_signal = AISignalIntegration()
                signal_result = await ai_signal.analyze_ticker(ticker)

                if signal_result:
                    # Форматируем результат для Telegram
                    result_text = f"🎯 **ТОРГОВЫЙ СИГНАЛ {ticker}**\n\n"

                    # Комбинированный сигнал
                    signal_strength = str(signal_result.signal_strength).replace(
                        "SignalStrength.", ""
                    )
                    combined_score = signal_result.combined_score
                    confidence = signal_result.confidence

                    signal_emoji = {
                        "STRONG_BUY": "💚",
                        "BUY": "🟢",
                        "HOLD": "🟡",
                        "SELL": "🟠",
                        "STRONG_SELL": "🔴",
                    }.get(signal_strength, "⚪")

                    result_text += f"{signal_emoji} **Рекомендация: {signal_strength}**\n"
                    result_text += f"📊 Итоговая оценка: {combined_score:+.2f}\n"
                    result_text += f"🎯 Уверенность: {confidence:.0%}\n\n"

                    # Компоненты анализа
                    technical_score = signal_result.technical_score
                    news_score = signal_result.news_sentiment_score

                    result_text += "📊 **ТЕХНИЧЕСКИЙ АНАЛИЗ (60% веса):**\n"
                    result_text += f"📈 Оценка: {technical_score:+.2f}\n"

                    # Технические индикаторы
                    tech_indicators = signal_result.technical_indicators
                    current_price = tech_indicators.get("current_price", 0)
                    rsi_data = tech_indicators.get("rsi", {})
                    macd_data = tech_indicators.get("macd", {})

                    result_text += (
                        f"• RSI: {rsi_data.get('value', 0):.1f} ({rsi_data.get('level', 'N/A')})\n"
                    )
                    result_text += f"• MACD: {macd_data.get('trend', 'N/A')}\n\n"

                    result_text += "📰 **АНАЛИЗ НОВОСТЕЙ (40% веса):**\n"
                    result_text += f"🤖 Оценка: {news_score:+.2f}\n"
                    result_text += f"📝 Сводка: {signal_result.news_summary}\n\n"

                    result_text += f"⚖️ Формула: ({technical_score:+.2f} × 0.6) + ({news_score:+.2f} × 0.4) = {combined_score:+.2f}\n\n"

                    # Торговые рекомендации
                    result_text += "💰 **ТОРГОВЫЕ РЕКОМЕНДАЦИИ:**\n"
                    result_text += f"💵 Цена входа: {current_price:.2f} ₽\n"
                    result_text += f"🛑 Стоп-лосс: {signal_result.stop_loss_price:.2f} ₽\n"
                    result_text += f"🎯 Тейк-профит: {signal_result.take_profit_price:.2f} ₽\n"
                    result_text += f"📊 Размер позиции: {signal_result.recommended_position_size:.1%} портфеля\n"
                    result_text += (
                        f"⚖️ Риск: {str(signal_result.risk_level).replace('RiskLevel.', '')}\n\n"
                    )

                    # Дополнительная информация и команды
                    result_text += f"⏰ Время анализа: {datetime.now().strftime('%H:%M:%S')}\n\n"
                    result_text += "💡 **Что дальше?**\n"
                    result_text += f"• `/analysis {ticker}` - детальный технический анализ\n"
                    result_text += f"• `/news {ticker}` - подробный анализ новостей\n"
                    result_text += f"• `/risk {ticker}` - анализ рисков покупки\n\n"
                    result_text += "⚠️ *Не является инвестиционной рекомендацией*"

                    await loading_msg.edit_text(result_text, parse_mode="Markdown")
                    logger.info(
                        f"Торговый сигнал {ticker} сгенерирован: {signal_strength} ({combined_score:+.2f})"
                    )

                else:
                    await loading_msg.edit_text(
                        f"❌ Не удалось сгенерировать сигнал для {ticker}.\n\n"
                        "💡 Попробуйте использовать отдельно:\n"
                        f"• `/analysis {ticker}` - технический анализ\n"
                        f"• `/news {ticker}` - анализ новостей",
                        parse_mode="Markdown",
                    )

            except Exception as e:
                await loading_msg.edit_text(
                    f"❌ Ошибка генерации сигнала {ticker}: {str(e)[:100]}...\n\n"
                    "💡 Попробуйте:\n"
                    "• Проверить тикер акции\n"
                    "- Повторить запрос через несколько секунд\n"
                    "- Использовать отдельно /analysis и /news",
                    parse_mode="Markdown",
                )
                logger.error(f"Ошибка signal_command для {ticker}: {e}")

        except Exception as e:
            await update.message.reply_text(
                "❌ Произошла неожиданная ошибка при генерации сигнала. Попробуйте позже.",
                parse_mode="Markdown",
            )
            logger.error(f"Критическая ошибка signal_command: {e}")

    async def strategies_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /strategies."""
        loading_msg = await update.message.reply_text(
            "📊 Получаю список доступных стратегий...", parse_mode=ParseMode.MARKDOWN
        )

        try:
            from strategy_engine import get_strategy_engine

            engine = get_strategy_engine()

            # Получаем все стратегии
            all_strategies = engine.get_all_strategies()
            active_strategies = engine.get_active_strategies()

            strategies_text = "*📊 АВТОМАТИЧЕСКИЕ ТОРГОВЫЕ СТРАТЕГИИ*\n\n"

            for strategy_id, info in all_strategies.items():
                status_emoji = {
                    "inactive": "⚫",
                    "active": "🟢",
                    "paused": "🟡",
                    "error": "🔴",
                    "stopped": "⚪",
                }.get(info["status"], "❓")

                strategies_text += f"*{info['name']}*\n"
                strategies_text += f"{status_emoji} Статус: {info['status'].upper()}\n"
                strategies_text += f"📝 Описание: {info['description']}\n"
                strategies_text += f"📈 Тикеры: {', '.join(info['supported_tickers'])}\n"
                strategies_text += f"🎯 Сигналов создано: {info['signals_generated']}\n\n"

            strategies_text += "*💡 КОМАНДЫ УПРАВЛЕНИЯ:*\n"
            strategies_text += "• `/start_strategy rsi_mean_reversion SBER` - запуск стратегии\n"
            strategies_text += "• `/stop_strategy rsi_mean_reversion` - остановка стратегии\n"
            strategies_text += "• `/strategy_status` - статус активных стратегий\n"
            strategies_text += "• `/strategy_signals SBER` - сигналы для тикера\n\n"

            if active_strategies:
                strategies_text += f"*🚀 АКТИВНЫХ СТРАТЕГИЙ: {len(active_strategies)}*"
            else:
                strategies_text += "*💤 Нет активных стратегий*"

            await loading_msg.edit_text(strategies_text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await loading_msg.edit_text(
                f"❌ Ошибка получения стратегий: {str(e)}", parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Strategies command error: {e}")

    async def start_strategy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start_strategy."""
        if len(context.args) < 2:
            await update.message.reply_text(
                "*🚀 ЗАПУСК СТРАТЕГИИ*\n\n"
                "Использование: `/start_strategy STRATEGY_ID TICKER`\n\n"
                "Примеры:\n"
                "• `/start_strategy rsi_mean_reversion SBER`\n"
                "• `/start_strategy macd_trend_following GAZP`\n\n"
                "Доступные стратегии:\n"
                "• `rsi_mean_reversion` - RSI Mean Reversion\n"
                "• `macd_trend_following` - MACD Trend Following\n\n"
                "Используйте `/strategies` для подробной информации",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        strategy_id = context.args[0]
        ticker = context.args[1].upper()

        loading_msg = await update.message.reply_text(
            f"🚀 Запускаю стратегию *{strategy_id}* для *{ticker}*...",
            parse_mode=ParseMode.MARKDOWN,
        )

        try:
            from strategy_engine import get_strategy_engine

            engine = get_strategy_engine()

            # Запускаем стратегию
            success = engine.start_strategy(strategy_id, [ticker])

            if success:
                result_text = "✅ *СТРАТЕГИЯ ЗАПУЩЕНА*\n\n"
                result_text += f"🎯 Стратегия: *{strategy_id}*\n"
                result_text += f"📈 Тикер: *{ticker}*\n"
                result_text += f"⏰ Время запуска: {datetime.now().strftime('%H:%M:%S')}\n\n"
                result_text += f"💡 Стратегия будет генерировать сигналы для {ticker}\n"
                result_text += f"Используйте `/strategy_signals {ticker}` для получения сигналов"
            else:
                result_text = "❌ *ОШИБКА ЗАПУСКА*\n\n"
                result_text += f"Не удалось запустить стратегию *{strategy_id}*\n\n"
                result_text += "Возможные причины:\n"
                result_text += "• Неизвестная стратегия\n"
                result_text += "• Тикер не поддерживается\n"
                result_text += "• Стратегия уже активна"

            await loading_msg.edit_text(result_text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await loading_msg.edit_text(
                f"❌ Ошибка запуска стратегии: {str(e)}", parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Start strategy error: {e}")

    async def stop_strategy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stop_strategy."""
        if not context.args:
            await update.message.reply_text(
                "*🛑 ОСТАНОВКА СТРАТЕГИИ*\n\n"
                "Использование: `/stop_strategy STRATEGY_ID`\n\n"
                "Примеры:\n"
                "• `/stop_strategy rsi_mean_reversion`\n"
                "• `/stop_strategy macd_trend_following`\n\n"
                "Используйте `/strategy_status` для списка активных стратегий",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        strategy_id = context.args[0]

        try:
            from strategy_engine import get_strategy_engine

            engine = get_strategy_engine()

            success = engine.stop_strategy(strategy_id)

            if success:
                result_text = "✅ *СТРАТЕГИЯ ОСТАНОВЛЕНА*\n\n"
                result_text += f"🎯 Стратегия: *{strategy_id}*\n"
                result_text += f"⏰ Время остановки: {datetime.now().strftime('%H:%M:%S')}"
            else:
                result_text = "⚠️ *СТРАТЕГИЯ НЕ АКТИВНА*\n\n"
                result_text += f"Стратегия *{strategy_id}* не была запущена"

            await update.message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка остановки стратегии: {str(e)}", parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Stop strategy error: {e}")

    async def strategy_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /strategy_status."""
        try:
            from strategy_engine import get_strategy_engine

            engine = get_strategy_engine()

            active_strategies = engine.get_active_strategies()

            if not active_strategies:
                status_text = "*📊 СТАТУС СТРАТЕГИЙ*\n\n"
                status_text += "💤 *Нет активных стратегий*\n\n"
                status_text += "Используйте `/strategies` для просмотра доступных стратегий"
            else:
                status_text = f"*📊 АКТИВНЫЕ СТРАТЕГИИ ({len(active_strategies)})*\n\n"

                for strategy_id, info in active_strategies.items():
                    status_text += f"🟢 *{info['name']}*\n"
                    status_text += f"🆔 ID: `{strategy_id}`\n"
                    status_text += f"📈 Тикеры: {', '.join(info['supported_tickers'])}\n"
                    status_text += f"🎯 Сигналов: {info['signals_generated']}\n"

                    if info["last_execution"]:
                        last_exec = datetime.fromisoformat(info["last_execution"])
                        status_text += (
                            f"⏰ Последнее выполнение: {last_exec.strftime('%H:%M:%S')}\n"
                        )

                    status_text += "\n"

                status_text += "*💡 Команды:*\n"
                status_text += "• `/stop_strategy STRATEGY_ID` - остановить\n"
                status_text += "• `/strategy_signals TICKER` - получить сигналы"

            await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка получения статуса: {str(e)}", parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Strategy status error: {e}")

    async def strategy_signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /strategy_signals."""
        if not context.args:
            await update.message.reply_text(
                "*🎯 СТРАТЕГИЧЕСКИЕ СИГНАЛЫ*\n\n"
                "Использование: `/strategy_signals TICKER`\n\n"
                "Примеры:\n"
                "• `/strategy_signals SBER`\n"
                "• `/strategy_signals GAZP`\n\n"
                "Команда покажет сигналы от всех активных стратегий",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        ticker = context.args[0].upper()

        loading_msg = await update.message.reply_text(
            f"🎯 Генерирую стратегические сигналы для *{ticker}*...", parse_mode=ParseMode.MARKDOWN
        )

        try:
            from strategy_engine import get_strategy_engine

            engine = get_strategy_engine()

            # Генерируем сигналы
            result = await engine.execute_strategy_signals(ticker)

            if result["signals_count"] == 0:
                signals_text = f"*🎯 СТРАТЕГИЧЕСКИЕ СИГНАЛЫ {ticker}*\n\n"
                signals_text += "💤 *Нет активных стратегий*\n\n"
                signals_text += result["message"]
            else:
                signals_text = f"*🎯 СТРАТЕГИЧЕСКИЕ СИГНАЛЫ {ticker}*\n\n"

                # Итоговая рекомендация
                rec_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(
                    result["recommendation"], "⚪"
                )
                signals_text += f"{rec_emoji} *ИТОГОВАЯ РЕКОМЕНДАЦИЯ: {result['recommendation']}*\n"
                signals_text += f"🎯 Уверенность: {result['confidence']:.2f}\n"
                signals_text += f"📊 Сигналов проанализировано: {result['signals_count']}\n\n"

                # Детализация по сигналам
                if result["buy_signals"] > 0:
                    signals_text += f"🟢 BUY сигналов: {result['buy_signals']}\n"
                if result["sell_signals"] > 0:
                    signals_text += f"🔴 SELL сигналов: {result['sell_signals']}\n"

                signals_text += "\n*📋 ДЕТАЛИ СИГНАЛОВ:*\n"
                for signal in result["signals"]:
                    signal_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(
                        signal["action"], "⚪"
                    )
                    signals_text += f"{signal_emoji} {signal['strategy_id']}: {signal['action']} ({signal['confidence']:.2f})\n"

                signals_text += f"\n⏰ Время генерации: {datetime.now().strftime('%H:%M:%S')}"

            await loading_msg.edit_text(signals_text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await loading_msg.edit_text(
                f"❌ Ошибка генерации сигналов: {str(e)}", parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Strategy signals error: {e}")

    async def auto_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /auto_trading on/off."""
        if not context.args:
            await update.message.reply_text(
                "💡 *Управление автоматической торговлей*\n\n"
                "Использование:\n"
                "• `/auto_trading on` - включить автоматическую торговлю\n"
                "• `/auto_trading off` - выключить автоматическую торговлю\n"
                "• `/auto_trading status` - текущий статус\n\n"
                "⚠️ *Внимание:* Автоматическая торговля работает только с виртуальным портфелем",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        action = context.args[0].lower()

        try:
            from strategy_executor import get_strategy_executor

            executor = get_strategy_executor()

            if action == "on":
                from strategy_executor import ExecutionMode

                success = executor.enable_auto_trading(ExecutionMode.AUTOMATIC)
                if success:
                    text = "🤖 *АВТОМАТИЧЕСКАЯ ТОРГОВЛЯ ВКЛЮЧЕНА*\n\n"
                    text += "✅ Режим: Автоматическое исполнение\n"
                    text += f"⚙️ Мин. уверенность сигнала: {executor.min_confidence_threshold:.1%}\n"
                    text += f"🎯 Макс. размер позиции: {executor.max_position_size_pct:.1%}\n\n"
                    text += "💡 *Следующие шаги:*\n"
                    text += "• `/auto_execute SBER` - добавить тикер\n"
                    text += "• `/execution_status` - статус исполнений\n"
                    text += "• `/auto_settings` - настройки"
                else:
                    text = "❌ Не удалось включить автоматическую торговлю"

            elif action == "off":
                success = executor.disable_auto_trading()
                if success:
                    text = "⏹️ *АВТОМАТИЧЕСКАЯ ТОРГОВЛЯ ВЫКЛЮЧЕНА*\n\n"
                    text += "🔒 Все автоматические операции остановлены\n"
                    text += "📊 Портфель остается без изменений\n\n"
                    text += "💡 Используйте `/auto_trading on` для повторного включения"
                else:
                    text = "❌ Не удалось выключить автоматическую торговлю"

            elif action == "status":
                status = executor.get_execution_status()
                mode = status.get("execution_mode", "unknown")
                enabled_tickers = status.get("enabled_tickers", [])
                daily_executions = status.get("daily_executions", 0)
                max_daily = status.get("max_daily_trades", 5)

                text = "📊 *СТАТУС АВТОМАТИЧЕСКОЙ ТОРГОВЛИ*\n\n"
                text += f"🔄 Режим: {mode.upper()}\n"
                text += f"📈 Активных тикеров: {len(enabled_tickers)}\n"
                if enabled_tickers:
                    text += f"🎯 Тикеры: {', '.join(enabled_tickers)}\n"
                text += f"📊 Сделок сегодня: {daily_executions}/{max_daily}\n"
                text += f"⚙️ Мин. уверенность: {status.get('min_confidence_threshold', 0):.1%}"
            else:
                text = "❌ Неизвестное действие. Используйте: on, off, status"

            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка управления автоматической торговлей: {str(e)}",
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.error(f"Auto trading command error: {e}")

    def _handle_ticker_list(self, executor) -> str:
        """Обработка команды списка тикеров."""
        status = executor.get_execution_status()
        enabled_tickers = status.get("enabled_tickers", [])

        text = "📋 *ТИКЕРЫ ДЛЯ АВТОМАТИЧЕСКОГО ИСПОЛНЕНИЯ*\n\n"
        if enabled_tickers:
            text += "✅ Активные тикеры:\n"
            for ticker in enabled_tickers:
                text += f"  • {ticker}\n"
        else:
            text += "❌ Нет активных тикеров\n"
        text += "\n💡 Используйте `/auto_execute TICKER` для добавления"
        return text

    def _handle_ticker_remove(self, executor, ticker: str) -> str:
        """Обработка удаления тикера."""
        success = executor.remove_ticker_from_execution(ticker)
        if success:
            return f"✅ Тикер *{ticker}* удален из автоматического исполнения"
        else:
            return f"❌ Не удалось удалить тикер {ticker}"

    def _handle_ticker_add(self, executor, ticker: str) -> str:
        """Обработка добавления тикера."""
        supported_tickers = ["SBER", "GAZP", "YNDX", "LKOH", "ROSN", "NVTK", "GMKN"]

        if ticker not in supported_tickers:
            text = f"❌ Тикер {ticker} не поддерживается\n\n"
            text += f"Поддерживаемые: {', '.join(supported_tickers)}"
            return text

        success = executor.add_ticker_for_execution(ticker)
        if success:
            text = f"✅ *{ticker}* добавлен для автоматического исполнения\n\n"
            text += f"🤖 Теперь торговые сигналы для {ticker} будут исполняться автоматически\n"
            text += "⚙️ При условии превышения порога уверенности\n\n"
            text += "💡 Проверьте статус: `/execution_status`"
            return text
        else:
            return f"❌ Не удалось добавить тикер {ticker}"

    async def auto_execute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /auto_execute TICKER."""
        if not context.args:
            await update.message.reply_text(
                "🎯 *Управление автоматическим исполнением*\n\n"
                "Использование:\n"
                "• `/auto_execute SBER` - добавить SBER к автоматическому исполнению\n"
                "• `/auto_execute remove SBER` - убрать SBER из автоматического исполнения\n"
                "• `/auto_execute list` - список активных тикеров\n\n"
                "Поддерживаемые тикеры: SBER, GAZP, YNDX, LKOH, ROSN, NVTK, GMKN",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        try:
            from strategy_executor import get_strategy_executor

            executor = get_strategy_executor()

            if context.args[0].lower() == "list":
                text = self._handle_ticker_list(executor)
            elif len(context.args) >= 2 and context.args[0].lower() == "remove":
                ticker = context.args[1].upper()
                text = self._handle_ticker_remove(executor, ticker)
            else:
                ticker = context.args[0].upper()
                text = self._handle_ticker_add(executor, ticker)

            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка управления тикерами: {str(e)}", parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Auto execute command error: {e}")

    async def execution_status_command(self, update: Update, context:ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /execution_status."""
        try:
            from strategy_executor import get_strategy_executor

            executor = get_strategy_executor()

            status = executor.get_execution_status()

            text = "📊 *СТАТУС АВТОМАТИЧЕСКОГО ИСПОЛНЕНИЯ*\n\n"

            # Основная информация
            mode = status.get("execution_mode", "unknown")
            enabled_tickers = status.get("enabled_tickers", [])
            daily_executions = status.get("daily_executions", 0)
            max_daily = status.get("max_daily_trades", 5)
            total_executions = status.get("total_executions", 0)

            if mode == "automatic":
                text += "🟢 Режим: АВТОМАТИЧЕСКОЕ ИСПОЛНЕНИЕ\n"
            elif mode == "disabled":
                text += "🔴 Режим: ОТКЛЮЧЕНО\n"
            else:
                text += f"🟡 Режим: {mode.upper()}\n"

            text += f"📈 Активных тикеров: {len(enabled_tickers)}\n"
            if enabled_tickers:
                text += f"🎯 Тикеры: {', '.join(enabled_tickers)}\n"

            text += f"📊 Исполнений сегодня: {daily_executions}/{max_daily}\n"
            text += f"📈 Всего исполнений: {total_executions}\n"
            text += f"⚙️ Мин. уверенность: {status.get('min_confidence_threshold', 0):.1%}\n\n"

            # Последние исполнения
            recent_executions = status.get("recent_executions", [])
            if recent_executions:
                text += "📋 *ПОСЛЕДНИЕ ИСПОЛНЕНИЯ:*\n"
                for execution in recent_executions[-5:]:  # Последние 5
                    ticker = execution.get("ticker", "N/A")
                    action = execution.get("signal_action", "N/A")
                    status_exec = execution.get("status", "N/A")
                    confidence = execution.get("signal_confidence", 0)

                    if status_exec == "executed":
                        emoji = "✅"
                    elif status_exec == "rejected":
                        emoji = "⚠️"
                    else:
                        emoji = "❌"

                    text += f"{emoji} {ticker}: {action} (уверенность: {confidence:.2f})\n"
            else:
                text += "📋 *Исполнений пока не было*\n"

            text += "\n💡 *Команды управления:*\n"
            text += "• `/auto_trading on/off` - включить/выключить\n"
            text += "• `/auto_execute TICKER` - добавить тикер\n"
            text += "• `/auto_settings` - настройки"

            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка получения статуса: {str(e)}", parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Execution status command error: {e}")

    async def auto_settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /auto_settings."""
        try:
            from strategy_executor import get_strategy_executor

            executor = get_strategy_executor()

            text = "⚙️ *НАСТРОЙКИ АВТОМАТИЧЕСКОЙ ТОРГОВЛИ*\n\n"

            text += "🎯 *Основные параметры:*\n"
            text += f"• Мин. уверенность сигнала: {executor.min_confidence_threshold:.1%}\n"
            text += f"• Макс. размер позиции: {executor.max_position_size_pct:.1%}\n"
            text += f"• Макс. сделок в день: {executor.get_execution_status().get('max_daily_trades', 5)}\n\n"

            text += "🛡️ *Риск-менеджмент:*\n"
            text += "• Виртуальный портфель: 1,000,000 ₽\n"
            text += "• Комиссия: 0.05%\n"
            text += "• Автоматические лимиты активны\n\n"

            text += "🤖 *Поддерживаемые стратегии:*\n"
            text += "• RSI Mean Reversion\n"
            text += "• MACD Trend Following\n\n"

            text += "📊 *Поддерживаемые активы:*\n"
            text += "• SBER - ПАО Сбербанк\n"
            text += "• GAZP - ПАО Газпром\n"
            text += "• YNDX - Яндекс\n"
            text += "• LKOH - ЛУКОЙЛ\n"
            text += "• ROSN - Роснефть\n"
            text += "• NVTK - НОВАТЭК\n"
            text += "• GMKN - ГМК Норильский никель\n\n"

            text += "⚠️ *Важные ограничения:*\n"
            text += "• Работа только в песочнице Tinkoff\n"
            text += "• Только виртуальные сделки\n"
            text += "• Автоматическая остановка при достижении лимитов\n\n"

            text += "💡 *Рекомендации:*\n"
            text += "• Начните с одного тикера\n"
            text += "• Следите за `/execution_status`\n"
            text += "• Регулярно проверяйте `/portfolio`"

            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка получения настроек: {str(e)}", parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Auto settings command error: {e}")

    async def portfolio_strategies_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /portfolio_strategies."""
        try:
            coordinator = self.portfolio_coordinator
            allocations = coordinator.get_strategy_allocations()
            status = coordinator.get_portfolio_status()

            if not allocations:
                text = """
📊 *ПОРТФЕЛЬ СТРАТЕГИЙ*

❌ В портфеле нет активных стратегий

💡 *Доступные команды:*
- `/coordinate_portfolio` - запустить координацию
- `/strategy_weights` - управление весами
- `/portfolio_performance` - производительность

*Для добавления стратегий используйте существующие команды Strategy Engine.*
                """
            else:
                text = f"""
📊 *АКТИВНЫЕ СТРАТЕГИИ ПОРТФЕЛЯ*

📈 *Общий статус:*
- Всего стратегий: {status.total_strategies}
- Активных: {status.active_strategies}
- Средняя производительность: {status.performance_score:.2%}
- Денежные средства: {status.cash_allocation:.1%}

"""

                for i, (key, allocation) in enumerate(allocations.items(), 1):
                    strategy_name = allocation.strategy_id.replace('_', ' ').title()
                    text += f"""
🎯 *{i}. {strategy_name} ({allocation.ticker}):*
- Вес в портфеле: {allocation.weight:.1%}
- Целевое распределение: {allocation.target_allocation:.1%}
- Текущее распределение: {allocation.current_allocation:.1%}
- Производительность: {allocation.performance_score:.2%}
- Последняя ребалансировка: {allocation.last_rebalance.strftime('%H:%M %d.%m')}

"""

                text += f"""
📊 *Координация:*
- Статус: {'🟢 Включена' if coordinator.enabled else '🔴 Отключена'}
- Метод весов: {coordinator.weight_method.value.replace('_', ' ').title()}
- Последняя координация: {coordinator.last_coordination.strftime('%H:%M %d.%m') if coordinator.last_coordination else 'Не выполнялась'}

💡 *Команды:*
- `/coordinate_portfolio` - запустить координацию
- `/strategy_weights` - настройки весов
- `/portfolio_performance` - детальная аналитика
                """

            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка получения стратегий портфеля: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Portfolio strategies command error: {e}")

    async def strategy_weights_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /strategy_weights."""
        try:
            coordinator = self.portfolio_coordinator
            allocations = coordinator.get_strategy_allocations()

            if not allocations:
                text = """
⚖️ *УПРАВЛЕНИЕ ВЕСАМИ СТРАТЕГИЙ*

❌ В портфеле нет стратегий для управления весами

💡 Сначала добавьте стратегии через команды Strategy Engine, затем используйте координацию портфеля.
                """
            else:
                text = f"""
⚖️ *ВЕСА СТРАТЕГИЙ В ПОРТФЕЛЕ*

📊 *Текущий метод:* {coordinator.weight_method.value.replace('_', ' ').title()}
🎯 *Порог ребалансировки:* {coordinator.rebalance_threshold:.1%}

"""

                total_weight = sum(a.weight for a in allocations.values())

                for key, allocation in allocations.items():
                    strategy_name = allocation.strategy_id.replace('_', ' ').title()
                    weight_pct = allocation.weight * 100
                    target_pct = allocation.target_allocation * 100
                    current_pct = allocation.current_allocation * 100

                    deviation = abs(current_pct - target_pct)
                    status_emoji = "🟢" if deviation <= coordinator.rebalance_threshold * 100 else "🟡"

                    text += f"""
{status_emoji} *{strategy_name} ({allocation.ticker}):*
- Текущий вес: {weight_pct:.1f}%
- Целевое распределение: {target_pct:.1f}%
- Фактическое распределение: {current_pct:.1f}%
- Отклонение: {deviation:.1f}%

"""

                text += f"""
📊 *Итого распределено:* {total_weight:.1%}
💰 *Свободные средства:* {(1-total_weight):.1%}

💡 *Доступные действия:*
- `/coordinate_portfolio` - выполнить ребалансировку
- Автоматическая ребалансировка при отклонении > {coordinator.rebalance_threshold:.1%}
                """

            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка получения весов стратегий: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Strategy weights command error: {e}")

    async def coordinate_portfolio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /coordinate_portfolio."""
        loading_msg = await update.message.reply_text(
            "🔄 Выполняем координацию портфеля...\n"
            "📊 Анализируем стратегии и агрегируем сигналы...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            coordinator = self.portfolio_coordinator

            # Включаем координацию если она отключена
            if not coordinator.enabled:
                from portfolio_coordinator import StrategyWeight
                coordinator.enable_coordination(StrategyWeight.EQUAL)

            # Выполняем координацию
            result = await coordinator.coordinate_portfolio()

            if result["success"]:
                text = f"""✅ *КООРДИНАЦИЯ ПОРТФЕЛЯ ЗАВЕРШЕНА*

📊 *Результаты:*
- Обработано стратегий: {result['strategies_count']}
- Общий вес стратегий: {result['total_weight']:.1f}
- Статус координации: {result['coordination_status']}
- Время выполнения: Не указано

💡 *Следующие шаги:*
- /portfolio_strategies - просмотр результатов
- /strategy_weights - проверка распределения
- /portfolio_performance - анализ производительности"""

            else:
                text = f"""
❌ *ОШИБКА КООРДИНАЦИИ ПОРТФЕЛЯ*

Причина: {result.get('message', 'Неизвестная ошибка')}

💡 Попробуйте:
- Проверить активные стратегии: `/portfolio_strategies`
- Проверить состояние системы: `/status`
                """

            await loading_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await loading_msg.edit_text(
                f"❌ Ошибка координации портфеля: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Coordinate portfolio command error: {e}")

    async def portfolio_performance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /portfolio_performance."""
        loading_msg = await update.message.reply_text(
            "📊 Анализируем производительность портфеля...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            coordinator = self.portfolio_coordinator
            status = coordinator.get_portfolio_status()
            allocations = coordinator.get_strategy_allocations()

            if not allocations:
                text = """
📊 *ПРОИЗВОДИТЕЛЬНОСТЬ ПОРТФЕЛЯ*

❌ В портфеле нет стратегий для анализа

💡 Добавьте стратегии и дайте им поработать для получения метрик производительности.
                """
            else:
                # Получаем аналитику портфеля
                try:
                    analytics = await self.portfolio_analytics.calculate_comprehensive_metrics()
                except:
                    analytics = None

                text = f"""
📊 *ПРОИЗВОДИТЕЛЬНОСТЬ ПОРТФЕЛЯ*

📈 *Общие метрики:*
- Всего стратегий: {status.total_strategies}
- Активных стратегий: {status.active_strategies}
- Средняя производительность: {status.performance_score:.2%}
- Средний риск: {status.risk_score:.2f}/1.0
- Распределение активов: {status.total_allocation:.1%}

"""

                if analytics and 'returns' in analytics:
                    returns = analytics['returns']
                    risk_metrics = analytics.get('risk_metrics', {})

                    text += f"""
💰 *Доходность:*
- Общая доходность: {returns.get('total_return', 0):.2%}
- Годовая доходность: {returns.get('annualized_return', 0):.2%}

🛡️ *Риски:*
- Волатильность: {risk_metrics.get('volatility', 0):.1%}
- Максимальная просадка: {risk_metrics.get('max_drawdown', 0):.1%}
- Sharpe ratio: {risk_metrics.get('sharpe_ratio', 0):.2f}

"""

                # Производительность по стратегиям
                text += "🎯 *По стратегиям:*\n"
                for key, allocation in allocations.items():
                    strategy_name = allocation.strategy_id.replace('_', ' ').title()
                    perf_icon = "📈" if allocation.performance_score > 0 else "📉" if allocation.performance_score < 0 else "➖"
                    risk_icon = "🟢" if allocation.risk_score < 0.3 else "🟡" if allocation.risk_score < 0.7 else "🔴"

                    text += f"""
{perf_icon} *{strategy_name} ({allocation.ticker}):*
- Производительность: {allocation.performance_score:.2%}
- Риск: {risk_icon} {allocation.risk_score:.2f}
- Вес: {allocation.weight:.1%}

"""

                text += f"""
📅 *Временные метрики:*
- Последняя ребалансировка: {status.last_rebalance.strftime('%H:%M %d.%m.%Y')}
- Интервал координации: {coordinator.coordination_interval.total_seconds()/3600:.0f} часов

💡 *Команды для улучшения:*
- `/coordinate_portfolio` - оптимизация распределения
- `/strategy_weights` - настройка весов
                """

            await loading_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            await loading_msg.edit_text(
                f"❌ Ошибка анализа производительности: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Portfolio performance command error: {e}")

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик неизвестных команд."""
        await update.message.reply_text(
            "🤔 Не понимаю эту команду.\n"
            "Воспользуйтесь /help для списка доступных команд."
        )
        logger.warning(f"Получена неизвестная команда: {update.message.text}")

    def setup_handlers(self, app: Application):
        """Настройка обработчиков команд"""
        # Команды для всех пользователей
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("price", self.price_command))
        app.add_handler(CommandHandler("accounts", self.accounts_command))
        app.add_handler(CommandHandler("news", self.news_command))
        app.add_handler(CommandHandler("risk", self.risk_command))
        # Команды портфеля
        app.add_handler(CommandHandler("portfolio", self.portfolio_command))
        app.add_handler(CommandHandler("analytics", self.analytics_command))
        app.add_handler(CommandHandler("buy", self.buy_command))
        app.add_handler(CommandHandler("sell", self.sell_command))
        # Команды анализа
        app.add_handler(CommandHandler("analysis", self.analysis_command))
        app.add_handler(CommandHandler("signal", self.signal_command))
        # Команды стратегий
        app.add_handler(CommandHandler("strategies", self.strategies_command))
        app.add_handler(CommandHandler("start_strategy", self.start_strategy_command))
        app.add_handler(CommandHandler("stop_strategy", self.stop_strategy_command))
        app.add_handler(CommandHandler("strategy_status", self.strategy_status_command))
        app.add_handler(CommandHandler("strategy_signals", self.strategy_signals_command))
        # Команды StrategyExecutor
        app.add_handler(CommandHandler("auto_trading", self.auto_trading_command))
        app.add_handler(CommandHandler("auto_execute", self.auto_execute_command))
        app.add_handler(CommandHandler("execution_status", self.execution_status_command))
        app.add_handler(CommandHandler("auto_settings", self.auto_settings_command))

        # Portfolio coordination commands
        app.add_handler(CommandHandler("portfolio_strategies", self.portfolio_strategies_command))
        app.add_handler(CommandHandler("strategy_weights", self.strategy_weights_command))
        app.add_handler(CommandHandler("coordinate_portfolio", self.coordinate_portfolio_command))
        app.add_handler(CommandHandler("portfolio_performance", self.portfolio_performance_command))
        # Обработчик текстовых сообщений
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.help_command))
        logger.info("✅ Обработчики команд настроены")

    def run(self):
        """Запуск бота"""
        try:
            logger.info("🚀 Запуск Trading Bot...")
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers(self.application)
            self.application.run_polling()
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске бота: {e}")


if __name__ == "__main__":
    bot = TradingTelegramBot()
    bot.run()