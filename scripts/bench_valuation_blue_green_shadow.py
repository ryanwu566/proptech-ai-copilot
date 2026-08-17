#!/usr/bin/env python3
"""BLUE vs GREEN /valuation/estimate shadow A/B harness.

Compares complete valuation behavior using identical inputs against:
  A = BLUE comparables (PLVR_DATA_BACKEND=blue)
  B = Compact GREEN comparables (PLVR_DATA_BACKEND=green)

Each side runs in a SEPARATE subprocess to avoid cache/env contamination.

Required environment:
  VALUATION_DATABASE_URL       — BLUE database (existing production DB)
  COMPACT_GREEN_DATABASE_URL   — GREEN database (Compact GREEN schema)

Usage:
  python scripts/bench_valuation_blue_green_shadow.py
  python scripts/bench_valuation_blue_green_shadow.py --dry-run

Exit codes:
  0 — completed (results in output artifacts)
  1 — configuration/setup failure
  2 — hard failure detected (exceptions, contract violations)
"""

from __future__ import annotations

import argparse
import json
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

# Maximum comparables to capture per case for diagnostics
MAX_COMPARABLE_DIAGNOSTICS = 5


# ============================================================
# Configuration
# ============================================================

def _check_configuration(dry_run: bool) -> dict[str, str]:
    """Validate required environment. Never print values."""
    issues = []
    if not dry_run:
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
# Case loading
# ============================================================

def load_cases() -> list[dict[str, Any]]:
    """Load deterministic shadow test cases."""
    if not CASES_FILE.is_file():
        raise FileNotFoundError(f"Cases file not found: {CASES_FILE}")
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or len(cases) == 0:
        raise ValueError("Cases file is empty or invalid")
    # Validate required fields
    required = {"case_id", "city", "district", "road", "building_type", "area_ping", "building_age_years", "floor"}
    for i, case in enumerate(cases):
        missing = required - set(case.keys())
        if missing:
            raise ValueError(f"Case {i} missing fields: {missing}")
        if case["area_ping"] <= 0:
            raise ValueError(f"Case {i} ({case['case_id']}): area_ping must be > 0")
        if case["building_age_years"] < 0:
            raise ValueError(f"Case {i} ({case['case_id']}): building_age_years must be >= 0")
        if case["floor"] < 0:
            raise ValueError(f"Case {i} ({case['case_id']}): floor must be >= 0")
    return cases


# ============================================================
# Subprocess execution for A/B isolation
# ============================================================

_WORKER_SCRIPT = '''
"""Worker subprocess for shadow A/B — executes one side."""
import json
import os
import sys
import time

# Ensure project root is importable
sys.path.insert(0, os.environ["PROJECT_ROOT"])

def run_case(payload):
    """Execute estimate_property and capture results."""
    from services.valuation_service import estimate_property
    t0 = time.perf_counter()
    try:
        result = estimate_property(payload)
        t1 = time.perf_counter()
        return {
            "status": "ok",
            "latency_ms": round((t1 - t0) * 1000, 1),
            "result": result,
        }
    except Exception as exc:
        t1 = time.perf_counter()
        return {
            "status": "error",
            "latency_ms": round((t1 - t0) * 1000, 1),
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:200],
        }

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
    outputs.append(run_case(payload))

# Output as JSON to stdout (no secrets, no connection strings)
print(json.dumps(outputs, ensure_ascii=False, default=str))
'''


def _run_side(side: str, cases: list[dict[str, Any]], env_overrides: dict[str, str]) -> list[dict[str, Any]]:
    """Run one A/B side in a subprocess."""
    env = {**os.environ, **env_overrides, "PROJECT_ROOT": str(PROJECT_ROOT)}
    # Remove potentially conflicting vars
    env.pop("PYTHONDONTWRITEBYTECODE", None)

    proc = subprocess.run(
        [sys.executable, "-c", _WORKER_SCRIPT],
        input=json.dumps(cases, ensure_ascii=False),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
        timeout=300,  # 5 minutes max
    )
    if proc.returncode != 0:
        print(f"ERROR: {side} subprocess failed (exit {proc.returncode})")
        if proc.stderr:
            # Only show last 500 chars of stderr, no secrets
            safe_err = proc.stderr[-500:]
            # Strip any connection-string-like content
            for pattern in ["postgresql://", "postgres://", "supabase"]:
                if pattern in safe_err.lower():
                    safe_err = "[stderr redacted - may contain connection info]"
                    break
            print(f"  stderr: {safe_err}")
        return [{"status": "subprocess_error"} for _ in cases]

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(f"ERROR: {side} subprocess output is not valid JSON")
        return [{"status": "parse_error"} for _ in cases]


# ============================================================
# Metrics computation
# ============================================================

def _extract_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract comparable metrics from a single-case result."""
    if raw.get("status") != "ok":
        return {
            "status": raw.get("status", "error"),
            "error_type": raw.get("error_type"),
            "latency_ms": raw.get("latency_ms"),
        }
    result = raw.get("result", {})
    return {
        "status": "ok",
        "latency_ms": raw.get("latency_ms"),
        "valuation_status": result.get("valuation_status"),
        "source": result.get("source"),
        "estimate_total_price": result.get("estimate_total_price"),
        "estimate_unit_price_per_ping": result.get("estimate_unit_price_per_ping"),
        "confidence": result.get("confidence"),
        "confidence_score": result.get("confidence_score"),
        "estimate_level": result.get("estimate_level"),
        "comparable_count": len(result.get("comparables", [])),
        "matched_community": result.get("matched_community"),
        "price_range": result.get("price_range"),
    }


def _compute_diff(blue: dict[str, Any], green: dict[str, Any]) -> dict[str, Any]:
    """Compute comparison metrics between BLUE and GREEN results."""
    diff: dict[str, Any] = {}

    b_est = blue.get("estimate_total_price")
    g_est = green.get("estimate_total_price")

    if isinstance(b_est, (int, float)) and isinstance(g_est, (int, float)) and b_est != 0:
        diff["estimate_abs_delta"] = round(g_est - b_est, 1)
        diff["estimate_pct_delta"] = round((g_est - b_est) / b_est * 100, 2)
    else:
        diff["estimate_abs_delta"] = None
        diff["estimate_pct_delta"] = None

    b_conf = blue.get("confidence_score")
    g_conf = green.get("confidence_score")
    if isinstance(b_conf, (int, float)) and isinstance(g_conf, (int, float)):
        diff["confidence_delta"] = g_conf - b_conf
    else:
        diff["confidence_delta"] = None

    b_count = blue.get("comparable_count", 0)
    g_count = green.get("comparable_count", 0)
    diff["comparable_count_delta"] = g_count - b_count

    b_lat = blue.get("latency_ms", 0)
    g_lat = green.get("latency_ms", 0)
    if b_lat and g_lat and b_lat > 0:
        diff["latency_delta_ms"] = round(g_lat - b_lat, 1)
        diff["latency_ratio"] = round(g_lat / b_lat, 2)
    else:
        diff["latency_delta_ms"] = None
        diff["latency_ratio"] = None

    return diff


def _classify_case(blue: dict[str, Any], green: dict[str, Any], diff: dict[str, Any]) -> str:
    """Classify a case comparison result.

    Returns: EXPECTED, REVIEW, or FAIL.
    """
    # FAIL conditions
    if green.get("status") != "ok":
        return "FAIL"
    if blue.get("status") == "ok" and green.get("valuation_status") in (None, "unavailable"):
        return "FAIL"
    if green.get("source") == "mock_fallback":
        return "FAIL"
    if green.get("comparable_count", 0) == 0 and blue.get("comparable_count", 0) > 0:
        return "FAIL"

    est = green.get("estimate_total_price")
    if est is not None and (not isinstance(est, (int, float)) or est < 0):
        return "FAIL"

    # If BLUE also failed, GREEN failure is acceptable
    if blue.get("status") != "ok":
        return "EXPECTED"

    # REVIEW conditions (provisional thresholds)
    pct = diff.get("estimate_pct_delta")
    if pct is not None and abs(pct) > 20:
        return "REVIEW"

    conf_delta = diff.get("confidence_delta")
    if conf_delta is not None and conf_delta < -20:
        return "REVIEW"

    return "EXPECTED"


# ============================================================
# Comparable diagnostics
# ============================================================

def _extract_comparable_diagnostics(result: dict[str, Any], max_n: int = MAX_COMPARABLE_DIAGNOSTICS) -> list[dict[str, Any]]:
    """Extract bounded comparable details for inspection."""
    comparables = result.get("result", {}).get("comparables", [])
    diagnostics = []
    for comp in comparables[:max_n]:
        diagnostics.append({
            "transaction_period": comp.get("transaction_period"),
            "city": comp.get("city"),
            "district": comp.get("district"),
            "road": comp.get("road"),
            "building_type": comp.get("building_type"),
            "area_ping": comp.get("area_ping"),
            "building_age_years": comp.get("building_age_years"),
            "unit_price_per_ping": comp.get("unit_price_per_ping"),
            "similarity_score": comp.get("similarity_score"),
            "distance_m": comp.get("distance_m"),
            "source": comp.get("source"),
        })
    return diagnostics


# ============================================================
# Output
# ============================================================

def _write_artifacts(run_id: str, summary: dict[str, Any], cases_output: list[dict[str, Any]], diagnostics: list[dict[str, Any]]) -> Path:
    """Write structured output artifacts."""
    run_dir = ARTIFACTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
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

    # Load cases
    try:
        cases = load_cases()
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Cases loaded: {len(cases)}")
    cities = sorted(set(c["city"] for c in cases))
    types = sorted(set(c["building_type"] for c in cases))
    print(f"Cities: {len(cities)} — {', '.join(cities[:6])}{'...' if len(cities) > 6 else ''}")
    print(f"Building types: {', '.join(types)}")
    print()

    # Dry-run mode
    if args.dry_run:
        print("DRY-RUN MODE")
        print("=" * 50)
        print(f"  Cases: {len(cases)}")
        print(f"  Cities: {len(cities)}")
        print(f"  Building types: {len(types)}")
        print(f"  Cases file: {CASES_FILE}")
        print(f"  Artifacts dir: {ARTIFACTS_DIR}")
        print(f"  Would execute: BLUE subprocess + GREEN subprocess")
        print(f"  Database connections: 0 (dry-run)")
        print(f"  HTTP requests: 0")
        print()
        print("  Phases that WOULD execute:")
        print("    1. BLUE: estimate_property() x {len(cases)} cases")
        print("    2. GREEN: estimate_property() x {len(cases)} cases")
        print("    3. Metrics computation")
        print("    4. Classification (EXPECTED/REVIEW/FAIL)")
        print("    5. Artifact output")
        print()
        print("  Required env (not checked in dry-run):")
        print("    VALUATION_DATABASE_URL")
        print("    COMPACT_GREEN_DATABASE_URL")
        print()
        print("DRY-RUN PASS")
        return 0

    # Configuration check
    config = _check_configuration(dry_run=False)
    if not config:
        return 1

    print("Configuration: OK (values not printed)")
    print()

    # Run BLUE side
    print("Running BLUE side...")
    blue_results = _run_side("BLUE", cases, {"PLVR_DATA_BACKEND": "blue"})
    print(f"  BLUE completed: {sum(1 for r in blue_results if r.get('status') == 'ok')}/{len(cases)} OK")
    print()

    # Run GREEN side
    print("Running GREEN side...")
    green_results = _run_side("GREEN", cases, {"PLVR_DATA_BACKEND": "green"})
    print(f"  GREEN completed: {sum(1 for r in green_results if r.get('status') == 'ok')}/{len(cases)} OK")
    print()

    # Compute metrics
    print("Computing metrics...")
    cases_output = []
    diagnostics = []
    classifications = {"EXPECTED": 0, "REVIEW": 0, "FAIL": 0}

    for i, case in enumerate(cases):
        blue_m = _extract_metrics(blue_results[i])
        green_m = _extract_metrics(green_results[i])
        diff = _compute_diff(blue_m, green_m)
        classification = _classify_case(blue_m, green_m, diff)
        classifications[classification] += 1

        case_record = {
            "case_id": case["case_id"],
            "payload": case,
            "blue": blue_m,
            "green": green_m,
            "diff": diff,
            "classification": classification,
        }
        cases_output.append(case_record)

        # Comparable diagnostics for first N cases
        if i < 10:
            diagnostics.append({
                "case_id": case["case_id"],
                "blue_comparables": _extract_comparable_diagnostics(blue_results[i]),
                "green_comparables": _extract_comparable_diagnostics(green_results[i]),
            })

    # Summary
    blue_latencies = [r.get("latency_ms", 0) for r in blue_results if r.get("status") == "ok" and r.get("latency_ms")]
    green_latencies = [r.get("latency_ms", 0) for r in green_results if r.get("status") == "ok" and r.get("latency_ms")]

    import statistics
    summary = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
        "total_cases": len(cases),
        "blue_ok": sum(1 for r in blue_results if r.get("status") == "ok"),
        "green_ok": sum(1 for r in green_results if r.get("status") == "ok"),
        "classifications": classifications,
        "blue_latency": {
            "median_ms": round(statistics.median(blue_latencies), 1) if blue_latencies else None,
            "p95_ms": round(sorted(blue_latencies)[int(len(blue_latencies) * 0.95)], 1) if len(blue_latencies) > 1 else None,
        },
        "green_latency": {
            "median_ms": round(statistics.median(green_latencies), 1) if green_latencies else None,
            "p95_ms": round(sorted(green_latencies)[int(len(green_latencies) * 0.95)], 1) if len(green_latencies) > 1 else None,
        },
        "hard_failures": classifications["FAIL"],
    }

    # Write artifacts
    run_dir = _write_artifacts(summary["run_id"], summary, cases_output, diagnostics)

    # Console summary
    print()
    print("=" * 50)
    print("SHADOW A/B RESULTS")
    print("=" * 50)
    print(f"Total cases: {len(cases)}")
    print(f"BLUE OK: {summary['blue_ok']}/{len(cases)}")
    print(f"GREEN OK: {summary['green_ok']}/{len(cases)}")
    print()
    print(f"EXPECTED: {classifications['EXPECTED']}")
    print(f"REVIEW:   {classifications['REVIEW']}")
    print(f"FAIL:     {classifications['FAIL']}")
    print()
    if summary["blue_latency"]["median_ms"]:
        print(f"BLUE latency:  median {summary['blue_latency']['median_ms']} ms, p95 {summary['blue_latency']['p95_ms']} ms")
    if summary["green_latency"]["median_ms"]:
        print(f"GREEN latency: median {summary['green_latency']['median_ms']} ms, p95 {summary['green_latency']['p95_ms']} ms")
    print()
    print(f"Artifacts: {run_dir}")
    print()

    if classifications["FAIL"] > 0:
        print("HARD FAILURES DETECTED — review cases.jsonl for details")
        return 2

    print("SHADOW A/B COMPLETE — no hard failures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
