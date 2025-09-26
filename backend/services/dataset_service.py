import pandas as pd
from typing import Dict, Any, List, Tuple


def _analyze_column(
    col_series: pd.Series, col_name: str
) -> Tuple[Dict[str, Any], pd.Series]:
    """
    Analyzes a single column (Pandas Series) of a DataFrame.

    Args:
        col_series: The Pandas Series representing the column.
        col_name: The name of the column.

    Returns:
        A tuple containing a dictionary with analysis information and the
        potentially modified series (e.g., after date conversion).
    """
    is_numeric = pd.api.types.is_numeric_dtype(col_series)
    is_datetime = pd.api.types.is_datetime64_dtype(col_series)
    modified_series = col_series

    # Attempt to convert object columns to datetime if possible
    if not is_datetime and not is_numeric:
        try:
            # Using errors='raise' is faster for successful conversions.
            # 'mixed' format allows parsing of different datetime formats.
            converted_dates = pd.to_datetime(col_series, errors='raise', format='mixed')
            is_datetime = True
            modified_series = converted_dates
        except (ValueError, TypeError):
            # Not a datetime column
            pass

    col_type = "numeric" if is_numeric else "datetime" if is_datetime else "categorical"

    col_info = {
        "name": col_name,
        "type": col_type,
        "missing_count": int(col_series.isna().sum()),
        "unique_count": int(col_series.nunique()),
        "is_time_series": False,
        "is_target": False,
    }

    if is_numeric:
        col_info.update({
            "min_value": float(col_series.min()) if col_series.notna().any() else None,
            "max_value": float(col_series.max()) if col_series.notna().any() else None,
            "mean_value": float(col_series.mean()) if col_series.notna().any() else None,
        })

    # Check for time series characteristics
    if is_datetime:
        # A column is considered a time series if it's sorted and has
        # minimal duplicates
        if col_series.is_monotonic_increasing or col_series.is_monotonic_decreasing:
            # High uniqueness suggests it's an index, not just a few
            # repeating dates
            if col_series.nunique() > len(col_series) * 0.8:
                col_info["is_time_series"] = True

    return col_info, modified_series


def _recommend_methods(columns_analysis: List[Dict[str, Any]]) -> List[str]:
    """
    Recommends preprocessing methods based on the analysis of all columns.

    Args:
        columns_analysis: A list of analysis dictionaries for each column.

    Returns:
        A list of recommended method names.
    """
    recommendations = []
    has_missing = any(col["missing_count"] > 0 for col in columns_analysis)
    numeric_cols = [
        col for col in columns_analysis if col["type"] == "numeric"
    ]
    has_categorical = any(
        col["type"] == "categorical" for col in columns_analysis
    )
    has_time_series = any(col["is_time_series"] for col in columns_analysis)

    if has_missing:
        recommendations.append("missing_values")
    if numeric_cols:
        recommendations.append("outliers")
        recommendations.append("standardization")
    if len(numeric_cols) > 5:
        recommendations.append("pca")
    if has_categorical:
        recommendations.append("categorical_encoding")
    if has_time_series:
        recommendations.append("time_series_analysis")
        recommendations.append("lagging")
        recommendations.append("rolling_statistics")

    return recommendations


def analyze_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Performs a comprehensive analysis of the uploaded dataset.

    This function inspects each column to determine its type, statistical
    properties, and potential issues like missing values. It also provides
    recommendations for suitable preprocessing steps.

    Args:
        df: The input DataFrame to be analyzed.

    Returns:
        A dictionary containing the analysis results.
    """
    analysis_results = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": [],
        "recommended_methods": [],
        "target_column": None,
    }

    # Analyze each column
    for col_name in df.columns:
        col_info, modified_series = _analyze_column(df[col_name], col_name)
        analysis_results["columns"].append(col_info)
        # Note: This modifies the DataFrame in place for performance.
        df[col_name] = modified_series

    # Generate recommendations based on the full analysis
    analysis_results["recommended_methods"] = _recommend_methods(
        analysis_results["columns"]
    )

    return analysis_results