#!/usr/bin/env python3
"""Compact GREEN post-load verifier (read-only).

Verifies the compact_green schema after production load.
Reads COMPACT_GREEN_DATABASE_URL from environment.

Usage:
    set COMPACT_GREEN_DATABASE_URL=postgresql://...
    python scripts/compact_green_post_load_verifier.py
"""

import os
import sys

import psycopg

SCHEMA = "compact_green"
GENERATION_ID = "official-plvr-green-18203c6347cd"
EXPECTED_MANIFEST_SHA256 = "18203c6347cd2e7c0fd4f274ec1c6e6b3f49cef8d4f890099a01ccacb9d0aa06"
EXPECTED_DATASET_SHA256 = "2ee0cf968d769a9dd8261031f3f13f6d7c5fcb4c0c33316a22120070806cef57"
EXPECTED_FACTS = 517195
EXPECTED_EVIDENCE = 517195
EXPECTED_AGGREGATES = 9606
EXPECTED_GEOGRAPHIES_DISTRICT = 323


def get_connection_string() -> str:
    url = os.environ.get("COMPACT_GREEN_DATABASE_URL", "")
    if not url:
        print("ERROR: COMPACT_GREEN_DATABASE_URL not set.", file=sys.stderr)
        sys.exit(1)
    return url


def check(label: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    suffix = f" ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}", flush=True)
    return condition


def main():
    conninfo = get_connection_string()
    conn = psycopg.connect(conninfo)
    conn.autocommit = True

    print("=" * 60)
    print("COMPACT GREEN POST-LOAD VERIFICATION")
    print("=" * 60)
    all_pass = True

    # === ROW COUNTS ===
    print("\n--- Row Counts ---")
    facts = conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_facts").fetchone()[0]
    evidence = conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_evidence").fetchone()[0]
    aggregates = conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_market_aggregates").fetchone()[0]

    all_pass &= check("Facts count", facts == EXPECTED_FACTS, f"{facts}/{EXPECTED_FACTS}")
    all_pass &= check("Evidence count", evidence == EXPECTED_EVIDENCE, f"{evidence}/{EXPECTED_EVIDENCE}")
    all_pass &= check("Aggregates count", aggregates == EXPECTED_AGGREGATES, f"{aggregates}/{EXPECTED_AGGREGATES}")

    # === GENERATION ===
    print("\n--- Generation ---")
    gen = conn.execute(f"SELECT generation_id, encode(source_manifest_sha256, 'hex'), encode(dataset_sha256, 'hex') FROM {SCHEMA}.compact_generations WHERE generation_key=1").fetchone()
    all_pass &= check("Generation ID", gen is not None and gen[0] == GENERATION_ID, gen[0] if gen else "MISSING")
    all_pass &= check("Manifest SHA256", gen is not None and gen[1] == EXPECTED_MANIFEST_SHA256, f"{gen[1][:16]}..." if gen else "MISSING")
    all_pass &= check("Dataset SHA256", gen is not None and gen[2] == EXPECTED_DATASET_SHA256, f"{gen[2][:16]}..." if gen else "MISSING")

    # === COVERAGE ===
    print("\n--- Coverage ---")
    lineage = conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_evidence WHERE length(source_row_hash)=32").fetchone()[0]
    identity = conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_evidence WHERE length(source_identity_hash)=32").fetchone()[0]
    dedupe = conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_evidence WHERE length(business_dedupe_key)=32").fetchone()[0]
    fact_hash = conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_evidence WHERE length(production_fact_hash)=32").fetchone()[0]
    address = conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_facts WHERE address_text IS NOT NULL AND address_text != ''").fetchone()[0]

    all_pass &= check("Lineage coverage 100%", lineage == EXPECTED_FACTS, f"{lineage}/{EXPECTED_FACTS}")
    all_pass &= check("Identity coverage 100%", identity == EXPECTED_FACTS, f"{identity}/{EXPECTED_FACTS}")
    all_pass &= check("Dedupe coverage 100%", dedupe == EXPECTED_FACTS, f"{dedupe}/{EXPECTED_FACTS}")
    all_pass &= check("Production fact coverage 100%", fact_hash == EXPECTED_FACTS, f"{fact_hash}/{EXPECTED_FACTS}")
    all_pass &= check("Address_text coverage 100%", address == EXPECTED_FACTS, f"{address}/{EXPECTED_FACTS}")

    # === UNIQUENESS ===
    print("\n--- Uniqueness ---")
    dup_tid_facts = conn.execute(f"SELECT count(*) - count(DISTINCT transaction_id) FROM {SCHEMA}.compact_transaction_facts").fetchone()[0]
    dup_tid_ev = conn.execute(f"SELECT count(*) - count(DISTINCT transaction_id) FROM {SCHEMA}.compact_transaction_evidence").fetchone()[0]
    dup_srh = conn.execute(f"SELECT count(*) - count(DISTINCT source_row_hash) FROM {SCHEMA}.compact_transaction_evidence").fetchone()[0]
    dup_sid = conn.execute(f"SELECT count(*) - count(DISTINCT source_identity_hash) FROM {SCHEMA}.compact_transaction_evidence").fetchone()[0]
    dup_bdk = conn.execute(f"SELECT count(*) - count(DISTINCT business_dedupe_key) FROM {SCHEMA}.compact_transaction_evidence").fetchone()[0]

    all_pass &= check("No duplicate transaction_id (facts)", dup_tid_facts == 0, str(dup_tid_facts))
    all_pass &= check("No duplicate transaction_id (evidence)", dup_tid_ev == 0, str(dup_tid_ev))
    all_pass &= check("No duplicate source_row_hash", dup_srh == 0, str(dup_srh))
    all_pass &= check("No duplicate source_identity_hash", dup_sid == 0, str(dup_sid))
    all_pass &= check("No duplicate business_dedupe_key", dup_bdk == 0, str(dup_bdk))

    # === GEOGRAPHY ===
    print("\n--- Geography ---")
    geo_district = conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_geographies WHERE geographic_unit_kind=1").fetchone()[0]
    geo_distinct = conn.execute(f"SELECT count(DISTINCT city || '|' || district) FROM {SCHEMA}.compact_geographies WHERE geographic_unit_kind=1").fetchone()[0]
    geo_dupes = conn.execute(f"SELECT count(*) FROM (SELECT city, district FROM {SCHEMA}.compact_geographies WHERE geographic_unit_kind=1 GROUP BY city, district HAVING count(*)>1) t").fetchone()[0]

    all_pass &= check("District geographies count", geo_district == EXPECTED_GEOGRAPHIES_DISTRICT, f"{geo_district}/{EXPECTED_GEOGRAPHIES_DISTRICT}")
    all_pass &= check("Geography pairs unique", geo_district == geo_distinct, f"distinct={geo_distinct}")
    all_pass &= check("No ambiguous (city,district)", geo_dupes == 0, str(geo_dupes))

    # === INDEXES ===
    print("\n--- Indexes ---")
    indexes = conn.execute("SELECT indexname FROM pg_indexes WHERE schemaname=%s ORDER BY indexname", (SCHEMA,)).fetchall()
    index_names = {r[0] for r in indexes}

    required_indexes = [
        "idx_compact_fact_region_period",
        "idx_compact_fact_geo_period_cover",
        "uq_compact_source_row_hash",
        "uq_compact_source_identity",
        "uq_compact_business_dedupe",
        "uq_compact_aggregate_key",
        "uq_compact_geography",
        "uq_compact_road",
        "uq_compact_building_type",
        "uq_compact_generation_id",
        "uq_compact_artifact_id",
        "uq_compact_artifact_sha",
    ]

    for idx in required_indexes:
        all_pass &= check(f"Index exists: {idx}", idx in index_names)

    # Check covering index INCLUDE columns
    cover_def = conn.execute("SELECT indexdef FROM pg_indexes WHERE schemaname=%s AND indexname='idx_compact_fact_geo_period_cover'", (SCHEMA,)).fetchone()
    if cover_def:
        has_include = "INCLUDE" in cover_def[0] and "unit_price_per_ping" in cover_def[0] and "total_price" in cover_def[0]
        all_pass &= check("Covering index has INCLUDE(unit_price_per_ping, total_price)", has_include)
    else:
        all_pass &= check("Covering index definition", False, "NOT FOUND")

    # === SUMMARY ===
    print("\n" + "=" * 60)
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    print("=" * 60)

    conn.close()
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
