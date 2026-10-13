# Wave 1B continuation implementation plan

**Goal:** Meet the supplied Wave 1B acceptance contract on authoritative main `319d7ef397e63493edebf4c91e6365bf929a04bf`.

**Spec:** User attachment, sections 0?27; retained as the binding task scope. Existing Wave 1B commit was behind main and did not implement distributed enforcement.

**Architecture:** Preserve all existing local safety envelopes. Add a separate synchronous PostgreSQL guard with database-owned finite policies, atomic subject locking, hourly durable admission/rejection aggregates, and bounded server-created retry markers. Keep provider telemetry in its existing bounded background sink. Reuse Wave 1A JWT and account authority, including optional bearer authentication on public expensive routes.

**Constraints:** One final local feature commit; no push/PR/merge/deploy/production DB/live provider traffic. Historical migrations remain byte-identical to main; new migration 021, next 022. User explicitly authorizes implementation and validation; execute inline and amend the existing feature commit at completion.

## Tasks

1. [x] Inspect/fetch/worktree/topology; integrate existing one-commit feature onto authoritative main; preserve 020 and move unpublished Wave 1B migration to 021.
2. [x] RED/GREEN: stable keyed anonymous identity, strict production configuration, optional public bearer/account authority, fail-closed durable admission and safe quota responses (`tests/test_usage_durable_guard.py`).
3. [x] RED/GREEN: SQL atomic consume, shared request/hour/day operation budgets, backend-only grants/functions, duplicate reservation markers, retention. Prove with real disposable PostgreSQL (`tests/test_usage_guard_postgres.py`).
4. [x] Add adversarial endpoint/metric/cancellation/dedup coverage; run focused and existing regression suites, full Python, migration registry, frontend auth/lint/build and release/operations gates. Classify failures without weakening limits.
5. [x] Fresh read-only adversarial review, fix material findings with RED/GREEN tests, update operations/acceptance documentation, amend to one commit and verify clean topology.

## Interfaces

- `UsagePrincipal`: verified UUID subject or HMAC transport-peer subject, never caller-selected claims.
- `AbuseControls.consume_durable(principal, capability, kind, marker)`: called by request admission and existing cache-owner provider reservation boundaries.
- `PostgresQuotaGuard.consume(...)`: database-selected policy; commits separate rejected accounting; raises bounded safe quota error or generic unavailable.
- `api_usage.consume(...)`: fixed-search-path private function executable only by backend guard role; no request-role direct counter/policy mutation.
- `UsageFlusher`: telemetry-only, same batch ID on ambiguous commit, retention maintenance even on quiet processes. Its loss cannot reopen durable quotas.

## Review focus

Account authority must finish before durable authenticated admission. No client retry namespace. No context loss in workers. No new provider attempts on cache/follower/rejection. SQL rejection increments no successful usage. Ordinary owner obeys FORCE RLS; superuser/BYPASSRLS credentials are rejected by runtime. Stale markers and quota rows are pruned with bounded work.

## Execution rulings

- Rebase/amend the existing feature commit rather than create extra feature commits: required by one-commit rule. Original SHA `6254797cb33683e40a1d436d84f8f8ea9a325e74` remains recoverable in reflog.
- Use repository numbered migration registry, not Supabase CLI timestamp migrations: explicit user migration contract takes precedence.
- Development without durable configuration retains process-local controls; production/preview cannot choose local mode. Telemetry may lose buffered observations; quota authority cannot fail open.

## Current-session evidence ledger

- Stable peer key, missing/malformed production secret, database guard absence, optional active-account auth: RED then GREEN.
- Shared budget: 24 simultaneous database connections for quota 5 admitted exactly 5; independent users and fresh adapters retain distinct/shared state as intended.
- Ambiguous telemetry batches, near-hour capture, locked-subject pruning, post-lock clock, cancellation responsiveness and unadmitted identity churn: reproduced and fixed with deterministic tests.
- All Important independent findings fixed in one pass: local admission before optional auth, finite TDX transport accounting, fixed retention index cutoffs. Actual PostgreSQL nested plans verify each time index condition.
- Deferred Minor: legacy telemetry-only summary fleet_quota_enforced=false must be removed/replaced before any future admin presentation; it is not an enforcement source or public endpoint.
- Backend-only migration 021 registry prefix/historical files match main exactly. New sequence 022.
- Full reviewed Python: 3814 passed,45 skipped; final run also enables disposable usage PostgreSQL to exercise all new SQL tests. Exact final outcome is recorded in the operations acceptance appendix.
- Frontend source unchanged; consumer auth25, typecheck, production build, route/mobile asset measurement and unchanged budgets pass. Lint0 errors/23 existing warnings. Gates pass; hosted decision NO_GO.
- User explicitly selected keeping one local commit with no push/PR/merge/deployment; finishing skill menu is unnecessary and worktree remains preserved.

Final acceptance: full Python with real disposable usage PostgreSQL 3828 passed/33 skipped/0 failures; final four-module Wave 1B suite 76 passed; original PostgreSQL auth/RLS/rehearsal25, existing abuse/provider183, auth/registry96. All Critical/Important review items resolved. Exactly one commit is finalized via amend, then clean status/parent topology verified for the final report.
