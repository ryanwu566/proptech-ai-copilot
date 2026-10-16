# Admin Control Plane v1 — architecture and acceptance

Historical read-only acceptance. Superseded by
[the current Wave 1C integration contract](admin-control-plane-v1-integration.md).

Base: `0185c81416a56b14c1dada38d959d90aeac2ecf4` (fetched origin/main on 2026-10-13).

## Routes and trust boundaries

`/admin`, `/admin/users`, `/admin/usage`, `/admin/providers`, `/admin/limits`,
`/admin/operations`, `/admin/audit` are independent Next.js route entries.
They load an isolated client operator surface. The static HTML contains only
an inert shell and loading text, never privileged records. In this existing
browser bearer-session architecture, navigation returns that shell; the UI
then shows authentication required or permission denied. Page HTTP 200 does
not assert admin authorization. Every data request goes to `/v1/admin/{section}`
and independently returns 401/403 before accessing its source.

Reuse `services.vnext.auth.require_authenticated_principal`: the existing
Supabase asymmetric JWT verifier validates signature, expiry, issuer, audience
and UUID subject. The browser session helper is transport convenience and is
never the authorization authority. See the [Supabase JWT verification contract](https://supabase.com/docs/guides/auth/jwts).

`PlatformAdminAuthority.lookup(principal)` is the single Wave 1A integration
seam. Only a current record matching that verified user, exact role
`platform_admin` and account status `active` authorizes. None, exceptions,
suspended accounts, mismatched identity, unknown roles/status and malformed
objects deny. Production defaults to `UnavailablePlatformAdminAuthority`,
which denies all callers. No allowlist, environment flag, workspace role,
JWT metadata, localStorage value or test switch can enable production access.
No new login system, privilege table, migration or grant command is created.
Deterministic tests inject an authority through FastAPI dependency overrides.

## Data sources and truthful states

`AdminSummarySource.read(section, cursor)` returns bounded `AdminSnapshot`
projections, separate from authorization. The API revalidates the DTO and
checks the requested section before serializing. Source failures return a
safe 503 envelope without exceptions, SQL, source bodies or credentials.

| Section | v1 source and behavior |
| --- | --- |
| Overview | Wave 1A accounts/activity/events and Wave 1B volume/attempts/429/5xx/warnings are unavailable. Health remains unavailable without operational evidence. Every metric has value/state, window and source. |
| Users | Unavailable pending an authoritative minimized account API. Typed rows support opaque UUID, account status, platform role, creation/activity timestamps and optional usage summary. Suspend/restore are explicitly unconnected; no local mutation exists. |
| API Usage | Existing `PROVIDER_COST_METRICS.snapshot()` supplies instrumented process-local logical requests, physical calls, admitted/rejected and cache hits where a counter exists. Missing counters stay null. These are not a complete HTTP request ledger or fleet aggregation. Provider attribution, HTTP 429/5xx totals, latency, quota consumption and monetary estimates remain unknown. Distinct existing 429 rejection reasons must not be mistaken for complete HTTP volume. Wave 1B must supply durable semantics. |
| Providers | Existing passive `provider_status()` projection reports configuration categories, last observation, freshness and last success/failure. It does not call an external provider. Configured does not imply healthy; `not_checked`, `no_data`, demo and unavailable remain distinct. No environment variable names or values are serialized. Capability-disabled state uses the same `capability_enabled()` function as enforcement, including malformed settings failing closed. Quota evidence is unavailable. |
| Limits | The effective `CONTROLS.policies` used by existing admission provides request/operation windows and limits/concurrency. Audience is explicitly all peers and enforcement is process-local, not anonymous/free account tiers or a distributed quota. Enabled state consumes the enforcement function. Read-only; no policy editor. |
| Operations | Existing validated build identity when built; unknown otherwise. Compatibility is declared/unverified, maintenance reflects the existing runtime switch, fleet enforcement explicitly local-only. Backup, restore and incident evidence unavailable. No rollback/WAF/recovery claims. |
| Audit | Unavailable until a reviewed platform-scoped append-only audit reader exists. Existing workspace audit concepts alone do not authorize a global audit query. Typed projection includes timestamp, UUID actor, allowlisted event/target/outcome/reason only. Read-only, max 50 rows/page. No metadata JSON rendering. |

Metric state `known` requires a numeric value, including legitimate zero.
Unknown/unavailable/not-applicable require null. Cost distinguishes a server
estimate with currency, unknown, and not-applicable; frontend only formats the
server estimate, never derives currency from attempts or quota units.
Available, partial, empty, unavailable, loading and request-error states differ.
Missing account/audit APIs are unavailable, not empty tables asserting no users.

## Refresh, lifecycle and performance

One bounded GET on route entry, one per explicit refresh, and one per requested
cursor page. No polling, background provider analysis, scrape credential or
provider billing call. Refresh discards old privileged rows while loading;
route changes abort requests. Session expiration/sign-out clears displayed
records and aborts pending reads. Session-generation checks prevent late
responses after logout or account changes from restoring rows. Already rendered
records clear on SDK identity changes, including another tab signing in. There are no
automatic retries. The existing authentication SDK may refresh its session.

Transport uses a 15-second abort deadline including SDK recovery, session acquisition
and expiry handling, no-store, omitted cookies, rejected
redirects, a 262,144-byte streaming response cap, strict parsing and a fixed
admin path. Each row list is capped at 50; metrics/operations at 20. Cursor
tokens are 1–128 URL-safe characters, server-selected and reauthorized each
request. Pagination replaces rows; it never accumulates an unbounded log.
The local source has no cursor-backed records yet. Wave 1A's implementation
must provide principal-bound cursors and enforce its own bounded query deadline.

Route code is imported only by admin pages, not consumer layout/homepage.
Performance Budget v2 includes all seven admin routes and validates the inert
shell under the existing network-blocked cold production measurement. All
admin UI code is eager within this isolated route chunk, so the gate includes
the authorized view's static code even when no session is configured.
Each new route has a fixed **1,300,000-byte** initial-static ceiling, below the
existing Compare ceiling (1,301,212); this is a policy cap, not a fabricated
measured baseline. Existing baselines/ceilings remain unchanged. Global
8,000,000-byte static and largest-JS 900,000-byte gates remain unchanged.
Missing admin routes fail coverage. Evidence uses the existing build-bound
fingerprint, two samples at each of 390/1440, and no provider/API network access.
The first eighteen-route measurement reached the original execution deadline
at the final admin route. Keep the eleven-route allowance unchanged and add
15 seconds per extra route, capped at seven: 315 seconds internal / 345 hard.
All four samples per route, cleanup rules and byte ceilings remain unchanged.

## Privacy and operator UX

DTOs discard unknown fields at every boundary; audit vocabulary is closed.
UUIDs minimize identity; no email, password hash, JWT, provider token, property
history, credentials, arbitrary metadata or environment values are rendered.
React text rendering escapes cells. Unknown values are never converted to zero.
No admin response or snapshot is stored in localStorage or consumer case storage.
Responses use `Cache-Control: private, no-store`, including denials and failures.
The inherited CSP, security headers and bearer handling remain in force.

Four copy catalogues support zh-TW/en/ja/ko through the existing locale selector.
Operational timestamps include localized date/time with seconds and explicit UTC.
Operational contract identifiers remain precise. Desktop uses dense tables;
tablet/mobile tables become labeled records. Navigation wraps, long UUIDs and
codes wrap, visible focus and semantic status text remain available. No chart
library is needed: labeled numeric cards and tables expose all evidence in text.
Widths 390, 430, 1024 and 1440 are browser acceptance targets.

## Dependency / integration report

**ALREADY WIRED:** VNext verified identity and browser session lifecycle;
independent FastAPI platform-admin guard; passive provider observation/config;
effective process-local anti-abuse policy and capability disable semantics;
process-local cost-unit snapshot; validated backend build identity; four locales;
bounded private DTO transport; route-specific performance gate.

**WAITING FOR 1A:** Implement the authority lookup from its authoritative
account/privilege/status API and register it at `get_platform_admin_authority`.
Connect minimized account pagination and safe global audit reader through
`get_admin_summary_source`. Add current suspension/revocation guarantees. Safe
suspend/restore commands remain Wave 1A-owned and need separate server guards,
idempotency/concurrency protections and append-only audit before any UI control.

**WAITING FOR 1B:** Durable logical-request/provider-attempt ledger; provider
attribution; time windows; 429/5xx/latency; real quota consumption; cache semantics;
known/unknown/not-applicable cost estimates; account-tier/fleet policies and quota
evidence; operational warnings. Replace/compose the narrow summary adapter,
preserving scope/source/time/state and no fresh provider work. Policy mutation
requires its safe authorized audited server command; none is added here.

**EXTERNAL OPERATIONS EVIDENCE REQUIRED:** Hosted identity/compatibility,
ingress/WAF, fleet enforcement, backup/restore rehearsal, rollback readiness,
provider/account quotas and incidents. Local passing tests do not prove these.

No push, merge, deploy, hosted request, database mutation or secrets editor is
part of this wave. All authorized browser records in acceptance are synthetic
network fixtures, never fake production fallback data.

## Validation evidence

Deterministic server tests use generated in-memory asymmetric signing keys;
no signing credentials are committed. Browser fixtures are confined to the e2e
test module and absent from production imports.

| Check | Result |
| --- | --- |
| Admin authorization/data/privacy/policy tests | 99 cases pass within the focused Python suite. |
| Admin model/client | 15 passed, including unknown vs zero, cost, privacy, session generation, timeout, native fetch binding and UTC timestamps. |
| Frontend deterministic suite | 391 passed (`node --test` over all `lib`/`scripts` test files). |
| Browser acceptance | 25 passed on Chromium: four locales × four widths across seven routes; direct gates, states, keyboard/focus, bounded refresh/pagination, provider/cost truth, account switch and delayed sign-out. External provider/API traffic is rejected by fixtures. |
| Relevant Python regressions | 259 passed: VNext JWT/authorization, Admin, provider observations/cost, guardrails, budgets and exact OpenAPI route surface. |
| Route measurement regressions | 37 Python + 12 Node passed, including bounded extra-route execution time and unchanged baseline-run deadlines. |
| Ordinary production build / typecheck | Passed. |
| Lint | Passed: zero errors; 23 existing warnings outside Admin files. |
| Production dependency audit | Zero vulnerabilities; existing dev-only advisory policy gate passes without exception changes. |
| Performance Budget v2 | All 18 routes pass. Each admin route: 1,117,446 / 1,300,000 bytes. Homepage: 1,906,347 / 2,066,966 bytes. Three admin-exclusive assets absent from homepage. |
| Global bundle budget | 3,166,817 / 8,000,000 static bytes; largest JS 602,354 / 900,000 bytes. |
| Security/performance and release contract gates | Passed. Release contract gate used `--skip-tests --skip-frontend-build` after separate builds/test runs; it is not proof of a green full Python suite. |

The full Windows Python 3.13 run recorded **3,796 passed, 6 failed, 32 skipped**.
One failure was the old exact VNext route catalogue: it now explicitly includes
the guarded admin GET and its documented VNext error envelopes, with tests
passing. Two subprocess output failures were Windows cp950/UTF-8 mismatches;
the affected tests pass with `PYTHONUTF8=1`. Three failures were unchanged Earth
Engine worker spawn/replacement deadline tests; an isolated Python 3.13 rerun
recorded 24 passed / 2 failed. Re-running that entire module under the repository
CI's Python 3.12 line, in an isolated uv environment with the same pytest/FastAPI
versions, recorded **26 passed**. No worker code or deadlines were changed.
The complete Python suite has not been re-run green under Python 3.12; CI must
confirm the whole suite before integration. Local frontend tooling was Node
24.14.1/npm 11.11.0; the repository Node pin is 24.21.0. No lockfile changed.

## Independent review and fixes

An independent read-only reviewer identified four material issues, all fixed
with regression coverage: clear prior rows when another account signs in;
preserve seconds/timezone in operational timestamps; leave incomplete HTTP 429
totals unknown; bound SDK session acquisition/expiry by the request deadline.
Browser sign-out/account-switch/delayed-response tests pass. Further validation
fixed the SDK recovery-generation race, native fetch receiver binding, and
reading the current effective enforcement registry. There are no deferred
review findings. The new route workload required bounded execution headroom,
not relaxed byte ceilings or fewer measurements.

Hygiene and `git diff --check` are final local gates before the sole feature
commit. Hosted authorization, persistence, provider-account quotas and external
operational evidence remain unproven; the authority seam still denies by default.
