"""Bounded TTL/LRU success reuse and single-flight for synchronous provider work.

The lock protects bookkeeping only. Provider calls and waiting happen outside it.
An in-flight capacity overflow bypasses reuse rather than serializing other keys.
This is per process and does not survive cold starts or coordinate instances.
"""
from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import Future
from copy import deepcopy
import asyncio
import math
import threading
import time
from typing import Any, Awaitable, Callable, Hashable, TypeVar

from services.provider_cost_metrics import CAPABILITIES, PROVIDER_COST_METRICS

T = TypeVar("T")


class BoundedRequestCache:
    def __init__(self, capability: str, ttl_seconds: float, max_entries: int,
                 max_bytes: int | None = None, clock: Callable[[], float] = time.monotonic) -> None:
        if capability not in CAPABILITIES:
            raise ValueError("Unsupported provider capability")
        if not math.isfinite(ttl_seconds) or ttl_seconds < 0 or max_entries < 1 or (max_bytes is not None and max_bytes < 1):
            raise ValueError("Cache requires finite TTL and positive capacity")
        self.capability = capability
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self.clock = clock
        self.metrics = PROVIDER_COST_METRICS
        self._entries: OrderedDict[Hashable, tuple[float, Any, int]] = OrderedDict()
        self._inflight: dict[Hashable, Future[Any]] = {}
        self._bytes = 0
        self._epoch = 0
        self._lock = threading.Lock()

    def clear(self) -> None:
        """Invalidate completed results; active callers still receive their result."""
        with self._lock:
            self._entries.clear()
            self._bytes = 0
            self._epoch += 1
            self._inflight.clear()

    def _expire(self, now: float) -> None:
        for key, (expires, _, size) in list(self._entries.items()):
            if expires <= now:
                del self._entries[key]
                self._bytes -= size

    def _retain(self, key: Hashable, result: T, epoch: int,
                cacheable: Callable[[T], bool], size_of: Callable[[T], int] | None) -> T:
        retain = self.ttl_seconds > 0 and cacheable(result)
        if retain and self.max_bytes is not None and size_of is None:
            raise ValueError("Byte-bounded reuse requires size_of")
        size = size_of(result) if retain and size_of is not None else 0
        if size < 0:
            raise ValueError("Cache result size must be nonnegative")
        stored = deepcopy(result)
        with self._lock:
            if retain and epoch == self._epoch and (self.max_bytes is None or size <= self.max_bytes):
                old = self._entries.pop(key, None)
                if old:
                    self._bytes -= old[2]
                self._entries[key] = (self.clock() + self.ttl_seconds, stored, size)
                self._bytes += size
                while len(self._entries) > self.max_entries or (self.max_bytes is not None and self._bytes > self.max_bytes):
                    _, (_, _, evicted_size) = self._entries.popitem(last=False)
                    self._bytes -= evicted_size
        return stored

    def _release(self, key: Hashable, future: Future[Any] | None) -> None:
        if future is not None:
            with self._lock:
                if self._inflight.get(key) is future:
                    del self._inflight[key]

    async def async_run(self, key: Hashable, operation: Callable[[], Awaitable[T]], *,
                        cacheable: Callable[[T], bool] = lambda value: True,
                        size_of: Callable[[T], int] | None = None) -> T:
        """Native async waiters; cancellation detaches a caller from shared work."""
        self.metrics.record(self.capability, "logical_requests")
        with self._lock:
            self._expire(self.clock())
            if key in self._entries:
                self._entries.move_to_end(key)
                cached_value = self._entries[key][1]
                cached = True
                future = None
                owner = False
            else:
                cached = False
                future = self._inflight.get(key)
                owner = future is None
                epoch = self._epoch
                if owner and len(self._inflight) < self.max_entries:
                    future = Future()
                    self._inflight[key] = future
        if cached:
            self.metrics.record(self.capability, "cache_hit")
            self.metrics.record(self.capability, "avoided_operations")
            return deepcopy(cached_value)
        if not owner:
            self.metrics.record(self.capability, "coalesced")
            self.metrics.record(self.capability, "avoided_operations")
            assert future is not None
            return deepcopy(await asyncio.shield(asyncio.wrap_future(future)))
        self.metrics.record(self.capability, "cache_miss")
        if future is None:
            self.metrics.record(self.capability, "capacity_bypass")

        async def produce() -> T:
            try:
                result = await operation()
                stored = self._retain(key, result, epoch, cacheable, size_of)
                self.metrics.record(self.capability, "operation_success")
                if future is not None:
                    future.set_result(stored)
                return result
            except BaseException as error:
                self.metrics.record(self.capability, "operation_timeout" if isinstance(error, TimeoutError) else "operation_failure")
                if future is not None:
                    future.set_exception(error)
                raise
            finally:
                self._release(key, future)

        task = asyncio.create_task(produce())
        # Retrieve exceptions even when the requesting client disconnects.
        task.add_done_callback(lambda finished: finished.exception() if not finished.cancelled() else None)
        return await asyncio.shield(task)

    def run(self, key: Hashable, operation: Callable[[], T], *,
            cacheable: Callable[[T], bool] = lambda value: True,
            size_of: Callable[[T], int] | None = None) -> T:
        self.metrics.record(self.capability, "logical_requests")
        cached_value = None
        cached = False
        with self._lock:
            self._expire(self.clock())
            if key in self._entries:
                self._entries.move_to_end(key)
                cached_value = self._entries[key][1]
                cached = True
                future = None
                owner = False
            else:
                future = self._inflight.get(key)
                owner = future is None
                epoch = self._epoch
                if owner and len(self._inflight) < self.max_entries:
                    future = Future()
                    self._inflight[key] = future
        if cached:
            self.metrics.record(self.capability, "cache_hit")
            self.metrics.record(self.capability, "avoided_operations")
            return deepcopy(cached_value)
        if not owner:
            self.metrics.record(self.capability, "coalesced")
            self.metrics.record(self.capability, "avoided_operations")
            assert future is not None
            return deepcopy(future.result())
        self.metrics.record(self.capability, "cache_miss")
        if future is None:
            self.metrics.record(self.capability, "capacity_bypass")
        try:
            result = operation()
            stored = self._retain(key, result, epoch, cacheable, size_of)
            self.metrics.record(self.capability, "operation_success")
            if future is not None:
                future.set_result(stored)
            return result
        except BaseException as error:
            event = "operation_timeout" if isinstance(error, TimeoutError) else "operation_failure"
            self.metrics.record(self.capability, event)
            if future is not None:
                future.set_exception(error)
            raise
        finally:
            self._release(key, future)
