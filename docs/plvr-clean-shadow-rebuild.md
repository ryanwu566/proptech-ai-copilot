# Authoritative PLVR Clean Shadow Rebuild

## Purpose

This workflow reacquires official PLVR sale-main artifacts and builds a local,
traceable shadow dataset. It does not repair, replace, or aggregate production
tables. A successful shadow build is evidence for a later cutover design; it is
not authorization to mutate production.

## Source and rebuild scope

- Source agency: Ministry of the Interior, Department of Land Administration.
- Dataset page: the official data.gov.tw PLVR sale dataset.
- Download host allowlist: `plvr.land.moi.gov.tw`, HTTPS only.
- Product retention contract: rolling 36 months.
- Phase 2C rebuild window: `2023-09` through `2026-08`, evaluated as of
  `2026-08-11`.
- Explicit source scope: seasons `112S3` through `115S2`, history releases
  `20260701`, `20260711`, `20260721`, `20260801`, and current release
  `20260811`.

The source scope is deliberately bounded. The tool does not default to
downloading all historical PLVR data.

## Acquisition

Inventory is the default. Adding `--download` is an explicit operator action.

```powershell
python scripts/acquire_official_plvr_artifacts.py `
  --season 112S3 --season 112S4 `
  --season 113S1 --season 113S2 --season 113S3 --season 113S4 `
  --season 114S1 --season 114S2 --season 114S3 --season 114S4 `
  --season 115S1 --season 115S2 `
  --history 20260701 --history 20260711 `
  --history 20260721 --history 20260801 `
  --current-release 20260811
```

Review the inventory before repeating the command with `--download`.
Downloads are streamed to unique partial files, bounded to 512 MiB per
artifact, SHA-256 hashed, ZIP-checked, parser-checked, and atomically renamed.
An existing artifact is never overwritten unless its checksum matches a
reviewed expected hash or the prior manifest.

The official TLS chain is validated, including hostname verification. The
transport disables only OpenSSL's legacy-certificate strict-extension flag
because the official chain omits Subject Key Identifier metadata; certificate
verification itself remains mandatory.

Raw ZIPs and the runtime manifest remain under `data/raw/plvr/phase2c`. That
directory, temporary extraction paths, SQLite shadows, and pytest temporary
paths are gitignored. Raw PLVR rows and artifact bytes must never be staged.
The reviewed, non-row manifest is published as
`artifacts/plvr_source_manifest.json`.

## Verification and partial scope

Artifact integrity and geographic coverage are separate states.

- A seasonal ZIP must contain all expected city members or it is rejected.
- A valid history/current incremental ZIP may be verified while retaining
  `PARTIAL_AUTHORITATIVE` coverage when an expected city member is absent.
- The 20260701, 20260711, and 20260721 increments omit the Lienchiang member.
  They remain verified artifacts with partial coverage; the coverage matrix
  must not promote that scope to complete.

The committed manifest contains no local absolute path, credential, database
setting, or transaction row.

## Clean shadow build

```powershell
python scripts/build_plvr_clean_shadow.py `
  --since 2023-09 `
  --until 2026-08 `
  --as-of-date 2026-08-11 `
  --normalized-at 2026-08-11T00:00:00+00:00
```

The default target is the local ignored SQLite database at
`data/processed/plvr/phase2c/clean-shadow.sqlite3`. The build reuses the
existing PLVR CSV reader, row normalizer, canonical geography guard, future
period guard, and dedupe-v2 key builder. It writes in bounded batches and
publishes the SQLite file only after finalization and invariant checks pass.

The shadow separates:

- source-row identity: artifact SHA, official identifiers, and canonical raw
  row serialization;
- normalized business dedupe: canonical transaction facts and existing
  dedupe-v2 semantics.

The source forensic table retains rejected/future evidence. The publishable
transaction and aggregate tables never contain a future period.

## Phase 2C observed result

- 17 required artifacts, 17 verified, 253,796,255 bytes.
- 1,106,777 raw rows read and 501,785 accepted transactions.
- 25,390 invalid geography, 3 future-period, 271,713 non-building, 579
  abnormal-unit-price, 174 invalid-area, 2 invalid-price, 29,384
  missing-location, and 277,743 pre-window exclusions.
- 10 duplicate source identities and 2 conflicting source identities.
- 501,785 accepted rows have artifact hash, source-row hash, and official ID.
- 9,536 district-period aggregates across 323 districts and 19 cities,
  spanning `2023-09` through `2026-07`.
- Coverage matrix: 12,012 complete and 1,236 partial cells; complete through
  `2026-05`; 90.67% complete.
- Canonical invalid accepted geography: 0.
- Publishable future transactions and aggregates: 0.

Hsinchu City and Chiayi City official rows use the city name itself as the
raw district label. The product registry requires their true administrative
districts. The source does not safely prove that mapping, so 25,390 rows are
excluded instead of deriving a district from address text. Lienchiang has no
accepted building transaction in this source set. These are coverage blockers,
not zero-market observations.

## Production reconciliation boundary

Production was queried only for aggregate counts. Phase 2C made zero
production writes. The local runtime did not expose a production row-stream
connection, so row-level reconciliation was not run and the prior 109,236
geography candidates and 57,350 probable duplicates are not promoted.

`--reconcile-production` is opt-in. When a later operator supplies an approved
runtime connection, `ReadOnlyProductionRepository` enforces PostgreSQL
read-only mode, a statement timeout, SELECT-only SQL, bounded fetches, and
resource closure. Reconciliation output must remain aggregate-only.

## Gate

The observed gate is `NOT_READY_FOR_SHADOW_CUTOVER_DESIGN` because source
coverage has material geographic gaps and production row-level reconciliation
is unavailable. Do not delete, truncate, rename, migrate, swap, import, or
rebuild production tables or aggregates from this result.
