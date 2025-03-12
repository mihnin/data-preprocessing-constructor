import pandas as pd
import json
import time
from pathlib import Path
from ..utils.validation_utils import load_and_validate_dataframe
from ..utils.file_utils import get_processed_file_path
from ..utils.json_utils import NumpyEncoder
from ..utils.logging_utils import log_error

async def process_data(dataset_id: str, result_id: str, config, file_path: Path, extension: str):
    """
    Обрабатывает данные согласно конфигурации и сохраняет результат.
    """
    try:
        # Функция для обновления прогресса
        def update_progress(stage: str, percent: int, method_name: str = None):
            progress_data = {
                "stage": stage,
                "percent": percent,
                "method_name": method_name,
                "timestamp": time.time()
            }
            progress_path = get_processed_file_path(result_id).parent / f"{result_id}_progress.json"
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump(progress_data, f, ensure_ascii=False)
        
        # Обновляем прогресс - начало загрузки
        update_progress("loading", 5)
        
        # Загружаем и валидируем данные
        df = await load_and_validate_dataframe(file_path, extension)
        
        # Обновляем прогресс - начало обработки
        update_progress("preprocessing", 20)
        
        # Получаем общее количество методов для расчета прогресса
        total_methods = len(config.dict()["methods"])
        
        # Применяем предобработку с отслеживанием прогресса
        processed_df = apply_preprocessing(df, config.dict(), 
                                          progress_callback=lambda method_idx, method_name:
                                          update_progress("processing_method", 
                                                         20 + int(70 * (method_idx + 1) / total_methods),
                                                         method_name))
        
        # Обновляем прогресс - сохранение результатов
        update_progress("saving", 90)
        
        # Сохраняем результаты
        result_path = get_processed_file_path(result_id)
        processed_df.to_csv(result_path, index=False, encoding='utf-8')
        
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
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, cls=NumpyEncoder, ensure_ascii=False)
        
        # Обновляем прогресс - завершение
        update_progress("completed", 100)
    
    except Exception as e:
        # Обновляем прогресс - ошибка
        update_progress("error", 0, str(e))
        log_error(e, f"Ошибка при обработке данных для result_id={result_id}")
        # Сохраняем информацию об ошибке
        error_path = get_processed_file_path(result_id).parent / f"{result_id}_error.txt"
        with open(error_path, "w", encoding="utf-8") as f:
            f.write(str(e))

def apply_preprocessing(df: pd.DataFrame, config: dict, progress_callback=None) -> pd.DataFrame:
    """
    Применяет шаги предобработки к DataFrame на основе конфигурации.
    
    Args:
        df: DataFrame для обработки
        config: Конфигурация с методами обработки
        progress_callback: Функция обратного вызова для отслеживания прогресса
                          Принимает индекс метода и его название
    """
    # Здесь должна быть реализация применения шагов предобработки
    if "methods" in config:
        for idx, method in enumerate(config["methods"]):
            # Если предоставлена функция обратного вызова, вызываем ее
            if progress_callback:
                method_name = method.get("name", f"method_{idx}")
                progress_callback(idx, method_name)
            
            # Здесь должна быть реализация применения конкретного метода
            
    return df
