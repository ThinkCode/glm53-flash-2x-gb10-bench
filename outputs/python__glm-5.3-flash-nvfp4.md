# python / glm-5.3-flash-nvfp4

- decode 33.5 tok/s
- TTFT 0.26s
- wall 30.8s
- 1024 tokens generated

---

# Async Rate-Limited HTTP Worker Pool

Below is a complete, production-quality module with a companion test suite. It's organized as a small package:

```
http_pool/
├── __init__.py
├── pool.py          # core implementation
└── test_pool.py     # pytest + respx tests
```

## `http_pool/pool.py`

```python
"""An async worker pool that rate-limits outbound HTTP calls.

Features
--------
- Bounded concurrency via a fixed set of asyncio worker tasks.
- Token-bucket rate limiting shared across all workers.
- Retries with exponential backoff and full jitter, honoring
  ``Retry-After`` headers when present.
- Full static typing (mypy --strict clean) and docstrings throughout.

Example
-------
    import httpx
    from http_pool import HttpWorkerPool

    async with HttpWorkerPool(workers=5, rate=10.0) as pool:
        response = await pool.submit(httpx.get, "https://example.com")
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import random
import time
from dataclasses import dataclass, field
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Generic,
    Optional,
    Sequence,
    TypeVar,
)

import httpx

__all__ = [
    "HttpWorkerPool",
    "PoolClosedError",
    "RateLimiter",
    "RetryPolicy",
    "TaskResult",
    "WorkerPool",
]

logger = logging.getLogger(__name__)

T = TypeVar("T")
U = TypeVar("U")

# A unit of work: any zero-argument callable returning an awaitable.
Job = Callable[[], Awaitable[T]]


class PoolClosedError(RuntimeError):
    """Raised when submitting work to a pool that is not running."""


class RateLimiter:
    """A token-bucket rate limiter for asyncio.

    The bucket starts full with ``capacity`` tokens and refills at
    ``rate`` tokens per second. ``acquire`` suspends the caller until a
    token is available, so it is safe to share one limiter across many
    concurrent workers.

    Args:
        rate: Sustained token refill rate, in tokens per second. Must
            be positive.
        capacity: Maximum burst size (bucket depth). Defaults to
            ``rate`` (i.e., one second's worth of tokens).

    Raises:
        ValueError: If ``rate`` or ``capacity`` is not positive.
    """

    def __init__(self, rate: float, capacity: Optional[float] = None) -> None:
        if rate <= 0:
            raise ValueError(f"rate must be positive, got {rate}")
        if capacity is None:
            capacity = rate
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")

        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    @property
    def rate(self) -> float:
        """Token refill rate in tokens per second."""
        return self._rate

    @property
    def capacity(self) -> float:
        """Maximum number of tokens the bucket can hold."""
        return self._capacity

    def _refill(self, now: float) -> None:
        """Top up the bucket based on elapsed time. Caller holds the lock."""
        elapsed = now - self._updated_at
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._updated_at = now

    async def acquire(self) -> float:
        """Acquire one token, suspending until one is available.

        Returns:
            The number of seconds the caller had to wait. Returns ``0.0``
            if a token was immediately available.
        """
        waited = 0.0
        start = time.monotonic()
        while True:
            async with self._lock:
                now = time.monotonic()
                self._refill(now)
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    waited = now - start
                    break
                # Time until the bucket accumulates one full token.
                deficit = 1.0 - self._tokens
                delay = deficit / self._rate
            # Sleep outside the lock so other waiters can re-check.
            await asyncio.sleep(delay)
        return waited


@dataclass(frozen=True)
class RetryPolicy:
    """Configuration for retrying failed jobs.

    Attributes:
        max_attempts: Total attempts per job, including the first. Must
            be at least 1.
        base_delay: Delay before the first retry, in seconds.
        max_delay: Upper bound on any single backoff
