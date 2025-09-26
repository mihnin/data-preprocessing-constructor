from pathlib import Path
from fastapi.testclient import TestClient

# This test file uses fixtures defined in backend/tests/conftest.py


def test_read_root(client: TestClient):
    """Tests the root endpoint to ensure it returns a welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to the Data Preprocessing Constructor API"
    }


def test_health_check(client: TestClient):
    """Tests the health check endpoint for a healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_upload_csv_dataset(client: TestClient, test_csv_file: Path):
    """Tests successful upload and analysis of a CSV file."""
    with open(test_csv_file, "rb") as f:
        response = client.post(
            "/api/datasets/upload", files={"file": ("test.csv", f, "text/csv")}
        )

    assert response.status_code == 200
    data = response.json()
    assert "dataset_id" in data
    assert data["row_count"] == 3
    assert data["column_count"] == 2
    assert len(data["columns"]) == 2
    assert data["columns"][0]["name"] == "col1"
    assert data["columns"][0]["type"] == "numeric"


def test_upload_excel_dataset(client: TestClient, test_excel_file: Path):
    """Tests successful upload and analysis of an Excel file."""
    with open(test_excel_file, "rb") as f:
        response = client.post(
            "/api/datasets/upload",
            files={
                "file": (
                    "test.xlsx",
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "dataset_id" in data
    assert data["row_count"] == 3
    assert data["column_count"] == 2
    assert data["columns"][0]["type"] == "numeric"


def test_upload_unsupported_file(client: TestClient, test_txt_file: Path):
    """Tests that uploading an unsupported file type returns a 400 error."""
    with open(test_txt_file, "rb") as f:
        response = client.post(
            "/api/datasets/upload",
            files={"file": ("unsupported.txt", f, "text/plain")},
        )

    assert response.status_code == 400
    assert "Only CSV and Excel files are supported" in response.json()["detail"]


def test_get_dataset_info(client: TestClient, test_csv_file: Path):
    """Tests retrieving information for a specific dataset."""
    # First, upload a file to get a valid dataset_id
    with open(test_csv_file, "rb") as f:
        upload_response = client.post(
            "/api/datasets/upload", files={"file": ("test.csv", f, "text/csv")}
        )
    dataset_id = upload_response.json()["dataset_id"]

    # Now, get the info
    info_response = client.get(f"/api/datasets/{dataset_id}")
    assert info_response.status_code == 200
    data = info_response.json()
    assert data["dataset_id"] == dataset_id
    assert data["row_count"] == 3


def test_get_nonexistent_dataset_info(client: TestClient):
    """Tests a 404 error for a non-existent dataset_id."""
    non_existent_id = "a-fake-id-that-does-not-exist"
    response = client.get(f"/api/datasets/{non_existent_id}")
    assert response.status_code == 404


def test_set_target_column(client: TestClient, test_csv_file: Path):
    """Tests setting the target column for a dataset."""
    # Upload file
    with open(test_csv_file, "rb") as f:
        upload_response = client.post(
            "/api/datasets/upload", files={"file": ("test.csv", f, "text/csv")}
        )
    dataset_id = upload_response.json()["dataset_id"]

    # Set 'col2' as the target
    target_data = {"target_column": "col2"}
    set_target_response = client.post(
        f"/api/datasets/{dataset_id}/set-target", json=target_data
    )

    assert set_target_response.status_code == 200
    data = set_target_response.json()
    assert data["target_column"] == "col2"

    # Verify the column 'col2' is marked as the target
    target_col_info = next(
        col for col in data["columns"] if col["name"] == "col2"
    )
    assert target_col_info["is_target"] is True

    # Verify other columns are not marked as the target
    other_col_info = next(
        col for col in data["columns"] if col["name"] == "col1"
    )
    assert other_col_info["is_target"] is False