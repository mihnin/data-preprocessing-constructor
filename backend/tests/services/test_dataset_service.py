import pytest
import pandas as pd
import numpy as np

from backend.services.dataset_service import (
    analyze_dataset,
    _analyze_column,
    _recommend_methods,
)


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Provides a standard DataFrame for testing."""
    data = {
        "numeric_col": [1, 2, 3, 4, 5],
        "string_col": ["a", "b", "c", "a", "b"],
        "float_col": [1.1, 2.2, np.nan, 4.4, 5.5],
        "date_str_col": [
            "2021-01-01",
            "2021-01-02",
            "2021-01-03",
            "2021-01-04",
            "2021-01-05",
        ],
        "bool_col": [True, False, True, False, True],
    }
    return pd.DataFrame(data)


@pytest.fixture
def timeseries_dataframe() -> pd.DataFrame:
    """Provides a DataFrame with a clear time series column."""
    date_rng = pd.to_datetime(
        ["2022-01-01", "2022-01-02", "2022-01-03", "2022-01-04", "2022-01-15"]
    )
    data = {"timestamp": date_rng, "value": [10, 12, 15, 11, 16]}
    # Ensure the timestamp column is sorted to be detected as a time series
    return pd.DataFrame(data).sort_values(by="timestamp")


def test_analyze_column_numeric():
    """Tests analysis of a numeric column."""
    series = pd.Series([1, 2, 3, np.nan])
    col_info, _ = _analyze_column(series, "numeric_test")

    assert col_info["type"] == "numeric"
    assert col_info["missing_count"] == 1
    assert col_info["unique_count"] == 3
    assert col_info["mean_value"] == 2.0
    assert col_info["min_value"] == 1.0
    assert col_info["max_value"] == 3.0


def test_analyze_column_categorical():
    """Tests analysis of a categorical column."""
    series = pd.Series(["cat", "dog", "cat", "mouse"])
    col_info, _ = _analyze_column(series, "categorical_test")

    assert col_info["type"] == "categorical"
    assert col_info["missing_count"] == 0
    assert col_info["unique_count"] == 3


def test_analyze_column_datetime_conversion():
    """Tests analysis of a string column that should be converted to datetime."""
    series = pd.Series(["2022-03-01", "2022-03-02", "2022-03-03"])
    col_info, modified_series = _analyze_column(series, "date_str_test")

    assert col_info["type"] == "datetime"
    assert pd.api.types.is_datetime64_dtype(modified_series)


def test_analyze_column_as_timeseries():
    """Tests that a sorted datetime column is identified as a time series."""
    dates = [f"2023-01-{day:02d}" for day in range(1, 12)]
    series = pd.to_datetime(pd.Series(dates))
    col_info, _ = _analyze_column(series, "timeseries_test")

    assert col_info["type"] == "datetime"
    assert col_info["is_time_series"] is True


def test_recommend_methods():
    """Tests the logic for recommending preprocessing methods."""
    # Scenario 1: Missing values and categorical data
    analysis1 = [
        {"type": "numeric", "missing_count": 5, "is_time_series": False},
        {"type": "categorical", "missing_count": 0, "is_time_series": False},
    ]
    recs1 = _recommend_methods(analysis1)
    assert "missing_values" in recs1
    assert "categorical_encoding" in recs1

    # Scenario 2: Many numeric columns, triggering PCA
    analysis2 = [
        {"type": "numeric", "missing_count": 0, "is_time_series": False}
    ] * 6
    recs2 = _recommend_methods(analysis2)
    assert "pca" in recs2
    assert "outliers" in recs2
    assert "standardization" in recs2

    # Scenario 3: Time series data
    analysis3 = [{"type": "datetime", "is_time_series": True, "missing_count": 0}]
    recs3 = _recommend_methods(analysis3)
    assert "time_series_analysis" in recs3
    assert "lagging" in recs3
    assert "rolling_statistics" in recs3


def test_analyze_dataset_structure(sample_dataframe):
    """Tests the overall structure of the returned analysis dictionary."""
    df = sample_dataframe.copy()
    result = analyze_dataset(df)

    assert "row_count" in result
    assert "column_count" in result
    assert "columns" in result
    assert "recommended_methods" in result
    assert result["row_count"] == 5
    assert result["column_count"] == 5
    assert len(result["columns"]) == 5


def test_analyze_dataset_recommendations(sample_dataframe):
    """Tests that correct recommendations are generated for a dataframe."""
    df = sample_dataframe.copy()
    result = analyze_dataset(df)

    # Based on sample_dataframe: has missing float, numeric, and categorical
    assert "missing_values" in result["recommended_methods"]
    assert "standardization" in result["recommended_methods"]
    assert "categorical_encoding" in result["recommended_methods"]
    assert "outliers" in result["recommended_methods"]
    assert "pca" not in result["recommended_methods"]  # Not enough numeric


def test_analyze_dataset_timeseries_detection(timeseries_dataframe):
    """Tests that a time series is correctly identified in a full analysis."""
    df = timeseries_dataframe.copy()
    result = analyze_dataset(df)

    ts_col = next(
        (col for col in result["columns"] if col["name"] == "timestamp"), None
    )

    assert ts_col is not None
    assert ts_col["is_time_series"] is True
    assert "time_series_analysis" in result["recommended_methods"]
    assert "lagging" in result["recommended_methods"]
    assert "rolling_statistics" in result["recommended_methods"]