# Compact GREEN Production Deployment Runbook

## Overview

This runbook defines the deployment sequence for the Compact GREEN PLVR schema
to the production Supabase free-plan database.

**Do NOT execute any remote steps until explicitly approved.**

## Prerequisites

- Local Round 2 benchmark: FINAL GO
- Semantic equivalence: 29/29 PASS
- Hot-path performance gate: ALL PASS
- Migration SQL reviewed and validated
- Production loader tested locally
- Post-load verifier tested locally

## Frozen Dataset Contract

| Property | Value |
|----------|-------|
| Generation ID | `official-plvr-green-18203c6347cd` |
| Dataset SHA256 | `2ee0cf968d769a9dd8261031f3f13f6d7c5fcb4c0c33316a22120070806cef57` |
| Manifest SHA256 | `18203c6347cd2e7c0fd4f274ec1c6e6b3f49cef8d4f890099a01ccacb9d0aa06` |
| Facts | 517,195 |
| Evidence | 517,195 |
| Aggregates | 9,606 |
| Expected storage | ~344 MiB |
| Free plan quota | 500 MiB |
| Expected headroom | ~156 MiB |

## Period Encoding

```
period_code = (year - 2000) * 12 + month - 1
Example: 2026-07 = 318 (NOT 317)
```

---

## Deployment Sequence

### Step A: Schema Migration

Apply the migration to the GREEN Supabase database:

```sql
-- File: database/migrations/011_add_plvr_compact_green_schema.sql
```

This creates the `compact_green` schema with all tables and indexes.

**Verification:**
- All 8 tables exist
- All 19 indexes exist
- No business rows yet

### Step B: Verify Empty Tables

```sql
SELECT count(*) FROM compact_green.compact_transaction_facts;
-- Expected: 0

SELECT count(*) FROM compact_green.compact_transaction_evidence;
-- Expected: 0
```

### Step C: Load Dictionaries + Generation

Run the production loader. It loads in order:
1. `compact_generations` (1 row)
2. `compact_artifacts` (17 rows)
3. `compact_geographies` (325 rows)
4. `compact_roads` (~25,299 rows)
5. `compact_building_types` (12 rows)

```bash
set COMPACT_GREEN_DATABASE_URL=postgresql://...
python scripts/compact_green_production_loader.py --source path/to/clean-shadow.sqlite3
```

The loader handles steps C, D, E automatically in sequence.

### Step D: Load Facts + Evidence (Resumable)

The loader inserts in batches of 5,000 rows. Each batch is committed.
If interrupted, re-running resumes from the last committed batch.

**No duplicate rows** — uses deterministic `transaction_id` as PK.

Progress: prints `MODEL_B_LOADED=N` every 5,000 rows.

Expected duration: 3-5 minutes (depending on network latency to Supabase).

### Step E: Load Aggregates

9,606 market aggregate rows. Small and fast.

### Step F: Verify Indexes

Indexes are created by the schema migration (Step A).
After data load, they are automatically populated.

If any index is missing, create it manually from the migration SQL.

### Step G: ANALYZE

The loader runs `ANALYZE` on all tables after loading.
If running manually:

```sql
ANALYZE compact_green.compact_transaction_facts;
ANALYZE compact_green.compact_transaction_evidence;
ANALYZE compact_green.compact_market_aggregates;
ANALYZE compact_green.compact_geographies;
ANALYZE compact_green.compact_roads;
ANALYZE compact_green.compact_building_types;
```

### Step H: Post-Load Verification

Run the verifier:

```bash
set COMPACT_GREEN_DATABASE_URL=postgresql://...
python scripts/compact_green_post_load_verifier.py
```

**Required result:** ALL checks PASS.

Verifies:
- Row counts (517195 / 517195 / 9606)
- Generation ID match
- Manifest and dataset SHA match
- 100% lineage/identity/dedupe/fact/address coverage
- No duplicates
- Geography uniqueness (323 district entries)
- All required indexes present
- Covering index INCLUDE columns correct

### Step I: Real Supabase Storage Measurement

```sql
SELECT pg_total_relation_size('compact_green.compact_transaction_facts');
SELECT pg_total_relation_size('compact_green.compact_transaction_evidence');
-- Sum all tables for total
```

**Gate:** Total ≤ 450 MiB (reject > 450 MiB)

### Step J: Supabase Hot-Path Smoke Benchmark

Run the three hot-path queries from the query contract against production.
Compare latency (accounting for network) to local benchmark.

Minimum acceptance: queries return correct results and complete within
reasonable latency (< 200ms including network).

### Step K: Application Cutover (Discussion Only)

**Do NOT execute until Steps A–J all pass.**

Cutover involves:
1. Update application to use `compact_green` schema
2. Implement in-process geography cache (323 entries)
3. Switch query patterns to frozen contract
4. Monitor production for 24 hours
5. If stable, decommission old schema

---

## Rollback

If any step fails:

- The `compact_green` schema is isolated — it does not affect existing tables.
- Drop the schema: `DROP SCHEMA compact_green CASCADE;`
- No existing data is modified.

---

## Files

| File | Purpose |
|------|---------|
| `database/migrations/011_add_plvr_compact_green_schema.sql` | Schema DDL |
| `scripts/compact_green_production_loader.py` | Data loader |
| `scripts/compact_green_post_load_verifier.py` | Post-load verification |
| `docs/plvr/compact-green-query-contract.md` | Frozen query patterns |
| `docs/plvr/compact-green-production-runbook.md` | This document |

---

## Safety Notes

- The loader reads `COMPACT_GREEN_DATABASE_URL` from environment only.
- No hard-coded DSN in any script.
- The loader is idempotent and resumable.
- The migration uses `CREATE SCHEMA IF NOT EXISTS` — safe to re-run.
- No existing schema/table is modified.
- No data deletion occurs.
