from datetime import datetime

"""
Telegram Bot для управления торговым ботом
Полная базовая версия с основными командами и интеграцией
"""

import logging
from typing import List

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
from risk_manager import RiskManager
from signal_generator import get_trading_signal_for_telegram
from tinkoff_client import TinkoffClient
from portfolio_manager import PortfolioManager
from trading_engine import TradingEngine, TradingMode

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
🤖 **Автоматизация:**
• `/automation` - настройки автоматизации
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
            await update.message.reply_text("🔍 Ищу цену для {ticker}...")
            logger.info("Запрос цены для тикера: {ticker}")
            # Ищем инструмент
            instrument = self.tinkoff_client.search_instrument(ticker)
            if not instrument:
                await update.message.reply_text("❌ Акция {ticker} не найдена. Проверьте тикер.")
                logger.warning("Инструмент {ticker} не найден")
                return
            # Получаем цену
            price_data = self.tinkoff_client.get_last_price(instrument.figi)
            if not price_data:
                await update.message.reply_text(
                    "❌ Не удалось получить цену для {ticker}. Попробуйте позже."
                )
                logger.error("Не удалось получить цену для {ticker}")
                return
            # Конвертируем цену
            price_rub = price_data.price.units + price_data.price.nano / 1_000_000_000
            price_message = f"""
💰 **{instrument.name}**
📊 **Цена:** {price_rub:.2f} ₽
🎯 **Тикер:** {ticker}
🔗 **FIGI:** `{instrument.figi}`
⏰ Данные актуальны на: сейчас
"""
            await update.message.reply_text(price_message, parse_mode="Markdown")
            logger.info("Цена {ticker} успешно получена: {price_rub:.2f} ₽")
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
            return """📰 <b>НОВОСТИ ПО {ticker}</b>
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
            sources_text += " и ещё {len(sources) - 3}"
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
        result_text += """🕐 <b>Время анализа:</b> {ticker} проанализирован
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
            accounts_message = "💼 **Ваши торговые счета** ({len(accounts)} шт.)\n\n"
            for i, account in enumerate(accounts, 1):
                account_id = account.id
                account_name = account.name if account.name else "Счет {i}"
                account_type = account.type.name if hasattr(account, "type") else "UNSPECIFIED"
                accounts_message += f"""
**🏦 Счет {i}:**
📝 Название: {account_name}
🆔 ID: `{account_id}`
📋 Тип: {account_type}
🏛️ Режим: Песочница
---
                """
            accounts_message += """
✅ **Всего активных счетов:** {len(accounts)}
🛡️ **Безопасность:** Все операции в песочнице
💡 **Следующий шаг:** Попробуйте `/price SBER`
⚠️ **Помните:** Это тестовые счета, реальные деньги не используются!
            """
            await update.message.reply_text(accounts_message, parse_mode="Markdown")
            logger.info("Список счетов успешно отправлен: {len(accounts)} счетов")
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
                "🔍 Ищу новости о <b>{ticker}</b>...\n" "🤖 Анализирую через Perplexity AI...",
                parse_mode="HTML",
            )
            try:
                from perplexity_client import PerplexityClient

                perplexity = PerplexityClient()
                news_results = perplexity.search_ticker_news(ticker, hours=24)
                result_text = await self._format_news_result(ticker, news_results)
            except ImportError:
                result_text = """❌ <b>PERPLEXITY CLIENT НЕ НАЙДЕН</b>
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
            logger.info("Команда news выполнена для {ticker}")
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
                "❌ Акция с тикером *{ticker}* не найдена.\n\n"
                "Попробуйте: SBER, GAZP, YNDX, LKOH, NVTK, ROSN",
                parse_mode=ParseMode.MARKDOWN,
            )
            return None

        price_data = self.tinkoff_client.get_last_price(instrument.figi)
        if not price_data:
            await loading_msg.edit_text(
                "❌ Не удалось получить цену для {ticker}", parse_mode=ParseMode.MARKDOWN
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
            "🔍 Анализирую риски для *{ticker}*...\n"
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
                "Анализ рисков {ticker} завершен: риск {position_analysis.get('risk_percent', 0):.2f}%"
            )

        except Exception as e:
            error_msg = "❌ *Ошибка анализа рисков {ticker}*\n\n"
            error_msg += "Причина: {str(e)}\n\n"
            error_msg += "💡 Попробуйте:\n"
            error_msg += "• Проверить правильность тикера\n"
            error_msg += "• Использовать `/risk SBER 100 93` с параметрами\n"
            error_msg += "• Повторить запрос через несколько секунд"

            await loading_msg.edit_text(error_msg, parse_mode=ParseMode.MARKDOWN)
            logger.error(f"Risk command error for {ticker}: {e}")

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
            parse_mode=ParseMode.MARKDOWN
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

            await loading_msg.edit_text(
                result_text,
                parse_mode=None
            )

            logger.info(f"Аналитика портфеля отправлена: {metrics.positions_count} позиций, "
                       f"Sharpe {metrics.sharpe_ratio:.2f}")

        except Exception as e:
            error_msg = "❌ *Ошибка расчета аналитики портфеля*\n\n"
            error_msg += f"Причина: {str(e)}\n\n"
            error_msg += "💡 Попробуйте:\n"
            error_msg += "• Убедиться что есть позиции в портфеле\n"
            error_msg += "• Повторить запрос через несколько секунд\n"
            error_msg += "• Использовать /portfolio для проверки позиций"

            await loading_msg.edit_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN
            )
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
                parse_mode=ParseMode.MARKDOWN
            )

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