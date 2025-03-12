import numpy as np
import pandas as pd
from typing import Any

def convert_numpy_types(obj: Any) -> Any:
    """
    Рекурсивно конвертирует NumPy типы в стандартные Python типы.
    
    Args:
        obj: Объект любого типа, который может содержать NumPy типы.
        
    Returns:
        Объект того же типа, но с NumPy типами, преобразованными в стандартные Python типы.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        # Обработка специальных значений
        if np.isnan(obj):
            return None
        if np.isinf(obj):
            return None if obj < 0 else float(1e308)  # Заменяем на большое конечное число или None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    elif pd.isna(obj):  # Проверка на все типы NaN/None
        return None
    else:
        return obj