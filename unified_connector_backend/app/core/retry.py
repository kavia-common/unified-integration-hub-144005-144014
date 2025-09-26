# PUBLIC_INTERFACE
"""
Simple retry/backoff helpers for vendor API calls.
"""
from __future__ import annotations

import time
from typing import Callable, TypeVar, Iterable

T = TypeVar("T")


# PUBLIC_INTERFACE
def retry_with_backoff(fn: Callable[[], T], attempts: int = 3, base_sleep: float = 0.5, retry_on: Iterable[type[Exception]] = (Exception,)) -> T:
    """Run fn with basic exponential backoff."""
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except tuple(retry_on) as e:
            last_err = e
            sleep_for = base_sleep * (2 ** i)
            time.sleep(sleep_for)
    assert last_err is not None
    raise last_err
