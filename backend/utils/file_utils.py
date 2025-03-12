from fastapi import UploadFile, HTTPException
import os
import shutil
import logging
from pathlib import Path
from typing import Union

# Получаем абсолютный путь к текущему файлу
CURRENT_DIR = Path(__file__).resolve().parent

# Определяем абсолютные пути к директориям
BASE_DIR = CURRENT_DIR.parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
TEMP_DIR = BASE_DIR / "data" / "temp"

# Создаем директории, если они не существуют
for directory in [UPLOAD_DIR, PROCESSED_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

async def save_uploaded_file(file: UploadFile, file_id: str, extension: str) -> Path:
    """
    Сохраняет загруженный файл в директории uploads.
    
    Args:
        file: Загруженный файл
        file_id: Уникальный идентификатор файла
        extension: Расширение файла
    
    Returns:
        Path: Путь к сохраненному файлу
    """
    file_path = UPLOAD_DIR / f"{file_id}.{extension}"
    
    try:
        # Сохраняем файл во временной директории сначала
        temp_path = TEMP_DIR / f"{file_id}_temp.{extension}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Перемещаем файл в директорию загрузок
        shutil.move(temp_path, file_path)
        
        return file_path
    
    except Exception as e:
        logging.error(f"Ошибка сохранения файла: {str(e)}", exc_info=True)
        if file_path.exists():
            file_path.unlink()
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения файла: {str(e)}")

def get_file_path_by_id(file_id: str, extension: str) -> Path:
    """
    Получает путь к файлу по его идентификатору.
    
    Args:
        file_id: Идентификатор файла
        extension: Расширение файла
    
    Returns:
        Path: Путь к файлу
    """
    return UPLOAD_DIR / f"{file_id}.{extension}"

def get_processed_file_path(result_id: str) -> Path:
    """
    Получает путь к обработанному файлу по идентификатору результата.
    
    Args:
        result_id: Идентификатор результата
    
    Returns:
        Path: Путь к обработанному файлу
    """
    return PROCESSED_DIR / f"{result_id}.csv"