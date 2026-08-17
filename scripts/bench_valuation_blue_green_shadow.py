#!/usr/bin/env python3
"""BLUE vs GREEN /valuation/estimate shadow A/B harness.

Compares complete valuation behavior using identical inputs against:
  A = BLUE comparables (PLVR_DATA_BACKEND=blue)
  B = Compact GREEN comparables (PLVR_DATA_BACKEND=green)

Measures TWO layers per side:
  SERVICE: estimate_property(payload) latency
  API: full POST /valuation/estimate via in-process ASGI TestClient

Each side runs in a SEPARATE subprocess for env/cache isolation.

Required environment:
  VALUATION_DATABASE_URL       — BLUE database (existing production DB)
  COMPACT_GREEN_DATABASE_URL   — GREEN database (Compact GREEN schema)

Usage:
  python scripts/bench_valuation_blue_green_shadow.py --dry-run
  python scripts/bench_valuation_blue_green_shadow.py

Exit codes:
  0 — completed (results in output artifacts)
  1 — configuration/setup failure
  2 — hard failure detected
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

# Pydantic-equivalent schema constraints for ValuationRequest
_SCHEMA_REQUIRED = {"city", "district", "road", "building_type", "area_ping", "building_age_years", "floor"}
_SCHEMA_OPTIONAL = {"lat", "lng", "address_text", "case_id"}

# Required response contract fields for a successful valuation
_RESPONSE_REQUIRED_FIELDS = {
    "source", "data_status", "estimate_level", "confidence", "confidence_score",
    "comparables", "methodology", "disclaimer",
}
_RESPONSE_NUMERIC_FIELDS = {
    "estimate_total_price", "estimate_unit_price_per_ping", "confidence_score",
}


# ============================================================
# Configuration
# ============================================================

def _check_configuration(dry_run: bool) -> dict[str, str]:
    """Validate required environment. Never print values."""
    if dry_run:
        return {"status": "configured"}
    issues = []
    if not os.getenv("VALUATION_DATABASE_URL", "").strip():
        issues.append("VALUATION_DATABASE_URL is not set (required for BLUE)")
    if not os.getenv("COMPACT_GREEN_DATABASE_URL", "").strip():
        issues.append("COMPACT_GREEN_DATABASE_URL is not set (required for GREEN)")
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return {}
    return {"status": "configured"}


# ============================================================
# Schema validation
# ============================================================

def validate_case_schema(case: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a case against the real ValuationRequest schema."""
    errors = []
    missing = _SCHEMA_REQUIRED - set(case.keys())
    if missing:
        errors.append(f"missing fields: {missing}")
    if not isinstance(case.get("city"), str) or not case.get("city", "").strip():
        errors.append("city must be non-empty string")
    if not isinstance(case.get("district"), str) or not case.get("district", "").strip():
        errors.append("district must be non-empty string")
    if not isinstance(case.get("road"), str):
        errors.append("road must be string")
    if not isinstance(case.get("building_type"), str) or not case.get("building_type", "").strip():
        errors.append("building_type must be non-empty string")
    area = case.get("area_ping")
    if not isinstance(area, (int, float)) or area <= 0:
        errors.append("area_ping must be > 0")
    age = case.get("building_age_years")
    if not isinstance(age, (int, float)) or age < 0:
        errors.append("building_age_years must be >= 0")
    floor_val = case.get("floor")
    if not isinstance(floor_val, int) or floor_val < 0:
        errors.append("floor must be int >= 0")
    return (len(errors) == 0, errors)


# ============================================================
# Case loading
# ============================================================

def load_cases() -> list[dict[str, Any]]:
    """Load deterministic shadow test cases."""
    if not CASES_FILE.is_file():
        raise FileNotFoundError(f"Cases file not found: {CASES_FILE}")
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or len(cases) == 0:
        raise ValueError("Cases file is empty or invalid")
    ids = [c.get("case_id") for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case_id found")
    return cases


# ============================================================
# Response contract validation
# ============================================================

def validate_response_contract(response: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate response against canonical valuation contract."""
    errors = []
    missing = _RESPONSE_REQUIRED_FIELDS - set(response.keys())
    if missing:
        errors.append(f"missing response fields: {missing}")
    for field in _RESPONSE_NUMERIC_FIELDS:
        val = response.get(field)
        if val is not None:
            if not isinstance(val, (int, float)):
                errors.append(f"{field} is not numeric: {type(val).__name__}")
            elif not math.isfinite(val):
                errors.append(f"{field} is non-finite: {val}")
            elif field in ("estimate_total_price", "estimate_unit_price_per_ping") and val < 0:
                errors.append(f"{field} is negative: {val}")
    # Price range check
    price_range = response.get("price_range")
    if isinstance(price_range, dict):
        for k in ("low", "mid", "high"):
            v = price_range.get(k)
            if v is not None and isinstance(v, (int, float)):
                if not math.isfinite(v):
                    errors.append(f"price_range.{k} non-finite: {v}")
    # Comparables must be list
    comps = response.get("comparables")
    if comps is not None and not isinstance(comps, list):
        errors.append(f"comparables is not a list: {type(comps).__name__}")
    return (len(errors) == 0, errors)


# ============================================================
# Subprocess worker script
# ============================================================

_WORKER_SCRIPT = r'''
import json, os, sys, time, math
sys.path.insert(0, os.environ["PROJECT_ROOT"])

# Provenance instrumentation — counts actual comparables calls
_blue_comparables_calls = 0
_green_comparables_calls = 0

def _instrument_provenance():
    global _blue_comparables_calls, _green_comparables_calls
    from services.valuation_providers.postgres_provider import PostgresValuationProvider
    _orig_blue = PostgresValuationProvider.query_comparables
    def _wrapped_blue(self, *args, **kwargs):
        global _blue_comparables_calls
        _blue_comparables_calls += 1
        return _orig_blue(self, *args, **kwargs)
    PostgresValuationProvider.query_comparables = _wrapped_blue

    import services.compact_green_query as gcq
    _orig_green = gcq.query_green_comparables
    def _wrapped_green(*args, **kwargs):
        global _green_comparables_calls
        _green_comparables_calls += 1
        return _orig_green(*args, **kwargs)
    gcq.query_green_comparables = _wrapped_green

_instrument_provenance()

from fastapi.testclient import TestClient
from backend.api_main import app

client = TestClient(app)

cases = json.loads(sys.stdin.read())
outputs = []

for case in cases:
    payload = {
        "city": case["city"],
        "district": case["district"],
        "road": case["road"],
        "building_type": case["building_type"],
        "area_ping": case["area_ping"],
        "building_age_years": case["building_age_years"],
        "floor": case["floor"],
    }
    if case.get("lat") is not None:
        payload["lat"] = case["lat"]
    if case.get("lng") is not None:
        payload["lng"] = case["lng"]
    if case.get("address_text"):
        payload["address_text"] = case["address_text"]

    # SERVICE layer
    from services.valuation_service import estimate_property
    svc_t0 = time.perf_counter()
    try:
        svc_result = estimate_property(payload)
        svc_t1 = time.perf_counter()
        svc_out = {"status": "ok", "latency_ms": round((svc_t1 - svc_t0) * 1000, 1), "result": svc_result}
    except Exception as exc:
        svc_t1 = time.perf_counter()
        svc_out = {"status": "error", "latency_ms": round((svc_t1 - svc_t0) * 1000, 1), "error_type": type(exc).__name__}

    # API layer
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

    outputs.append({
        "service": svc_out,
        "api": api_out,
        "provenance": {
            "blue_comparables_calls": _blue_comparables_calls,
            "green_comparables_calls": _green_comparables_calls,
        },
    })
    # Reset per-case provenance
    _blue_comparables_calls = 0
    _green_comparables_calls = 0

print(json.dumps(outputs, ensure_ascii=False, default=str))
'''


def _run_side(side: str, cases: list[dict[str, Any]], env_overrides: dict[str, str]) -> list[dict[str, Any]]:
    """Run one A/B side in a subprocess."""
    env = {**os.environ, **env_overrides, "PROJECT_ROOT": str(PROJECT_ROOT)}
    proc = subprocess.run(
        [sys.executable, "-c", _WORKER_SCRIPT],
        input=json.dumps(cases, ensure_ascii=False),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
        timeout=600,
    )
    if proc.returncode != 0:
        print(f"ERROR: {side} subprocess failed (exit {proc.returncode})")
        stderr = proc.stderr[-500:] if proc.stderr else ""
        for secret_pat in ["postgresql://", "postgres://", "supabase"]:
            if secret_pat in stderr.lower():
                stderr = "[stderr redacted]"
                break
        if stderr:
            print(f"  stderr: {stderr}")
        return [{"service": {"status": "subprocess_error"}, "api": {"status": "subprocess_error"}, "provenance": {}} for _ in cases]
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(f"ERROR: {side} subprocess output is not valid JSON")
        return [{"service": {"status": "parse_error"}, "api": {"status": "parse_error"}, "provenance": {}} for _ in cases]


# ============================================================
# Metrics
# ============================================================

def _extract_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract metrics from one side's result for one case."""
    svc = raw.get("service", {})
    api = raw.get("api", {})
    prov = raw.get("provenance", {})

    svc_result = svc.get("result", {}) if svc.get("status") == "ok" else {}
    api_result = api.get("result", {}) if api.get("status") == "ok" else {}

    return {
        "service_status": svc.get("status"),
        "api_status": api.get("status"),
        "api_http_status": api.get("http_status"),
        "service_latency_ms": svc.get("latency_ms"),
        "api_latency_ms": api.get("latency_ms"),
        "valuation_status": svc_result.get("valuation_status"),
        "source": svc_result.get("source"),
        "estimate_total_price": svc_result.get("estimate_total_price"),
        "estimate_unit_price_per_ping": svc_result.get("estimate_unit_price_per_ping"),
        "confidence": svc_result.get("confidence"),
        "confidence_score": svc_result.get("confidence_score"),
        "estimate_level": svc_result.get("estimate_level"),
        "comparable_count": len(svc_result.get("comparables", [])),
        "price_range": svc_result.get("price_range"),
        "blue_comparables_calls": prov.get("blue_comparables_calls", 0),
        "green_comparables_calls": prov.get("green_comparables_calls", 0),
    }


def _compute_diff(blue: dict[str, Any], green: dict[str, Any]) -> dict[str, Any]:
    """Compute comparison metrics."""
    diff: dict[str, Any] = {}
    b_est = blue.get("estimate_total_price")
    g_est = green.get("estimate_total_price")
    if _is_valid_number(b_est) and _is_valid_number(g_est) and b_est != 0:
        diff["estimate_abs_delta"] = round(g_est - b_est, 1)
        diff["estimate_pct_delta"] = round((g_est - b_est) / b_est * 100, 2)
    else:
        diff["estimate_abs_delta"] = None
        diff["estimate_pct_delta"] = None
    b_conf = blue.get("confidence_score")
    g_conf = green.get("confidence_score")
    if _is_valid_number(b_conf) and _is_valid_number(g_conf):
        diff["confidence_delta"] = g_conf - b_conf
    else:
        diff["confidence_delta"] = None
    diff["comparable_count_delta"] = (green.get("comparable_count") or 0) - (blue.get("comparable_count") or 0)
    b_slat = blue.get("service_latency_ms")
    g_slat = green.get("service_latency_ms")
    diff["service_latency_delta"] = round(g_slat - b_slat, 1) if _is_valid_number(b_slat) and _is_valid_number(g_slat) else None
    b_alat = blue.get("api_latency_ms")
    g_alat = green.get("api_latency_ms")
    diff["api_latency_delta"] = round(g_alat - b_alat, 1) if _is_valid_number(b_alat) and _is_valid_number(g_alat) else None
    return diff


def _is_valid_number(val: Any) -> bool:
    return isinstance(val, (int, float)) and math.isfinite(val)


def classify_case(blue: dict[str, Any], green: dict[str, Any], diff: dict[str, Any], expected_side: str) -> tuple[str, list[str]]:
    """Classify a case. Returns (classification, reasons)."""
    reasons: list[str] = []

    # Hard failures
    if blue.get("service_status") != "ok":
        reasons.append("BLUE service exception")
        return ("FAIL", reasons)
    if green.get("service_status") != "ok":
        reasons.append("GREEN service exception")
        return ("FAIL", reasons)

    # Provenance check
    if expected_side == "BLUE":
        if blue.get("green_comparables_calls", 0) != 0:
            reasons.append("BLUE side called GREEN comparables")
            return ("FAIL", reasons)
    elif expected_side == "GREEN":
        if green.get("blue_comparables_calls", 0) != 0:
            reasons.append("GREEN side called BLUE comparables")
            return ("FAIL", reasons)
        if green.get("green_comparables_calls", 0) == 0:
            reasons.append("GREEN side did not call GREEN comparables")
            return ("FAIL", reasons)

    # Response contract
    g_est = green.get("estimate_total_price")
    if g_est is not None and isinstance(g_est, (int, float)):
        if not math.isfinite(g_est):
            reasons.append(f"GREEN estimate non-finite: {g_est}")
            return ("FAIL", reasons)
        if g_est < 0:
            reasons.append(f"GREEN estimate negative: {g_est}")
            return ("FAIL", reasons)

    # Source check
    if green.get("source") == "mock_fallback":
        reasons.append("GREEN used mock_fallback source")
        return ("FAIL", reasons)

    # Zero comparables when BLUE has data
    if (green.get("comparable_count") or 0) == 0 and (blue.get("comparable_count") or 0) > 0:
        if green.get("valuation_status") not in ("unavailable", "no_data"):
            reasons.append("GREEN zero comparables when BLUE has data")
            return ("FAIL", reasons)

    # GREEN unavailable when BLUE is available
    if blue.get("valuation_status") in ("available", "demo") and green.get("valuation_status") == "unavailable":
        reasons.append("GREEN unavailable when BLUE available")
        return ("FAIL", reasons)

    # REVIEW: large estimate delta
    pct = diff.get("estimate_pct_delta")
    if pct is not None and abs(pct) > 20:
        reasons.append(f"estimate delta {pct:.1f}% > 20%")
        return ("REVIEW", reasons)

    # REVIEW: large confidence drop
    conf_delta = diff.get("confidence_delta")
    if conf_delta is not None and conf_delta < -20:
        reasons.append(f"confidence delta {conf_delta} < -20")
        return ("REVIEW", reasons)

    reasons.append("within expected bounds")
    return ("EXPECTED", reasons)


# ============================================================
# Comparable diagnostics
# ============================================================

def _extract_comparable_diagnostics(raw: dict[str, Any], max_n: int = MAX_COMPARABLE_DIAGNOSTICS) -> list[dict[str, Any]]:
    comparables = raw.get("service", {}).get("result", {}).get("comparables", [])
    return [{
        "transaction_period": c.get("transaction_period"),
        "city": c.get("city"), "district": c.get("district"), "road": c.get("road"),
        "building_type": c.get("building_type"), "area_ping": c.get("area_ping"),
        "building_age_years": c.get("building_age_years"),
        "unit_price_per_ping": c.get("unit_price_per_ping"),
        "similarity_score": c.get("similarity_score"),
        "distance_m": c.get("distance_m"), "source": c.get("source"),
    } for c in comparables[:max_n]]


# ============================================================
# Statistics helpers
# ============================================================

def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(len(s) * pct)
    return s[min(idx, len(s) - 1)]


def _distribution(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0, "p25": 0, "median": 0, "p75": 0, "p95": 0, "max": 0}
    s = sorted(values)
    return {
        "min": round(s[0], 2),
        "p25": round(_percentile(s, 0.25), 2),
        "median": round(_percentile(s, 0.50), 2),
        "p75": round(_percentile(s, 0.75), 2),
        "p95": round(_percentile(s, 0.95), 2),
        "max": round(s[-1], 2),
    }


# ============================================================
# Output
# ============================================================

def _write_artifacts(run_id: str, summary: dict[str, Any], cases_output: list[dict[str, Any]], diagnostics: list[dict[str, Any]]) -> Path:
    run_dir = ARTIFACTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    with (run_dir / "cases.jsonl").open("w", encoding="utf-8") as f:
        for case in cases_output:
            f.write(json.dumps(case, ensure_ascii=False, default=str) + "\n")
    with (run_dir / "comparable_diagnostics.jsonl").open("w", encoding="utf-8") as f:
        for diag in diagnostics:
            f.write(json.dumps(diag, ensure_ascii=False, default=str) + "\n")
    return run_dir


# ============================================================
# Main
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="BLUE vs GREEN valuation shadow A/B")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup without DB connections")
    args = parser.parse_args()

    print("VALUATION BLUE vs GREEN SHADOW A/B")
    print("=" * 50)

    # Load and validate cases
    try:
        cases = load_cases()
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    # Schema validation
    schema_valid = 0
    schema_errors: list[str] = []
    for case in cases:
        valid, errs = validate_case_schema(case)
        if valid:
            schema_valid += 1
        else:
            schema_errors.extend([f"{case.get('case_id')}: {e}" for e in errs])

    print(f"Cases loaded: {len(cases)}")
    print(f"Schema valid: {schema_valid}/{len(cases)}")
    cities = sorted(set(c["city"] for c in cases))
    types = sorted(set(c["building_type"] for c in cases))
    print(f"Cities: {len(cities)}")
    print(f"Building types: {', '.join(types)}")

    if schema_valid != len(cases):
        print(f"ERROR: Schema validation failed for {len(cases) - schema_valid} cases")
        for err in schema_errors[:5]:
            print(f"  {err}")
        return 1
    print()

    # Dry-run
    if args.dry_run:
        print("DRY-RUN MODE")
        print("=" * 50)
        print(f"  Cases: {len(cases)}")
        print(f"  Cities: {len(cities)}")
        print(f"  Building types: {len(types)}")
        print(f"  Artifacts dir: {ARTIFACTS_DIR}")
        print(f"  Database connections: 0")
        print(f"  External HTTP requests: 0")
        print(f"  Subprocess executions: 0")
        print()
        print("  Phases that WOULD execute:")
        print(f"    1. BLUE: estimate_property + API x {len(cases)} cases")
        print(f"    2. GREEN: estimate_property + API x {len(cases)} cases")
        print("    3. Metrics + contract validation")
        print("    4. Classification (EXPECTED/REVIEW/FAIL)")
        print("    5. Artifact output")
        print()
        print(f"DRY_RUN_SCHEMA_VALID = PASS")
        print(f"DRY_RUN_NO_NETWORK = PASS")
        return 0

    # Real execution configuration
    config = _check_configuration(dry_run=False)
    if not config:
        return 1
    print("Configuration: OK (values not printed)")
    print()

    # Run sides
    print("Running BLUE side...")
    blue_results = _run_side("BLUE", cases, {"PLVR_DATA_BACKEND": "blue"})
    blue_ok = sum(1 for r in blue_results if r.get("service", {}).get("status") == "ok")
    print(f"  BLUE completed: {blue_ok}/{len(cases)} OK")
    print()

    print("Running GREEN side...")
    green_results = _run_side("GREEN", cases, {"PLVR_DATA_BACKEND": "green"})
    green_ok = sum(1 for r in green_results if r.get("service", {}).get("status") == "ok")
    print(f"  GREEN completed: {green_ok}/{len(cases)} OK")
    print()

    # Compute metrics and classify
    cases_output = []
    diagnostics = []
    classifications = {"EXPECTED": 0, "REVIEW": 0, "FAIL": 0}
    pct_deltas: list[float] = []

    for i, case in enumerate(cases):
        blue_m = _extract_metrics(blue_results[i])
        green_m = _extract_metrics(green_results[i])
        diff = _compute_diff(blue_m, green_m)

        # Contract validation
        blue_contract_valid, blue_contract_errors = (True, [])
        green_contract_valid, green_contract_errors = (True, [])
        if blue_m.get("service_status") == "ok":
            svc_result = blue_results[i].get("service", {}).get("result", {})
            blue_contract_valid, blue_contract_errors = validate_response_contract(svc_result)
        if green_m.get("service_status") == "ok":
            svc_result = green_results[i].get("service", {}).get("result", {})
            green_contract_valid, green_contract_errors = validate_response_contract(svc_result)

        classification, class_reasons = classify_case(blue_m, green_m, diff, expected_side="GREEN")

        # Contract failure overrides
        if not green_contract_valid:
            classification = "FAIL"
            class_reasons = [f"GREEN contract invalid: {green_contract_errors[:3]}"]

        classifications[classification] += 1

        if diff.get("estimate_pct_delta") is not None:
            pct_deltas.append(abs(diff["estimate_pct_delta"]))

        case_record = {
            "case_id": case["case_id"],
            "payload_schema_valid": True,
            "blue": {**blue_m, "contract_valid": blue_contract_valid},
            "green": {**green_m, "contract_valid": green_contract_valid},
            "diff": diff,
            "classification": classification,
            "classification_reasons": class_reasons,
        }
        cases_output.append(case_record)

        if i < 10:
            diagnostics.append({
                "case_id": case["case_id"],
                "blue_comparables": _extract_comparable_diagnostics(blue_results[i]),
                "green_comparables": _extract_comparable_diagnostics(green_results[i]),
                "blue_provenance": blue_results[i].get("provenance", {}),
                "green_provenance": green_results[i].get("provenance", {}),
            })

    # Latency aggregation
    blue_svc_lats = [m["blue"]["service_latency_ms"] for m in cases_output if _is_valid_number(m["blue"].get("service_latency_ms"))]
    green_svc_lats = [m["green"]["service_latency_ms"] for m in cases_output if _is_valid_number(m["green"].get("service_latency_ms"))]
    blue_api_lats = [m["blue"]["api_latency_ms"] for m in cases_output if _is_valid_number(m["blue"].get("api_latency_ms"))]
    green_api_lats = [m["green"]["api_latency_ms"] for m in cases_output if _is_valid_number(m["green"].get("api_latency_ms"))]

    summary = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
        "total_cases": len(cases),
        "blue_ok": blue_ok,
        "green_ok": green_ok,
        "classifications": classifications,
        "estimate_pct_delta_distribution": _distribution(pct_deltas),
        "blue_service_latency": {"median": round(_percentile(blue_svc_lats, 0.5), 1), "p95": round(_percentile(blue_svc_lats, 0.95), 1)} if blue_svc_lats else None,
        "green_service_latency": {"median": round(_percentile(green_svc_lats, 0.5), 1), "p95": round(_percentile(green_svc_lats, 0.95), 1)} if green_svc_lats else None,
        "blue_api_latency": {"median": round(_percentile(blue_api_lats, 0.5), 1), "p95": round(_percentile(blue_api_lats, 0.95), 1)} if blue_api_lats else None,
        "green_api_latency": {"median": round(_percentile(green_api_lats, 0.5), 1), "p95": round(_percentile(green_api_lats, 0.95), 1)} if green_api_lats else None,
        "hard_failures": classifications["FAIL"],
    }

    run_dir = _write_artifacts(summary["run_id"], summary, cases_output, diagnostics)

    # Console summary
    print("=" * 50)
    print("SHADOW A/B RESULTS")
    print("=" * 50)
    print(f"BLUE OK: {blue_ok}/{len(cases)}  GREEN OK: {green_ok}/{len(cases)}")
    print(f"EXPECTED: {classifications['EXPECTED']}  REVIEW: {classifications['REVIEW']}  FAIL: {classifications['FAIL']}")
    if summary.get("blue_service_latency"):
        print(f"BLUE service: median {summary['blue_service_latency']['median']} ms, p95 {summary['blue_service_latency']['p95']} ms")
    if summary.get("green_service_latency"):
        print(f"GREEN service: median {summary['green_service_latency']['median']} ms, p95 {summary['green_service_latency']['p95']} ms")
    if summary.get("blue_api_latency"):
        print(f"BLUE API: median {summary['blue_api_latency']['median']} ms, p95 {summary['blue_api_latency']['p95']} ms")
    if summary.get("green_api_latency"):
        print(f"GREEN API: median {summary['green_api_latency']['median']} ms, p95 {summary['green_api_latency']['p95']} ms")
    if pct_deltas:
        dist = summary["estimate_pct_delta_distribution"]
        print(f"Estimate |delta|%: median {dist['median']}, p95 {dist['p95']}, max {dist['max']}")
    print(f"Artifacts: {run_dir}")
    print()

    if classifications["FAIL"] > 0:
        print("HARD FAILURES DETECTED")
        return 2
    print("SHADOW A/B COMPLETE — no hard failures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
