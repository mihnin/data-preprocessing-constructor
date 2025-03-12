from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import numpy as np
import os
import uuid
import shutil
import json
import logging
from pathlib import Path
from services.dataset_service import analyze_dataset
from utils.file_utils import save_uploaded_file, get_file_path_by_id  # Абсолютный импорт вместо относительного

router = APIRouter()

@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Загрузка набора данных в формате CSV или Excel.
    """
    # Проверка расширения файла
    filename = file.filename
    extension = filename.split(".")[-1].lower()
    
    if extension not in ["csv", "xlsx", "xls"]:
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы CSV и Excel")
    
    # Создаем уникальный ID для набора данных
    dataset_id = str(uuid.uuid4())
    
    try:
        # Сохраняем файл
        file_path = await save_uploaded_file(file, dataset_id, extension)
        
        # Загружаем данные в pandas
        if extension == "csv":
            df = pd.read_csv(file_path)
        else:  # Excel
            df = pd.read_excel(file_path)
        
        # Проверяем размер данных
        if len(df) > 1000000:
            raise HTTPException(status_code=400, detail="Превышен лимит в 1 миллион строк")
        
        # Анализируем набор данных
        analysis = analyze_dataset(df)
        analysis["dataset_id"] = dataset_id
        
        # Сохраняем метаданные
        metadata_path = file_path.parent / f"{dataset_id}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(analysis, f)
        
        return analysis
    
    except Exception as e:
        logging.error(f"Ошибка при загрузке файла: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")

@router.get("/{dataset_id}")
async def get_dataset_info(dataset_id: str):
    """
    Получение информации о загруженном наборе данных.
    """
    try:
        # Ищем метаданные
        for extension in ["csv", "xlsx", "xls"]:
            file_path = get_file_path_by_id(dataset_id, extension)
            metadata_path = file_path.parent / f"{dataset_id}_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                return metadata
        
        raise HTTPException(status_code=404, detail="Набор данных не найден")
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Ошибка получения информации о наборе данных: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

@router.get("/export/{result_id}")
async def export_dataset(result_id: str):
    """
    Экспорт обработанных данных.
    """
    from ..utils.file_utils import get_processed_file_path
    
    try:
        # Получаем путь к файлу результатов
        result_path = get_processed_file_path(result_id)
        
        if not result_path.exists():
            raise HTTPException(status_code=404, detail="Результаты не найдены")
        
        return FileResponse(result_path, filename=f"processed_data_{result_id}.csv")
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Ошибка экспорта данных: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")