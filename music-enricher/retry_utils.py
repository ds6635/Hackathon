"""Retry decorator and error handling utilities."""
import time
from functools import wraps
from typing import Any, Callable, Type, Union, Tuple
import random

def retry_with_backoff(
    retries: int = 3,
    backoff_in_seconds: float = 1.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
) -> Callable:
    """Retries the wrapped function with exponential backoff.
    
    Args:
        retries: Number of times to retry before giving up
        backoff_in_seconds: Initial backoff time between retries in seconds
        exceptions: Exception or tuple of exceptions to catch and retry on
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Add jitter to avoid thundering herd
            jitter = lambda: random.uniform(0.8, 1.2)
            
            retry_count = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retry_count += 1
                    if retry_count > retries:
                        raise e
                    
                    # Calculate sleep time with exponential backoff and jitter
                    sleep_time = (backoff_in_seconds * (2 ** (retry_count - 1))) * jitter()
                    time.sleep(sleep_time)
                    
                    # Print retry attempt (helpful for debugging)
                    print(f"\nRetrying {func.__name__} (attempt {retry_count}/{retries})...")
            
        return wrapper
    return decorator