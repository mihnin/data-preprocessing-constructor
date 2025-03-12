import logging
import traceback
import functools
from fastapi import HTTPException
from typing import Any, Callable, TypeVar, cast

T = TypeVar('T')

def handle_exceptions(func: Callable[..., T]) -> Callable[..., T]:
    """
    Декоратор для обработки исключений в функциях.
    Логирует ошибки и преобразует их в HTTPException.
    
    Args:
        func: Декорируемая функция
    
    Returns:
        Callable: Функция-обертка
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Пробрасываем HTTPException без изменений
            raise
        except Exception as e:
            # Логируем подробную информацию об ошибке
            logging.error(
                f"Ошибка в функции {func.__name__}: {str(e)}", 
                exc_info=True
            )
            # Получаем стек вызовов
            stack_trace = traceback.format_exc()
            logging.debug(f"Стек вызовов: {stack_trace}")
            
            # Возвращаем более информативную ошибку
            error_message = f"Ошибка: {str(e)}"
            raise HTTPException(status_code=500, detail=error_message)
    
    return cast(Callable[..., T], wrapper)

def log_error(e: Exception, message: str = "Произошла ошибка") -> None:
    """
    Логирует ошибку с подробной информацией.
    
    Args:
        e: Исключение
        message: Дополнительное сообщение
    """
    logging.error(
        f"{message}: {str(e)}", 
        exc_info=True
    )
    stack_trace = traceback.format_exc()
    logging.debug(f"Стек вызовов: {stack_trace}")