# Этап 1: Сборка фронтенда Vue.js с использованием образа node:16-alpine
FROM node:16-alpine as frontend-build

WORKDIR /app/frontend

# Копируем только package.json и package-lock.json сначала
COPY frontend/package*.json ./

# Устанавливаем зависимости
RUN npm ci --no-audit --no-fund

# Копируем исходный код фронтенда
COPY frontend/ .

# Собираем приложение для продакшна с отключенным ESLint
RUN npm run build

# Этап 2: Настройка Python для бэкенда с использованием slim образа
FROM python:3.11-slim

WORKDIR /app

# Устанавливаем необходимые пакеты и очищаем кэш apt, все в одной команде
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    nginx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements.txt
COPY backend/requirements.txt .

# Устанавливаем зависимости Python с использованием кеша pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем собранный фронтенд из первого этапа
COPY --from=frontend-build /app/frontend/dist /app/static

# Копируем файлы бэкенда
COPY backend/ /app/

# Создаем директории для данных и настраиваем права доступа
RUN mkdir -p /app/data/uploads \
    /app/data/processed \
    /app/data/temp \
    /app/logs \
    && chmod -R 777 /app/data

# Копируем конфигурацию Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Открываем порт для Nginx
EXPOSE 80

# Создаем стартовый скрипт
RUN echo '#!/bin/bash\n\
nginx\n\
cd /app\n\
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4\n\
' > /app/start.sh && chmod +x /app/start.sh

# Настраиваем переменные среды
ENV PYTHONPATH=/app
ENV MAX_WORKERS=4
ENV UPLOAD_FILE_SIZE_LIMIT=10485760

# Проверка здоровья
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost/health || exit 1

# Запуск приложения
CMD ["/app/start.sh"]