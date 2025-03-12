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
        }
    ]
    
    return methods

def apply_preprocessing(df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Применение методов предобработки к данным.
    """
    processed_df = df.copy()
    
    for method in config["methods"]:
        method_id = method["method_id"]
        parameters = method.get("parameters", {})
        
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
                
            if strategy == "standard":
                scaler = StandardScaler()
            elif strategy == "minmax":
                scaler = MinMaxScaler()
            else:
                continue
            
            # Проверяем наличие столбцов в DataFrame
            valid_columns = [col for col in columns if col in processed_df.columns]
            if not valid_columns:
                continue
            
            # Применяем стандартизацию
            processed_df[valid_columns] = scaler.fit_transform(processed_df[valid_columns])
        
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
    
    return processed_df