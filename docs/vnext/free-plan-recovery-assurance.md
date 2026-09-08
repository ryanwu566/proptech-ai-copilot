# Stage 1 Free-Plan Recovery Assurance

Status: **BLOCKED**
Assessed: 2026-09-08 (Asia/Taipei)
Live project: `proptech-valuation-db`
Project ref: `flyhsjcynreuofbcdxod`
Authoritative source: `origin/main` at
`a8331e1b30da27b8992ea8f4b040a04666543170`
Starting readiness source: `ops/stage1-production-readiness` at
`214e4eb1ca62dac37a2190072e40f7792d3171d7`

This gate evaluates a recovery substitute for the bounded custom-ledger
reconciliation. It does not authorize that transaction or any migration.
Live database access remained read-only. No dump content, credential, token,
connection string, or business row is included in this document.

## Decision

| Item | Classification |
| --- | --- |
| Supabase Scheduled Backup | **NOT AVAILABLE** |
| Supabase PITR | **NOT AVAILABLE** |
| Full Logical Backup | **UNVERIFIED** |
| Ledger-only Snapshot | **VERIFIED** |
| Ledger-only Local Restore Rehearsal | **PASS** |
| Full Local Restore Rehearsal | **NOT EXECUTED** |
| Ledger Snapshot Strategy | **VERIFIED** |
| Recovery Assurance | **BLOCKED** |
| Operator | **DEFERRED** |
| Peer Reviewer | **DEFERRED** |
| Change Window | **DEFERRED** |
| Live Ledger Reconciliation | **NOT AUTHORIZED** |
| Production Rollout | **BLOCKED** |

The exact ledger snapshot and transaction rollback paths are sound, but they
do not replace the requested full logical backup and full restore evidence.
The current execution safety boundary correctly rejected copying the entire
live production database to local storage. A protected human-operated full
export and restore rehearsal is therefore still required before recovery
assurance can be GO.

## Accepted Free Plan limitation

The project owner manually verified that Scheduled Backups and Point in Time
Recovery are unavailable on this Free Plan. This is accepted account-state
evidence and was not re-queried. Supabase recommends that Free-tier projects
regularly create their own logical exports with the Supabase CLI or
`pg_dump`; such an export remains a database-level backup, not a complete
Supabase project backup.

## Minimum adequate recovery standard

For this specific operation, all five controls are required:

1. A fresh, exact six-row ledger-before snapshot.
2. A fresh full PostgreSQL custom-format logical dump stored securely outside
   Git.
3. A successful restore of that full archive to disposable PostgreSQL 17.
4. Exact restored-state validation for the ledger, `HISTORY-001`, public
   application catalog, and logically restorable security definitions.
5. The reconciliation artifact's atomic transaction and tested rollback
   guards.

Both backup layers are required. The ledger snapshot is the fastest,
least-invasive source for a narrowly reviewed correction after commit. The
full dump provides broader evidence if the observed effect exceeds the
intended nine ledger rows. Atomic rollback is the primary response before
commit, but it cannot undo a transaction after commit.

This standard applies only to
`ops/stage1/reconcile_migration_ledger.sql`. It does not authorize or provide
adequate recovery assurance for migrations 008, 009, or 013 through 017.

## Executed ledger-only logical snapshot

The safe live export was restricted to
`public.schema_migration_ledger`, whose live marker states that it contains
no secrets or business records. The client used a serializable-deferrable,
read-only `pg_dump` snapshot and never emitted or persisted the database
credential.

| Field | Result |
| --- | --- |
| Executed | Yes, ledger table only |
| Tool | `pg_dump 17.11` |
| Format | PostgreSQL custom, compression level 9 |
| Options | no owner or privilege restoration; no password prompt |
| Created UTC | `2026-09-08T04:35:47.8656768Z` |
| Dump duration | 4.107 seconds |
| File size | 3,776 bytes |
| SHA-256 | `2a4434580f5aa96d80ef0083dfc13908cb9e6a6d4d8c81afc52a20a38e1f486e` |
| File | `stage1-ledger-snapshot-flyhsjcynreuofbcdxod-20260908T043547Z.dump` |
| Storage class | Local, outside every Git repository |

The artifact is under
`C:\Projects\proptech-recovery-artifacts\`. Treat it as sensitive
production operational metadata: access-controlled local storage only; no
Git, cloud upload, documentation attachment, or external transmission.

The archive integrity listing passed before restore. The readiness worktree
remained clean after artifact creation, proving that no backup was added to
Git.

## Executed ledger-only restore rehearsal

The archive was restored to a fresh local database named
`vnext_recovery_rehearsal_20260908` on PostgreSQL 17.11. The disposable
cluster is outside the repository at
`C:\tmp\stage1-freeplan-ledger-restore-pg17-20260908T043735Z` and was
stopped after verification.

| Measurement | Result |
| --- | --- |
| Restore duration after server readiness | 0.189 seconds |
| Verification duration | 0.220 seconds |
| Exact six ledger rows and fields | PASS |
| Ledger column count/fingerprint | 5 / `a1391c16b5ab6450d4f2980064fcad25` |
| Primary constraint | 1 |
| Indexes | 2 |
| RLS enabled / FORCE | true / false |
| User triggers | 0 |
| Ledger security marker | exact |
| Local server stopped | true |

This rehearsal proves archive integrity and exact recovery of the bounded
ledger snapshot. It intentionally did not contain
`public.tax_analysis_history`; therefore it did not restore or prove
`HISTORY-001`, the 004/005/006 catalog, PLVR functions/triggers/indexes, or
the broader 012 posture. Those omissions are why the full recovery gate
remains blocked.

## Full logical backup requirement

**Full Logical Backup: UNVERIFIED. Full Restore Rehearsal: NOT EXECUTED.**

The available credential could reach production read-only, but this execution
environment did not permit copying the full production dataset into a local
artifact. Do not bypass that control or approximate a full backup with
unreviewed table selections.

An authorized human operator must perform the full dump from a secured
workstation or separately authorize a controlled full-data export. Requirements:

- PostgreSQL 17 `pg_dump`, version equal to or newer than the 17.6 server;
- custom format with compression and a serializable-deferrable snapshot;
- ephemeral `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`,
  `PGPASSWORD`, and `PGSSLMODE=require` supplied by the approved secret
  channel;
- no database URL or password in command arguments, shell history, output,
  filenames, or documentation;
- archive created outside Git on encrypted or equivalently access-controlled
  local storage;
- owner and ACL metadata retained in the archive for inspection;
- `pg_restore --list`, SHA-256, size, UTC snapshot start/end, client/server
  versions, and source project ref recorded;
- immediate credential removal from the process environment.

The reviewed command shape is:

```powershell
# NOT AUTHORIZED HERE - OPERATOR TEMPLATE ONLY
# PG* values are injected out of band and must never be echoed.
pg_dump --format=custom --compress=9 --serializable-deferrable `
  --no-password --file $approvedDumpPath
```

The operator must then restore that exact hash into a fresh disposable local
PostgreSQL 17 database. For portability, owner/ACL application may be skipped
during rehearsal with `pg_restore --no-owner --no-privileges`, while the
archive listing and independent live catalog snapshot retain the security
evidence. Any missing extension, dependency, definition, or data fails the
gate rather than being silently excluded.

### Full restore validation

The full rehearsal must prove:

- exact six-row ledger identity, schema version, timestamp, release, and
  checksum fields;
- exactly one `id=1, case_id='HISTORY-001'` sentinel without exposing its
  other contents;
- expected public base-table count and the documented 001 through 012 catalog
  fingerprints;
- 004 columns/constraints, combined 004/005 indexes, and 006
  columns/constraints/indexes;
- PLVR functions, triggers, views, comments, critical indexes, and
  constraints;
- RLS-enabled flags and policies that the logical format can recreate;
- an archive inventory of ownership, ACL, and default-privilege entries, with
  separate comparison to the live read-only 012 security snapshot when those
  entries cannot safely be applied to a vanilla local cluster;
- no unexpected missing definition and no unexplained restore warning.

Record dump duration, restore duration, verification duration, and the
complete bounded pass/fail report. A partial or warning-tolerant restore is
not PASS.

## Platform state not covered

A PostgreSQL logical archive is not a full Supabase project backup. It cannot
by itself guarantee or restore:

- Supabase Auth provider and email configuration;
- API, publishable, secret, service-role, and JWT signing keys;
- Dashboard and project settings, including Data API Exposed Schemas and
  automatic table exposure;
- platform backup/PITR state and retention;
- historical platform, database, Auth, or API logs;
- Storage object bytes outside PostgreSQL metadata;
- Edge Function code, configuration, and deployed secrets;
- external provider credentials, webhooks, DNS, custom domains, and other
  infrastructure configuration;
- cluster-global roles/passwords and every hosting-managed privilege;
- Realtime publications/replication state where platform-managed;
- an in-place hosted restore service or a measured hosted recovery time.

These limitations are acceptable only for assessing the narrow ledger-only
transaction. They are not acceptable as generalized recovery assurance for
the subsequent migration rollout.

## Reconciliation-specific recovery paths

1. **Transaction rollback before commit:** primary and fastest. Any artifact
   guard failure raises inside its single transaction and rolls back both
   ledger statements. Capture the terminal rollback and stop.
2. **Exact ledger correction after commit:** if an unexpected problem is
   discovered after commit, freeze all writers and use the freshly captured
   ledger-before snapshot as the sole source for a separately reviewed,
   separately authorized inverse transaction. The draft would delete only
   the four exact baseline rows and restore only the five exact historical
   checksums, with before/after guards. **NOT AUTHORIZED; DRAFT ONLY.** No live
   rollback SQL was generated or executed in this gate.
3. **Full logical restore evidence:** proves the broader database archive is
   usable and supplies disaster-recovery material if the effect is not
   confined to the ledger. Do not restore a full archive into live production
   merely to correct nine ledger rows.

## Future pre-mutation snapshot

Immediately before any separately authorized reconciliation:

1. Start the recorded deployment/migration freeze.
2. Create the full custom-format logical dump and verify its hash/inventory.
3. Capture all six ledger rows with `migration_id`, `schema_version`,
   `applied_at`, `release_version`, and `checksum` into an
   access-controlled audit artifact.
4. Create a fresh table-only custom-format ledger archive.
5. Capture only the bounded `id=1, case_id='HISTORY-001'` sentinel result.
6. Capture the current business counts and catalog/security fingerprints.
7. Confirm no database/schema/ledger change occurred since the dump snapshot.
8. Obtain peer approval of the exact hashes and evidence.

Do not include unrelated business rows in the ledger audit record.

## Freshness, RPO, and timing

Both the full dump and ledger snapshot must complete no more than 15 minutes
before the reconciliation starts. The freeze must cover the full dump's MVCC
snapshot through final postcondition capture. Fifteen minutes is the maximum
because the accepted live precondition is an exact six-row state, and without
PITR any unrelated change after the snapshot would create an unprotected
recovery gap. If the full dump cannot complete and be validated inside that
window, stop and redesign the window.

The ledger snapshot strategy provides a planned zero-row-loss RPO for the nine
intended ledger changes only, provided the freeze holds. It makes no RPO claim
for concurrent business activity or platform state.

Measured local mechanics:

- ledger snapshot: 4.107 seconds;
- ledger restore after server readiness: 0.189 seconds;
- ledger verification: 0.220 seconds.

These measurements support a provisional operational target of at most 30
minutes for a separately authorized ledger correction once the operator,
reviewer, credential, and freeze are active. They do not measure or guarantee
a full production-database RTO. Full-database RTO remains unverified until the
protected full restore rehearsal is performed and its initialization,
extension, restore, and validation times are recorded.

## Exposed schemas and JWT

The project owner manually verified the current Data API Exposed Schemas as
`graphql_public` and `public`. `vnext_core` and `vnext_private` remain
absent. Therefore the current VNext exposure state is
**VERIFIED_SAFE**.

`Automatically expose new tables` is **ON**. It was not changed. It remains
a mandatory review item before later schema rollout; this gate does not
generalize current safety to future VNext schemas.

**Live JWT Compatibility: UNVERIFIED.** No production user was created and no
token work was performed. JWT compatibility remains a feature-enablement
blocker but is not independently a ledger-reconciliation blocker.

## Deferred human preconditions

- Operator: **DEFERRED / REQUIRED BEFORE LIVE AUTHORIZATION**
- Peer reviewer: **DEFERRED / REQUIRED BEFORE LIVE AUTHORIZATION**
- Change window: **DEFERRED / REQUIRED BEFORE LIVE AUTHORIZATION**

These are intentionally deferred, not failed. No identity or schedule was
invented.

## Failure and stop conditions

Recovery Assurance remains blocked if any of the following applies:

- the protected full logical dump cannot be obtained;
- archive SHA/inventory validation fails;
- the full restore fails or reports unexplained omissions;
- restored ledger or `HISTORY-001` differs;
- required database definitions are unexpectedly absent;
- client/server or extension incompatibility appears;
- credential handling or artifact storage is unsafe;
- either backup is older than 15 minutes at the eventual operation;
- the freeze, operator, or peer-review evidence is absent.

Every failure means no live mutation, stop, and review.

## Future authorization checklist

Before requesting separate live reconciliation authorization, attach:

- full dump metadata and SHA-256, without the dump content;
- successful full PostgreSQL 17 restore and exact validation report;
- fresh ledger snapshot metadata and SHA-256;
- bounded ledger-before and `HISTORY-001` evidence;
- accepted full restore RTO and ledger-specific RTO/RPO;
- secure storage/custody confirmation and deletion/retention owner;
- named operator, peer reviewer, freeze owner, and window;
- current source, readiness, and reconciliation artifact hashes.

The reconciliation artifact remains unchanged at SHA-256
`2ef66850881947cb2c10f3ee0896e4ac7de48828155f9ff2cfe9c03d25f6f409`.

## Scope

No live write, live-ledger mutation, migration, role/schema/user/workspace
creation, Auth change, feature enablement, Migration 018, product-source
change, Hero-worktree change, Stage 2, or NLSC work occurred. No backup
artifact was committed to Git.

**Recovery Assurance: BLOCKED. Live Ledger Reconciliation: NOT AUTHORIZED.
Production Rollout: BLOCKED.**
