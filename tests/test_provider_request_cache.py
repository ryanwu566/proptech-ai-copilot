"""Deterministic resource, failure and concurrency contracts for provider reuse."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import asyncio

import pytest

from services.provider_request_cache import BoundedRequestCache
from services.provider_cost_metrics import ProviderCostMetrics


def test_expiry_lru_and_mutation_isolation():
    now = [0.0]
    cache = BoundedRequestCache("places", ttl_seconds=10, max_entries=2, clock=lambda: now[0])
    calls = []
    def load(key):
        calls.append(key)
        return {"value": [key]}
    first = cache.run("a", lambda: load("a"))
    first["value"].append("changed")
    assert cache.run("a", lambda: load("a")) == {"value": ["a"]}
    cache.run("b", lambda: load("b"))
    cache.run("a", lambda: load("a"))
    cache.run("c", lambda: load("c"))
    cache.run("b", lambda: load("b"))
    assert calls == ["a", "b", "c", "b"]
    now[0] = 10
    cache.run("b", lambda: load("b"))
    assert calls == ["a", "b", "c", "b", "b"]


def test_byte_bound_and_oversize_results_are_not_retained():
    cache = BoundedRequestCache("satellite", ttl_seconds=10, max_entries=5, max_bytes=5)
    calls = []
    def load(value):
        calls.append(value)
        return value
    for key, value in [("a", b"aaa"), ("b", b"bbb"), ("a", b"aaa"), ("x", b"123456"), ("x", b"123456")]:
        assert cache.run(key, lambda: load(value), size_of=len) == value
    assert calls == [b"aaa", b"bbb", b"aaa", b"123456", b"123456"]


def test_failure_and_unavailable_do_not_poison_reuse():
    cache = BoundedRequestCache("routes", ttl_seconds=10, max_entries=2)
    def failed():
        raise TimeoutError("provider timeout")
    with pytest.raises(TimeoutError):
        cache.run("a", failed)
    assert cache.run("a", lambda: None, cacheable=lambda value: value is not None) is None
    assert cache.run("a", lambda: "available") == "available"


def test_same_key_waits_while_other_key_runs(monkeypatch):
    cache = BoundedRequestCache("geocoding", ttl_seconds=0, max_entries=2)
    started, release, joined = Event(), Event(), Event()
    calls = []
    original_record = cache.metrics.record
    def record(capability, event, count=1):
        original_record(capability, event, count)
        if event == "coalesced":
            joined.set()
    monkeypatch.setattr(cache.metrics, "record", record)
    def load():
        calls.append("a")
        started.set()
        assert release.wait(5)
        return {"value": ["a"]}
    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(cache.run, "a", load)
        assert started.wait(5)
        second = pool.submit(cache.run, "a", load)
        assert joined.wait(5)
        assert pool.submit(cache.run, "b", lambda: "b").result(5) == "b"
        release.set()
        one, two = first.result(5), second.result(5)
    one["value"].append("changed")
    assert two == {"value": ["a"]}
    assert calls == ["a"]
    cache.run("a", lambda: calls.append("fresh"))
    assert calls == ["a", "fresh"]


def test_metrics_reject_sensitive_labels_and_render_finite_counters():
    registry = ProviderCostMetrics()
    registry.record("places", "logical_requests", 2)
    registry.record("places", "physical_calls")
    with pytest.raises(ValueError):
        registry.record("25.123,121.456", "physical_calls")
    with pytest.raises(ValueError):
        registry.record("places", "secret-address")
    rendered = registry.render_prometheus()
    assert 'capability="places",event="logical_requests"} 2' in rendered
    assert 'capability="places",event="physical_calls"} 1' in rendered
    assert "25.123" not in rendered


def test_clear_during_operation_does_not_repopulate_old_configuration():
    cache = BoundedRequestCache("routes", ttl_seconds=10, max_entries=2)
    started, release = Event(), Event()
    def old_configuration():
        started.set()
        assert release.wait(5)
        return "old"
    with ThreadPoolExecutor(max_workers=1) as pool:
        old = pool.submit(cache.run, "key", old_configuration)
        assert started.wait(5)
        cache.clear()
        assert cache.run("key", lambda: "new") == "new"
        release.set()
        assert old.result(5) == "old"
    assert cache.run("key", lambda: "wrong") == "new"


def test_inflight_capacity_bypasses_without_blocking_different_keys():
    cache = BoundedRequestCache("routes", ttl_seconds=10, max_entries=1)
    started, release = Event(), Event()
    def slow():
        started.set()
        assert release.wait(5)
        return "a"
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(cache.run, "a", slow)
        assert started.wait(5)
        assert pool.submit(cache.run, "b", lambda: "b").result(5) == "b"
        assert len(cache._inflight) == 1
        release.set()
        assert first.result(5) == "a"


def test_coalesced_failure_releases_all_waiters_and_next_attempt(monkeypatch):
    cache = BoundedRequestCache("routes", ttl_seconds=10, max_entries=2)
    started, release, joined = Event(), Event(), Event()
    original_record = cache.metrics.record
    def record(capability, event, count=1):
        original_record(capability, event, count)
        if event == "coalesced":
            joined.set()
    monkeypatch.setattr(cache.metrics, "record", record)
    def failing():
        started.set()
        assert release.wait(5)
        raise TimeoutError("timeout")
    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(cache.run, "a", failing)
        assert started.wait(5)
        two = pool.submit(cache.run, "a", failing)
        assert joined.wait(5)
        release.set()
        for result in (one, two):
            with pytest.raises(TimeoutError):
                result.result(5)
    assert cache.run("a", lambda: "recovered") == "recovered"


def test_async_waiters_do_not_consume_worker_threads_or_cancel_shared_work():
    cache = BoundedRequestCache("satellite", ttl_seconds=10, max_entries=2)
    calls = []
    async def exercise():
        started, release = asyncio.Event(), asyncio.Event()
        async def generate():
            calls.append("generation")
            started.set()
            await release.wait()
            return {"image": "bounded"}
        owner = asyncio.create_task(cache.async_run("a", generate))
        await started.wait()
        waiter = asyncio.create_task(cache.async_run("a", generate))
        await asyncio.sleep(0)
        owner.cancel()
        with pytest.raises(asyncio.CancelledError):
            await owner
        async def independent():
            return "b"
        assert await cache.async_run("b", independent) == "b"
        release.set()
        assert await waiter == {"image": "bounded"}
        assert await cache.async_run("a", generate) == {"image": "bounded"}
    asyncio.run(asyncio.wait_for(exercise(), timeout=5))
    assert calls == ["generation"]
