# API cost optimization v1

Implementation date: 2026-10-08 (Asia/Taipei). No deployment, push or merge.
All provider measurements use deterministic injected transports/adapters.
No monetary or Places SKU savings are claimed.

## Starting state

Clean linked worktree `C:\Projects\proptech-api-cost-optimization`, branch
`perf/api-cost-optimization-v1`; HEAD and origin/main both
`a27bbdead6e3f4196426a6016a20ddff6f86f1f1`. Required status, refs and last
12 commits were inspected before changes. Work stayed in this worktree.

## Baseline provider map

| Capability | Frontend trigger / backend | Original downstream work and reuse | Final behavior |
|---|---|---|---|
| Google Geocoding | Explicit map search; POST `/map/search` | One GET per search; adapter recreated; no coalescing; TGOS recovery remains independent | Default adapter reused; identical concurrent GETs coalesce; acceptance unchanged |
| Trusted address resolution | Destination on explicit POST `/commute/route`; address lookup | TGOS first, Google fallback; re-resolves repeated text even when Routes hits cache | Safe derived resolved result reused for 60 seconds; supplied coordinates bypass geocoding |
| Google Places | Accepted map location POST `/map/nearby`; explicit Location POST `/location/insight` | Up to six parallel category POSTs; unbounded 600s cache; five-decimal coordinate key; duplicate categories and concurrent misses repeat calls | Unique categories, exact coordinates, bounded category cache and whole-fan-out single-flight; successful categories survive partial failures |
| Google Routes | Explicit Commute action; POST `/commute/route` | One computeRoutes POST; unbounded 600s result cache; rounded coordinates; concurrent misses duplicate | Complete material key, 256 entries and in-flight sharing; original observation timestamp retained |
| Satellite | Terrain coordinate becomes available; POST `/terrain/satellite-reference` | Automatically generates on mount/remount; no completed reuse or single-flight | Explicit action; zero generation on mount, disclosure, locale change or saved-case reopen; bounded imagery cache and native async sharing |
| ARDSWC | Explicit Risk/Terrain action; POST `/terrain-risk/analyze` | Four MVT layers, up to 36 tiles/layer; raw-byte cache unbounded; every hit decodes again; concurrent misses duplicate | Bounded successful decoded tiles; geometry rematched per exact point/radius; partial tile errors preserved |
| GeologyCloud liquefaction | Same Risk action/endpoint | Three classification GETs for each identical point/radius/city | Complete final layer reused/coalesced; partial/error remains retryable |
| NLSC numeric terrain | Same Risk action/endpoint | One fixed numeric gateway POST per identical point query | Successful numeric observation reused/coalesced; WMTS and village identities remain separate |
| WRA / GSMMA | Same Risk action/endpoint | Validated local artifacts and existing singleton indexes | Existing version/hash/scenario validation and warm reuse preserved; no speculative optimization |
| Market / Valuation | Explicit Market/Price actions | SQL/read model; CSV fallback already bounded LRU | Unchanged; Finder quartiles, SQL failures, Trend isolation, 36-month window and BLUE/GREEN provenance preserved |
| RIS / TDX | Demographics / explicit secondary commute lookup | Database observations / operationally refreshed station snapshot | Unchanged remote refresh separation; TDX button gets synchronous duplicate guard |

Application retries remain one attempt per Google HTTP request, numeric NLSC
request, GeologyCloud classification, and ARDSWC tile. ARDSWC retains six workers,
1.5s per-tile timeout and 2.5s query budget. GeologyCloud retains its existing
classification order. Satellite retains the existing bounded worker lifecycle,
eight-second total deadline, credential single-attempt transport, disabled HTTP
authorization replay and `ee.data.setMaxRetries(0)`. One generation can involve
several SDK HTTP stages; generation counts are not HTTP-stage counts. No retry
layer was added or removed blindly. No frontend automatic retry was introduced.

## Deterministic cost units

Baselines were executed before each provider change. Original starting-SHA
modules were also executed against the same combined journey fixture afterward
to verify the aggregate. These are mocked workload counts, not a prediction of
production hit ratios or billing.

| Workload | Before | After | Boundary |
|---|---:|---:|---|
| Two identical concurrent map Geocoding searches | 2 GETs | 1 GET | In-flight only; no completed map geocode cache |
| Two identical destination-address route queries | 2 Google resolutions and up to 2 TGOS attempts | 1 resolution of each required provider | Safe derived resolver context, 60 seconds |
| One category, two identical concurrent Places requests | 2 POSTs | 1 POST | Category/language/radius/configuration identity |
| Category list food, food, park | 3 category dispatches | 2 | Duplicate categories suppressed before dispatch |
| Six-category Places request followed by an identical warm request | 6 total POSTs | 6 total POSTs | Existing sequential saving preserved; second adds zero |
| Two identical concurrent Routes requests | 2 POSTs | 1 POST | Different destination/mode/coordinate/configuration misses |
| Satellite mount after accepted Terrain result | 1 generation | 0 | Explicit request required |
| Two identical explicit Satellite requests | 2 generations | 1 | Concurrent or within valid completed cache window |
| 64 concurrent Satellite requests plus one warm repeat | Not measured at this concurrency | 1 observed generation | Mocked native async manager; no waiter thread starvation |
| Two warm ARDSWC queries for one tile | 1 GET, 2 decodes | 1 GET, 1 decode | Exact per-query geometry matching remains |
| Two identical concurrent cold ARDSWC tile queries | 2 GETs, 2 decodes | 1 GET, 1 decode | Successful tile only; failures remain visible |
| Two identical GeologyCloud queries | 6 GETs | 3 GETs | All three classifications complete |
| Two identical NLSC numeric queries | 2 POSTs | 1 POST | Numeric gateway identity only |
| Two passes through combined provider segment | 23 operations, 8 tile decodes | 17 operations, 4 tile decodes | One controlled tile per each of four MVT layers |
| Saved representative journey / Save / Reopen / Compare / Report | 0 analysis calls | 0 analysis calls | Separate real browser navigation proof |

The combined segment uses production resolver/adapter/service code with mocked
transport boundaries: destination resolution, six Places categories, one Route,
one numeric NLSC query, three liquefaction classifications, four controlled MVT
tiles and one Satellite request. Its first pass costs 17 operations in both
versions. Its second pass previously added six operations and four decodes; now
it adds zero within valid cache windows. It excludes variable real-world tile
fan-out and provider-internal HTTP stages. The browser proof consumes saved
Property, Market/Valuation, Location/Commute, Risk and Overview evidence, saves
the snapshot, reopens it, compares it and reads Report. It does not pretend those
saved views are live analysis. See `tests/test_api_cost_journey.py` and
`frontend_next/e2e/api-cost-journey.spec.ts`.

## Cache architecture and identity

`services/provider_request_cache.py` supplies thread-safe TTL/LRU bookkeeping,
synchronous and native asynchronous single-flight, copied results and conservative
caller-controlled retention. Provider work/waiting never holds the global lock.
Each cache has a finite active-flight count equal to its entry capacity. Capacity
overflow bypasses dedupe rather than adding an unbounded flight map or blocking
unrelated keys. This is resource bookkeeping, not an anti-abuse quota.

| Cache | TTL | Entry / active-flight bound | Additional retained bound |
|---|---:|---:|---|
| Map/direct trusted Google geocoding | 0 (in-flight only) | 256 per adapter | No completed payload |
| Final safe derived address resolution | 60s | 64 process entries | Safe normalized schema only |
| Places category observation | 600s | 256 per adapter | Existing max 10 places/category |
| Whole Places fan-out | 0 (in-flight only) | 256 per adapter | No completed partial response retained |
| Routes observation | 600s | 256 process entries | Small normalized result only |
| Satellite embedded JPEG plus metadata | 300s | 16 process entries | 4 MiB serialized retained results; existing 250,000-byte image/365,000-byte response bounds |
| ARDSWC decoded tiles | 600s | 256 process entries | 16 MiB retained Python-container accounting |
| GeologyCloud final complete layer | 300s | 64 process entries | Existing response/feature bounds remain |
| NLSC numeric observation | 60s | 64 process entries | Small normalized observation only |

All new identities use exact material coordinates, rather than five-decimal
rounding. Harmless address whitespace is normalized without removing meaningful
tokens. Places includes radius/category order/provider language/type filters/
field mask/configuration. Routes includes both endpoints/mode/provider endpoint/
field mask/fixed routing options/configuration and provider namespace. The API
does not accept departure time; if it gains one, that input must enter the key.
Satellite includes dataset/date window/AOI/RGB/SCL/cloud filter/dimensions/image
format/configuration and weak provider identity. Its lifecycle clears reuse on
startup/shutdown. ARDSWC includes layer/tile coordinates/URL/vintage/version and
decodes successful tiles only. GeologyCloud includes administrative hint/routed
area/radius/coordinates/configuration. NLSC uses the numeric contract version and
validated configured origin; it has no provider-supplied dataset vintage.

Credential rotation replaces provider namespaces. Credential-bearing adapters
are not retained as cache keys; custom Routes providers use weak identity, and
unweakrefable custom providers bypass reuse. No API key, authorization header,
database URL or signed Satellite URL is retained. Request keys can contain private
query inputs internally and are never logged or exposed as metric labels.

Expired entries are removed on access; valid hits become most-recently-used.
Entry/byte overflow evicts the least-recently-used completed result. Oversized
images/tiles are returned within their existing response bounds but not retained.
Copying and active request/response buffers temporarily use memory beyond retained
byte accounting; the byte budgets do not claim a whole-process RSS limit.

Authentication/provider errors, timeouts, malformed responses and partial results
do not become completed-success hits. Explicit empty Places is successful zero;
malformed present rows become category failures. Explicit empty Routes remains
the pre-existing deterministic no-route observation with its existing 600s TTL;
error/missing/malformed collections become unavailable. Failed owners always
release flights. Async caller cancellation detaches from shared work without
cancelling other callers; the original generation still has its bounded deadline.
Invalidation epochs prevent old in-flight work repopulating a cleared cache.

Cache hits preserve original observation times. Mixed cached/retried Places uses
the oldest relevant successful category timestamp; ARDSWC preserves tile fetch
times and rematches each property query. Trusted address reuse preserves the
existing resolver's acceptance policy; it does not claim cadastral identity or
the separate map geocoding acceptance contract's ROOFTOP quality.

## Frontend and trust

Satellite shows not-run until the explicit localized action. It keeps coordinates,
secondary-evidence status, attribution, limitations and disclaimer. Its evidence
and response commits are keyed by coordinates/property context; old A imagery
cannot appear under B. No imagery is persisted in browser localStorage.

Synchronous submit refs protect Location, Terrain, Risk, Routes and TDX against
two clicks before React commits loading state. Existing disabled loading actions
remain. Input/radius/mode/identity changes invalidate pending responses. External
Location props and result-ready events now invalidate the old request generation;
render identity also hides old evidence before the cleanup effect runs. Risk uses
its current case/fingerprint for response and display isolation.

Presentation-only locale changes do not dispatch analysis. Places provider
language is material to its key. Navigation prefetch, mounts, disclosure,
saved-case reopen, Compare, Report, storage notifications and print remain
provider-free consumers. Saved summaries stay distinct from live evidence.

The Places field mask retains all ten fields. Actual consumers use ID/type
classification and dedupe; display name/location/address; rating/review count and
sorting; current-opening-hours, regular hours and business-status evidence.
`app/page.tsx`, `components/map/geo-map.tsx` and adapter normalization prove usage.
Removing these fields would silently reduce existing evidence. No SKU reduction
is claimed.

## Metrics

`proptech_provider_cost_events_total{capability,event}` is appended to the existing
protected `/metrics` scrape. Both label domains are fixed. Counters distinguish
logical helper operations, actual physical dispatch, cache hits/misses, coalesced
waiters, avoided operations, operation outcomes and provider outcomes/timeouts.
Addresses, coordinates, user identifiers, cache keys, credentials and raw payloads
cannot become labels. Address-bearing provider recovery logs were removed.

For Google/terrain HTTP adapters, physical units are HTTP dispatches. Satellite's
physical unit is a successfully sent worker generation request, or an explicitly
injected adapter fetch in tests. Admission rejection, unavailable state and failed
worker sends add zero generation dispatches. SDK authentication/thumbnail/download
stages are not individually counted. `avoided_operations` counts reusable helper
operations, not inferred downstream calls: a coalesced whole Places request can
save several category calls, and a liquefaction hit saves three. Compare physical
counter deltas for the exact workload; do not sum nested logical counters as if
they were distinct user actions.

## Limitations and decisions

Reuse/coalescing is per warm process. It does not survive cold start, replacement,
scale-out, or coordinate Cloud Run instances. No Redis or persistent provider
cache was added. Existing routes remain non-live 600s observations; changing to
time-dependent departure queries would require a different key/freshness policy.
WRA/GSMMA keep validated immutable artifact indexes; TDX/RIS keep their local
snapshot/database behavior. No Anti-Abuse, ML, provider replacement or deployment
work was performed. Skill defaults for extra approval/intermediate commits were
superseded by the user's detailed implementation authorization and one-commit
instruction.

## Requested completion record

The following numbered record corresponds to the user's 65 requested items.
The final commit SHA and post-commit status are reported in the completion message;
this document is part of that same single commit.

1. Starting SHA: `a27bbdead6e3f4196426a6016a20ddff6f86f1f1`.
2. Branch: `perf/api-cost-optimization-v1`.
3. Baseline provider map: table above; mocked counts before product edits.
4. Geocoding: in-flight sharing, reused default adapter, request-local diagnostics; final safe resolver context reused 60s.
5. Places: exact keys, bounded category reuse, whole-fan-out sharing, unique categories, partial/freshness retained.
6. Places FieldMask: unchanged; all fields consumed; no SKU claim.
7. Places fan-out: duplicate categories 3 to 2; six unique categories still six; repeat adds zero.
8. Routes: bounded complete-key reuse and coalescing; accepted-coordinate bypass; weak custom provider identity.
9. Routes duplicates: concurrent identical physical POSTs 2 to 1; changed material query misses.
10. Satellite trigger: explicit localized action; not-run is separate from unavailable.
11. Satellite reuse: native async sharing and 300s successful embedded-image cache.
12. ARDSWC: bounded decoded-tile reuse; concurrent GET/decode 2 to 1; warm decode 2 to 1.
13. Liquefaction: complete-layer reuse; two identical queries 6 to 3 classification GETs.
14. NLSC: numeric observation reuse; repeated gateway POSTs 2 to 1; map/village identity separate.
15. WRA/GSMMA: existing validated versioned artifact/runtime indexes retained, regression tested.
16. TDX/RIS: snapshot/database consumers retained, operational refresh separate; TDX duplicate submit guarded.
17. Request keys: exact material inputs, locale/configuration/version/opaque provider identity; no credential objects.
18. Cache architecture: process-local shared TTL/LRU helper with synchronous/native async single-flight.
19. TTL/invalidation: cache table above; original observation times; lifecycle/credential/query version changes invalidate identity.
20. Bounds: cache table above; finite entries/flights; Satellite 4 MiB and ARDSWC 16 MiB retained accounting.
21. Eviction: deterministic expiry/LRU/byte overflow; oversized values not retained.
22. In-flight sharing: same key awaits one operation; unrelated keys run outside locks; failure cleanup.
23. Failure policy: no completed failure/partial/error/auth/timeout cache; explicit successful zero/no-route semantics preserved.
24. Retries: existing effective single-attempt HTTP/SDK contracts preserved; no additional retry layer.
25. Double submit: synchronous refs plus existing loading disable for explicit expensive actions.
26. Locale: local translations free; provider Places language included in key.
27. Property switch: backend complete keys and frontend request/context guards; late A cannot commit/display under B.
28. Reopen: reads saved evidence; zero automatic analysis/provider calls.
29. Compare: reads saved snapshots; zero automatic provider calls.
30. Report: frozen saved snapshot/explicit newer load/print; zero automatic provider calls.
31. Provider metrics: fixed-label counters on existing protected scrape.
32. Logical/physical metrics: separate events; nested operations and Satellite generation unit documented above.
33. Journey counts: two mocked external segments 23 to 17 operations; saved browser journey zero before/after.
34. Satellite counts: mount 1 to 0; identical pair 2 to 1; 64 concurrent plus repeat one observed generation.
35. Places counts: identical concurrent category 2 to 1; unique six-category fan-out preserved.
36. Routes counts: identical concurrent POSTs 2 to 1; accepted-coordinate forms zero geocoding.
37. Live provider requests: zero; synthetic mocks/local ASGI only.
38. Multi-instance: per process, not global across instances.
39. Cold start: no survival or saving guarantee across replacement/cold start.
40. Privacy: no credential/raw payload persistence, opaque/weak namespaces, fixed metric labels, private recovery log removed.
41. Files: 35 paths listed below, including implementation, regression tests and two operation documents.
42. Backend tests: complete serialized suite passed: 3,262 passed, 32 skipped, one existing Starlette/httpx deprecation warning, 254.13s. Optional environment-dependent checks, including PostgreSQL integrations, remain skipped.
43. Frontend tests: 187 library unit tests passed; 202 browser checks verified across Chromium and Chrome (196 passed in the combined run; six Chromium timeouts passed an isolated serial rerun without timeout changes).
44. Cache/coalescing tests: fake-clock expiry/eviction, independent keys, concurrent failures, copied results, byte limits, lifecycle epoch and async cancellation tested.
45. Chromium: all 101 selected checks verified; six contention-related timeouts passed isolated with original deadlines.
46. Chrome: all 101 selected checks passed in the combined run.
47. 390px: commercial mobile/Compare/Risk/Location/report print cases included in browser regression.
48. E3–E10: commercial suite and saved journey included in browser regression.
49. Provider Closure: affected broad Google/terrain/Market/Valuation/trust suites included.
50. Lint: passed, zero errors; 23 existing unused-variable warnings.
51. Typecheck: passed.
52. Build: optimized E2E build and ordinary `npm run build` both passed, including TypeScript and static page generation.
53. Production npm audit: passed, zero production vulnerabilities; existing repository dev-only audited exception unchanged.
54. Python/security audit: pip-audit strict requirements check passed with UTF-8 environment; repository hygiene passed.
55. Release-quality gate: contract checks passed using the workflow's `--skip-tests --skip-frontend-build` invocation; standalone full-suite and ordinary build evidence accompanies these checks.
56. Security/performance gate: contract/bundle/route checks passed; local API/SQLite/load smoke all passed with zero errors. Desktop and mobile browser rubric (three samples each) passed; five memory-smoke repetitions showed zero listener, sampled heap and speech-queue growth. This is the repository Playwright equivalent, not Lighthouse or a whole-process memory proof.
57. Production operations gate: passed all six checks.
58. Independent review: fresh read-only reviewer examined changed/new files and ran mocked suites; final narrow source/test review confirmed the weak Routes identity and physical Satellite dispatch fixes with no remaining Critical/Important issues.
59. Findings: five Important fixes (Routes/Places malformed poison, external Location stale response, weak custom Routes identity, Satellite admission-versus-dispatch metrics); zero Critical.
60. Commit: exactly one bounded commit, `perf: reduce provider api cost and duplicate requests`, after all local checks passed. Its SHA is the HEAD containing this report and is included in the completion message.
61. Git status: the post-commit `git status --short` result is checked and reported in the completion message; ignored local evidence stays outside the commit.
62. Diff check: passed; repository LF/CRLF conversion notices are advisory, no whitespace errors.
63. Nonblocking limitations: process-local/cold-start boundary, existing freshness/acceptance policy, retained-byte versus RSS accounting, variable real tile/SDK fan-out.
64. Push/PR readiness: suitable to push/open a PR for CI review; local regressions, audits and workflow equivalents passed. CI must still exercise its provisioned PostgreSQL integration job. No push performed here.
65. Anti-Abuse: may be a separate wave after merge/release review; none implemented in this wave.

## Changed files

Backend integration:

- `backend/api/routes_metrics.py`
- `backend/api_main.py`

Shared bookkeeping and provider services:

- `services/provider_cost_metrics.py`
- `services/provider_request_cache.py`
- `services/adapters/geocoding_adapter.py`
- `services/adapters/google_places_adapter.py`
- `services/adapters/nlsc_gateway_adapter.py`
- `services/adapters/routes_adapter.py`
- `services/commute_routing_service.py`
- `services/earth_engine_worker_pool.py`
- `services/location_resolver.py`
- `services/map_service.py`
- `services/satellite_reference.py`
- `services/terrain_risk_providers/ardswc_slope_hazard_provider.py`
- `services/terrain_risk_providers/geologycloud_provider.py`
- `services/terrain_risk_providers/nlsc_terrain_provider.py`

Frontend actions and context isolation:

- `frontend_next/components/commute-livability-card.tsx`
- `frontend_next/components/commute-route-card.tsx`
- `frontend_next/components/location-insight.tsx`
- `frontend_next/components/satellite-evidence.tsx`
- `frontend_next/components/terrain-risk-analysis.tsx`
- `frontend_next/components/workspace/risk/risk-environment-view.tsx`
- `frontend_next/lib/experience-i18n.ts`

Regression coverage:

- `tests/test_api_cost_journey.py`
- `tests/test_earth_engine_worker_pool.py`
- `tests/test_google_provider_cost_optimization.py`
- `tests/test_provider_request_cache.py`
- `tests/test_satellite_cost_optimization.py`
- `tests/test_terrain_provider_cost.py`
- `frontend_next/e2e/api-cost-journey.spec.ts`
- `frontend_next/e2e/commercial-location-commute.spec.ts`
- `frontend_next/e2e/commercial-risk-environment.spec.ts`
- `frontend_next/e2e/satellite-evidence.spec.ts`

Operation documentation:

- `docs/operations/api-cost-optimization-v1-plan.md`
- `docs/operations/api-cost-optimization-v1.md`

## Verification scope and reproducibility

The workflow equivalents run the complete Python suite and ordinary frontend
build separately, then invoke `release_quality_gate.py` with its workflow's
`--skip-tests --skip-frontend-build` flags. Those two `not_run` fields describe
that contract-only invocation, not the independent full-suite/build results.
Security/performance and production-operations scripts also passed independently.
No gate, timeout, assertion, dependency exception or deployment configuration was
relaxed. No PostgreSQL server was provisioned and no migration was applied;
database-backed integration checks require the CI PostgreSQL service.

Local evidence is kept in ignored `.tmp` artifacts: `journey-call-budget.json`,
`pytest-serialized.log`, `frontend-unit.log`, `frontend-lint.log`,
`frontend-build.log`, `browser-regression.log`, `browser-isolated.log`, `browser-isolated-final.log`,
`api-benchmark.json`, `database-benchmark.json`, `load-smoke.json`,
`browser-desktop.json`, `browser-mobile.json` and `memory-regression.json`.
The production npm audit found zero vulnerabilities. The repository's separate
development dependency audit gate retains its existing GHSA-vfj7-8cjw-p6xm
exception, expiring 2026-11-04; this change adds no dependency or exception.

The initial overlapping backend/browser run exposed resource-sensitive timing
checks: a spatial intersection exceeded 500ms and six Chromium checks reached
their original deadlines. Each passed unchanged in isolation. The complete
backend suite was subsequently rerun without browser/build concurrency. This
validation does not claim live provider reliability or production billing savings.
