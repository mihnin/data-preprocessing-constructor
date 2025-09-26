import sys
from pathlib import Path

# Add the project root to the Python path before any other imports
# to ensure that local modules can be found.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.logging_config import setup_logging
from config.settings import AppSettings
from controllers.datasets import router as datasets_router
from controllers.preprocessing import router as preprocessing_router
from utils.exception_handlers import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from utils.json_utils import NumpyJSONEncoder


# --- Setup ---
logger = setup_logging()
settings = AppSettings()


# --- Lifespan Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events.
    """
    # Startup logic
    logger.info("Application starting up...")
    try:
        for directory in [
            settings.UPLOAD_DIR,
            settings.PROCESSED_DIR,
            settings.TEMP_DIR,
        ]:
            Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info("Application startup complete. Data directories are ready.")
    except Exception as e:
        logger.error(f"Error during startup directory creation: {e}", exc_info=True)

    yield

    # Shutdown logic
    logger.info("Application shutting down...")
    try:
        temp_dir = Path(settings.TEMP_DIR)
        if temp_dir.exists():
            for file in temp_dir.iterdir():
                try:
                    file.unlink()
                    logger.info(f"Removed temporary file: {file}")
                except OSError as e:
                    logger.warning(f"Failed to remove temp file {file}: {e}")
        logger.info("Temporary files cleaned up successfully.")
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {e}", exc_info=True)


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    json_encoder=NumpyJSONEncoder,
    lifespan=lifespan,
)


# --- Middleware ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Measures the processing time for each request."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Exception Handlers ---
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# --- API Routers ---
app.include_router(datasets_router, prefix="/api/datasets", tags=["datasets"])
app.include_router(
    preprocessing_router, prefix="/api/preprocessing", tags=["preprocessing"]
)


# This space is intentionally left blank.
# The old on_event handlers have been replaced by the lifespan manager.


# --- Root and Health Check ---
@app.get("/", tags=["Root"])
async def read_root():
    """Welcome endpoint for the API."""
    return {"message": "Welcome to the Data Preprocessing Constructor API"}


@app.get("/health", tags=["Health Check"])
async def health_check():
    """Health check endpoint for monitoring service availability."""
    return {"status": "healthy", "timestamp": time.time()}


# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.RELOAD,
    )