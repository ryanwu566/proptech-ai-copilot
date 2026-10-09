"""Bounded process-local admission; no forwarded-header or global quota claims."""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
import inspect
import os
import threading
import time

from starlette.exceptions import HTTPException

from services.provider_cost_metrics import PROVIDER_COST_METRICS
from services.rate_limit import FixedWindowRateLimiter


@dataclass(frozen=True)
class Policy:
    requests: int
    window: int
    concurrency: int
    operations: int
    operation_window: int = 3600


# Counts are conservative operation units, never estimated currency. Places
# makes up to six category calls; Routes one origin/destination/mode; satellite
# one contained generation. Coarse peer limits must be tuned behind ingress.
POLICIES = {
    "geocoding": Policy(30, 60, 4, 300),
    "places": Policy(10, 60, 6, 300),
    "routes": Policy(10, 60, 2, 120),
    "satellite": Policy(2, 300, 1, 12),
    "location": Policy(10, 60, 4, 120),
    "terrain": Policy(6, 60, 2, 60),
    "valuation": Policy(20, 60, 4, 300),
    "trend": Policy(20, 60, 4, 300),
    "finder": Policy(20, 60, 4, 300),
    "market": Policy(30, 60, 4, 600),
    "market_ops": Policy(10, 300, 1, 12),
    "parcel": Policy(6, 60, 2, 60),
    "metadata": Policy(120, 60, 8, 1200),
    "ardswc": Policy(6, 60, 6, 600),
    "liquefaction": Policy(6, 60, 2, 300),
    "nlsc": Policy(6, 60, 2, 120),
    "tgos": Policy(30, 60, 4, 300),
    "identity": Policy(20, 60, 4, 300),
}


def _configured_int(name: str, default: int, ceiling: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise RuntimeError("Invalid anti-abuse configuration.") from None
    if value < 1:
        raise RuntimeError("Invalid anti-abuse configuration.")
    return min(value, ceiling)


def configured_policies() -> dict[str, Policy]:
    result = {}
    for name, default in POLICIES.items():
        prefix = f"ANTI_ABUSE_{name.upper()}_"
        result[name] = Policy(
            _configured_int(prefix + "REQUESTS", default.requests, 100_000),
            _configured_int(prefix + "WINDOW_SECONDS", default.window, 3600),
            _configured_int(prefix + "CONCURRENCY", default.concurrency, 32),
            _configured_int(prefix + "OPERATIONS", default.operations, 100_000),
            _configured_int(prefix + "OPERATION_WINDOW_SECONDS", default.operation_window, 3600),
        )
    return result


class AbuseRejected(HTTPException):
    def __init__(self, reason: str, *, status: int = 429, retry_after: int = 1):
        messages = {
            "rate_limited": "Too many requests. Please retry later.",
            "provider_budget_exhausted": "This capability has reached its temporary operation limit.",
            "capacity_exhausted": "This capability is busy. Please try again later.",
            "capability_disabled": "This capability is temporarily disabled.",
            "guard_unavailable": "This capability is temporarily unavailable.",
        }
        super().__init__(status_code=status, detail={"reason_code": reason, "message": messages[reason]},
                         headers={"Retry-After": str(max(1, retry_after))})


class AbuseControls:
    def __init__(self, policies=None, *, clock=time.monotonic):
        self.policies = policies if policies is not None else configured_policies()
        self.request_limiters = {name: FixedWindowRateLimiter(limit=p.requests, window_seconds=p.window, clock=clock) for name, p in self.policies.items()}
        self.operation_limiters = {name: FixedWindowRateLimiter(limit=p.operations, window_seconds=p.operation_window, clock=clock) for name, p in self.policies.items()}
        self.semaphores = {name: threading.BoundedSemaphore(p.concurrency) for name, p in self.policies.items()}

    def reject(self, name: str, reason: str, *, status=429, retry_after=1):
        PROVIDER_COST_METRICS.record(name, "rejected_requests")
        PROVIDER_COST_METRICS.record(name, reason)
        raise AbuseRejected(reason, status=status, retry_after=retry_after)

    def enabled(self, name: str):
        # Malformed emergency settings fail closed, independently per capability.
        if not capability_enabled(name):
            self.reject(name, "capability_disabled", status=503, retry_after=60)

    def admit(self, name: str, peer: str):
        self.enabled(name)
        try:
            decision = self.request_limiters[name].check(peer)
            allowed, retry_after = decision.allowed, decision.retry_after_seconds
        except Exception:
            self.reject(name, "guard_unavailable", status=503)
        if not allowed:
            self.reject(name, "rate_limited", retry_after=retry_after)
        PROVIDER_COST_METRICS.record(name, "admitted_requests")

    @contextmanager
    def operation(self, name: str):
        self.enabled(name)
        semaphore = self.semaphores[name]
        if not semaphore.acquire(blocking=False):
            self.reject(name, "capacity_exhausted", status=503)
        try:
            # One fixed key per capability: aggregate across peers and adapters.
            try:
                decision = self.operation_limiters[name].check("process")
                allowed, retry_after = decision.allowed, decision.retry_after_seconds
            except Exception:
                self.reject(name, "guard_unavailable", status=503)
            if not allowed:
                self.reject(name, "provider_budget_exhausted", retry_after=retry_after)
            PROVIDER_COST_METRICS.record(name, "operation_reservations")
            yield
        finally:
            semaphore.release()


def capability_enabled(name: str) -> bool:
    value = os.getenv(f"ANTI_ABUSE_{name.upper()}_DISABLED", "false").strip().lower()
    return value in {"", "0", "false", "no", "off"}


CONTROLS = AbuseControls()


def ensure_enabled(name: str):
    CONTROLS.enabled(name)


def provider_operation(name: str):
    """Hold nonwaiting permits around actual work, after cache owner selection.

    Physical call counters remain at existing dispatch sites. Async cancellation
    detaches the waiter; its permit is held until the producer actually stops.
    """
    def decorate(function):
        if inspect.iscoroutinefunction(function):
            @wraps(function)
            async def async_wrapper(*args, **kwargs):
                async def produce():
                    with CONTROLS.operation(name):
                        return await function(*args, **kwargs)
                task = asyncio.create_task(produce())
                task.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
                return await asyncio.shield(task)
            return async_wrapper
        @wraps(function)
        def wrapper(*args, **kwargs):
            with CONTROLS.operation(name):
                return function(*args, **kwargs)
        return wrapper
    return decorate
