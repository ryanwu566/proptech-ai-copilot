# Wave 1B Dedicated Usage Database Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, with one independent final security reviewer. The operator authorized implementation and exactly one final local commit.

**Goal:** Bootstrap immutable 021 safely on a fresh dedicated PostgreSQL 17 database without superuser privileges.

**Architecture:** Verify freshness, execute exact source slices with temporary privileges at two ownership/ACL seams, clean up, verify, and record subsystem history in one transaction. Provision a constrained runtime login separately. Keep legacy production untouched.

**Tech Stack:** Python, psycopg 3, PostgreSQL 17, pytest, disposable Docker.

**Spec:** `docs/superpowers/specs/2026-10-16-usage-database-bootstrap-design.md`

## Global constraints

- Do not edit 021 or its registered checksum `00ed7d4b78de6d92c285ab8cd87241d1477bee2ce6e97caef6bbf6e2f43b98af`.
- No production connections, Render changes, pushes, merges, or deployment.
- Exactly one bounded local commit after validation/review.
- Never print, persist, or pass database credentials on the command line.

## Review focus

- Actor role creation defaults or indirect memberships could retain executor authority.
- Object/default-ACL drift could expose SECURITY DEFINER functions or bypass RLS.
- Failed transactions or repeated execution could leave partial cluster-wide roles.
- A connection URL for an unrelated database must never be an implicit default.
- Runtime ownership/CREATE or unsafe session authority must fail startup.

## Tasks

### 1. Bootstrap and subsystem security contract

Files: `scripts/bootstrap_usage_database.py`, `scripts/usage_database_security.py`,
`tests/test_usage_database_bootstrap.py`.

Interfaces: `bootstrap(connection, expected_database, release_version)` owns its
transaction and returns sanitized metadata; `provision_runtime(...)` validates
the subsystem and creates only the fixed runtime login. `verify_security`
checks exact catalog/ACL/membership/ownership expectations.

- [x] Write real database tests first; observe raw migration ownership failure and missing bootstrap failures.
- [x] Implement checksum-pinned contiguous slices and one transaction, exact freshness refusal and metadata history.
- [x] Add runtime provisioner and final security verifier; prove no temporary CREATE/SET/INHERIT survives.
- [x] Prove refusal, rollback, PUBLIC/request denial, forced RLS and real runtime functional operations.

### 2. Runtime startup protection

Files: `services/usage_guard.py`, same integration tests.

Interface: retain `PostgresQuotaGuard.check()` and existing sanitized errors.

- [x] Write failing real-connection tests for CREATEDB and inherited/schema/database ownership.
- [x] Extend catalog audit while retaining current/session checks.
- [x] Verify safe guard and runtime logins pass and unsafe logins fail.

### 3. Rehearsal, runbook, review and commit

Files: `scripts/rehearse_usage_database.py`, hosted closure runbook, validation evidence.

- [x] Run pinned PostgreSQL 17 rehearsal with a direct non-superuser actor, no BYPASSRLS.
- [x] Run focused and full relevant tests, then full pytest with external connections blocked and production environment removed.
- [x] Replace the legacy closure path with dedicated-database steps and preserve the observed legacy STOP evidence.
- [x] Request independent security review, resolve material findings with regression tests.
- [x] Verify 021 diff/checksum, stage only intended files, make one local commit, verify clean worktree and no push/deployment.

## Execution record

- Starting SHA: `59631992e03c05ff01e67fb691710c738fcc6d1b`.
- Existing linked worktree reused; local branch `ops/wave1b-hosted-usage-db-closure`.
- Ruling: user brief authorizes local implementation; preserve their single final commit instead of skill intermediate commits.
- Ruling: dedicated subsystem history replaces the global migration ledger; no historical application records are manufactured.
- Ruling: real PG17 records automatic creator memberships under the bootstrap superuser grantor. Preserve those ADMIN-only grants with SET/INHERIT disabled, revoke the actor's own temporary grant after each seam, and prove effective SET/USAGE denial. Trusted CREATEROLE administrators can deliberately regrant authority later.
- RED: raw immutable 021 failed with `must be able to SET ROLE`; its transaction left no usage schema/roles.
- RED: bootstrap integration failed because the new module did not exist.
- RED: CREATEDB runtime login passed the old guard, demonstrating missing rejection coverage.
- Baseline focused regression: 83 passed, 1 integration skipped, one existing Starlette deprecation warning.

- Independent review: five Important findings and one column-ACL completeness finding; all reproduced with RED tests before the single fix pass.
- Final fix pass: reject unsafe actor attributes, predefined runtime roles and SET-reachable CREATE; refuse executable trigger/rule and column-ACL drift; pin Docker to validated local IPC and exclude inherited Docker/usage secrets.
- Review rulings: retained creator ADMIN-only memberships are an explicit trust boundary; provider behavior and future administrator mutation remain unproven/out of scope; the Python harness is not an OS sandbox against malicious test code. Column-ACL drift was fixed as part of the requested exact security audit.

- After review fixes: bootstrap/security suite 63 passed on PostgreSQL 17.10; relevant regression 99 passed (including all usage PostgreSQL integration proofs).
- First whole-suite attempt: 3772 passed, 87 skipped, 46 failed. Forty-five failures lacked frontend TypeScript dependencies; the bank-rate API failure was caused by the rehearsal socket blocker raising RuntimeError instead of OSError. Restoring locked frontend dependencies from offline cache and using ConnectionRefusedError preserves fallback semantics without allowing any external connection. No unrelated application code changed.

- Task 1: complete; immutable raw ownership failures and bootstrap/security GREEN: 63 passed on PG17.10.
- Task 2: complete; unsafe principal rejection RED/GREEN and 99 relevant regressions passed.
- Task 3: full final suite GREEN: 3823 passed, 101 skipped, one existing Starlette deprecation, 392.76 seconds. All initial failures resolved through offline dependency setup and harness error semantics; no unrelated product changes.
- Final review: five Important findings plus column-ACL completeness addressed with RED/GREEN tests; no deferred findings. Provider behavior, later administrator mutation, and malicious-code OS sandboxing remain explicit limits.
- Final disposition: one authorized local commit; keep this branch/worktree, do not push, merge or deploy.
