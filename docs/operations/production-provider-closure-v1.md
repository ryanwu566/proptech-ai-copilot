# Production Provider Closure v1

Implementation date: 2026-10-08. Branch: `fix/production-provider-closure-v1`.
Starting HEAD and `origin/main`: `d06ed4f062a212fed4ce0adf092c2fdc515a3f62`.
All five starting checks passed, including a clean worktree and the last twelve
commits. This report describes local software closure and operator handoff.
It does not establish deployed production readiness.

## Capability scorecard

Classifications describe evidence available in this checkout. A missing local
configuration is not a claim that the deployed service lacks that configuration.
Production configuration, deployed SHA and real artifact evidence were not
inspected. No external provider capability is classified CLOSED on local tests.

| Capability | Classification | Local closure / remaining acceptance |
| --- | --- | --- |
| Finder | CONFIGURATION REQUIRED | Correct road/district quartiles and SQL failure semantics; BLUE database, demo off and deployed acceptance required |
| Valuation | CONFIGURATION REQUIRED | BLUE/GREEN rolling 36 months and actual capability provenance; configured selected database(s), demo off, current accepted data required |
| Trend | CONFIGURATION REQUIRED | SQL failure distinct from insufficient evidence; BLUE database and deployed acceptance required |
| Market | CONFIGURATION REQUIRED | Existing road → district → insufficient chain preserved; accepted BLUE read models/coverage and deployed acceptance required |
| PLVR update/import | CONFIGURATION REQUIRED | Runnable checksum-bound dry-run and atomic idempotent importer; protected import environment, approved release, role/schema and scheduler handoff required |
| Google Geocoding | CONFIGURATION REQUIRED | Real adapter acceptance, failures and TGOS recovery covered; backend credential and one accepted-address request required |
| Google Routes | CONFIGURATION REQUIRED | Real adapter offline acceptance and independent TDX failure covered; backend credential and one transit request required |
| Google Places / Location | CONFIGURATION REQUIRED | Partial categories preserved, failed counts null and successful zero distinct; backend credential and bounded category query required |
| Google Maps display | CONFIGURATION REQUIRED | Existing browser display/load uncertainty retained; browser key restrictions and deployed browser acceptance required |
| Google Street View | CONFIGURATION REQUIRED | Independent load/not-confirmed/no-panorama uncertainty retained; browser key and deployed browser acceptance required |
| Liquefaction / GeologyCloud | READY FOR PRODUCTION ACCEPTANCE | Accepted admin handoff and A → B isolation pass; official area/coverage and one bounded result remain unverified |
| ARDSWC landslide | READY FOR PRODUCTION ACCEPTANCE | Vintage 113 retained, polygon holes/topology, tile failures/bounds verified; official positive/negative comparison and deployed endpoint evidence required |
| ARDSWC debris-flow | READY FOR PRODUCTION ACCEPTANCE | Independent line proximity, vintage and partial tiles verified; official coverage and deployed endpoint evidence required |
| WRA flood | ARTIFACT ROLLOUT REQUIRED | Runtime scenario/schema/CRS/checksum/index/fixtures verified locally; reviewed actual vintage/artifact, R2 and deployed acceptance required |
| GSMMA sensitivity | ARTIFACT ROLLOUT REQUIRED | Exact immutable version, quarantine, checksum and finite WGS84 geometry verified; actual accepted artifact, R2 and deployed acceptance required |
| Active Fault | MANUAL VERIFICATION ONLY | Official source and competent-authority verification; GSMMA cannot substitute for this capability |
| TDX MRT | CONFIGURATION REQUIRED | Content version, SrcUpdateTime and advisory staleness added; credentialed snapshot refresh and instance/version evidence required |
| RIS demographics | CONFIGURATION REQUIRED | Missing/invalid counts remain no-data; statistical month freshness added; database, accepted boundary and deployed latest-month evidence required |
| NLSC WMTS display | DATA COVERAGE LIMITATION | Public visual layer is independent of numeric terrain and village identity; visual loading proves no numeric or property coverage |
| NLSC village identity | ARTIFACT ROLLOUT REQUIRED | Existing point identity/checksum/vintage contract verified; actual accepted boundary artifact and access configuration required |
| NLSC numeric terrain | CONFIGURATION REQUIRED | Fixed gateway endpoint/deadline/response contracts verified; separate gateway URL/token/deployment required |
| Satellite / GEE | CONFIGURATION REQUIRED | Optional flag/project, ADC/IAM failures, deadline and worker isolation verified; deployed credentials and optional bounded smoke required |
| Tax / legal / hazard legal conclusion | MANUAL VERIFICATION ONLY | Preserve official/professional verification, no automated legal guarantee |
| Hosted release acceptance | CONFIGURATION REQUIRED | Targets and exact frontend/backend SHA contracts fixed; real targets/expected SHAs and configured release run required |
| Passive health software | CLOSED | Per-capability configuration/recent evidence only; reads make no external calls or analysis-budget charges |
| ML readiness | BLOCKED | No ML work authorized; provider/data/deployment evidence remains incomplete |

Successful no-match is a DATA COVERAGE LIMITATION for WRA, GSMMA, ARDSWC and
liquefaction: it means no match in the tested source/scenario/loaded coverage.
It establishes neither safety nor full parcel/building coverage. Partial tile
coverage is also a limitation, even when a positive warning is preserved.

## Fixed software contracts

Finder's district-only quartile branch left road quartiles empty. Quartiles now
use the actual scoped valid price pool, with at least three finite samples.
Smaller pools carry null P25/P75 and `insufficient_sample`; the frontend suppresses
the range. SQL query metadata is reset per query. Exceptions return provider
failure and cannot become empty evidence. Trend applies the same failure rule;
its independent failure cannot invalidate the estimate.

At the current date the valuation window is 2023-11 through 2026-10 inclusive.
BLUE and frozen GREEN both enforce current month plus 35 preceding months,
excluding future and malformed periods. Eligibility is applied before SQL LIMIT
and rechecked in the service, so old/future/ineligible closer rows cannot starve
valid comparables. BLUE queries require official source and finite positive
valuation metrics before LIMIT. Sample/demo data remains a separate provider.
Valuation may use GREEN while Finder, Trend, Market and coverage still use BLUE.
Public allowlisted `source_details` and `data_status.capability_sources` identify
actual capability/backend; compatibility `source=postgres` remains unchanged.

Places retains cache, bounded concurrency, timeout and place-ID dedupe. Location
preserves source, category statuses, failed categories, check time and coverage.
Four successful categories out of six yield limited/partial evidence. Failed
counts/scores are null; valid zero stays zero. A partial aggregate score is null,
buyer fit is unavailable and demo POIs cannot become official Google evidence.
The existing neutral risk category is unchanged and unknown facility count is
null. Save/Reopen accepts nullable counts without restoring a fabricated zero.

Terrain no longer counts `limited` as fully available. All no-match, incomplete,
unknown and unavailable evidence cannot produce reassuring low overall risk.
Partial positive alerts remain visible with reduced confidence. Frontend saved
evidence preserves `coverage_status=partial`. Liquefaction's already-correct
accepted city/district handoff was regression-tested rather than redesigned.

ARDSWC retains the configured 113 layer vintage. Polygon/MultiPolygon topology
and holes are preserved; streams remain line proximity even when closed.
Each layer retains requested/successful/failed tile counts. Existing bounds are
36 tiles per layer, six workers, 1.5-second request timeout, 2.5-second query
budget and ten-minute tile cache, with no retries. Running requests can finish
after the cooperative budget within their individual timeout.

WRA retains rainfall scenario (default `24h-350mm`), exact processing contract,
vintage, checksum and coordinate-point intersection including boundaries.
Unknown legacy vintage is exposed as unknown and cannot pass operator artifact
acceptance. GSMMA reuses its accepted-artifact builder/runtime and rejects
checksum, schema, version, quarantine and CRS failures, including checksummed
projected coordinates mislabeled WGS84. Artifact acceptance uses actual index
loaders and at most three declared positive/negative/boundary fixtures.

Google Geocoding distinguishes missing configuration, rejected request, timeout,
valid empty result, malformed response and unaccepted match. Missing mandatory
response status/results or invalid numeric coordinates is malformed, not no-data.
Finite nonboolean coordinates must fall within WGS84 latitude/longitude bounds.
TGOS recovery retains its own
source and cannot mark Google enabled. Mock coordinates remain unaccepted.
Routes uses one adapter request, no synthetic production route and no TDX
dependency. Maps/Street View iframe loading proves neither API health nor full
panorama coverage and cannot invalidate other evidence.

TDX adds content SHA version and advisory stale status after 30 days based on
source update time. RIS uses latest statistical month, treats lag greater than
two months as stale, preserves boundary vintage separately, and never derives
property residents. Invalid/missing latest counts return no-data, valid zero
remains zero. Satellite remains secondary and independent, with its existing
eight-second timeout, two active/two queued workers and no request replay.

## PLVR operational handoff

The updater replaces a skeleton with: reviewed official release identity and
checksum → bounded safe ZIP/parse/normalization → complete-scope quality gate →
dry-run → explicit atomic import → acceptance ledger/audit. One corrupt/future
row cannot be silently accepted as a partial release. Future seasonal release
years/quarters fail closed. Duplicate release/scope/checksum preserves original
import time and adds no duplicate acceptance. Same identity with changed bytes
fails. Source release, newest transaction period and import time remain separate.

Dry-run is the default and never opens a database. Fixtures use temporary SQLite
or a separately guarded disposable loopback PostgreSQL database. Real PostgreSQL
17 verification proved rollback of a 201-row multi-chunk import when the final
ledger write fails, followed by recovery and duplicate handling. Its isolated
cluster was stopped. No application/production database was used.

Protected manual workflow requires explicit reviewed release/checksum/scope,
`PLVR_UPDATE_DATABASE_URL`, and exact
`PLVR_UPDATE_ENVIRONMENT=production-market-import`. Scheduled execution gives a
configuration-required notice, with no automatic acquisition/import. Selecting
and accepting an authoritative recurring release/checksum handoff remains
external work. Import and retention are separate auditable operations. Updating
BLUE transaction rows does not refresh GREEN, Market aggregates or coverage.

Use [PLVR operations](plvr-provider-update.md) for commands, role/schema grants,
limits, recovery, approved retention and freshness evidence. Do not interpret an
import timestamp as new transaction coverage or a prune exit code alone as
successful retention.

## Configuration, release and passive observation

`config/hosted-environment-manifest.json` contains names and validation rules,
never values. `services/provider_config_contract.py` returns only present,
missing or invalid-contract, with conditional GREEN and boundary/R2 prerequisites.
NLSC's actual token name is `NLSC_GATEWAY_CLIENT_TOKEN`; acceptance reuses its
runtime production URL/token validator. ADC/IAM, key restrictions,
schema grants, artifact existence and source coverage require separate evidence;
a syntactically valid variable is not acceptance.

Frontend `/release-version` exposes a build-bound exact 40-character SHA from
`RELEASE_COMMIT_SHA` or `VERCEL_GIT_COMMIT_SHA`; backend exposes exact SHA or
unconfigured. Hosted smoke uses explicit HTTPS origins, records both deployed
identities and compares configured expected SHAs. Unknown deployed identity
cannot pass. Missing targets exit 2 as configuration_required before requests;
the scheduled workflow records that state without falsely claiming an outage.
The existing smoke schedule is unchanged; no provider polling was added.

Protected `/provider-status` reuses `X-Metrics-Scrape-Token` and returns per-capability
configuration/recent observations, bounded source/reason/version, check time,
last success/failure and freshness. Google health is passive and source-specific.
Observations are process-local, retain only the last result until restart and
contain no property addresses or raw payloads. Current runtime hookups cover
Geocoding, Places, Routes, Valuation, Finder, Trend and terrain layers. Other
capabilities are honestly not_checked even if a result is available elsewhere;
this is not a durable cross-instance monitoring system. Valuation observation
uses its actual nested freshness. There is no universal all-available signal.

## Acceptance procedure and exact budget

Run from the repository root. Configuration and deterministic modes make zero
external provider calls and never load dotenv or expose credentials:

```powershell
python scripts/provider_acceptance.py --capability valuation --dry-run
python scripts/provider_acceptance.py --capability geocoding --mode offline-fixture
python scripts/provider_acceptance.py --capability routes --mode offline-fixture
python scripts/provider_acceptance.py --capability ardswc --mode offline-fixture
python scripts/provider_acceptance.py --capability hosted --mode config-only
python scripts/production_smoke.py --hosted
```

CLI JSON records capability, local checkout SHA, source, configuration states,
dataset version, freshness, test mode, result/reason, UTC check time and request
count. Local fixture success always carries `production_readiness=unproven`.
Before commit, checkout SHA identifies the base commit, not uncommitted code or
a deployed release. Bind the final commit and deployment identities to retained
operator evidence. Offline subprocess suites deny external socket connections;
numeric loopback is allowed for the local satellite fixture HTTP server only.

For real local WRA/GSMMA files use `--manifest`, `--artifact`, exact version/scenario
and `--fixtures-json` with at most three independently known fixtures. A hash/index
check with no fixtures does not constitute complete operational acceptance.
Use [risk rollout](risk-provider-rollout.md) for exact build/validate/accept →
immutable upload → configure exact version → deploy → one smoke → evidence,
and [secondary freshness](secondary-provider-freshness.md) for TDX/RIS/NLSC/GEE.

**Live requests during this implementation: exactly 0** (including agents).
Hosted network requests: 0. Production writes, deployments, uploads and secret
changes: 0. Mock transport calls, local browser/backend servers, dependency
downloads and disposable database queries are deterministic/tooling operations,
not live provider acceptance.

Future authorized acceptance uses exactly one representative property:
`台北市大安區敦化南路二段100號`; commute destination `台北車站`, transit mode.
Budget: at most one analysis invocation per core capability, zero retries after
failure, no property enumeration or stress test. Explicit Google CLI commands:

```powershell
python scripts/provider_acceptance.py --capability geocoding --mode bounded-live --allow-live --query 台北市大安區敦化南路二段100號
# Supply the accepted property coordinate and separately verified station coordinate:
python scripts/provider_acceptance.py --capability routes --mode bounded-live --allow-live --origin ACCEPTED_LAT ACCEPTED_LNG --destination STATION_LAT STATION_LNG
```

Each Google command makes at most one upstream GET/POST, no automatic TGOS
fallback or retry. Invalid/blank/nonfinite/out-of-range input returns request
count zero. Missing live contract makes no request. For Places, one analysis
invocation can make up to six category requests; ARDSWC up to 36 tiles per layer
(72 for two layers); artifact providers can read manifest/artifact once on cold
load. Record actual upstream requests separately; never label a fan-out analysis
as one network request. Do not run these fan-outs if the approved upstream budget
allows only one request. This branch executes no such live calls. Hosted release
smoke is separate and makes twelve bounded hosted requests (four frontend,
seven backend JSON and one CORS), with no analysis POSTs; record it separately.

## External blockers and rollback

Remaining production blockers: exact deployed frontend/backend identities;
approved credentials and key/IAM restrictions; accepted PLVR release/data/read
models/coverage and protected role/environment; actual accepted WRA/GSMMA/boundary
artifacts and immutable version configuration; NLSC numeric gateway deployment;
bounded official positive/negative acceptance and recorded actual request count.
TDX durable shared persistence/cross-instance rollout, RIS recurring refresh and
PLVR authoritative recurring scheduler handoff remain explicit operational/P2
work. Manual capabilities and geographic/source coverage cannot be coded away.

Roll back application code/API types together to the previous accepted release.
Keep previous accepted snapshots and artifacts; switch to the previous exact
GSMMA version and restart rather than overwriting immutable bytes. WRA's existing
v1 prefix must never be overwritten with different bytes. Stop on artifact
validation failure; do not edit a quality flag/checksum to admit damaged data.
PLVR failed transactions roll back atomically; inspect ledger read-only before
retrying an uncertain disconnect. A successfully imported bad release requires
approved backup/restore or reviewed corrective import, not blanket deletion.
Retention deletion has separate recovery/approval evidence. Do not roll back by
turning missing data into zero or no-match into safety.

## Verification and fresh review

Final full backend regression: **3,114 passed, 32 skipped**, one existing Starlette
deprecation warning, in 203.22 seconds. All 32 skips require explicitly configured
disposable PostgreSQL fixtures (Market, historical PLVR cutover/migration, RIS,
VNext migration/RLS and the new updater). The new updater's guarded PostgreSQL
rollback/recovery/duplicate test was additionally executed and passed separately.
The remaining skipped integration suites were not exercised; no production DB
credentials were substituted to turn them green.
The first full run had 3,080 passing tests and 32 skips; its only failure was an
outdated exact-public-variable assertion after adding the nonsecret release SHA.
The corrected assertion and Google fixture envelopes pass their focused suites.
The optional real PostgreSQL rollback test was also explicitly executed and passed.

Frontend unit regression: 163 passing checks across provider visualization,
commercial design foundations and affected workspace/E3–E10 evidence/state suites.
Browser regression: 160 existing commercial tests pass in Chromium and installed
Chrome. The new 390px partial Location test initially asserted the wrong existing
localized label and fixture duration; corrected to `未提供` and 24 minutes, then
both browser projects pass. Reload preserves null failed counts, successful zero
and independent route evidence, without automatic provider POSTs. Existing E10
navigation, A → B stale protection, Save/Reopen, Compare and Report remain covered.

Lint: exit 0, zero errors and 24 existing warnings. Typecheck, standard production
build, Python compile, full Python regression and final repository gates pass.
No dependencies were added. Python
dependency audit reports no known vulnerabilities. Production npm audit reports
zero vulnerabilities. Existing dev-only GHSA-vfj7-8cjw-p6xm exception remains
time-bounded through 2026-11-04; it was not broadened. Release-quality static,
security/performance, production-operations and bundle/route-budget gates pass;
full tests/build are run separately, so static gate skip flags do not claim those
checks ran within that process. CI contracts were not weakened.

Independent fresh review reproduced and fixed: malformed Google result promoted
to no-data; invalid Google provider coordinates accepted; TGOS marking Google
available; invalid live inputs reporting a request;
GSMMA projected-coordinate admission; ARDSWC polygon holes; BLUE ineligible rows
starving official evidence before LIMIT. Earlier domain review also fixed Trend
future-row starvation and PLVR corrupt-row partial acceptance. Minor future
seasonal provenance and nested freshness omissions were fixed. No Critical finding
was identified. Runtime observation coverage remains an explicitly documented
limitation. Final reviewer confirmation found no remaining Critical/Important
findings and independently ran 76 focused tests successfully. The final staged
whitespace check passes. The change contains 74 files; the inventory follows.

| Final verification | Command / result |
| --- | --- |
| Python | `python -m pytest -q -rs --basetemp .local/pytest-provider-closure-final-all`: 3,114 pass / 32 guarded skips |
| Python syntax | `python -m compileall -q backend services scripts`: pass |
| Frontend unit checks | Provider/design checks 15 pass; affected workspace/evidence checks 148 pass |
| Browser | 160 existing tests pass, then corrected new partial Location test 2 pass; Chromium and installed Chrome, no retries |
| Lint/type/build | `npm run lint`, `npm run typecheck`, `npm run build`: pass; lint has 24 warnings |
| Production npm audit | `npm audit --omit=dev --audit-level=high`: zero vulnerabilities |
| Python audit | `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, `python -m pip_audit`: no known vulnerabilities |
| Dev exception gate | `scripts/npm_audit_gate.py`: existing dev-only timed exception accepted, unchanged |
| Release-quality | `scripts/release_quality_gate.py --skip-tests --skip-frontend-build`: static contracts pass; tests/build independently pass above |
| Security/performance | `scripts/security_performance_release_gate.py --json`: pass |
| Production operations | `scripts/production_ops_gate.py`: pass |
| Budgets/hygiene | Bundle, route and repository hygiene scripts pass; total static bytes 2,982,151, largest client chunk 606,888 |
| Offline acceptance | Google Geocoding/Routes, WRA/GSMMA synthetic artifacts, ARDSWC and satellite modes pass with zero external requests |
| Hosted missing targets | configuration_required, zero requests; intentionally not a production pass |
| Whitespace | `git diff --check` and `git diff --cached --check`: pass |

## Requested final-report mapping

| Item | Evidence / outcome |
| --- | --- |
| 1. Starting SHA | `d06ed4f062a212fed4ce0adf092c2fdc515a3f62`, clean start, equal origin/main |
| 2. Branch | `fix/production-provider-closure-v1` |
| 3. Finder quartiles | Removed district-only branch; actual scoped finite pool, minimum three samples |
| 4. Finder SQL | Reset query metadata; provider error cannot become no-data |
| 5. Trend SQL | Failure distinct from insufficient evidence; estimate remains independent |
| 6. Valuation window | Current rolling 36 months enforced in BLUE/GREEN SQL before LIMIT and service |
| 7. Provenance | Actual capability backend/source; GREEN valuation does not imply GREEN Market/Finder/Trend |
| 8. Places partial | Successful categories/zero preserved; failed counts null; aggregate partial, demo isolated |
| 9. Terrain | Limited/no-match/unknown/unavailable cannot imply low risk; partial positives preserved |
| 10. Liquefaction | Accepted admin handoff/A → B regressions pass; no unnecessary rewrite |
| 11. PLVR updater | Reviewed release/checksum, dry-run, atomic idempotent import, ledger and recovery |
| 12. Retention/freshness | Separate auditable prune; transaction period, release and import time independent |
| 13. Market | Existing road/district/insufficient scope/sample/fallback contract preserved |
| 14. Geocoding | Rejection/timeout/no-match/malformed/unaccepted/success and TGOS source distinctions |
| 15. Routes | One request, explicit endpoints/transit; Google result survives TDX failure |
| 16. Maps/Street View | Load uncertainty/no-panorama preserved; no iframe-based provider-health claim |
| 17. TDX | Content version/SrcUpdateTime/30-day advisory staleness; persistence remains P2 |
| 18. RIS | Latest statistical month/2-month advisory staleness; missing != zero, boundary independent |
| 19. NLSC | WMTS, village artifact and numeric gateway are separate; configuration uses runtime contract |
| 20. ARDSWC | Vintage 113, topology/holes, line proximity and bounded partial tiles |
| 21. WRA | Scenario/vintage/checksum/index/point contract; actual accepted artifact rollout required |
| 22. GSMMA | Exact version, accepted quality/quarantine/CRS/geometry/checksum; actual artifact rollout required |
| 23. Active Fault | MANUAL VERIFICATION ONLY |
| 24. Satellite | Existing optional flag/project/ADC/IAM/deadline/worker isolation verified |
| 25. Config manifest | Names and rules only; no credential values |
| 26. Release identity | Exact build-bound frontend SHA and backend SHA; unknown cannot pass hosted acceptance |
| 27. Hosted smoke | Explicit targets; missing config distinguished before requests; expected SHA validation |
| 28. Observability | Protected passive per-capability process-local last results; hookup limits disclosed |
| 29. Failure isolation | Domain fixtures preserve unrelated providers; no universal availability signal |
| 30. Property switch | Existing A → B stale mechanisms pass backend/frontend/browser regressions |
| 31. Live requests | Exactly 0 external provider requests, including agents |
| 32. Scorecard | Every capability classified above with evidence and remaining requirements |
| 33. CLOSED | Passive health software contract; no external provider declared production CLOSED |
| 34. READY | Liquefaction and both ARDSWC layers, subject to deployed/official acceptance |
| 35. CONFIG REQUIRED | Finder/Valuation/Trend/Market/PLVR, Google capabilities, TDX/RIS, numeric NLSC, GEE and hosted acceptance |
| 36. ARTIFACT REQUIRED | WRA, GSMMA and NLSC village boundary; real accepted bytes not rolled out |
| 37. MANUAL ONLY | Active Fault and tax/legal conclusions |
| 38. Blockers | Deployed SHA, approved config/data/artifacts/gateway/acceptance; scheduling/persistence P2; ML BLOCKED |
| 39. Changed files | Provider/services/adapters, narrow API routes, two workflows, config, acceptance/update/build/smoke scripts, frontend null/partial/provenance/release types, tests and four operations docs. Exact inventory: `git show --name-only --format= HEAD` after the one commit |
| 40. Backend tests | Full final result below; explicit PostgreSQL rollback/recovery test also passed |
| 41. Frontend tests | 163 affected provider/design/workspace unit checks pass |
| 42. Chromium | 80 existing commercial checks plus one corrected new provider closure check pass |
| 43. Installed Chrome | 80 existing commercial checks plus one corrected new provider closure check pass |
| 44. 390px | Partial Location/reload/route/null-versus-zero and touched commercial mobile paths pass |
| 45. E3–E10 | Navigation, Market, Location, Risk, Finance, Overview/Save, Compare/Report and UI UX covered |
| 46. Lint | Exit 0, zero errors, 24 existing warnings |
| 47. Typecheck | `npm run typecheck` passes |
| 48. Build | `npm run build` passes, including `/release-version`; E2E build also passed |
| 49. Dependency audit | Production npm zero vulnerabilities; Python no known vulnerabilities; dev exception unchanged |
| 50. Release-quality | Static gate pass, full tests/build run separately; no CI weakening |
| 51. Security/performance | Gate pass; final bundle/route budgets pass |
| 52. Production operations | Gate pass; hosted acceptance remains configuration-required |
| 53. Independent review | Fresh read-only review of complete implementation and scorecard |
| 54. Findings | Reproduced and fixed all known Important issues listed above; no Critical identified |
| 55. Runbooks | This report plus PLVR, risk rollout and secondary freshness instructions |
| 56. Commit | Exactly one authorized commit after local criteria pass; final response records SHA because a commit cannot contain its own hash |
| 57. Git status | Final response records post-commit `git status --short` |
| 58. Whitespace | `git diff --check` passes; final staged/post-commit verification required |
| 59. Push/PR | Safe for push/open-PR review after final local gates pass; no push/PR/merge/deploy executed |
| 60. Next work | API Cost Optimization may begin as a separate task after merge; external provider acceptance remains required, ML stays BLOCKED |

## Changed-file inventory

```text
.github/workflows/hosted-production-smoke.yml
.github/workflows/import-official-market-data.yml
backend/api/routes_commute.py
backend/api/routes_map.py
backend/api/routes_metrics.py
backend/api/routes_pilot.py
backend/api/routes_terrain_risk.py
backend/api/routes_valuation.py
config/hosted-environment-manifest.json
docs/operations/plvr-provider-update.md
docs/operations/production-provider-closure-v1.md
docs/operations/risk-provider-rollout.md
docs/operations/secondary-provider-freshness.md
docs/superpowers/plans/2026-10-08-production-provider-closure.md
frontend_next/app/release-version/route.ts
frontend_next/components/location-insight.tsx
frontend_next/e2e/provider-closure.spec.ts
frontend_next/lib/api.ts
frontend_next/lib/property-search-visualization.ts
frontend_next/lib/risk-summary.ts
frontend_next/lib/terrain-reference-evidence.ts
frontend_next/lib/workspace/risk-evidence-model.test.ts
frontend_next/lib/workspace/risk-evidence-model.ts
frontend_next/lib/workspace/saved-case-diagnostics.test.ts
frontend_next/lib/workspace/saved-case-diagnostics.ts
frontend_next/next.config.mjs
frontend_next/scripts/provider-closure-contract.test.mjs
scripts/build_wra_flood_artifact.py
scripts/production_smoke.py
scripts/provider_acceptance.py
scripts/update_valuation_data.py
services/adapters/geocoding_adapter.py
services/commute_routing_service.py
services/commute_service.py
services/compact_green_query.py
services/gsmma_geological_sensitivity_artifact.py
services/location_insight_service.py
services/map_service.py
services/plvr_provider_update.py
services/property_search_service.py
services/provider_artifact_acceptance.py
services/provider_config_contract.py
services/provider_observability.py
services/ris_demographics_insight.py
services/tdx_mrt_snapshot.py
services/terrain_risk_providers/ardswc_slope_hazard_provider.py
services/terrain_risk_providers/wra_flood_provider.py
services/terrain_risk_service.py
services/valuation_providers/postgres_provider.py
services/valuation_result_contract.py
services/valuation_service.py
services/valuation_trend_service.py
services/wra_flood_artifact.py
services/wra_flood_runtime.py
tests/test_compact_green_query.py
tests/test_frontend_vnext_property_identity.py
tests/test_hosted_production_launch.py
tests/test_map_api.py
tests/test_map_service.py
tests/test_plvr_provider_update.py
tests/test_property_search_service.py
tests/test_provider_acceptance.py
tests/test_provider_artifact_acceptance.py
tests/test_provider_closure_location.py
tests/test_provider_closure_market_valuation.py
tests/test_provider_closure_smoke.py
tests/test_provider_observability.py
tests/test_risk_provider_closure.py
tests/test_secondary_provider_freshness.py
tests/test_terrain_risk_providers.py
tests/test_terrain_risk_service.py
tests/test_valuation_api.py
tests/test_wra_flood_artifact.py
tests/test_wra_flood_runtime.py
```
