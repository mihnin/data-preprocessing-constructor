import pandas as pd
from fastapi import HTTPException
from pathlib import Path
import logging
from typing import Tuple, Optional, List

def validate_dataframe(df: pd.DataFrame, max_rows: int = 1000000) -> Tuple[bool, Optional[str]]:
    """
    Проверяет DataFrame на корректность и соответствие требованиям.
    
    Args:
        df: Pandas DataFrame для проверки
        max_rows: Максимальное допустимое количество строк
    
    Returns:
        Tuple[bool, Optional[str]]: (успех, сообщение об ошибке)
    """
    # Проверка на пустой DataFrame
    if df.empty:
        return False, "Файл не содержит данных"
    
    # Проверка на количество строк
    if len(df) > max_rows:
        return False, f"Превышен лимит в {max_rows} строк"
    
    # Проверка на количество столбцов
    if len(df.columns) < 1:
        return False, "Файл должен содержать хотя бы один столбец"
    
    # Проверка на дубликаты в заголовках
    if len(df.columns) != len(set(df.columns)):
        return False, "Обнаружены дубликаты в названиях столбцов"
    
    # Проверка на корректность данных (проверка на наличие строк с одними NaN)
    if df.isna().all(axis=1).any():
        return False, "Обнаружены строки, состоящие только из пропущенных значений"
    
    return True, None

async def load_and_validate_dataframe(file_path: Path, extension: str, encoding: str = 'utf-8') -> pd.DataFrame:
    """
    Загружает и валидирует DataFrame из файла.
    
    Args:
        file_path: Путь к файлу
        extension: Расширение файла
        encoding: Кодировка файла (по умолчанию utf-8)
    
    Returns:
        pd.DataFrame: Загруженный и проверенный DataFrame
    
    Raises:
        HTTPException: Если файл не соответствует требованиям
    """
    try:
        # Загружаем данные
        if extension.lower() == "csv":
            # Пробуем разные разделители
            separators = [',', ';', '\t', '|']
            df = None
            exception = None
            
            for sep in separators:
                try:
                    df = pd.read_csv(file_path, sep=sep, encoding=encoding)
                    # Если есть только один столбец, возможно разделитель неверный
                    if len(df.columns) > 1:
                        break
                except Exception as e:
                    exception = e
            
            if df is None or len(df.columns) <= 1:
                raise HTTPException(
                    status_code=400, 
                    detail="Не удалось правильно прочитать CSV файл. Проверьте формат и разделитель."
                )
        else:  # Excel
            df = pd.read_excel(file_path, engine='openpyxl')
        
        # Валидируем DataFrame
        is_valid, error_message = validate_dataframe(df)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        return df
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Ошибка при загрузке и валидации файла: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка при обработке файла: {str(e)}"
        )