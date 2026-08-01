# Security and Performance Release Contract

This document is the authoritative release boundary for the PropTech AI
Copilot security and performance work. It describes controls that are
implemented in this repository and operator actions that remain environment
dependent. It does not claim that a local build proves production readiness.

## Architecture overview

The Next.js application is a public presentation layer. FastAPI owns provider
calls, validation, pilot boundaries, persistence selection, and safe error
responses. Pilot evidence is an additive domain: the SQLite adapter is for
local, test, and explicitly single-process use; a Postgres-compatible adapter
is selected for durable production persistence. Public evidence is aggregate
only and is filtered by consent, verification, publication state, and fixture
exclusion.

## Threat model

| Asset | Actor / entry point | Attack path | Mitigation and test | Residual risk / owner |
| --- | --- | --- | --- | --- |
| Consent and participant evidence | malicious participant / pilot APIs | IDOR or token replay | scoped session lookup, hashed tokens, participant API tests | deployment cookie and retention review / operator |
| Admin and professional review actions | compromised browser / admin routes | privilege confusion or CSRF | separate roles, short-lived scoped cookies, Origin and CSRF checks | durable session revocation requires production store / operator |
| Provider credentials and database | anonymous request / API and provider adapters | error or log disclosure | bounded safe errors, no raw exception response, secret-free tests | runtime secret rotation / operator |
| Exports and printable reports | reviewer or administrator | HTML, CSV formula, or path injection | escaped HTML, CSV formula neutralization, bounded aggregate export | human review of released export / reviewer |
| Public source and aggregate metadata | automated bot / public routes | cache poisoning or stale overclaim | explicit cache classes, publication filtering, source freshness states | CDN configuration verification / deployment owner |
| Application resources | bot / all request bodies and expensive routes | oversized input, retry storm, rate-limit memory growth | Pydantic bounds, body limit, bounded buckets, timeouts and local tests | distributed limiter activation / operator |
| Browser supply chain | compromised dependency | malicious package or bundle leakage | lockfile review, npm/pip audit in CI, bundle and hygiene gates | advisories requiring compatible patch / dependency owner |

## Trust boundaries

1. Browser to Next.js: untrusted input is rendered as text; no bootstrap
   credentials are shipped to the browser.
2. Next.js to FastAPI: only allowlisted API payloads are accepted. Client
   error and performance telemetry exclude exact case values, URLs with query
   state, coordinates, addresses, and free text.
3. FastAPI to database: SQL is parameterized, selected columns are explicit,
   participant scope is checked before every private mutation, and production
   serverless mode fails closed without durable storage.
4. FastAPI to official providers: provider URLs and credentials are
   server-side configuration. User feedback and review notes are never fetched.
5. Private evidence to public aggregate: consent, verification, publication,
   and fixture filters are applied before public output.

## Authorization model

The security module defines `participant`, `reviewer`, `administrator`, and
`public_aggregate_reader` roles. Private participant operations require the
session token hash to match the requested session. Administrative and review
mutations use separate bootstrap secrets for server-to-server compatibility,
or short-lived scoped HttpOnly cookies after a server-side bootstrap exchange.
Authorization is deny-by-default, constant-time for configured secrets, and
resource scoped. A hidden route or frontend-only guard never grants access.

## Token and session model

Pilot and bootstrap values are random, bounded, never logged, and never
returned in general exports. The scoped session payload contains only a random
session identifier, an explicit role, and an expiry; it does not contain the
bootstrap secret. Cookies are HttpOnly, SameSite Strict, bounded by Max-Age,
Secure in production, and use narrow paths. A CSRF cookie is paired with an
`X-CSRF-Token` header for cookie-authenticated mutations. Production should use
a shared signing key or a durable session store so revocation survives process
replacement.

## CSRF strategy

State-changing requests with an Origin are checked against the server CORS
allowlist. Cookie-authenticated admin and reviewer mutations additionally
require a matching CSRF cookie and header. Bearer-style headers remain
available only for explicit server-to-server compatibility and do not put a
bootstrap secret in browser JavaScript. Missing, malformed, or cross-origin
protections receive a generic 403.

## Security headers

FastAPI responses set `X-Content-Type-Options`, `Referrer-Policy`,
`Permissions-Policy`, `X-Frame-Options`, COOP, CORP, and no-store/private
cache policy for pilot and review routes. Production HTTPS responses add HSTS.
Next.js applies the same clickjacking, MIME, referrer, permissions, and base
URI protections. Its CSP permits only the minimal Next runtime inline behavior
required by this application, forbids `unsafe-eval`, objects, and frames, and
documents that map/provider origins must be added only after a reviewed need.

## Export safety

HTML exports escape all untrusted text and CSV exports neutralize spreadsheet
formula prefixes. Export output is aggregate-only, bounded, and never includes
participant identity, contact, raw case facts, coordinates, SQL, or secrets.

## Input, output, XSS, SQL, and SSRF safety

All pilot models forbid extra fields and bound strings, arrays, scores, event
metadata, exports, and request bodies. Stored text is rendered as text or
escaped in HTML. CSV cells beginning with spreadsheet formula characters are
prefixed according to the export policy in `safe_csv_cell`. SQL uses
parameters; dynamic identifiers are selected from fixed internal allowlists.
The `safe_external_url` helper accepts only HTTP(S), rejects credentials and
local/private destinations, and never fetches user-controlled links. Provider
redirect and DNS policy remains an operator/provider-adapter responsibility.

## Production persistence decision

SQLite remains supported for local development, unit tests, isolated browser
acceptance, and explicitly documented single-process deployments. When
`APP_ENV` is production/preview or the runtime is marked serverless, a missing
durable pilot database makes persistence `unavailable`; the application does
not silently use a writable local file or claim that evidence was stored.
`PILOT_EVIDENCE_DATABASE_URL` selects the additive Postgres adapter. The
operator must apply `database/migrations/004_add_pilot_evidence.sql` and
`005_add_pilot_security_indexes.sql` through a reviewed migration process,
then enable the adapter only after isolation and transaction checks pass.

## Cache classification

| Route class | Policy |
| --- | --- |
| Static/versioned public assets | immutable CDN cache with versioned names |
| Public aggregate evidence | cacheable only after publication filtering and with freshness metadata |
| Pilot session, consent, feedback, review, export, deletion | private, no-store |
| Provider-dependent results and errors | no-store unless a reviewed public reference contract exists |

Service workers and CDN rules must never cache participant, reviewer, admin, or
raw case responses. Cache keys must include locale and public scope where a
public cache is approved.

## Dependency and CI security

`security-performance.yml` runs the Python suite, frontend build, migration
validation, route budgets, static secret hygiene, dependency audits, and a
machine-readable release gate without production credentials. Third-party
actions are used only for checkout/runtime setup with least-privilege
permissions. The workflow does not expose secrets to forked pull requests or
write to production. A disposable CycloneDX-style manifest is generated as a
CI artifact and is not committed.

## Performance baseline

The baseline is recorded from an existing production build by
`scripts/check_frontend_bundle_budget.py` and
`scripts/check_route_budgets.py`: uncompressed static bytes and largest client
chunk are measured before any claim of improvement. The route report keeps
separate budgets for homepage, competition demo, TaxOracle, Map Insight,
pilot, and administrative surfaces. No route is allowed to claim a lower
budget by omitting required runtime assets.

## Route bundle budgets

Road catalogs and map/report/admin code must remain out of public initial
chunks; existing route boundaries and lazy loading are regression-tested.
Optional first-party telemetry sends sampled LCP, CLS, INP, or TTFB only with a
coarse route, viewport, locale, release, and pilot-mode classification. It is
disabled unless explicitly enabled and never stores address, price, case,
coordinate, contact, token, or feedback data.

## API and database performance

Important routes have bounded body, array, page, export, retry, and provider
timeouts. Idempotency keys protect event ingestion. The additive indexes cover
campaign/status lookup, session completion, event idempotency, and review
publication. Operators must capture before/after query plans and local warm
p50/p95 measurements using synthetic records only; no production records are
copied into fixtures.

## Load-test envelope

## Load, Lighthouse, and browser acceptance

Use only local or explicitly created preview environments with synthetic test
records. The bounded envelope is 1, 5, 10, and 20 concurrent virtual users;
record throughput, p50, p95, errors, timeouts, lock errors, and rate-limit
responses. Run Lighthouse mobile and desktop for the public routes, then the
existing Playwright Chromium/Chrome, four-locale, mobile 360/390/430,
console/page/network checks. A missing preview credential or durable database
is an environment requirement, not a passed production claim.

## Residual risks

The repository cannot prove production CDN behavior, durable database
availability, advisory freshness, or preview cookie behavior without operator
configuration and an approved preview environment. These remain explicit
release blockers rather than silently passing checks.

## Release gate and remaining human actions

The local gate distinguishes `pass`, `failed`, `not_run`, and `environment
required`. Local security tests, migration validation, the frontend build,
bundle/route budgets, and browser acceptance must pass before a release
candidate. Human actions remain: configure a strong session signing key and
durable pilot database, apply reviewed migrations, run dependency advisories
against the approved network mirror, verify HSTS/CSP and cookie behavior on a
real HTTPS preview, capture performance/load/Lighthouse measurements, and
review residual advisories before deployment.

Rollback is an application redeploy to the previous version. Keep additive
tables until retention and deletion review is complete; disable pilot admin
and reviewer boundaries during rollback. Never delete evidence tables as a
first response.

## Incident response

Use the bounded correlation ID and support reference. Revoke scoped sessions,
rotate bootstrap secrets in the runtime secret manager, disable pilot
administration, revoke publication where appropriate, preserve only approved
aggregate evidence, and review logs without copying raw request data. Do not
put tokens, addresses, exports, SQL, or stack traces in issues or chat.
