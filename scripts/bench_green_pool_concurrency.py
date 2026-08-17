#!/usr/bin/env python3
"""Compact GREEN pool concurrency benchmark for Render production validation.

Measures pooled query_green_comparables() under concurrent load.

Phase A: concurrency=3, 90 calls (matches pool max_size=3)
Phase B: concurrency=6, 60 calls (intentional overload observation)

Required environment:
    COMPACT_GREEN_DATABASE_URL  — GREEN database connection

Not required:
    VALUATION_DATABASE_URL, DATABASE_URL, PLVR_DATA_BACKEND

Exit codes:
    0 — Phase A hard gate PASS + Phase B correctness PASS
    1 — setup/configuration error
    2 — performance or correctness gate FAIL
"""

from __future__ import annotations

import os
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any


def main() -> int:
    # ----------------------------------------------------------------
    # Configuration check
    # ----------------------------------------------------------------
    if not os.getenv("COMPACT_GREEN_DATABASE_URL", "").strip():
        print("ERROR: COMPACT_GREEN_DATABASE_URL is not set.")
        return 1

    # ----------------------------------------------------------------
    # Import adapter
    # ----------------------------------------------------------------
    try:
        from services.compact_green_query import (
            close_green_pool,
            decode_period,
            get_geography_cache,
            get_max_period_code,
            query_green_comparables,
            reset_geography_cache,
        )
    except ImportError as exc:
        print(f"ERROR: Cannot import compact_green_query: {exc}")
        return 1

    # ----------------------------------------------------------------
    # Warm caches
    # ----------------------------------------------------------------
    print("COMPACT GREEN POOL CONCURRENCY BENCHMARK")
    print("=" * 50)

    reset_geography_cache()

    try:
        cache = get_geography_cache()
    except Exception as exc:
        print(f"ERROR: Geography cache load failed: {type(exc).__name__}")
        return 1

    try:
        max_pc = get_max_period_code()
    except Exception as exc:
        print(f"ERROR: Max period code unavailable: {type(exc).__name__}")
        return 1

    geography_entries = len(cache)
    max_period = decode_period(max_pc)

    print(f"geography_entries = {geography_entries}")
    print(f"max_period_code = {max_pc}")
    print(f"max_period = {max_period}")

    if geography_entries != 323:
        print(f"WARNING: Expected 323 geography entries, got {geography_entries}")
    if max_pc != 318:
        print(f"WARNING: Expected max_period_code 318, got {max_pc}")

    # ----------------------------------------------------------------
    # Build test cases
    # ----------------------------------------------------------------
    target_cities = ["南投縣", "嘉義縣", "基隆市", "宜蘭縣", "屏東縣", "彰化縣"]
    all_districts = list(cache.keys())

    test_cases: list[dict[str, Any]] = []
    for city in target_cities:
        districts_in_city = sorted(d for c, d in all_districts if c == city)
        if districts_in_city:
            test_cases.append({
                "city": city,
                "district": districts_in_city[0],
                "road": "",
                "building_type": "",
                "area_ping": 30.0,
                "building_age_years": 15.0,
            })

    if len(test_cases) < 5:
        print(f"ERROR: Only found {len(test_cases)} valid cases (need >= 5)")
        return 1

    print(f"cases = {len(test_cases)}")
    print()

    # ----------------------------------------------------------------
    # Pool warmup: concurrent calls to establish up to max_size=3
    # ----------------------------------------------------------------
    print("Pool warmup (concurrent, unmeasured)...")
    with ThreadPoolExecutor(max_workers=3) as warmup_pool:
        warmup_futures = [
            warmup_pool.submit(query_green_comparables, test_cases[i % len(test_cases)])
            for i in range(3)
        ]
        for f in as_completed(warmup_futures):
            try:
                rows = f.result(timeout=15)
                print(f"  warmup: {len(rows)} rows")
            except Exception as exc:
                print(f"ERROR: Pool warmup failed: {type(exc).__name__}")
                return 1
    print()

    # ----------------------------------------------------------------
    # Phase A: concurrency=3, 90 calls
    # ----------------------------------------------------------------
    print("=" * 50)
    print("PHASE A: concurrency=3, 90 calls, seed=42")
    print("=" * 50)

    result_a = _run_phase(
        query_fn=query_green_comparables,
        test_cases=test_cases,
        concurrency=3,
        total_calls=90,
        seed=42,
    )
    _print_results(result_a)

    phase_a_pass = (
        result_a["samples"] >= 90
        and result_a["errors"] == 0
        and result_a["timeouts"] == 0
        and result_a["empty"] == 0
        and result_a["p95"] <= 300
    )
    print(f"PASS_PHASE_A = {'PASS' if phase_a_pass else 'FAIL'}")
    if not phase_a_pass:
        reasons = []
        if result_a["samples"] < 90:
            reasons.append(f"samples {result_a['samples']} < 90")
        if result_a["errors"] > 0:
            reasons.append(f"errors {result_a['errors']} > 0")
        if result_a["timeouts"] > 0:
            reasons.append(f"timeouts {result_a['timeouts']} > 0")
        if result_a["empty"] > 0:
            reasons.append(f"empty {result_a['empty']} > 0")
        if result_a["p95"] > 300:
            reasons.append(f"p95 {result_a['p95']:.1f}ms > 300ms")
        print(f"FAIL_REASONS: {'; '.join(reasons)}")
    print()

    # ----------------------------------------------------------------
    # Phase B: concurrency=6, 60 calls (overload observation)
    # ----------------------------------------------------------------
    print("=" * 50)
    print("PHASE B: concurrency=6, 60 calls, seed=43 (overload observation)")
    print("=" * 50)

    result_b = _run_phase(
        query_fn=query_green_comparables,
        test_cases=test_cases,
        concurrency=6,
        total_calls=60,
        seed=43,
    )
    _print_results(result_b)

    phase_b_correctness = (
        result_b["errors"] == 0
        and result_b["timeouts"] == 0
        and result_b["empty"] == 0
    )
    print(f"PASS_PHASE_B_CORRECTNESS = {'PASS' if phase_b_correctness else 'FAIL'}")
    if not phase_b_correctness:
        reasons = []
        if result_b["errors"] > 0:
            reasons.append(f"errors {result_b['errors']} > 0")
        if result_b["timeouts"] > 0:
            reasons.append(f"timeouts {result_b['timeouts']} > 0")
        if result_b["empty"] > 0:
            reasons.append(f"empty {result_b['empty']} > 0")
        print(f"FAIL_REASONS: {'; '.join(reasons)}")
    print()

    # ----------------------------------------------------------------
    # Pool statistics (if available)
    # ----------------------------------------------------------------
    try:
        from services.compact_green_query import _pool
        if _pool is not None and hasattr(_pool, "get_stats"):
            stats = _pool.get_stats()
            print("Pool stats:", {k: v for k, v in stats.items() if not any(s in str(k).lower() for s in ["dsn", "url", "pass", "secret"])})
            print()
    except Exception:
        pass

    # ----------------------------------------------------------------
    # Final verdict
    # ----------------------------------------------------------------
    overall = phase_a_pass and phase_b_correctness
    print("=" * 50)
    print(f"OVERALL = {'PASS' if overall else 'FAIL'}")
    print("=" * 50)

    return 0 if overall else 2


def _run_phase(
    query_fn,
    test_cases: list[dict[str, Any]],
    concurrency: int,
    total_calls: int,
    seed: int,
) -> dict[str, Any]:
    """Run a concurrent benchmark phase and return metrics."""
    random.seed(seed)
    schedule = [random.choice(test_cases) for _ in range(total_calls)]

    durations_ms: list[float] = []
    errors = 0
    timeouts = 0
    empty = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for payload in schedule:
            futures.append(executor.submit(_timed_query, query_fn, payload))

        for f in as_completed(futures):
            try:
                elapsed, row_count = f.result(timeout=30)
                durations_ms.append(elapsed)
                if row_count == 0:
                    empty += 1
            except TimeoutError:
                timeouts += 1
            except Exception:
                errors += 1

    durations_ms.sort()
    n = len(durations_ms)

    if n == 0:
        return {"samples": 0, "median": 0, "p95": 0, "p99": 0, "max": 0,
                "over_300": 0, "over_500": 0, "over_1000": 0,
                "errors": errors, "timeouts": timeouts, "empty": empty}

    return {
        "samples": n,
        "median": statistics.median(durations_ms),
        "p95": durations_ms[int(n * 0.95)],
        "p99": durations_ms[int(n * 0.99)],
        "max": max(durations_ms),
        "over_300": sum(1 for d in durations_ms if d > 300),
        "over_500": sum(1 for d in durations_ms if d > 500),
        "over_1000": sum(1 for d in durations_ms if d > 1000),
        "errors": errors,
        "timeouts": timeouts,
        "empty": empty,
    }


def _timed_query(query_fn, payload: dict[str, Any]) -> tuple[float, int]:
    """Execute one query and return (elapsed_ms, row_count)."""
    t0 = time.perf_counter()
    rows = query_fn(payload)
    t1 = time.perf_counter()
    return (t1 - t0) * 1000, len(rows)


def _print_results(results: dict[str, Any]) -> None:
    """Print benchmark results in standard format."""
    print(f"samples = {results['samples']}")
    print(f"median_ms = {results['median']:.1f}")
    print(f"p95_ms = {results['p95']:.1f}")
    print(f"p99_ms = {results['p99']:.1f}")
    print(f"max_ms = {results['max']:.1f}")
    print()
    print(f"over_300ms = {results['over_300']}")
    print(f"over_500ms = {results['over_500']}")
    print(f"over_1000ms = {results['over_1000']}")
    print()
    print(f"errors = {results['errors']}")
    print(f"timeouts = {results['timeouts']}")
    print(f"empty_results = {results['empty']}")
    print()


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        # Explicitly close the GREEN connection pool to avoid
        # PythonFinalizationError from ConnectionPool.__del__ at shutdown.
        try:
            from services.compact_green_query import close_green_pool
            close_green_pool()
        except Exception:
            pass
