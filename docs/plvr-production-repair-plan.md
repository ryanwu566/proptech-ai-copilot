# PLVR Production Repair Dry Run and Reconciliation Plan v1

## Scope and safety boundary

This document is the Phase 2B-1 plan. It does not authorize a production
repair. Production inspection for this plan used `SELECT` statements only.
No transaction row, aggregate row, schema object, migration, import run, or
runtime setting was changed.

The committed machine-readable artifact is
`docs/plvr-production-repair-summary-v1.json`. It contains aggregate counts,
not row identifiers, addresses, source payloads, or connection information.
The planner can materialize a privacy-bounded row manifest at operator runtime,
but that manifest must be kept out of the repository and access controlled.

## Baseline snapshot

Snapshot time: `2026-08-11T13:49:33+08:00`

End-of-audit verification: `2026-08-11T14:32:35+08:00`; all transaction and
aggregate baseline counts were unchanged.

| Measure | Count |
| --- | ---: |
| Official PLVR transaction rows | 451,672 |
| Canonical valid rows | 325,585 |
| Canonical invalid rows | 126,087 |
| Invalid rate | 27.9156% |
| Future transaction rows | 1 |
| Materialized aggregate rows | 11,018 |
| Future aggregate rows | 1 |

Canonical validation uses the same whitespace and `台`/`臺` normalization and
county aliases as `services.plvr_data_integrity`, backed by the checked-in
368-region registry. A SQL-only equality join can over-count invalid rows, so
it is not the repair contract.

## Evidence model

Evidence precedence is:

1. Source artifact identity and official city file code.
2. Row-linked import run, source filename, artifact hash, and import scope.
3. Explicit raw source city that was not overwritten.
4. Address-derived county as supporting evidence only.
5. Canonical district ownership as supporting evidence only.

`real_price_transactions` does not persist source filename, source artifact
hash, raw source city, raw transaction date/type, or an `import_run_id`.
`valuation_import_runs` is a coarse run summary and has no foreign key from a
transaction row. Production schema inspection found no foreign keys into or
out of these two tables. Import timestamps can group the contamination but
cannot establish authoritative row lineage.

### Classification result

| Classification | Count | Phase 2B-2 eligibility |
| --- | ---: | --- |
| `SAFE_AUTOMATIC_REPAIR` | 0 | None |
| `REPAIR_WITH_SUPPORTING_EVIDENCE` | 109,236 | Candidate only; no apply authorization |
| `AMBIGUOUS` | 5,870 | Exclude and quarantine |
| `SOURCE_CORRUPT_OR_UNRESOLVED` | 10,981 | Exclude and quarantine |

The supporting group has two agreeing, non-authoritative signals: a unique
canonical district owner and an address county prefix. That is sufficient to
propose a target for reconciliation, not sufficient to execute a production
change.

### Concentration

All supporting rows, all ambiguous rows, and 7 unresolved rows share import
date `2026-06-07`. The other 10,974 unresolved rows share import date
`2026-06-08`. There is no deterministic row-to-run link.

The invalid population spans `2024-01` through `2026-05`. The largest period
groups are `2024-03` (8,299), `2024-07` (7,657), `2024-01` (7,504),
`2024-06` (7,427), `2024-04` (7,250), `2024-05` (6,402), and `2025-03`
(6,162).

The leading proposed mappings are:

| Current pair | Proposed canonical pair | Candidate rows |
| --- | --- | ---: |
| 台南市 / 中壢區 | 桃園市 / 中壢區 | 5,056 |
| 台南市 / 桃園區 | 桃園市 / 桃園區 | 5,003 |
| 台南市 / 三民區 | 高雄市 / 三民區 | 4,574 |
| 台南市 / 北屯區 | 台中市 / 北屯區 | 4,514 |
| 台南市 / 鳳山區 | 高雄市 / 鳳山區 | 3,786 |
| 台南市 / 楠梓區 | 高雄市 / 楠梓區 | 3,707 |
| 台南市 / 西屯區 | 台中市 / 西屯區 | 3,613 |
| 台南市 / 龜山區 | 桃園市 / 龜山區 | 2,864 |
| 台南市 / 左營區 | 高雄市 / 左營區 | 2,843 |

## Collision analysis

Collision checks compare a proposed target against existing canonical rows.
The natural key follows importer semantics: source, canonical region, period,
normalized address and road, building type, area, total price, and unit price.
The exact key additionally checks age and floor facts. Raw addresses are used
inside the read-only runtime only and are never emitted.

| Collision class | Candidate rows |
| --- | ---: |
| `NO_COLLISION` | 51,689 |
| `EXACT_DUPLICATE_AFTER_REPAIR` | 57,350 |
| `NATURAL_KEY_COLLISION` | 3 |
| `AMBIGUOUS_COLLISION` / proposed dedupe overlap | 194 |

Total collision candidates are 57,547. No collision class implies deletion.
Every collision row and its canonical counterpart must be included in the
pre-repair snapshot and reviewed before choosing update, dedupe, or quarantine.

## Dedupe key impact

The v2 dedupe seed includes city and district. A geography change therefore
invalidates the old identity. The seed may also include the official source
transaction identifier, but that identifier is not stored in
`real_price_transactions`. Rebuilding from persisted columns alone can produce
a different key from the import-time key.

The database has a unique partial index on `(source, dedupe_key)`. No foreign
key references to the transaction table or dedupe key were found. Aggregate
queries use transaction facts rather than dedupe-key references. Even so,
dedupe regeneration is blocked until the authoritative source identifier or a
reviewed replacement identity policy is available.

## Future row

The single future row is from `official_plvr_opendata`, canonical region
`臺北市 / 南港區`, period `2026-10`, imported on `2026-06-07`. The database does
not retain the source filename, raw transaction date, raw transaction type, or
artifact identity needed to decide whether it is presale data, a source
anomaly, a date conversion error, or an import error.

Classification: `UNRESOLVED`.

The one future aggregate has one linked source transaction. Rebuilding the
affected `臺北市 / 南港區 / 2026-10` scope after a future transaction is
quarantined should remove that aggregate. The region has 34 publishable
historical aggregate periods through the snapshot ceiling, so existing guarded
latest/history reads remain available. Phase 2B-2 should quarantine, not
delete, the row pending source artifact verification.

## Reconciliation simulation

This simulation applies proposed geography only. It does not deduplicate,
quarantine, mutate dedupe keys, or change production.

| Measure | Before | Simulated after |
| --- | ---: | ---: |
| Transaction rows | 451,672 | 451,672 |
| Canonical valid rows | 325,585 | 434,821 |
| Canonical invalid rows | 126,087 | 16,851 |
| Future rows | 1 | 1 |
| Publishable canonical rows | 325,584 | 434,820 |
| Aggregate rows | 11,018 | 7,729 source scopes before dedupe disposition |

There are 2,149 affected proposed target city/district/period scopes. The
current aggregate table contains 7,614 canonical publishable rows, 3,403 rows
for invalid geography, and 1 future row. Derived output must be rebuilt only
for the approved affected scopes.

### Golden region preservation

The simulation retains every existing canonical transaction and adds proposed
rows without deleting either side. Baseline checks cover:

* 台北市 / 中正區
* 台北市 / 南港區
* 台中市 / 北屯區
* 桃園市 / 平鎮區
* 高雄市 / 小港區
* 桃園市 / 中壢區
* 桃園市 / 桃園區
* 高雄市 / 三民區

For example, 台中市 / 北屯區 has both existing canonical data and proposed
inbound rows. Collision disposition must preserve the canonical rows.

## Phase 2B-2 snapshot and rollback specification

Before any future apply, create timestamped, encrypted, access-controlled
snapshots outside the repository for:

* all candidate transaction rows and every collision counterpart;
* all affected `market_district_period_aggregates` scopes;
* affected `market_region_coverage` rows;
* `market_read_model_metadata` before a scoped rebuild;
* relevant `valuation_import_runs` lineage summaries.

Record table/schema identity, query scope, row count, deterministic ordering,
SHA-256 checksum, capture time, operator, and restoration target. Verify every
snapshot by recounting and rehashing before apply. Restore in reverse dependency
order inside a controlled transaction, validate the same counts and checksums,
then rebuild only affected derived scopes. Any invariant mismatch requires a
rollback before the batch is released.

## Future apply batching design

Phase 2B-2, if later approved, should use small batches grouped by source/import
date, proposed target county, and period. Each batch needs pre-count, snapshot
verification, collision disposition, post-count, canonical validation, scoped
aggregate reconciliation, and rollback on any mismatch. A nationwide full
rebuild is not justified by current evidence.

Ambiguous, unresolved, future-unresolved, and collision rows remain excluded.
Quarantine options, in preferred order, are:

1. A dedicated quarantine table with immutable source identity and reason.
2. A separate access-controlled repair artifact/release quarantine.
3. A temporary exclusion marker only if a reviewed schema contract already
   supports it.

No quarantine schema is created in Phase 2B-1.

## Decision gate

`NOT_READY_FOR_PHASE_2B2`

The snapshot, rollback, affected-scope, and exclusion strategies are defined,
but deterministic authoritative lineage is absent for all 109,236 proposed
rows, 57,547 collision dispositions are unapproved, dedupe regeneration cannot
reconstruct import-time identity, and the future row remains unresolved.
