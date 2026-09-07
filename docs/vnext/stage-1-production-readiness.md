# Stage 1 Production Rollout Readiness

Status: preparation gate complete; production rollout blocked
Prepared: 2026-09-07 (Asia/Taipei)
Authoritative source: `origin/main` at `a8331e1b30da27b8992ea8f4b040a04666543170`
Preparation branch: `ops/stage1-production-readiness`

This is an operator runbook and evidence record. It is not production deployment
authorization. The checks documented here did not apply a live migration, create or
alter a live role or user, change Auth, enable a feature, or mutate a live table.

## Decision

- Stage 1 Code Gate: **GO — VERIFIED**
- Stage 1 Main Integration: **GO — VERIFIED**
- Production Readiness Gate: **GO — VERIFIED for preparation only**
- Production Rollout: **BLOCKED**

Production remains blocked until every mandatory item marked `UNVERIFIED` below is
re-checked and changed to `VERIFIED` in an explicitly authorized rollout window. No
item was classified `INCOMPATIBLE`; the live migration-ledger state is an unresolved
operational boundary, not evidence that the frozen migrations are invalid.

## Prerequisite matrix

| Prerequisite | Classification | Evidence / required closure |
| --- | --- | --- |
| Signed Stage 0/1 architecture and exit gates | VERIFIED | Re-read the nine signed VNext architecture, signoff, and role-provisioning documents at the stated main SHA. |
| Stage 1 source and migration immutability | VERIFIED | Focused gates pass; 013–017 match frozen SHA-256 values; no 018 exists. |
| Current live VNext database pre-state | VERIFIED | Read-only catalog transaction: no `vnext_core`, no `vnext_private`, no `vnext_api`, and no 013–017 custom-ledger rows. |
| Public live JWKS algorithm/key shape | VERIFIED | Public endpoint has one verification key: ES256, EC P-256, with `kid` and `key_ops=[verify]`. |
| Backend verifier contract | VERIFIED | RS256/ES256, `kid`, JWKS rotation/cache, expiry, issuer, audience, UUID `sub`, and privileged-token rejection are implemented and focused tests pass. |
| Actual live user-token claims | UNVERIFIED | No authorized existing user access token was available. Do not create a user solely for this gate. |
| LIVE JWT COMPATIBILITY | UNVERIFIED | Requires a non-logging verification of one authorized existing real user token against the deployed issuer/audience and public JWKS. |
| Browser session implementation contract | VERIFIED | Current Supabase storage key/session shape and refresh semantics match the implementation; lifecycle hardening harness passes. |
| Deployed browser configuration and real session | UNVERIFIED | Requires the controlled real-user smoke step after approved environment variables are set. |
| Migration files and disposable rehearsal | VERIFIED | PostgreSQL 17 clean apply, production-prefix upgrade, 016→017, repeat runner, ledger, FK, FORCE RLS, ownership, grants, trigger `search_path`, and tenant isolation pass. |
| Live custom-ledger reconciliation / exact pending set | UNVERIFIED | Live catalog contains some unledgered historical migrations; an authorized operator must approve the exact 11-migration pending set or approve a separately reviewed reconciliation mechanism before running the runner. |
| `vnext_api` contract | VERIFIED | Frozen SQL, provisioning document, runtime fail-closed checks, and local PostgreSQL catalog proof agree. |
| Live `vnext_api` provisioning | UNVERIFIED | Role is correctly absent before rollout; later create/provision/verify it under explicit authorization. |
| VNext Data API architecture | VERIFIED | Browser → FastAPI → direct `vnext_api` PostgreSQL connection; no browser Data API table/RPC path is required. |
| Current VNext schema exposure | NOT APPLICABLE | The VNext schemas do not yet exist live. Post-migration Dashboard exposure settings remain an `UNVERIFIED` rollout check. |
| Live tenant/RLS smoke matrix | UNVERIFIED | Must run with controlled users/workspaces only after migration and role/JWT verification. |
| Feature defaults in source | VERIFIED | `FEATURE_IDENTITY_V1=false` and `FEATURE_LEGACY_CASE_IMPORT_V1=false`. |
| Deployed feature-flag state | UNVERIFIED | Verify both runtime variables are explicitly false immediately before and after deployment. |
| Backup/PITR checkpoint and recovery owner | UNVERIFIED | Record a current restorable checkpoint, recovery target, retention, recovery owner, and expected downtime before DDL. |
| Production alerts/dashboards | UNVERIFIED | Privacy-safe request telemetry exists, but category-specific dashboards and alert routing were not available for verification. |

## Live database state — read only

The inspected connection resolved to the current Supabase production candidate for
project ref `flyhsjcynreuofbcdxod`. Every SQL inspection ran inside `BEGIN TRANSACTION
READ ONLY` and ended with `COMMIT`; no write statement was issued.

| Check | Exact observed result | Classification |
| --- | --- | --- |
| `vnext_core` | absent | VERIFIED |
| `vnext_private` | absent | VERIFIED |
| `vnext_api` | absent | VERIFIED; expected before rollout |
| custom-ledger 013–017 rows | 0 | VERIFIED |
| custom-ledger total | 6 rows | VERIFIED |
| public base tables | 22; all 22 have RLS enabled; 0 use FORCE RLS | VERIFIED current legacy posture |
| `PUBLIC` / `anon` / `authenticated` public-table grants | 0 catalog grants | VERIFIED current legacy posture |

The six custom-ledger IDs remain:

1. `001_add_dedupe_key_to_real_price_transactions`
2. `002_add_market_direct_query_indexes`
3. `002_expand_valuation_import_runs`
4. `003_add_market_region_coverage`
5. `007_add_schema_migration_ledger`
6. `010_add_plvr_generation_schema`

`HISTORY-001` is a signed preservation requirement, not a live catalog object. It is
**VERIFIED untouched by this gate**: the signed Stage 1 exit record remains unchanged,
the historical six-row live ledger set remains present, and this gate used no live
write-capable SQL. No claim is made that the label itself can be queried from Postgres.

### Live ledger boundary that must be resolved

The production runner manages 13 migrations. The live custom ledger records only 007
and 010 from that set. Read-only catalog inspection found:

- 004–006 artifacts already present, including all five inspected 005/006 indexes;
- migration 012's effective posture already present (all public base tables have RLS,
  and no public-table grants remain for `PUBLIC`, `anon`, or `authenticated`); the
  signed security closure also records 012 in Supabase migration history;
- 008–009 artifacts absent;
- 013–017 artifacts absent.

Consequently, the current runner would treat these 11 IDs as pending:

```text
004_add_pilot_evidence
005_add_pilot_security_indexes
006_add_tax_analysis_history
008_add_official_market_pipeline
009_separate_official_market_region_coverage
012_security_rls_deny_by_default
013_vnext_workspace_case_foundation
014_vnext_property_graph_evidence_foundation
015_vnext_identity_resolution_candidates
016_vnext_identity_confirmation_case_links
017_vnext_legacy_saved_case_import
```

Do not describe that operation as “013–017 only.” Before execution, an authorized
database owner must compare both Supabase migration history and the custom ledger,
confirm exact live schemas for the unledgered objects, and then approve either:

1. the complete 11-ID transactional runner set, including idempotent historical
   statements and creation of the currently absent 008–009 objects; or
2. a separately designed, reviewed, and tested history-reconciliation mechanism.

Do not manually insert ledger rows ad hoc. A checksum mismatch, unexplained live object,
or disagreement between histories is a stop condition.

## JWT compatibility

### Backend verifier — VERIFIED

`services/vnext/auth.py`:

- permits only RS256 and ES256;
- requires a bounded non-empty `kid` and selects through the issuer JWKS;
- uses a five-minute application JWKS cache and fails closed on unknown/rotated keys or
  discovery failure;
- verifies signature, `exp`, issuer, audience, and subject;
- requires a UUID subject and rejects `service_role` as a normal request principal;
- returns a bounded authentication error without token, claim, or exception leakage.

`services/vnext/authorization.py` derives authorization from the active
`workspace_members` row, never a client role/header. `services/vnext/db_principal.py`
accepts only `VNEXT_DATABASE_URL`, authenticates directly as `vnext_api`, rejects owner,
superuser, `service_role`, and BYPASSRLS principals, and sets the JWT subject/claims only
transaction-locally.

Supabase documents asymmetric JWT verification, `kid`-selected JWKS discovery, issuer,
expiry, subject, and authenticated role claims in its [JWT guide](https://supabase.com/docs/guides/auth/jwts).
Its [signing-key guide](https://supabase.com/docs/guides/auth/signing-keys) documents
zero-downtime rotation states. The public JWKS edge cache can last about ten minutes;
the later operator should wait at least twenty minutes after a signing-key state change
before treating discovery as converged.

### Actual public live JWKS — VERIFIED

- project origin: `https://flyhsjcynreuofbcdxod.supabase.co`
- issuer convention: `https://flyhsjcynreuofbcdxod.supabase.co/auth/v1`
- JWKS: `https://flyhsjcynreuofbcdxod.supabase.co/auth/v1/.well-known/jwks.json`
- observed keys: 1
- observed key: `kid=af4a8fe9-b9f8-4038-8041-838175741be2`, `alg=ES256`,
  `kty=EC`, `crv=P-256`, `use=sig`, `key_ops=[verify]`

This proves signing-key shape, not the claims in an issued user token.

### Issuer and audience

- Issuer convention: **VERIFIED** publicly and compatible with the backend derivation.
- Supabase user-token audience/role convention (`authenticated`): **VERIFIED** from
  current public documentation and compatible with source defaults.
- Actual live token `iss`, `aud`, `sub`, `role`, `iat`, and `exp`: **UNVERIFIED**.

No `SUPABASE_URL`, `SUPABASE_JWT_ISSUER`, or safely authorized existing real user token
was available in the normal runtime environment. No user was created and no token was
printed, persisted, or sent elsewhere. Therefore:

**LIVE JWT COMPATIBILITY: UNVERIFIED.**

Controlled closure step: with an already-authorized existing non-privileged user, set
the intended backend issuer/audience configuration and validate one access token only
in memory through a non-logging path. Require: ES256 signature validates against the
public `kid`; issuer equals the project Auth URL; audience includes `authenticated`;
`sub` is the expected Auth user UUID; role is `authenticated`; time claims are current;
the backend maps only `sub`; and membership authorization still comes from Postgres.
Then discard the token without writing it to disk or logs.

## Browser session compatibility — VERIFIED

`frontend_next/lib/vnext-auth-session.ts` matches the current official client contract:

- standard hosted-project key `sb-<project-ref>-auth-token`; custom domains require an
  explicit matching key;
- top-level session payload with `access_token`, single-use `refresh_token`,
  `expires_in`, and `expires_at`;
- token structure, issuer, authenticated audience/role, UUID subject, and expiry checks;
- refresh at `/auth/v1/token?grant_type=refresh_token`, with rotated access and refresh
  tokens accepted only after validation;
- bounded timeout, failed/corrupt refresh → `missing_session`, and no raw error logging;
- same-realm single-flight refresh plus before/after storage comparison so a refreshed,
  replaced, or signed-out session from another tab is not overwritten by a stale result;
- current `sb_publishable_...` public keys and legacy JWT `anon` keys; service keys fail
  closed.

The default key derivation is visible in Supabase's official
[`SupabaseClient.ts`](https://github.com/supabase/supabase-js/blob/master/packages/core/supabase-js/src/SupabaseClient.ts),
and the current session fields are defined in official
[`auth-js` session types](https://github.com/supabase/auth-js/blob/master/src/lib/types.ts).
Supabase's [session guide](https://supabase.com/docs/guides/auth/sessions) confirms
short-lived access tokens and rotating one-time refresh tokens; its
[API-key guide](https://supabase.com/docs/guides/getting-started/api-keys) covers
publishable keys and legacy `anon` compatibility.

This classification covers implementation compatibility. The real deployed browser
configuration/session remains `UNVERIFIED` until the controlled user-token smoke step.

## Migrations 013–017

No migration file was changed. No migration 018 exists. Canonical SHA-256:

| Migration | Frozen checksum | Status |
| --- | --- | --- |
| 013 | `322c66295975a612d03b39d46c2fdb4fdb0a7e4be6212ae3f4488fee4ce73952` | VERIFIED |
| 014 | `0b465671d513a4b182af8c56e784e8a7e161ed019e6218934ce30625cde7dacd` | VERIFIED |
| 015 | `b87b582e013d3733fe8db179681489fcc950ea6998b7c23552b0fa88a044361f` | VERIFIED |
| 016 | `b0f5ae9694fbb6dcb64d467aa9338778b3c83e7d0da3c5bbab9f710dbebd3636` | VERIFIED |
| 017 | `0753b222597d7e0d6cbc618a17bc1d07d047a0d499318936c29880a119182efa` | VERIFIED |

Registry count is 18, production-runner count is 13, and next safe sequence is 018.

## Production migration runbook

Every step below requires a later, explicit production rollout authorization. Stop at
the first mismatch. Never use the normal application `vnext_api` credential for DDL.

### 1. PRECHECK

1. Pin the release to the exact reviewed main SHA and verify a clean checkout.
2. Re-run the focused gates, registry validator, dry-run, and a fresh PostgreSQL 17
   rehearsal from the pinned checkout.
3. Verify both feature flags are explicitly false in the deployed backend environment.
4. Confirm maintenance/change window, operator, incident lead, recovery owner, and
   communications channel.
5. Identify the direct/session-mode production PostgreSQL endpoint approved for DDL;
   do not use `VNEXT_DATABASE_URL` and do not use a browser/API key.
6. In read-only transactions, capture current database/version, schema/table owners,
   active sessions/long transactions, locks, free capacity, the complete custom ledger,
   Supabase migration history, VNext object absence, public RLS/grants, and the exact
   11-ID pending-set analysis above.
7. Require written approval of that exact pending set or a reviewed reconciliation
   mechanism. If approval is only for 013–017, stop: the current runner is not a
   013–017-only command on this live ledger.
8. Confirm `auth.users` and `auth.uid()` exist. Their absence must stop the runner.

### 2. BACKUP / RECOVERY ASSUMPTIONS

Before DDL, record the latest restorable backup/PITR timestamp, retention window,
project ref, database size, recovery owner, and tested recovery procedure. Confirm the
restore target precedes the migration transaction and that the organization accepts
the recovery point/time objectives and expected downtime. Supabase documents plan- and
configuration-dependent daily backup/PITR behavior in its
[database backup guide](https://supabase.com/docs/guides/platform/backups); do not infer
coverage from plan name or from the existence of a Dashboard page.

The rollback strategy is application flags OFF plus preserved durable data. Do not use
destructive `DROP` rollback SQL. A provider restore is disaster recovery, not the first
response to an application-level rollback.

### 3. OPERATOR PRINCIPAL

Use a short-lived, audited migration/owner credential approved for DDL. Verify its
identity before execution. It must be distinct from `vnext_api`, browser keys,
`service_role` API keys, and normal request credentials. Limit secret exposure to the
approved deployment secret channel; never place it in source, documentation, logs, or
screenshots.

### 4. MIGRATION COMMAND

Only after the pending set and backup are approved, execute once from the pinned
checkout through a secured operator shell:

```powershell
python scripts/apply_production_migrations.py `
  --database-url "$env:STAGE1_MIGRATOR_DATABASE_URL" `
  --release-version "stage1-production-YYYYMMDD"
```

Expected bounded result: `status=pass`, `migration_count=13`, `registry_count=18`,
`next_migration_sequence=018`, `ledger=applied`, and
`verification=tables_indexes_foreign_keys`. The URL must be injected ephemerally and
the command environment must not capture or echo it.

The runner requires explicit CLI input, never loads dotenv or a database environment
implicitly, validates the frozen registry/file set and checksums, executes inside one
transaction, and returns bounded failures without connection details. Its dry-run does
not connect or mutate. Ordinary tests remove/block hosted-looking database variables;
real PostgreSQL tests require the dedicated `VNEXT_RLS_POSTGRES_*` opt-in and a database
name beginning `vnext_rls_test`.

### 5. POST-MIGRATION CATALOG CHECK

Run catalog SELECTs in a read-only transaction and archive only bounded results:

- `vnext_core` and `vnext_private` both exist;
- exactly the expected 19 VNext base tables exist;
- all required 69+ foreign keys and registered indexes exist;
- every VNext base table has `relrowsecurity=true` and
  `relforcerowsecurity=true`;
- no VNext table or schema is owned by `vnext_api`;
- every non-internal VNext trigger function has an explicit `search_path`;
- no unexpected schema/table/function appears.

### 6. RLS CHECK

1. Confirm every VNext table has RLS enabled and forced.
2. Confirm no permissive policy or grant exists for `PUBLIC`, `anon`,
   `authenticated`, or `service_role` on either VNext schema.
3. Connect directly as `vnext_api`, set only the transaction-local request JWT subject
   and claims, and run the controlled tenant matrix below.
4. Confirm empty/malformed/forged claims, revoked membership, and cross-workspace IDs
   fail closed and do not enumerate records.

### 7. ROLE CHECK

For `vnext_api`, require:

```text
LOGIN
NOSUPERUSER
NOCREATEDB
NOCREATEROLE
NOREPLICATION
NOBYPASSRLS
NOINHERIT
```

It may have only the schema usage, `auth.uid()` execution, and table operations granted
by 013–017. It must have no DELETE grant and may UPDATE only the explicitly mutable
tables. Reject any owner, superuser, BYPASSRLS, `postgres`, or `service_role` connection.

### 8. LEDGER / CHECKSUM CHECK

After success, the custom ledger must contain exactly the approved production-runner
IDs with repository checksums. Verify 013–017 against the table above, no 018 row, no
duplicate/unknown ID, and no changed checksum. Re-running the same pinned runner must
return `status=pass` without creating objects or duplicate ledger rows.

### 9. FAILURE STOP CONDITIONS

Stop the rollout and keep both flags OFF for any of:

- backup/PITR or recovery ownership not verified;
- live/Supabase history differs from the approved pending set;
- checksum mismatch, unknown migration, or unreviewed object;
- missing Auth prerequisite;
- migration transaction failure or incomplete catalog verification;
- RLS absent/not forced on any VNext table;
- `vnext_api` owns a VNext object or has superuser/BYPASSRLS/DELETE/unexpected grants;
- trigger function lacks a fixed `search_path`;
- JWT issuer/audience/signature/claim mismatch;
- any cross-tenant visibility or write;
- unexpected 5xx increase or monitoring blind spot during the controlled rollout.

## `vnext_api` provisioning checklist

Migration 013 creates the role without a password; credential provisioning is a
separate authorized operation. The migration owner must:

1. verify the role flags exactly match the role contract above;
2. generate/rotate a strong credential only through the approved managed secret path;
3. expose only a direct `vnext_api` connection as `VNEXT_DATABASE_URL` to FastAPI;
4. verify `current_user='vnext_api'`, all privilege flags, and zero VNext ownership;
5. verify schema/table/function grants against the frozen migrations;
6. run transaction-local principal and real RLS tests;
7. ensure the frontend, logs, screenshots, source, and API responses contain no
   database URL or credential;
8. document rotation and revocation ownership.

Local PostgreSQL 17 proof observed: `LOGIN=true`; all six restriction flags expected by
the contract were false capabilities (`rolsuper`, `rolcreatedb`, `rolcreaterole`,
`rolreplication`, `rolbypassrls`, `rolinherit`); 0 of 19 VNext tables were owned by the
role; DELETE grants were 0.

## Supabase Data API boundary

The required route is:

```text
browser → FastAPI BFF → direct PostgreSQL as vnext_api → FORCE RLS
```

No browser code uses `.from(...)` or `.rpc(...)` for VNext data, and no service-role key
is accepted. `vnext_core` and `vnext_private` must not be added to Supabase **Exposed
schemas**. Supabase's current [custom-schema guide](https://supabase.com/docs/guides/api/using-custom-schemas)
confirms that custom schemas require an explicit Dashboard exposure setting plus SQL
grants; its [API security guide](https://supabase.com/docs/guides/api/securing-your-api)
recommends disabling the Data API when it is unused.

Before rollout, an authorized Dashboard operator must record:

- Integrations / Data API → Exposed schemas excludes `vnext_core` and `vnext_private`;
- no Data API grants exist to `anon`, `authenticated`, or `service_role` for those
  schemas, tables, sequences, or routines;
- GraphQL/REST cannot address either schema with public or authenticated keys;
- FastAPI is the only normal tenant-data path.

Do not modify the setting in this preparation gate.

## Controlled tenant/RLS production smoke plan

Do not run this until migration, role, JWT, deployed flags-OFF state, backup, and
observability are all verified. Creation and cleanup of controlled data require a
separate explicit live-write authorization.

### Temporary controlled data

- six pre-authorized non-production Auth users: A-owner, A-admin, A-manager, A-member,
  A-viewer, and B-owner; plus one A user whose membership is revoked during the test;
- Workspace A and Workspace B, each clearly tagged with the rollout/test identifier;
- active membership rows for all five roles in A and owner in B;
- one Case in each workspace;
- one unverified Property, bounded graph nodes/relations, and Evidence in each
  workspace;
- one A resolution with immutable candidate/evidence suitable for explicit human
  confirmation; separate idempotency keys for each command;
- an approved retention/cleanup record. Durable identity/audit/history records are not
  destructively deleted merely to clean up a smoke test.

### Matrix

| Principal / action | Expected result |
| --- | --- |
| no token, malformed token, unknown `kid`, expired token | structured 401; no data |
| token with forged user/workspace/role headers | ignored/rejected; membership remains authoritative |
| active A role reads A Case/Property/Evidence | allowed for owner/admin/manager/member/viewer |
| any A role reads or writes B IDs | generic non-enumerating 404/deny; no change |
| B owner reads or writes A IDs | generic non-enumerating 404/deny; no change |
| viewer creates resolution/Case/import or confirms/attaches | denied; no change |
| member or manager attempts confirmation/rejection/attachment | denied; no Property/relation/link/audit change |
| admin or owner explicitly confirms a current A candidate | allowed; exactly the approved human-gated effects |
| admin/owner repeats same idempotency key/request | replay; no duplicate Property, relation, decision, link, or audit |
| same key with changed request | 409 idempotency conflict; no partial effects |
| revoked A member reads/writes | denied after revocation; no data |
| A Case/Property/Evidence reads with random or B IDs | same generic 404 shape; no enumeration |
| forced transaction failure/version conflict | complete rollback; retry/error observable; no partial durable effects |

Also prove candidate rank/confidence never confirms identity, confirmation never
auto-attaches a Case, legacy import stays `legacy_unverified`, and legacy import creates
no PropertyEntity, confirmation, or CasePropertyLink.

## Feature-flag rollout order

1. Resolve and approve live ledger/pending-set handling.
2. Verify the backup/recovery checkpoint.
3. Apply the approved migrations; verify catalog, RLS, role, and ledger.
4. Provision and verify `vnext_api`.
5. Verify one real authorized user token and the deployed browser session.
6. Run the controlled tenant/RLS matrix.
7. Deploy backend and frontend with both flags explicitly OFF.
8. Verify health, privacy-safe telemetry, dashboards, alert routing, and stop controls.
9. Enable `FEATURE_IDENTITY_V1` only in the approved controlled environment/cohort.
10. Repeat identity smoke checks and expand gradually only with clean metrics.
11. Keep `FEATURE_LEGACY_CASE_IMPORT_V1` OFF until its separate consent/copy-only
    rollout is explicitly authorized and independently monitored.

At every rollback point: flags OFF, stop new writes, preserve durable data and immutable
history, investigate by correlation/request IDs, and do not run destructive reversal.

## Observability and failure plan

The current middleware emits bounded route, method, status class, duration, release,
environment, dependency status, and correlation ID for failed requests. VNext responses
use allowlisted structured error envelopes. Successful confirmation, rejection, Case
attachment, and legacy import write immutable audit events with actor/request reference
inside the same transaction. Raw JWTs, refresh tokens, secrets, request bodies, raw
private evidence references, storage paths, and exceptions are not included.

| Signal | Current classification | Rollout requirement |
| --- | --- | --- |
| unexpected 5xx by route/status class | VERIFIED in source | Verify deployed log ingestion, rate/baseline, dashboard, and pager. |
| authentication failure volume (401) | VERIFIED at status-class level | Add/verify dashboard filter and alert threshold; never log tokens. |
| authorization failure volume (403/404) | VERIFIED at status-class level | Correlate by route/request ID without logging identifiers or private data. |
| RLS/database permission failure | UNVERIFIED as a distinct signal | Prove safe categorization/alerting in controlled smoke without raw SQL/exception leakage. |
| provider unavailable | UNVERIFIED as a distinct operational metric | Verify bounded provider category and alert/dashboard behavior. |
| identity confirmation failure | UNVERIFIED as a distinct operational metric | Verify error-rate and audit-presence/absence queries by request ID. |
| version conflict | UNVERIFIED as a distinct operational metric | Establish expected baseline and alert only on anomalous rate. |
| transaction rollback | VERIFIED by tests, UNVERIFIED in live monitoring | Prove no partial rows plus safe operator-visible signal. |
| category-specific dashboards and paging | UNVERIFIED | Record dashboard URLs, owners, thresholds, notification test, and retention. |

The request observer currently reduces detailed VNext error categories to generic
privacy-safe status-class observations. That is safe but not proof of category-specific
production detection. Do not claim those signals are monitored until the deployed
logging/metrics pipeline is exercised and the operator records evidence.

Immediate STOP / flags OFF conditions:

- cross-tenant read/write or enumerating error behavior;
- JWT signature, issuer, audience, subject, role, expiry, or rotation mismatch;
- migration/history/checksum mismatch or transaction failure;
- missing/FORCE-disabled RLS, unexpected grant, or `vnext_api` privilege/ownership drift;
- partial confirmation/case/import effects or missing required audit event;
- secret/token/private-reference leakage;
- unexplained 5xx, provider failure, latency, conflict, or rollback spike;
- alerting/logging unavailable during controlled enablement.

## Local PostgreSQL 17 rehearsal evidence

Target: local-only PostgreSQL 17.11 database
`vnext_rls_test_production_readiness_20260907`. The server was stopped after validation.
No hosted database URL was present in the real-test process; it exported only
`VNEXT_RLS_POSTGRES_URL` and `VNEXT_RLS_POSTGRES_DISPOSABLE=1`.

- real migration/RLS suite: **9 passed in 140.91s**;
- rollback-only database validator: **PASS**;
- clean production runner: **PASS**;
- repeat production runner: **PASS**;
- VNext tables: 19; RLS enabled+forced: 19; owned by `vnext_api`: 0;
- VNext foreign keys: 72;
- trigger functions: 26; missing fixed `search_path`: 0;
- `vnext_api` DELETE grants: 0; UPDATE grants: 2, both within the allowlist;
- ledger rows: 13; 013–017 checksums exactly match the frozen registry;
- clean registry apply, existing production prefix→017, 016→017, repeat execution,
  tenant isolation, human gate, idempotency, and atomic rollback: PASS.

**REAL POSTGRES: EXECUTED — PASS.**

## Validation evidence

- focused auth/authorization/database-principal/Stage 1 exit gate:
  **56 passed, 1 deprecation warning**;
- migration static validator: **PASS** (`registry_count=18`,
  `managed_migration_count=13`, `next_migration_sequence=018`);
- production migration dry-run: **READY**, no connection/mutation;
- production operations gate: **PASS**;
- production dependencies: `npm audit --omit=dev` found 0 vulnerabilities;
- `git diff --check`: **PASS** before documentation; repeat after final edit/commit.

The first focused execution had 55 passes and one environment-only failure because the
fresh worktree lacked `typescript`. After `npm ci` installed the lockfile-pinned
dependencies in this worktree, the exact gate passed 56/56. No source or lockfile was
changed.

## Remaining production blockers

1. **LIVE JWT COMPATIBILITY — UNVERIFIED:** no authorized real user access token was
   available for non-logging end-to-end claims verification.
2. **Live migration ledger/pending-set approval — UNVERIFIED:** the current runner would
   process 11 unrecorded IDs, not only 013–017.
3. **Backup/PITR and recovery evidence — UNVERIFIED.**
4. **Live `vnext_api` provisioning and acceptance — UNVERIFIED.**
5. **Supabase Exposed schemas and post-migration Data API denial — UNVERIFIED.**
6. **Controlled live tenant/RLS and browser-session smoke — UNVERIFIED.**
7. **Deployed flag-OFF state, dashboards, category detection, alert routing, and pager
   exercise — UNVERIFIED.**

## Exact next authorized action

Authorize a bounded pre-rollout operator session that remains read-only except for no
database changes: provide access to backup/PITR metadata, Supabase migration history,
deployment environment configuration, Data API settings, observability dashboards,
and one already-authorized non-privileged real user session through a non-logging
verification path. In that session:

1. verify the real token and deployed browser configuration;
2. reconcile the custom ledger against Supabase history and approve the exact pending
   migration set or commission a separately reviewed reconciliation change;
3. record backup/recovery and monitoring evidence;
4. return a new go/no-go decision for a separately authorized production execution
   window.

That authorization must still not apply a migration, provision a role, create a user or
workspace, change Auth, enable a flag, or run the tenant write smoke test. Those actions
belong to the later production execution authorization only.

## Scope verification

This gate made no product/source/migration change. It performed no live mutation,
migration, role/user creation, Auth change, signing-key rotation, workspace creation,
feature enablement, Migration 018, Hero/homepage change, Stage 2 work, Parcel/GIS,
NLSC/provider expansion, Terrain, title/listing, CRM, or AI reasoning work. The separate
Hero/user worktree at `C:\Projects\proptech-ai-copilot` was not edited.
