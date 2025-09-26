import logging
from typing import Callable, Dict, Any, List, Tuple

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler, StandardScaler

logger = logging.getLogger(__name__)


def get_preprocessing_methods() -> List[Dict[str, Any]]:
    """
    Returns a list of available preprocessing methods with their configurations.
    """
    return [
        {
            "method_id": "missing_values",
            "name": "Handle Missing Values",
            "description": "Fill or remove rows with missing values.",
            "applicable_types": ["numeric", "categorical"],
            "parameters": {
                "strategy": {
                    "type": "select",
                    "options": ["mean", "median", "mode", "drop_rows"],
                    "default": "mean",
                    "description": "Method for handling missing data",
                },
                "columns": {
                    "type": "multiselect",
                    "description": "Columns to process",
                },
            },
        },
        {
            "method_id": "outliers",
            "name": "Handle Outliers",
            "description": "Detect and remove outliers from the dataset.",
            "applicable_types": ["numeric"],
            "parameters": {
                "strategy": {
                    "type": "select",
                    "options": ["zscore", "iqr"],
                    "default": "zscore",
                    "description": "Outlier detection method",
                },
                "threshold": {
                    "type": "number",
                    "default": 3.0,
                    "description": "Threshold for outlier detection",
                },
                "columns": {
                    "type": "multiselect",
                    "description": "Columns to process",
                },
            },
        },
        {
            "method_id": "standardization",
            "name": "Scale Numeric Data",
            "description": "Scale numeric features to a standard range.",
            "applicable_types": ["numeric"],
            "parameters": {
                "strategy": {
                    "type": "select",
                    "options": ["standard", "minmax"],
                    "default": "standard",
                    "description": "Scaling method",
                },
                "columns": {
                    "type": "multiselect",
                    "description": "Columns to scale",
                },
            },
        },
        {
            "method_id": "categorical_encoding",
            "name": "Encode Categorical Variables",
            "description": "Convert categorical data into a numerical format.",
            "applicable_types": ["categorical"],
            "parameters": {
                "strategy": {
                    "type": "select",
                    "options": ["onehot", "label"],
                    "default": "onehot",
                    "description": "Encoding method",
                },
                "columns": {
                    "type": "multiselect",
                    "description": "Columns to encode",
                },
            },
        },
        {
            "method_id": "pca",
            "name": "Dimensionality Reduction (PCA)",
            "description": (
                "Reduce the number of features using Principal Component Analysis."
            ),
            "applicable_types": ["numeric"],
            "parameters": {
                "n_components": {
                    "type": "number",
                    "default": 2,
                    "description": "Number of components",
                },
                "columns": {
                    "type": "multiselect",
                    "description": "Columns to use for PCA",
                },
            },
        },
        {
            "method_id": "date_components",
            "name": "Extract Date Components",
            "description": (
                "Extract features like year, month, and day from date columns."
            ),
            "applicable_types": ["datetime"],
            "parameters": {
                "columns": {
                    "type": "multiselect",
                    "description": "Date columns to process",
                },
                "components": {
                    "type": "multiselect",
                    "options": [
                        "year",
                        "month",
                        "quarter",
                        "day_of_week",
                        "day_of_year",
                    ],
                    "default": ["year", "month"],
                    "description": "Components to extract",
                },
            },
        },
    ]


# --- Individual Preprocessing Handlers ---


def _handle_missing_values(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    strategy = params.get("strategy", "mean")
    columns = params.get("columns") or df.select_dtypes(
        include=np.number
    ).columns.tolist()

    for col in columns:
        if col not in df.columns or not df[col].isna().any():
            continue
        if strategy == "mean" and pd.api.types.is_numeric_dtype(df[col]):
            df[col].fillna(df[col].mean(), inplace=True)
        elif strategy == "median" and pd.api.types.is_numeric_dtype(df[col]):
            df[col].fillna(df[col].median(), inplace=True)
        elif strategy == "mode":
            df[col].fillna(df[col].mode()[0], inplace=True)
        elif strategy == "drop_rows":
            df.dropna(subset=[col], inplace=True)
    return df


def _handle_outliers(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    strategy = params.get("strategy", "zscore")
    threshold = params.get("threshold", 3.0)
    columns = params.get("columns") or df.select_dtypes(
        include=np.number
    ).columns.tolist()

    for col in columns:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        if strategy == "zscore":
            z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
            df = df[z_scores < threshold]
        elif strategy == "iqr":
            q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - threshold * iqr, q3 + threshold * iqr
            df = df[(df[col] >= lower) & (df[col] <= upper)]
    return df


def _perform_standardization(
    df: pd.DataFrame, params: Dict[str, Any]
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    strategy = params.get("strategy", "standard")
    columns = params.get("columns") or df.select_dtypes(
        include=np.number
    ).columns.tolist()
    valid_columns = [col for col in columns if col in df.columns]

    if not valid_columns:
        return df, {}

    scaling_params = {"method": strategy, "columns": valid_columns, "params": {}}

    if strategy == "standard":
        scaler = StandardScaler()
        df[valid_columns] = scaler.fit_transform(df[valid_columns])
        scaling_params["params"] = {
            col: {"mean": mean, "std": std if std > 0 else 1.0}
            for col, mean, std in zip(valid_columns, scaler.mean_, scaler.scale_)
        }
    elif strategy == "minmax":
        scaler = MinMaxScaler()
        df[valid_columns] = scaler.fit_transform(df[valid_columns])
        scaling_params["params"] = {
            col: {"min": min_val, "max": max_val}
            for col, min_val, max_val in zip(
                valid_columns, scaler.min_, scaler.data_max_
            )
        }

    return df, {"standardization": scaling_params}


def _encode_categorical(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    strategy = params.get("strategy", "onehot")
    columns = params.get("columns") or df.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    for col in columns:
        if col not in df.columns:
            continue
        if strategy == "onehot":
            dummies = pd.get_dummies(df[col], prefix=col, dummy_na=False)
            df = pd.concat([df.drop(columns=[col]), dummies], axis=1)
        elif strategy == "label":
            df[col] = df[col].astype("category").cat.codes
    return df


def _apply_pca(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    n_components = params.get("n_components", 2)
    columns = params.get("columns") or df.select_dtypes(
        include=np.number
    ).columns.tolist()
    valid_columns = [c for c in columns if c in df.columns]

    if len(valid_columns) < 2:
        return df

    # PCA requires data with no missing values
    pca_data = df[valid_columns].fillna(df[valid_columns].mean())

    # Ensure n_components is not greater than the number of features
    actual_n_components = min(n_components, len(valid_columns))

    pca = PCA(n_components=actual_n_components)
    pca_result = pca.fit_transform(pca_data)

    df.drop(columns=valid_columns, inplace=True)
    for i in range(pca_result.shape[1]):
        df[f"PCA_{i+1}"] = pca_result[:, i]
    return df


def _extract_date_components(
    df: pd.DataFrame, params: Dict[str, Any]
) -> pd.DataFrame:
    columns = (
        params.get("columns")
        or df.select_dtypes(include="datetime").columns.tolist()
    )
    components = params.get("components", ["year", "month"])

    for col in columns:
        if col not in df.columns:
            continue
        # Ensure column is datetime
        try:
            date_series = pd.to_datetime(df[col])
        except (ValueError, TypeError):
            logger.warning(f"Could not convert column {col} to datetime. Skipping.")
            continue

        if "year" in components:
            df[f"{col}_year"] = date_series.dt.year
        if "month" in components:
            df[f"{col}_month"] = date_series.dt.month
        if "quarter" in components:
            df[f"{col}_quarter"] = date_series.dt.quarter
        if "day_of_week" in components:
            df[f"{col}_day_of_week"] = date_series.dt.dayofweek
        if "day_of_year" in components:
            df[f"{col}_day_of_year"] = date_series.dt.dayofyear

    return df


# --- Main Dispatcher ---

METHOD_HANDLERS: Dict[str, Callable] = {
    "missing_values": _handle_missing_values,
    "outliers": _handle_outliers,
    "standardization": _perform_standardization,
    "categorical_encoding": _encode_categorical,
    "pca": _apply_pca,
    "date_components": _extract_date_components,
}


def apply_preprocessing(
    df: pd.DataFrame, config: Dict[str, Any]
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Applies a sequence of preprocessing methods to a DataFrame."""
    processed_df = df.copy()
    all_scaling_params = {}

    for method in config.get("methods", []):
        method_id = method.get("method_id")
        handler = METHOD_HANDLERS.get(method_id)

        if not handler:
            logger.warning(f"Unknown preprocessing method: {method_id}. Skipping.")
            continue

        params = method.get("parameters", {})

        if method_id == "standardization":
            processed_df, scaling_params = handler(processed_df, params)
            if scaling_params:
                all_scaling_params.update(scaling_params)
        else:
            processed_df = handler(processed_df, params)

    return processed_df, all_scaling_params


def apply_inverse_scaling(
    df: pd.DataFrame, columns: List[str], scaling_params: Dict[str, Any]
) -> pd.DataFrame:
    """Applies inverse scaling to specified columns of a DataFrame."""
    processed_df = df.copy()

    # Normalize the structure of scaling_params if it's nested
    if "standardization" in scaling_params:
        scaling_params = scaling_params["standardization"]

    method = scaling_params.get("method")
    params = scaling_params.get("params", {})
    valid_columns = [col for col in columns if col in df.columns and col in params]

    if not valid_columns or not method:
        logger.warning(
            "Inverse scaling skipped: No valid columns or method specified."
        )
        return processed_df

    if method == "standard":
        for col in valid_columns:
            col_params = params[col]
            mean = col_params.get("mean", 0.0)
            std = col_params.get("std", 1.0)
            processed_df[col] = processed_df[col] * std + mean
    elif method == "minmax":
        for col in valid_columns:
            col_params = params[col]
            min_val, max_val = col_params.get("min", 0.0), col_params.get("max", 1.0)
            processed_df[col] = processed_df[col] * (max_val - min_val) + min_val

    return processed_df