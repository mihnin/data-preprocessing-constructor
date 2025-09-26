import uuid
import json
import logging
import asyncio
from pathlib import Path
from typing import Coroutine

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from services.preprocessing_service import (
    get_preprocessing_methods,
    apply_preprocessing,
)
from utils.file_utils import (
    get_file_path_by_id,
    get_processed_file_path,
)
from utils.validation_utils import load_and_validate_dataframe
from utils.error_utils import handle_exceptions, log_error
from utils.lock_utils import run_with_lock, is_file_processing
from models.schemas import PreprocessingConfig
from config.settings import settings
from utils.json_utils import NumpyJSONEncoder


router = APIRouter()
logger = logging.getLogger(__name__)


def run_async_job(job: Coroutine):
    """
    Synchronous wrapper to run a coroutine in a new asyncio event loop.
    This is necessary for running async functions in FastAPI's BackgroundTasks.
    """
    asyncio.run(job)


async def run_preprocessing_job(
    config_dict: dict, result_id: str, file_path: Path, extension: str
):
    """
    The main async logic for the preprocessing job. This function is executed
    in the background and is wrapped by run_with_lock.
    """
    async def task_to_lock():
        try:
            logger.info(f"Background task starting for result_id: {result_id}")
            df = await load_and_validate_dataframe(file_path, extension)
            processed_df, s_params = apply_preprocessing(df, config_dict)

            result_path = get_processed_file_path(result_id)
            processed_df.to_csv(result_path, index=False)

            metadata = {
                "dataset_id": config_dict.get("dataset_id"),
                "result_id": result_id,
                "row_count": len(processed_df),
                "column_count": len(processed_df.columns),
                "columns": processed_df.columns.tolist(),
                "config": config_dict,
                "scaling_params": s_params or {},
            }
            metadata_path = result_path.parent / f"{result_id}_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, cls=NumpyJSONEncoder)
            logger.info(f"Task finished for result_id: {result_id}")

        except Exception as e:
            logger.error(
                f"Background task failed for result_id={result_id}", exc_info=True
            )
            error_path = get_processed_file_path(result_id).parent / f"{result_id}_error.txt"
            with open(error_path, "w") as f:
                f.write(str(e))

    await run_with_lock(result_id, task_to_lock())


@router.get("/methods", summary="Get available preprocessing methods")
@handle_exceptions
async def get_methods():
    """Retrieve a list of all available data preprocessing methods."""
    return get_preprocessing_methods()


@router.post("/preview", summary="Preview preprocessing results")
@handle_exceptions
async def preview_preprocessing(config: PreprocessingConfig):
    """Apply preprocessing to a sample of data to preview the results."""
    dataset_id = config.dataset_id
    if await is_file_processing(dataset_id):
        raise HTTPException(
            status_code=409, detail="File is currently being processed."
        )

    async def process_preview():
        file_path, extension = None, None
        for ext in ["csv", "xlsx", "xls"]:
            temp_path = get_file_path_by_id(dataset_id, ext)
            if temp_path.exists():
                file_path, extension = temp_path, ext
                break

        if not file_path:
            raise HTTPException(status_code=404, detail="Dataset not found.")

        df = await load_and_validate_dataframe(file_path, extension)
        sample_df = df.head(min(100, len(df)))
        processed_df, _ = apply_preprocessing(sample_df, config.model_dump())

        return {
            "original_sample": json.loads(sample_df.to_json(orient="records")),
            "processed_sample": json.loads(
                processed_df.to_json(orient="records")
            ),
            "original_columns": sample_df.columns.tolist(),
            "processed_columns": processed_df.columns.tolist(),
        }

    return await run_with_lock(dataset_id, process_preview())


@router.post("/execute", summary="Execute full preprocessing")
@handle_exceptions
async def execute_preprocessing(
    config: PreprocessingConfig, background_tasks: BackgroundTasks
):
    """Execute the full preprocessing pipeline on the dataset."""
    dataset_id = config.dataset_id
    if await is_file_processing(dataset_id):
        raise HTTPException(
            status_code=409,
            detail="A processing job for this dataset is already active.",
        )

    result_id = str(uuid.uuid4())

    file_path, extension = None, None
    for ext in ["csv", "xlsx", "xls"]:
        temp_path = get_file_path_by_id(dataset_id, ext)
        if temp_path.exists():
            file_path, extension = temp_path, ext
            break
    if not file_path:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    job_coro = run_preprocessing_job(
        config.model_dump(), result_id, file_path, extension
    )
    background_tasks.add_task(run_async_job, job_coro)
    logger.info(f"Dispatched background job {result_id} for {dataset_id}")

    return {"result_id": result_id, "status": "processing"}


@router.get("/status/{result_id}", summary="Get preprocessing status")
@handle_exceptions
async def get_preprocessing_status(result_id: str):
    """Check the status of a preprocessing task."""
    if await is_file_processing(result_id):
        return {"status": "processing"}

    result_path = get_processed_file_path(result_id)
    error_path = result_path.parent / f"{result_id}_error.txt"

    if error_path.exists():
        with open(error_path, "r") as f:
            return {"status": "error", "message": f.read()}

    if result_path.exists():
        metadata_path = result_path.parent / f"{result_id}_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                return {"status": "completed", "metadata": json.load(f)}
        return {"status": "completed", "metadata": {}}

    return {"status": "pending"}


@router.get("/data/{result_id}", summary="Get processed data preview")
@handle_exceptions
async def get_data_preview(result_id: str, limit: int = 100, offset: int = 0):
    """Retrieve a paginated preview of the processed data."""
    if await is_file_processing(result_id):
        raise HTTPException(
            status_code=409, detail="Data is currently being processed."
        )

    async def load_preview():
        result_path = get_processed_file_path(result_id)
        if not result_path.exists():
            raise HTTPException(status_code=404, detail="Result not found.")

        try:
            with open(result_path, "r", encoding="utf-8") as f:
                total_count = sum(1 for _ in f) - 1

            df = pd.read_csv(
                result_path,
                skiprows=range(1, offset + 1),
                nrows=limit,
                encoding="utf-8",
            )
            df.replace([np.inf, -np.inf], np.nan, inplace=True)

            return {
                "preview": json.loads(df.to_json(orient="records")),
                "total_count": total_count,
            }
        except Exception as e:
            log_error(e, f"Error loading data preview for result_id={result_id}")
            raise HTTPException(
                status_code=500, detail=f"Error loading data: {e}"
            )

    return await run_with_lock(result_id, load_preview())


@router.get("/export-metadata/{result_id}", summary="Export scaling metadata")
@handle_exceptions
async def export_metadata(result_id: str):
    """Export the scaling parameters to a JSON file."""
    if await is_file_processing(result_id):
        raise HTTPException(
            status_code=409, detail="Data is currently being processed."
        )

    async def process_metadata_export():
        metadata_path = (
            get_processed_file_path(result_id).parent
            / f"{result_id}_metadata.json"
        )
        if not metadata_path.exists():
            raise HTTPException(status_code=404, detail="Metadata not found.")

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        scaling_params = metadata.get("scaling_params")
        if not scaling_params:
            raise HTTPException(
                status_code=400, detail="No scaling parameters found."
            )

        export_data = {
            "result_id": result_id,
            "scaling_params": scaling_params,
            "exported_at": "placeholder_time",
        }

        temp_path = settings.TEMP_DIR / f"scaling_metadata_{result_id}.json"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        return FileResponse(
            temp_path,
            filename=f"scaling_metadata_{result_id}.json",
            media_type="application/json",
        )

    return await run_with_lock(result_id, process_metadata_export())