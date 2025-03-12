# Этап 1: Сборка фронтенда Vue.js
FROM node:16-alpine as frontend-build

WORKDIR /app/frontend

# Копируем package.json и package-lock.json
COPY frontend/package*.json ./

# Устанавливаем зависимости
RUN npm install

# Копируем исходный код фронтенда
COPY frontend/ .

# Собираем приложение для продакшна с отключенным ESLint
ENV DISABLE_ESLINT_PLUGIN=true
RUN npm run build

# Этап 2: Настройка Python для бэкенда
FROM python:3.11-slim

WORKDIR /app

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости Python
COPY backend/requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем собранный фронтенд из первого этапа
COPY --from=frontend-build /app/frontend/dist /app/static

# Копируем файлы бэкенда
COPY backend/ /app/

# Создаем директории для данных
RUN mkdir -p /app/data/uploads \
    /app/data/processed \
    /app/data/temp \
    && chmod -R 777 /app/data

# Копируем конфигурацию Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Открываем порт для Nginx
EXPOSE 80

# Создаем стартовый скрипт
RUN echo '#!/bin/bash\n\
nginx\n\
cd /app\n\
uvicorn main:app --host 0.0.0.0 --port 8000\n\
' > /app/start.sh && chmod +x /app/start.sh

# Запуск приложения
CMD ["/app/start.sh"]