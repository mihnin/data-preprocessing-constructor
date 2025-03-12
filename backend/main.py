import sys
import os
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import time
import json
import numpy as np
from fastapi.encoders import jsonable_encoder

# Add the parent directory to sys.path to enable absolute imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Настройка логирования
LOG_DIR = Path("./logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Настройка ротации логов (10 файлов по 10 МБ)
file_handler = RotatingFileHandler(
    LOG_DIR / "app.log", 
    maxBytes=10*1024*1024, 
    backupCount=10
)
file_handler.setFormatter(log_format)

# Настройка вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)

# Настройка корневого логгера
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

# Определение пользовательского кодировщика JSON для обработки специальных значений NumPy
class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            if np.isnan(obj) or np.isinf(obj):  # Исправлено 'или' на 'or'
                return None
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# Создание приложения FastAPI
app = FastAPI(
    title="Конструктор предобработки данных API",
    description="API для анализа и предобработки наборов данных",
    version="1.0.0",
    json_encoder=NumpyJSONEncoder  # Добавляем собственный кодировщик
)

# Middleware для измерения времени выполнения запросов
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшне следует указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Обработчики ошибок
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP ошибка: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Ошибка валидации: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=422,
        content={"detail": "Ошибка валидации данных"},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Необработанное исключение: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Произошла внутренняя ошибка сервера"},
    )

# Импорт маршрутов
from controllers.datasets import router as datasets_router
from controllers.preprocessing import router as preprocessing_router

# Добавление маршрутов к приложению
app.include_router(datasets_router, prefix="/api/datasets", tags=["datasets"])
app.include_router(preprocessing_router, prefix="/api/preprocessing", tags=["preprocessing"])

@app.get("/")
async def read_root():
    return {"message": "Добро пожаловать в API Конструктора предобработки данных"}

@app.get("/health")
async def health_check():
    """
    Эндпоинт для проверки работоспособности сервиса.
    Используется для мониторинга и проверок доступности.
    """
    return {"status": "healthy", "timestamp": time.time()}

# Создание директорий для данных
@app.on_event("startup")
async def startup_event():
    # Директории для хранения данных
    from config.settings import UPLOAD_DIR, PROCESSED_DIR, TEMP_DIR
    
    # Создаем директории, если они не существуют
    for directory in [UPLOAD_DIR, PROCESSED_DIR, TEMP_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    logger.info("Приложение запущено, директории созданы")

# Очистка временных данных при завершении
@app.on_event("shutdown")
async def shutdown_event():
    try:
        # Очистка временных файлов
        TEMP_DIR = Path("./data/temp")
        if TEMP_DIR.exists():
            for file in TEMP_DIR.iterdir():
                try:
                    file.unlink()
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл {file}: {str(e)}")
        
        logger.info("Приложение завершено, временные файлы очищены")
    except Exception as e:
        logger.error(f"Ошибка при завершении приложения: {str(e)}", exc_info=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)