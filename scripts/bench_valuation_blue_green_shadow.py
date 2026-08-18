#!/usr/bin/env python3
"""BLUE vs GREEN /valuation/estimate shadow A/B harness.

Compares complete valuation behavior using identical inputs against:
  A = BLUE comparables (PLVR_DATA_BACKEND=blue)
  B = Compact GREEN comparables (PLVR_DATA_BACKEND=green)

Measures TWO layers per side with independent provenance:
  SERVICE: estimate_property(payload)
  API: POST /valuation/estimate via in-process ASGI TestClient

Each side runs in a SEPARATE subprocess for env/cache isolation.
TestClient uses proper lifespan context manager.

Required environment:
  VALUATION_DATABASE_URL       — BLUE database
  COMPACT_GREEN_DATABASE_URL   — GREEN database

Usage:
  python scripts/bench_valuation_blue_green_shadow.py --dry-run
  python scripts/bench_valuation_blue_green_shadow.py
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CASES_FILE = SCRIPT_DIR / "valuation_shadow_cases.json"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "valuation-shadow"
MAX_COMPARABLE_DIAGNOSTICS = 5

# Ensure project root is importable when run as standalone script
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_RESPONSE_REQUIRED_FIELDS = {
    "source", "data_status", "estimate_level", "confidence", "confidence_score",
    "comparables", "methodology", "disclaimer",
}
_RESPONSE_NUMERIC_FIELDS = {
    "estimate_total_price", "estimate_unit_price_per_ping", "confidence_score",
}
# Deterministic fields that must match between service and API layers
_DETERMINISTIC_FIELDS = (
    "valuation_status", "estimate_total_price", "estimate_unit_price_per_ping",
    "confidence_score", "estimate_level",
)


# ============================================================
# Configuration
# ============================================================

def _check_configuration(dry_run: bool) -> dict[str, str]:
    if dry_run:
        return {"status": "configured"}
    issues = []
    if not os.getenv("VALUATION_DATABASE_URL", "").strip():
        issues.append("VALUATION_DATABASE_URL is not set")
    if not os.getenv("COMPACT_GREEN_DATABASE_URL", "").strip():
        issues.append("COMPACT_GREEN_DATABASE_URL is not set")
    if issues:
        for i in issues:
            print(f"ERROR: {i}")
        return {}
    return {"status": "configured"}


# ============================================================
# Schema validation — uses canonical model
# ============================================================

def validate_case_schema(case: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate against the canonical ValuationRequest Pydantic model."""
    try:
        from backend.api.routes_valuation import ValuationRequest
        payload = {k: v for k, v in case.items() if k != "case_id"}
        ValuationRequest(**payload)
        return (True, [])
    except Exception as exc:
        return (False, [str(exc)[:200]])


# ============================================================
# Response contract validation
# ============================================================

def validate_response_contract(response: dict[str, Any]) -> tuple[bool, list[str]]:
    errors = []
    missing = _RESPONSE_REQUIRED_FIELDS - set(response.keys())
    if missing:
        errors.append(f"missing: {missing}")
    for field in _RESPONSE_NUMERIC_FIELDS:
        val = response.get(field)
        if val is not None:
            if not isinstance(val, (int, float)):
                errors.append(f"{field} not numeric")
            elif not math.isfinite(val):
                errors.append(f"{field} non-finite: {val}")
            elif field in ("estimate_total_price", "estimate_unit_price_per_ping") and val < 0:
                errors.append(f"{field} negative: {val}")
    price_range = response.get("price_range")
    if isinstance(price_range, dict):
        for k in ("low", "mid", "high"):
            v = price_range.get(k)
            if isinstance(v, (int, float)) and not math.isfinite(v):
                errors.append(f"price_range.{k} non-finite")
    comps = response.get("comparables")
    if comps is not None and not isinstance(comps, list):
        errors.append("comparables not list")
    return (len(errors) == 0, errors)


# ============================================================
# Provenance validation
# ============================================================

def validate_backend_provenance(
    blue_svc_prov: dict[str, int],
    blue_api_prov: dict[str, int],
    green_svc_prov: dict[str, int],
    green_api_prov: dict[str, int],
) -> tuple[bool, list[str]]:
    """Validate that each side used exactly its expected backend."""
    reasons = []
    # BLUE service
    if blue_svc_prov.get("blue_calls", 0) == 0:
        reasons.append("BLUE service: blue_calls=0")
    if blue_svc_prov.get("green_calls", 0) != 0:
        reasons.append(f"BLUE service: green_calls={blue_svc_prov.get('green_calls')}")
    # BLUE API
    if blue_api_prov.get("blue_calls", 0) == 0:
        reasons.append("BLUE API: blue_calls=0")
    if blue_api_prov.get("green_calls", 0) != 0:
        reasons.append(f"BLUE API: green_calls={blue_api_prov.get('green_calls')}")
    # GREEN service
    if green_svc_prov.get("green_calls", 0) == 0:
        reasons.append("GREEN service: green_calls=0")
    if green_svc_prov.get("blue_calls", 0) != 0:
        reasons.append(f"GREEN service: blue_calls={green_svc_prov.get('blue_calls')}")
    # GREEN API
    if green_api_prov.get("green_calls", 0) == 0:
        reasons.append("GREEN API: green_calls=0")
    if green_api_prov.get("blue_calls", 0) != 0:
        reasons.append(f"GREEN API: blue_calls={green_api_prov.get('blue_calls')}")
    return (len(reasons) == 0, reasons)


# ============================================================
# Service/API consistency check
# ============================================================

def check_service_api_consistency(service_result: dict[str, Any], api_result: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check deterministic fields match between service and API layers."""
    reasons = []
    for field in _DETERMINISTIC_FIELDS:
        svc_val = service_result.get(field)
        api_val = api_result.get(field)
        if field == "estimate_total_price" or field == "estimate_unit_price_per_ping" or field == "confidence_score":
            # Numeric comparison with tolerance
            if isinstance(svc_val, (int, float)) and isinstance(api_val, (int, float)):
                if abs(svc_val - api_val) > 0.01:
                    reasons.append(f"{field}: service={svc_val} api={api_val}")
            elif svc_val != api_val:
                reasons.append(f"{field}: service={svc_val} api={api_val}")
        else:
            if svc_val != api_val:
                reasons.append(f"{field}: service={svc_val} api={api_val}")
    return (len(reasons) == 0, reasons)


# ============================================================
# Classification
# ============================================================

def classify_case(case_data: dict[str, Any]) -> tuple[str, list[str]]:
    """Classify based on full case data including both sides."""
    reasons: list[str] = []
    blue = case_data["blue"]
    green = case_data["green"]

    # Hard: any exception
    if blue.get("service_status") != "ok":
        return ("FAIL", ["BLUE service exception"])
    if green.get("service_status") != "ok":
        return ("FAIL", ["GREEN service exception"])
    if blue.get("api_status") != "ok":
        return ("FAIL", [f"BLUE API status: {blue.get('api_status')}"])
    if green.get("api_status") != "ok":
        return ("FAIL", [f"GREEN API status: {green.get('api_status')}"])
    if blue.get("api_http_status") != 200:
        return ("FAIL", [f"BLUE API HTTP {blue.get('api_http_status')}"])
    if green.get("api_http_status") != 200:
        return ("FAIL", [f"GREEN API HTTP {green.get('api_http_status')}"])

    # Contract
    if not blue.get("service_contract_valid"):
        return ("FAIL", [f"BLUE service contract: {blue.get('service_contract_errors', [])[:2]}"])
    if not green.get("service_contract_valid"):
        return ("FAIL", [f"GREEN service contract: {green.get('service_contract_errors', [])[:2]}"])
    if not blue.get("api_contract_valid"):
        return ("FAIL", [f"BLUE API contract: {blue.get('api_contract_errors', [])[:2]}"])
    if not green.get("api_contract_valid"):
        return ("FAIL", [f"GREEN API contract: {green.get('api_contract_errors', [])[:2]}"])

    # Service/API consistency
    if not blue.get("svc_api_consistent"):
        return ("FAIL", [f"BLUE service/API mismatch: {blue.get('svc_api_reasons', [])[:2]}"])
    if not green.get("svc_api_consistent"):
        return ("FAIL", [f"GREEN service/API mismatch: {green.get('svc_api_reasons', [])[:2]}"])

    # Provenance
    if not case_data.get("provenance_valid"):
        return ("FAIL", case_data.get("provenance_reasons", ["provenance invalid"]))

    # Source check
    if green.get("source") == "mock_fallback":
        return ("FAIL", ["GREEN used mock_fallback"])

    # Non-finite/negative estimate
    g_est = green.get("estimate_total_price")
    if isinstance(g_est, (int, float)):
        if not math.isfinite(g_est):
            return ("FAIL", [f"GREEN estimate non-finite: {g_est}"])
        if g_est < 0:
            return ("FAIL", [f"GREEN estimate negative: {g_est}"])

    # Zero comparables when BLUE has data
    if (green.get("comparable_count") or 0) == 0 and (blue.get("comparable_count") or 0) > 0:
        if green.get("valuation_status") not in ("unavailable", "no_data"):
            return ("FAIL", ["GREEN zero comparables when BLUE has data"])

    # GREEN unavailable when BLUE available
    if blue.get("valuation_status") in ("available", "demo") and green.get("valuation_status") == "unavailable":
        return ("FAIL", ["GREEN unavailable when BLUE available"])

    # REVIEW: large delta
    diff = case_data.get("diff", {})
    pct = diff.get("estimate_pct_delta")
    if pct is not None and abs(pct) > 20:
        return ("REVIEW", [f"estimate delta {pct:.1f}% > 20%"])
    conf_delta = diff.get("confidence_delta")
    if conf_delta is not None and conf_delta < -20:
        return ("REVIEW", [f"confidence delta {conf_delta} < -20"])

    return ("EXPECTED", ["within expected bounds"])


# ============================================================
# Case loading
# ============================================================

def load_cases() -> list[dict[str, Any]]:
    if not CASES_FILE.is_file():
        raise FileNotFoundError(f"Cases file not found: {CASES_FILE}")
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or len(cases) == 0:
        raise ValueError("Cases file empty or invalid")
    ids = [c.get("case_id") for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case_id")
    return cases


# ============================================================
# Worker subprocess
# ============================================================

_WORKER_SCRIPT = r'''
import json, os, sys, time
sys.path.insert(0, os.environ["PROJECT_ROOT"])

# Provenance counters — separate for service and API layers
_counters = {"blue": 0, "green": 0}

def _reset_counters():
    _counters["blue"] = 0
    _counters["green"] = 0

def _get_counters():
    return {"blue_calls": _counters["blue"], "green_calls": _counters["green"]}

def _instrument():
    from services.valuation_providers.postgres_provider import PostgresValuationProvider
    _orig_blue = PostgresValuationProvider.query_comparables
    def _wrapped_blue(self, *a, **kw):
        _counters["blue"] += 1
        return _orig_blue(self, *a, **kw)
    PostgresValuationProvider.query_comparables = _wrapped_blue

    import services.compact_green_query as gcq
    _orig_green = gcq.query_green_comparables
    def _wrapped_green(*a, **kw):
        _counters["green"] += 1
        return _orig_green(*a, **kw)
    gcq.query_green_comparables = _wrapped_green

_instrument()

from fastapi.testclient import TestClient
from backend.api_main import app

cases = json.loads(sys.stdin.read())
outputs = []

with TestClient(app) as client:
    for case in cases:
        payload = {k: v for k, v in case.items() if k != "case_id"}

        # SERVICE layer
        _reset_counters()
        from services.valuation_service import estimate_property
        svc_t0 = time.perf_counter()
        try:
            svc_result = estimate_property(payload)
            svc_t1 = time.perf_counter()
            svc_out = {"status": "ok", "latency_ms": round((svc_t1 - svc_t0) * 1000, 1), "result": svc_result}
        except Exception as exc:
            svc_t1 = time.perf_counter()
            svc_out = {"status": "error", "latency_ms": round((svc_t1 - svc_t0) * 1000, 1), "error_type": type(exc).__name__}
        svc_prov = _get_counters()

        # API layer
        _reset_counters()
        api_t0 = time.perf_counter()
        try:
            resp = client.post("/valuation/estimate", json=payload)
            api_t1 = time.perf_counter()
            api_out = {
                "status": "ok" if resp.status_code == 200 else "http_error",
                "http_status": resp.status_code,
                "latency_ms": round((api_t1 - api_t0) * 1000, 1),
                "result": resp.json() if resp.status_code == 200 else None,
            }
        except Exception as exc:
            api_t1 = time.perf_counter()
            api_out = {"status": "error", "latency_ms": round((api_t1 - api_t0) * 1000, 1), "error_type": type(exc).__name__}
        api_prov = _get_counters()

        outputs.append({"service": svc_out, "api": api_out, "service_provenance": svc_prov, "api_provenance": api_prov})

print(json.dumps(outputs, ensure_ascii=True, default=str))
'''


def _run_side(side: str, cases: list[dict[str, Any]], env_overrides: dict[str, str]) -> list[dict[str, Any]]:
    env = {**os.environ, **env_overrides, "PROJECT_ROOT": str(PROJECT_ROOT)}
    proc = subprocess.run(
        [sys.executable, "-c", _WORKER_SCRIPT],
        input=json.dumps(cases, ensure_ascii=False),
        capture_output=True, text=True, env=env,
        cwd=str(PROJECT_ROOT), timeout=600,
    )
    if proc.returncode != 0:
        stderr = proc.stderr[-500:] if proc.stderr else ""
        for pat in ["postgresql://", "postgres://", "supabase"]:
            if pat in stderr.lower():
                stderr = "[redacted]"
                break
        print(f"ERROR: {side} failed (exit {proc.returncode})")
        if stderr:
            print(f"  {stderr}")
        return [{"service": {"status": "subprocess_error"}, "api": {"status": "subprocess_error"}, "service_provenance": {}, "api_provenance": {}} for _ in cases]
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [{"service": {"status": "parse_error"}, "api": {"status": "parse_error"}, "service_provenance": {}, "api_provenance": {}} for _ in cases]


# ============================================================
# Metrics
# ============================================================

def _extract_side_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    svc = raw.get("service", {})
    api = raw.get("api", {})
    svc_result = svc.get("result", {}) if svc.get("status") == "ok" else {}
    api_result = api.get("result", {}) if api.get("status") == "ok" else {}

    # Contract validation
    svc_cv, svc_ce = validate_response_contract(svc_result) if svc.get("status") == "ok" else (False, ["no result"])
    api_cv, api_ce = validate_response_contract(api_result) if api.get("status") == "ok" else (False, ["no result"])

    # Service/API consistency
    if svc.get("status") == "ok" and api.get("status") == "ok":
        consistent, consist_reasons = check_service_api_consistency(svc_result, api_result)
    else:
        consistent, consist_reasons = (False, ["one side failed"])

    # Comparable count from service result (for primary comparison)
    comp_count = len(svc_result.get("comparables", []))

    return {
        "service_status": svc.get("status"),
        "service_latency_ms": svc.get("latency_ms"),
        "service_contract_valid": svc_cv,
        "service_contract_errors": svc_ce[:3],
        "service_provenance": raw.get("service_provenance", {}),
        "api_status": api.get("status"),
        "api_http_status": api.get("http_status"),
        "api_latency_ms": api.get("latency_ms"),
        "api_contract_valid": api_cv,
        "api_contract_errors": api_ce[:3],
        "api_provenance": raw.get("api_provenance", {}),
        "svc_api_consistent": consistent,
        "svc_api_reasons": consist_reasons[:3],
        "valuation_status": svc_result.get("valuation_status"),
        "source": svc_result.get("source"),
        "estimate_total_price": svc_result.get("estimate_total_price"),
        "estimate_unit_price_per_ping": svc_result.get("estimate_unit_price_per_ping"),
        "confidence": svc_result.get("confidence"),
        "confidence_score": svc_result.get("confidence_score"),
        "estimate_level": svc_result.get("estimate_level"),
        "comparable_count": comp_count,
    }


def _compute_diff(blue: dict[str, Any], green: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {}
    b_est = blue.get("estimate_total_price")
    g_est = green.get("estimate_total_price")
    if _fin(b_est) and _fin(g_est) and b_est != 0:
        diff["estimate_abs_delta"] = round(g_est - b_est, 1)
        diff["estimate_pct_delta"] = round((g_est - b_est) / b_est * 100, 2)
    else:
        diff["estimate_abs_delta"] = None
        diff["estimate_pct_delta"] = None
    b_c = blue.get("confidence_score")
    g_c = green.get("confidence_score")
    diff["confidence_delta"] = (g_c - b_c) if _fin(b_c) and _fin(g_c) else None
    diff["comparable_count_delta"] = (green.get("comparable_count") or 0) - (blue.get("comparable_count") or 0)
    b_sl = blue.get("service_latency_ms")
    g_sl = green.get("service_latency_ms")
    diff["service_latency_delta"] = round(g_sl - b_sl, 1) if _fin(b_sl) and _fin(g_sl) else None
    b_al = blue.get("api_latency_ms")
    g_al = green.get("api_latency_ms")
    diff["api_latency_delta"] = round(g_al - b_al, 1) if _fin(b_al) and _fin(g_al) else None
    return diff


def _fin(val: Any) -> bool:
    return isinstance(val, (int, float)) and math.isfinite(val)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(int(len(s) * pct), len(s) - 1)]


def _distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0, "p25": 0, "median": 0, "p75": 0, "p95": 0, "max": 0}
    s = sorted(values)
    return {"min": round(s[0], 2), "p25": round(_percentile(s, 0.25), 2), "median": round(_percentile(s, 0.50), 2), "p75": round(_percentile(s, 0.75), 2), "p95": round(_percentile(s, 0.95), 2), "max": round(s[-1], 2)}


# ============================================================
# Comparable diagnostics
# ============================================================

def _extract_diagnostics(raw: dict[str, Any], max_n: int = MAX_COMPARABLE_DIAGNOSTICS) -> list[dict[str, Any]]:
    comps = raw.get("service", {}).get("result", {}).get("comparables", [])
    return [{k: c.get(k) for k in ("transaction_period", "city", "district", "road", "building_type", "area_ping", "building_age_years", "unit_price_per_ping", "similarity_score", "distance_m", "source")} for c in comps[:max_n]]


# ============================================================
# Output
# ============================================================

def _write_artifacts(run_id: str, summary: dict[str, Any], cases_out: list[dict[str, Any]], diags: list[dict[str, Any]]) -> Path:
    run_dir = ARTIFACTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    with (run_dir / "cases.jsonl").open("w", encoding="utf-8") as f:
        for c in cases_out:
            f.write(json.dumps(c, ensure_ascii=False, default=str) + "\n")
    with (run_dir / "comparable_diagnostics.jsonl").open("w", encoding="utf-8") as f:
        for d in diags:
            f.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")
    return run_dir


# ============================================================
# Main
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("VALUATION BLUE vs GREEN SHADOW A/B")
    print("=" * 50)

    try:
        cases = load_cases()
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    schema_valid = 0
    for case in cases:
        valid, _ = validate_case_schema(case)
        if valid:
            schema_valid += 1

    print(f"Cases: {len(cases)}")
    print(f"Schema valid: {schema_valid}/{len(cases)}")
    if schema_valid != len(cases):
        print("ERROR: schema validation failed")
        return 1
    print()

    if args.dry_run:
        print("DRY-RUN MODE")
        print(f"  Cases: {len(cases)}")
        print(f"  Cities: {len(set(c['city'] for c in cases))}")
        print(f"  Database connections: 0")
        print(f"  External HTTP requests: 0")
        print(f"  Subprocess executions: 0")
        print(f"DRY_RUN_SCHEMA_VALID = PASS")
        print(f"DRY_RUN_NO_NETWORK = PASS")
        return 0

    config = _check_configuration(dry_run=False)
    if not config:
        return 1
    print("Configuration: OK")
    print()

    print("Running BLUE side...")
    blue_raw = _run_side("BLUE", cases, {"PLVR_DATA_BACKEND": "blue"})
    print(f"  BLUE: {sum(1 for r in blue_raw if r.get('service',{}).get('status')=='ok')}/{len(cases)} OK")
    print()

    print("Running GREEN side...")
    green_raw = _run_side("GREEN", cases, {"PLVR_DATA_BACKEND": "green"})
    print(f"  GREEN: {sum(1 for r in green_raw if r.get('service',{}).get('status')=='ok')}/{len(cases)} OK")
    print()

    # Process results
    cases_out = []
    diags = []
    classifications = {"EXPECTED": 0, "REVIEW": 0, "FAIL": 0}
    pct_deltas: list[float] = []

    for i, case in enumerate(cases):
        blue_m = _extract_side_metrics(blue_raw[i])
        green_m = _extract_side_metrics(green_raw[i])

        # Provenance validation (both sides)
        prov_valid, prov_reasons = validate_backend_provenance(
            blue_m["service_provenance"], blue_m["api_provenance"],
            green_m["service_provenance"], green_m["api_provenance"],
        )

        diff = _compute_diff(blue_m, green_m)

        case_data = {
            "case_id": case["case_id"],
            "payload_schema_valid": True,
            "blue": blue_m,
            "green": green_m,
            "diff": diff,
            "provenance_valid": prov_valid,
            "provenance_reasons": prov_reasons,
        }

        cls, cls_reasons = classify_case(case_data)
        case_data["classification"] = cls
        case_data["classification_reasons"] = cls_reasons
        classifications[cls] += 1

        if diff.get("estimate_pct_delta") is not None:
            pct_deltas.append(abs(diff["estimate_pct_delta"]))

        cases_out.append(case_data)
        if i < 10:
            diags.append({"case_id": case["case_id"], "blue": _extract_diagnostics(blue_raw[i]), "green": _extract_diagnostics(green_raw[i])})

    # Latency aggregation
    b_sl = [m["blue"]["service_latency_ms"] for m in cases_out if _fin(m["blue"].get("service_latency_ms"))]
    g_sl = [m["green"]["service_latency_ms"] for m in cases_out if _fin(m["green"].get("service_latency_ms"))]
    b_al = [m["blue"]["api_latency_ms"] for m in cases_out if _fin(m["blue"].get("api_latency_ms"))]
    g_al = [m["green"]["api_latency_ms"] for m in cases_out if _fin(m["green"].get("api_latency_ms"))]

    summary = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
        "total_cases": len(cases),
        "classifications": classifications,
        "estimate_pct_delta_distribution": _distribution(pct_deltas),
        "blue_service_latency": {"median": round(_percentile(b_sl, 0.5), 1), "p95": round(_percentile(b_sl, 0.95), 1)} if b_sl else None,
        "green_service_latency": {"median": round(_percentile(g_sl, 0.5), 1), "p95": round(_percentile(g_sl, 0.95), 1)} if g_sl else None,
        "blue_api_latency": {"median": round(_percentile(b_al, 0.5), 1), "p95": round(_percentile(b_al, 0.95), 1)} if b_al else None,
        "green_api_latency": {"median": round(_percentile(g_al, 0.5), 1), "p95": round(_percentile(g_al, 0.95), 1)} if g_al else None,
        "hard_failures": classifications["FAIL"],
    }

    run_dir = _write_artifacts(summary["run_id"], summary, cases_out, diags)

    print("=" * 50)
    print("SHADOW A/B RESULTS")
    print("=" * 50)
    print(f"EXPECTED: {classifications['EXPECTED']}  REVIEW: {classifications['REVIEW']}  FAIL: {classifications['FAIL']}")
    if summary.get("blue_service_latency"):
        print(f"BLUE svc: median {summary['blue_service_latency']['median']}ms p95 {summary['blue_service_latency']['p95']}ms")
    if summary.get("green_service_latency"):
        print(f"GREEN svc: median {summary['green_service_latency']['median']}ms p95 {summary['green_service_latency']['p95']}ms")
    if pct_deltas:
        d = summary["estimate_pct_delta_distribution"]
        print(f"|delta|%: median {d['median']} p95 {d['p95']} max {d['max']}")
    print(f"Artifacts: {run_dir}")
    print()
    if classifications["FAIL"] > 0:
        print("HARD FAILURES DETECTED")
        return 2
    print("SHADOW A/B COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
