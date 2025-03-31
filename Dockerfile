FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install git+https://github.com/xtekky/gpt4free.git

# Копирование исходного кода
COPY . .

# Создание volume для результатов
VOLUME /app/results

# Открываем порт для веб-интерфейса
EXPOSE 8000

# Меняем команду запуска на uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 