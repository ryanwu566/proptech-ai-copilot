"""Bounded process-local principal quotas; not subscription entitlements."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import math
import os
import threading
import time

from services.usage_principal import UsagePrincipal


@dataclass(frozen=True)
class QuotaPolicy:
    requests: int
    window: int
    operations: int
    operation_window: int
    daily_operations: int
    concurrency: int

    def __post_init__(self):
        ceilings = (100_000, 3600, 100_000, 3600, 1_000_000, 32)
        for value, ceiling in zip(vars(self).values(), ceilings):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= ceiling:
                raise RuntimeError("Invalid API quota configuration.")


DEFAULT_QUOTA_POLICIES = {
    "anonymous": QuotaPolicy(120, 60, 240, 3600, 1000, 16),
    "free": QuotaPolicy(240, 60, 600, 3600, 2000, 16),
    # Inert until a server-authorized entitlement adapter exists.
    "paid": QuotaPolicy(240, 60, 600, 3600, 2000, 16),
}
_CONFIG_FIELDS = ("REQUESTS", "WINDOW_SECONDS", "OPERATIONS", "OPERATION_WINDOW_SECONDS", "DAILY_OPERATIONS", "CONCURRENCY")


def configured_quota_policies() -> dict[str, QuotaPolicy]:
    result = {}
    for tier, policy in DEFAULT_QUOTA_POLICIES.items():
        values = []
        for name, default in zip(_CONFIG_FIELDS, vars(policy).values()):
            raw = os.getenv(f"API_QUOTA_{tier.upper()}_{name}", "").strip()
            try:
                value = int(raw) if raw else default
            except ValueError:
                raise RuntimeError("Invalid API quota configuration.") from None
            values.append(value)
        result[tier] = QuotaPolicy(*values)
    return result


class QuotaExceeded(Exception):
    def __init__(self, reason: str, retry_after: int):
        self.reason = reason
        self.retry_after = max(1, min(3600, int(retry_after)))
        super().__init__(reason)


@dataclass
class _Bucket:
    requests: tuple[float, int]
    operations: tuple[float, int]
    day: int
    daily_operations: int = 0
    active: int = 0
    last_used: float = 0.0


class PrincipalQuotas:
    def __init__(self, policies=None, *, clock=time.monotonic, wall_clock=time.time, max_keys=4096):
        self.policies = policies if policies is not None else configured_quota_policies()
        self.clock, self.wall_clock = clock, wall_clock
        self.max_keys = max(4, min(int(max_keys), 4096))
        self._buckets: dict[tuple[str, str], _Bucket] = {}
        self._lock = threading.Lock()
        self._last_prune = clock()

    def _bucket(self, principal, now, day):
        # Reserve one overflow bucket per tier; never evict live allowance state.
        if now - self._last_prune >= 3600:
            expired = [key for key, value in self._buckets.items() if not value.active and now - value.last_used >= 86400]
            for key in expired:
                del self._buckets[key]
            self._last_prune = now
        key = (principal.tier, principal.key)
        if key not in self._buckets:
            tiers = len(self.policies)
            overflow_key = (principal.tier, "overflow")
            if len(self._buckets) >= self.max_keys - tiers:
                key = overflow_key
            self._buckets.setdefault(key, _Bucket((now, 0), (now, 0), day, last_used=now))
        bucket = self._buckets[key]
        bucket.last_used = now
        return bucket

    @staticmethod
    def _window(value, now, seconds):
        return (now, 0) if now - value[0] >= seconds else value

    @contextmanager
    def request(self, principal: UsagePrincipal):
        policy = self.policies[principal.tier]
        with self._lock:
            now = self.clock()
            bucket = self._bucket(principal, now, int(self.wall_clock() // 86400))
            if bucket.active >= policy.concurrency:
                raise QuotaExceeded("principal_concurrency", 1)
            start, count = self._window(bucket.requests, now, policy.window)
            if count >= policy.requests:
                raise QuotaExceeded("principal_request_quota", math.ceil(policy.window - (now - start)))
            bucket.requests = start, count + 1
            bucket.active += 1
        try:
            yield
        finally:
            with self._lock:
                bucket.active -= 1

    def reserve_operation(self, principal: UsagePrincipal):
        policy = self.policies[principal.tier]
        with self._lock:
            now, wall = self.clock(), self.wall_clock()
            day = int(wall // 86400)
            bucket = self._bucket(principal, now, day)
            start, count = self._window(bucket.operations, now, policy.operation_window)
            daily = bucket.daily_operations if bucket.day == day else 0
            if count >= policy.operations:
                raise QuotaExceeded("principal_operation_quota", math.ceil(policy.operation_window - (now - start)))
            if daily >= policy.daily_operations:
                raise QuotaExceeded("principal_daily_quota", math.ceil((day + 1) * 86400 - wall))
            bucket.operations = start, count + 1
            bucket.day, bucket.daily_operations = day, daily + 1

    def tracked_key_count(self):
        with self._lock:
            return len(self._buckets)

    def current_usage(self, principal: UsagePrincipal) -> dict:
        """Server-only, one caller-selected verified identity; never enumerate users."""
        with self._lock:
            now, wall = self.clock(), self.wall_clock()
            bucket = self._bucket(principal, now, int(wall // 86400))
            policy = self.policies[principal.tier]
            return {"enforcement_scope": "process_local", "tier": principal.tier,
                    "requests": self._window(bucket.requests, now, policy.window)[1],
                    "operations": self._window(bucket.operations, now, policy.operation_window)[1],
                    "daily_operations": bucket.daily_operations if bucket.day == int(wall // 86400) else 0,
                    "concurrency": bucket.active, "policy": dict(vars(policy))}
