"""
Per-process circuit breaker for external API calls.

States:
  CLOSED    - normal; failures are counted
  OPEN      - provider considered unavailable; calls fail fast
  HALF-OPEN - one test call allowed after recovery_timeout

Each worker process has its own breaker instance. There is no shared state
across processes (acceptable: each worker protects itself independently).
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Awaitable, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CBState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CBState.CLOSED
        self._failures = 0
        self._opened_at: float = 0.0

    @property
    def state(self) -> CBState:
        if self._state == CBState.OPEN:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                self._state = CBState.HALF_OPEN
                logger.info(f"[CB:{self.name}] -> HALF-OPEN - testing recovery")
        return self._state

    def _on_success(self) -> None:
        was_half_open = self._state == CBState.HALF_OPEN
        self._failures = 0
        self._state = CBState.CLOSED
        if was_half_open:
            logger.info(f"[CB:{self.name}] -> CLOSED (recovered)")

    def _on_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state = CBState.OPEN
            self._opened_at = time.monotonic()
            logger.warning(
                f"[CB:{self.name}] -> OPEN after {self._failures} consecutive failures. "
                f"Fast-failing for {self.recovery_timeout:.0f}s."
            )

    async def call(self, coro: Awaitable[T]) -> T:
        """Await *coro* under circuit-breaker protection."""
        if self.state == CBState.OPEN:
            raise RuntimeError(
                f"[CB:{self.name}] Circuit is OPEN - provider unavailable. "
                f"Retrying after {self.recovery_timeout:.0f}s."
            )
        try:
            result = await coro
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise


dalle_cb = CircuitBreaker("dall-e-3", failure_threshold=3, recovery_timeout=60.0)
gemini_cb = CircuitBreaker("gemini", failure_threshold=3, recovery_timeout=60.0)
r2_cb = CircuitBreaker("r2-storage", failure_threshold=5, recovery_timeout=30.0)
