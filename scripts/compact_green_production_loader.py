#!/usr/bin/env python3
"""Compact GREEN production loader.

Loads the frozen PLVR dataset into the compact_green schema.
Reads database URL from COMPACT_GREEN_DATABASE_URL environment variable at runtime.
Does NOT contain hard-coded remote DSN.

Source: frozen clean-shadow.sqlite3
Expected: 517195 transactions, 9606 aggregates
Dataset SHA: 2ee0cf968d769a9dd8261031f3f13f6d7c5fcb4c0c33316a22120070806cef57

Usage:
    set COMPACT_GREEN_DATABASE_URL=postgresql://...
    python scripts/compact_green_production_loader.py --source path/to/clean-shadow.sqlite3
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

import psycopg

# Frozen dataset contract
DATASET_KEY = "official_plvr"
GENERATION_ID = "official-plvr-green-18203c6347cd"
EXPECTED_MANIFEST_SHA256 = "18203c6347cd2e7c0fd4f274ec1c6e6b3f49cef8d4f890099a01ccacb9d0aa06"
EXPECTED_DATASET_SHA256 = "2ee0cf968d769a9dd8261031f3f13f6d7c5fcb4c0c33316a22120070806cef57"
SOURCE_NAME = "official_plvr_opendata"
EXPECTED_FACTS = 517195
EXPECTED_AGGREGATES = 9606
BATCH_SIZE = 5000
SCHEMA = "compact_green"


def encode_period(value: str) -> int:
    """Encode YYYY-MM to integer: (year - 2000) * 12 + month - 1."""
    year, month = value.split("-", 1)
    return (int(year) - 2000) * 12 + int(month) - 1


def digest_bytes(value: str) -> bytes:
    """Convert hex string (possibly with 'official:' prefix) to raw bytes."""
    digest = str(value).split(":", 1)[-1]
    if len(digest) != 64:
        raise ValueError(f"digest_length_invalid: {len(digest)}")
    return bytes.fromhex(digest)


def identity_kind(value: str) -> int:
    """0 = official, 1 = source-row."""
    return 0 if value.startswith("official:") else 1


def get_connection_string() -> str:
    """Read database URL from environment."""
    url = os.environ.get("COMPACT_GREEN_DATABASE_URL", "")
    if not url:
        print("ERROR: COMPACT_GREEN_DATABASE_URL not set.", file=sys.stderr)
        sys.exit(1)
    return url


def load_generation(pg_conn, shadow_conn):
    """Load the generation record."""
    existing = pg_conn.execute(
        f"SELECT count(*) FROM {SCHEMA}.compact_generations WHERE generation_id=%s",
        (GENERATION_ID,)
    ).fetchone()[0]
    if existing > 0:
        print(f"  Generation already exists: {GENERATION_ID}")
        return

    cursor = shadow_conn.cursor()
    cursor.execute("SELECT source_name, aggregation_method, min(built_at) FROM shadow_market_aggregates")
    agg_meta = cursor.fetchone()

    pg_conn.execute(
        f"""INSERT INTO {SCHEMA}.compact_generations
            (generation_key, dataset_key, generation_id, source_manifest_sha256,
             dataset_sha256, source, canonical_status, publishable,
             market_source_name, aggregation_method, aggregate_built_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (1, DATASET_KEY, GENERATION_ID,
         digest_bytes(EXPECTED_MANIFEST_SHA256),
         digest_bytes(EXPECTED_DATASET_SHA256),
         SOURCE_NAME, 1, 1,
         agg_meta[0], agg_meta[1], agg_meta[2])
    )
    pg_conn.commit()
    print(f"  Generation loaded: {GENERATION_ID}")


def load_artifacts(pg_conn, shadow_conn):
    """Load artifact records."""
    existing = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_artifacts").fetchone()[0]
    if existing > 0:
        print(f"  Artifacts already loaded: {existing}")
        return

    cursor = shadow_conn.cursor()
    cursor.execute("SELECT artifact_id, sha256 FROM shadow_artifacts ORDER BY artifact_id")
    key = 1
    for art in cursor:
        pg_conn.execute(
            f"INSERT INTO {SCHEMA}.compact_artifacts (artifact_key, artifact_id, source_artifact_sha256) VALUES (%s, %s, %s)",
            (key, art[0], digest_bytes(art[1]))
        )
        key += 1
    pg_conn.commit()
    print(f"  Artifacts loaded: {key - 1}")


def load_geographies(pg_conn, shadow_conn):
    """Load geography dictionary."""
    existing = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_geographies").fetchone()[0]
    if existing > 0:
        print(f"  Geographies already loaded: {existing}")
        return

    cursor = shadow_conn.cursor()
    cursor.execute("SELECT DISTINCT city, district, geographic_unit_kind FROM shadow_transactions ORDER BY city, district, geographic_unit_kind")
    key = 1
    for geo in cursor:
        kind_int = 1 if geo[2] == 'district' else 0
        pg_conn.execute(
            f"INSERT INTO {SCHEMA}.compact_geographies (geographic_unit_id, city, district, geographic_unit_kind) VALUES (%s, %s, %s, %s)",
            (key, geo[0], geo[1], kind_int)
        )
        key += 1
    pg_conn.commit()
    print(f"  Geographies loaded: {key - 1}")


def load_roads(pg_conn, shadow_conn):
    """Load road dictionary."""
    existing = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_roads").fetchone()[0]
    if existing > 0:
        print(f"  Roads already loaded: {existing}")
        return

    geo_lookup = {}
    for r in pg_conn.execute(f"SELECT geographic_unit_id, city, district, geographic_unit_kind FROM {SCHEMA}.compact_geographies").fetchall():
        geo_lookup[(r[1], r[2], r[3])] = r[0]

    cursor = shadow_conn.cursor()
    cursor.execute("SELECT DISTINCT city, district, geographic_unit_kind, road FROM shadow_transactions ORDER BY city, district, geographic_unit_kind, road")
    key = 1
    batch = []
    for rd in cursor:
        kind_int = 1 if rd[2] == 'district' else 0
        geo_id = geo_lookup[(rd[0], rd[1], kind_int)]
        batch.append((key, geo_id, rd[3]))
        key += 1
        if len(batch) >= BATCH_SIZE:
            with pg_conn.cursor() as cur:
                cur.executemany(f"INSERT INTO {SCHEMA}.compact_roads (road_id, geographic_unit_id, road) VALUES (%s, %s, %s)", batch)
            pg_conn.commit()
            batch = []
    if batch:
        with pg_conn.cursor() as cur:
            cur.executemany(f"INSERT INTO {SCHEMA}.compact_roads (road_id, geographic_unit_id, road) VALUES (%s, %s, %s)", batch)
        pg_conn.commit()
    print(f"  Roads loaded: {key - 1}")


def load_building_types(pg_conn, shadow_conn):
    """Load building type dictionary."""
    existing = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_building_types").fetchone()[0]
    if existing > 0:
        print(f"  Building types already loaded: {existing}")
        return

    cursor = shadow_conn.cursor()
    cursor.execute("SELECT DISTINCT building_type FROM shadow_transactions ORDER BY building_type")
    key = 1
    for bt in cursor:
        pg_conn.execute(
            f"INSERT INTO {SCHEMA}.compact_building_types (building_type_id, building_type) VALUES (%s, %s)",
            (key, bt[0])
        )
        key += 1
    pg_conn.commit()
    print(f"  Building types loaded: {key - 1}")


def load_transactions(pg_conn, shadow_conn):
    """Load facts and evidence in resumable batches."""
    fact_count = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_facts").fetchone()[0]
    evidence_count = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_evidence").fetchone()[0]

    if fact_count == EXPECTED_FACTS and evidence_count == EXPECTED_FACTS:
        print(f"  Transactions already complete: {fact_count}")
        return

    # Sync inconsistent state
    resume_from = min(fact_count, evidence_count)
    if fact_count != evidence_count:
        print(f"  Syncing: facts={fact_count} evidence={evidence_count} -> resume from {resume_from}")
        if resume_from < fact_count:
            pg_conn.execute(f"DELETE FROM {SCHEMA}.compact_transaction_facts WHERE transaction_id > %s", (resume_from,))
        if resume_from < evidence_count:
            pg_conn.execute(f"DELETE FROM {SCHEMA}.compact_transaction_evidence WHERE transaction_id > %s", (resume_from,))
        pg_conn.commit()
        fact_count = resume_from

    # Build lookups
    geo_lookup = {}
    for r in pg_conn.execute(f"SELECT geographic_unit_id, city, district, geographic_unit_kind FROM {SCHEMA}.compact_geographies").fetchall():
        geo_lookup[(r[1], r[2], r[3])] = r[0]

    road_lookup = {}
    for r in pg_conn.execute(f"SELECT road_id, geographic_unit_id, road FROM {SCHEMA}.compact_roads").fetchall():
        road_lookup[(r[1], r[2])] = r[0]

    bt_lookup = {}
    for r in pg_conn.execute(f"SELECT building_type_id, building_type FROM {SCHEMA}.compact_building_types").fetchall():
        bt_lookup[r[1]] = r[0]

    artifact_lookup = {}
    for r in pg_conn.execute(f"SELECT artifact_key, source_artifact_sha256 FROM {SCHEMA}.compact_artifacts").fetchall():
        artifact_lookup[bytes(r[1]).hex()] = r[0]

    # Read from source
    cursor = shadow_conn.cursor()
    cursor.execute("""
        SELECT source_row_hash, source_identity, artifact_sha256,
               official_transaction_id, official_transfer_id, business_dedupe_key,
               production_fact_hash, transaction_period, city, district,
               geographic_unit_kind, road, address_text, building_type,
               area_ping, building_age_years, floor, total_floor,
               unit_price_per_ping, total_price
        FROM shadow_transactions
        ORDER BY source_identity, source_row_hash
    """)

    # Skip already loaded
    if fact_count > 0:
        for _ in range(fact_count):
            cursor.fetchone()
        print(f"  Resuming from row {fact_count}")

    fact_batch, evidence_batch = [], []
    loaded = fact_count
    transaction_id = fact_count
    start_time = time.time()

    for row in cursor:
        transaction_id += 1
        source_row_hash, source_identity, artifact_sha256 = row[0], row[1], row[2]
        official_txn_id, official_transfer_id = row[3], row[4]
        business_dedupe, production_fact_hash = row[5], row[6]
        period_str, city, district = row[7], row[8], row[9]
        geo_unit_kind, road, address_text, building_type = row[10], row[11], row[12], row[13]
        area_ping, building_age, floor_val, total_floor = row[14], row[15], row[16], row[17]
        unit_price, total_price = row[18], row[19]

        kind_int = 1 if geo_unit_kind == 'district' else 0
        geo_id = geo_lookup[(city, district, kind_int)]
        road_id = road_lookup[(geo_id, road)]
        bt_id = bt_lookup[building_type]
        period_code = encode_period(period_str)
        artifact_sha_hex = digest_bytes(artifact_sha256).hex()
        artifact_key = artifact_lookup[artifact_sha_hex]

        fact_batch.append((
            transaction_id, 1, geo_id, period_code, road_id, bt_id,
            area_ping, building_age, floor_val, total_floor,
            unit_price, total_price, address_text
        ))
        evidence_batch.append((
            transaction_id,
            digest_bytes(source_row_hash),
            identity_kind(source_identity),
            digest_bytes(source_identity),
            artifact_key,
            official_txn_id,
            official_transfer_id or '',
            digest_bytes(business_dedupe),
            digest_bytes(production_fact_hash),
            address_text
        ))

        if len(fact_batch) >= BATCH_SIZE:
            with pg_conn.cursor() as cur:
                cur.executemany(
                    f"""INSERT INTO {SCHEMA}.compact_transaction_facts
                        (transaction_id, generation_key, geographic_unit_id, period_code,
                         road_id, building_type_id, area_ping, building_age_years,
                         floor, total_floor, unit_price_per_ping, total_price, address_text)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    fact_batch)
                cur.executemany(
                    f"""INSERT INTO {SCHEMA}.compact_transaction_evidence
                        (transaction_id, source_row_hash, source_identity_kind,
                         source_identity_hash, artifact_key, official_transaction_id,
                         official_transfer_id, business_dedupe_key,
                         production_fact_hash, address_text)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    evidence_batch)
            pg_conn.commit()
            loaded += len(fact_batch)
            fact_batch, evidence_batch = [], []
            elapsed = time.time() - start_time
            rate = (loaded - fact_count) / elapsed if elapsed > 0 else 0
            print(f"  MODEL_B_LOADED={loaded} ({rate:.0f} rows/s)")

    if fact_batch:
        with pg_conn.cursor() as cur:
            cur.executemany(
                f"""INSERT INTO {SCHEMA}.compact_transaction_facts
                    (transaction_id, generation_key, geographic_unit_id, period_code,
                     road_id, building_type_id, area_ping, building_age_years,
                     floor, total_floor, unit_price_per_ping, total_price, address_text)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                fact_batch)
            cur.executemany(
                f"""INSERT INTO {SCHEMA}.compact_transaction_evidence
                    (transaction_id, source_row_hash, source_identity_kind,
                     source_identity_hash, artifact_key, official_transaction_id,
                     official_transfer_id, business_dedupe_key,
                     production_fact_hash, address_text)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                evidence_batch)
        pg_conn.commit()
        loaded += len(fact_batch)

    print(f"  Transactions complete: {loaded}")


def load_aggregates(pg_conn, shadow_conn):
    """Load market aggregates."""
    existing = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_market_aggregates").fetchone()[0]
    if existing == EXPECTED_AGGREGATES:
        print(f"  Aggregates already complete: {existing}")
        return
    if existing > 0:
        pg_conn.execute(f"DELETE FROM {SCHEMA}.compact_market_aggregates")
        pg_conn.commit()

    geo_lookup = {}
    for r in pg_conn.execute(f"SELECT geographic_unit_id, city, district, geographic_unit_kind FROM {SCHEMA}.compact_geographies").fetchall():
        geo_lookup[(r[1], r[2], r[3])] = r[0]

    cursor = shadow_conn.cursor()
    cursor.execute("SELECT county, district, geographic_unit_kind, period, average_unit_price, transaction_count, record_count, coverage_status, data_status FROM shadow_market_aggregates")

    batch = []
    for agg in cursor:
        kind_int = 1 if agg[2] == 'district' else 0
        geo_id = geo_lookup[(agg[0], agg[1], kind_int)]
        period_code = encode_period(agg[3])
        coverage_int = 1 if agg[7] == 'COMPLETE' else 2
        data_int = 1 if agg[8] == 'available' else 0
        batch.append((1, geo_id, period_code, agg[4], agg[5], agg[6], coverage_int, data_int))
        if len(batch) >= 1000:
            with pg_conn.cursor() as cur:
                cur.executemany(
                    f"""INSERT INTO {SCHEMA}.compact_market_aggregates
                        (generation_key, geographic_unit_id, period_code,
                         average_unit_price, transaction_count, record_count,
                         coverage_status, data_status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", batch)
            pg_conn.commit()
            batch = []
    if batch:
        with pg_conn.cursor() as cur:
            cur.executemany(
                f"""INSERT INTO {SCHEMA}.compact_market_aggregates
                    (generation_key, geographic_unit_id, period_code,
                     average_unit_price, transaction_count, record_count,
                     coverage_status, data_status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", batch)
        pg_conn.commit()

    final = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_market_aggregates").fetchone()[0]
    print(f"  Aggregates loaded: {final}")


def verify_final(pg_conn):
    """Verify final counts and coverage."""
    facts = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_facts").fetchone()[0]
    evidence = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_evidence").fetchone()[0]
    aggregates = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_market_aggregates").fetchone()[0]

    assert facts == EXPECTED_FACTS, f"Facts mismatch: {facts}"
    assert evidence == EXPECTED_FACTS, f"Evidence mismatch: {evidence}"
    assert aggregates == EXPECTED_AGGREGATES, f"Aggregates mismatch: {aggregates}"

    # Coverage checks
    lineage = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_evidence WHERE length(source_row_hash)=32").fetchone()[0]
    identity = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_evidence WHERE length(source_identity_hash)=32").fetchone()[0]
    dedupe = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_evidence WHERE length(business_dedupe_key)=32").fetchone()[0]
    fact_hash = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_evidence WHERE length(production_fact_hash)=32").fetchone()[0]
    addr = pg_conn.execute(f"SELECT count(*) FROM {SCHEMA}.compact_transaction_facts WHERE address_text IS NOT NULL").fetchone()[0]

    assert lineage == EXPECTED_FACTS, f"Lineage coverage: {lineage}"
    assert identity == EXPECTED_FACTS, f"Identity coverage: {identity}"
    assert dedupe == EXPECTED_FACTS, f"Dedupe coverage: {dedupe}"
    assert fact_hash == EXPECTED_FACTS, f"Fact hash coverage: {fact_hash}"
    assert addr == EXPECTED_FACTS, f"Address coverage: {addr}"

    print(f"\n  VERIFICATION PASSED")
    print(f"  Facts: {facts}")
    print(f"  Evidence: {evidence}")
    print(f"  Aggregates: {aggregates}")
    print(f"  Lineage: {lineage}/{EXPECTED_FACTS}")
    print(f"  Identity: {identity}/{EXPECTED_FACTS}")
    print(f"  Dedupe: {dedupe}/{EXPECTED_FACTS}")
    print(f"  Fact hash: {fact_hash}/{EXPECTED_FACTS}")
    print(f"  Address: {addr}/{EXPECTED_FACTS}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="Path to frozen clean-shadow.sqlite3")
    args = parser.parse_args()

    if not args.source.exists():
        print(f"ERROR: Source not found: {args.source}", file=sys.stderr)
        return 1

    conninfo = get_connection_string()
    shadow_conn = sqlite3.connect(f"file:{args.source.as_posix()}?mode=ro", uri=True)
    pg_conn = psycopg.connect(conninfo)

    try:
        print("=== Compact GREEN Production Loader ===")
        print(f"Source: {args.source}")
        print(f"Schema: {SCHEMA}")
        print(f"Generation: {GENERATION_ID}")

        print("\n--- Loading generation ---")
        load_generation(pg_conn, shadow_conn)

        print("\n--- Loading artifacts ---")
        load_artifacts(pg_conn, shadow_conn)

        print("\n--- Loading geographies ---")
        load_geographies(pg_conn, shadow_conn)

        print("\n--- Loading roads ---")
        load_roads(pg_conn, shadow_conn)

        print("\n--- Loading building types ---")
        load_building_types(pg_conn, shadow_conn)

        print("\n--- Loading transactions ---")
        load_transactions(pg_conn, shadow_conn)

        print("\n--- Loading aggregates ---")
        load_aggregates(pg_conn, shadow_conn)

        print("\n--- Running ANALYZE ---")
        for table in ["compact_generations", "compact_artifacts", "compact_geographies",
                      "compact_roads", "compact_building_types", "compact_transaction_facts",
                      "compact_transaction_evidence", "compact_market_aggregates"]:
            pg_conn.execute(f"ANALYZE {SCHEMA}.{table}")
        pg_conn.commit()
        print("  ANALYZE complete")

        print("\n--- Verifying ---")
        verify_final(pg_conn)

        print("\n=== LOAD COMPLETE ===")
        return 0

    finally:
        pg_conn.close()
        shadow_conn.close()


if __name__ == "__main__":
    sys.exit(main())
