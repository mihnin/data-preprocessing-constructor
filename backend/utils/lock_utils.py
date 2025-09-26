import asyncio
from typing import Dict, Coroutine, Any
import logging

logger = logging.getLogger(__name__)

# Global dictionary to store asyncio.Lock instances for each file_id
_locks: Dict[str, asyncio.Lock] = {}
# A lock to manage access to the global _locks dictionary itself, ensuring it's safely accessed
_management_lock = asyncio.Lock()

async def _get_or_create_lock(file_id: str) -> asyncio.Lock:
    """
    Atomically retrieves an existing asyncio.Lock or creates a new one for a given file_id.
    This ensures that each file_id maps to a single lock instance.
    """
    async with _management_lock:
        if file_id not in _locks:
            _locks[file_id] = asyncio.Lock()
        return _locks[file_id]

async def run_with_lock(file_id: str, coro: Coroutine) -> Any:
    """
    Executes a coroutine while holding a file-specific lock.

    This function prevents race conditions by ensuring that only one coroutine
    can operate on a given file_id at a time.

    Args:
        file_id: The identifier for the resource to lock (e.g., a dataset ID).
        coro: The coroutine to execute once the lock is acquired.

    Returns:
        The result of the executed coroutine.

    Raises:
        TimeoutError: If the lock cannot be acquired within 30 seconds.
    """
    lock = await _get_or_create_lock(file_id)
    logger.debug(f"Attempting to acquire lock for file_id: {file_id}")
    
    try:
        # wait_for will raise TimeoutError if the lock isn't acquired in time
        await asyncio.wait_for(lock.acquire(), timeout=30.0)
        logger.debug(f"Lock acquired for file_id: {file_id}")
        # Execute the provided coroutine now that we have the lock
        return await coro
    except asyncio.TimeoutError:
        logger.warning(f"Could not acquire lock for {file_id} within 30 seconds.")
        # Re-raise as a standard TimeoutError which can be caught by exception handlers
        raise TimeoutError(f"Timeout occurred while waiting to access file: {file_id}")
    finally:
        if lock.locked():
            lock.release()
            logger.debug(f"Lock released for file_id: {file_id}")

async def is_file_processing(file_id: str) -> bool:
    """
    Asynchronously checks if a file is currently locked for processing.

    This is useful for status endpoints to quickly check if an operation
    on a file is already in progress.

    Args:
        file_id: The identifier of the file.

    Returns:
        True if the file is currently locked, False otherwise.
    """
    async with _management_lock:
        lock = _locks.get(file_id)

    return lock.locked() if lock else False