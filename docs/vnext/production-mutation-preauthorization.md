# Stage 1 Production Mutation Pre-Authorization

Status: **BLOCKED**
Inspected: 2026-09-08 (Asia/Taipei)
Live project: Supabase project ref `flyhsjcynreuofbcdxod`
Authoritative source: `origin/main` at
`a8331e1b30da27b8992ea8f4b040a04666543170`
Readiness source: `ops/stage1-production-readiness` at
`be044ce5ce7c51c55b555bec211b3450bc50d50b`

This is a read-only pre-authorization record. It does not authorize the live
ledger reconciliation or any Stage 1 migration rollout. The live inspection
used project metadata plus `SELECT` queries only. It did not execute
`ops/stage1/reconcile_migration_ledger.sql` and issued no live DDL, DML,
role, grant, Auth, configuration, user, workspace, or feature-flag mutation.

## Decision

| Gate | Result |
| --- | --- |
| Reconciliation Design | **GO** |
| Local Rehearsal | **PASS** |
| Backup/PITR Readiness | **UNVERIFIED** |
| Live JWT Compatibility | **UNVERIFIED** |
| Exposed Schemas | **UNVERIFIED** |
| Operator Readiness | **UNVERIFIED** |
| Live Drift | **NONE** |
| Production Mutation Pre-Authorization | **BLOCKED** |
| Live Ledger Reconciliation | **NOT AUTHORIZED** |
| Production Rollout | **BLOCKED** |

The design and current database preconditions are sound. A request for separate
live mutation authorization is premature until backup/recovery, operator,
peer-review, and exclusive-window evidence is attached. Real-user JWT and Data
API exposure evidence also remain required before feature rollout.

## Live state and drift

The read-only connector returned the expected project ref, project name
`proptech-valuation-db`, region `ap-northeast-1`, status
`ACTIVE_HEALTHY`, PostgreSQL engine 17, and database server 17.6. Project
health is not backup or recovery evidence.

The custom ledger still has exactly six rows and exact previously accepted
schema versions, timestamps, release labels, and historical checksums:

- `001_add_dedupe_key_to_real_price_transactions`
- `002_add_market_direct_query_indexes`
- `002_expand_valuation_import_runs`
- `003_add_market_region_coverage`
- `007_add_schema_migration_ledger`
- `010_add_plvr_generation_schema`

`vnext_core`, `vnext_private`, `compact_green`, and role `vnext_api`
remain absent. All eight unambiguous 008/009 object names remain absent, and
the legacy 003 coverage table has no `release_id` column. Therefore 008,
009, and 013 through 017 have no observed live effects; 011 remains outside
this production-runner path.

The preservation sentinel remains exactly one row with
`id = 1, case_id = 'HISTORY-001'`. Current bounded business counts are zero
for the eight pilot/professional-review tables and one for
`tax_analysis_history`. No business-row content was selected.

### Revalidated forensic fingerprints

| Evidence | Count | MD5 fingerprint |
| --- | ---: | --- |
| 001/both 002 selected columns | 11 | `6dd82bcb2ecc516651cc28c428a16a6d` |
| 001/002 selected indexes | 3 | `6e8bd68e3b5aa27299cdd744376e5439` |
| 003 columns | 6 | `f681f236cccbecce6fd558f1b287e678` |
| 003 constraints | 1 | `96ef2d4cfdc370761570f232265f3939` |
| 003 indexes | 3 | `aa18507695bdb64d22de873942caf89d` |
| 004 columns | 88 | `b04525126e78daaa099fabe0d9e1a77c` |
| 004 constraints | 22 | `397b9530a6fda39661d06cb7ceaca985` |
| 004/005 indexes | 16 | `b165db9aa7dd12f6d1e4b5e3449666b7` |
| 006 columns | 8 | `22f2bd72fccef149e338520c817db037` |
| 006 constraints | 1 | `79a4eb019dd9a52fdd3f34507de1e623` |
| 006 indexes | 3 | `3790479b830d9529b39bf2090076b916` |
| 007 columns | 5 | `a1391c16b5ab6450d4f2980064fcad25` |
| 010 columns | 86 | `5789d4ae6c0ddacc6b7d530fbd412ebb` |
| 010 constraints | 31 | `94d993dd79acebd0197608179756f1b7` |
| 010 indexes | 14 | `c45bab43ebc9e0c353ac85834bdcafad` |
| 010 triggers | 5 | `96ebffe557e94ce747a4a32c3dad5cf9` |
| 010 guard functions and 012 configuration | 4 | `b1b438a22a8191241dbcbb859c497d37` |
| 010 views | 3 | `63a5a1cee8637f7fcc22760796a1779e` |
| 010 comments | 6 | `dd71461d748513bf64bfdc168dd85029` |

Supabase history again returned exact one-statement SHA-256 values for 004, 005,
and 006:
`ba2a3f21605983f13b16648e344e3a71baf677ee7e086d155a39dc9b2220b516`,
`7da6cffddc6a715bfc041fe37eb9ebf19574e30ef5379a4917db6bc634614d3c`,
and `cc0e6bc09b4f0736c6ddb012ff34912db0385339c93d329d39203e696dc3d1c0`.
The deployed 012 statement remains
`be150b2576aca111f0b6bc3075532c4b0808174b912ac46abb5a8409bdfaa6e0`;
its previously proven executable-normalized fingerprint remains
`f19ef88fbd02c95382024b3d7217649ccf98eafad794f18e4030e1a22ad2c2dd`.

The 012 posture remains exact: 22 public base tables, 22 with RLS, zero FORCE
RLS tables, zero policies, and zero prohibited or effective relation,
sequence, routine, or current-owner default-ACL privileges for `PUBLIC`,
`anon`, or `authenticated`. Four PLVR guards retain the expected
security-invoker/search-path fingerprint. The ledger marker comment is exact.
The ledger has no user trigger.

## Reconciliation artifact and blast radius

The only reviewed artifact is
`ops/stage1/reconcile_migration_ledger.sql`, SHA-256
`2ef66850881947cb2c10f3ee0896e4ac7de48828155f9ff2cfe9c03d25f6f409`.
It retains the three warnings `NOT A MIGRATION`,
`NOT AUTHORIZED FOR PRODUCTION EXECUTION`, and
`REQUIRES SEPARATE LIVE MUTATION APPROVAL`. It is outside
`database/migrations`, absent from `database/migration_registry.json`,
and unreachable by the ordinary migration runner.

Its maximum write set is confined to `public.schema_migration_ledger`:

- update exactly 001, both 002 entries, 003, and 007 from their exact
  historical checksums to canonical registry checksums;
- insert exactly 004, 005, 006, and 012 with the reviewed reconciliation
  release label and one transaction timestamp.

It does not modify 010, 008, 009, 011, or 013 through 017. It contains no
business-table, `HISTORY-001`, schema, RLS, role, grant, Auth, or migration
execution write. One serializable transaction, an exclusive ledger-table
lock, exact before-state guards, exact after-state guards, and exceptions
inside the transaction make every mismatch roll back the full write set.

## Backup and PITR

| Required evidence | Classification | Evidence needed |
| --- | --- | --- |
| PITR enabled | UNVERIFIED | Account-specific Database Backups / Point in Time evidence |
| PITR health | UNVERIFIED | Healthy current backup/WAL status for this project |
| Retention window | UNVERIFIED | Earliest and latest recoverable points |
| Latest usable recovery point | UNVERIFIED | Timestamp captured for the approved window |
| Recovery-point age at most 15 minutes | UNVERIFIED | Timestamp and age calculation at execution time |
| Restore/recovery rehearsal at most 90 days old | UNVERIFIED | Dated successful restore record |
| Restore destination | UNVERIFIED | Named isolated target or approved in-place procedure |
| Expected RTO | UNVERIFIED | Owner-approved estimate from rehearsal evidence |
| Expected RPO | UNVERIFIED | Owner-approved objective supported by actual recovery mode |

The available account connector exposed project health, catalog queries, and
migration-history listing, but no read-only backup/PITR endpoint. No Dashboard
backup evidence was available. Do not infer coverage from the healthy project,
PostgreSQL version, plan defaults, or documentation.

An authorized operator must provide a current capture or read-only Management
API result for project `flyhsjcynreuofbcdxod` from
`Database > Backups` and its `Point in Time` settings, including earliest
and latest recovery points and retention. Attach the most recent restore
rehearsal record, destination, outcome, duration, RTO, and RPO. Recheck the
latest recovery point inside the mutation window.

**Backup/PITR Readiness: UNVERIFIED.**

## JWT and exposed schemas

No matching JWT/access-token environment variable was present and the checkout
contains only `.env.example`. No authorized existing production-user token
was therefore available for non-logging validation. No user was created and no
credential was printed, persisted, or transmitted.

**Live JWT Compatibility: UNVERIFIED.** This does not alter the live ledger
preconditions, but it remains a Stage 1 feature-rollout blocker.

The live database session returned no `pgrst.db_schemas` value. The
`authenticator` role and database-role settings contain no manual
`pgrst.db_schemas` override. The available project connector cannot inspect
the Dashboard-managed Data API schema list, so absence of an override is not
proof of the effective exposed schemas.

An authorized project operator must open
`Project Settings > Data API > Exposed Schemas`, capture the effective list,
and confirm that future `vnext_core` and `vnext_private` are excluded.
Recheck for a role-level override if the Dashboard reports it cannot manage
the list. Do not change the setting in this gate.

**Exposed Schemas: UNVERIFIED.**

## Operator principal and change freeze

The future reconciliation principal must be an audited operator/admin database
principal with permission to lock and modify
`public.schema_migration_ledger`. It must not be a browser credential,
normal application user, frontend environment variable, public/publishable
key, service-role API key, or the future `vnext_api` request principal.

Read-only inspection currently reaches database `postgres` as role
`postgres`, which proves the inspected database and role name only. It does
not prove who controls the future credential, how it will be issued, whether
it will still be valid in the approved window, or whether its use has been
peer-reviewed. The approved operator must obtain a short-lived or otherwise
tightly controlled database owner/admin credential through the deployment
secret channel, inject it only into the secured operator process, prevent
shell/history/log capture, and destroy or rotate it after the window. It must
remain separate from application and frontend secrets.

A named operator and a different named peer reviewer must record the project
ref, database, current role, source/artifact hashes, backup evidence, and the
exact command before execution. The peer must review the artifact and evidence
instead of approving an edited console copy.

**Operator Readiness: UNVERIFIED.**

The future window also requires a recorded freeze owner, start/end time, and
acknowledgement that no production migration, database schema deployment,
ledger writer, or release process touching migration history can run
concurrently. If exclusivity cannot be assured, the operation stays blocked.
No such approved window or acknowledgements were available in this gate.

## Future operator walkthrough

This is the exact separately authorized sequence. It is not an execution
instruction for the current gate.

1. Freeze migration, schema-deployment, ledger-writer, and migration-history
   release activity.
2. Confirm project ref `flyhsjcynreuofbcdxod` and database `postgres`.
3. Record `origin/main` SHA
   `a8331e1b30da27b8992ea8f4b040a04666543170`.
4. Record the approved readiness SHA.
5. Record the exact artifact SHA-256
   `2ef66850881947cb2c10f3ee0896e4ac7de48828155f9ff2cfe9c03d25f6f409`.
6. Verify backup/PITR health, retention, current recovery point, approved RTO
   and RPO, and restore evidence.
7. Capture the complete six-row live custom-ledger before image.
8. Capture the bounded `HISTORY-001` sentinel result.
9. Capture every documented history, catalog, security, absence, and
   business-count precondition.
10. Obtain the named peer review approval on the frozen artifact and evidence.
11. Execute only the exact reviewed reconciliation artifact using the approved
    operator principal.
12. Capture the terminal `COMMIT` or `ROLLBACK` outcome without secrets.
13. Verify custom-ledger count equals ten.
14. Verify all ten checksums equal the canonical registry.
15. Verify `HISTORY-001` is unchanged.
16. Verify bounded business counts and the security posture are unchanged.
17. Run the production migration runner in `--dry-run` mode only.
18. Confirm the pending production set is exactly 008, 009, 013, 014, 015,
    016, and 017.
19. Stop. Do not continue into migration rollout under the reconciliation
    authorization.

The audit record must contain the UTC start/end times, operator and reviewer,
project/database/current role, source and artifact hashes, backup/PITR
evidence, freeze acknowledgements, ledger before/after images, sentinel and
business-count results, security/catalog results, transaction outcome,
dry-run output, and incident reference if any guard fails.

## Abort conditions

Every item below means **NO LIVE MUTATION; STOP; REVIEW REQUIRED**:

- wrong live project ref or database;
- backup/PITR unverified or recovery point stale;
- unexpected or missing ledger row;
- checksum, catalog, or security drift;
- `HISTORY-001` mismatch;
- any partial 008/009 effect;
- any unexpected `vnext_core`, `vnext_private`, or `vnext_api`;
- artifact SHA mismatch;
- absent peer reviewer;
- concurrent migration/deployment/ledger activity;
- insufficient operator identity, credential provenance, or audit protection.

Any precondition or postcondition guard failure requires a rollback and a new
review. Do not repair production state inside the same window.

## Expected post-reconciliation state

Only after separate authorization and a successful transaction, the custom
ledger must contain exactly ten canonical rows: 001, both 002 entries, 003,
004, 005, 006, 007, 010, and 012. The subsequent production-runner dry-run
must report exactly 008, 009, 013, 014, 015, 016, and 017 pending. Migration
011 remains excluded, and 018 remains absent.

## Local validation and provenance

The artifact and focused PostgreSQL test are byte-for-byte unchanged from
`be044ce5ce7c51c55b555bec211b3450bc50d50b`, so the accepted fresh
PostgreSQL 17 reconciliation rehearsal was reused: **9 passed in 16.11s**.
That rehearsal proved exact success, rollback on drift, idempotency failure
after application, and preservation checks. This gate reran:

- migration validator: **PASS**, 18 registry entries, 13 managed migrations,
  next sequence 018;
- production runner dry-run: **READY**, 18 registry entries, 13 managed
  migrations, next sequence 018;
- production operations gate: **PASS**;
- `git diff --check`: **PASS**.

No full backend or frontend suite was rerun, as required by this gate.

## Scope

There was no live write, live-ledger mutation, migration execution, role or
schema creation, Auth mutation, user/workspace creation, feature enablement,
Migration 018, product-source change, Hero-worktree change, Stage 2 work, or
NLSC work.

**Production Mutation: NOT AUTHORIZED. Production Rollout: BLOCKED.**
