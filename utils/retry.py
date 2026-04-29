import time
from typing import Callable, TypeVar

T = TypeVar('T')

def retry(fn: Callable[[], T], attempts: int = 3, delay: float = 1.0) -> T:
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last = e
            if i < attempts - 1:
                time.sleep(delay)
    raise last  # type: ignore[misc]
