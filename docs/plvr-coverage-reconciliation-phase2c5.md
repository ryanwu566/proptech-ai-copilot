# PLVR Coverage Closure and Production Reconciliation

## Scope and safety

Phase 2C.5 closes the source-coverage interpretation gaps from the clean PLVR
rebuild and adds an executable production row-level reconciliation path. It
does not authorize or perform a production cutover.

Production access is fail-closed and SELECT-only. The runtime opens a
repeatable-read, read-only PostgreSQL transaction, uses bounded stable-key
pages, and writes only to ignored local SQLite files. It has no production
`INSERT`, `UPDATE`, `DELETE`, DDL, migration, table swap, aggregate rebuild, or
quarantine path. Raw production snapshots and official ZIPs must not be
committed.

## Expected official coverage

Coverage is derived from verified artifact release metadata and embedded
official package scope. It is not derived from the current calendar date or
from the presence of transaction rows.

- Complete season evidence settles transaction periods through `2026-05`.
- Verified incremental releases prove an official availability ceiling of
  `2026-07`.
- `2026-06` and `2026-07` remain `PARTIAL` because no complete season settles
  them.
- `2026-08` is `NOT_YET_EXPECTED` and is excluded from the expected-coverage
  denominator.
- An expected verified scope with zero eligible building transactions remains
  complete source coverage; it is not a missing artifact and not a zero-price
  market observation.

The 792 city-period matrix contains 726 `COMPLETE`, 44 `PARTIAL`, zero
`MISSING`, 22 `NOT_YET_EXPECTED`, and zero `NOT_APPLICABLE` scopes. Raw
calendar coverage is 91.67%; expected-official coverage is 94.29%.

The `20260701`, `20260711`, and `20260721` history packages are valid official
incremental releases whose embedded manifests omit the Lienchiang member.
They are classified `PARTIAL_BY_OFFICIAL_RELEASE`, not as failed downloads.
The reviewed coverage matrix is published at
`artifacts/plvr_coverage_matrix.json`.

## Geography findings

The official Hsinchu City and Chiayi City members represent the geography as
the city itself rather than a lower district. Phase 2C.5 therefore adds an
explicit `city_level` geographic-unit kind for those two official source
members only. It does not fabricate districts from addresses and does not
relax the normal district contract for any other county or city.

- Hsinchu City: 22,080 source rows, 9,856 publishable rows in the rebuild
  window, one city-level geographic unit.
- Chiayi City: 10,819 source rows, 5,552 publishable rows in the rebuild
  window, one city-level geographic unit.
- Lienchiang County: 314 source rows are present. All are excluded as either
  non-building transactions or missing-location rows, so zero publishable
  building transactions is source-proven rather than an acquisition gap.

The existing canonical validator remains strict by default. City-level
handling is an explicit shadow-rebuild option and cannot silently enter the
production importer.

## Clean shadow result

The rebuild used the same 17 checksum-verified local official artifacts from
Phase 2C; no source was downloaded again. It read 1,106,777 rows and produced
517,195 publishable rows across 21 cities and 325 geographic units, covering
`2023-09` through `2026-07`. It produced 9,606 aggregates.

Every publishable row has an artifact hash, source-row hash, and official
identifier. The two previously conflicting official identities have one
immutable transaction anchor each and differing corrected numeric facts in a
later official artifact. The latest artifact revision is selected
deterministically; two revision groups are resolved and zero source-identity
conflicts remain unresolved. Ten duplicate source-identity excess rows remain
accounted for without being treated as ten publishable duplicates.

Three source-confirmed future rows remain in the forensic table only. There
are zero future publishable transactions and zero future publishable
aggregates.

## Row-level runtime

Run the reconciliation only in an approved environment that supplies the
named database setting without printing it:

```powershell
python scripts/reconcile_plvr_shadow_with_production.py `
  --production-access select-only `
  --main-sha 8fb8158beabd98f5a656bb1f2d6009f3d6b87243
```

The runtime first captures a local snapshot with:

- snapshot time and source filter;
- expected and observed production row count;
- `id > last_id` keyset pagination;
- first and last stable keys, page count, and deterministic snapshot hash;
- main commit and clean-manifest hash.

It then classifies each local production and clean row with strict evidence
tiers. Official or reconstructed official identity is authoritative. Exact
business facts without official identity are probable only. Raw addresses can
exist in the ignored ephemeral snapshot for matching, but never appear in the
committed summary.

The current execution environment had no approved row-level PostgreSQL
connection setting. The CLI correctly stopped with
`production_read_runtime_not_configured`. A separate SELECT-only aggregate
observation reverified 451,672 official production transactions, 11,018
production aggregates, and one future transaction/aggregate, but these counts
are not substituted for row-level reconciliation.

## Gate

The result remains `NOT_READY_FOR_SHADOW_CUTOVER_DESIGN` because expected
official coverage is partial and the production row-level runtime could not be
executed here. Production-only, clean-only, geography-corruption, and duplicate
cohorts must not be promoted from the prior baselines until the row-level
snapshot completes.

Do not update production rows, apply migrations, replace tables, rebuild
production aggregates, or start a cutover from this result.
