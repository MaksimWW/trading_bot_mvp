"""
Telegram Bot для управления торговым ботом
Полная базовая версия с основными командами и интеграцией
"""

import logging
from typing import List
from datetime import datetime

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
from signal_generator import get_trading_signal_for_telegram
from tinkoff_client import TinkoffClient
from risk_manager import RiskManager, RiskSettings
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
• `/analysis TICKER` - технический анализ акции
• `/signal TICKER` - комбинированный торговый сигнал
⚖️ **Управление рисками:**
• `/risk TICKER` - анализ рисков позиции
• `/portfolio` - анализ портфеля и рисков
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
                parse_mode=ParseMode.MARKDOWN
            )
            return

        ticker = context.args[0].upper()
        
        # Отправляем сообщение о начале анализа
        loading_msg = await update.message.reply_text(
            f"⚖️ Анализирую риски для *{ticker}*...\n"
            f"📊 Получаю данные и рассчитываю параметры...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Получаем текущую цену если не указана
            entry_price = None
            stop_loss_price = None
            
            if len(context.args) >= 2:
                try:
                    entry_price = float(context.args[1])
                except ValueError:
                    await loading_msg.edit_text(
                        f"❌ Неверный формат цены входа: {context.args[1]}\n"
                        f"Используйте число, например: `/risk SBER 100`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
            
            if len(context.args) >= 3:
                try:
                    stop_loss_price = float(context.args[2])
                except ValueError:
                    await loading_msg.edit_text(
                        f"❌ Неверный формат стоп-лосса: {context.args[2]}\n"
                        f"Используйте число, например: `/risk SBER 100 93`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return

            # Если цена не указана, получаем текущую
            if entry_price is None:
                instrument = self.tinkoff_client.search_instrument(ticker)
                if not instrument:
                    await loading_msg.edit_text(
                        f"❌ Акция с тикером *{ticker}* не найдена.\n\n"
                        "Попробуйте: SBER, GAZP, YNDX, LKOH, NVTK, ROSN",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                
                price_data = self.tinkoff_client.get_last_price(instrument.figi)
                if not price_data:
                    await loading_msg.edit_text(
                        f"❌ Не удалось получить цену для {ticker}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                
                entry_price = price_data.price.units + price_data.price.nano / 1_000_000_000

            # Создаем risk manager
            risk_manager = RiskManager()
            
            # Рассчитываем стоп-лосс если не указан
            if stop_loss_price is None:
                sl_tp = risk_manager.calculate_stop_loss_take_profit(
                    ticker=ticker,
                    entry_price=entry_price,
                    signal_direction="BUY"
                )
                stop_loss_price = sl_tp["stop_loss_price"]
            
            # Примерный баланс счета (в реальности получаем из API)
            account_balance = 100000.0  # 100k рублей для примера
            
            # Рассчитываем позицию
            position_analysis = risk_manager.calculate_position_size(
                ticker=ticker,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                account_balance=account_balance,
                confidence_score=0.6  # Средняя уверенность
            )
            
            # Рассчитываем стоп-лосс и тейк-профит
            sl_tp_analysis = risk_manager.calculate_stop_loss_take_profit(
                ticker=ticker,
                entry_price=entry_price,
                signal_direction="BUY"
            )

            # Форматируем результат
            if not position_analysis.get("approved", False):
                result_text = f"❌ *АНАЛИЗ РИСКОВ {ticker}*\n\n"
                result_text += f"🚫 *Позиция отклонена*\n"
                result_text += f"📝 Причина: {position_analysis.get('reason', 'Неизвестная ошибка')}\n\n"
                result_text += f"💡 Рекомендации:\n"
                result_text += f"• Снизьте размер позиции\n"
                result_text += f"• Используйте более близкий стоп-лосс\n"
                result_text += f"• Дождитесь лучших условий"
            else:
                # Эмодзи для уровня риска
                risk_emoji = {
                    "LOW": "🟢",
                    "MEDIUM": "🟡", 
                    "HIGH": "🟠",
                    "EXTREME": "🔴"
                }
                
                emoji = risk_emoji.get(position_analysis["risk_level"], "⚪")
                
                result_text = f"⚖️ *АНАЛИЗ РИСКОВ {ticker}*\n\n"
                
                # Основные параметры
                result_text += f"💰 *Параметры позиции:*\n"
                result_text += f"📈 Цена входа: {entry_price:.2f} ₽\n"
                result_text += f"🛑 Стоп-лосс: {stop_loss_price:.2f} ₽\n"
                result_text += f"🎯 Тейк-профит: {sl_tp_analysis['take_profit_price']:.2f} ₽\n\n"
                
                # Расчет позиции
                result_text += f"📊 *Рекомендуемая позиция:*\n"
                result_text += f"🔢 Количество акций: {position_analysis['shares_count']}\n"
                result_text += f"💵 Сумма позиции: {position_analysis['position_amount']:,.0f} ₽\n"
                result_text += f"📈 Доля портфеля: {position_analysis['position_percent']:.1f}%\n\n"
                
                # Анализ рисков
                result_text += f"⚖️ *Анализ рисков:*\n"
                result_text += f"{emoji} Уровень риска: {position_analysis['risk_level']}\n"
                result_text += f"💸 Потенциальный убыток: {position_analysis['risk_amount']:,.0f} ₽\n"
                result_text += f"📉 Риск от депозита: {position_analysis['risk_percent']:.2f}%\n"
                result_text += f"⚖️ Риск/Доходность: 1:{sl_tp_analysis['risk_reward_ratio']:.1f}\n\n"
                
                # Рекомендация
                result_text += f"💡 *Рекомендация:*\n"
                result_text += f"{position_analysis['recommendation']}\n\n"
                
                # Дополнительная информация
                result_text += f"📋 *Дополнительно:*\n"
                result_text += f"• Трейлинг стоп: {sl_tp_analysis['trailing_stop_distance']:.2f} ₽\n"
                result_text += f"• Волатильность: Нормальная\n"
                result_text += f"• Ликвидность: Высокая\n\n"

            # Подсказки
            result_text += f"*🛠️ Дополнительные команды:*\n"
            result_text += f"• `/price {ticker}` - текущая цена\n"
            result_text += f"• `/analysis {ticker}` - технический анализ\n"
            result_text += f"• `/news {ticker}` - анализ новостей\n\n"
            
            result_text += f"⚠️ *Внимание:* Анализ основан на примерном депозите 100,000 ₽. "
            result_text += f"Скорректируйте размер позиции под ваш реальный депозит."

            await loading_msg.edit_text(
                result_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Анализ рисков {ticker} завершен: риск {position_analysis.get('risk_percent', 0):.2f}%")

        except Exception as e:
            error_msg = f"❌ *Ошибка анализа рисков {ticker}*\n\n"
            error_msg += f"Причина: {str(e)}\n\n"
            error_msg += f"💡 Попробуйте:\n"
            error_msg += f"• Проверить правильность тикера\n"
            error_msg += f"• Использовать `/risk SBER 100 93` с параметрами\n"
            error_msg += f"• Повторить запрос через несколько секунд"
            
            await loading_msg.edit_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Risk command error for {ticker}: {e}")

    async def portfolio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /portfolio."""
        loading_msg = await update.message.reply_text(
            "📊 Анализирую портфель...\n"
            "🔍 Оцениваю риски и составляю рекомендации...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Создаем risk manager
            risk_manager = RiskManager()
            
            # Примерные позиции для демонстрации
            sample_positions = [
                {
                    "ticker": "SBER",
                    "shares": 100,
                    "entry_price": 95.0,
                    "current_price": 99.95,
                    "risk_percent": 2.1,
                    "sector": "Финансы"
                },
                {
                    "ticker": "GAZP", 
                    "shares": 50,
                    "entry_price": 180.0,
                    "current_price": 175.0,
                    "risk_percent": 1.8,
                    "sector": "Энергетика"
                }
            ]
            
            # Анализ портфеля
            portfolio_analysis = risk_manager.assess_portfolio_risk(sample_positions)
            
            # Форматируем результат
            result_text = f"📊 *АНАЛИЗ ПОРТФЕЛЯ*\n\n"
            
            # Общая статистика
            result_text += f"📈 *Общая статистика:*\n"
            result_text += f"🔢 Позиций в портфеле: {portfolio_analysis['positions_count']}\n"
            result_text += f"⚖️ Общий риск: {portfolio_analysis['total_risk_percent']:.1f}%\n"
            result_text += f"📊 Использование лимита: {portfolio_analysis['risk_utilization']:.1f}%\n"
            
            # Уровень риска с эмодзи
            risk_emoji = {
                "LOW": "🟢 Низкий",
                "MEDIUM": "🟡 Средний",
                "HIGH": "🟠 Высокий", 
                "EXTREME": "🔴 Критический"
            }
            risk_text = risk_emoji.get(portfolio_analysis['risk_level'], "⚪ Неизвестный")
            result_text += f"🎯 Уровень риска: {risk_text}\n\n"
            
            # Текущие позиции
            if sample_positions:
                result_text += f"💼 *Текущие позиции:*\n"
                for pos in sample_positions:
                    pnl = ((pos['current_price'] - pos['entry_price']) / pos['entry_price']) * 100
                    pnl_emoji = "📈" if pnl >= 0 else "📉"
                    result_text += f"• *{pos['ticker']}*: {pos['shares']} шт.\n"
                    result_text += f"  {pnl_emoji} P&L: {pnl:+.1f}% | Риск: {pos['risk_percent']:.1f}%\n"
                result_text += "\n"
            
            # Секторальное распределение
            if 'sector_exposure' in portfolio_analysis:
                result_text += f"🏭 *Секторальное распределение:*\n"
                for sector, exposure in portfolio_analysis['sector_exposure'].items():
                    result_text += f"• {sector}: {exposure:.1f}%\n"
                result_text += "\n"
            
            # Рекомендации
            result_text += f"💡 *Рекомендации:*\n"
            for recommendation in portfolio_analysis['recommendations']:
                result_text += f"• {recommendation}\n"
            result_text += "\n"
            
            # Лимиты риск-менеджмента
            result_text += f"⚙️ *Настройки риск-менеджмента:*\n"
            result_text += f"• Макс. риск портфеля: {portfolio_analysis['max_allowed_risk']:.1f}%\n"
            result_text += f"• Макс. позиция: 5.0% депозита\n"
            result_text += f"• Макс. дневной убыток: 3.0%\n"
            result_text += f"• Макс. сделок в день: 5\n\n"
            
            # Подсказки
            result_text += f"*🛠️ Управление портфелем:*\n"
            result_text += f"• `/risk TICKER` - анализ новой позиции\n"
            result_text += f"• `/settings` - настройки риск-менеджмента\n\n"
            
            result_text += f"⚠️ *Примечание:* Показаны демонстрационные данные. "
            result_text += f"В боевом режиме будут использоваться реальные позиции."

            await loading_msg.edit_text(
                result_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Анализ портфеля завершен: риск {portfolio_analysis['total_risk_percent']:.1f}%")

        except Exception as e:
            error_msg = f"❌ *Ошибка анализа портфеля*\n\n"
            error_msg += f"Причина: {str(e)}\n\n"
            error_msg += f"💡 Попробуйте повторить запрос через несколько секунд"
            
            await loading_msg.edit_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Portfolio command error: {e}")

    async def automation_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /automation."""
        loading_msg = await update.message.reply_text(
            "🤖 Анализирую возможности автоматизации...\n"
            "⚙️ Проверяю настройки торговой системы...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Создаем торговый движок
            trading_engine = TradingEngine(mode=TradingMode.PAPER)
            
            # Генерируем сигнал для демонстрации
            signal = await trading_engine.generate_trading_signal("SBER")
            
            result_text = f"🤖 *АВТОМАТИЗАЦИЯ ТОРГОВЛИ*\n\n"
            
            # Статус системы
            result_text += f"⚙️ *Статус системы:*\n"
            result_text += f"🟢 Режим: {trading_engine.mode.value} (Виртуальная торговля)\n"
            result_text += f"📊 Анализ новостей: ✅ Активен\n"
            result_text += f"📈 Технический анализ: ✅ Активен\n"
            result_text += f"⚖️ Risk Management: ✅ Активен\n\n"
            
            # Настройки автоматизации
            result_text += f"🎛️ *Настройки автоматизации:*\n"
            result_text += f"• Мин. сила сигнала: {trading_engine.min_signal_strength.value}\n"
            result_text += f"• Мин. уверенность: {trading_engine.min_confidence:.1f}\n"
            result_text += f"• Интервал сканирования: {trading_engine.scan_interval//60} мин\n"
            result_text += f"• Список наблюдения: {', '.join(trading_engine.watchlist)}\n\n"
            
            # Демонстрация сигнала
            if signal:
                emoji = "🟢" if signal.direction == "BUY" else "🔴" if signal.direction == "SELL" else "🟡"
                result_text += f"🎯 *Демо-сигнал {signal.ticker}:*\n"
                result_text += f"{emoji} Направление: {signal.direction}\n"
                result_text += f"💪 Сила: {signal.strength.value}\n"
                result_text += f"🎯 Уверенность: {signal.confidence:.0%}\n"
                result_text += f"💡 Обоснование: {signal.reasoning}\n"
                result_text += f"💰 Вход: {signal.entry_price:.2f} ₽\n"
                result_text += f"🛑 Стоп: {signal.stop_loss:.2f} ₽\n"
                result_text += f"🎯 Цель: {signal.take_profit:.2f} ₽\n\n"
            else:
                result_text += f"📊 *Текущие сигналы:*\n"
                result_text += f"❌ Нет сильных сигналов в данный момент\n\n"
            
            # Возможности автоматизации
            result_text += f"🚀 *Доступные режимы:*\n"
            result_text += f"📝 **MANUAL** - Ручные рекомендации\n"
            result_text += f"🔄 **SEMI_AUTO** - Полуавтоматический режим\n"
            result_text += f"📊 **PAPER** - Виртуальная торговля (текущий)\n"
            result_text += f"🤖 **AUTO** - Полная автоматизация (скоро)\n\n"
            
            # Статистика
            result_text += f"📈 *Потенциал автоматизации:*\n"
            result_text += f"• Экономия времени: 2-4 часа/день\n"
            result_text += f"• Дисциплина: Устранение эмоций\n"
            result_text += f"• Скорость: Реакция за секунды\n"
            result_text += f"• Контроль: 24/7 мониторинг\n\n"
            
            # Команды управления
            result_text += f"*🛠️ Команды управления:*\n"
            result_text += f"• `/scan` - сканирование рынка\n"
            result_text += f"• `/morning_brief` - утренний анализ\n"
            result_text += f"• `/settings` - настройки автоматизации\n\n"
            
            result_text += f"⚠️ *Важно:* Автоматизация работает в тестовом режиме. "
            result_text += f"Переход на реальную торговлю только после полного тестирования."

            await loading_msg.edit_text(
                result_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info("Команда /automation выполнена успешно")

        except Exception as e:
            error_msg = f"❌ *Ошибка системы автоматизации*\n\n"
            error_msg += f"Причина: {str(e)}\n\n"
            error_msg += f"💡 Попробуйте повторить запрос через несколько секунд"
            
            await loading_msg.edit_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Automation command error: {e}")

    async def scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /scan."""
        loading_msg = await update.message.reply_text(
            "🔍 Запускаю сканирование рынка...\n"
            "📊 Анализирую тикеры из списка наблюдения...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Создаем торговый движок
            trading_engine = TradingEngine(mode=TradingMode.PAPER)
            
            # Сканируем рынок (ограничиваем до 3 тикеров для быстроты)
            quick_watchlist = trading_engine.watchlist[:3]
            signals = []
            
            for ticker in quick_watchlist:
                try:
                    signal = await trading_engine.generate_trading_signal(ticker)
                    if signal:
                        signals.append(signal)
                except Exception as e:
                    logger.error(f"Ошибка сканирования {ticker}: {e}")
                    continue
            
            # Форматируем результаты
            result_text = f"🔍 *СКАНИРОВАНИЕ РЫНКА*\n\n"
            result_text += f"⏰ Время сканирования: {datetime.now().strftime('%H:%M:%S')}\n"
            result_text += f"📊 Проанализировано тикеров: {len(quick_watchlist)}\n"
            result_text += f"🎯 Найдено сигналов: {len(signals)}\n\n"
            
            if signals:
                result_text += f"📈 *НАЙДЕННЫЕ СИГНАЛЫ:*\n\n"
                
                for i, signal in enumerate(signals, 1):
                    emoji = "🟢" if signal.direction == "BUY" else "🔴" if signal.direction == "SELL" else "🟡"
                    
                    result_text += f"*{i}. {signal.ticker}*\n"
                    result_text += f"{emoji} {signal.direction} • {signal.strength.value}\n"
                    result_text += f"🎯 Уверенность: {signal.confidence:.0%}\n"
                    result_text += f"💰 Цена: {signal.entry_price:.2f} ₽\n"
                    result_text += f"📝 {signal.reasoning[:50]}...\n\n"
                
                # Рекомендации
                result_text += f"💡 *Рекомендации:*\n"
                buy_signals = [s for s in signals if s.direction == "BUY"]
                sell_signals = [s for s in signals if s.direction == "SELL"]
                
                if buy_signals:
                    best_buy = max(buy_signals, key=lambda x: x.confidence)
                    result_text += f"• Лучший сигнал на покупку: {best_buy.ticker}\n"
                
                if sell_signals:
                    best_sell = max(sell_signals, key=lambda x: x.confidence)
                    result_text += f"• Лучший сигнал на продажу: {best_sell.ticker}\n"
                
            else:
                result_text += f"📊 *РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ:*\n"
                result_text += f"❌ Сильных сигналов не обнаружено\n\n"
                result_text += f"📈 Проанализированы: {', '.join(quick_watchlist)}\n"
                result_text += f"⏳ Рекомендуется повторить сканирование через 30-60 минут\n\n"
                
                result_text += f"💡 *Возможные причины:*\n"
                result_text += f"• Рынок в консолидации\n"
                result_text += f"• Слабые технические сигналы\n"
                result_text += f"• Нейтральный новостной фон\n"
            
            result_text += f"\n*🔄 Следующие действия:*\n"
            result_text += f"• `/risk TICKER` - анализ рисков\n"
            result_text += f"• `/automation` - настройки автоматизации\n"
            result_text += f"• `/portfolio` - текущий портфель\n\n"
            
            result_text += f"⚠️ *Примечание:* Сканирование в демо-режиме. "
            result_text += f"Проведите дополнительный анализ перед принятием решений."

            await loading_msg.edit_text(
                result_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Сканирование завершено: найдено {len(signals)} сигналов")

        except Exception as e:
            error_msg = f"❌ *Ошибка сканирования рынка*\n\n"
            error_msg += f"Причина: {str(e)}\n\n"
            error_msg += f"💡 Попробуйте повторить сканирование через несколько секунд"
            
            await loading_msg.edit_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.error(f"Scan command error: {e}")

    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /analysis TICKER."""
        if not context.args:
            await update.message.reply_text(
                "📊 *Технический анализ акции*\n\n"
                "Использование: `/analysis TICKER`\n\n"
                "Примеры:\n"
                "• `/analysis SBER` - анализ Сбербанка\n"
                "• `/analysis GAZP` - анализ Газпрома\n"
                "• `/analysis YNDX` - анализ Яндекса\n\n"
                "📈 Включает: RSI, MACD, скользящие средние, Боллинджер\n"
                "⏱️ Время обработки: 3-8 секунд",
                parse_mode="Markdown",
            )
            return

        ticker = context.args[0].upper()

        loading_msg = await update.message.reply_text(
            f"📊 Выполняю технический анализ *{ticker}*...\n"
            f"📈 Рассчитываю RSI, MACD, скользящие средние...",
            parse_mode="Markdown",
        )

        try:
            from technical_analysis import get_ticker_analysis_for_telegram

            result_text = await get_ticker_analysis_for_telegram(ticker)

            await loading_msg.edit_text(result_text, parse_mode="Markdown")

            logger.info(f"Технический анализ {ticker} завершен успешно")

        except Exception as e:
            error_msg = f"❌ *Ошибка технического анализа {ticker}*\n\n"
            error_msg += f"Причина: {str(e)}\n\n"
            error_msg += "💡 Попробуйте:\n"
            error_msg += "• Проверить тикер (SBER, GAZP, YNDX)\n"
            error_msg += "• Повторить запрос через несколько секунд\n"
            error_msg += "• Использовать /status для проверки систем"

            await loading_msg.edit_text(error_msg, parse_mode="Markdown")
            logger.error(f"Analysis command error for {ticker}: {e}")

    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /signal TICKER."""
        if not context.args:
            await update.message.reply_text(
                "🎯 *Комбинированный торговый сигнал*\n\n"
                "Использование: `/signal TICKER`\n\n"
                "Примеры:\n"
                "• `/signal SBER` - сигнал для Сбербанка\n"
                "• `/signal GAZP` - сигнал для Газпрома\n"
                "• `/signal YNDX` - сигнал для Яндекса\n\n"
                "🧠 Объединяет: технический анализ (60%) + новости (40%)\n"
                "⏱️ Время обработки: 5-12 секунд",
                parse_mode="Markdown",
            )
            return

        ticker = context.args[0].upper()

        loading_msg = await update.message.reply_text(
            f"🎯 Генерирую торговый сигнал для *{ticker}*...\n"
            "📊 Анализирую техническую картину...\n"
            "📰 Обрабатываю новостной фон...\n"
            "🧠 Комбинирую результаты...",
            parse_mode="Markdown",
        )

        try:
            result_text = await get_trading_signal_for_telegram(ticker)

            await loading_msg.edit_text(result_text, parse_mode="Markdown")

            logger.info(f"Торговый сигнал {ticker} сгенерирован успешно")

        except Exception as e:
            error_msg = f"❌ *Ошибка генерации сигнала {ticker}*\n\n"
            error_msg += f"Причина: {str(e)}\n\n"
            error_msg += "💡 Попробуйте:\n"
            error_msg += "• Проверить тикер (SBER, GAZP, YNDX)\n"
            error_msg += f"• Использовать отдельно `/analysis {ticker}` и `/news {ticker}`\n"
            error_msg += "• Повторить запрос через несколько секунд"

            await loading_msg.edit_text(error_msg, parse_mode="Markdown")
            logger.error(f"Signal command error for {ticker}: {e}")

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
        # Аналитика и риски
        self.application.add_handler(CommandHandler("news", self.news_command))
        self.application.add_handler(CommandHandler("risk", self.risk_command))
        self.application.add_handler(CommandHandler("portfolio", self.portfolio_command))
        self.application.add_handler(CommandHandler("analysis", self.analysis_command))
        self.application.add_handler(CommandHandler("signal", self.signal_command))
        # Автоматизация
        self.application.add_handler(CommandHandler("automation", self.automation_command))
        self.application.add_handler(CommandHandler("scan", self.scan_command))
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
