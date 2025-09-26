import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Get the logger instance
logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handles HTTP-specific errors (e.g., 404 Not Found, 403 Forbidden).
    """
    logger.error(f"HTTP error occurred: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles request validation errors from Pydantic models.
    """
    # exc.errors() provides a detailed list of validation errors
    logger.error(f"Validation error: {exc.errors()}", exc_info=True)
    return JSONResponse(
        status_code=422,
        content={"detail": "Data validation error", "errors": exc.errors()},
    )

async def general_exception_handler(request: Request, exc: Exception):
    """
    Handles any other unhandled exceptions, preventing the app from crashing.
    """
    logger.error(f"An unhandled exception occurred: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )