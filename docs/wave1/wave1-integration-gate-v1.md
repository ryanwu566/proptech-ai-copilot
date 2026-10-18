# Wave 1 final integration gate v1

Acceptance date: 2026-10-18 (Asia/Taipei). Starting main and branch HEAD:
`4a17ddb91f4b7d3e5a106759ba71175619347419`.
Branch: `release/wave1-integration-gate-v1`. Preflight: clean, 0 behind / 0 ahead.

This record reports only results actually observed below. Hosted production is
a separate gate. No deployment, push, Render operation, hosted database connection,
Supabase project operation, or installed Chrome operation is authorized here.

## Execution plan and scope

- [x] Fetch and validate exact starting SHA, branch and clean tree.
- [x] Read integrated authority, replay, migration and split-store contracts before tracked edits.
- [x] Run existing focused Wave 1 tests; add only missing boundary proof.
- [x] Run real SQL against fresh loopback PostgreSQL 17 clusters; proof clusters stopped and removed.
- [x] Run frontend model tests and isolated bundled headless Chromium, one worker, zero retries; preserve two failures.
- [x] Run typecheck, lint, E2E build, production build, route/global budgets and repository gates.
- [x] On a quiet host, run complete Python once, including the worker module once.
- [x] Resolve independent adversarial review findings and finalize bounded JSON evidence.
- [x] Fetch main again; unchanged at the starting SHA, 0 behind / 0 ahead.
- [x] Evaluate conditional certification: local FAIL, so no certification commit or push.

No product features or budget increases. Source fixes require demonstrated defects.
Raw logs and JUnit records are ignored artifacts under `artifacts/wave1-integration-gate-v1/`.

## Authority and integration matrix

| Transition | Authority source | Fail-closed condition | Store | Browser influence | Replay / idempotency |
| --- | --- | --- | --- | --- | --- |
| Bearer JWT → `AuthenticatedPrincipal` | Existing asymmetric JWKS verifier; issuer, audience, lifetime, UUID subject | Missing/duplicate/malformed bearer, invalid signature/claims, unavailable verifier | Auth provider JWKS; no browser role authority | Supplies token, never signing authority; metadata ignored | JWT lifetime; no mutation |
| Verified principal → own account | Fresh `PostgresAccountRepository` via validated `vnext_api` principal context | Missing/mismatched/malformed/unavailable authority → 503 | Application `vnext_private.consumer_accounts` | Cannot choose account identity/status/role | Own-ID insert with defaults; conflict never resets role or suspension |
| Account → consumer access | `AccountAuthorizer.require_active` | Suspended → 403; unavailable → 503 | Application/account DB | No role/status override | Fresh authorization per request; own-status GET remains available to suspended user |
| Principal → workspace access | Active membership scoped to user and workspace; tenant RLS | Absent, foreign, revoked or insufficient membership denies | Application `vnext_core`; account-aware restrictive membership RLS | Requested workspace is a target, never authority | Existing command header keys and DB idempotency records |
| Transport peer → anonymous usage | Bounded ASGI transport peer, HMAC-SHA256 with server key | Missing/invalid required key denies; production never ephemeral | Local admission; dedicated usage quota/telemetry | Forwarded/user/role headers ignored | Stable opaque HMAC subject for same key/peer; quota reservation UUIDs |
| Verified principal → authenticated usage | Only typed server `AuthenticatedPrincipal` with UUID | Strings/mappings/headers cannot create authenticated subject | Dedicated usage DB plus bounded local counters | Metadata cannot select tier; authenticated tier fixed `free` | Stable `user:<UUID>`; consume marker deduplicates |
| Usage subject → quota admission | Server-selected capability, fixed class policies, PostgreSQL guard | Required guard unavailable/unsafe → 503; exhausted → 429 | Dedicated `api_usage` | No browser policy/DB access | Atomic consume and markers; request/operation/day windows independent |
| Usage context → telemetry | Bounded server events/dimensions | Failures reported as unavailable/partial; never enforcement proof | `api_usage.hourly`, `flush_batches` | No raw peer IP/token/payload as principal | Batch UUID transaction; bounded retention; telemetry is partial |
| Verified principal + active account → Admin | `require_platform_admin`; authoritative `platform_role=platform_admin` | Consumer/suspended/missing/malformed authority denies before reads/commands | Account authority plus dedicated Admin account login | JWT metadata, workspace roles and localStorage cannot grant Admin | Fresh dependency authorization and DB reauthorization |
| Admin → account command | Dedicated operator; bounded SQL function; account advisory lock | Unsafe role, revoked actor, self-change, last-admin violation, audit failure deny | Account DB: account change + immutable command + audit | UUID target, reason and enum are validated inputs | Body UUID scoped by actor; exact replay; changed payload → 409; one-store atomic commit |
| Admin → quota acceptance | Active Admin reauthorized under account lock | Account outage, revoked actor, changed key/body/store deny | Account DB immutable `admin_plane.claims` | Browser cannot choose actor/owning store | Durable exact claim binds actor, command, body, effective target + instance UUID |
| Accepted quota → owning-store command | Backend coordinator credential and verified actor GUC; bounded SQL | Usage outage/audit failure/uncertain commit never returns success | Usage DB: policy + command + audit in one transaction | Only bounded class/hour/day fields, no direct DB access | Reauthorize retry; original owning result replay; no duplicate audit; no distributed transaction |

Source authority: `services/vnext/{auth,accounts,authorization,db_principal}.py`,
`backend/api/abuse_middleware.py`, `services/{usage_principal,api_usage,usage_guard,usage_quota,usage_ledger}.py`,
`services/admin/{authorization,store,commands}.py`, and migrations 020/021/022.

## Ordering and split-store semantics

For capability-classified requests, bounded transport-peer admission precedes
JWT/JWKS and account lookup. On legacy product routes, a supplied bearer must
verify and have an active account before authenticated quota admission; invalid
or suspended credentials never downgrade to anonymous. On protected `/v1` routes,
verification binds the shared usage context, then `require_active_account` admits
authenticated quota after the account check. Unadmitted request telemetry is
system-scoped. The capability classifier covers selected routes, not every route:
Account and Admin are not claimed to consume the same classified quota pipeline.
Quota identity does not grant account access, platform privilege or workspace membership.

Account reads and ordinary tenancy use `VNEXT_DATABASE_URL`. Dedicated quota and
telemetry use `API_USAGE_DATABASE_URL`. Admin uses `ADMIN_DATABASE_URL` for the
account domain and `ADMIN_USAGE_DATABASE_URL` for the usage domain, with effective
target checks against their respective source URLs. No generic database fallback
is claimed for Admin. Account commands remain independent of a usage outage;
quota/usage/audit operations must fail when their required store is unavailable.

Quota commands commit durable account-side acceptance before remote execution.
A lost acceptance acknowledgement yields 503 without dispatch. A lost usage
commit acknowledgement yields 503; exact retry reauthorizes and resolves the
original result. Claims persist after failure/uncertainty. Revocation or owning
store change can require owner incident resolution; no background retry, claim
deletion, rebind, or cross-database atomic commit is claimed. Accepted work can
finish after later revocation; every new request/retry reauthorizes. Test-only
disabled fsync/synchronous commit settings prove transaction semantics, not crash
durability or hosted storage recovery.

## Migration allocation and database placement

| Migration | Canonical SHA-256 | Placement |
| --- | --- | --- |
| 020 | `01aa6d71588cefa8b1e4d35e9bdf08cc7944ac4280791de2f5f974a9f466dd31` | Application/account foundation; private forced-RLS consumer accounts |
| 021 | `00ed7d4b78de6d92c285ab8cd87241d1477bee2ce6e97caef6bbf6e2f43b98af` | Dedicated usage subsystem bootstrap; quota, telemetry, runtime roles |
| 022 | `f9c3c389d15cd3702a31be12f4e0f68e56f482ecc03eecf4d5c6e7b92c4fc709` | Apply to each domain; installs bounded functions only for present authority tables |

Registry orders are 21/22/23; next sequence is **023**. Canonical hashes normalize
CRLF to LF. Historical files and registry remain unchanged. A global migration
rehearsal belongs only on the disposable application rehearsal database; never
run the application chain against the dedicated usage store. Usage provisioning
must bootstrap/verify exact 021 and provision runtime before extending with 022;
the strict 021 verifier deliberately rejects the extended catalog on rerun.

## Idempotency classification

The authoritative executable matrix is `HEADER_IDEMPOTENCY` / `BODY_COMMAND_ID`
in `tests/test_vnext_stage1_exit_gate.py`, checked against every persisted `/v1`
mutation in OpenAPI. The bounded JSON companion enumerates each route exactly once.
There are 19 header routes and two Admin body-command routes. Planning observation
is an explicitly classified provider read despite POST; legacy provider computations
outside `/v1` are not falsely described as persisted command mutations.

## Results

These are fresh results. Historical Wave 1A/1B/1C pass counts are not acceptance
evidence for this gate.

| Check | Fresh result |
| --- | --- |
| Application RLS, migration rehearsal, usage guard, Admin co-located/split stores | 82 passed, 0 failed, 0 skipped; 178.35 seconds; 1 existing Starlette deprecation warning |
| Dedicated usage bootstrap/security and bootstrap → runtime → 022 integration | 64 passed, 0 failed, 0 skipped; 131.58 seconds |
| Explicit disposable ledger replay/retention/browser-role denial | 1 passed, 0 failed, 0 skipped; 3.47 seconds |
| Real missing-store quota/audit outage recheck | 3 passed, 0 failed, 0 skipped; 11.63 seconds; two new quota cases and one audit recheck |
| Focused serial Wave 1 pack | 388 passed, 0 failed, 1 skipped; 142.64 seconds; 1 existing Starlette deprecation warning |
| Final startup/cache-isolation proof | 10 passed, 0 failed, 0 skipped; 16.78 seconds |
| Complete serial Python suite, exactly once | 4,123 passed, 3 failed, 151 skipped; 4 warnings; 516.58 seconds |
| Worker pool, once within complete suite | 26 passed, 0 failed, 0 skipped; no standalone retry or deadline changes |
| Three-case encoding diagnostic | 3 passed, 0 failed, 0 skipped; 3.54 seconds; original complete-suite failures retained |
| Frontend Auth/Admin/navigation/workspace models | 305 passed, 0 failed, 0 skipped |
| Decision Room models | 13 passed, 0 failed, 0 skipped |
| Configured bundled Chromium, workers=1, retries=0 | 71 passed, 2 failed, 0 skipped; both real-backend fixtures exceeded the existing 15-second readiness deadline before UI assertions; failures preserved |
| Production unconfigured bundled Chromium | 17 passed, 0 failed, 0 skipped; 59.2 seconds; four locales × widths 390/430/1024/1440 plus route asset measurement |
| Typecheck | Exit 0 |
| Lint | Exit 0; 0 errors, 23 existing warnings |
| E2E build | Actual npm build exit 0; initial local log-summary encoding error occurred after success and was corrected in the untracked runner |
| Production build | Actual npm build exit 0; no public Auth/API configuration; two build workers via child-only `CIRCLE_NODE_TOTAL=3` |
| Route/global budgets | All 24 routes pass; Home 1,926,394 bytes; largest Admin route 1,135,301 bytes; total static 3,507,067 bytes; largest JS 604,482 bytes; unchanged ceilings |
| Home/Admin isolation | No `/v1/admin/`, `admin-shell` or account-lookup markers in the 18 observed Home assets |
| Security/performance gate | Exit 0; all repository checks pass |
| Release-quality gate | Source contracts exit 0; wrapper explicitly skips Python/build; separate complete Python execution failed, and browser acceptance failed; wrapper success does not override either |
| Production-operations repository gate | Exit 0; external guardrails BLOCKED; production decision NO_GO |

The SQL/bootstrap packs contain **150 passing executions without skips**, including
one explicit audit recheck: 149 distinct cases, comprising 140 real PostgreSQL
cases and nine local configuration/bootstrap contract cases. The focused pack's
single skip is `test_disposable_postgres_ledger_idempotency_retention_and_denied_clients`
without a configured target; that exact case passed separately on its fresh
disposable target, as recorded above. Native local PostgreSQL
17.11 clusters bind only loopback, use unique temporary data directories and
ports, and contain synthetic Auth/users only. Test child environments exclude
inherited DB URLs, libpq settings and credential variables; psycopg targets are
allowlisted by loopback host/port/database and Python external socket connections
are refused. No application chain is applied to the dedicated usage bootstrap
database. Both proof clusters were stopped and their data directories removed.

Before tests began, a first native launcher held an inherited Windows output pipe
open after cluster startup. That cluster was stopped without running tests. Its
ignored, stopped scratch data directory remains because automatic command review
rejected deletion, including a bounded cleanup attempt. It has no running server
or occupied port. This unresolved cleanup item must remain visible in the verdict.

The complete suite's 151 skips remain part of its result. All 140 Wave 1
PostgreSQL skips were separately proved against disposable targets. The remaining
11 comprise nine other subsystem database cases without targets (market, backup,
PLVR and RIS) and two operating-system constraints (Windows symlink privilege and
Unix identity permissions). Their skipped node IDs and module counts are retained
in the JSON record; no broader SQL acceptance is claimed.

The complete suite's three failures are:

- `tests/test_gsmma_geological_sensitivity_artifact.py::test_operator_cli_builds_local_outputs_without_uploading`
- `tests/test_market_coverage_registry.py::test_coverage_audit_script_outputs_safe_lines`
- `tests/test_market_coverage_rollout_workflow.py::test_market_coverage_county_helper_outputs_tracked_counties_safely`

Each child command exited with its expected status, but a subprocess reader
raised `UnicodeDecodeError` and left `stdout=None`. The gate harness forced
`PYTHONIOENCODING=utf-8` while the parent tests used Windows CP950 for
`subprocess.run(text=True)` decoding. A diagnostic of only these three cases,
with child-only `PYTHONUTF8=1` aligning parent and child encodings, passed without
source changes. The original complete-suite result is still FAIL; there was no
second complete run. Its four warnings comprise one existing Starlette warning
and three subprocess reader-thread warnings. No unrelated CLI changes were made.

Three zero-competing-process observations were recorded before the complete
suite and again immediately before the worker module. Personal Chrome was
excluded from these queries. The worker module passed, so a failing-worker
current-main baseline comparison was unnecessary.

## Startup and authority phases

`app_lifespan` calls `assert_startup_configuration`,
`assert_guardrail_configuration`, configured abuse/usage quota policies,
`validate_usage_startup` (including peer key and guard check), then
`start_usage_ledger`, before optional provider startup and accepting requests.
Production requires a strict 64-hex-character HMAC key and PostgreSQL guard/URL;
it cannot select local guard mode. Unsafe or unavailable guard checks abort
startup. A required ledger must pass its write-permission probe; optional ledger
failure remains explicitly unavailable rather than enforcement success.

Auth/account configuration is **request-time authority**, not an assertion of
Auth readiness by the production startup validator. Missing verifier configuration
denies authentication; missing account configuration denies protected access.
The focused integration startup tests exercise actual lifespan ordering and this
phase distinction without contacting any external target. No startup behavior
was relaxed or changed for hosted availability.

## Independent adversarial review and fixes

A fresh read-only reviewer inspected the integrated system and then the fixes.
No Critical findings. Two Important findings were reproduced and corrected:

1. Consumer request-role verification accepted inherited Admin executor authority,
   SET-only parent roles, privileged sessions hidden by `SET ROLE`, CREATEROLE,
   and database ownership. It now requires a direct, unprivileged login with no
   parent memberships, database/schema CREATE or application object ownership,
   before binding principal settings. Real SQL demonstrates that inherited 022
   grants permitted account-role mutation under the old verifier, then proves
   rejection with the fix. Canonical migrations remain unchanged.
2. SQL `NOT LIKE 'pg_%'` treated `_` as a wildcard and skipped ordinary `pgx`
   schemas. Exact `left(name,3) <> 'pg_'` checks now cover schema ownership/CREATE
   drift in both consumer and Admin runtime verification.

RED proof against the original HEAD consumer verifier and original Admin schema
checks: 11 expected failures and 4 passes, including actual inherited account
UPDATE and `pgx` CREATE/ownership cases. This is defect reproduction, not final
acceptance failure. Final SQL: all 82 passed. A separate 12-pass principal unit
pack proves rejection before GUC binding. An additional SQL integration test
proves an active platform admin cannot read or write a foreign workspace.

The final reviewer reported no residual Critical/Important source findings.
The reviewer did not execute tests or verify runtime logs independently.

A separate backend readiness diagnostic passed in 10.874 seconds after three
quiet-host observations. It used the same backend helper and interpreter, with
a diagnostic-only 60-second observation window. It did not rerun the failed
browser cases or change their existing 15-second deadline. Concurrent automation
and low free memory were observed during the original failures, but the later
diagnostic alone does not establish their root cause or replace acceptance proof.

The final outage recheck verifies the database is absent in the disposable
cluster catalog and requires a real psycopg connection error before testing
Admin's 503 response, unchanged policy, and zero claim/command/audit records.
Its scope is pre-acceptance failure of each store. Separate existing tests cover
post-acceptance rollback, uncertain acknowledgements and deterministic replay.

## Hosted boundary

Hosted production remains **NO_GO**. No hosted configuration, deployment, database,
provider runtime, professor-server, backup/restore or recovery evidence was collected.
Repository `render.yaml` does not declare the Wave 1 Auth/account, usage HMAC/DB,
or dedicated Admin settings; record this manifest gap as follow-up, without changing
the manifest. Dedicated usage provisioning/runtime credentials, migrations and
least-privilege roles in both domains, Auth/JWKS/provider setup, first-admin bootstrap,
actual startup/guard/ledger readiness, and owner runtime/recovery evidence remain
separate hosted closure requirements. Local proof cannot establish those facts.

## Final disposition

**WAVE 1 LOCAL INTEGRATION: FAIL. HOSTED PRODUCTION: NO_GO.**

Local certification is withheld because the single complete Python run failed,
two configured browser cases failed their backend readiness setup, and the initial
stopped scratch directory could not be removed. The encoding and readiness
diagnostics do not substitute for the required acceptance runs. Both Important
software findings were fixed and verified; no remaining Critical/Important source
finding was reported by the independent reviewer.

The final fetch confirmed `origin/main` and HEAD remain
`4a17ddb91f4b7d3e5a106759ba71175619347419`, 0 behind / 0 ahead. No rebase was
needed. Nine scoped files are left staged for review, including both acceptance
records. The tree is not clean; safe-to-push is NO. No certification commit,
deployment, production database connection, Render/Supabase change or push occurred.
