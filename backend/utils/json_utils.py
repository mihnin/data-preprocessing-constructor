import numpy as np
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
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj