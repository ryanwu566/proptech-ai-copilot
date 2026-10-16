# Admin Control Plane v1 Implementation Plan

**Goal:** Deliver the operator surface specified in Wave 1C with truthful data and independently authorized server reads.

**Architecture:** Route-isolated Next.js client shell consumes bounded FastAPI DTOs. Reuse VNext verified principals; an unavailable platform-admin adapter denies every request until Wave 1A supplies its authority. Reuse passive provider observations and effective anti-abuse policy without creating auth, a ledger, or mutations.

**Spec:** User-supplied Wave 1C acceptance specification; architecture and acceptance recorded in `docs/operations/admin-control-plane-v1.md`.

**Execution:** Native implementation in the existing isolated worktree. The supplied implementation instruction authorizes the scope and routine design decisions. Exactly one final feature commit overrides incremental skill commits and intermediate approval handoffs.

## Global constraints

- No push, merge, deploy, new authority, ledger, provider probes, or infrastructure mutations.
- Missing authority denies; missing data stays unavailable, never zero or healthy.
- Four locales; widths 390, 430, 1024, 1440; keyboard and visible focus.
- Preserve existing route ceilings, global 8,000,000 bytes, largest JS 900,000 bytes.

## Review focus

- Identity mismatch, malformed privileges, suspended accounts, and privilege lookup exceptions deny.
- Partial and oversized source data is projected onto strict bounded DTOs; metadata and credentials never pass through.
- Late responses after logout/navigation cannot restore privileged data.
- No implicit refresh loop, provider traffic, or unbounded pagination.
- Admin-only code is absent from homepage assets; budget measures route assets.

## Tasks

1. [x] Write failing server authorization and DTO/privacy tests. Implement `services/admin/authorization.py`, `contracts.py`, `summaries.py`, and `backend/api/routes_admin.py`; register with existing error handling. Verify anonymous 401, consumer/workspace admin 403, active platform admin allowed, all bad authority cases denied. Verify provider semantics and bounded sanitized projection.
2. [x] Write failing typed-model/client tests. Implement `frontend_next/lib/admin` contracts, client, and four-locale copy. Parse strict fields, cap rows/payload, preserve cost states, use existing session lifecycle and cancellation. Run deterministic tests.
3. [x] Write browser acceptance before UI. Implement `/admin` and six route-backed sections, manual refresh, safe auth gate, responsive tables, focus, pagination, distinct states. Verify all locales/widths and bounded reads against deterministic network fixtures.
4. [x] Extend Performance Budget v2 with admin route attribution and an explicit fixed ceiling without raising existing limits. Run production browser measurement; verify homepage asset isolation.
5. [x] Document sources, dependency report, validation, limitations. Run frontend deterministic suite, browser acceptance, Python regressions, build/typecheck/lint, budgets, security/release/hygiene/diff gates. Obtain independent branch review, fix material findings, and create exactly one local commit with clean worktree.

## 2026-10-16 integration continuation

The user explicitly authorizes completion in this existing worktree. Current acceptance supersedes the historical read-only scope above. Execute natively and retain exactly one feature commit above current main.

- [x] Integrate Wave 1A AccountAuthorizer, bounded account commands, exact lookup, directory.
- [x] Add migration 022 with immutable audit/idempotency, serialized mutation functions and restricted operator grants; preserve 020/021 byte-for-byte.
- [x] Integrate Wave 1B durable usage and quota policy, fix ambiguous fleet telemetry.
- [x] Complete localized responsive account/quota controls, safe retries, audit details, operational truth.
- [x] Prove SQL concurrency, atomicity, idempotency, privilege boundaries on disposable PostgreSQL 17; run regressions and all required gates. Full Python remains red on seven unchanged worker-pool tests; baseline comparison and exact results are recorded in the integration acceptance document.
- [x] Obtain independent adversarial review, fix Critical/Important findings, squash locally, verify topology. No push/merge/deploy/integration gate.

Review focus: revocation while waiting for a lock; retry after lost response; cross-action key reuse; stale responses after logout; false operational health or fleet claims.

Rebased baseline is `194d17ce721fac5fa878db3c16c1c9233348bae5`. Its supported hosted
Wave 1B topology separates usage from account authority. 022 installs conditionally
on each owning database. Quota commands commit an immutable, payload/store-bound
acceptance record in the account database before remote mutation. Authorization
linearizes at acceptance; each new request/retry reauthorizes. Mutation, result and
audit are atomic in the owning database. Durable claims preserve cross-action key
ownership even if the account connection terminates during remote work. This
replaces a rejected advisory-lock-only cross-database design. Details and recovery
limits are in `docs/operations/admin-control-plane-v1-integration.md`.
