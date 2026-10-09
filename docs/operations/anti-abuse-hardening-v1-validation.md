# Anti-abuse hardening v1: validation and handoff

Scope: local implementation and mocked verification only. No push, merge, deployment, production traffic, infrastructure changes or credential changes. This record follows all 48 requested report fields; commit identity and post-commit status are supplied by the final handoff.

| # | Requested field | Result |
| --- | --- | --- |
| 1 | Starting SHA | `a677ca6b2dd6957102434b3494f9495556e7c941`; initial HEAD and local `origin/main` matched; initial worktree clean. |
| 2 | Branch | `security/anti-abuse-hardening-v1`, existing isolated linked worktree. |
| 3 | Existing protections reused | `FixedWindowRateLimiter`, provider request caches/coalescing, physical-call metrics, existing provider timeouts/worker pools, satellite process isolation, scrape/operator authentication and upload contracts. Removed the competing shared map admission path. |
| 4 | Threat model | Unauthenticated repeated expensive requests, varied cache keys, failure storms, concurrent fan-out, oversized/streaming input and native geometry exhaustion. Coarse peer sharing and autoscaling multiply exposure. See runbook threat model. |
| 5 | Protected endpoint matrix | Actual inspected geocoding, Places, Routes, Location, Terrain, satellite, valuation, Trend, Finder, Market, operator Market, parcel and VNext routes; additional physical terrain/TGOS/cadastral boundaries. Complete LOW/MODERATE/EXPENSIVE/VERY_EXPENSIVE matrix in runbook. Passive health/status remain available. |
| 6 | Client identity/trust boundary | ASGI transport host only, without port. All forwarded headers, query/token/correlation values ignored. Missing peer shares `unknown`. Deployed repository commands use `--no-proxy-headers`; real end-user attribution is unproven. No per-user claim. |
| 7 | Rate-limit architecture | Existing atomic fixed-window limiter, independent fixed capability dictionaries, at most 4,096 buckets per limiter including overflow; one process-wide operation key per capability. Safe fail-closed rejection; no distributed system added. |
| 8 | Endpoint-specific limits | Geocoding 30/min; Places/Routes/Location 10/min; satellite 2/5min; Terrain/parcel 6/min; valuation/Trend/Finder 20/min; public Market 30/min; operator Market 10/5min; metadata 120/min. Configurable bounded positive values. |
| 9 | Concurrency limits | Nonwaiting per-capability permits: geocoding 4, Places 6, Routes 2, satellite 1, Location 4, Terrain 2, valuation/Trend/Finder 4 each, Market 4, operator Market 1, parcel 2; subprovider ceilings in runbook. Exception/timeout safe; canceled async waiters detach while actual producers retain permits. |
| 10 | Satellite protection | Explicit POST only; strict request, one-generation concurrency and 12/hour generation reservations. Kill switch prevents calls and worker startup; existing feature flag/IAM/timeouts retained. No automatic action/retry/polling. |
| 11 | Places protection | Six category limit and six physical permits preserve one normal fan-out. Per-process 300/hour reservations after cache ownership; cache hits/coalesced work preserved. Partial/zero semantics preserved; all guard-blocked categories return an error instead of mock success. |
| 12 | Routes protection | Two physical permits, 120/hour reservations, material destination/mode cache keys preserved. Killed cached routes return disabled without fallback/provider calls. |
| 13 | Provider budget protection | Aggregate reservations before expensive work, after cache/coalescing where present; failure attempts consume budget. Admissions/reservations/dispatches distinguished. TGOS/cadastral physical dispatch counters added at transport; no cache-hit dispatch counting or duplicate downstream metrics. |
| 14 | Kill switches | Independent `ANTI_ABUSE_<CAPABILITY>_DISABLED` backend flags; malformed settings disable safely. Places/Routes/satellite enforce before cache reuse as well as physical work. Changes across deployed revisions remain owner work. |
| 15 | Input limits | Actual streamed bytes capped at 1,000,000; parcel multipart 11,000,000 preserving 10 MiB file limit. Sixteen body slots, 15s receive deadline, 8,192-byte query cap, 512-character DTO text, finite/ranged coordinates, bounded radii/categories/layers/districts/horizons; cumulative 100,000 geometry coordinates before native construction. Archive limits retained. |
| 16 | Error handling | Safe 429/503 reason/message plus integer Retry-After; 400/413/422 validation, 414 query cap, 408 receive timeout. CORS and safe correlation/security headers preserved. VNext retains guard status and `retryable=false`. No peer keys, credentials, stacks or raw provider output. |
| 17 | Failure isolation | Independent capability quotas/permits, including valuation vs Trend vs Finder and public vs operator Market. Admission rejection does not mutate saved evidence. Places partial state and existing terrain error/limited evidence remain distinct from complete/safe. |
| 18 | Metrics | Existing bounded capability/event counters extended with admit/reject/rate/capacity/disabled/guard/budget/reservation events. Physical calls/cache hits/misses/coalescing/failures remain separate. No user/address/coordinate/peer labels. |
| 19 | Cache compatibility | Existing complete material keys, bounded caches and owner/coalescing logic retained. Hits/coalesced waiters do not reserve another physical call; kill switches checked before selected expensive cached responses. |
| 20 | Multi-instance limitations | Tests demonstrate independent controls each admit their own quota; process restart resets state. Workers/instances/revisions/regions do not coordinate; shared credentials have additional consumers. |
| 21 | Global-budget limitations | **Operational acceptance BLOCKED.** Application limits are process-local and do not guarantee global quota or monetary spending ceilings. No Redis or production infrastructure was introduced. |
| 22 | Edge/WAF owner actions | Verify all ingress and direct-origin paths, preserve/prove peer boundary, establish capability edge/WAF throttles, close origin bypass, measure shared-peer legitimate traffic and record enforcement evidence. Detailed platform-specific contract and official references in runbook. |
| 23 | Provider quota owner actions | Record Google project/API/shared-consumer inventory, enforce supported Maps quotas, verify Earth Engine concurrency/EECU controls, capture enforcement and retain credential/IAM restrictions. No invented quota availability or pricing. |
| 24 | Billing-alert owner actions | Named primary/backup recipients, delivery proof, incident SLA and actual/forecast thresholds; budgets are alert-only. Verify actual eligible spend-cap coverage/delay, combine with quotas and shutoff; record rollout/rollback approval. |
| 25 | Tests added | 35 deterministic anti-abuse tests plus updated map admission tests; fake clocks, threaded contention, mock transports, blocked producers, body streams and geometry spies. Boundaries, reset, independence, memory, spoofing, rejection-before-work, health, CORS, kill/cache/fan-out, authorization and cancellation covered. |
| 26 | Backend test results | Full suite: **3,296 passed, 32 skipped, 1 warning**, 194.85s. Focused anti-abuse: 35 passed; config/deployment/acceptance checks: 65 passed. Skips are existing optional external/platform contracts without configured services. |
| 27 | Frontend results | Relevant unit/static scripts: 16 passed; reliability tests: 12 passed. No frontend product source or dependency lockfile changed. Existing transport displays safe error messages and performs no automatic retries. |
| 28 | Chromium results | **81 passed** in the final selected mocked browser suite. |
| 29 | Chrome results | Installed Chrome: **81 passed**; combined final suite **162 passed** in approximately four minutes. |
| 30 | 390px results | Included mobile 390px assertions passed in selected browser contracts; E10 layout preserved. |
| 31 | API Cost regression | Mocked physical operations remain **23 to 17**, tile decode **8 to 4**; explicit satellite action, no repeat dispatch, complete cache keys and retained spatial evidence pass. Save/Reopen/Compare/Report issue zero automatic analysis/provider requests. |
| 32 | Provider Closure regression | Full backend and selected browser/static contracts pass: Finder quartiles, SQL error/no-data, valuation/Trend isolation, retention, BLUE/GREEN provenance, Places partial state, terrain/source versioning and PLVR operations. |
| 33 | Commercial regression | E3-E10 commercial/trust suites pass across both browser projects. Missing/unknown/partial/unavailable/stale distinctions, saved evidence and zero automatic provider calls preserved; no score/ranking added. |
| 34 | Lint | Exit 0, zero errors; 23 existing warnings. |
| 35 | Typecheck | Exit 0. |
| 36 | Build | Production build and explicit mock-origin `build:e2e` pass. Initial browser attempt with the production-origin build was stopped; final browser evidence uses the correct mock-origin build. |
| 37 | Dependency audit | `npm audit --omit=dev --audit-level=high`: zero vulnerabilities, exit 0. Existing full-audit gate passes its documented dev-only `GHSA-vfj7-8cjw-p6xm` exception, expiring 2026-11-04; no CI or dependencies weakened. |
| 38 | Release gates | Release quality, production operations, security/performance, npm audit, route budget, bundle budget, repository hygiene and provider-free local production smoke pass; SBOM generated locally. Pilot execution gate passes all nine checks with no required checks omitted. |
| 39 | Independent review | Read-only security reviewer examined real changes and ran mocked tests. Reviewed spoofing/proxy identity, bypass/memory, permit leaks, input/streaming, metric privacy, fan-out, kill switches, multi-instance claims and browser retries. |
| 40 | Critical/Important findings | Critical: 0. Important: 4 found and fixed, each reproduced with a failing regression then passing (details below). Remaining generic nested terrain reason is Minor and documented; no false complete/safe state. |
| 41 | Files changed | Backend routes/middleware/startup, shared guards/DTO bounds, provider/service work boundaries, geometry, fixed metrics, config manifest, tests and three operational documents; exhaustive list below. No frontend product files, infrastructure, credentials or CI workflows changed. |
| 42 | Operational runbook | `docs/operations/anti-abuse-hardening-v1.md`: endpoint thresholds/config, threat/ingress, quotas/billing, emergency flags, staged rollout/rollback, local verification and named owner acceptance contract. |
| 43 | Commit SHA | Supplied in final handoff after creation of exactly one commit: `security: harden expensive api endpoints against abuse`. |
| 44 | git status --short | Post-commit result supplied in final handoff; validation logs/build artifacts remain ignored. |
| 45 | git diff --check | Passed before commit; final post-commit result supplied in handoff. |
| 46 | Remaining acceptance blockers | Unverified deployed ingress/origin exclusion, shared-peer tuning, effective provider quotas, cross-consumer/global spend exposure, alert recipients/delivery and owner rollout/rollback signoff. No live acceptance testing performed. |
| 47 | Safe to push/open PR? | Yes for code review after the single-commit/clean-worktree check in the final handoff. All local gates pass. No push/PR publication is performed under this task. |
| 48 | Ready for Final Production Acceptance after merge? | **No.** Owner edge/provider/billing enforcement and acceptance evidence are mandatory; merge alone does not resolve global protection. |

## Review fixes and testing integrity

1. Unauthorized operator Market requests could reserve work before authentication. Separate operator quota and reserve work only after token authorization; public Market remains independent. Regression verifies rejected authorization spends zero work units.
2. Upload geometry could reach native construction before cumulative resource checks, and async upload performed native work on the event loop. Bound GeoJSON/KML/Shapefile totals before native construction and move upload processing into the retained parcel worker. Rejection-before-construction regressions pass.
3. Default Places concurrency of four rejected part of the existing six-worker fan-out. Set six default physical permits; a deterministic blocked six-category test verifies ordinary complete fan-out.
4. Admission middleware outside CORS prevented the permitted frontend from reading guard errors. Wrap admission in CORS and remove the competing outer length check. Allowed-origin 429/503/413 regressions pass.

The first full backend run exposed satellite replacement startup timeouts: importing FastAPI through the new guard unnecessarily loaded it in spawned workers. Use lightweight Starlette HTTPException and preserve the existing startup timing assertions. Both failures and the final full suite pass; no timeout/test weakening.

Release-quality invocation used `--skip-tests --skip-frontend-build` only because the complete tests and build had already run separately. Pilot gate executes its own existing command set. All abuse and browser provider work uses local mocks; passive local production smoke reports `external_provider_called=false`.

## Pilot execution gate

`python scripts/pilot_release_quality_gate.py --execute`: **pass**, `required_not_run=[]`. Passed checks: diff, migration, environment, bundle budget, full Python tests, production build, E2E build, Chromium and installed Chrome pilot-evidence suites. Existing default browser retries recovered transient UI deadline failures under the gate's default parallelism; the final runner status is passed with no failed tests. No assertions, deadlines, retry configuration or CI gates were changed.

## Changed files

- `backend/api/abuse_middleware.py`
- `backend/api/routes_commute.py`
- `backend/api/routes_location_insight.py`
- `backend/api/routes_map.py`
- `backend/api/routes_market.py`
- `backend/api/routes_parcel_geometry.py`
- `backend/api/routes_terrain_risk.py`
- `backend/api/routes_valuation.py`
- `backend/api_main.py`
- `config/hosted-environment-manifest.json`
- `conftest.py`
- `services/anti_abuse.py`
- `services/input_limits.py`
- `services/adapters/geocoding_adapter.py`
- `services/adapters/google_places_adapter.py`
- `services/adapters/nlsc_cad_gateway_adapter.py`
- `services/adapters/nlsc_gateway_adapter.py`
- `services/adapters/routes_adapter.py`
- `services/adapters/tgos_geocoding_adapter.py`
- `services/commute_routing_service.py`
- `services/location_resolver.py`
- `services/map_service.py`
- `services/parcel_geometry.py`
- `services/provider_cost_metrics.py`
- `services/satellite_reference.py`
- `services/terrain_risk_providers/ardswc_slope_hazard_provider.py`
- `services/terrain_risk_providers/geologycloud_provider.py`
- `tests/test_anti_abuse.py`
- `tests/test_map_api.py`
- `docs/operations/anti-abuse-hardening-v1-plan.md`
- `docs/operations/anti-abuse-hardening-v1.md`
- `docs/operations/anti-abuse-hardening-v1-validation.md`
