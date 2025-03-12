from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание приложения FastAPI
app = FastAPI(title="Конструктор предобработки данных API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшне следует указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Создание директорий для данных
@app.on_event("startup")
async def startup_event():
    # Директории для хранения данных
    UPLOAD_DIR = Path("./data/uploads")
    PROCESSED_DIR = Path("./data/processed")
    TEMP_DIR = Path("./data/temp")
    
    # Создаем директории, если они не существуют
    for directory in [UPLOAD_DIR, PROCESSED_DIR, TEMP_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    logger.info("Приложение запущено, директории созданы")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)