"""Process-local, bounded fixed-window cost guard for public API routes."""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass


DEFAULT_LIMIT = 30
DEFAULT_WINDOW_SECONDS = 60
MAX_TRACKED_BUCKETS = 4096
_MAX_LIMIT = 100_000
_MAX_WINDOW_SECONDS = 3_600


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class FixedWindowRateLimiter:
    """Thread-safe limiter with one shared overflow bucket at capacity.

    The overflow bucket prevents new peer keys from growing memory or
    resetting their budget by cycling addresses after the table is full.
    State is per process and is not a distributed production quota.
    """

    def __init__(
        self,
        *,
        limit: int = DEFAULT_LIMIT,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        clock=time.monotonic,
    ) -> None:
        self._limit = max(1, min(int(limit), _MAX_LIMIT))
        self._window = max(1, min(int(window_seconds), _MAX_WINDOW_SECONDS))
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets: dict[str, tuple[float, int]] = {}
        self._overflow: tuple[float, int] | None = None
        self._last_prune = clock()

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def window_seconds(self) -> int:
        return self._window

    def _prune_locked(self, now: float) -> None:
        stale = [
            key for key, (started, _count) in self._buckets.items()
            if now - started >= self._window
        ]
        for key in stale:
            del self._buckets[key]
        if self._overflow is not None and now - self._overflow[0] >= self._window:
            self._overflow = None

    def check(self, key: str) -> RateLimitDecision:
        """Consume one request for a server-selected peer key."""

        with self._lock:
            now = self._clock()
            if now - self._last_prune >= self._window:
                self._prune_locked(now)
                self._last_prune = now

            overflow = key not in self._buckets and len(self._buckets) >= MAX_TRACKED_BUCKETS - 1
            if overflow:
                started, count = self._overflow or (now, 0)
            else:
                started, count = self._buckets.get(key, (now, 0))
            elapsed = now - started
            if elapsed >= self._window:
                started, count, elapsed = now, 0, 0.0

            if count >= self._limit:
                decision = RateLimitDecision(False, max(1, math.ceil(self._window - elapsed)))
            else:
                count += 1
                decision = RateLimitDecision(True, 0)

            if overflow:
                self._overflow = (started, count)
            else:
                self._buckets[key] = (started, count)
            return decision

    def reset(self) -> None:
        """Clear state for isolated tests."""

        with self._lock:
            self._buckets.clear()
            self._overflow = None
            self._last_prune = self._clock()

    def tracked_key_count(self) -> int:
        """Report retained buckets for tests and local observability."""

        with self._lock:
            return len(self._buckets) + (self._overflow is not None)
