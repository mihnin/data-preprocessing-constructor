import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging

def analyze_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Анализ загруженного набора данных.
    """
    analysis = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": [],
        "recommended_methods": []
    }
    
    # Анализ столбцов
    for col in df.columns:
        col_data = df[col]
        is_numeric = pd.api.types.is_numeric_dtype(col_data)
        is_datetime = pd.api.types.is_datetime64_dtype(col_data)
        
        # Пытаемся автоматически определить даты, если они не распознаны как даты
        if not is_datetime and not is_numeric:
            try:
                pd.to_datetime(col_data, errors='raise')
                is_datetime = True
            except:
                pass
        
        col_info = {
            "name": col,
            "type": "numeric" if is_numeric else "datetime" if is_datetime else "categorical",
            "missing_count": col_data.isna().sum(),
            "unique_count": col_data.nunique(),
            "is_time_series": False
        }
        
        if is_numeric:
            col_info.update({
                "min_value": float(col_data.min()) if not pd.isna(col_data.min()) else None,
                "max_value": float(col_data.max()) if not pd.isna(col_data.max()) else None,
                "mean_value": float(col_data.mean()) if not pd.isna(col_data.mean()) else None
            })
        
        # Проверка на временной ряд
        if is_datetime and len(df) > 10:
            # Проверяем, отсортированы ли данные по времени
            sorted_dates = col_data.sort_values()
            if sorted_dates.equals(col_data) or sorted_dates.equals(col_data.iloc[::-1]):
                col_info["is_time_series"] = True
        
        analysis["columns"].append(col_info)
    
    # Рекомендуемые методы предобработки
    has_missing = any(col["missing_count"] > 0 for col in analysis["columns"])
    has_numeric = any(col["type"] == "numeric" for col in analysis["columns"])
    has_categorical = any(col["type"] == "categorical" for col in analysis["columns"])
    has_time_series = any(col["is_time_series"] for col in analysis["columns"])
    
    # Добавляем рекомендации
    if has_missing:
        analysis["recommended_methods"].append("missing_values")
    
    if has_numeric:
        analysis["recommended_methods"].append("outliers")
        analysis["recommended_methods"].append("standardization")
        
        # Если много числовых столбцов, рекомендуем PCA
        numeric_cols = [col for col in analysis["columns"] if col["type"] == "numeric"]
        if len(numeric_cols) > 5:
            analysis["recommended_methods"].append("pca")
    
    if has_categorical:
        analysis["recommended_methods"].append("categorical_encoding")
    
    if has_time_series:
        analysis["recommended_methods"].append("time_series_analysis")
        analysis["recommended_methods"].append("lagging")
        analysis["recommended_methods"].append("rolling_statistics")
    
    return analysis