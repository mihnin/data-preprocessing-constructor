import shutil
import logging
from pathlib import Path
from fastapi import UploadFile, HTTPException

from config.settings import settings

logger = logging.getLogger(__name__)

async def save_uploaded_file(file: UploadFile, file_id: str, extension: str) -> Path:
    """
    Saves an uploaded file securely to the designated uploads directory.

    The file is first saved to a temporary location and then moved to the final
    destination to prevent partial file writes.

    Args:
        file: The uploaded file object from FastAPI.
        file_id: A unique identifier for the file.
        extension: The file's extension.

    Returns:
        The path to the saved file.

    Raises:
        HTTPException: If the file cannot be saved.
    """
    file_path = settings.UPLOAD_DIR / f"{file_id}.{extension}"
    temp_path = settings.TEMP_DIR / f"temp_{file_id}.{extension}"

    try:
        # Save the file to a temporary location first
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Move the file to its final destination
        shutil.move(temp_path, file_path)
        
        logger.info(f"Successfully saved uploaded file to {file_path}")
        return file_path
    
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}", exc_info=True)
        # Clean up any partial files
        if file_path.exists():
            file_path.unlink()
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

def get_file_path_by_id(file_id: str, extension: str) -> Path:
    """
    Constructs the path to an original uploaded file using its ID and extension.

    Args:
        file_id: The unique identifier of the file.
        extension: The file's extension.

    Returns:
        The full path to the file in the uploads directory.
    """
    return settings.UPLOAD_DIR / f"{file_id}.{extension}"

def get_processed_file_path(result_id: str) -> Path:
    """
    Constructs the path to a processed data file using its result ID.

    Args:
        result_id: The unique identifier of the processing result.

    Returns:
        The full path to the processed CSV file.
    """
    return settings.PROCESSED_DIR / f"{result_id}.csv"