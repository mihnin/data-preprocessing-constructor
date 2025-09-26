import uuid
import json
import logging
import pandas as pd

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from services.dataset_service import analyze_dataset
from services.preprocessing_service import apply_inverse_scaling
from utils.file_utils import (
    save_uploaded_file,
    get_file_path_by_id,
    get_processed_file_path,
)
from utils.validation_utils import load_and_validate_dataframe
from utils.error_utils import handle_exceptions
from utils.lock_utils import run_with_lock, is_file_processing
from utils.json_utils import NumpyJSONEncoder
from config.settings import settings


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", summary="Upload a new dataset")
@handle_exceptions
async def upload_dataset(file: UploadFile = File(...)):
    """Upload a dataset in CSV or Excel format."""
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is missing.")

    extension = filename.split(".")[-1].lower()
    if extension not in ["csv", "xlsx", "xls"]:
        raise HTTPException(
            status_code=400, detail="Only CSV and Excel files are supported."
        )

    dataset_id = str(uuid.uuid4())

    async def process_upload():
        file_path = await save_uploaded_file(file, dataset_id, extension)
        df = await load_and_validate_dataframe(file_path, extension)
        analysis = analyze_dataset(df)
        analysis["dataset_id"] = dataset_id

        metadata_path = settings.UPLOAD_DIR / f"{dataset_id}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(analysis, f, cls=NumpyJSONEncoder)
        return analysis

    return await run_with_lock(dataset_id, process_upload())


@router.get("/{dataset_id}", summary="Get dataset information")
@handle_exceptions
async def get_dataset_info(dataset_id: str):
    """Retrieve information for a previously uploaded dataset."""
    if await is_file_processing(dataset_id):
        return {
            "status": "processing",
            "message": "The file is currently being processed.",
        }

    async def load_metadata():
        metadata_path = settings.UPLOAD_DIR / f"{dataset_id}_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail="Dataset not found.")

    return await run_with_lock(dataset_id, load_metadata())


@router.post("/{dataset_id}/set-target", summary="Set the target variable")
@handle_exceptions
async def set_target_column(dataset_id: str, data: dict):
    """Define the target variable for the dataset."""
    if await is_file_processing(dataset_id):
        return {
            "status": "processing",
            "message": "The file is currently being processed.",
        }

    target_column = data.get("target_column")
    if not target_column:
        raise HTTPException(
            status_code=400, detail="Target column was not specified."
        )

    async def update_metadata():
        metadata_path = settings.UPLOAD_DIR / f"{dataset_id}_metadata.json"
        if not metadata_path.exists():
            raise HTTPException(status_code=404, detail="Dataset metadata not found.")

        with open(metadata_path, "r+") as f:
            metadata = json.load(f)
            metadata["target_column"] = target_column
            for col in metadata.get("columns", []):
                col["is_target"] = col.get("name") == target_column

            f.seek(0)
            json.dump(metadata, f, cls=NumpyJSONEncoder)
            f.truncate()
        return metadata

    return await run_with_lock(dataset_id, update_metadata())


@router.get("/export/{result_id}", summary="Export processed data")
@handle_exceptions
async def export_dataset(result_id: str, file_format: str = "csv"):
    """Export the processed data in either CSV or Excel format."""
    if await is_file_processing(result_id):
        raise HTTPException(
            status_code=409,
            detail="Result file is currently being generated or modified.",
        )

    async def do_export():
        result_path = get_processed_file_path(result_id)
        if not result_path.exists():
            raise HTTPException(status_code=404, detail="Result not found.")

        if file_format.lower() == "excel":
            df = pd.read_csv(result_path, encoding="utf-8")
            excel_path = settings.TEMP_DIR / f"{result_id}.xlsx"
            df.to_excel(excel_path, index=False, sheet_name="Results")
            return FileResponse(
                excel_path,
                filename=f"processed_data_{result_id}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            return FileResponse(
                result_path,
                filename=f"processed_data_{result_id}.csv",
                media_type="text/csv",
            )

    return await run_with_lock(result_id, do_export())


@router.post(
    "/{dataset_id}/apply-inverse-scaling", summary="Apply inverse scaling"
)
@handle_exceptions
async def apply_inverse_scaling_to_dataset(dataset_id: str, data: dict):
    """Apply inverse scaling to specified columns of a dataset."""
    if await is_file_processing(dataset_id):
        return {
            "status": "processing",
            "message": "The file is currently being processed.",
        }

    columns = data.get("columns", [])
    scaling_params = data.get("scaling_params", {})
    if not columns or not scaling_params:
        raise HTTPException(
            status_code=400, detail="Columns and scaling_params are required."
        )

    async def process_inverse_scaling():
        file_path, extension = None, None
        for ext in ["csv", "xlsx", "xls"]:
            temp_path = get_file_path_by_id(dataset_id, ext)
            if temp_path.exists():
                file_path, extension = temp_path, ext
                break

        if not file_path:
            raise HTTPException(status_code=404, detail="Dataset not found.")

        df = await load_and_validate_dataframe(file_path, extension)
        result_id = str(uuid.uuid4())
        processed_df = apply_inverse_scaling(df, columns, scaling_params)

        result_path = get_processed_file_path(result_id)
        processed_df.to_csv(result_path, index=False)

        metadata = {
            "dataset_id": dataset_id,
            "result_id": result_id,
            "row_count": len(processed_df),
            "column_count": len(processed_df.columns),
            "columns": processed_df.columns.tolist(),
            "inverse_scaling_applied": {
                "columns": columns,
                "scaling_params": scaling_params,
            },
        }
        metadata_path = result_path.parent / f"{result_id}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, cls=NumpyJSONEncoder)

        return {
            "result_id": result_id,
            "status": "completed",
            "metadata": metadata,
        }

    return await run_with_lock(dataset_id, process_inverse_scaling())