from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import numpy as np
import json
import logging
import uuid
from pathlib import Path
from ..services.preprocessing_service import get_preprocessing_methods, apply_preprocessing
from ..utils.file_utils import get_file_path_by_id, get_processed_file_path

router = APIRouter()

class PreprocessingConfig(BaseModel):
    dataset_id: str
    methods: List[Dict[str, Any]]

@router.get("/methods")
async def get_methods():
    """
    Получение списка доступных методов предобработки.
    """
    try:
        methods = get_preprocessing_methods()
        return methods
    except Exception as e:
        logging.error(f"Ошибка получения методов предобработки: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

@router.post("/preview")
async def preview_preprocessing(config: PreprocessingConfig):
    """
    Предпросмотр результатов предобработки на небольшом примере данных.
    """
    try:
        dataset_id = config.dataset_id
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
        
        # Загружаем данные
        if extension == "csv":
            df = pd.read_csv(file_path)
        else:  # Excel
            df = pd.read_excel(file_path)
        
        # Берем небольшой пример для предпросмотра
        sample_size = min(100, len(df))
        sample_df = df.head(sample_size)
        
        # Применяем предобработку
        processed_df = apply_preprocessing(sample_df, config.dict())
        
        # Возвращаем результаты
        return {
            "original_sample": sample_df.to_dict(orient="records"),
            "processed_sample": processed_df.to_dict(orient="records"),
            "original_columns": sample_df.columns.tolist(),
            "processed_columns": processed_df.columns.tolist()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Ошибка при предпросмотре: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка предпросмотра: {str(e)}")

@router.post("/execute")
async def execute_preprocessing(config: PreprocessingConfig, background_tasks: BackgroundTasks):
    """
    Выполнение полной предобработки набора данных.
    """
    try:
        dataset_id = config.dataset_id
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
        
        async def process_data():
            try:
                # Загружаем данные
                if extension == "csv":
                    df = pd.read_csv(file_path)
                else:  # Excel
                    df = pd.read_excel(file_path)
                
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
                    json.dump(metadata, f)
            
            except Exception as e:
                logging.error(f"Ошибка при обработке: {str(e)}")
                # Сохраняем информацию об ошибке
                error_path = get_processed_file_path(result_id).parent / f"{result_id}_error.txt"
                with open(error_path, "w") as f:
                    f.write(str(e))
        
        # Запускаем обработку в фоновом режиме
        background_tasks.add_task(process_data)
        
        return {"result_id": result_id, "status": "processing"}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Ошибка запуска обработки: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка запуска обработки: {str(e)}")

@router.get("/status/{result_id}")
async def get_preprocessing_status(result_id: str):
    """
    Получение статуса выполнения предобработки.
    """
    try:
        result_path = get_processed_file_path(result_id)
        error_path = result_path.parent / f"{result_id}_error.txt"
        
        if error_path.exists():
            with open(error_path, "r") as f:
                error_message = f.read()
            return {"status": "error", "message": error_message}
        
        if result_path.exists():
            metadata_path = result_path.parent / f"{result_id}_metadata.json"
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            return {"status": "completed", "metadata": metadata}
        
        return {"status": "processing"}
    
    except Exception as e:
        logging.error(f"Ошибка получения статуса: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

@router.get("/data/{result_id}")
async def get_data_preview(result_id: str, limit: int = 100):
    """
    Получение предпросмотра обработанных данных.
    """
    try:
        result_path = get_processed_file_path(result_id)
        
        if not result_path.exists():
            raise HTTPException(status_code=404, detail="Результаты не найдены")
        
        # Загружаем данные для предпросмотра
        df = pd.read_csv(result_path, nrows=limit)
        
        return {"preview": df.to_dict(orient="records")}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Ошибка получения предпросмотра данных: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")