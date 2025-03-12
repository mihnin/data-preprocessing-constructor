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
import time  # Add time module import
from pathlib import Path

# Импорты из собственных модулей
from services.dataset_service import analyze_dataset
from utils.file_utils import save_uploaded_file, get_file_path_by_id, get_processed_file_path
from utils.json_utils import convert_numpy_types
from utils.validation_utils import load_and_validate_dataframe
from utils.error_utils import handle_exceptions, log_error
from utils.lock_utils import with_file_lock, is_file_processing

# Добавляем импорт для временной директории
from config.settings import TEMP_DIR

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

@router.post("/{dataset_id}/set-target")
@handle_exceptions
async def set_target_column(dataset_id: str, data: dict):
    """
    Установка целевой переменной для набора данных.
    """
    # Проверяем, обрабатывается ли файл в данный момент
    if is_file_processing(dataset_id):
        return {"status": "processing", "message": "Файл в данный момент обрабатывается"}
    
    target_column = data.get("target_column")
    if not target_column:
        raise HTTPException(status_code=400, detail="Целевая переменная не указана")
    
    async def update_metadata():
        # Ищем метаданные
        for extension in ["csv", "xlsx", "xls"]:
            file_path = get_file_path_by_id(dataset_id, extension)
            metadata_path = file_path.parent / f"{dataset_id}_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                
                # Обновляем информацию о целевой переменной
                metadata["target_column"] = target_column
                
                # Обновляем статус целевой переменной в колонках
                for col in metadata["columns"]:
                    col["is_target"] = col["name"] == target_column
                
                # Сохраняем обновленные метаданные
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, cls=NumpyEncoder)
                
                return convert_numpy_types(metadata)
        
        raise HTTPException(status_code=404, detail="Набор данных не найден")
    
    return await with_file_lock(dataset_id, update_metadata)

@router.get("/export/{result_id}")
@handle_exceptions
async def export_dataset(result_id: str, format: str = "csv"):
    """
    Экспорт обработанных данных.
    
    Поддерживаемые форматы: csv, excel.
    """
    async def process_export():
        try:
            # Получаем путь к файлу результатов
            result_path = get_processed_file_path(result_id)
            
            if not result_path.exists():
                raise HTTPException(status_code=404, detail="Результаты не найдены")
            
            # Загружаем данные
            df = pd.read_csv(result_path, encoding='utf-8')
            
            if format.lower() == "excel":
                # Создаем временный файл Excel
                excel_path = TEMP_DIR / f"{result_id}.xlsx"
                
                # Используем openpyxl явно с полной настройкой параметров Unicode
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Результаты')
                
                return FileResponse(
                    excel_path, 
                    filename=f"processed_data_{result_id}.xlsx",
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:  # По умолчанию CSV
                # Сохраняем с BOM (Byte Order Mark) для распознавания кодировки Excel
                csv_path = TEMP_DIR / f"{result_id}.csv"
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                
                return FileResponse(
                    csv_path, 
                    filename=f"processed_data_{result_id}.csv",
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f'attachment; filename="processed_data_{result_id}.csv"',
                        "Content-Type": "text/csv; charset=utf-8"
                    }
                )
        
        except HTTPException:
            raise
        except Exception as e:
            log_error(e, "Ошибка экспорта данных")
            raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    
    return await with_file_lock(result_id, process_export)

# Функция для применения обратного масштабирования
def apply_inverse_scaling(df: pd.DataFrame, columns: List[str], scaling_params: Dict[str, Any]) -> pd.DataFrame:
    """
    Применяет обратное масштабирование к указанным столбцам DataFrame.
    
    Args:
        df: Исходный DataFrame
        columns: Список столбцов для обратного масштабирования
        scaling_params: Параметры масштабирования (тип и значения)
    
    Returns:
        DataFrame с обратно масштабированными столбцами
    """
    result_df = df.copy()
    
    scaling_type = scaling_params.get("type")
    
    for column in columns:
        if column not in df.columns:
            continue
            
        if scaling_type == "standard":
            # Обратное масштабирование для стандартизации (z-score)
            mean = scaling_params.get("mean", {}).get(column)
            std = scaling_params.get("std", {}).get(column)
            if mean is not None and std is not None:
                result_df[column] = result_df[column] * std + mean
                
        elif scaling_type == "minmax":
            # Обратное масштабирование для MinMax
            min_val = scaling_params.get("min", {}).get(column)
            max_val = scaling_params.get("max", {}).get(column)
            if min_val is not None and max_val is not None:
                result_df[column] = result_df[column] * (max_val - min_val) + min_val
                
        elif scaling_type == "robust":
            # Обратное масштабирование для RobustScaler
            median = scaling_params.get("median", {}).get(column)
            iqr = scaling_params.get("iqr", {}).get(column)
            if median is not None and iqr is not None:
                result_df[column] = result_df[column] * iqr + median
    
    return result_df

@router.post("/{dataset_id}/apply-inverse-scaling")
@handle_exceptions
async def apply_inverse_scaling_to_dataset(dataset_id: str, data: dict):
    """
    Применяет обратное масштабирование к столбцам датасета.
    """
    # Проверка обрабатывается ли файл
    if is_file_processing(dataset_id):
        return {"status": "processing", "message": "Файл в данный момент обрабатывается"}
    
    # Проверяем входные данные и логируем их для диагностики
    logging.info(f"Получены данные для обратного масштабирования: {data}")
    
    columns = data.get("columns", [])
    scaling_params = data.get("scaling_params")
    
    if not columns:
        logging.warning(f"Не указаны столбцы для обратного масштабирования: {data}")
        raise HTTPException(status_code=400, detail="Необходимо указать столбцы для масштабирования")
    
    # Log the structure of scaling_params to help identify issues
    logging.info(f"Structure of scaling_params: {scaling_params.keys() if isinstance(scaling_params, dict) else type(scaling_params)}")

    # If scaling_params is empty or not properly structured, return a clearer error
    if not scaling_params or not isinstance(scaling_params, dict) or len(scaling_params) == 0:
        logging.warning(f"Empty or invalid scaling_params: {scaling_params}")
        raise HTTPException(
            status_code=400, 
            detail="Параметры масштабирования отсутствуют или имеют неверный формат"
        )

    # Check for required keys based on expected structure patterns
    valid_structure = False
    if "standardization" in scaling_params:
        valid_structure = True
    elif "type" in scaling_params or "method" in scaling_params:
        valid_structure = True
    elif "mean" in scaling_params or "min" in scaling_params:
        valid_structure = True

    if not valid_structure:
        logging.warning(f"Invalid scaling_params structure: {scaling_params}")
        raise HTTPException(
            status_code=400, 
            detail="Параметры масштабирования имеют неверную структуру. Необходимы ключи standardization, type/method, или mean/min"
        )
    
    if not scaling_params:
        logging.warning(f"Не указаны параметры масштабирования: {data}")
        raise HTTPException(status_code=400, detail="Необходимо указать параметры масштабирования")
    
    # Проверяем структуру scaling_params
    if isinstance(scaling_params, dict) and not scaling_params:
        logging.warning(f"Неверная структура параметров масштабирования: {scaling_params}")
        raise HTTPException(
            status_code=400, 
            detail="Параметры масштабирования должны содержать информацию о методе и значениях"
        )
    
    async def process_inverse_scaling():
        # Ищем исходный файл датасета
        file_path = None
        for ext in ["csv", "xlsx", "xls"]:
            temp_path = get_file_path_by_id(dataset_id, ext)
            if temp_path.exists():
                file_path = temp_path
                extension = ext
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail="Набор данных не найден")
        
        # Загружаем данные
        df = await load_and_validate_dataframe(file_path, extension)
        
        # Создаем уникальный ID для результата
        result_id = str(uuid.uuid4())
        
        # Применяем обратное масштабирование
        from services.preprocessing_service import apply_inverse_scaling
        processed_df = apply_inverse_scaling(df, columns, scaling_params)
        
        # Сохраняем результат
        result_path = get_processed_file_path(result_id)
        processed_df.to_csv(result_path, index=False)
        
        # Сохраняем метаданные
        metadata = {
            "dataset_id": dataset_id,
            "result_id": result_id,
            "row_count": len(processed_df),
            "column_count": len(processed_df.columns),
            "columns": processed_df.columns.tolist(),
            "inverse_scaling_applied": {
                "columns": columns,
                "scaling_params": scaling_params
            }
        }
        
        metadata_path = result_path.parent / f"{result_id}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, cls=NumpyEncoder)
        
        # Применяем convert_numpy_types к результату перед возвратом
        return convert_numpy_types({
            "result_id": result_id,
            "status": "completed",
            "metadata": metadata
        })
    
    return await with_file_lock(dataset_id, process_inverse_scaling)

@router.post("/{dataset_id}/import-metadata")
@handle_exceptions
async def import_metadata_for_dataset(
    dataset_id: str,
    file: UploadFile = File(...)
):
    """
    Импорт метаданных масштабирования из файла для датасета.
    """
    # Проверяем, обрабатывается ли файл в данный момент
    if is_file_processing(dataset_id):
        return {"status": "processing", "message": "Файл в данный момент обрабатывается"}
    
    async def process_metadata_import():
        try:
            # Сохраняем загруженный файл метаданных во временную директорию
            temp_dir = TEMP_DIR
            temp_metadata_path = temp_dir / f"temp_metadata_{str(uuid.uuid4())}.json"
            
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
            
            # Загружаем или создаем метаданные датасета
            metadata_path = None
            for ext in ["csv", "xlsx", "xls"]:
                temp_path = get_file_path_by_id(dataset_id, ext)
                if temp_path.exists():
                    metadata_path = temp_path.parent / f"{dataset_id}_metadata.json"
                    break
            
            if not metadata_path:
                raise HTTPException(status_code=404, detail="Набор данных не найден")
                
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    existing_metadata = json.load(f)
            else:
                existing_metadata = {
                    "dataset_id": dataset_id,
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
    
    return await with_file_lock(dataset_id, process_metadata_import)

@router.post("/{dataset_id}/set-scaling-params")
@handle_exceptions
async def set_scaling_params_for_dataset(dataset_id: str, data: dict):
    """
    Set scaling parameters manually for a dataset.
    """
    # Check if file is being processed
    if is_file_processing(dataset_id):
        return {"status": "processing", "message": "File is currently being processed"}
    
    # Log the received parameters for debugging
    logging.info(f"Received scaling params: {json.dumps(data, default=str)}")
    
    # Validate the scaling parameters
    scaling_params = data.get("scaling_params")
    
    if not scaling_params or not isinstance(scaling_params, dict):
        logging.warning(f"Invalid scaling parameters: {scaling_params}")
        raise HTTPException(
            status_code=400,
            detail="Scaling parameters are missing or have an invalid format"
        )
    
    # Check for required keys based on expected structure patterns
    valid_structure = False
    if "standardization" in scaling_params:
        valid_structure = True
    elif "type" in scaling_params or "method" in scaling_params:
        valid_structure = True
    elif "mean" in scaling_params or "min" in scaling_params:
        valid_structure = True
        
    if not valid_structure:
        logging.warning(f"Invalid scaling_params structure: {scaling_params}")
        raise HTTPException(
            status_code=400,
            detail="Scaling parameters have an invalid structure. Keys like standardization, type/method, or mean/min are required"
        )
    
    async def update_metadata_with_scaling_params():
        # Find the dataset metadata file
        metadata_path = None
        for ext in ["csv", "xlsx", "xls"]:
            temp_path = get_file_path_by_id(dataset_id, ext)
            if temp_path.exists():
                metadata_path = temp_path.parent / f"{dataset_id}_metadata.json"
                break
        
        if not metadata_path:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Load existing metadata or create new one
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            metadata = {
                "dataset_id": dataset_id,
                "columns": []
            }
        
        # Update the metadata with the provided scaling parameters
        metadata["scaling_params"] = scaling_params
        metadata["manually_set"] = True
        metadata["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Save the updated metadata
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, cls=NumpyEncoder, ensure_ascii=False)
        
        return {
            "status": "success",
            "message": "Scaling parameters successfully set",
            "metadata": convert_numpy_types(metadata)
        }
    
    return await with_file_lock(dataset_id, update_metadata_with_scaling_params)