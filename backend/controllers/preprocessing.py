from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import numpy as np
import json
import logging
import uuid
from pathlib import Path

# Импорты из собственных модулей
from services.preprocessing_service import get_preprocessing_methods, apply_preprocessing
from utils.file_utils import get_file_path_by_id, get_processed_file_path
from utils.json_utils import convert_numpy_types
from utils.validation_utils import load_and_validate_dataframe
from utils.error_utils import handle_exceptions, log_error
from utils.lock_utils import with_file_lock, is_file_processing
from models.schemas import PreprocessingConfig
from controllers.datasets import NumpyEncoder

router = APIRouter()

@router.get("/methods")
@handle_exceptions
async def get_methods():
    """
    Получение списка доступных методов предобработки.
    """
    methods = get_preprocessing_methods()
    # Применяем convert_numpy_types к методам перед возвратом
    return convert_numpy_types(methods)

@router.post("/preview")
@handle_exceptions
async def preview_preprocessing(config: PreprocessingConfig):
    """
    Предпросмотр результатов предобработки на небольшом примере данных.
    """
    dataset_id = config.dataset_id
    
    # Проверяем, обрабатывается ли файл в данный момент
    if is_file_processing(dataset_id):
        return {"status": "processing", "message": "Файл в данный момент обрабатывается"}
    
    async def process_preview():
        file_path = None
        
        # Ищем файл данных
        for ext in ["csv", "xlsx", "xls"]:
            temp_path = get_file_path_by_id(dataset_id, ext)
            if temp_path.exists():
                file_path = temp_path
                extension = ext
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Набор данных не найден")
        
        # Загружаем и валидируем данные
        df = await load_and_validate_dataframe(file_path, extension)
        
        # Берем небольшой пример для предпросмотра
        sample_size = min(100, len(df))
        sample_df = df.head(sample_size)
        
        # Применяем предобработку
        processed_df = apply_preprocessing(sample_df, config.dict())
        
        # Возвращаем результаты и применяем convert_numpy_types
        result = {
            "original_sample": sample_df.to_dict(orient="records"),
            "processed_sample": processed_df.to_dict(orient="records"),
            "original_columns": sample_df.columns.tolist(),
            "processed_columns": processed_df.columns.tolist()
        }
        
        return convert_numpy_types(result)
    
    return await with_file_lock(dataset_id, process_preview)

@router.post("/execute")
@handle_exceptions
async def execute_preprocessing(
    config: PreprocessingConfig, 
    background_tasks: BackgroundTasks
):
    """
    Выполнение полной предобработки набора данных.
    """
    dataset_id = config.dataset_id
    
    # Проверяем, обрабатывается ли файл в данный момент
    if is_file_processing(dataset_id):
        return {"status": "processing", "message": "Файл в данный момент обрабатывается"}
    
    async def prepare_processing():
        file_path = None
        
        # Ищем файл данных
        for ext in ["csv", "xlsx", "xls"]:
            temp_path = get_file_path_by_id(dataset_id, ext)
            if temp_path.exists():
                file_path = temp_path
                extension = ext
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Набор данных не найден")
        
        # Создаем уникальный ID для результатов
        result_id = str(uuid.uuid4())
        
        # Подготавливаем фоновую задачу
        async def process_data():
            try:
                # Загружаем и валидируем данные
                df = await load_and_validate_dataframe(file_path, extension)
                
                # Применяем предобработку
                processed_df = apply_preprocessing(df, config.dict())
                
                # Сохраняем результаты
                result_path = get_processed_file_path(result_id)
                processed_df.to_csv(result_path, index=False)
                
                # Сохраняем метаданные
                metadata = {
                    "dataset_id": dataset_id,
                    "result_id": result_id,
                    "row_count": len(processed_df),
                    "column_count": len(processed_df.columns),
                    "columns": processed_df.columns.tolist(),
                    "config": config.dict()
                }
                
                metadata_path = result_path.parent / f"{result_id}_metadata.json"
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, cls=NumpyEncoder)
            
            except Exception as e:
                log_error(e, f"Ошибка при обработке данных для result_id={result_id}")
                # Сохраняем информацию об ошибке
                error_path = get_processed_file_path(result_id).parent / f"{result_id}_error.txt"
                with open(error_path, "w") as f:
                    f.write(str(e))
        
        # Запускаем обработку в фоновом режиме
        background_tasks.add_task(process_data)
        
        # Применяем convert_numpy_types к результату перед возвратом
        result = {"result_id": result_id, "status": "processing"}
        return convert_numpy_types(result)
    
    return await with_file_lock(dataset_id, prepare_processing)

@router.get("/status/{result_id}")
@handle_exceptions
async def get_preprocessing_status(result_id: str):
    """
    Получение статуса выполнения предобработки.
    """
    # Проверяем, обрабатывается ли файл в данный момент
    if is_file_processing(result_id):
        # Проверяем наличие метаданных о прогрессе
        progress_path = get_processed_file_path(result_id).parent / f"{result_id}_progress.json"
        if progress_path.exists():
            try:
                with open(progress_path, "r") as f:
                    progress_data = json.load(f)
                return convert_numpy_types({"status": "processing", "progress": progress_data})
            except:
                pass
        return {"status": "processing"}
    
    async def check_status():
        result_path = get_processed_file_path(result_id)
        error_path = result_path.parent / f"{result_id}_error.txt"
        
        if error_path.exists():
            with open(error_path, "r") as f:
                error_message = f.read()
            return convert_numpy_types({"status": "error", "message": error_message})
        
        if result_path.exists():
            metadata_path = result_path.parent / f"{result_id}_metadata.json"
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            return convert_numpy_types({"status": "completed", "metadata": metadata})
        
        return {"status": "processing"}
    
    return await with_file_lock(result_id, check_status)

@router.get("/data/{result_id}")
@handle_exceptions
async def get_data_preview(result_id: str, limit: int = 100):
    """
    Получение предпросмотра обработанных данных.
    """
    # Проверяем, обрабатывается ли файл в данный момент
    if is_file_processing(result_id):
        return {"status": "processing", "message": "Данные в данный момент обрабатываются"}
    
    async def load_preview():
        result_path = get_processed_file_path(result_id)
        
        if not result_path.exists():
            raise HTTPException(status_code=404, detail="Результаты не найдены")
        
        # Загружаем данные для предпросмотра
        df = pd.read_csv(result_path, nrows=limit)
        
        # Применяем convert_numpy_types к результату перед возвратом
        result = {"preview": df.to_dict(orient="records")}
        return convert_numpy_types(result)
    
    return await with_file_lock(result_id, load_preview)