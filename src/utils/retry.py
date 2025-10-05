"""Retry decorator for handling transient failures

Implements exponential backoff for API calls and network operations.
"""

import asyncio
import functools
from typing import Any, Callable, TypeVar

from src.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def async_retry(
    max_attempts: int = 3, backoff_factor: float = 2.0, exceptions: tuple = (Exception,)
):
    """Decorator to retry async functions with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries (2^attempt * backoff_factor)
        exceptions: Tuple of exception types to catch and retry

    Usage:
        @async_retry(max_attempts=3, backoff_factor=2.0)
        async def unreliable_api_call():
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = (2**attempt) * backoff_factor
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )

            # Re-raise the last exception if all attempts failed
            raise last_exception

        return wrapper

    return decorator
