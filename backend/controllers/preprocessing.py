from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, File, UploadFile, Form
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import numpy as np
import json
import logging
import uuid
import time
import os
from pathlib import Path
from fastapi.responses import FileResponse

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
                
                # Добавляем параметры масштабирования в метаданные, если они есть
                if hasattr(processed_df, 'scaling_params'):
                    metadata["scaling_params"] = processed_df.scaling_params
                
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
        
        try:
            # Загружаем данные для предпросмотра
            df = pd.read_csv(result_path, nrows=limit)
            
            # Заменяем бесконечные значения и NaN на None перед сериализацией
            df = df.replace([np.inf, -np.inf], np.nan)
            
            # Применяем convert_numpy_types к результату перед возвратом
            result = {"preview": df.to_dict(orient="records")}
            return convert_numpy_types(result)
        except Exception as e:
            log_error(e, f"Ошибка загрузки предпросмотра данных для result_id={result_id}")
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки данных: {str(e)}")
    
    return await with_file_lock(result_id, load_preview)

@router.get("/export-metadata/{result_id}")
@handle_exceptions
async def export_metadata(result_id: str):
    """
    Экспорт метаданных масштабирования в отдельный файл.
    """
    # Проверяем, обрабатывается ли файл в данный момент
    if is_file_processing(result_id):
        return {"status": "processing", "message": "Данные в данный момент обрабатываются"}
        
    async def process_metadata_export():
        try:
            # Получаем путь к метаданным
            metadata_path = get_processed_file_path(result_id).parent / f"{result_id}_metadata.json"
            
            if not metadata_path.exists():
                raise HTTPException(status_code=404, detail="Метаданные не найдены")
            
            # Загружаем метаданные
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # Извлекаем только параметры масштабирования
            scaling_params = metadata.get("scaling_params", {})
            
            if not scaling_params:
                raise HTTPException(
                    status_code=400, 
                    detail="Параметры масштабирования не найдены в метаданных"
                )
            
            # Подготавливаем упрощенный объект метаданных для экспорта
            export_metadata = {
                "result_id": result_id,
                "scaling_params": scaling_params,
                "columns": metadata.get("columns", []),
                "exported_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Сохраняем во временный файл
            temp_dir = get_processed_file_path(result_id).parent
            temp_path = temp_dir / f"scaling_metadata_{result_id}.json"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(export_metadata, f, ensure_ascii=False, indent=2)
            
            return FileResponse(
                temp_path, 
                filename=f"scaling_metadata_{result_id}.json",
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="scaling_metadata_{result_id}.json"'
                }
            )
        
        except HTTPException:
            raise
        except Exception as e:
            log_error(e, "Ошибка экспорта метаданных")
            raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    
    return await with_file_lock(result_id, process_metadata_export)

@router.post("/import-metadata")
@handle_exceptions
async def import_metadata(
    file: UploadFile = File(...),
    result_id: str = Form(...)
):
    """
    Импорт метаданных масштабирования из файла и их применение к результату.
    """
    # Проверяем, обрабатывается ли файл в данный момент
    if is_file_processing(result_id):
        return {"status": "processing", "message": "Данные в данный момент обрабатываются"}
    
    async def process_metadata_import():
        try:
            # Проверяем существование результата
            result_path = get_processed_file_path(result_id)
            
            if not result_path.exists():
                raise HTTPException(status_code=404, detail="Результаты не найдены")
            
            # Используем директорию результата в качестве временной директории
            temp_dir = result_path.parent
            temp_metadata_path = temp_dir / f"temp_metadata_{str(uuid.uuid4())}.json"
            
            # Сохраняем загруженный файл метаданных во временную директорию
            with open(temp_metadata_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Загружаем метаданные из временного файла
            with open(temp_metadata_path, "r", encoding="utf-8") as f:
                imported_metadata = json.load(f)
            
            # Проверяем наличие параметров масштабирования
            if "scaling_params" not in imported_metadata:
                raise HTTPException(
                    status_code=400, 
                    detail="Файл не содержит параметров масштабирования"
                )
            
            # Загружаем существующие метаданные результата
            metadata_path = result_path.parent / f"{result_id}_metadata.json"
            
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    existing_metadata = json.load(f)
            else:
                # Создаем базовые метаданные, если они не существуют
                existing_metadata = {
                    "result_id": result_id,
                    "row_count": 0,
                    "column_count": 0,
                    "columns": []
                }
            
            # Обновляем метаданные с импортированными параметрами масштабирования
            existing_metadata["scaling_params"] = imported_metadata["scaling_params"]
            existing_metadata["imported_metadata"] = True
            existing_metadata["imported_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Сохраняем обновленные метаданные
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(existing_metadata, f, cls=NumpyEncoder, ensure_ascii=False)
            
            # Удаляем временный файл
            os.remove(temp_metadata_path)
            
            return {
                "status": "success",
                "message": "Метаданные успешно импортированы",
                "scaling_params": imported_metadata["scaling_params"]
            }
        
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Некорректный формат JSON файла")
        except HTTPException:
            raise
        except Exception as e:
            log_error(e, "Ошибка импорта метаданных")
            raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    
    return await with_file_lock(result_id, process_metadata_import)

@router.post("/set-scaling-params/{result_id}")
@handle_exceptions
async def set_scaling_params(result_id: str, params: dict):
    """
    Установка параметров масштабирования вручную.
    """
    # Проверяем, обрабатывается ли файл в данный момент
    if is_file_processing(result_id):
        return {"status": "processing", "message": "Данные в данный момент обрабатываются"}
    
    if "method" not in params or "columns" not in params or "parameters" not in params:
        raise HTTPException(
            status_code=400, 
            detail="Необходимо указать метод, столбцы и параметры масштабирования"
        )
    
    async def process_manual_params():
        try:
            # Проверяем существование результата
            result_path = get_processed_file_path(result_id)
            
            if not result_path.exists():
                raise HTTPException(status_code=404, detail="Результаты не найдены")
            
            # Загружаем существующие метаданные результата
            metadata_path = result_path.parent / f"{result_id}_metadata.json"
            
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            else:
                # Создаем базовые метаданные, если они не существуют
                metadata = {
                    "result_id": result_id,
                    "row_count": 0,
                    "column_count": 0,
                    "columns": []
                }
            
            # Проверяем корректность параметров в зависимости от метода
            method = params["method"]
            columns = params["columns"]
            parameters = params["parameters"]
            
            # Формируем параметры масштабирования в правильном формате
            scaling_params = {
                "standardization": {
                    "method": method,
                    "columns": columns,
                    "params": {}
                }
            }
            
            # Проверяем и добавляем параметры для каждого столбца
            for column, column_params in parameters.items():
                if column not in columns:
                    continue
                
                if method == "standard":
                    # Проверяем наличие mean и std
                    if "mean" not in column_params or "std" not in column_params:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Для столбца {column} необходимо указать mean и std"
                        )
                    
                    scaling_params["standardization"]["params"][column] = {
                        "mean": float(column_params["mean"]),
                        "std": float(column_params["std"])
                    }
                
                elif method == "minmax":
                    # Проверяем наличие min и max
                    if "min" not in column_params or "max" not in column_params:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Для столбца {column} необходимо указать min и max"
                        )
                    
                    scaling_params["standardization"]["params"][column] = {
                        "min": float(column_params["min"]),
                        "max": float(column_params["max"])
                    }
            
            # Обновляем метаданные с указанными параметрами масштабирования
            metadata["scaling_params"] = scaling_params
            metadata["manual_params"] = True
            metadata["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Сохраняем обновленные метаданные
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, cls=NumpyEncoder, ensure_ascii=False)
            
            return {
                "status": "success",
                "message": "Параметры масштабирования успешно установлены",
                "scaling_params": scaling_params
            }
        
        except HTTPException:
            raise
        except Exception as e:
            log_error(e, "Ошибка установки параметров масштабирования")
            raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    
    return await with_file_lock(result_id, process_manual_params)