import uuid
import json
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from ..utils.validation_utils import load_and_validate_dataframe
from ..utils.file_utils import save_uploaded_file, with_file_lock, get_processed_file_path, is_file_processing, get_file_path_by_id
from ..utils.analysis import analyze_dataset
from ..utils.json_utils import NumpyEncoder, convert_numpy_types
from ..utils.logging_utils import log_error
from ..config import TEMP_DIR

router = APIRouter(prefix="/datasets", tags=["datasets"])

@router.post("/upload")
@handle_exceptions
async def upload_dataset(
    file: UploadFile = File(...),
    encoding: str = Form("utf-8"),
    has_header: bool = Form(True),
    delimiter: str = Form(","),
    background_tasks: BackgroundTasks = None
):
    """
    Загрузка набора данных в формате CSV или Excel.
    
    Поддерживаемые форматы: CSV, XLSX, XLS.
    Максимальный размер файла: 10 МБ.
    Максимальное количество строк: 1 000 000.
    """
    # Проверка расширения файла
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Имя файла отсутствует")
    
    extension = filename.split(".")[-1].lower()
    
    if extension not in ["csv", "xlsx", "xls"]:
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы CSV и Excel")
    
    # Создаем уникальный ID для набора данных
    dataset_id = str(uuid.uuid4())
    
    # Определяем функцию для выполнения в блокирующем контексте
    async def process_upload():
        try:
            # Сохраняем файл
            file_path = await save_uploaded_file(file, dataset_id, extension)
            
            # Загружаем и валидируем данные
            df = await load_and_validate_dataframe(file_path, extension, encoding)
            
            # Анализируем набор данных
            analysis = analyze_dataset(df)
            analysis["dataset_id"] = dataset_id
            
            # Сохраняем метаданные
            metadata_path = file_path.parent / f"{dataset_id}_metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(analysis, f, cls=NumpyEncoder, ensure_ascii=False)
            
            # Применяем функцию convert_numpy_types к результату перед возвратом
            return convert_numpy_types(analysis)
        
        except Exception as e:
            log_error(e, "Ошибка при обработке загруженного файла")
            raise
    
    # Выполняем обработку с блокировкой
    return await with_file_lock(dataset_id, process_upload)

@router.get("/export/{result_id}")
@handle_exceptions
async def export_dataset(result_id: str, format: str = "csv"):
    """
    Экспорт обработанных данных.
    
    Поддерживаемые форматы: csv, excel.
    """
    async def process_export():
        try:
            # Получаем путь к файлу результатов
            result_path = get_processed_file_path(result_id)
            
            if not result_path.exists():
                raise HTTPException(status_code=404, detail="Результаты не найдены")
            
            # Загружаем данные
            df = pd.read_csv(result_path, encoding='utf-8')
            
            if format.lower() == "excel":
                # Создаем временный файл Excel
                excel_path = TEMP_DIR / f"{result_id}.xlsx"
                df.to_excel(excel_path, index=False, engine='openpyxl')
                
                return FileResponse(
                    excel_path, 
                    filename=f"processed_data_{result_id}.xlsx",
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:  # По умолчанию CSV
                return FileResponse(
                    result_path, 
                    filename=f"processed_data_{result_id}.csv",
                    media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="processed_data_{result_id}.csv"',
                             "Content-Type": "text/csv; charset=utf-8"}
                )
        
        except HTTPException:
            raise
        except Exception as e:
            log_error(e, "Ошибка экспорта данных")
            raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
    
    return await with_file_lock(result_id, process_export)

@router.post("/{dataset_id}/set-target")
@handle_exceptions
async def set_target_column(dataset_id: str, data: dict):
    """
    Установка целевой переменной для набора данных.
    """
    # Проверяем, обрабатывается ли файл в данный момент
    if is_file_processing(dataset_id):
        return {"status": "processing", "message": "Файл в данный момент обрабатывается"}
    
    target_column = data.get("target_column")
    if not target_column:
        raise HTTPException(status_code=400, detail="Целевая переменная не указана")
    
    async def update_metadata():
        # Ищем метаданные
        for extension in ["csv", "xlsx", "xls"]:
            file_path = get_file_path_by_id(dataset_id, extension)
            metadata_path = file_path.parent / f"{dataset_id}_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                
                # Обновляем информацию о целевой переменной
                metadata["target_column"] = target_column
                
                # Обновляем статус целевой переменной в колонках
                for col in metadata["columns"]:
                    col["is_target"] = col["name"] == target_column
                
                # Сохраняем обновленные метаданные
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, cls=NumpyEncoder)
                
                return convert_numpy_types(metadata)
        
        raise HTTPException(status_code=404, detail="Набор данных не найден")
    
    return await with_file_lock(dataset_id, update_metadata)
