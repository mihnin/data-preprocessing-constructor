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
    
    columns = data.get("columns", [])
    scaling_params = data.get("scaling_params")
    
    if not columns or not scaling_params:
        raise HTTPException(status_code=400, detail="Необходимо указать столбцы и параметры масштабирования")
    
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