import logging
import traceback
import functools
from typing import Any, Callable, TypeVar, cast
from fastapi import HTTPException

logger = logging.getLogger(__name__)
T = TypeVar('T')

def log_error(e: Exception, func_name: str, message: str = "An unexpected error occurred"):
    """
    Logs an exception with detailed information, including the function name and stack trace.

    Args:
        e: The exception that was caught.
        func_name: The name of the function where the error occurred.
        message: A custom message to prepend to the log.
    """
    error_message = f"{message} in function '{func_name}': {e}"
    logger.error(error_message, exc_info=True)
    stack_trace = traceback.format_exc()
    logger.debug(f"Stack trace:\n{stack_trace}")

def handle_exceptions(func: Callable[..., T]) -> Callable[..., T]:
    """
    A decorator to catch and handle exceptions in async functions.

    It logs any exceptions and re-raises them as HTTPExceptions to be handled
    by the global exception handlers. This is useful for service-layer functions
    or any part of the application that doesn't directly interact with the FastAPI
    request/response cycle but still needs robust error handling.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-throw HTTPExceptions without modification
            raise
        except Exception as e:
            # Log the detailed error
            log_error(e, func.__name__)
            # Raise a generic HTTPException
            raise HTTPException(
                status_code=500,
                detail=f"An internal error occurred in {func.__name__}."
            )
    
    return cast(Callable[..., T], wrapper)