"""Run a bounded local ASGI load smoke test with synthetic requests."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api_main import app
from backend.api.abuse_middleware import AbuseMiddleware


SAFE_REASONS = {"rate_limited", "capacity_exhausted", "provider_budget_exhausted", "capability_disabled", "guard_unavailable"}
EXPECTED_GUARDS = {
    ("road_lookup", 429): "rate_limited",
    ("taxoracle_calculation", 503): "capacity_exhausted",
}


def classify_response(response: httpx.Response, scenario: str) -> dict[str, Any]:
    """Accept only guard contracts observed on these specific local scenarios."""
    status = response.status_code
    reason = "none"
    if status >= 400:
        reason = "unrecognized"
        if len(response.content) <= 4096:
            try:
                payload = response.json()
                detail = payload.get("detail") if isinstance(payload, dict) else None
                raw = detail.get("reason_code") if isinstance(detail, dict) else None
                if isinstance(raw, str) and raw in SAFE_REASONS:
                    reason = raw
            except ValueError:
                pass
    retry = response.headers.get("Retry-After", "")
    valid_retry = bool(retry and len(retry) <= 4 and retry.isascii() and retry.isdecimal() and 0 < int(retry) <= 3600)
    expected = EXPECTED_GUARDS.get((scenario, status)) == reason and valid_retry
    outcome = "success" if 200 <= status < 300 else "rate_limited" if expected and status == 429 else "capacity_rejected" if expected else "unexpected_http"
    return {"status": status, "http_status_category": f"{status // 100}xx", "outcome": outcome,
            "reason_code": reason, "exception_category": "none", "valid_retry_after": valid_retry,
            "intended_guard_rejection": bool(expected)}


async def _measure_request(client, scenario, method, path, *, deadline=5, **kwargs):
    started = time.perf_counter()
    try:
        # ASGITransport does not itself enforce HTTPX network timeouts.
        async with asyncio.timeout(deadline):
            response = await client.request(method, path, **kwargs)
        result = classify_response(response, scenario)
    except (TimeoutError, httpx.TimeoutException):
        result = _exception_result("timeout")
    except httpx.TransportError:
        result = _exception_result("transport_error")
    except Exception:
        result = _exception_result("request_exception")
    return {**result, "scenario": scenario, "duration_ms": (time.perf_counter() - started) * 1000}


def _exception_result(category):
    return {"status": 0, "http_status_category": "no_response", "outcome": category,
            "reason_code": "none", "exception_category": category, "valid_retry_after": False,
            "intended_guard_rejection": False}


async def _worker(client: httpx.AsyncClient, loops: int, worker_id: int) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for index in range(loops):
        scenarios = [
            ("homepage_static_read", "GET", "/health", None),
            ("taxoracle_calculation", "POST", "/taxoracle/report", {"case_id": f"load-{worker_id}-{index}", "client_name": "synthetic", "sold_self_occupied": True, "residency_condition_met": True, "purchase_within_reasonable_period": True, "purchased_self_occupied": True, "same_owner": True, "land_value_available": True, "required_docs_complete": True, "enters_five_year_monitoring": False, "exceptional_circumstances": False}),
            ("road_lookup", "GET", "/roads/cities", None),
            ("public_evidence_read", "GET", "/pilot/public-evidence", None),
        ]
        for name, method, path, body in scenarios:
            requests.append(await _measure_request(client, name, method, path, json=body))
    return requests


def _summarize(results, *, concurrency, elapsed_seconds, mode):
    counts = Counter(item["outcome"] for item in results)
    accepted = {"success", "rate_limited", "capacity_rejected"}
    errors = sum(value for key, value in counts.items() if key not in accepted)
    durations = sorted(item["duration_ms"] for item in results if item["outcome"] == "success")
    percentile = lambda fraction: round(durations[max(0, math.ceil(len(durations) * fraction) - 1)], 3) if durations else None
    groups = Counter((item["scenario"], item["status"], item["http_status_category"], item["reason_code"], item["exception_category"], item["intended_guard_rejection"], item["valid_retry_after"]) for item in results)
    diagnostics = [{"scenario": key[0], "status": key[1], "http_status_category": key[2], "reason_code": key[3], "transport_exception_category": key[4], "intended_guard_rejection": key[5], "valid_retry_after": key[6], "count": count} for key, count in sorted(groups.items())]
    successful = counts["success"]
    total = len(results)
    passed = total > 0 and errors == 0 and (mode == "overload" or successful == total)
    return {
        "status": "pass" if passed else "failed", "mode": mode, "concurrency": concurrency, "requests": total,
        "successful_requests": successful, "rate_limited_requests": counts["rate_limited"],
        "controlled_capacity_rejections": counts["capacity_rejected"],
        "unexpected_5xx": sum(item["status"] >= 500 and item["outcome"] == "unexpected_http" for item in results),
        "unexpected_http_responses": counts["unexpected_http"], "transport_errors": counts["transport_error"],
        "request_exceptions": counts["request_exception"], "timeout_count": counts["timeout"], "timeouts": counts["timeout"],
        "unexpected_failure_count": errors, "unexpected_error_rate": round(errors / total, 4) if total else 0,
        # Retain the original raw 5xx/exception rate, even for controlled 503s.
        "error_rate": round(sum(item["status"] == 0 or item["status"] >= 500 for item in results) / total, 4) if total else 0,
        "rate_limit_responses": sum(item["status"] == 429 for item in results),
        "intended_guard_rejections": counts["rate_limited"] + counts["capacity_rejected"],
        "total_elapsed_time": round(elapsed_seconds, 6),
        "throughput_requests_per_second": round(total / max(elapsed_seconds, 0.000001), 3),
        "successful_requests_per_second": round(successful / max(elapsed_seconds, 0.000001), 3),
        "latency_sample_count": len(durations), "admitted_request_latency_p95": percentile(0.95),
        "p50_ms": round(statistics.median(durations), 3) if durations else None,
        "p95_ms": percentile(0.95), "p99_ms": percentile(0.99), "diagnostics": diagnostics,
    }


async def _run(concurrency: int, loops: int) -> dict[str, Any]:
    transport = httpx.ASGITransport(app=app)
    started = time.perf_counter()
    async with httpx.AsyncClient(transport=transport, base_url="http://local.test", timeout=5) as client:
        results = [item for group in await asyncio.gather(*[_worker(client, loops, index) for index in range(concurrency)]) for item in group]
    return _summarize(results, concurrency=concurrency, elapsed_seconds=time.perf_counter() - started,
                      mode="ordinary" if concurrency <= 10 else "overload")


async def _capacity_probe(*, timeout=5) -> dict[str, Any]:
    """Hold real streamed bodies to prove rejection and all sixteen permits.

    A local endpoint uses the actual middleware and shared semaphore, without
    altering limits/counters or dispatching provider/database work.
    """
    async def endpoint(scope, receive, send):
        if scope["method"] == "POST":
            await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=AbuseMiddleware(endpoint)), base_url="http://local.test") as client:
        async def wave(size):
            release = asyncio.Event()
            filled = asyncio.Event()
            rejected = asyncio.Event()
            if size <= 16:
                rejected.set()
            entered = 0
            completed = 0
            async def body():
                nonlocal entered
                entered += 1
                if entered >= 16:
                    filled.set()
                yield b"{"
                await release.wait()
                yield b"}"
            async def request():
                nonlocal completed
                result = await _measure_request(client, "taxoracle_calculation", "POST", "/taxoracle/report", deadline=timeout + 1, content=body())
                completed += 1
                if completed >= size - 16:
                    rejected.set()
                return result
            started = time.perf_counter()
            tasks = [asyncio.create_task(request()) for _ in range(size)]
            observed = False
            health = None
            try:
                async with asyncio.timeout(timeout):
                    await asyncio.gather(filled.wait(), rejected.wait())
                observed = entered == 16
                health = await _measure_request(client, "homepage_static_read", "GET", "/health")
            except TimeoutError:
                pass
            finally:
                release.set()
                results = await asyncio.gather(*tasks)
            report = _summarize(results, concurrency=size, elapsed_seconds=time.perf_counter() - started, mode="overload")
            report["saturation_observed"] = observed
            report["health_available"] = health is not None and health["outcome"] == "success"
            return report

        initial = await wave(20)
        recovery = await wave(16)
    recovery_passed = recovery["status"] == "pass" and recovery["successful_requests"] == 16 and recovery["saturation_observed"] and recovery["health_available"]
    passed = initial["status"] == "pass" and initial["successful_requests"] == 16 and initial["controlled_capacity_rejections"] == 4 and initial["saturation_observed"] and initial["health_available"] and recovery_passed
    return {**initial, "status": "pass" if passed else "failed", "scenario": "streamed_body_capacity",
            "recovery_status": "pass" if recovery_passed else "failed", "recovery_successful_requests": recovery["successful_requests"],
            "recovery": recovery}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loops", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = [asyncio.run(_run(concurrency, max(1, min(args.loops, 20)))) for concurrency in (1, 5, 10, 20)]
    capacity = asyncio.run(_capacity_probe())
    ordinary = all(item["status"] == "pass" for item in results if item["mode"] == "ordinary")
    overload = capacity["status"] == "pass" and all(item["status"] == "pass" for item in results if item["mode"] == "overload")
    result = {"status": "pass" if ordinary and overload else "failed", "ordinary_traffic_status": "pass" if ordinary else "failed",
              "overload_status": "pass" if overload else "failed", "local_only": True, "stages": results, "capacity_probe": capacity,
              "supported_pilot_envelope": "bounded local smoke only; not a scale-readiness claim"}
    encoded = json.dumps(result, ensure_ascii=True, sort_keys=True)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
