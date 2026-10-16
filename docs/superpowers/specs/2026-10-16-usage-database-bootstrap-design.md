# Dedicated Wave 1B usage database bootstrap

The operator authorized local engineering, disposable PostgreSQL 17 rehearsal,
independent security review, and one local commit. Production is STOP / NO_GO.
Do not contact the legacy database, reconcile its history, create Render
resources, change configuration, push, merge, or deploy.

## Design

Use a repository-owned bootstrap around the exact registry-verified bytes of
`021_api_usage_quota_ledger.sql`. Do not run the historical application chain.
A dedicated subsystem history in `api_usage_bootstrap.history` records only 021,
its exact canonical checksum, bootstrap version, release identity, and actor.
It does not claim migrations 001–020 ran. The global runner is not suitable for
this database and must never be pointed at it.

The entry point accepts only an explicit bootstrap environment variable, an
expected database name, and acknowledgement of the fresh dedicated target.
Default CLI behavior is a database-free plan. Execution requires an explicit
flag. Freshness requires PostgreSQL 17, a direct non-superuser CREATEROLE actor
owning the database, with LOGIN/NOBYPASSRLS/NOREPLICATION, no unrelated user
schemas/objects, no nonstandard default
ACLs, event triggers, extensions, large objects, publications/subscriptions, or
preexisting usage roles. Existing/partial installations are refused; there is
no force, repair, automatic cleanup, or history reconciliation mode.

Execute the immutable migration as exact contiguous source slices. A fixed,
checksum-pinned seam consists of each ownership transfer and its following
PUBLIC revoke and intended EXECUTE grant. Immediately around that slice only,
grant the actor executor membership with SET/INHERIT and grant executor schema
CREATE. Revoke both capabilities immediately afterward. INHERIT is needed for
the ACL statements after ownership changes. Verify cleanup after both seams.
All schema, role, grant, history, and verification work uses one transaction.
Any failure rolls everything back. Do not set default privileges or elevate
the actor to superuser/BYPASSRLS. The actor's automatic administrative-only
memberships are retained with SET FALSE and INHERIT FALSE. PostgreSQL records
these automatic grants under the bootstrap superuser grantor; an ordinary
creator cannot revoke that grantor's membership. The actor's own temporary
executor grant is removed entirely after each seam. ADMIN alone is not usable
SET ROLE or inherited executor authority, but can deliberately regrant it later.

A bounded runtime provisioner validates the installed subsystem before adding
`proptech_usage_runtime_v1` as LOGIN with a null password. Secure credential
provisioning is a later operator action. It grants only guard and writer with
INHERIT TRUE, SET FALSE, ADMIN FALSE. The creator's automatic runtime membership
is also administrative-only. Runtime has no ownership, CREATE, elevated attributes, executor,
reader, or other memberships. No credentials enter source, tests, or logs.

The runtime guard additionally rejects CREATEDB, REPLICATION, database/schema/
function ownership, reachable unsafe roles, ADMIN OPTION, and CREATE privilege,
including when an unsafe login switches into an apparently safe role. Reject
predefined PostgreSQL memberships and CREATE held by SET-reachable parents,
even when their privileges are not inherited. Final audits reject column ACLs
and executable trigger/rule drift as well as table/function ACL drift.

## Verification

Disposable loopback PostgreSQL 17 uses trust authentication only on an isolated
local container. A superuser creates the test actor and database for setup only.
Bootstrap connects directly as LOGIN CREATEROLE NOSUPERUSER NOBYPASSRLS
NOCREATEDB NOREPLICATION. Test raw 021's failure first, and the corrected path's
success, exact checksum, role options, real SET ROLE denial, complete ACL/RLS
and ownership state, actual guard and writer behavior, runtime rejection cases,
fresh-target refusal, repeat refusal, partial state and rollback. Run focused
and full relevant regressions with production credentials excluded and external
connections blocked. Independent review precedes the sole local commit.

## Alternatives and limits

Provider-superuser execution is unavailable as a portability assumption.
Permanent executor CREATE or executor ownership of tables/schema breaks the
security model. Rewriting 021 or manufacturing old ledger rows breaks history.
The bounded source seam avoids all three. This is an architectural extension
of the existing migration/runtime flow; the user's explicit implementation
brief supplies scope and authorization, and their one-commit instruction
overrides intermediate skill commit/reapproval conventions.

Roles are cluster-wide: use a dedicated PostgreSQL instance, not another
database in a cluster already hosting these role names. PostgreSQL role
administrators can deliberately grant themselves privileges later; cleanup
proves current usable authority, not immunity from a trusted administrator.
Local rehearsal does not certify provider-specific restrictions or production
connectivity. Legacy checksum drift remains a separate unresolved task.
