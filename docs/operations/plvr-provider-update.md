# PLVR provider update operations

Local software status: **READY FOR PRODUCTION ACCEPTANCE**. Production database,
workflow environment permissions, reviewed release checksum, deployment identity
and scheduler acceptance remain required. This branch ran local fixtures only.

The updater writes BLUE `real_price_transactions` and `valuation_import_runs`.
It does not switch GREEN, rebuild Market aggregate/read models, reconcile coverage,
or claim that those separate capabilities have refreshed. Run their existing
reviewed operations independently after acceptance where needed.

## Acquire and review one release

Run outside the web-service runtime. Inventory makes official metadata requests;
download is explicitly enabled and makes one bounded official acquisition with
no retries. Acquire only a specified release and bind a reviewed SHA256:

```powershell
python scripts/acquire_official_plvr_artifacts.py --current-release 20261001 --output-dir data/raw/plvr/update --manifest data/raw/plvr/update/source_manifest.json
python scripts/acquire_official_plvr_artifacts.py --current-release 20261001 --download --expected-sha256 moi-plvr-sale-current-20261001=<reviewed-sha256> --output-dir data/raw/plvr/update --manifest data/raw/plvr/update/source_manifest.json
python scripts/update_valuation_data.py --manifest data/raw/plvr/update/source_manifest.json --artifact-id moi-plvr-sale-current-20261001 --city 台北市 --since 2023-11 --until 2026-10 --dry-run
```

Replace the example dates with the actual approved release and rolling 36-month
scope. Repeat `--city` for multiple cities. Historical and seasonal manifests
from the same acquisition script are supported. The current-release date is an
operator label for a mutable official endpoint; the reviewed checksum provides
the immutable binding. A self-generated checksum proves integrity, not official
publication authenticity; approve provenance before import.

The command verifies manifest checksum, official release identity and URL,
artifact checksum, ZIP safety, main-file headers, requested city members, source
period bounds, normalizer integrity and the existing importer quality gate.
Both warnings and blocked quality outcomes stop acceptance. A single malformed
date, future transaction, invalid geography, missing location, invalid area/price
or nonfinite normalized metric stops the entire scope regardless of percentage.
Failed acceptance reports safe exclusion reason counts. Legitimate
non-building exclusions remain counted; transaction-window filtering is reported
separately from the acceptance denominator. No row-limit truncation is accepted.

Dry-run is the default, never connects to any database, and never creates a
destination database even when production credentials exist. All output is bounded
metadata without addresses, raw provider responses, DSNs or credential values.
`source_release`, `newest_transaction_period` and `imported_at` remain separate.
Dry-run freshness is explicitly a transaction-period projection with no import
timestamp; recent publication does not make old transactions fresh.

## Accept, retry and audit

For a disposable local integration fixture only, add `--import --fixture-db
.local/plvr-update-fixture.sqlite`. CI uses temporary SQLite files and local ZIP
fixtures; it must never inject production credentials into fixture tests.

For the optional real-SQL integration test, initialize a fresh disposable
loopback PostgreSQL database whose name starts with `plvr_update_test`, set
`PLVR_UPDATE_TEST_URL` and `PLVR_UPDATE_TEST_DISPOSABLE=1`, then run
`python -m pytest -q tests/test_plvr_provider_update.py -k postgres`.
The test creates and removes its own unique schema, proves rollback across a
201-row/two-chunk import when final ledger acceptance fails, then proves recovery
and duplicate-release behavior. Without that separate disposable contract it
skips; ordinary tests never inherit application database credentials. Local
verification on this branch passed against an isolated PostgreSQL 17 cluster,
which was stopped afterward. This is deterministic integration evidence and
does not establish production connectivity or deployed acceptance.

For a reviewed production run, inject `PLVR_UPDATE_DATABASE_URL` through the
protected environment secret and set `PLVR_UPDATE_ENVIRONMENT` to exactly
`production-market-import`. Add `--import` to the reviewed dry-run command.
Missing or invalid contracts exit 2 with a safe reason code. Never put a DSN on
the command line. The protected `.github/workflows/import-official-market-data.yml`
supports manual dry-run and import on main, with explicit release/checksum/scope.
Scheduled executions emit a readiness notice without acquisition or mutation.
Enable recurring imports only after choosing and accepting an authoritative
release/checksum handoff; scheduling acceptance remains an external requirement.

Production prerequisites: apply existing valuation schema/migrations including
the unique source/dedupe index; allow the import role to create the small
`plvr_update_releases` ledger or provision its equivalent reviewed schema from
`LEDGER_SQL` in the service; grant insert/select on that ledger and existing
transaction/import-run tables. PostgreSQL runs use one transaction for all
staging chunks, transaction rows, acceptance ledger and completed import audit.
A failure in the final acceptance/audit write rolls back every new row. There
is no scope replacement, intermediate commit or automatic retry.

Release identity includes artifact id and exact city/month scope. The unique
ledger and PostgreSQL advisory lock serialize updater runs. Same release/scope
and checksum is an idempotent success, returns the original import time, and
recomputes current freshness. Changed checksum for the same identity fails
closed: investigate a source correction and approve a distinct release identity;
do not delete the ledger to force reacceptance. Repeated facts in different
releases retain the existing importer's natural and source/dedupe guards.

Record the deployed importer SHA, the final JSON result and run identity in the
operator evidence store. JSON carries source release, checksums, scope, count,
acceptance status and transaction freshness. A duplicate release does not add
a new completed import record or reset dataset freshness.

## Retention is a separate operation

After import acceptance, use the existing guarded command independently against
the approved BLUE destination via `VALUATION_DATABASE_URL`. Save its JSON output
as separate retention evidence:

```powershell
python scripts/prune_valuation_data.py --before 2023-11 --cities 台北市 --dry-run
# Only after reviewing the separate deletion scope:
python scripts/prune_valuation_data.py --before 2023-11 --cities 台北市 --confirm-delete
```

The example retains 2023-11 through 2026-10 inclusive. Import never calls pruning,
changes retention audit history or deletes old rows. Query-time retention remains
required regardless of whether this operation has run. The existing pruning
command prints a configuration notice and exits 0 when its credential is absent;
operators must require `status=deleted`/`dry_run` evidence, not exit code alone.

## Bounds and recovery

Defaults: 256 MiB compressed archive, twice that total decompressed size, at most
256 ZIP members, 100,000 parsed rows, 240-second cooperative runtime deadline.
Hard maxima are 512 MiB, 500,000 rows and 600 seconds. Byte limits apply before
shared verification and parsing. The existing parser loads one member at a time;
row count is checked before normalization. Split larger official scope into
approved city/month runs; never accept a prefix of a release because of a limit.
PostgreSQL connection timeout is 10 seconds, statement timeout 30 seconds and
lock timeout 5 seconds. CI/workflow wraps processing with a 300-second hard
process limit; use an equivalent supervisor deadline for local scheduled jobs.
The cooperative deadline alone cannot interrupt a parser or blocked library call.

Before production import, retain a recoverable database snapshot under the
existing backup policy. On timeout, failure or uncertain client disconnect:
stop, inspect the ledger by `release_key` using a read-only connection, and
rerun the exact reviewed command once only after inspection. An accepted ledger
proves atomic acceptance; an absent ledger means retry is safe because there
are no committed intermediate chunks. Do not assume absence merely from a
client timeout while the server transaction may still be completing.

For a bad but successfully accepted source, stop further imports and use the
reviewed database snapshot/restore process. The updater has no destructive
rollback command because deduplicated rows may be shared with older releases;
deleting by period or imported timestamp would erase unrelated evidence.
Retention recovery uses the pre-retention snapshot separately. Preserve ledger,
source manifest, checksum and acceptance evidence during recovery.
