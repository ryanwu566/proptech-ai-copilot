#!/usr/bin/env python3
"""Compact GREEN adapter latency benchmark for Render network measurement.

This script runs ONCE at startup, prints results to deployment logs, then exits.
It directly calls the GREEN adapter (query_green_comparables) — NOT the full
valuation estimate endpoint. No BLUE provider, no market insight, no writes.

The adapter uses a psycopg_pool.ConnectionPool (min=1, max=3) for connection
reuse. This benchmark measures production-representative pooled behavior.

Required environment:
    COMPACT_GREEN_DATABASE_URL  — GREEN database connection

Not required:
    VALUATION_DATABASE_URL, DATABASE_URL, PLVR_DATA_BACKEND

Exit codes:
    0 — gate PASS (p95 <= 300ms, 0 errors/timeouts/empty)
    1 — setup/configuration error
    2 — performance or correctness gate FAIL
"""

from __future__ import annotations

import os
import random
import statistics
import sys
import time


def main() -> int:
    # ----------------------------------------------------------------
    # Configuration check
    # ----------------------------------------------------------------
    if not os.getenv("COMPACT_GREEN_DATABASE_URL", "").strip():
        print("ERROR: COMPACT_GREEN_DATABASE_URL is not set.")
        print("Set it in the Render service environment variables.")
        return 1

    # ----------------------------------------------------------------
    # Import adapter (validates module availability)
    # ----------------------------------------------------------------
    try:
        from services.compact_green_query import (
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
    print("COMPACT GREEN RENDER BENCHMARK")
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
    print()

    # Validate expected production state
    if geography_entries != 323:
        print(f"WARNING: Expected 323 geography entries, got {geography_entries}")
    if max_pc != 318:
        print(f"WARNING: Expected max_period_code 318, got {max_pc}")
    if max_period != "2026-07":
        print(f"WARNING: Expected max_period 2026-07, got {max_period}")

    # ----------------------------------------------------------------
    # Build test cases from 6 known-good cities
    # ----------------------------------------------------------------
    target_cities = ["南投縣", "嘉義縣", "基隆市", "宜蘭縣", "屏東縣", "彰化縣"]
    all_districts = list(cache.keys())

    test_cases = []
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
    for tc in test_cases:
        print(f"  {tc['city']} {tc['district']}")
    print()

    # ----------------------------------------------------------------
    # Pool warmup: one unmeasured call to initialize lazy pool + min connection
    # ----------------------------------------------------------------
    print("Pool warmup (unmeasured)...")
    try:
        warmup_rows = query_green_comparables(test_cases[0])
        print(f"  warmup OK: {len(warmup_rows)} rows")
    except Exception as exc:
        print(f"ERROR: Pool warmup failed: {type(exc).__name__}")
        return 1
    print()

    # ----------------------------------------------------------------
    # Benchmark: 120 interleaved calls (seed=42)
    # ----------------------------------------------------------------
    random.seed(42)
    NUM_SAMPLES = 120
    schedule = [random.choice(test_cases) for _ in range(NUM_SAMPLES)]

    print(f"Running {NUM_SAMPLES} measured calls...")
    print("Each call: pooled connection checkout + SET READ ONLY + SQL + fetch + map")
    print()

    durations_ms: list[float] = []
    errors = 0
    timeouts = 0
    empty_results = 0

    for payload in schedule:
        t0 = time.perf_counter()
        try:
            rows = query_green_comparables(payload)
            t1 = time.perf_counter()
            elapsed = (t1 - t0) * 1000
            durations_ms.append(elapsed)
            if len(rows) == 0:
                empty_results += 1
        except TimeoutError:
            timeouts += 1
        except Exception:
            errors += 1

    # ----------------------------------------------------------------
    # Report
    # ----------------------------------------------------------------
    durations_ms.sort()
    n = len(durations_ms)

    if n == 0:
        print("ERROR: No successful measurements")
        return 1

    median_ms = statistics.median(durations_ms)
    p95_ms = durations_ms[int(n * 0.95)]
    p99_ms = durations_ms[int(n * 0.99)]
    max_ms = max(durations_ms)

    over_300 = sum(1 for d in durations_ms if d > 300)
    over_500 = sum(1 for d in durations_ms if d > 500)
    over_1000 = sum(1 for d in durations_ms if d > 1000)

    print("=" * 50)
    print("RESULTS")
    print("=" * 50)
    print(f"samples = {n}")
    print(f"median_ms = {median_ms:.1f}")
    print(f"p95_ms = {p95_ms:.1f}")
    print(f"p99_ms = {p99_ms:.1f}")
    print(f"max_ms = {max_ms:.1f}")
    print()
    print(f"over_300ms = {over_300}")
    print(f"over_500ms = {over_500}")
    print(f"over_1000ms = {over_1000}")
    print()
    print(f"errors = {errors}")
    print(f"timeouts = {timeouts}")
    print(f"empty_results = {empty_results}")
    print()

    # ----------------------------------------------------------------
    # Gate
    # ----------------------------------------------------------------
    gate_pass = (
        n >= 120
        and errors == 0
        and timeouts == 0
        and empty_results == 0
        and p95_ms <= 300
    )

    print(f"PASS_GATE = {'PASS' if gate_pass else 'FAIL'}")

    if not gate_pass:
        reasons = []
        if n < 120:
            reasons.append(f"samples {n} < 120")
        if errors > 0:
            reasons.append(f"errors {errors} > 0")
        if timeouts > 0:
            reasons.append(f"timeouts {timeouts} > 0")
        if empty_results > 0:
            reasons.append(f"empty_results {empty_results} > 0")
        if p95_ms > 300:
            reasons.append(f"p95 {p95_ms:.1f}ms > 300ms")
        print(f"FAIL_REASONS: {'; '.join(reasons)}")
        return 2

    return 0


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
