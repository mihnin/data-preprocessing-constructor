import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import logging

def detect_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """
    Автоматическое определение типов столбцов.
    """
    column_types = {}
    
    for col in df.columns:
        col_data = df[col]
        
        if pd.api.types.is_numeric_dtype(col_data):
            column_types[col] = "numeric"
        elif pd.api.types.is_datetime64_dtype(col_data):
            column_types[col] = "datetime"
        else:
            # Пытаемся преобразовать в дату
            try:
                pd.to_datetime(col_data, errors='raise')
                column_types[col] = "datetime"
            except:
                # Если не получилось, считаем столбец категориальным
                column_types[col] = "categorical"
    
    return column_types

def detect_time_series(df: pd.DataFrame, datetime_columns: List[str]) -> List[str]:
    """
    Определение столбцов временных рядов.
    """
    time_series_columns = []
    
    for col in datetime_columns:
        col_data = df[col]
        
        # Проверяем, отсортированы ли данные по времени
        sorted_dates = col_data.sort_values()
        if sorted_dates.equals(col_data) or sorted_dates.equals(col_data.iloc[::-1]):
            time_series_columns.append(col)
    
    return time_series_columns

def calculate_column_statistics(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    """
    Расчет статистик для столбца.
    """
    col_data = df[column]
    
    stats = {
        "missing_count": col_data.isna().sum(),
        "unique_count": col_data.nunique()
    }
    
    if pd.api.types.is_numeric_dtype(col_data):
        stats.update({
            "min_value": float(col_data.min()) if not pd.isna(col_data.min()) else None,
            "max_value": float(col_data.max()) if not pd.isna(col_data.max()) else None,
            "mean_value": float(col_data.mean()) if not pd.isna(col_data.mean()) else None,
            "median_value": float(col_data.median()) if not pd.isna(col_data.median()) else None,
            "std_value": float(col_data.std()) if not pd.isna(col_data.std()) else None
        })
    
    return stats