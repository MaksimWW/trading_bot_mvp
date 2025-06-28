
# 🔧 Environment Setup Guide
### Руководство по настройке окружения Trading Bot MVP

## 📋 Обзор

Данное руководство поможет настроить рабочее окружение для Trading Bot MVP в Replit, включая решение основных проблем с зависимостями и автоматизацию запуска.

## ⚠️ Решение проблемы libstdc++.so.6

### Проблема
```
ImportError: libstdc++.so.6: cannot open shared object file: No such file or directory
```

### Постоянное решение

#### 1. Обновление системных библиотек
```bash
# Добавить в replit.nix или выполнить в терминале
nix-env -iA nixpkgs.gcc-unwrapped
nix-env -iA nixpkgs.glibc
```

#### 2. Настройка переменных окружения
```bash
# Добавить в ~/.profile
export LD_LIBRARY_PATH="/nix/store/$(ls /nix/store | grep glibc | head -1)/lib:$LD_LIBRARY_PATH"
export LD_LIBRARY_PATH="/nix/store/$(ls /nix/store | grep gcc | head -1)/lib:$LD_LIBRARY_PATH"
```

#### 3. Альтернативный метод через apt
```bash
# Если предыдущий способ не работает
apt update && apt install -y libstdc++6
```

## 🔄 Автоматическая настройка окружения

### Создание файла ~/.trading_bot_env
```bash
cat > ~/.trading_bot_env << 'EOF'
#!/bin/bash
# Trading Bot Environment Setup

# Системные библиотеки
export LD_LIBRARY_PATH="/nix/store/$(ls /nix/store | grep glibc | head -1)/lib:$LD_LIBRARY_PATH"
export LD_LIBRARY_PATH="/nix/store/$(ls /nix/store | grep gcc | head -1)/lib:$LD_LIBRARY_PATH"

# Python путь
export PYTHONPATH="$PYTHONPATH:/home/runner/workspace/src"

# Tinkoff API настройки
export TINKOFF_SANDBOX=true
export TINKOFF_APP_NAME="TradingBotMVP"

# Логирование
export LOG_LEVEL=INFO
export LOG_DIR="/home/runner/workspace/logs"

# Создание директорий
mkdir -p $LOG_DIR
mkdir -p /home/runner/workspace/data

echo "✅ Trading Bot environment loaded"
EOF

chmod +x ~/.trading_bot_env
```

### Автоматическая загрузка через ~/.profile
```bash
# Добавить в ~/.profile для автоматической загрузки
echo "source ~/.trading_bot_env" >> ~/.profile
```

### Применение настроек
```bash
source ~/.profile
```

## 🔍 Проверка работоспособности gRPC

### Тест 1: Базовая проверка импорта
```bash
python3 -c "import grpc; print('✅ gRPC импортирован успешно')"
```

### Тест 2: Проверка Tinkoff клиента
```bash
cd src
python3 -c "
try:
    from tinkoff.invest import Client
    print('✅ Tinkoff Client импортирован успешно')
except Exception as e:
    print(f'❌ Ошибка: {e}')
"
```

### Тест 3: Полная проверка зависимостей
```bash
python3 -c "
import sys
modules = ['grpc', 'tinkoff.invest', 'telegram', 'pandas', 'numpy']
for module in modules:
    try:
        __import__(module)
        print(f'✅ {module}')
    except ImportError as e:
        print(f'❌ {module}: {e}')
"
```

## 🛠️ Устранение проблем

### Если ошибка повторяется

#### Метод 1: Пересборка окружения
```bash
# Очистка кэша pip
pip cache purge

# Переустановка зависимостей
pip uninstall tinkoff-investments grpcio grpcio-tools -y
pip install tinkoff-investments==0.2.0b108 grpcio grpcio-tools
```

#### Метод 2: Обновление nix пакетов
```bash
# В replit.nix добавить:
pkgs.gcc-unwrapped
pkgs.glibc
pkgs.stdenv.cc.cc.lib
```

#### Метод 3: Использование conda (если доступен)
```bash
conda install grpcio grpcio-tools
```

### Проверка системных библиотек
```bash
# Поиск libstdc++.so.6
find /nix/store -name "libstdc++.so.6" 2>/dev/null | head -5

# Проверка LD_LIBRARY_PATH
echo $LD_LIBRARY_PATH

# Проверка доступных библиотек
ldconfig -p | grep libstdc++
```

## 🚀 Команды для запуска компонентов

### Полный запуск бота
```bash
# Загрузка окружения и запуск
source ~/.trading_bot_env && python src/main.py
```

### Тестирование отдельных компонентов

#### Tinkoff Client
```bash
cd src && python3 -c "
from tinkoff_client import TinkoffClient
client = TinkoffClient()
accounts = client.get_accounts()
print(f'Найдено счетов: {len(accounts)}')
"
```

#### Telegram Bot (тест)
```bash
cd src && python3 -c "
from config import TELEGRAM_TOKEN
print('Telegram token:', '✅ Настроен' if TELEGRAM_TOKEN else '❌ Не найден')
"
```

#### Portfolio Manager
```bash
cd src && python3 -c "
from portfolio_manager import get_portfolio_manager
pm = get_portfolio_manager()
summary = pm.get_portfolio_summary()
print('Portfolio Manager:', '✅ Работает' if summary else '❌ Ошибка')
"
```

#### Technical Analysis
```bash
cd src && python3 -c "
from technical_analysis import TechnicalAnalyzer
analyzer = TechnicalAnalyzer()
print('Technical Analyzer: ✅ Инициализирован')
"
```

## 📦 Упрощенные команды запуска

### Создание алиасов для удобства
```bash
cat >> ~/.bashrc << 'EOF'
# Trading Bot Aliases
alias tb-start='source ~/.trading_bot_env && python /home/runner/workspace/src/main.py'
alias tb-test='source ~/.trading_bot_env && python /home/runner/workspace/src/tinkoff_client.py'
alias tb-env='source ~/.trading_bot_env'
alias tb-check='source ~/.trading_bot_env && python3 -c "import grpc; from tinkoff.invest import Client; print(\"✅ Все компоненты работают\")"'
EOF

source ~/.bashrc
```

### Использование алиасов
```bash
tb-env      # Загрузка окружения
tb-check    # Проверка всех компонентов
tb-test     # Тест Tinkoff API
tb-start    # Запуск бота
```

## 🔧 Дополнительные настройки

### Оптимизация производительности
```bash
# В ~/.trading_bot_env добавить:
export GRPC_VERBOSITY=ERROR
export GRPC_TRACE=""
export PYTHONOPTIMIZE=1
```

### Настройка логирования
```bash
# Создание структуры логов
mkdir -p logs/{trading,telegram,errors}

# Ротация логов
echo "0 0 * * * find /home/runner/workspace/logs -name '*.log' -mtime +7 -delete" | crontab -
```

## ✅ Финальная проверка

### Комплексный тест
```bash
#!/bin/bash
echo "🔍 Финальная проверка Trading Bot MVP..."

source ~/.trading_bot_env

echo "1. Проверка Python путей..."
python3 -c "import sys; print('✅ Python paths OK')"

echo "2. Проверка gRPC..."
python3 -c "import grpc; print('✅ gRPC OK')"

echo "3. Проверка Tinkoff..."
cd src && python3 -c "from tinkoff.invest import Client; print('✅ Tinkoff OK')"

echo "4. Проверка Telegram..."
cd src && python3 -c "from telegram import Bot; print('✅ Telegram OK')"

echo "5. Проверка всех модулей бота..."
cd src && python3 -c "
from main import check_environment
if check_environment():
    print('✅ Все модули загружены успешно')
else:
    print('❌ Проблемы с конфигурацией')
"

echo "🎉 Проверка завершена!"
```

### Сохранение скрипта проверки
```bash
cat > ~/check_trading_bot.sh << 'EOF'
#!/bin/bash
source ~/.trading_bot_env
cd /home/runner/workspace
echo "🔍 Проверка Trading Bot MVP..."
python3 -c "
try:
    import grpc
    from tinkoff.invest import Client
    from telegram import Bot
    print('✅ Все основные зависимости работают')
    print('🚀 Готов к запуску: python src/main.py')
except Exception as e:
    print(f'❌ Ошибка: {e}')
    print('💡 Выполните: source ~/.trading_bot_env')
"
EOF

chmod +x ~/check_trading_bot.sh
```

## 📞 Поддержка

При возникновении проблем:

1. **Выполните:** `~/check_trading_bot.sh`
2. **Проверьте логи:** `tail -f logs/trading_bot.log`
3. **Перезагрузите окружение:** `source ~/.trading_bot_env`
4. **Очистите кэш:** `pip cache purge && pip install -r requirements.txt`

---

*Последнее обновление: 2024*  
*Автор: Trading Bot MVP Team*
