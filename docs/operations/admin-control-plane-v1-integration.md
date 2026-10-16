# Wave 1C Admin Control Plane v1 integration

This document supersedes the historical read-only acceptance in
`admin-control-plane-v1.md`. Integration baseline: current main
`194d17ce721fac5fa878db3c16c1c9233348bae5` (including the Wave 1B portable database
bootstrap closure merged during validation). Historical work remains preserved at
`backup/admin-control-plane-v1-7400fb6` (`7400fb6`). No hosted changes are part of this work.

## Authorization and topology

Browser bearer session → FastAPI verified `AuthenticatedPrincipal` →
`AccountAuthorizer.require_active` → `AccountAuthorizer.require_platform_admin` →
dedicated `ADMIN_DATABASE_URL` connection. No metadata, workspace role, browser
storage, identity header or query parameter grants authority. Account state is
read afresh using the Wave 1A `VNEXT_DATABASE_URL` connection. No Admin request
uses the consumer connection for privileged SQL.

Current main's supported Wave 1B hosted topology uses a **separate usage database**.
Set `ADMIN_DATABASE_URL` to the account database with its dedicated Admin login;
set `ADMIN_USAGE_DATABASE_URL` to the usage database with another dedicated Admin
login. Targets must match `VNEXT_DATABASE_URL` and `API_USAGE_DATABASE_URL`, when
those source URLs are configured. Comparison uses effective libpq host, hostaddr,
port and database options, including query overrides, without logging credentials.
Service/default-target connections and explicitly empty port/hostaddr parameters
are refused. Co-located development is also
supported. Missing or mismatched usage configuration fails usage, quota and audit
requests; directory and account commands remain available independently.

`ADMIN_DATABASE_URL` must authenticate directly as a dedicated login inheriting
only `proptech_admin_operator`. There is no `DATABASE_URL` fallback. Every Admin
database transaction rejects superuser, BYPASSRLS, CREATEDB, CREATEROLE,
replication, table/schema/database ownership, unsafe transitive role memberships,
consumer/usage executor credentials, and a changed session role. It also checks
the definer role for elevated attributes/ownership. Runtime role errors fail
closed with a safe 503. Neither operator nor function executor owns data tables.

The NOLOGIN `proptech_admin_executor` owns only bounded functions. It has column
UPDATE privileges on existing account and quota policy tables, SELECT, and
INSERT/SELECT on private audit/command tables. The operator gets SELECT under
active-admin RLS and EXECUTE on those bounded functions; it cannot directly
update accounts, policy, audit, claims, commands or usage counters. Consumer, anonymous,
authenticated, service and usage roles receive no Admin grants.

Example provisioning for a database owner to review and execute separately:

```sql
CREATE ROLE proptech_admin_runtime LOGIN INHERIT NOSUPERUSER NOBYPASSRLS
  NOCREATEDB NOCREATEROLE NOREPLICATION;
GRANT proptech_admin_operator TO proptech_admin_runtime;
```

Provision authentication through the deployment secret manager; do not put a
password into this document or shell history. Use this login exclusively for
the respective Admin URL. Never grant a usage writer/guard login an Admin role.
Use verified TLS or the reviewed authenticated database proxy for hosted
connections; loopback trust authentication is confined to disposable validation.
The first platform admin must be established through the
existing reviewed Wave 1A owner/bootstrap procedure; a zero-admin system has no
public self-promotion escape hatch. Review role membership and ownership drift
as part of deployment checks. These instructions are documentation, not executed
production operations.

## Migration 022 and command guarantees

`022_admin_control_plane.sql` is registered with a checksum. Migrations 020 and
021 remain unchanged. Apply 022 separately to the account and usage databases.
Run the strict reviewed 021 bootstrap and runtime provisioning **before** 022 on
the usage database. The original bootstrap verifier intentionally requires the
exact 021 catalog; do not rerun it against the extended catalog or weaken it to
accept arbitrary additions. 022 installs account functions only where account
authority exists, and usage functions only where the quota ledger exists. It
refuses an unrelated database and creates no shadow auth schema.

The migrator owns the affected source tables/schemas and has CREATEROLE; it is
separate from runtime. PostgreSQL 17 ownership transfer temporarily grants the
migrator SET membership in the function executor and executor CREATE on the new
Admin schema. Both temporary grants are removed before commit. Runtime checks
also reject leftover CREATE privileges and role ADMIN options.
If the grant roles already exist in the same PostgreSQL cluster, the reviewed
migrator also needs ADMIN option on them, with INHERIT FALSE and SET FALSE;
never give these migration privileges to a runtime login.

The migration creates only Admin audit/commands, bounded
account/quota functions, and required least-privilege grants, RLS and immutability
triggers. All definer functions use an empty search path and qualified objects.

Every mutation requires a UUID command ID and a nonblank reason of at most 500
characters without control characters. Extra command fields are rejected. Fields
and values are closed enums. Quota ranges match migration 021: hourly requests
and operations 1–100,000; daily operations 1–1,000,000.

Account mutation and quota acceptance share account-DB advisory lock `(832,1)`.
Quota execution uses the same lock namespace in its owning database. Only READ
COMMITTED is accepted, so authorization and last-admin reads after the lock wait
see newly committed changes. The actor is a private GUC installed from the verified
principal, never a body parameter. The function reauthorizes after locking.
Self-account commands are denied, including self-suspension and self-role changes.
Removing the final active admin is denied. Concurrent cross-suspensions or
cross-demotions leave one active admin; the losing actor is denied after lock wait.
An out-of-band database owner can override application invariants and must follow
the owner runbook; the application does not claim protection against a malicious DBA.

Success atomically writes the account/policy change, immutable command result and
immutable audit event. Audit contains actor, target, before/after, reason, UTC
timestamp and command ID. Any audit failure rolls back the mutation and retry
record in the owning database. UPDATE/DELETE/TRUNCATE triggers and absence of runtime DML privileges
make audit and command history append-only. A successful no-op is audited with
identical before/after state.

Before remote quota execution, the account database commits an immutable command
claim under the account-authority lock. This binds actor, key, action, exact
payload/reason and owning store (effective target hash plus immutable instance
UUID). Account commands reject quota-reserved keys. Target/instance changes
conflict rather than silently applying a retry to another database. Claims are
command records, not successful mutations or audit events.

Authorization linearizes at durable acceptance. Already accepted work can finish
after subsequent suspension/demotion; every new request or retry reauthorizes
under the account lock. No claim authorizes a suspended actor to retry. Usage-only
SQL trusts the dedicated backend coordinator credential and verified actor GUC;
consumer, writer and guard roles cannot execute it. Account authority is never
copied into the usage database. Protect this credential as privileged server code.

A lost claim-commit acknowledgement returns 503 without dispatch. An exact retry
reauthorizes and confirms the durable claim before execution. A lost usage commit
acknowledgement returns 503; retry resolves the original owning-store result without
another audit. Uncertain or failed work retains its claim permanently. There is no
cross-database atomic commit or background retry. If an actor is revoked or the
store changes before resolution, an owner must inspect the claim and owning result
through the incident procedure. Never delete/rebind a claim or substitute a new
key for uncertain work.

Idempotency is scoped by actor and command ID across all mutation types. Identical
retries return the original result without another mutation/audit event. Reusing
the key for another target/action/reason/policy conflicts with HTTP 409. Revoked
or suspended actors cannot replay commands. The UI freezes the reviewed payload
and retains its key during uncertain-result retries. A retry returns the original
command outcome, not a promise that no later operator changed the account; refresh
or exact lookup establishes current state.

## Read and UI contracts

The `/admin` route family is isolated from homepage imports. Main sections are
Overview, Accounts (`/admin/users`), Usage & Quotas and Audit. Existing Providers,
Limits and Operations remain available as passive evidence views. All four locales
are supported: zh-TW, en, ja, ko. Forms use native labels, keyboard controls,
visible focus, confirmation focus, and responsive layout.

- Directory: ordered UUID keyset pagination, 50 rows; exact UUID account lookup
  uses `/v1/admin/accounts/{uuid}`. No email wildcard search or Auth directory dump.
- Commands: `/accounts/{uuid}/commands`, `/quota-policy/commands`; policy reads
  use `/quota-policy`. Every endpoint independently authorizes and returns no-store.
- Audit: timestamp/event-ID/store keyset pagination, 50 rows, no offset or unbounded
  accumulation; minimized allowlisted projection, no provider payloads or secrets.
  Each store contributes at most 51 rows. Equal timestamps and event IDs are
  ordered by store. Unavailable stores fail the page instead of being omitted.
- Usage: fixed last 24 UTC hourly buckets, closed capability domains, maximum 50
  rows. Telemetry and authoritative quota aggregates are separately aggregated
  before joining, avoiding multiplicative counts. Cost stays unknown. Missing
  telemetry stays null; persisted zeroes remain zero. Totals do not include
  unflushed or lost telemetry and are explicitly partial.
- Overview: authoritative account count; incomplete traffic totals remain unknown.
- Provider views consume passive configuration and existing observations only.
  Configured does not mean healthy. Backup/restore/incident evidence remains
  unavailable; compatibility remains unverified. No Admin page calls a provider.
- Quota editing affects only shared principal limits from Wave 1B. Provider,
  capability and concurrency limits remain process-local. The legacy fleet flag
  never asserts global capability protection; telemetry does not claim enforcement.

Queries have a 3-second statement deadline and 1.5-second lock deadline; connections
have a 2-second timeout. HTTP clients have a 15-second abort deadline and 256 KiB
stream cap. Server errors never include raw SQL/credentials. Browser state clears
on sign-out/identity change; late reads and commands are guarded by session generation
and abort signals. No polling, automatic command retries or browser persistence of
Admin records is introduced. A server authorization check cannot retract data already
delivered; new requests always reauthorize.

## Validation and release boundary

Validation artifacts are stored locally under ignored `artifacts/admin-v1/`.
The acceptance report records fresh command results and any environmental skips.
Disposable PostgreSQL tests bind only loopback, require an explicit disposable
flag and test database prefix, and run migrations 013/020/021/022 on PostgreSQL 17.
The SQL proof uses a real restricted login, not a superuser connection with SET ROLE.
Separate account-only and usage-only databases prove the supported split layout,
ordinary-owner migration, unchanged guard consumption of updated policy, durable
claim recovery, connection termination during remote lock wait, audit rollback,
cross-action reuse, owning-target changes and audit ties across stores.
The disposable cluster disables fsync, synchronous commit, full-page writes and
JIT to reduce contention on this validation machine. These test-only settings are
absent from migration 022 and runtime configuration. Tests prove transaction and
authorization semantics, not crash recovery or hosted storage durability.

Required checks: focused Admin API/SQL/transport/browser tests, concurrency,
atomicity, retry conflicts, grants, Wave 1A/1B regressions, both browser channels
with retries=0, typecheck, lint, production build, measured route/global budgets,
security/performance, release-quality, production-operations and full Python.
Independent adversarial review follows implementation. Exactly one local feature
commit sits above current main; no push, merge, deploy or Wave 1 Integration Gate.

Hosted owner credentials, first-admin bootstrap, migration execution, deployed
configuration and externally evidenced recovery remain deployment responsibilities.
Local test success is not hosted production certification.

## Independent adversarial review

A separate reviewer inspected the whole branch and uncommitted integration on
2026-10-16. No Critical findings. Corrections made for all three Important findings:

1. Cast PostgreSQL aggregate sums to bigint before strict integer DTO validation;
   add populated telemetry/quota regression rather than testing empty tables only.
2. Enforce exact runtime and executor membership allowlists, including rejection
   of PostgreSQL predefined server/file/signal roles; test both grant targets.
3. Reserve SQLSTATE `PT409` for genuine idempotency conflicts. Generic `P0001`
   failures, including audit insertion failure, remain unavailable/503 and atomic.

Two Minor findings were also corrected: shared audit formatting delimiter for
four-locale before/after text, and deterministic command validation/not-found
errors distinguished from uncertain outcomes. Reason input normalizes line breaks
and tabs before review. Explicit lock-wait revocation and cross-action key reuse
proofs supplement the initial concurrent cross-admin tests.

The review also identified the split-database integration requirement and a
connection-loss race in a proposed cross-database advisory-lock approach. Durable
account-DB acceptance replaces that approach. Final implementation review and
fresh validation are the acceptance authority; this does not certify deployment.

The final read-only source review reported no remaining Critical/Important findings
after adding function-ownership and schema-CREATE drift rejection, with four real
role regressions. Browser acceptance also caught a native fetch receiver error in
new command requests; the transport now invokes fetch without a wrapper receiver.
Fresh validation results are recorded in the acceptance report.

## Final local acceptance evidence (2026-10-16)

Implementation and local security proofs are complete. **Full-suite acceptance is
blocked**, and this branch is not production certification. All artifacts below
are local ignored files under `artifacts/admin-v1/`.

| Check | Result and evidence |
| --- | --- |
| Admin API and route contracts | 124 passed after the final OpenAPI error-envelope correction; `final-admin-contracts.log`. |
| PostgreSQL 17.11 | All 34 Admin co-located/split-database cases passed, including both last-admin races, revocation during lock wait, restricted roles, audit rollback/immutability and idempotency; `final-sql-wave-regressions.log`. |
| Wave 1A/1B and migration rehearsal | The focused regression run had 378 passes and one OpenAPI declaration failure, subsequently corrected and covered by the 124-pass run above. Real auth/RLS, durable quota/usage and clean/prefix/repeat migration rehearsal passed. The separate empty-role PostgreSQL cluster passed all 63 usage-bootstrap tests in `python-full-ci.log`. |
| Frontend deterministic tests | 18 Admin tests and 17 consumer session/auth tests passed; `node-final.log`, `consumer-node-final.log`. |
| Chromium and Chrome | All 66 cases in the final specification are covered across the unchanged passing cases and the final 16 responsive command cases. Both channels use retries=0; four locales and widths 390/430/1024/1440. See `browsers-verified.log`, `browsers-command-corrected.log`, `browsers-controls-all-widths.log`. The earlier two account-command failures were ambiguous test alert selectors, corrected before the final command runs. |
| Typecheck, lint, build | Exit 0 for all three; lint retains 23 existing warnings. See `typecheck-verified.log`, `lint-verified.log`, `build-verified.log`. |
| Performance/security | All 24 route budgets pass: Admin maximum 1,134,730 bytes, home 1,907,113 bytes, total static 3,294,427 bytes, largest chunk 602,295 bytes. Existing ceilings unchanged. Security/performance gate and tracked-source hygiene pass. See `route-budgets-final.json`, `security-performance-final.json`, `hygiene-final.log`. |
| Release and operations | Release-quality contract checks pass with tests/build explicitly skipped inside that wrapper and independently executed above. Repository operations checks pass; external guardrails remain BLOCKED and production decision NO_GO. See `release-quality-final.json`, `production-ops-final.json`. |
| Full Python | **3,938 passed, 133 skipped, 7 failed**, Python 3.12.13, pytest 9.1.1, 668.72 seconds; `python-full-final.log`. This hermetic run omits external database configuration; live SQL proof is reported separately above. |

The seven final failures are confined to unchanged
`tests/test_earth_engine_worker_pool.py`: crash replacement, failed replacement,
shutdown, credential startup classification, active/queued admission, queued
cancellation and repeated queued cancellation. The same suite on clean current
main (`194d17c`) produced 19 passes and seven failures, with three exact failures
overlapping (`earth-engine-main-baseline.log`). No worker-pool
or satellite implementation/test changes are included. This is evidence of a
baseline/host timing problem, consistent with observed free RAM below 300 MB;
it does not establish the root cause of every failure. The full-suite result
remains red. The satellite initialization case that failed in the earlier broad
run passes in the final run. No deadlines were relaxed or failing tests excluded.

The single-process route measurement hit its existing overall deadline. The
successful measurement used the unchanged `measure_route_assets.cjs` protocol in
eight batches of three routes, with four cold samples per route, the same child
and parent deadlines, network policy and build fingerprint. Every route is
measured; no samples or budgets were reduced. `route-assets-batched-final.log`
and `route-batch-*.json` retain the raw results. The homepage's 18 observed assets
contain no Admin API path, Admin shell marker or exact-lookup UI text
(`home-admin-isolation.json`).

Migration 022 is registered with its canonical checksum and validated only on
disposable PostgreSQL. Migrations 020 and 021 are unchanged. Both owned clusters
were stopped and the temporary clean-main comparison worktree removed. Independent
read-only review found no remaining Critical or Important Admin source findings.
No push, merge, deployment or Wave 1 Integration Gate was performed.
