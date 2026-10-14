# Wave 1A final integration — 2026-10-14

This is the current-main integration record. The earlier [frozen acceptance](wave-1a-auth-account-acceptance.md) remains historical evidence, including its old-base failures. Nothing was pushed, merged, deployed or changed in a hosted Supabase project.

## Source and integration

- Authoritative fetched main: `99fe79a82af37a4783b89275b747036ce7e1e06b`.
- Frozen Wave 1A: `a0c037fc915096dc8b02665035dee21ff4b8c5ba`; historical base `0185c81416a56b14c1dada38d959d90aeac2ecf4`.
- Historical backup: `backup/wave-1a-frozen-a0c037f`; clean detached reproduction: `C:/Projects/proptech-wave1a-frozen-a0c037f`.
- Preflight was clean, 4 behind/1 ahead, with no unexpected commits. The feature was replayed onto main without an intermediate commit. The single header-import conflict was resolved by keeping both My Places and Account, and the latest product navigation was preserved.
- Final feature diff: **65 files**.
- The existing production browser workflow remains byte-for-byte unchanged, including `timeout-minutes: 45`, workers, retries, timeouts and coverage.
- Final commit identity and clean-tree/topology verification are returned with the integration completion message; a report cannot embed the hash of its own containing commit.

## Auth and account contract

The implementation extends the existing Supabase browser singleton/session implementation in `frontend_next/lib/vnext-auth-session.ts`. Backend identity remains the asymmetric JWKS verifier and `AuthenticatedPrincipal` in `services/vnext/auth.py`; issuer, audience, expiry, signature, privileged-token and malformed/oversized token checks fail closed. Workspace authorization and `DatabasePrincipalContext` are reused without modification. No password storage, custom signing, new session format, browser service key or client-controlled administrative authority was introduced.

`/login` provides password login, existing session restoration, safe credential failure and bounded transport deadlines. `/signup` preserves explicit authenticated, confirmation_required, request_accepted, validation_error, configuration_unavailable and provider_error model results. Confirmation and duplicate-account public wording is neutral. `/account` reads only the verified user's bounded authoritative account, displays active/suspended state and authored email without translation, and offers device-local logout. Missing configuration disables forms and denies protected access. Redirects after authentication are fixed to `/account`; arbitrary query redirects are ignored.

Password reset is **request only**. It returns acceptance, never a claim that mail was sent or delivered. The provider owns confirmation/recovery destinations and templates. Recovery completion is external to this slice. Provider contracts were checked against [Supabase signup](https://supabase.com/docs/reference/javascript/auth-signup) and [reset request](https://supabase.com/docs/reference/javascript/auth-resetpasswordforemail); no live provider acceptance is claimed.

The private account record contains only user_id, status, platform_role, created_at and updated_at. Auth remains identity authority. Workspace owner/admin/manager/member/viewer roles grant no platform role; only a fresh server-side consumer/platform_admin record can authorize platform administration. User metadata is ignored as authority. Missing, mismatched or malformed account authority and lookup failure deny access. A suspended platform admin is also denied.

Every protected VNext consumer route depends on `require_active_account`. Direct API calls cannot bypass it by forging headers, browser storage, displayed state or user_metadata. Stable safe failures are `account_suspended` (403) and `account_unavailable` (503). The bearer-protected own-account status exception remains readable while suspended and sends no-store responses. Platform administration never bypasses workspace tenancy.

Wave 1B can consume verified UUID/stable `AuthenticatedPrincipal`, `AccountAuthorizer.get_account` / `require_active`, and `require_active_account`, including fail-closed status lookup. Wave 1C can consume `require_platform_admin`, minimal own-account reads and suspension status. Account mutation remains a separately authorized operator boundary; no Admin, quota, usage or audit-command workflow was added.

## Compatibility and database

No Saved Cases, Preferences, Scenario drafts, Decision Room records, My Places or commute results are uploaded, converted, assigned to an owner, refreshed or rewritten by authentication. Auth browser tests assert exact local-store preservation through login/restore/logout. Existing anonymous property workflows remain available. Account stays in the header tools area alongside the current primary workflow, including Preferences and My Places; current Case Scenario/Decision Room/Commute navigation, Compare and Report remain in place.

Migration `020_consumer_account_foundation.sql` remains additive and unoccupied on main; no renumbering or merged migration edit was necessary. The registry contains 21 entries / 16 managed migrations and next sequence 021. It creates/backfills private consumer accounts, forces RLS, permits own-account SELECT and default-only user_id INSERT for the dedicated request role, and grants no UPDATE/DELETE. Conflict inserts cannot restore suspension or elevate privilege. Restrictive workspace-members RLS denies membership-dependent tenant data for missing/suspended accounts. Disposable PostgreSQL 17 migration rehearsal, grants, tenant isolation and suspension proof passed; this does not mean production migrations or RLS were deployed.

## Fixed performance provenance

Each Auth baseline was reproduced as **1,112,023 bytes** from the clean detached frozen commit using its own unchanged lockfile and `npm ci`, the historical repository pins Node 24.21.0 / npm 11.19.0 / Next 16.3.8. A separate corroborating reproduction with the original available host runtime (Node 24.14.1 / npm 11.11.0) produced exactly the same bytes. Auth/API public configuration was absent, matching the frozen acceptance configuration. The application source stayed clean.

The measurement harness was taken from authoritative current main and changed only outside the frozen worktree to add the Auth route inventory and rendered selectors. It uses the existing Performance Budget v2 contract: unique uncompressed static files; two fresh contexts per viewport at 390 and 1440; loopback documents/static only; API/provider requests and prefetch blocked. Files, build ID, fingerprints, lockfile hash, harness hashes and toolchain are preserved in `docs/performance-budget-v2-baseline.json`.

`/login`, `/signup` and `/account` are required measured routes, each with fixed ceiling **1,334,428 bytes**: baseline + min(20%, 300,000), using existing integer rounding. Missing routes, incomplete attribution and excess bytes fail. All 14 previous route budget entries and global ceilings remain unchanged. The header imports only a small Account entry catalogue; form/reset/account copy and the Supabase component remain outside the homepage dependency graph.

Final build measurements and gate results are recorded in the [machine-readable validation artifact](wave-1a-final-validation-20261014.json). Configured-anonymous route measurement was explicitly exercised, in addition to the ordinary unavailable-configuration production build.

## Independent read-only review and repairs

A separate reviewer found no Critical issue, two Important issues and two Minor issues. All were addressed:

1. Delayed SDK signup/password-login could persist a session after logout. Real installed-SDK regression tests first reproduced both failures. Logout now invalidates access immediately, marks pending writes stale, drains the bounded SDK writes before completing local logout, and ignores late SIGNED_IN while clearing. SDK signout notifications also drain pending local writes without awaiting SDK methods inside the callback. Tests cover local logout, signout notifications, persisted session removal and subsequent deliberate login. Existing cross-tab login behavior remains covered by browser tests.
2. The first `/account` measurement selector required an unavailable-config alert. It now validates a stable labeled account section for both configured-anonymous and unavailable-config pages. The exact-selector test failed before the fix; configured cold production measurement verifies the real rendered path.
3. Measurement diagnostics now retain only allow-listed Auth route identities, with a regression test.
4. Full four-locale Auth copy was imported by the shared header for one label. A small entry-only catalogue follows main's My Places pattern and removes that unnecessary shared content.

An additional cross-feature acceptance defect was diagnosed before changing behavior: the existing provider observer did not recognize new `/account` RSC prefetch as internal navigation. The initial interrupted pack showed only same-origin `/account?_rsc=…` URLs in four provider-call assertions. Classification **C: deterministic test-contract gap**. Exact Auth routes were added under the existing same-origin GET + RSC header + `_rsc` contract; APIs, external URLs, POSTs, missing signatures and unknown routes remain counted. A new unit test was observed failing before the change and passing after. No retry, timeout, worker or coverage setting was relaxed. The full pack was restarted on the final build; initial failures remain disclosed here.

No reviewer finding was deferred. Recovery completion, quota/Admin implementation and anonymous public API protection were left at their explicitly required scope boundaries, rather than expanding Wave 1A.

## Acceptance evidence

Full raw logs, JUnit files and browser artifacts are retained locally under `.tmp/wave1a-integration/`; the adjacent validation JSON contains portable commands, counts and final measurements. No credentials or raw provider responses are committed as evidence.

Fresh checks include the full Python 3.12 suite, focused Auth/JWT/workspace/security contracts, disposable PostgreSQL, all deterministic frontend tests, VNext hardening/GIS contracts, typecheck/lint, production builds, no-retry Auth Chromium/Chrome matrix, real-loopback API authority tests, cross-feature Chromium regression, unavailable-config browser acceptance, required route/global budgets, security/performance gate, release source/production operations contracts, npm policy audit, repository hygiene and diff whitespace checks.

The release source gate uses `--skip-tests --skip-frontend-build` because fresh full-suite and build commands are run separately; its result is not represented as proof that its skipped phases ran. Existing lint warnings and dependency-policy exceptions remain visible in the validation record. No baseline failure is used to excuse an integrated failure. One initial Windows evidence-driver print failed under CP950 after the Node test process had already passed all 427 tests (classification D: console encoding); the UTF-8-safe final driver completed successfully with 432 passing tests. This was not a product-test failure.

## Hosted truth and required operator work

Implemented and tested locally does not prove hosted acceptance. Operators still need:

- Matching public Supabase URL/publishable key; server issuer/audience/JWKS configuration; server-only dedicated-role database connection; approved CORS/CSP origins.
- Apply registered migrations through 020 and verify dedicated-role grants/forced RLS in the target project.
- Configure email/password Auth, confirmation mode/templates, Site URL, SMTP and a provider-owned recovery destination that can finish password update. `detectSessionInUrl` stays false.
- Perform hosted signup/login/restore/logout/suspension tests, JWKS rotation/availability checks, actual confirmation/recovery and delivery tests, and deployment-origin security checks.

Email delivery, hosted signup/reset, production migration application and production RLS acceptance remain **unproven**. No deployment or hosted-ready assertion is made. A local green integration can be reviewed in a PR while these hosted release conditions remain explicit.

## Final measured results

| Check | Fresh final result |
| --- | --- |
| Full Python 3.12.13 | **3,748 passed, 33 skipped, zero failures**, 313.21 seconds; 155 dependency deprecation warnings |
| Earlier fresh full Python | 3,734 passed, 33 skipped, zero failures before 14 additional explicit role/JWT cases |
| Focused backend | 189 domain/Auth tests; final Auth/JWT/security/budget pack 117; final source/operations pack 68; all passed |
| Disposable PostgreSQL 17 | **25 passed, zero skipped**; migration ordering, forced RLS, tenant isolation and suspension; cluster stopped |
| Deterministic frontend | **432 passed** across 61 files; Auth model 25; measurement harness 17; VNext hardening 35; GIS contract passed |
| Typecheck / lint | Passed; lint zero errors / 23 existing warnings; E2E exclusion policy unchanged |
| Production builds | Frozen pinned baseline, configured integrated production compiler and ordinary unavailable-config production build all passed |
| Focused Auth / identity / real backend / invalid credentials | **74 passed**, 37 Chromium + 37 Chrome; retries disabled, workers=1 |
| Four locales / four widths | zh-TW, en, ja, ko at 390, 430, 1024, 1440; all three Auth routes; active authored email, labels, keyboard/focus, overflow and runtime checks passed |
| Unavailable-config browser | **34 passed**, 17 per browser; includes the complete locale/width matrix and independent asset observations |
| Cross-feature browser | **153 passed**, zero skips/failures, Chromium, retries disabled, 15.3 minutes; complete restarted pack |
| Final browser acceptance total | **261 passed**, zero final failures/skips; initial observer failures remain disclosed above |
| `/login` ordinary production | **1,112,711 bytes** / fixed baseline **1,112,023** / ceiling **1,334,428** |
| `/signup` ordinary production | **1,112,711 bytes** / fixed baseline **1,112,023** / ceiling **1,334,428** |
| `/account` ordinary production | **1,112,711 bytes** / fixed baseline **1,112,023** / ceiling **1,334,428** |
| Configured Auth production | 1,112,474 bytes per route; all 17 route budgets passed |
| Homepage ordinary production | **1,907,364 bytes** / unchanged ceiling 2,066,966 |
| Total `.next/static` | **3,250,478 bytes** / unchanged ceiling 8,000,000 |
| Largest client JS | **602,354 bytes** / unchanged ceiling 900,000 |
| Required routes / global / security-performance | All passed on both configured and ordinary production builds |
| Release quality/source contracts | Passed with full Python/build run separately; source gate's skipped phases remain explicitly `not_run` in its raw result |
| Dependency audit | Passed repository policy; production has no blocking finding; existing exact dev-only advisory exception expires 2026-11-04; no policy/dependency/lockfile changes |
| Initial broad-suite failure classification | Four **C** observer-contract failures; fixed with RED/GREEN test, then the whole 153-case pack passed fresh |
| Existing ceilings changed | **NO**; all 14 existing route entries unchanged |

The 33 full-suite skips are reported as skips, not passes. Dedicated disposable PostgreSQL proof ran separately with zero skips. No historical timing failure is used to excuse an integrated failure.

Local integration is suitable for PR review after the final commit/topology check. Hosted release conditions above remain unproven. The safe push command is supplied for a human to execute, and was **not** executed:

```powershell
git -C C:/Projects/proptech-auth-account-v1 push --set-upstream origin feat/auth-account-foundation-v1
```
