"""Provider-free acceptance regressions for the real bounded ASGI smoke."""
import asyncio
import json
import threading

import httpx
import pytest

from backend.api.abuse_middleware import AbuseMiddleware
from scripts import run_bounded_load as load
from services.anti_abuse import AbuseControls, Policy


def rejection(status=503, reason="capacity_exhausted", retry="1"):
    headers = {} if retry is None else {"Retry-After": retry.encode("utf-8") if not retry.isascii() else retry}
    return httpx.Response(status, json={"detail": {"reason_code": reason, "message": "Temporarily unavailable."}}, headers=headers)


@pytest.mark.parametrize("scenario,response,outcome", [
    ("taxoracle_calculation", httpx.Response(200), "success"),
    ("road_lookup", rejection(429, "rate_limited"), "rate_limited"),
    ("taxoracle_calculation", rejection(), "capacity_rejected"),
    ("taxoracle_calculation", rejection(503, "guard_unavailable"), "unexpected_http"),
    ("taxoracle_calculation", rejection(503, "capability_disabled"), "unexpected_http"),
    ("taxoracle_calculation", rejection(500), "unexpected_http"),
    ("homepage_static_read", rejection(), "unexpected_http"),
    ("taxoracle_calculation", rejection(429, "rate_limited"), "unexpected_http"),
    ("road_lookup", rejection(429, "provider_budget_exhausted"), "unexpected_http"),
    ("road_lookup", httpx.Response(422, json={"detail": []}), "unexpected_http"),
    ("road_lookup", httpx.Response(302), "unexpected_http"),
    ("taxoracle_calculation", httpx.Response(503, text="not JSON", headers={"Retry-After": "1"}), "unexpected_http"),
    ("taxoracle_calculation", httpx.Response(503, json={"reason_code": "capacity_exhausted"}, headers={"Retry-After": "1"}), "unexpected_http"),
])
def test_only_verified_scenario_status_reason_and_header_can_be_expected(scenario, response, outcome):
    result = load.classify_response(response, scenario)
    assert result["outcome"] == outcome
    assert result["intended_guard_rejection"] is (outcome in {"rate_limited", "capacity_rejected"})


@pytest.mark.parametrize("retry", [None, "0", "-1", "1.5", "later", "999999", "\u0661"])
def test_capacity_without_valid_bounded_retry_after_is_unexpected(retry):
    assert load.classify_response(rejection(retry=retry), "taxoracle_calculation")["outcome"] == "unexpected_http"


def test_diagnostics_never_echo_unrecognized_response_data():
    response = rejection(reason="private-token-address-123", retry="private-header")
    result = load.classify_response(response, "taxoracle_calculation")
    assert result["reason_code"] == "unrecognized"
    assert "private" not in json.dumps(result)


@pytest.mark.parametrize("error,category", [
    (httpx.ReadTimeout("private-url-token"), "timeout"),
    (TimeoutError("private-body"), "timeout"),
    (httpx.ConnectError("private-peer"), "transport_error"),
    (RuntimeError("private-stack"), "request_exception"),
])
def test_worker_retains_sanitized_exceptions_as_blocking_failures(error, category):
    async def run():
        async def fail(request):
            raise error
        async with httpx.AsyncClient(transport=httpx.MockTransport(fail), base_url="http://local.test") as client:
            records = await load._worker(client, 1, 0)
        assert len(records) == 4
        assert {item["outcome"] for item in records} == {category}
        assert "private" not in json.dumps(records)
        report = load._summarize(records, concurrency=1, elapsed_seconds=1, mode="ordinary")
        assert report["status"] == "failed"
        assert report["unexpected_failure_count"] == 4
        assert report["timeout_count"] == (4 if category == "timeout" else 0)
    asyncio.run(run())


def record(response, scenario, duration):
    return {**load.classify_response(response, scenario), "scenario": scenario, "duration_ms": duration}


def test_rejected_latency_does_not_inflate_admitted_latency_or_throughput():
    records = [record(httpx.Response(200), "taxoracle_calculation", value) for value in (10, 20, 30)]
    records += [record(rejection(), "taxoracle_calculation", 10000), record(rejection(429, "rate_limited"), "road_lookup", 9000)]
    report = load._summarize(records, concurrency=20, elapsed_seconds=2, mode="overload")
    assert report["status"] == "pass"
    assert report["successful_requests"] == 3
    assert report["controlled_capacity_rejections"] == 1
    assert report["rate_limited_requests"] == 1
    assert report["unexpected_failure_count"] == 0
    assert report["admitted_request_latency_p95"] == 30
    assert report["throughput_requests_per_second"] == 2.5
    assert report["successful_requests_per_second"] == 1.5
    assert report["error_rate"] == 0.2  # legacy 5xx evidence is retained
    assert report["unexpected_error_rate"] == 0


@pytest.mark.parametrize("response", [rejection(), rejection(429, "rate_limited")])
def test_ordinary_traffic_cannot_pass_by_rejecting_requests(response):
    scenario = "road_lookup" if response.status_code == 429 else "taxoracle_calculation"
    report = load._summarize([record(response, scenario, 1)], concurrency=1, elapsed_seconds=1, mode="ordinary")
    assert report["status"] == "failed"
    assert report["successful_requests"] == 0
    assert report["admitted_request_latency_p95"] is None


@pytest.mark.parametrize("response", [rejection(500), rejection(503, "guard_unavailable")])
def test_unexpected_http_errors_block_overload_acceptance(response):
    report = load._summarize([record(response, "taxoracle_calculation", 1)], concurrency=20, elapsed_seconds=1, mode="overload")
    assert report["status"] == "failed"
    assert report["unexpected_5xx"] == 1
    assert report["unexpected_failure_count"] == 1


async def success_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"{}"})


def test_smoke_preserves_real_rate_admission_across_runs_and_capabilities(monkeypatch):
    controls = AbuseControls({"metadata": Policy(2, 60, 1, 2), "places": Policy(2, 60, 1, 2)})
    monkeypatch.setattr(load, "app", AbuseMiddleware(success_app, controls=controls))
    async def run():
        first = await load._run(1, 1)
        second = await load._run(1, 1)
        third = await load._run(1, 1)
        assert first["successful_requests"] == second["successful_requests"] == 4
        assert first["status"] == second["status"] == "pass"
        assert third["rate_limited_requests"] == 1
        assert third["status"] == "failed"  # still ordinary traffic
        assert controls.request_limiters["metadata"].tracked_key_count() == 1
        controls.admit("places", "independent-capability")
    asyncio.run(run())


def test_real_twenty_request_capacity_probe_proves_rejection_and_full_recovery():
    report = asyncio.run(load._capacity_probe())
    assert report["status"] == "pass"
    assert report["concurrency"] == report["requests"] == 20
    assert report["successful_requests"] == 16
    assert report["controlled_capacity_rejections"] == 4
    assert report["unexpected_failure_count"] == 0
    assert report["recovery_successful_requests"] == 16
    assert report["recovery_status"] == "pass"


def test_capacity_probe_fails_if_the_guard_is_bypassed_and_drains_tasks(monkeypatch):
    monkeypatch.setattr(load, "AbuseMiddleware", lambda app: app)
    report = asyncio.run(load._capacity_probe(timeout=0.1))
    assert report["status"] == "failed"
    assert report["controlled_capacity_rejections"] == 0
    assert report["successful_requests"] == 20


def test_capacity_probe_detects_a_leaked_permit_and_releases_its_requests(monkeypatch):
    slots = threading.BoundedSemaphore(16)
    assert slots.acquire(blocking=False)
    monkeypatch.setattr("backend.api.abuse_middleware.BODY_SLOTS", slots)
    try:
        report = asyncio.run(load._capacity_probe(timeout=0.1))
        assert report["status"] == "failed"
        assert report["recovery_status"] == "failed"
        assert report["recovery_successful_requests"] == 15
    finally:
        slots.release()
    acquired = 0
    try:
        for _ in range(16):
            assert slots.acquire(blocking=False)
            acquired += 1
    finally:
        for _ in range(acquired):
            slots.release()
