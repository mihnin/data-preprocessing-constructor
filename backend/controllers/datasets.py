from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
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

# Импорты из собственных модулей
from services.dataset_service import analyze_dataset
from utils.file_utils import save_uploaded_file, get_file_path_by_id, get_processed_file_path
from utils.json_utils import convert_numpy_types
from utils.validation_utils import load_and_validate_dataframe
from utils.error_utils import handle_exceptions, log_error
from utils.lock_utils import with_file_lock, is_file_processing

router = APIRouter()

# Добавляем класс для сериализации NumPy типов
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

@router.post("/upload")
@handle_exceptions
async def upload_dataset(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Загрузка набора данных в формате CSV или Excel.
    
    Поддерживаемые форматы: CSV, XLSX, XLS.
    Максимальный размер файла: 10 МБ.
    Максимальное количество строк: 1 000 000.
    """
    # Проверка расширения файла
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Имя файла отсутствует")
    
    extension = filename.split(".")[-1].lower()
    
    if extension not in ["csv", "xlsx", "xls"]:
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы CSV и Excel")
    
    # Создаем уникальный ID для набора данных
    dataset_id = str(uuid.uuid4())
    
    # Определяем функцию для выполнения в блокирующем контексте
    async def process_upload():
        try:
            # Сохраняем файл
            file_path = await save_uploaded_file(file, dataset_id, extension)
            
            # Загружаем и валидируем данные
            df = await load_and_validate_dataframe(file_path, extension)
            
            # Анализируем набор данных
            analysis = analyze_dataset(df)
            analysis["dataset_id"] = dataset_id
            
            # Сохраняем метаданные
            metadata_path = file_path.parent / f"{dataset_id}_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(analysis, f, cls=NumpyEncoder)
            
            # Применяем функцию convert_numpy_types к результату перед возвратом
            return convert_numpy_types(analysis)
        
        except Exception as e:
            log_error(e, "Ошибка при обработке загруженного файла")
            raise
    
    # Выполняем обработку с блокировкой
    return await with_file_lock(dataset_id, process_upload)

@router.get("/{dataset_id}")
@handle_exceptions
async def get_dataset_info(dataset_id: str):
    """
    Получение информации о загруженном наборе данных.
    """
    # Проверяем, обрабатывается ли файл в данный момент
    if is_file_processing(dataset_id):
        return {"status": "processing", "message": "Файл в данный момент обрабатывается"}
    
    async def load_metadata():
        # Ищем метаданные
        for extension in ["csv", "xlsx", "xls"]:
            file_path = get_file_path_by_id(dataset_id, extension)
            metadata_path = file_path.parent / f"{dataset_id}_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                # Применяем convert_numpy_types к метаданным перед возвратом
                return convert_numpy_types(metadata)
        
        raise HTTPException(status_code=404, detail="Набор данных не найден")
    
    return await with_file_lock(dataset_id, load_metadata)

@router.get("/export/{result_id}")
@handle_exceptions
async def export_dataset(result_id: str):
    """
    Экспорт обработанных данных.
    """
    async def process_export():
        try:
            # Получаем путь к файлу результатов
            result_path = get_processed_file_path(result_id)
            
            if not result_path.exists():
                raise HTTPException(status_code=404, detail="Результаты не найдены")
            
            return FileResponse(
                result_path, 
                filename=f"processed_data_{result_id}.csv",
                media_type="text/csv"
            )
        
        except HTTPException:
            raise
        except Exception as e:
            log_error(e, "Ошибка экспорта данных")
            raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    
    return await with_file_lock(result_id, process_export)