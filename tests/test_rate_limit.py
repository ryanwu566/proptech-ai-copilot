"""Deterministic tests for the bounded public-map cost guard."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from services.rate_limit import (
    DEFAULT_LIMIT,
    DEFAULT_WINDOW_SECONDS,
    MAX_TRACKED_BUCKETS,
    FixedWindowRateLimiter,
)


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_defaults_match_public_map_budget() -> None:
    limiter = FixedWindowRateLimiter()
    assert limiter.limit == DEFAULT_LIMIT == 30
    assert limiter.window_seconds == DEFAULT_WINDOW_SECONDS == 60


def test_first_n_requests_allowed_then_n_plus_one_rejected() -> None:
    limiter = FixedWindowRateLimiter(limit=3, window_seconds=60, clock=FakeClock())
    assert [limiter.check("k").allowed for _ in range(3)] == [True, True, True]
    assert limiter.check("k").allowed is False


def test_rejection_reports_positive_retry_after_without_extending_window() -> None:
    clock = FakeClock()
    limiter = FixedWindowRateLimiter(limit=1, window_seconds=60, clock=clock)
    assert limiter.check("k").allowed is True
    clock.advance(10.25)
    decision = limiter.check("k")
    assert decision.allowed is False
    assert decision.retry_after_seconds == 50
    clock.advance(49.75)
    assert limiter.check("k").allowed is True


def test_window_expiry_allows_traffic_again() -> None:
    clock = FakeClock()
    limiter = FixedWindowRateLimiter(limit=2, window_seconds=60, clock=clock)
    assert limiter.check("k").allowed is True
    assert limiter.check("k").allowed is True
    assert limiter.check("k").allowed is False
    clock.advance(60)
    assert limiter.check("k").allowed is True


def test_separate_keys_have_independent_budgets() -> None:
    limiter = FixedWindowRateLimiter(limit=1, window_seconds=60, clock=FakeClock())
    assert limiter.check("a").allowed is True
    assert limiter.check("a").allowed is False
    assert limiter.check("b").allowed is True


def test_active_bucket_table_stays_bounded_and_new_keys_share_overflow() -> None:
    limiter = FixedWindowRateLimiter(limit=1, window_seconds=60, clock=FakeClock())
    for index in range(MAX_TRACKED_BUCKETS - 1):
        assert limiter.check(f"key-{index}").allowed is True
    assert limiter.check("overflow-a").allowed is True
    assert limiter.check("overflow-b").allowed is False
    for index in range(10_000):
        limiter.check(f"extra-{index}")
    assert limiter.tracked_key_count() == MAX_TRACKED_BUCKETS


def test_stale_entries_are_pruned_after_window() -> None:
    clock = FakeClock()
    limiter = FixedWindowRateLimiter(limit=1, window_seconds=10, clock=clock)
    for index in range(5000):
        limiter.check(f"key-{index}")
    clock.advance(11)
    assert limiter.check("fresh").allowed is True
    assert limiter.tracked_key_count() == 1


def test_reset_clears_state() -> None:
    limiter = FixedWindowRateLimiter(limit=1, window_seconds=60)
    limiter.check("k")
    assert limiter.tracked_key_count() == 1
    limiter.reset()
    assert limiter.tracked_key_count() == 0


def test_limit_and_window_are_clamped_to_safe_bounds() -> None:
    zero = FixedWindowRateLimiter(limit=0, window_seconds=0)
    assert zero.limit == 1
    assert zero.window_seconds == 1
    huge = FixedWindowRateLimiter(limit=10_000_000, window_seconds=10_000_000)
    assert huge.limit == 100_000
    assert huge.window_seconds == 3_600


def test_concurrent_requests_share_one_atomic_budget() -> None:
    limiter = FixedWindowRateLimiter(limit=7, window_seconds=60, clock=FakeClock())
    with ThreadPoolExecutor(max_workers=16) as pool:
        decisions = list(pool.map(limiter.check, ["same-peer"] * 100))
    assert sum(decision.allowed for decision in decisions) == 7
    assert all(decision.retry_after_seconds > 0 for decision in decisions if not decision.allowed)
