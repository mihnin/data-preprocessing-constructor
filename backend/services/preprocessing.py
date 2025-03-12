import pandas as pd
import json
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
        # Загружаем и валидируем данные
        df = await load_and_validate_dataframe(file_path, extension)
        
        # Применяем предобработку
        processed_df = apply_preprocessing(df, config.dict())
        
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
    
    except Exception as e:
        log_error(e, f"Ошибка при обработке данных для result_id={result_id}")
        # Сохраняем информацию об ошибке
        error_path = get_processed_file_path(result_id).parent / f"{result_id}_error.txt"
        with open(error_path, "w", encoding="utf-8") as f:
            f.write(str(e))

def apply_preprocessing(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Применяет шаги предобработки к DataFrame на основе конфигурации.
    """
    # Здесь должна быть реализация применения шагов предобработки
    return df
