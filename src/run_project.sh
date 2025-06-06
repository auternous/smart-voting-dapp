#!/bin/bash

set -e

echo "--------------------------------------------"
echo "1. Настройка бэкенда (Hardhat)"
echo "--------------------------------------------"

echo "🔧 Настройка бэкенда (Hardhat)..."

# Установка Node.js 20 через NVM
if ! command -v node &> /dev/null || [[ $(node -v) != v20* ]]; then
    echo "Установка Node.js 20..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    nvm install 20
    nvm use 20
fi

# Установка Hardhat и зависимостей
if [ ! -d "node_modules" ]; then
    echo "Установка зависимостей Hardhat..."
    npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
fi

# Запуск локальной ноды Hardhat в фоне
echo "🚀 Запуск Hardhat ноды..."
npx hardhat node &
HARDHAT_PID=$!
sleep 5  # Даем время ноде запуститься

# Деплой контрактов
echo "📦 Деплой контрактов..."
npx hardhat run scripts/deploy.js --network localhost

echo "--------------------------------------------"
echo "2. Настройка Python бэкенда (FastAPI)"
echo "--------------------------------------------"

cd backend || { echo "❌ Папка backend не найдена"; exit 1; }

# Проверка наличия Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не установлен!"
    exit 1
fi

# Создание виртуального окружения, если не существует
if [ ! -d ".venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv .venv
fi

# Активация виртуального окружения
source .venv/bin/activate

# Установка / обновление pip
echo "⚙️ Обновление pip..."
python -m pip install --upgrade pip > /dev/null

# Установка зависимостей (или из requirements.txt при наличии)
if [ -f "requirements.txt" ]; then
    echo "⬇️ Установка зависимостей из requirements.txt..."
    pip install -r requirements.txt > /dev/null
else
    echo "⬇️ Установка Uvicorn и FastAPI..."
    pip install uvicorn fastapi > /dev/null
fi
# Запуск Python-бэкенда
if [ -f "main.py" ]; then
    echo "🌐 Запуск Python бэкенда (Uvicorn)..."
    uvicorn main:app --host 0.0.0.0 --port 8000 &
    UVICORN_PID=$!
else
    echo "⚠️ Файл main.py не найден! Пропускаем запуск Python бэкенда."
    UVICORN_PID=""
fi

cd ..

echo "--------------------------------------------"
echo "3. Настройка и запуск фронтенда"
echo "--------------------------------------------"

if [ -d "frontend" ]; then
    cd frontend || exit

    # Установка зависимостей
    if [ ! -d "node_modules" ]; then
        npm install
    fi

    # Запуск фронтенда
    echo "⚡ Запуск фронтенда..."
    npm run dev &
    FRONTEND_PID=$!
    cd ..
else
    echo "⚠️ Папка frontend не найдена, пропуск..."
    FRONTEND_PID=""
fi

echo "--------------------------------------------"
echo "✅ Все компоненты запущены!"
echo "--------------------------------------------"
echo "Hardhat нода:    http://localhost:8545"
echo "Python бэкенд:   http://localhost:8000"
echo "Фронтенд:        http://localhost:5173"
echo "--------------------------------------------"
echo "Для остановки: нажмите Ctrl+C"

# Завершение по Ctrl+C
trap "echo '⏹ Остановка процессов...'; kill $HARDHAT_PID $UVICORN_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT

# Ожидание завершения
wait