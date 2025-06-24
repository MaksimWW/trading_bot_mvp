# 🤖 Trading Bot MVP

[![CI/CD Pipeline](https://github.com/MaksimWW/trading_bot_mvp/actions/workflows/ci.yml/badge.svg)](https://github.com/MaksimWW/trading_bot_mvp/actions)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Private-red.svg)](LICENSE)

Автоматизированный торговый бот для российского фондового рынка с интеграцией через Telegram.

## 🚀 Возможности

- 📈 **Технический анализ**: RSI, MACD, Moving Average
- 📰 **Анализ новостей**: ИИ-анализ настроений с помощью OpenAI API  
- 🤖 **Telegram интерфейс**: Удобное управление через бота
- 🛡️ **Risk Management**: Встроенная система управления рисками
- 📊 **Tinkoff Integration**: Работа через Tinkoff Invest API
- ⚡ **Автоматизация**: Полный цикл от анализа до исполнения сделок

## 🏗️ Архитектура

```
trading_bot_mvp/
├── 📁 src/                    # Основной код
│   ├── main.py               # Точка входа
│   ├── config.py             # Конфигурация
│   ├── tinkoff_client.py     # API Tinkoff
│   ├── news_analyzer.py      # Анализ новостей
│   ├── technical_analysis.py # Технические индикаторы
│   ├── risk_manager.py       # Управление рисками
│   ├── telegram_bot.py       # Telegram интерфейс
│   └── database.py          # База данных
├── 📁 tests/                 # Тесты
├── 📁 docs/                  # Документация
├── 📁 data/                  # Данные для анализа
└── 📁 logs/                  # Логи работы
```

## ⚡ Быстрый старт

### 1. Клонирование проекта

```bash
git clone https://github.com/MaksimWW/trading_bot_mvp.git
cd trading_bot_mvp
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

```bash
# Скопируйте шаблон
cp .env.example .env

# Отредактируйте .env файл и добавьте ваши API ключи:
# TELEGRAM_TOKEN=your_telegram_bot_token
# TINKOFF_TOKEN=your_tinkoff_api_token  
# OPENAI_API_KEY=your_openai_api_key
```

### 4. Запуск бота

```bash
python src/main.py
```

## 🔑 Получение API ключей

### Telegram Bot Token
1. Перейдите к [@BotFather](https://t.me/BotFather) в Telegram
2. Создайте нового бота командой `/newbot`
3. Скопируйте полученный токен

### Tinkoff Invest API
1. Зарегистрируйтесь в [Tinkoff Invest](https://www.tinkoff.ru/invest/)
2. Перейдите в настройки API
3. Создайте токен для **песочницы** (для тестирования)

### OpenAI API Key
1. Зарегистрируйтесь на [OpenAI Platform](https://platform.openai.com/)
2. Создайте API ключ в разделе API Keys
3. Пополните баланс для использования

## 🤖 Команды бота

### Информационные команды
- `/start` - Приветствие и инструкции
- `/help` - Список всех команд
- `/status` - Состояние системы

### Аналитические команды  
- `/price SBER` - Текущая цена акции
- `/news SBER` - Анализ новостей по компании
- `/analysis SBER` - Технический анализ
- `/signal SBER` - Торговый сигнал

### Торговые команды
- `/morning_brief` - Утренний анализ рынка
- `/positions` - Текущие позиции
- `/daily_report` - Отчет за день
- `/settings` - Настройки риск-менеджмента

## ⚙️ Настройки Risk Management

```python
# Базовые лимиты
MAX_POSITION_SIZE = 0.05      # 5% от депозита на позицию
MAX_DAILY_LOSS = 0.03         # 3% максимальный дневной убыток  
MAX_DAILY_TRADES = 5          # Максимум 5 сделок в день
DEFAULT_STOP_LOSS = 0.07      # 7% стоп-лосс
DEFAULT_TAKE_PROFIT = 0.10    # 10% тейк-профит

# Торговые часы (МСК)
MARKET_OPEN = "10:00"
MARKET_CLOSE = "19:00"
FORCE_CLOSE_TIME = "18:50"    # Принудительное закрытие
```

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest tests/

# Тесты с покрытием
pytest tests/ --cov=src/ --cov-report=html

# Линтинг кода
flake8 src/
black src/
isort src/
```

## 🔄 CI/CD Pipeline

Проект использует GitHub Actions для автоматизации:

- ✅ **Linting**: flake8, black, isort
- ✅ **Testing**: pytest с покрытием кода
- ✅ **Security**: проверка на утечку секретов
- ✅ **Dependencies**: автоматическая проверка зависимостей

## 📊 Торговая логика

### Алгоритм принятия решений
1. **Утренний анализ** (09:00-10:00):
   - Сбор новостей за 24 часа
   - Расчет технических индикаторов
   - Генерация торговых сигналов

2. **Дневной мониторинг** (10:00-18:50):
   - Отслеживание позиций
   - Мониторинг стоп-лоссов
   - Реагирование на новости

3. **Вечернее закрытие** (18:50-19:00):
   - Закрытие дневных позиций
   - Генерация отчета P&L

### Система скоринга
- **Технический анализ**: 60% веса
- **Новостной анализ**: 40% веса
- **Пороги**: Покупка >0.6, Продажа <-0.6

## 🛡️ Безопасность

- ❌ **НЕ храните** API ключи в коде
- ✅ **Используйте** файл `.env` для секретов
- ✅ **Начните с песочницы** Tinkoff
- ✅ **Тестируйте** стратегии на исторических данных
- ✅ **Следите** за лимитами риск-менеджмента

## 📈 Статус разработки

- [x] Архитектура и планирование
- [x] Базовая инфраструктура  
- [x] GitHub интеграция и CI/CD
- [ ] Анализ новостей через OpenAI
- [ ] Технические индикаторы
- [ ] Торговая логика и риск-менеджмент
- [ ] Интеграция с Tinkoff API
- [ ] Telegram интерфейс
- [ ] Тестирование и деплой

## 🤝 Участие в разработке

1. **Fork** репозитория
2. **Создайте** ветку для новой функции (`git checkout -b feature/AmazingFeature`)
3. **Закоммитьте** изменения (`git commit -m 'Add some AmazingFeature'`)
4. **Push** в ветку (`git push origin feature/AmazingFeature`)
5. **Создайте** Pull Request

## 📄 Лицензия

Проект является частным. Все права защищены.

## ⚠️ Дисклеймер

**ВНИМАНИЕ**: Этот бот предназначен только для образовательных целей. Торговля на финансовых рынках сопряжена с высокими рисками. Всегда:

- 🧪 Тестируйте стратегии в песочнице
- 💰 Не вкладывайте средства, которые не можете позволить себе потерять  
- 📚 Изучайте финансовые рынки перед началом торговли
- ⚖️ Соблюдайте законодательство вашей юрисдикции

---

## 📞 Поддержка

Для вопросов и предложений:
- 🐛 [Создайте Issue](https://github.com/MaksimWW/trading_bot_mvp/issues)
- 💬 [Обсуждения](https://github.com/MaksimWW/trading_bot_mvp/discussions)

**Удачной торговли!** 🚀📈