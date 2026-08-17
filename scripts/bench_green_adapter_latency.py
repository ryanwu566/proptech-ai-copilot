#!/usr/bin/env python3
"""Compact GREEN FINAL Render benchmark gate — single entry point.

Executes ALL benchmark phases sequentially:
1. GREEN configuration/geography validation
2. Sequential pool warmup (unmeasured)
3. Sequential 120-call benchmark (p95 <= 300ms hard gate)
4. Concurrency=3 warmup (unmeasured)
5. Concurrency=3 / 90 measured calls (p95 <= 300ms hard gate)
6. Concurrency=6 / 60 measured calls (correctness only)
7. Explicit pool cleanup
8. Final consolidated summary

Required environment:
    COMPACT_GREEN_DATABASE_URL  — GREEN database connection

Not required:
    VALUATION_DATABASE_URL, DATABASE_URL, PLVR_DATA_BACKEND

Exit codes:
    0 — benchmark completed (FINAL_GATE result printed in logs)
    1 — setup/configuration failure (benchmarking impossible)
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
    # ================================================================
    # Configuration check
    # ================================================================
    if not os.getenv("COMPACT_GREEN_DATABASE_URL", "").strip():
        print("ERROR: COMPACT_GREEN_DATABASE_URL is not set.")
        return 1

    # ================================================================
    # Import adapter
    # ================================================================
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

    # ================================================================
    # Phase 0: Geography/period validation
    # ================================================================
    print("COMPACT GREEN FINAL RENDER GATE")
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
    print()

    # ================================================================
    # Build test cases
    # ================================================================
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

    # ================================================================
    # Sequential warmup (unmeasured)
    # ================================================================
    print("Sequential pool warmup (unmeasured)...")
    try:
        warmup_rows = query_green_comparables(test_cases[0])
        print(f"  warmup OK: {len(warmup_rows)} rows")
    except Exception as exc:
        print(f"ERROR: Pool warmup failed: {type(exc).__name__}")
        return 1
    print()

    # ================================================================
    # SEQUENTIAL BENCHMARK: 120 calls
    # ================================================================
    print("=" * 50)
    print("SEQUENTIAL: 120 calls, seed=42")
    print("=" * 50)

    seq_result = _run_sequential(query_green_comparables, test_cases, 120, seed=42)
    _print_results(seq_result)

    seq_pass = (
        seq_result["samples"] >= 120
        and seq_result["errors"] == 0
        and seq_result["timeouts"] == 0
        and seq_result["empty"] == 0
        and seq_result["p95"] <= 300
    )
    print(f"SEQUENTIAL = {'PASS' if seq_pass else 'FAIL'}")
    if not seq_pass:
        _print_fail_reasons(seq_result, 120, 300)
    print()

    # ================================================================
    # Concurrency=3 warmup (unmeasured)
    # ================================================================
    print("Concurrency=3 pool warmup (unmeasured)...")
    with ThreadPoolExecutor(max_workers=3) as wp:
        warmup_futures = [
            wp.submit(query_green_comparables, test_cases[i % len(test_cases)])
            for i in range(3)
        ]
        for f in as_completed(warmup_futures):
            try:
                rows = f.result(timeout=15)
                print(f"  warmup: {len(rows)} rows")
            except Exception as exc:
                print(f"ERROR: Concurrent warmup failed: {type(exc).__name__}")
                return 1
    print()

    # ================================================================
    # CONCURRENCY=3 BENCHMARK: 90 calls
    # ================================================================
    print("=" * 50)
    print("CONCURRENCY_3: 90 calls, seed=42, workers=3")
    print("=" * 50)

    c3_result = _run_concurrent(query_green_comparables, test_cases, 90, concurrency=3, seed=42)
    _print_results(c3_result)

    c3_pass = (
        c3_result["samples"] >= 90
        and c3_result["errors"] == 0
        and c3_result["timeouts"] == 0
        and c3_result["empty"] == 0
        and c3_result["p95"] <= 300
    )
    print(f"CONCURRENCY_3 = {'PASS' if c3_pass else 'FAIL'}")
    if not c3_pass:
        _print_fail_reasons(c3_result, 90, 300)
    print()

    # ================================================================
    # CONCURRENCY=6 BENCHMARK: 60 calls (observation)
    # ================================================================
    print("=" * 50)
    print("CONCURRENCY_6: 60 calls, seed=43, workers=6 (overload observation)")
    print("=" * 50)

    c6_result = _run_concurrent(query_green_comparables, test_cases, 60, concurrency=6, seed=43)
    _print_results(c6_result)

    c6_correctness = (
        c6_result["errors"] == 0
        and c6_result["timeouts"] == 0
        and c6_result["empty"] == 0
    )
    print(f"CONCURRENCY_6_CORRECTNESS = {'PASS' if c6_correctness else 'FAIL'}")
    if not c6_correctness:
        reasons = []
        if c6_result["errors"] > 0:
            reasons.append(f"errors {c6_result['errors']} > 0")
        if c6_result["timeouts"] > 0:
            reasons.append(f"timeouts {c6_result['timeouts']} > 0")
        if c6_result["empty"] > 0:
            reasons.append(f"empty {c6_result['empty']} > 0")
        print(f"FAIL_REASONS: {'; '.join(reasons)}")
    print()

    # ================================================================
    # Pool cleanup
    # ================================================================
    pool_clean = False
    try:
        close_green_pool()
        pool_clean = True
    except Exception as exc:
        print(f"POOL CLOSE ERROR: {type(exc).__name__}: {exc}")

    # ================================================================
    # FINAL CONSOLIDATED SUMMARY
    # ================================================================
    final_gate = seq_pass and c3_pass and c6_correctness and pool_clean

    print("=" * 50)
    print("COMPACT GREEN FINAL RENDER GATE")
    print("=" * 50)
    print()
    print(f"SEQUENTIAL = {'PASS' if seq_pass else 'FAIL'}")
    print(f"SEQUENTIAL_P95_MS = {seq_result['p95']:.1f}")
    print()
    print(f"CONCURRENCY_3 = {'PASS' if c3_pass else 'FAIL'}")
    print(f"CONCURRENCY_3_P95_MS = {c3_result['p95']:.1f}")
    print()
    print(f"CONCURRENCY_6_CORRECTNESS = {'PASS' if c6_correctness else 'FAIL'}")
    print(f"CONCURRENCY_6_P95_MS = {c6_result['p95']:.1f}")
    print()
    print(f"POOL_CLEAN_CLOSE = {'PASS' if pool_clean else 'FAIL'}")
    print()
    print(f"FINAL_GATE = {'PASS' if final_gate else 'FAIL'}")
    print("=" * 50)

    # Exit 0 regardless of gate result — allows Render service to stay alive
    return 0


# ============================================================
# Benchmark runners
# ============================================================

def _run_sequential(
    query_fn,
    test_cases: list[dict[str, Any]],
    total_calls: int,
    seed: int,
) -> dict[str, Any]:
    """Run sequential (single-threaded) benchmark."""
    random.seed(seed)
    schedule = [random.choice(test_cases) for _ in range(total_calls)]

    durations_ms: list[float] = []
    errors = 0
    timeouts = 0
    empty = 0

    for payload in schedule:
        t0 = time.perf_counter()
        try:
            rows = query_fn(payload)
            t1 = time.perf_counter()
            durations_ms.append((t1 - t0) * 1000)
            if len(rows) == 0:
                empty += 1
        except TimeoutError:
            timeouts += 1
        except Exception:
            errors += 1

    return _build_results(durations_ms, errors, timeouts, empty)


def _run_concurrent(
    query_fn,
    test_cases: list[dict[str, Any]],
    total_calls: int,
    concurrency: int,
    seed: int,
) -> dict[str, Any]:
    """Run concurrent benchmark with ThreadPoolExecutor."""
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

    return _build_results(durations_ms, errors, timeouts, empty)


def _timed_query(query_fn, payload: dict[str, Any]) -> tuple[float, int]:
    """Execute one query and return (elapsed_ms, row_count)."""
    t0 = time.perf_counter()
    rows = query_fn(payload)
    t1 = time.perf_counter()
    return (t1 - t0) * 1000, len(rows)


def _build_results(
    durations_ms: list[float],
    errors: int,
    timeouts: int,
    empty: int,
) -> dict[str, Any]:
    """Build standardized results dict from measurements."""
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


def _print_results(results: dict[str, Any]) -> None:
    """Print benchmark results."""
    print(f"samples = {results['samples']}")
    print(f"median_ms = {results['median']:.1f}")
    print(f"p95_ms = {results['p95']:.1f}")
    print(f"p99_ms = {results['p99']:.1f}")
    print(f"max_ms = {results['max']:.1f}")
    print(f"over_300ms = {results['over_300']}")
    print(f"over_500ms = {results['over_500']}")
    print(f"over_1000ms = {results['over_1000']}")
    print(f"errors = {results['errors']}")
    print(f"timeouts = {results['timeouts']}")
    print(f"empty_results = {results['empty']}")
    print()


def _print_fail_reasons(results: dict[str, Any], min_samples: int, max_p95: float) -> None:
    """Print failure reasons for a hard gate."""
    reasons = []
    if results["samples"] < min_samples:
        reasons.append(f"samples {results['samples']} < {min_samples}")
    if results["errors"] > 0:
        reasons.append(f"errors {results['errors']} > 0")
    if results["timeouts"] > 0:
        reasons.append(f"timeouts {results['timeouts']} > 0")
    if results["empty"] > 0:
        reasons.append(f"empty {results['empty']} > 0")
    if results["p95"] > max_p95:
        reasons.append(f"p95 {results['p95']:.1f}ms > {max_p95}ms")
    if reasons:
        print(f"FAIL_REASONS: {'; '.join(reasons)}")


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
