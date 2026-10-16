# Wave 1B hosted closure: dedicated usage database

Production remains **STOP / NO_GO**. This revision authorizes no production
connection, database mutation, Render resource/configuration change, push,
merge, or deployment. Commands below are prepared for later separately approved
steps; only disposable local rehearsal is authorized and has been performed.

Starting application revision: `59631992e03c05ff01e67fb691710c738fcc6d1b`.
Local work branch: `ops/wave1b-hosted-usage-db-closure`.

## Architecture and legacy boundary

The application's `API_USAGE_DATABASE_URL` is intentionally separate from its
application/legacy database URLs. Use a **new dedicated PostgreSQL 17 instance**
for Wave 1B quotas and telemetry. Leave the existing production database and its
migration ledger untouched. The dedicated database requires only immutable 021
and the bounded subsystem history created by this bootstrap; it does not require
Auth tables or migrations 001?020.

Section B previously inspected the legacy target under an approved read-only
transaction. It found PostgreSQL 17.6, current/session user `postgres`, no 020/021
ledger records, no usage schema/roles, and five ledger checksum mismatches
(001 dedupe, both managed 002 migrations, 003 coverage, 007 ledger). Classification
was **E: unexpected state**, with earlier managed migrations also missing from
the ledger. Supabase-specific roles were observed, so the target also needs
separate verification against prior Render database assumptions. That connection
was closed. **Do not reconnect to or repair that target as part of this task.**

This separation removes the dependency between Wave 1B usage provisioning and
legacy database-history reconciliation. It does not excuse the drift: establish
provenance and reconcile the legacy history in a separate authorized task.
Never forge historical ledger rows or change registered checksums.

## Repository-owned bootstrap

Primary mechanism: `scripts/bootstrap_usage_database.py`, with the fail-closed
catalog verifier `scripts/usage_database_security.py`. It consumes the actual
registered migration file, rehashes the exact canonical bytes it executes, and
splits it only at two fixed ownership-transfer/ACL blocks. It does not copy the
migration body or invoke the global migration runner.

Immutable file: `database/migrations/021_api_usage_quota_ledger.sql`.
Canonical LF SHA256:
`00ed7d4b78de6d92c285ab8cd87241d1477bee2ce6e97caef6bbf6e2f43b98af`.

The script defaults to a database-free plan:

```powershell
python -B scripts/bootstrap_usage_database.py
```

PASS: `status=plan`, `database_contacted=false`, expected checksum. No URL is
read and no connection is attempted. Failure means stop and investigate locally.

### Freshness and actor contract

Execution requires all of the following:

- An explicitly named expected database and acknowledgement of a fresh dedicated
  target. The only accepted connection variable is
  `API_USAGE_BOOTSTRAP_DATABASE_URL`; there is no fallback to the production,
  application, VNext, or runtime URL. Values never enter arguments or output.
- PostgreSQL 17; a direct LOGIN CREATEROLE administrative connection, with
  current user equal to session user, owning that database, NOSUPERUSER, NOBYPASSRLS, and NOREPLICATION.
  Rehearsal additionally proves NOCREATEDB works; database creation is setup only.
- An otherwise fresh database: only system schemas and empty `public`, with no
  unrelated objects/types/functions, extra extensions, default ACLs, event
  triggers, large objects, publications/subscriptions, or foreign servers.
- No preexisting `proptech_usage_*` roles. Roles are cluster-wide: a new database
  on a cluster already hosting these roles is refused. Use a dedicated instance.

No force, adoption, repair, down-migration, or historical-chain mode exists.
An already provisioned or partial target is refused with a bounded category.
For bootstrap itself, inspect fresh state, schema/role creation, migration,
security cleanup, verification and subsystem history all use one transaction.
Errors roll back the entire attempt, including transactional role creation.
There is no exception permitting manual partial-state cleanup in production.

### Ownership-transfer seam and PostgreSQL 17 membership semantics

Raw 021 creates ordinary NOLOGIN roles and grants executor schema USAGE only.
An ordinary actor requires SET ROLE to executor, plus executor schema CREATE,
to transfer function ownership. Granting only one does not solve the other.
See [PostgreSQL ALTER FUNCTION](https://www.postgresql.org/docs/17/sql-alterfunction.html).

For each function, execute the original migration prefix, then temporarily:

1. Grant actor executor membership with INHERIT TRUE and SET TRUE.
2. Grant executor CREATE on `api_usage`.
3. Execute the exact original ALTER OWNER, PUBLIC revoke, and intended EXECUTE
   grant together. INHERIT permits the actor to complete the ACL statements
   after ownership changes; the connection never switches to executor.
4. Revoke executor schema CREATE and the actor's own temporary membership.
5. Assert executor has no schema CREATE and actor has neither effective executor
   privileges nor usable SET ROLE capability. Repeat for the second function.

No temporary capability survives commit. Both functions belong to executor;
all tables and schemas stay with the migration actor. PUBLIC has no usage schema,
table, or function privileges. All six tables retain ENABLE and FORCE RLS. The audit also refuses unexpected
column ACLs, user triggers/rules, event triggers, and unrelated public objects;
legitimate internal foreign-key triggers remain.
Executor remains NOLOGIN, NOSUPERUSER, NOBYPASSRLS, NOCREATEDB, NOCREATEROLE,
NOREPLICATION and NOINHERIT.

PostgreSQL 17 automatically grants a non-superuser role creator ADMIN OPTION
under the bootstrap superuser grantor, with SET/INHERIT disabled here. Its
separate administrative-only memberships remain; the actor revokes its own
usable seam grant. The verifier checks every membership option and effective
SET/USAGE capability, and rehearsal attempts an actual forbidden SET ROLE.
A trusted role administrator can deliberately regrant authority later; this is
not a permanent loss of administrative capability. See [role membership](https://www.postgresql.org/docs/17/role-membership.html).

### Honest subsystem history

`api_usage_bootstrap.history` is private, actor-owned metadata. It records exactly
`021_api_usage_quota_ledger`, its immutable checksum, bootstrap version 1,
release SHA, actor, and timestamp. It records no earlier migration as applied.
No `public.schema_migration_ledger` is created. The global application migration
runner assumes the whole managed chain and must **never** target this subsystem
database. Future subsystem changes require an explicit reviewed history model.

## Bounded runtime login provisioner

A separate `provision-runtime` operation audits the installed security state,
refuses an existing runtime role, and atomically creates:

| Property | Required final value |
| --- | --- |
| Name | `proptech_usage_runtime_v1` |
| Attributes | LOGIN, INHERIT, NOSUPERUSER, NOBYPASSRLS, NOCREATEDB, NOCREATEROLE, NOREPLICATION |
| Memberships | Guard and writer only; ADMIN FALSE, INHERIT TRUE, SET FALSE |
| Executor / reader membership | Neither |
| Database/schema/table/function ownership | None |
| Database CREATE / usage-schema CREATE | Neither |
| Credential | Null password; separately provision a real credential securely |

The runtime inherits guard EXECUTE on consume and writer telemetry/prune
permissions without switching roles. Reader is unnecessary: writer already has
the SELECT privileges used by the telemetry store. Guard has no telemetry DML;
writer has no direct quota-policy/counter mutation privileges. Browser/request
roles have no usage access. Credential provisioning is deliberately separate;
the provisioner accepts no password and prints no connection details.

The runtime startup guard now also rejects CREATEDB, REPLICATION, predefined
PostgreSQL role memberships, SET-reachable CREATE authority, ownership of
the database/schema/functions, reachable unsafe roles, ADMIN OPTION and CREATE,
in addition to its existing superuser/BYPASSRLS/executor/table-owner protections.
It checks both current and original session authority, rejecting disguises via
SET ROLE. Reachability checks are deliberately conservative: inaccessible
memberships to unsafe roles are rejected too.

## Future production sequence: proposed, not executed

1. Review the local commit and rehearsal/security evidence. Independently verify
   the intended new database/service identity. Separately authorize provisioning
   a dedicated Render PostgreSQL 17 instance, backup/recovery and an isolated
   provider rehearsal. Local PG17 evidence does not certify provider restrictions.
2. Privately inject the **new dedicated** administrative URL into
   `API_USAGE_BOOTSTRAP_DATABASE_URL`. Never reuse the inspected legacy URL.
   Confirm supported TLS, CREATEROLE/admin membership authority, and fresh target.
3. After separate execution approval, run the repository bootstrap:

```powershell
python -B scripts/bootstrap_usage_database.py --execute --acknowledge-fresh-dedicated --expected-database <approved-new-database-name> --release-version 59631992e03c05ff01e67fb691710c738fcc6d1b
```

Changes: new usage schemas, roles, grants, policies, two functions and one
subsystem history record. PASS: `status=bootstrapped`, exact checksum, all
precommit checks pass. STOP: any refusal/error. Recovery: transaction rollback
on error; after successful commit preserve additive state for investigation.
No automatic DROP, cascade cleanup, restore, or retry against partial state.

4. Separately approve the bounded runtime operation:

```powershell
python -B scripts/bootstrap_usage_database.py --operation provision-runtime --execute --acknowledge-fresh-dedicated --expected-database <approved-new-database-name>
```

Changes: one runtime LOGIN and guard/writer memberships. PASS:
`status=runtime_provisioned`, `credentials=not_provisioned`. STOP: any refusal.
Recovery on failure: transaction rollback. Provision the password afterward
through the operator's secure credential process; do not pass it to this chat,
SQL literals, source, logs, or command arguments.

5. With separate approval, authenticate directly as that runtime login and verify
   current/session identity, startup guard, telemetry startup probe, consume,
   idempotent batch replay and retention. Functional probes write even if rolled
   back: obtain explicit approval. Never use destructive disposable fixtures
   against production. Do not simulate a runtime login using SET ROLE from admin.
6. Only after those gates, separately approve Render configuration. Preserve the
   existing valid 64-hex `API_USAGE_PEER_HMAC_KEY`; set `API_USAGE_DATABASE_URL`
   to the dedicated runtime credential, `API_USAGE_GUARD_MODE=postgres`, and
   `API_USAGE_LEDGER_REQUIRED=true`. General/legacy DB URLs remain unchanged.
   Review `POSTGRES_SSLMODE` and platform save actions that might auto-deploy.
7. Deployment is a distinct approval. Reverify the exact backend/frontend SHAs
   and release identities; do not silently deploy a newer main. Then separately
   approved health/readiness/release/provider-status and hosted smoke checks must
   prove durable guard and telemetry availability across instances/flushes.
   Configuration alone is not closure evidence. Do not disable fail-closed
   behavior, fall back to local quotas, or treat general DB readiness as proof
   that the dedicated usage database is healthy.

## Local-only rehearsal and evidence

Primary commands:

```powershell
python -B scripts/rehearse_usage_database.py --suite bootstrap
python -B scripts/rehearse_usage_database.py --suite regression
python -B scripts/rehearse_usage_database.py --suite all
```

The script rejects remote Docker endpoints and pins every daemon command to a
validated local named-pipe/Unix-socket endpoint. It uses a digest-pinned,
already-local PostgreSQL 17 image, a fresh
UUID-named container, loopback-only random port, in-memory database storage and
local trust authentication. No image pull or existing database URL is used.
Inherited database URLs and secret variables are excluded from child tools.
Workers block non-disposable libpq connections and external Python network
connections while permitting Windows asyncio loopback. Only the exact container
created by that invocation is removed on exit. No production password is needed.

Final local results: **63 bootstrap/security passed**, **99 relevant regressions
passed**, and **3823 full-suite passed / 101 skipped / 0 failed**, with one
existing Starlette deprecation warning. Initial missing TypeScript dependencies
were restored with offline locked npm installation; a harness exception type
was corrected so blocked network access exercises normal OS-error fallbacks.
No unrelated application code or dependency manifests changed.

See `wave1b-usage-bootstrap-validation.json` for actual counts, commands,
RED/GREEN evidence, review findings and remaining limitations. The all-suite run
omits disposable integration contracts unless explicitly supplied by the runner;
focused regression enables the legacy usage integration tests in a separate
container, and bootstrap tests have their own container and non-superuser actor.

## Recovery and unresolved work

Legacy history drift remains deferred and unresolved. Fresh-database safety
refusals must be investigated, not bypassed. A later provider execution failure
requires separately approved evidence gathering, not broader privileges by
trial and error. Retain known-compatible immutable artifacts and a recoverable
checkpoint before production changes. No automatic rollback may remove Wave 1B
quota enforcement or overwrite legacy data. Production stays NO_GO until all
provider, credential, runtime, deployment and hosted validation gates pass.
