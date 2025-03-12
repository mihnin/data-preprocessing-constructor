import threading
import asyncio
import time
from typing import Dict, Set, Optional, Callable, Any
import logging

# Глобальный словарь для блокировок файлов
file_locks: Dict[str, threading.Lock] = {}
file_locks_lock = threading.Lock()

# Набор идентификаторов файлов, которые в данный момент обрабатываются
processing_files: Set[str] = set()
processing_files_lock = threading.Lock()

def get_file_lock(file_id: str) -> threading.Lock:
    """
    Получает или создает объект блокировки для указанного идентификатора файла.
    
    Args:
        file_id: Идентификатор файла
    
    Returns:
        threading.Lock: Объект блокировки
    """
    with file_locks_lock:
        if file_id not in file_locks:
            file_locks[file_id] = threading.Lock()
        return file_locks[file_id]

async def with_file_lock(file_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Выполняет функцию с блокировкой для указанного идентификатора файла.
    
    Args:
        file_id: Идентификатор файла
        func: Функция для выполнения
        *args: Аргументы для функции
        **kwargs: Именованные аргументы для функции
    
    Returns:
        Any: Результат выполнения функции
    """
    lock = get_file_lock(file_id)
    
    # Пытаемся получить блокировку с таймаутом
    acquired = False
    try:
        # Неблокирующая попытка получить блокировку
        acquired = lock.acquire(blocking=False)
        if not acquired:
            # Если не удалось получить блокировку сразу, делаем блокирующий вызов
            # в другом потоке, чтобы не блокировать событийный цикл asyncio
            loop = asyncio.get_event_loop()
            acquired = await loop.run_in_executor(None, lambda: lock.acquire(blocking=True, timeout=30))
        
        if not acquired:
            logging.warning(f"Не удалось получить блокировку для файла {file_id} в течение 30 секунд")
            raise TimeoutError(f"Превышено время ожидания доступа к файлу {file_id}")
        
        # Помечаем файл как обрабатываемый
        with processing_files_lock:
            processing_files.add(file_id)
        
        # Выполняем функцию
        return await func(*args, **kwargs)
    
    finally:
        # Снимаем пометку обработки
        with processing_files_lock:
            if file_id in processing_files:
                processing_files.remove(file_id)
        
        # Освобождаем блокировку
        if acquired:
            lock.release()

def is_file_processing(file_id: str) -> bool:
    """
    Проверяет, обрабатывается ли файл в данный момент.
    
    Args:
        file_id: Идентификатор файла
    
    Returns:
        bool: True, если файл обрабатывается
    """
    with processing_files_lock:
        return file_id in processing_files