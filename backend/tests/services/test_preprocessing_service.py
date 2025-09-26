import pytest
import pandas as pd
import numpy as np

from backend.services.preprocessing_service import (
    get_preprocessing_methods,
    apply_preprocessing,
    apply_inverse_scaling,
    _handle_missing_values,
    _perform_standardization,
    _encode_categorical,
    _apply_pca,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """A versatile DataFrame for testing various preprocessing steps."""
    data = {
        "A": [1, 2, np.nan, 4, 5],
        "B": [10.0, 20.0, 30.0, 40.0, 50.0],
        "C": ["cat", "dog", "cat", "mouse", "dog"],
        "D": [100, 200, 300, 400, 1000],  # Includes an outlier
    }
    return pd.DataFrame(data)


def test_get_preprocessing_methods():
    """Tests if the method list is returned correctly and has the right structure."""
    methods = get_preprocessing_methods()
    assert isinstance(methods, list)
    assert len(methods) > 0
    assert any(m["method_id"] == "missing_values" for m in methods)
    assert "method_id" in methods[0]
    assert "name" in methods[0]
    assert "parameters" in methods[0]


# --- Test Individual Handlers ---


def test_handle_missing_values_mean(sample_df):
    """Tests filling missing values with the mean."""
    df = sample_df.copy()
    params = {"strategy": "mean", "columns": ["A"]}
    processed_df = _handle_missing_values(df, params)
    assert processed_df["A"].isna().sum() == 0
    # The mean of [1, 2, 4, 5] is 3.0. The NaN value should be replaced by it.
    assert processed_df.loc[2, "A"] == 3.0


def test_perform_standardization_standard(sample_df):
    """Tests standard scaling (z-score)."""
    df = sample_df.copy()
    params = {"strategy": "standard", "columns": ["B"]}
    processed_df, scaling_params = _perform_standardization(df, params)
    # Mean should be close to 0 and population std dev close to 1
    assert np.isclose(processed_df["B"].mean(), 0)
    assert np.isclose(processed_df["B"].std(ddof=0), 1)
    assert "standardization" in scaling_params
    assert "mean" in scaling_params["standardization"]["params"]["B"]


def test_perform_standardization_minmax(sample_df):
    """Tests min-max scaling."""
    df = sample_df.copy()
    params = {"strategy": "minmax", "columns": ["B"]}
    processed_df, scaling_params = _perform_standardization(df, params)
    # Values should be between 0 and 1
    assert processed_df["B"].min() >= 0
    assert processed_df["B"].max() <= 1
    assert "standardization" in scaling_params
    assert "min" in scaling_params["standardization"]["params"]["B"]


def test_encode_categorical_onehot(sample_df):
    """Tests one-hot encoding for categorical variables."""
    df = sample_df.copy()
    params = {"strategy": "onehot", "columns": ["C"]}
    processed_df = _encode_categorical(df, params)
    # Original column 'C' should be removed
    assert "C" not in processed_df.columns
    # New one-hot encoded columns should exist
    assert "C_cat" in processed_df.columns
    assert "C_dog" in processed_df.columns
    assert "C_mouse" in processed_df.columns
    # Check if the sum of new columns is correct (should be 1 for each row)
    assert processed_df[["C_cat", "C_dog", "C_mouse"]].sum(axis=1).eq(1).all()


def test_apply_pca(sample_df):
    """Tests PCA for dimensionality reduction."""
    df = sample_df.copy()
    # PCA requires no NaNs
    df.dropna(inplace=True)
    params = {"n_components": 2, "columns": ["A", "B", "D"]}
    processed_df = _apply_pca(df, params)
    # Original columns should be gone
    assert "A" not in processed_df.columns
    assert "B" not in processed_df.columns
    assert "D" not in processed_df.columns
    # New PCA components should be present
    assert "PCA_1" in processed_df.columns
    assert "PCA_2" in processed_df.columns


# --- Test Main Dispatcher ---


def test_apply_preprocessing_pipeline(sample_df):
    """Tests applying a full pipeline of preprocessing steps."""
    df = sample_df.copy()
    config = {
        "methods": [
            {
                "method_id": "missing_values",
                "parameters": {"strategy": "mean", "columns": ["A"]},
            },
            {
                "method_id": "standardization",
                "parameters": {"strategy": "minmax", "columns": ["B"]},
            },
            {
                "method_id": "categorical_encoding",
                "parameters": {"strategy": "onehot", "columns": ["C"]},
            },
        ]
    }
    processed_df, scaling_params = apply_preprocessing(df, config)

    # Check results of each step
    assert processed_df["A"].isna().sum() == 0
    assert processed_df["B"].min() >= 0 and processed_df["B"].max() <= 1
    assert "C" not in processed_df.columns and "C_cat" in processed_df.columns
    assert "standardization" in scaling_params


# --- Test Inverse Scaling ---


def test_apply_inverse_scaling_standard():
    """Tests if inverse scaling correctly reverts standard scaling."""
    original_series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    # Manually scale it
    mean, std = original_series.mean(), original_series.std()
    scaled_series = (original_series - mean) / std

    scaled_df = pd.DataFrame({"B": scaled_series})
    scaling_params = {
        "standardization": {
            "method": "standard",
            "columns": ["B"],
            "params": {"B": {"mean": mean, "std": std}},
        }
    }

    inversed_df = apply_inverse_scaling(scaled_df, ["B"], scaling_params)

    # The inversed series should be very close to the original
    assert np.allclose(inversed_df["B"], original_series)


def test_apply_inverse_scaling_minmax():
    """Tests if inverse scaling correctly reverts min-max scaling."""
    original_series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    # Manually scale it
    min_val, max_val = original_series.min(), original_series.max()
    scaled_series = (original_series - min_val) / (max_val - min_val)

    scaled_df = pd.DataFrame({"B": scaled_series})
    scaling_params = {
        "standardization": {
            "method": "minmax",
            "columns": ["B"],
            "params": {"B": {"min": min_val, "max": max_val}},
        }
    }

    inversed_df = apply_inverse_scaling(scaled_df, ["B"], scaling_params)

    # The inversed series should be very close to the original
    assert np.allclose(inversed_df["B"], original_series)