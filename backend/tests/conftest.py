import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

# Make the backend directory discoverable for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app, settings


@pytest.fixture(scope="module")
def client() -> TestClient:
    """
    Provides a TestClient instance for making API requests.
    This fixture has a 'module' scope, so the client is created once per
    test module.
    """
    # Ensure test directories exist
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def test_csv_file() -> Path:
    """
    Creates a temporary CSV file for upload testing and cleans it up afterward.
    This fixture has a 'function' scope, creating a new file for each test.
    """
    df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["A", "B", "C"]})

    # Use the test-specific temp directory
    file_path = settings.TEMP_DIR / "test_upload.csv"
    df.to_csv(file_path, index=False)

    yield file_path

    # Cleanup: remove the file after the test is done
    os.remove(file_path)


@pytest.fixture(scope="function")
def test_excel_file() -> Path:
    """
    Creates a temporary Excel (XLSX) file for upload testing and cleans it up
    afterward.
    """
    df = pd.DataFrame(
        {"feature1": [10.5, 20.3, 30.1], "feature2": [100, 200, 300]}
    )

    file_path = settings.TEMP_DIR / "test_upload.xlsx"
    df.to_excel(file_path, index=False, engine="openpyxl")

    yield file_path

    os.remove(file_path)


@pytest.fixture(scope="function")
def test_txt_file() -> Path:
    """
    Creates a temporary unsupported .txt file for testing error handling.
    """
    file_path = settings.TEMP_DIR / "unsupported.txt"
    with open(file_path, "w") as f:
        f.write("this is not a valid file format")

    yield file_path

    os.remove(file_path)