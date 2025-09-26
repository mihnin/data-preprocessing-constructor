import pandas as pd
from fastapi import HTTPException
from pathlib import Path
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

def validate_dataframe(df: pd.DataFrame, max_rows: int = 1_000_000) -> Tuple[bool, Optional[str]]:
    """
    Validates a DataFrame against a set of predefined rules.

    Args:
        df: The pandas DataFrame to validate.
        max_rows: The maximum number of allowed rows.

    Returns:
        A tuple containing a boolean indicating validity and an optional error message.
    """
    if df.empty:
        return False, "The uploaded file is empty or could not be parsed correctly."
    if len(df) > max_rows:
        return False, f"The file exceeds the maximum row limit of {max_rows}."
    if len(df.columns) < 1:
        return False, "The file must contain at least one column."
    if df.columns.duplicated().any():
        return False, "Duplicate column names were found in the file."
    if df.isna().all(axis=1).any():
        return False, "The file contains rows with all missing values."

    return True, None

async def load_and_validate_dataframe(file_path: Path, extension: str) -> pd.DataFrame:
    """
    Loads a DataFrame from a file and validates its structure and content.

    Args:
        file_path: The path to the file.
        extension: The file's extension (csv, xlsx, etc.).

    Returns:
        A validated pandas DataFrame.

    Raises:
        HTTPException: If the file is invalid or cannot be processed.
    """
    try:
        if extension.lower() == "csv":
            # Use sep=None to let pandas auto-detect the separator
            df = pd.read_csv(file_path, sep=None, engine='python', encoding_errors='replace')
        elif extension.lower() in ["xlsx", "xls"]:
            df = pd.read_excel(file_path, engine='openpyxl')
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file extension: {extension}")

        is_valid, error_message = validate_dataframe(df)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        return df

    except HTTPException:
        raise # Re-raise HTTPException to preserve status code and detail
    except Exception as e:
        logger.error(f"Failed to load or validate the file {file_path}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while processing the file: {e}"
        )