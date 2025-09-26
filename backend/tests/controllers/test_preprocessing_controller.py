import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# This test file uses fixtures defined in backend/tests/conftest.py


@pytest.fixture(scope="module")
def setup_dataset(client: TestClient) -> str:
    """
    Upload a dataset once, providing its ID to all tests in this module.
    This avoids re-uploading the same file for every single test function.
    """
    file_path = Path("test_for_preprocessing.csv")
    with open(file_path, "w") as f:
        f.write("A,B,C\n1,10,cat\n2,20,dog\n,30,cat\n4,40,mouse")

    with open(file_path, "rb") as f:
        response = client.post(
            "/api/datasets/upload", files={"file": ("test.csv", f, "text/csv")}
        )

    file_path.unlink()

    assert response.status_code == 200
    return response.json()["dataset_id"]


def test_get_preprocessing_methods(client: TestClient):
    """Tests that the endpoint for listing methods returns a valid list."""
    response = client.get("/api/preprocessing/methods")
    assert response.status_code == 200
    methods = response.json()
    assert isinstance(methods, list)
    assert len(methods) > 0
    assert "method_id" in methods[0]


def test_preview_preprocessing(client: TestClient, setup_dataset: str):
    """Tests the preview functionality for a preprocessing step."""
    dataset_id = setup_dataset
    config = {
        "dataset_id": dataset_id,
        "methods": [
            {
                "method_id": "missing_values",
                "parameters": {"strategy": "mean", "columns": ["A"]},
            }
        ],
    }
    response = client.post("/api/preprocessing/preview", json=config)
    assert response.status_code == 200
    data = response.json()
    assert "original_sample" in data
    assert "processed_sample" in data
    # Check that the missing value in 'A' was filled in the processed sample
    original_a = [row.get("A") for row in data["original_sample"]]
    processed_a = [row["A"] for row in data["processed_sample"]]
    assert original_a[2] is None
    assert processed_a[2] is not None


def test_execute_and_status_preprocessing(client: TestClient, setup_dataset: str):
    """
    Tests the full execution pipeline: start, check status, and verify
    completion.
    """
    dataset_id = setup_dataset
    config = {
        "dataset_id": dataset_id,
        "methods": [
            {
                "method_id": "missing_values",
                "parameters": {"strategy": "median", "columns": ["A"]},
            },
            {
                "method_id": "standardization",
                "parameters": {"strategy": "minmax", "columns": ["B"]},
            },
        ],
    }

    # 1. Execute preprocessing
    execute_response = client.post("/api/preprocessing/execute", json=config)
    assert execute_response.status_code == 200
    execute_data = execute_response.json()
    assert "result_id" in execute_data
    assert execute_data["status"] == "processing"
    result_id = execute_data["result_id"]

    # 2. Poll for status
    for _ in range(10):  # Poll for up to 10 seconds
        status_response = client.get(f"/api/preprocessing/status/{result_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        if status_data.get("status") == "completed":
            break
        time.sleep(1)
    else:
        pytest.fail("Processing did not complete in time.")

    # 3. Verify metadata
    metadata = status_data.get("metadata", {})
    assert metadata["result_id"] == result_id
    assert "scaling_params" in metadata
    assert "standardization" in metadata["scaling_params"]

    # 4. Verify data preview of the result
    data_response = client.get(f"/api/preprocessing/data/{result_id}")
    assert data_response.status_code == 200
    data_preview = data_response.json()
    assert data_preview["total_count"] == 4
    assert len(data_preview["preview"]) == 4

    # 5. Verify metadata export
    export_response = client.get(
        f"/api/preprocessing/export-metadata/{result_id}"
    )
    assert export_response.status_code == 200
    export_data = export_response.json()
    assert "scaling_params" in export_data
    assert export_data["result_id"] == result_id