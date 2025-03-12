from fastapi import UploadFile, HTTPException
import os
import shutil
import logging
from pathlib import Path
from typing import Union

# Директории для хранения файлов
UPLOAD_DIR = Path("./data/uploads")
PROCESSED_DIR = Path("./data/processed")
TEMP_DIR = Path("./data/temp")

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
        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return file_path
    
    except Exception as e:
        logging.error(f"Ошибка сохранения файла: {str(e)}")
        if file_path.exists():
            file_path.unlink()
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