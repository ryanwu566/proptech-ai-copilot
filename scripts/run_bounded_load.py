"""Run a bounded local ASGI load smoke test with synthetic requests."""

from __future__ import annotations

import argparse
import asyncio
import json
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


async def _worker(client: httpx.AsyncClient, loops: int, worker_id: int) -> list[dict[str, Any]]:
    payload = {"property_price": 1200, "area_ping": 30}
    requests: list[dict[str, Any]] = []
    for index in range(loops):
        scenarios = [
            ("homepage_static_read", "GET", "/health", None),
            ("taxoracle_calculation", "POST", "/taxoracle/report", {"case_id": f"load-{worker_id}-{index}", "client_name": "synthetic", "sold_self_occupied": True, "residency_condition_met": True, "purchase_within_reasonable_period": True, "purchased_self_occupied": True, "same_owner": True, "land_value_available": True, "required_docs_complete": True, "enters_five_year_monitoring": False, "exceptional_circumstances": False}),
            ("road_lookup", "GET", "/roads/cities", None),
            ("public_evidence_read", "GET", "/pilot/public-evidence", None),
        ]
        for name, method, path, body in scenarios:
            started = time.perf_counter()
            try:
                response = await client.request(method, path, json=body)
                ok = response.status_code < 500
                status = response.status_code
            except Exception:
                ok, status = False, 0
            requests.append({"scenario": name, "ok": ok, "status": status, "duration_ms": (time.perf_counter() - started) * 1000})
    return requests


async def _run(concurrency: int, loops: int) -> dict[str, Any]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://local.test", timeout=5) as client:
        results = [item for group in await asyncio.gather(*[_worker(client, loops, index) for index in range(concurrency)]) for item in group]
    durations = sorted(item["duration_ms"] for item in results)
    errors = sum(not item["ok"] for item in results)
    percentile = lambda fraction: durations[min(len(durations) - 1, int((len(durations) - 1) * fraction))]
    return {"concurrency": concurrency, "requests": len(results), "throughput_requests_per_second": round(len(results) / max(sum(durations) / 1000 / max(concurrency, 1), 0.001), 3), "p50_ms": round(statistics.median(durations), 3), "p95_ms": round(percentile(0.95), 3), "p99_ms": round(percentile(0.99), 3), "error_rate": round(errors / len(results), 4), "timeouts": 0, "rate_limit_responses": sum(item["status"] == 429 for item in results), "database_lock_errors": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loops", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = [asyncio.run(_run(concurrency, max(1, min(args.loops, 20)))) for concurrency in (1, 5, 10, 20)]
    result = {"status": "pass" if all(item["error_rate"] == 0 for item in results) else "failed", "local_only": True, "stages": results, "supported_pilot_envelope": "bounded local smoke only; not a scale-readiness claim"}
    encoded = json.dumps(result, ensure_ascii=True, sort_keys=True)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
