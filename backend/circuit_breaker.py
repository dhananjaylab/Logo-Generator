"""
Shared-state circuit breaker backed by Redis.

HIGH-04 FIX: The previous implementation used per-process Python objects, meaning
each worker process had an independent view of provider health. If OpenAI went
down, one process would trip its breaker while others continued hammering the
failing API. With Redis as the state store, ALL API and worker processes share
a single consistent view of each circuit's state.

States (stored as Redis keys):
  CLOSED    — normal operation; failures are counted in cb:failures:{name}
  OPEN      — provider unavailable; all calls fail fast for `recovery_timeout` s
  HALF-OPEN — implicit; when the OPEN key expires Redis deletes it, the next
              call is a test probe (success → CLOSED, failure → re-OPEN)

Each circuit breaker maintains its own lightweight Redis connection (separate
from the main ARQ pool) so it works correctly in both API and worker processes
without requiring dependency injection.
"""

from __future__ import annotations

import logging
import os
from typing import Awaitable, TypeVar

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)
T = TypeVar("T")

# Read once at module load; override per-instance if needed.
_REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")


class RedisCircuitBreaker:
    """
    Async circuit breaker with Redis-backed shared state.

    Usage (identical to the old per-process breaker):
        result = await dalle_cb.call(some_awaitable)

    All processes that share the same Redis instance share circuit state,
    eliminating the split-brain problem of the previous per-process design.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
        redis_url: str = _REDIS_URL,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None

        # Redis key names
        self._key_open     = f"cb:open:{name}"
        self._key_failures = f"cb:failures:{name}"

    # ── Internal helpers ──────────────────────────────────────────────────

    async def _get_redis(self) -> aioredis.Redis:
        """Lazily create a dedicated Redis connection for this breaker."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._redis

    async def _is_open(self) -> bool:
        r = await self._get_redis()
        return bool(await r.exists(self._key_open))

    async def _on_success(self) -> None:
        r = await self._get_redis()
        was_half_open = not bool(await r.exists(self._key_open))
        await r.delete(self._key_failures)
        if was_half_open:
            logger.info(f"[CB:{self.name}] → CLOSED (recovered from half-open probe)")

    async def _on_failure(self) -> None:
        r = await self._get_redis()
        failures = int(await r.incr(self._key_failures) or 0)
        # Keep the failure counter alive for 2× the recovery window
        await r.expire(self._key_failures, self.recovery_timeout * 2)

        if failures >= self.failure_threshold:
            await r.setex(self._key_open, self.recovery_timeout, "1")
            logger.warning(
                f"[CB:{self.name}] → OPEN after {failures} consecutive failures. "
                f"Fast-failing for {self.recovery_timeout}s. "
                f"(All processes share this state via Redis key {self._key_open})"
            )

    # ── Public API ────────────────────────────────────────────────────────

    async def call(self, coro: Awaitable[T]) -> T:
        """Await *coro* under circuit-breaker protection."""
        if await self._is_open():
            r = await self._get_redis()
            ttl = await r.ttl(self._key_open)
            raise RuntimeError(
                f"[CB:{self.name}] Circuit OPEN — "
                f"provider unavailable. Retrying automatically in ~{max(ttl, 0)}s."
            )

        try:
            result = await coro
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise

    async def reset(self) -> None:
        """Manually reset the circuit to CLOSED (useful for admin tooling)."""
        r = await self._get_redis()
        await r.delete(self._key_open, self._key_failures)
        logger.info(f"[CB:{self.name}] Manually reset to CLOSED")

    async def close(self) -> None:
        """Release the Redis connection (call during worker/app shutdown)."""
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None
            logger.debug(f"[CB:{self.name}] Redis connection closed")

    async def status(self) -> dict:
        """Return current circuit state as a dict (useful for /health endpoint)."""
        r = await self._get_redis()
        is_open = bool(await r.exists(self._key_open))
        failures = int(await r.get(self._key_failures) or 0)
        ttl = await r.ttl(self._key_open) if is_open else -1
        return {
            "name": self.name,
            "state": "OPEN" if is_open else "CLOSED",
            "failures": failures,
            "recovery_ttl_seconds": max(ttl, 0),
        }


# ── Shared circuit breaker instances ──────────────────────────────────────────
# State lives in Redis — consistent across every API process and every worker.

dalle_cb = RedisCircuitBreaker(
    "dall-e-3",
    failure_threshold=3,
    recovery_timeout=60,
)

gemini_cb = RedisCircuitBreaker(
    "gemini",
    failure_threshold=3,
    recovery_timeout=60,
)

r2_cb = RedisCircuitBreaker(
    "r2-storage",
    failure_threshold=5,
    recovery_timeout=30,
)


async def close_all() -> None:
    """Close all circuit breaker Redis connections. Call on app/worker shutdown."""
    for cb in (dalle_cb, gemini_cb, r2_cb):
        await cb.close()
