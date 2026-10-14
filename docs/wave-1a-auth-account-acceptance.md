# Wave 1A — Consumer Auth & Account Foundation v1

Historical implementation and acceptance, 2026-10-13 (Asia/Taipei).

For authoritative current-main integration and fresh acceptance, see [final integration](wave-1a-final-integration-20261014.md). The results below describe the frozen feature and its old base; they are not the final integration verdict.
Base: `0185c81416a56b14c1dada38d959d90aeac2ecf4`, fetched and fast-forwarded from origin/main before implementation. The original feature branch/worktree was clean, with no unrelated commits. One final local feature commit; no push, merge or deployment.

## Implemented

`/login`, `/signup`, `/account` and a localized Account link in the commercial header. All use the established four-locale catalogue/provider and commercial design tokens. Forms have semantic labels, password autocomplete, visible focus, associated validation errors, loading/disabled controls and bounded public errors. Anonymous property exploration remains available.

Identity continues to use `frontend_next/lib/vnext-auth-session.ts`, the existing Supabase browser singleton/official persisted sessions, `services/vnext/auth.py` asymmetric JWKS verifier, workspace authorization, and `DatabasePrincipalContext`. No password store, new JWT issuer/session format, service credential or invented browser token storage was added. The browser JWT shape check is advisory; FastAPI verifies signature, issuer, audience and lifetime.

Signup returns authenticated, confirmation_required, request_accepted, configuration_unavailable, validation_error or provider_error. Session-bearing responses must pass existing token checks. Confirmation/accepted/duplicate-account outcomes share neutral public wording; no response claims delivery. Login uses Supabase password sign-in with generic failures. Restore uses the existing session refresh and a bearer-authenticated own-account request. A backend 401 invalidates only the matching session. Account responses are discarded when the session generation changes; auth events clear stale displayed accounts before restoring. Logout uses Supabase local scope (this device), invalidates the current tab immediately, and reports provider failure without claiming successful revocation. Auth HTTP requests have a 10-second abort deadline; the existing SDK may retry refresh failures within its bounded refresh window.

Password-reset **request only** calls the provider's existing API without a caller-controlled redirect. It reports request acceptance, never email delivery. This slice does not implement a recovery/password-update callback.

## Authoritative account and suspension contract

Registered additive migration `020_consumer_account_foundation.sql` creates a private account record: user_id (auth.users FK), status (active/suspended), platform_role (consumer/platform_admin), created_at, updated_at. Existing Auth users are backfilled as active consumers; subsequent records are created lazily on verified account access. No email/profile/password/token/IP/location history is persisted. Existing migration checksums remain frozen; next sequence is 021.

The table forces RLS. The dedicated non-owner/non-BYPASSRLS `vnext_api` request role can read its own account and INSERT only user_id. Database defaults and INSERT policy force active/consumer; conflict inserts never reset an existing role or suspension. It has no UPDATE/DELETE grant. Platform-admin authority is a fresh server-side table lookup, separate from workspace owner/admin/manager/member/viewer. JWT user_metadata and workspace roles cannot grant platform privilege. Missing, mismatched, malformed or unavailable account authority denies access.

All protected VNext routes share `require_active_account`; suspended requests receive stable `account_suspended` (403), unavailable authority receives `account_unavailable` (503). `/v1/account` is a bearer-protected, no-store own-status exception so a suspended user can understand their status. There is no account-update or Admin endpoint. A restrictive workspace-members SELECT policy also blocks membership-dependent tenant RLS for suspended/missing accounts. Workspace access still requires the established membership/role checks; platform admin does not bypass tenancy.

Status/role changes require a separately authorized database operator. Such changes must also set updated_at; do not grant browser/request roles UPDATE. No Admin workflow is claimed. Auth deletion is restricted by the account FK until the approved retention/deactivation process handles the record.

## SavedCase and security boundaries

No SavedCase implementation, import wiring or ownership mapping changed. Tests preserve the exact browser SavedCase value across signup/login/restore/logout; preference/case browser regressions are included. Signing in never uploads cases, refreshes providers or rewrites evidence. Durable consumer-owned cases, cross-device migration, billing, quotas and collaboration remain future work.

Passwords are supplied only in provider request bodies; no password/JWT/provider errors are rendered or logged by this slice. Existing browser config accepts only a publishable Supabase key; service-role/secret keys are rejected. API calls use Authorization Bearer, omit cookies, disable caches, reject HTTP redirects, and accept no user-controlled target. Navigation after login/signup is fixed to `/account`, ignoring redirect query parameters. Existing CORS, write-origin enforcement, pilot-cookie CSRF protection, CSP and security headers remain intact. Consumer bearer credentials are explicitly attached rather than automatically sent as an application cookie; existing pilot CSRF contracts remain separate. Account data is not exposed through the Supabase Data API.

## External Supabase configuration still required

Use existing browser variables NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY; backend SUPABASE_URL or SUPABASE_JWT_ISSUER (same project), expected audience authenticated, and server-only VNEXT_DATABASE_URL authenticated directly as vnext_api. The hosted environment manifest now records these conditional server requirements. Missing browser configuration disables forms; missing API/database verification denies account/protected access. No real secret was committed and no new public service secret is required.

Operators must apply registered migrations through 020, provision the dedicated role, verify issuer/JWKS/audience and CORS/CSP origins, enable email/password auth, configure confirmation behavior, email templates, Site URL and SMTP delivery. Confirmation templates must support confirmation followed by ordinary password login because detectSessionInUrl remains false. Reset requests additionally require a working provider-owned recovery destination/template that completes password update; the current application cannot consume recovery tokens. Do not enable hosted reset acceptance without verifying that destination. Supabase public enumeration behavior depends on confirmation settings; verify intended provider settings before launch. See [provider signup contract](https://supabase.com/docs/reference/javascript/auth-signup) and [reset request contract](https://supabase.com/docs/reference/javascript/auth-resetpasswordforemail).

## Local acceptance evidence

Tests use mocked Supabase HTTP/SDK contracts, in-memory signing keys and a loopback-only disposable PostgreSQL 17 cluster; no live commercial Supabase call occurs.

| Check | Observed result |
| --- | --- |
| Focused auth/account Python | 17 account authority/direct API tests passed; migration registration test passed |
| Existing VNext auth/authorization/domain API pack | 182 passed before six additional direct suspension cases were added |
| Final focused account/migration/security/configuration pack | 90 passed |
| Disposable PostgreSQL 17 | 25 passed, zero skipped; includes account grants/forced RLS, suspended case read/write denial, migration rehearsal, existing VNext tenant isolation; cluster stopped |
| Frontend deterministic suites | 62 Node tests passed; 35 VNext hardening checks passed; GIS contract passed |
| Browser flow/regression pack | 116 unique cases: 54 consumer auth, 14 existing identity auth, 48 preferences/SavedCase regressions. Main run 113 passed/3 failed; corrected duplicate-email CORS fixtures and repeated both-browser duplicate/cross-tab cases: 4 passed. All 116 cases have passing final outcomes across run/rerun |
| Production unavailable-config browser pack | 34 passed: 16 locale/width combinations plus route measurement in each of Chromium and Chrome; no external requests |
| Locale/width matrix | zh-TW/en/ja/ko × 390/430/1024/1440 × three routes, both browsers; focus, labels, localized copy and overflow checks passed |
| Final production build/typecheck | Passed with public auth/API configuration absent; build concurrency limited to two workers through CIRCLE_NODE_TOTAL=3 (no product configuration change) |
| Lint | Exit 0, zero errors; 23 warnings in unchanged files |
| Performance Budget v2 | All 11 existing route ceilings passed; baseline/ceiling files unchanged |
| Global bundle budget | Passed: 3,161,562 static bytes; largest JS 602,354 bytes versus unchanged limits 8,000,000/900,000 |
| Security/performance release gate | Passed |
| Release quality source contracts | Passed with --skip-tests --skip-frontend-build; full Python/build were run separately, so this is not an all-green integrated release claim |
| Migration registry/static validation | Passed, 21 registered / 16 managed migrations; next sequence 021 |
| Hygiene | git diff --check passed; no new dependencies or lockfile change, no historical SQL/checksum edits |

Cold route measurement uses the same document/static-only, prefetch-blocked semantics as Performance Budget v2. Both browsers measured `/login`, `/signup`, `/account` at **1,112,023 bytes each** (unique uncompressed JS+CSS loaded). Ordinary navigation including automatic prefetch measured 2,223,405 bytes; the cold figure above is the comparable route metric, not compressed transfer size.

Same-lockfile production build of BASE_SHA (separate archive and dependency install, identical absent public auth/API settings): 3,045,909 static bytes, largest JS 602,354. Feature delta: **+115,653 static bytes (+3.80%)**, +111,104 total JS bytes; largest JS unchanged. Final homepage cold assets: 1,914,397 bytes, under its existing 2,066,966 ceiling. New auth routes are measured separately; no existing ceiling was increased.

The full Python run was **3,700 passed, 33 skipped, 15 failed**. Five failures were frozen pre-Wave-1A route/signup/migration assertions, now updated and passed in the final focused pack. A PLVR subprocess timeout passed on rerun. Worker startup failures varied under concurrent host load; a final isolated module comparison of the feature and BASE_SHA produced **23 passed / the same 3 failed** on both:

- `tests/test_earth_engine_worker_pool.py::test_crashed_worker_is_joined_and_replaced_once_without_request_replay`
- `tests/test_earth_engine_worker_pool.py::test_timeout_kills_worker_before_one_bounded_replacement`
- `tests/test_earth_engine_worker_pool.py::test_failed_replacement_cleans_other_worker_and_all_pipes`

Initial worker failures also included wrong request/generation, project capture, shutdown, credential-unavailable startup, queued cancellation and active cancellation; those passed in the final module comparison. The intermediate rerun also exposed slot-count, physical-generation and before-executor cancellation timing failures, which likewise passed in the final comparison. No Earth Engine production or test code was changed. The overall Python acceptance is **not all green**, and baseline reproduction is not a reason to hide these failures.

Reproduction commands: `npm run test:consumer-auth`, `npm run test:vnext-hardening`, the package's existing preference/reliability/design-system/runner/maps/GIS commands, `node e2e/run-e2e.cjs e2e/consumer-account.spec.ts e2e/property-identity-auth.spec.ts e2e/preference-tradeoff.spec.ts`, and the explicit unavailable-config spec with WAVE1A_UNCONFIGURED=1 after a production build with absent public auth configuration. Backend: `python -m pytest -q`, the focused modules, and existing VNEXT_RLS_POSTGRES_URL/VNEXT_RLS_POSTGRES_DISPOSABLE=1 integration contract targeting a loopback disposable database whose name starts with vnext_rls_test. Performance: `python scripts/analyze_next_bundle.py --measure-browser`, `python scripts/check_route_budgets.py`, `python scripts/check_frontend_bundle_budget.py`.

## Independent review

A separate reviewer found no critical issue or admin/suspension bypass. Fixes: abort stalled SDK transport, clear old account display on auth changes, test late response/401 rejection, normalize logout failure, correct provider API-version/CORS-exposure and joined_at fixtures, advance frozen migration-surface expectations while preserving historical checksums. Recovery completion is explicitly external. Follow-up review found no remaining critical/important security blocker and independently reran all 21 consumer-auth/account-client tests successfully. It also verified the duplicate-signup fixture with an intercepted Chromium experiment. Local tooling's temporary Windows dependency-junction issue was corrected using separate lockfile installs; no dependency/source change resulted.

## Hosted acceptance not proven / future work

Local passing tests do not prove hosted migrations/grants, real JWKS rotation, SMTP or email delivery, confirmation/recovery templates, cross-device logout revocation, hosted CSP/CORS, production UX or operational owners. No hosted-ready claim is made. Wave 1B owns usage/quota/abuse; Wave 1C owns Admin UI. OAuth, billing and durable SavedCase migration are excluded.

Safe for PR after integration review: **NO under an all-green acceptance requirement**. The feature/security review is ready, but the three reproduced baseline worker failures need resolution or explicit acceptance by the integration owner. This document does not authorize push, merge or deployment.
