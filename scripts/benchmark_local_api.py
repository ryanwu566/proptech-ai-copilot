"""Benchmark safe local API paths with synthetic inputs only."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api_main import app
from backend.api.routes_pilot import reset_pilot_store_for_tests
from services.pilot_evidence import PilotEvidenceStore


SAMPLES = 30


def _stats(samples: list[dict[str, Any]]) -> dict[str, Any]:
    values = sorted(item["duration_ms"] for item in samples)
    sizes = [item["response_bytes"] for item in samples]
    errors = sum(not item["ok"] for item in samples)
    percentile = lambda fraction: values[min(len(values) - 1, max(0, int((len(values) - 1) * fraction)))]
    return {
        "samples": len(samples),
        "p50_ms": round(statistics.median(values), 3) if values else None,
        "p95_ms": round(percentile(0.95), 3) if values else None,
        "p99_ms": round(percentile(0.99), 3) if values else None,
        "min_ms": round(min(values), 3) if values else None,
        "max_ms": round(max(values), 3) if values else None,
        "error_rate": round(errors / len(samples), 4) if samples else 0,
        "response_bytes_min": min(sizes) if sizes else None,
        "response_bytes_max": max(sizes) if sizes else None,
    }


def _run(client: TestClient, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = client.request(method, path, **kwargs)
        ok = response.status_code < 500
        size = len(response.content)
    except Exception:
        ok, size = False, 0
    return {"duration_ms": (time.perf_counter() - started) * 1000, "ok": ok, "response_bytes": size}


def _setup_store() -> tuple[PilotEvidenceStore, str, str]:
    store = PilotEvidenceStore(":memory:")
    store.create_campaign("bench-campaign", "synthetic-access-code")
    session = store.start_session("bench-campaign", "synthetic-access-code", locale="en", device_class="desktop", viewport_class="wide")
    assert session
    store.save_consent(session["session_id"], session["session_token"], {"participation": True, "interaction_metrics": True, "written_feedback": True, "publication": False})
    reset_pilot_store_for_tests(store)
    return store, session["session_id"], session["session_token"]


def benchmark(samples: int = SAMPLES) -> dict[str, Any]:
    store, session_id, session_token = _setup_store()
    tax_payload = {
        "case_id": "synthetic-api-benchmark",
        "client_name": "synthetic",
        "sold_self_occupied": True,
        "residency_condition_met": True,
        "purchase_within_reasonable_period": True,
        "purchased_self_occupied": True,
        "same_owner": True,
        "land_value_available": True,
        "required_docs_complete": True,
        "enters_five_year_monitoring": False,
        "exceptional_circumstances": False,
    }
    feedback = {
        "task_completion": "complete", "result_clarity": 4, "source_clarity": 4, "limitation_clarity": 4,
        "entry_ease": 4, "meeting_usefulness": 4, "trust_level": 4, "reuse_likelihood": 4,
        "most_confusing_step": "", "missing_capability": "", "current_alternative": "",
        "decision_maker_role": "analyst", "privacy_concern": "", "required_integration": "", "free_text": "synthetic", "willingness_to_pay": {},
    }
    with TestClient(app) as client:
        scenarios: dict[str, Callable[[int], dict[str, Any]]] = {
            "taxoracle_calculation": lambda i: _run(client, "POST", "/taxoracle/report", json=tax_payload),
            "holding_cost_calculation": lambda i: _run(client, "POST", "/holding-cost/calculate", json={"property_price": 1200, "area_ping": 30}),
            "road_location_lookup": lambda i: _run(client, "GET", "/roads/cities"),
            "pilot_access": lambda i: _run(client, "POST", "/pilot/access", json={"campaign_id": "bench-campaign", "pilot_code": "synthetic-access-code"}),
            "batched_event_ingestion": lambda i: _run(client, "POST", f"/pilot/sessions/{session_id}/events", headers={"X-Pilot-Session-Token": session_token}, json={"event_type": "workflow_opened", "idempotency_key": f"bench-{i}", "metadata": {"step_id": "synthetic"}}),
            "structured_feedback_submission": lambda i: _run(client, "POST", f"/pilot/sessions/{session_id}/feedback", headers={"X-Pilot-Session-Token": session_token}, json=feedback),
            "public_evidence_aggregate": lambda i: _run(client, "GET", "/pilot/public-evidence"),
            "source_status": lambda i: _run(client, "GET", "/valuation/data-status"),
            "deletion_dry_run": lambda i: _run(client, "GET", f"/pilot/sessions/{session_id}/deletion-dry-run", headers={"X-Pilot-Session-Token": session_token}),
        }
        result = {name: _stats([runner(i) for i in range(samples)]) for name, runner in scenarios.items()}
    store.close()
    return {"status": "pass" if all(item["error_rate"] == 0 for item in result.values()) else "failed", "samples_per_scenario": samples, "scenarios": result, "external_providers_called": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=SAMPLES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = benchmark(max(1, min(args.samples, 100)))
    encoded = json.dumps(result, ensure_ascii=True, sort_keys=True)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
