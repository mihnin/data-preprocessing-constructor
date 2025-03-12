import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging
from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder
from sklearn.decomposition import PCA
import statsmodels.api as sm

def get_preprocessing_methods() -> List[Dict[str, Any]]:
    """
    Получение списка доступных методов предобработки.
    """
    methods = [
        {
            "method_id": "missing_values",
            "name": "Обработка пропущенных значений",
            "description": "Заполнение или удаление пропущенных значений в данных",
            "applicable_types": ["numeric", "categorical"],
            "parameters": {
                "strategy": {
                    "type": "select",
                    "options": ["mean", "median", "mode", "drop_rows"],
                    "default": "mean",
                    "description": "Способ обработки пропусков"
                },
                "columns": {
                    "type": "multiselect",
                    "description": "Столбцы для обработки"
                }
            }
        },
        {
            "method_id": "outliers",
            "name": "Обработка выбросов",
            "description": "Обнаружение и обработка аномальных значений",
            "applicable_types": ["numeric"],
            "parameters": {
                "strategy": {
                    "type": "select",
                    "options": ["zscore", "iqr"],
                    "default": "zscore",
                    "description": "Метод обнаружения выбросов"
                },
                "threshold": {
                    "type": "number",
                    "default": 3.0,
                    "description": "Порог для определения выбросов"
                },
                "columns": {
                    "type": "multiselect",
                    "description": "Столбцы для обработки"
                }
            }
        },
        {
            "method_id": "standardization",
            "name": "Стандартизация числовых данных",
            "description": "Приведение числовых признаков к стандартному масштабу",
            "applicable_types": ["numeric"],
            "parameters": {
                "strategy": {
                    "type": "select",
                    "options": ["standard", "minmax"],
                    "default": "standard",
                    "description": "Метод стандартизации"
                },
                "columns": {
                    "type": "multiselect",
                    "description": "Столбцы для обработки"
                }
            }
        },
        {
            "method_id": "categorical_encoding",
            "name": "Кодирование категориальных переменных",
            "description": "Преобразование категориальных данных в числовой формат",
            "applicable_types": ["categorical"],
            "parameters": {
                "strategy": {
                    "type": "select",
                    "options": ["onehot", "label"],
                    "default": "onehot",
                    "description": "Метод кодирования"
                },
                "columns": {
                    "type": "multiselect",
                    "description": "Столбцы для обработки"
                }
            }
        },
        {
            "method_id": "pca",
            "name": "Снижение размерности (PCA)",
            "description": "Уменьшение количества признаков при сохранении информативности",
            "applicable_types": ["numeric"],
            "parameters": {
                "n_components": {
                    "type": "number",
                    "default": 2,
                    "description": "Количество компонент"
                },
                "columns": {
                    "type": "multiselect",
                    "description": "Столбцы для обработки"
                }
            }
        },
        {
            "method_id": "lagging",
            "name": "Лагирование переменных",
            "description": "Создание лагированных версий переменных для временных рядов",
            "applicable_types": ["numeric"],
            "parameters": {
                "target_column": {
                    "type": "select",
                    "description": "Целевая переменная"
                },
                "lag_periods": {
                    "type": "multiselect",
                    "options": [1, 2, 3, 4, 5, 6, 7, 14, 30],
                    "default": [1, 2, 3],
                    "description": "Периоды лагирования"
                },
                "exog_columns": {
                    "type": "multiselect",
                    "description": "Экзогенные переменные для лагирования"
                }
            }
        },
        {
            "method_id": "rolling_statistics",
            "name": "Скользящие статистики",
            "description": "Расчет статистик в скользящем окне для временных рядов",
            "applicable_types": ["numeric"],
            "parameters": {
                "target_column": {
                    "type": "select",
                    "description": "Целевая переменная"
                },
                "window_size": {
                    "type": "number",
                    "default": 3,
                    "description": "Размер окна"
                },
                "statistics": {
                    "type": "multiselect",
                    "options": ["mean", "std", "min", "max"],
                    "default": ["mean", "std"],
                    "description": "Статистики для расчета"
                }
            }
        },
        {
            "method_id": "date_components",
            "name": "Извлечение компонентов даты",
            "description": "Извлечение года, месяца, квартала, дня недели из столбцов с датами",
            "applicable_types": ["datetime"],
            "parameters": {
                "columns": {
                    "type": "multiselect",
                    "description": "Столбцы с датами для обработки"
                },
                "components": {
                    "type": "multiselect",
                    "options": ["year", "month", "quarter", "day_of_week", "day_of_month", "day_of_year", "week_of_year"],
                    "default": ["year", "month", "quarter", "day_of_week"],
                    "description": "Компоненты даты для извлечения"
                }
            }
        },
        {
            "method_id": "inverse_scaling",
            "name": "Обратное масштабирование",
            "description": "Отмена стандартизации или нормализации данных",
            "applicable_types": ["numeric"],
            "parameters": {
                "scaling_params": {
                    "type": "object",
                    "description": "Параметры масштабирования для обратного преобразования"
                },
                "columns": {
                    "type": "multiselect",
                    "description": "Столбцы для обработки"
                }
            }
        }
    ]
    
    return methods

def apply_preprocessing(df: pd.DataFrame, config: Dict[str, Any], 
                        progress_callback=None) -> pd.DataFrame:
    """
    Применение методов предобработки к данным.
    """
    processed_df = df.copy()
    
    for method_idx, method in enumerate(config["methods"]):
        method_id = method["method_id"]
        parameters = method.get("parameters", {})
        
        # Вызов callback для обновления прогресса
        if progress_callback:
            progress_callback(method_idx, getMethodName(method_id))
        
        if method_id == "missing_values":
            strategy = parameters.get("strategy", "mean")
            columns = parameters.get("columns", [])
            
            # Если столбцы не указаны, применяем ко всем числовым
            if not columns:
                columns = processed_df.select_dtypes(include=np.number).columns.tolist()
            
            for col in columns:
                if col in processed_df.columns and processed_df[col].isna().any():
                    if strategy == "mean" and pd.api.types.is_numeric_dtype(processed_df[col]):
                        processed_df[col] = processed_df[col].fillna(processed_df[col].mean())
                    elif strategy == "median" and pd.api.types.is_numeric_dtype(processed_df[col]):
                        processed_df[col] = processed_df[col].fillna(processed_df[col].median())
                    elif strategy == "mode":
                        # Для категориальных переменных используем моду
                        processed_df[col] = processed_df[col].fillna(processed_df[col].mode()[0])
                    elif strategy == "drop_rows":
                        processed_df = processed_df.dropna(subset=[col])
        
        elif method_id == "outliers":
            strategy = parameters.get("strategy", "zscore")
            threshold = parameters.get("threshold", 3.0)
            columns = parameters.get("columns", [])
            
            # Если столбцы не указаны, применяем ко всем числовым
            if not columns:
                columns = processed_df.select_dtypes(include=np.number).columns.tolist()
            
            for col in columns:
                if col in processed_df.columns and pd.api.types.is_numeric_dtype(processed_df[col]):
                    if strategy == "zscore":
                        # Z-оценка для обнаружения выбросов
                        z_scores = np.abs((processed_df[col] - processed_df[col].mean()) / processed_df[col].std())
                        processed_df = processed_df[z_scores < threshold]
                    elif strategy == "iqr":
                        # Межквартильный размах для обнаружения выбросов
                        Q1 = processed_df[col].quantile(0.25)
                        Q3 = processed_df[col].quantile(0.75)
                        IQR = Q3 - Q1
                        lower_bound = Q1 - threshold * IQR
                        upper_bound = Q3 + threshold * IQR
                        processed_df = processed_df[(processed_df[col] >= lower_bound) & 
                                                   (processed_df[col] <= upper_bound)]
        
        elif method_id == "standardization":
            strategy = parameters.get("strategy", "standard")
            columns = parameters.get("columns", [])
            # Если столбцы не указаны, применяем ко всем числовым
            if not columns:
                columns = processed_df.select_dtypes(include=np.number).columns.tolist()
            
            if not columns:
                # Пропускаем, если нет числовых столбцов
                continue
            
            # Создаем словарь для хранения параметров масштабирования
            scaling_params = {
                "method": strategy,
                "columns": columns,
                "params": {}
            }
            
            # Проверяем наличие столбцов в DataFrame
            valid_columns = [col for col in columns if col in processed_df.columns]
            if not valid_columns:
                continue
                    
            if strategy == "standard":
                # Для каждого столбца сохраняем параметры масштабирования
                for col in valid_columns:
                    mean_val = float(processed_df[col].mean())
                    std_val = float(processed_df[col].std()) if float(processed_df[col].std()) != 0 else 1.0
                    
                    scaling_params["params"][col] = {
                        "mean": mean_val,
                        "std": std_val
                    }
                
                scaler = StandardScaler()
            
            elif strategy == "minmax":
                # Для каждого столбца сохраняем параметры масштабирования
                for col in valid_columns:
                    min_val = float(processed_df[col].min())
                    max_val = float(processed_df[col].max())
                    
                    scaling_params["params"][col] = {
                        "min": min_val,
                        "max": max_val
                    }
                
                scaler = MinMaxScaler()
            else:
                continue
            
            # Применяем стандартизацию
            processed_df[valid_columns] = scaler.fit_transform(processed_df[valid_columns])
            
            # Добавляем параметры масштабирования к DataFrame в виде атрибута
            if not hasattr(processed_df, 'scaling_params'):
                processed_df.scaling_params = {}
            
            processed_df.scaling_params["standardization"] = scaling_params
        
        elif method_id == "categorical_encoding":
            strategy = parameters.get("strategy", "onehot")
            columns = parameters.get("columns", [])
            
            # Если столбцы не указаны, применяем ко всем категориальным
            if not columns:
                columns = processed_df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            for col in columns:
                if col in processed_df.columns:
                    if strategy == "onehot":
                        # One-hot кодирование
                        dummies = pd.get_dummies(processed_df[col], prefix=col)
                        processed_df = pd.concat([processed_df.drop(columns=[col]), dummies], axis=1)
                    elif strategy == "label":
                        # Label кодирование
                        processed_df[col] = processed_df[col].astype('category').cat.codes
        
        elif method_id == "pca":
            n_components = parameters.get("n_components", 2)
            columns = parameters.get("columns", [])
            
            # Если столбцы не указаны, применяем ко всем числовым
            if not columns:
                columns = processed_df.select_dtypes(include=np.number).columns.tolist()
            
            if len(columns) > 1:
                # Проверяем наличие столбцов в DataFrame
                valid_columns = [col for col in columns if col in processed_df.columns]
                if len(valid_columns) < 2:
                    continue
                
                # Заполняем пропущенные значения для PCA
                for col in valid_columns:
                    if processed_df[col].isna().any():
                        processed_df[col] = processed_df[col].fillna(processed_df[col].mean())
                
                # Применяем PCA
                pca = PCA(n_components=min(n_components, len(valid_columns)))
                pca_result = pca.fit_transform(processed_df[valid_columns])
                
                # Удаляем исходные столбцы и добавляем компоненты PCA
                processed_df = processed_df.drop(columns=valid_columns)
                for i in range(pca_result.shape[1]):
                    processed_df[f'PCA_{i+1}'] = pca_result[:, i]
        
        elif method_id == "lagging":
            target_column = parameters.get("target_column")
            lag_periods = parameters.get("lag_periods", [1, 2, 3])
            exog_columns = parameters.get("exog_columns", [])
            
            if target_column and target_column in processed_df.columns:
                # Создаем лаги для целевой переменной
                for lag in lag_periods:
                    processed_df[f'{target_column}_lag_{lag}'] = processed_df[target_column].shift(lag)
            
            # Создаем лаги для экзогенных переменных
            for exog_col in exog_columns:
                if exog_col in processed_df.columns:
                    for lag in lag_periods:
                        processed_df[f'{exog_col}_lag_{lag}'] = processed_df[exog_col].shift(lag)
        
        elif method_id == "rolling_statistics":
            target_column = parameters.get("target_column")
            window_size = parameters.get("window_size", 3)
            statistics = parameters.get("statistics", ["mean", "std"])
            
            if target_column and target_column in processed_df.columns:
                # Расчет скользящих статистик
                for stat in statistics:
                    if stat == "mean":
                        processed_df[f'{target_column}_rolling_mean_{window_size}'] = processed_df[target_column].rolling(window=window_size).mean()
                    elif stat == "std":
                        processed_df[f'{target_column}_rolling_std_{window_size}'] = processed_df[target_column].rolling(window=window_size).std()
                    elif stat == "min":
                        processed_df[f'{target_column}_rolling_min_{window_size}'] = processed_df[target_column].rolling(window=window_size).min()
                    elif stat == "max":
                        processed_df[f'{target_column}_rolling_max_{window_size}'] = processed_df[target_column].rolling(window=window_size).max()
        
        elif method_id == "date_components":
            columns = parameters.get("columns", [])
            components = parameters.get("components", ["year", "month", "quarter", "day_of_week"])
            
            # Если столбцы не указаны, ищем столбцы с датами
            if not columns:
                # Пытаемся обнаружить столбцы с датами
                datetime_columns = []
                for col in processed_df.columns:
                    if pd.api.types.is_datetime64_dtype(processed_df[col]):
                        datetime_columns.append(col)
                    else:
                        # Пробуем конвертировать в дату
                        try:
                            pd.to_datetime(processed_df[col], errors='raise')
                            datetime_columns.append(col)
                        except:
                            pass
                columns = datetime_columns
            
            for col in columns:
                if col in processed_df.columns:
                    # Конвертируем в datetime, если еще не datetime
                    if not pd.api.types.is_datetime64_dtype(processed_df[col]):
                        try:
                            processed_df[col] = pd.to_datetime(processed_df[col])
                        except Exception as e:
                            logging.warning(f"Не удалось преобразовать столбец {col} в дату: {str(e)}")
                            continue
                    
                    # Извлекаем компоненты даты
                    for component in components:
                        if component == "year":
                            processed_df[f'{col}_year'] = processed_df[col].dt.year
                        elif component == "month":
                            processed_df[f'{col}_month'] = processed_df[col].dt.month
                        elif component == "quarter":
                            processed_df[f'{col}_quarter'] = processed_df[col].dt.quarter
                        elif component == "day_of_week":
                            processed_df[f'{col}_day_of_week'] = processed_df[col].dt.dayofweek + 1  # +1 для 1-7 вместо 0-6
                        elif component == "day_of_month":
                            processed_df[f'{col}_day_of_month'] = processed_df[col].dt.day
                        elif component == "day_of_year":
                            processed_df[f'{col}_day_of_year'] = processed_df[col].dt.dayofyear
                        elif component == "week_of_year":
                            processed_df[f'{col}_week_of_year'] = processed_df[col].dt.isocalendar().week
        
        elif method_id == "inverse_scaling":
            scaling_params = parameters.get("scaling_params", {})
            if not scaling_params:
                continue
                
            standardization_params = scaling_params.get("standardization", {})
            method_name = standardization_params.get("method")
            columns = standardization_params.get("columns", [])
            params = standardization_params.get("params", {})
            
            # Проверяем наличие столбцов в DataFrame
            valid_columns = [col for col in columns if col in processed_df.columns]
            if not valid_columns:
                continue
                
            # Применяем обратное масштабирование
            if method_name == "standard":
                for col in valid_columns:
                    if col in params:
                        mean = params[col].get("mean", 0)
                        std = params[col].get("std", 1)
                        if std == 0:
                            std = 1  # Избегаем деления на ноль
                        
                        # Обратное преобразование: x_original = x_scaled * std + mean
                        processed_df[col] = processed_df[col] * std + mean
                        
            elif method_name == "minmax":
                for col in valid_columns:
                    if col in params:
                        min_val = params[col].get("min", 0)
                        max_val = params[col].get("max", 1)
                        range_val = max_val - min_val
                        if range_val == 0:
                            range_val = 1  # Избегаем деления на ноль
                        
                        # Обратное преобразование: x_original = x_scaled * (max - min) + min
                        processed_df[col] = processed_df[col] * range_val + min_val
    
    return processed_df

def apply_inverse_scaling(df: pd.DataFrame, columns: List[str], scaling_params: Dict[str, Any]) -> pd.DataFrame:
    """
    Применяет обратное масштабирование к указанным столбцам.
    
    Args:
        df: Исходный DataFrame
        columns: Список столбцов для обратного масштабирования
        scaling_params: Параметры масштабирования в различных форматах
    
    Returns:
        DataFrame с обратно масштабированными данными
    """
    # Создаем копию DataFrame
    processed_df = df.copy()
    
    # Определяем формат параметров масштабирования и извлекаем нужные данные
    method_name = None
    params = {}
    
    # Формат 1: {standardization: {method, columns, params}}
    if "standardization" in scaling_params:
        standardization_params = scaling_params.get("standardization", {})
        method_name = standardization_params.get("method")
        params = standardization_params.get("params", {})
    
    # Формат 2: {method, columns, params/parameters}
    elif "method" in scaling_params:
        method_name = scaling_params.get("method")
        # Проверяем оба возможных ключа для параметров
        params = scaling_params.get("params", {}) or scaling_params.get("parameters", {})
    
    # Формат 3: {type, ...} (используется в datasets.py)
    elif "type" in scaling_params:
        method_name = scaling_params.get("type")
        # В этом формате параметры могут быть в разных ключах в зависимости от типа масштабирования
        if method_name == "standard":
            # Собираем параметры для standard scaling
            means = scaling_params.get("mean", {})
            stds = scaling_params.get("std", {})
            for col in columns:
                if col in means and col in stds:
                    params[col] = {"mean": means[col], "std": stds[col]}
        elif method_name == "minmax":
            # Собираем параметры для minmax scaling
            mins = scaling_params.get("min", {})
            maxs = scaling_params.get("max", {})
            for col in columns:
                if col in mins and col in maxs:
                    params[col] = {"min": mins[col], "max": maxs[col]}
    
    # Если метод не определен, пробуем угадать по наличию параметров
    if not method_name:
        # Проверяем наличие параметров mean/std или min/max для первого столбца
        if columns and columns[0] in params:
            col_params = params[columns[0]]
            if "mean" in col_params and "std" in col_params:
                method_name = "standard"
            elif "min" in col_params and "max" in col_params:
                method_name = "minmax"
    
    # Фильтруем столбцы, которые есть в датафрейме и в параметрах
    valid_columns = [col for col in columns if col in processed_df.columns and col in params]
    
    if not valid_columns or not method_name:
        # Если нет подходящих столбцов или метод не определен, возвращаем исходный DataFrame
        return processed_df
    
    # Применяем обратное масштабирование в зависимости от метода
    if method_name == "standard":
        for col in valid_columns:
            mean = params[col].get("mean", 0)
            std = params[col].get("std", 1)
            if std == 0:
                std = 1  # Избегаем деления на ноль
            
            # Обратное преобразование: x_original = x_scaled * std + mean
            processed_df[col] = processed_df[col] * std + mean
    
    elif method_name == "minmax":
        for col in valid_columns:
            min_val = params[col].get("min", 0)
            max_val = params[col].get("max", 1)
            range_val = max_val - min_val
            if range_val == 0:
                range_val = 1  # Избегаем деления на ноль
            
            # Обратное преобразование: x_original = x_scaled * (max - min) + min
            processed_df[col] = processed_df[col] * range_val + min_val
    
    return processed_df

def getMethodName(method_id):
    """Получение читаемого названия метода по его ID"""
    method_names = {
        'missing_values': 'Обработка пропущенных значений',
        'outliers': 'Обработка выбросов',
        'standardization': 'Стандартизация данных',
        'categorical_encoding': 'Кодирование категориальных переменных',
        'pca': 'Снижение размерности (PCA)',
        'time_series_analysis': 'Анализ временных рядов',
        'lagging': 'Лагирование переменных',
        'rolling_statistics': 'Скользящие статистики',
        'date_components': 'Извлечение компонентов даты',
        'inverse_scaling': 'Обратное масштабирование'  # Добавленный метод
    }
    return method_names.get(method_id, method_id)