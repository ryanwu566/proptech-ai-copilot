# PLVR Production Reconciliation Phase 2C.6

## Safety and lineage

- Base main: `619771335d757ed24d9baa3103f636d932e752d6`
- Production access: repeatable-read, read-only PostgreSQL transaction
- `transaction_read_only`: `on`
- Production writes, changed rows, migrations, and schema changes: `0`
- Production snapshot rows: `451672`
- Closing snapshot rows: `451672`
- Snapshot stationary: `true`
- Snapshot SHA-256: `d18823a8e9953fd78598f3aa428b43e302dd1af1ce6d6338ca4ceabbaa6b9d33`
- Clean shadow rows: `517195`
- Clean shadow SHA-256: `2ee0cf968d769a9dd8261031f3f13f6d7c5fcb4c0c33316a22120070806cef57`
- Clean manifest SHA-256: `18203c6347cd2e7c0fd4f274ec1c6e6b3f49cef8d4f890099a01ccacb9d0aa06`

Raw production rows and the SQLite snapshot remain under ignored local storage.
Only aggregate counts, reason codes, and safe hashes are published.

## Evidence hierarchy

- Tier A, authoritative: a persisted official identity key corresponds to one
  clean official transaction identity.
- Tier B, authoritative: deterministic production facts reconstruct and verify
  one clean official transaction identity.
- Tier C, strong fact match: exact normalized geography, period, address
  fingerprint, road, building type, area, prices, and floor facts. It is not an
  official-ID match and remains probable.
- Tier D, probable only: a legacy natural or business key. It is never promoted
  to authoritative evidence.

## Row conservation

Production buckets conserve `451672 / 451672` rows:

| Bucket | Rows | Percent | Evidence summary |
| --- | ---: | ---: | --- |
| AUTHORITATIVE_MATCH | 157608 | 34.89% | Tier A: 145235; Tier B: 12373 |
| GEOGRAPHY_CORRUPT_MATCH | 1 | <0.01% | Tier B reconstructed identity |
| PROVABLE_DUPLICATE | 0 | 0.00% | No A/B multiplicity found |
| PROBABLE_DUPLICATE | 162464 | 35.97% | Tier C exact facts only |
| NOT_IN_CLEAN_SOURCE | 131140 | 29.03% | No clean match |
| FUTURE_ANOMALY | 1 | <0.01% | Tier C only; excluded |
| CONFLICTING | 458 | 0.10% | Multiple Tier C candidates |
| UNCLASSIFIED | 0 | 0.00% | None |

Clean buckets conserve `517195 / 517195` rows:

| Bucket | Rows |
| --- | ---: |
| PRESENT_CORRECTLY | 157608 |
| PRESENT_BUT_PROD_CORRUPT | 1 |
| MISSING_FROM_PROD | 197256 |
| DUPLICATED_IN_PROD | 134 |
| SOURCE_CONFLICT | 0 |
| UNCLASSIFIED | 162196 |

The clean `DUPLICATED_IN_PROD` count is a count of clean identities with
multiple production candidates. Production duplicate counts are row counts,
so they are not expected to equal the clean-side count.

## Legacy cohorts

The canonical-invalid cohort is unchanged at `126087` rows. It reclassifies to
`115113 NOT_IN_CLEAN_SOURCE` and `10974 UNCLASSIFIED`; all other requested
invalid-geography categories are zero. The sum is `126087`.

The old supporting-evidence count was `109236`. The current deterministic
full-snapshot predicate selects `390878` rows: `129679` authoritative,
`141800` probable only, `119033` with no source match, `365` conflicting, and
`1` unclassified. Historical row membership was not persisted, so this is not
an assertion that production added `281642` rows; it is a broader current
recomputation and cannot exactly reclassify the frozen historical cohort.

The old exact duplicate-identity candidate count was `57350`. Current
full-snapshot recomputation selects `58219`: `0` provable duplicates, `186`
probable duplicates, `74` not actually duplicate, `57596` with no clean match,
`363` conflicting, and `0` unresolved. The historical membership was not
persisted, so the `869` difference remains a comparability limitation.

## Duplicate topology

- Authoritative one-to-one clean identities: `157609`
- Authoritative two-row or larger groups: `0`
- Provable duplicate groups and excess rows: `0 / 0`
- Probable Tier C one-to-one identities: `162197`
- Probable Tier C two-row groups: `134`
- Probable Tier C three-plus groups: `0`
- Probable duplicate excess rows: `134`
- Candidate rows associated with invalid geography: `0`

The `162464` probable candidate rows are not all duplicate groups. Most are
one-to-one Tier C matches whose official identity is not proven. Legacy key
collision is not treated as proof.

## Residual classifications

Production-only rows conserve `131140 / 131140`:

- `OUTSIDE_REBUILD_WINDOW`: `11010`
- `PROBABLE_BAD_IMPORT`: `115113`
- `UNRESOLVED`: `5017`
- all other requested subtypes: `0`

Clean-only rows conserve `197256 / 197256`:

- `PREVIOUS_IMPORT_SCOPE_GAP`: `170016`
- `SOURCE_NEWER_THAN_PROD`: `27240`
- all other requested subtypes, including `UNRESOLVED`: `0`

The single `2026-10` production row remains excluded. The clean forensic
artifact and period are present, but matching reaches only Tier C, not an
authoritative identity tier. Its status is `PROD_FUTURE_UNRESOLVED`.

## Aggregate reconciliation

- Production aggregate scopes through the official ceiling: `11017`
- Clean shadow aggregate scopes: `9606`
- Exact scopes: `2938`
- Same-scope value mismatches: `2551`
- Production-only scopes: `5528`
- Shadow-only scopes: `4117`
- Transaction-count absolute delta across mismatched scopes: `98204`
- Mean / maximum absolute average-unit-price delta: `2.60 / 84.96`
- Total-transaction-value absolute delta: `143764410.05`

The former `11018` production baseline included the future scope; this
comparison excludes periods after the `2026-07` official release ceiling.
Geography corruption, probable matches, production-only rows, clean-only rows,
and future exclusion are quantified context, but the mismatched scopes have not
been causally attributed row by row. Aggregate deltas therefore remain a gate
blocker and production aggregates were not rebuilt.

## Gate

`NOT_READY_FOR_SHADOW_CUTOVER_DESIGN`

Blockers:

- `production_conflicts_unresolved`
- `production_only_rows_unresolved`
- `clean_rows_unclassified`
- `probable_duplicate_candidates_unresolved`
- `future_anomaly_identity_unresolved`
- `aggregate_deltas_require_explanation`
- `historical_supporting_cohort_membership_not_reproducible`
- `historical_duplicate_cohort_membership_not_reproducible`

No cutover, repair, backfill, quarantine write, aggregate rebuild, or production
metadata change was performed.
