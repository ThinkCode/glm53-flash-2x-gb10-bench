# python / glm-5.3-flash-exl3

- decode 28.2 tok/s
- TTFT 0.39s
- wall 36.7s
- 1024 tokens generated

---

# Async HTTP Worker Pool

Below is a complete, production-quality module with an async worker pool, token-bucket rate limiting, exponential backoff with jitter, full type hints, docstrings, and a comprehensive `respx`-based test suite.

## Project layout

```
http_pool/
├── __init__.py
├── pool.py          # core implementation
└── tests/
    └── test_pool.py # pytest + respx tests
```

---

## `http_pool/pool.py`

```python
"""Async worker pool for rate-limited, retrying outbound HTTP calls.

This module provides :class:`HttpWorkerPool`, an asyncio-native worker pool
that:

* Bounds concurrency with a fixed set of worker tasks pulling from a queue.
* Rate-limits requests globally with a token-bucket limiter.
* Retries failed requests with exponential backoff plus full jitter.
* Honors ``Retry-After`` headers on 429/503 responses.
* Supports both ``httpx.AsyncClient`` (default) and any async callable,
  making it easy to swap in a different transport for testing.

Example
-------
>>> import asyncio
>>> from http_pool import HttpWorkerPool
>>>
>>> async def main() -> None:
...     async with HttpWorkerPool(workers=4, rate=10.0) as pool:
...         results = await pool.map("GET", "https://example.com")
...         print(results.status_code)
>>>
>>> asyncio.run(main())
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
)

import httpx

__all__ = [
    "HttpWorkerPool",
    "RequestSpec",
    "Response",
    "PoolResult",
    "PoolClosedError",
    "RetryPolicy",
    "RateLimiter",
]

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: HTTP status codes that are considered retryable by default.
DEFAULT_RETRYABLE_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

#: Exceptions that trigger a retry by default (transport-level failures).
DEFAULT_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    httpx.TimeoutException,
    httpx.TransportError,
)


class PoolClosedError(RuntimeError):
    """Raised when a request is submitted to a closed or not-yet-started pool."""


class RateLimiter:
    """A token-bucket rate limiter for asyncio.

    The bucket starts full and refills at ``rate`` tokens per second, up to
    ``capacity`` tokens. Callers ``await`` :meth:`acquire` before performing
    a rate-limited action; the call blocks until a token is available.

    Parameters
    ----------
    rate:
        Sustained number of tokens (requests) allowed per second.
    capacity:
        Maximum burst size. Defaults to ``rate`` (i.e. a one-second burst).

    Notes
    -----
    The implementation uses a single-condition broadcast: every waiter is
    woken on refill and re-checks availability. This is simple and correct
    for the pool's use case; for very high contention a fair queue would be
    preferable.
    """

    def __init__(self, rate: float, capacity: Optional[float] = None) -> None:
        if rate <= 0:
            raise ValueError(f"rate must be > 0, got {rate}")
        self._rate = float(rate)
        self._capacity = float(capacity if capacity is not None else rate)
        if self._capacity <= 0:
            raise ValueError(f"capacity must be > 0, got {self._capacity}")
        self._tokens = self._capacity
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()
        self._cond: Optional[asyncio.Condition] = None

    @property
    def rate(self) -> float:
        """Sustained token refill rate (tokens per second)."""
        return self._rate

    def _refill(self) -> None:
        """Add tokens accrued since the last refill, capped at capacity."""
        now = time.monotonic()
        elapsed = now - self._updated_at
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._updated_at = now

    async def acquire(self) -> None:
        """Block until one token is available, then consume it."""
        # The Condition must be created inside the running loop.
        if self._cond is None:
            async with self._lock:

