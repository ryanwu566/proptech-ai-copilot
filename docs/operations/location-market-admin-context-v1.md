# Location to Market administrative context incident

Investigation date: 2026-10-23 (Asia/Taipei). Repository work only; no deployment, traffic change, credential change, or PR merge.

## Root cause and exact loss boundary

The production frontend and backend are on different generations of the location contract. The frontend reports commit `3ab03f9b2d8d4e9e947b5a5c57c6fc9cc8b8bd77`. Its downloaded JavaScript points to `https://proptech-earth-engine-api-712372598609.asia-east1.run.app`.

That backend's live `GET /openapi.json` exposes only these `LocationResolveResponse` fields:

`status`, `source`, `formatted_address`, `latitude`, `longitude`, `confidence`, `message`.

It does **not** expose `county` or `district`. The service's alternate URL returns the same schema. Read-only Cloud Run inspection shows 100% traffic on `proptech-earth-engine-api-00021-saf`, with image tag `01207cfa1b2aa6a6582c0051753bab7c6fb618cb` and image digest `sha256:66b31bfa6e400fb1935cea9c3a7b6f5119e6175e81068e2c95af60e3cd31848e`. The backend's release SHA is `unconfigured`, so the image tag alone is not asserted as embedded build provenance.

Git inspection at that tagged source revision independently shows:

- `LocationResolveResult` and `to_safe_dict()` have no county/district fields.
- The Google resolver does not extract administrative components into the result contract.
- `LocationResolveResponse` has no county/district fields either. Its response model also drops fields outside that schema.

The first missing-data boundary is the deployed backend provider-result projection; its API schema/serialization also cannot carry the fields. The frontend correctly treats absent optional fields as null and saves an incomplete anchor. This is **confirmed backend/frontend release skew**, not a missing current-source frontend mapping. No raw incident provider payload was captured, so no claim is made about the exact component types returned during the two original production requests.

## Contract map, recorded before implementation

`POST /location/resolve` → `services/location_resolver.py` → Google provider → `_google_administrative_area` → structural acceptance in `_resolved` → `LocationResolveResult.to_safe_dict` → FastAPI `LocationResolveResponse` → frontend `LocationResolveResult` → `api.locationResolve` → `acquireLocationResolution` → `interpretLocationResolution` → `LocationCandidate` → `buildConfirmedLocationAnchor` → `JourneyPropertyIdentityAnchorV1.administrative_location` → saved-case normalization → `hasCompleteAdministrativeArea` / `buildMarketRefreshContext` → Market refresh button.

Current source at the requested baseline already preserves county→city and district through every boundary. Both incident-address fixtures pass before changing that path. No backend resolver change, second parser, coordinate inference, reverse geocoding, or formatted-address fallback was added.

## Google component audit

Current extraction uses `administrative_area_level_1` for county/city, and a district-suffixed `administrative_area_level_2` or `administrative_area_level_3` for district. `台` is normalized to `臺`; village names ending in `里` are excluded. Structured fields must agree with the same response's formatted address and the supplied address. ROOFTOP/non-partial acceptance and strict TGOS fallback remain unchanged.

Google documents that component presence and types can change; no particular component is guaranteed. See [Google Geocoding response documentation](https://developers.google.com/maps/documentation/geocoding/guides-v3/requests-geocoding). Locality/sublocality fields are not newly promoted without incident evidence. Missing administrative data remains missing.

`tests/fixtures/location_market_google.json` contains **representative deterministic Google-shaped fixtures**, not captured live Google responses. They include street number, route, village, district, city, country, postal code, precision and coordinates for:

- 臺北市信義區市府路1號
- 臺北市中正區中山南路21號

Python runs these through the real Google provider and actual HTTP API with only outbound HTTP replaced. It asserts the entire serialized response equals the shared response fixture used by frontend unit and browser tests. Each address is checked with level-2 and level-3 district variants.

The original 新北市新莊區中正路191號 → 新北市樹林區中正路191號 incident remains rejected by existing provider/API/frontend regressions. No structural acceptance rule was loosened.

## Saved-case recovery

Market's incomplete-area notice links to Location. Location offers **Recheck administrative area** in zh-TW/en/ja/ko.

1. Clicking Recheck performs one bounded `/location/resolve` request.
2. The returned city/district is displayed for review, without writing the case.
3. A separate Confirm saves administrative context under the existing Web Lock and exact-case-version check.

The original anchor ID, input/normalized address, coordinates, parcel/building status, confidence level and underlying evidence are preserved. The repair adds administrative context and records its geocoding/manual-confirmation provenance. The existing checklist fingerprint mechanism marks previous checklist completion for recheck after an anchor changes; it does not erase the underlying evidence.

Repair fails closed for missing fields, cross-district disagreement, a changed normalized address, coordinate drift over the existing 0.000001-degree identity tolerance, conflicting partial administrative fields, low-confidence/stale identity, changed saved-case version, unavailable locks/storage, or write failure. Even tolerated coordinate rounding never replaces the saved coordinates. Legacy normalized addresses without both city and district prefixes cannot be repaired by this narrowly scoped flow; they need a separate explicit identity revalidation.

Recheck results are transient. Reload, cancellation or leaving Location discards them without another request. A queued confirmation also checks the panel's active lifecycle **inside the storage lock**, so leaving Location prevents a late save.

The existing spatial-only confirmation behavior remains compatible with older backend responses: coordinates may still be confirmed, city/district remain null, and Market remains blocked. Until the backend release is corrected, repair against the old backend safely fails and preserves the case.

## Market result and provider cost

With a complete current response, explicit Home Start → candidate → explicit Confirm saves `臺北市/信義區` or `臺北市/中正區`; Market refresh is enabled and remains enabled after reload/reopen.

Price estimation has an independent input contract: road, building type, area, age and floor are required. Address-only Home drafts deliberately lack those facts. Their estimation button therefore remains disabled; supplying explicit saved building facts enables both buttons. No facts or zero-valued assumptions are fabricated to satisfy an administrative-area fix.

Browser request ledgers assert exactly one resolve for an explicit Home Start and no additional provider acquisition when opening Overview, Market, Location, Report or Compare, or after reload/reopen. Repair adds requests only on explicit Recheck clicks; confirmation itself makes none. Basemap tile requests are excluded from acquisition counts and stubbed locally.

Live investigation used only frontend release/static JavaScript, backend release/OpenAPI and read-only Cloud Run metadata. **Live Google/TGOS calls: 0.** No customer saved cases were read or changed.

## Validation and integration

The branch integrated `origin/main` at `c377ee94955429ab3d4804ffd8d8a6fae8c99a52` using `git merge --autostash origin/main` (fast-forward; no rebase). Its demo-case feature is preserved.

| Check | Result |
| --- | --- |
| Initial resolver/API/accuracy baseline | 64 passed before implementation |
| Focused Python resolver/API/accuracy/deadline/admin/budget contracts | 133 passed; the shared admin contract file subsequently expanded from 4 to 6 passing cases |
| Final shared Google/API incident contracts | 6 passed |
| Final frontend/workspace/Report/Market/Decision Room/Command Palette/demo unit tests | 163 passed |
| Final storage roundtrip and concurrency tests | 60 passed |
| Full Python suite | 4,216 passed, 151 skipped, 1 timing failure in 639.92 s; details below |
| Bundled Chromium | 30 distinct targeted tests passing, workers=1, retries=0 |
| Four locales/mobile | zh-TW, en, ja, ko; 390 and 430; both addresses, repair candidate focus, touch targets and overflow checked |
| Typecheck | `npm run typecheck` passed |
| Lint | `npm run lint` passed: 0 errors, 23 existing warnings |
| Build | `npm run build:e2e` passed on integrated main; optimized production compiler, Next.js 16.4.2, test API origin |
| Global bundle budget | Passed: 4,058,099 / 8,000,000 static bytes; largest JS 600,971 / 900,000 bytes |
| Route budgets | All 24 routes passed with browser attribution and unchanged ceilings |
| Home route | 1,950,257 / 2,066,966 bytes |
| Location route | 1,151,068 / 1,551,855 bytes |
| Market route | 1,115,439 / 1,301,212 bytes |
| Repository hygiene / diff whitespace | Passed |

The full-suite failure was `tests/test_earth_engine_worker_pool.py::test_timeout_kills_worker_before_one_bounded_replacement` (`starts[0]` was 1 instead of 2). It reproduced during concurrent browser/measurement load, then **passed in isolation after that load ended** (1 passed in 4.65 s). The worker-pool implementation and its test are unchanged from `origin/main` (`git diff --quiet origin/main -- services/earth_engine_worker_pool.py tests/test_earth_engine_worker_pool.py` returned 0). This is a documented timing-sensitive validation result, not a claim that the original full run was entirely green. The two extra exact-incident cases were added after full-suite collection; the subsequent six-case contract run includes them.

The integrated browser run passed 29 checks. Its final cross-tab test initially lost its test-only lock-release function on document navigation. Moving the lock owner to a separate synthetic same-origin tab corrected the harness; that check then passed separately. No product change was needed for that harness correction. The earlier 18-check browser pass is not added again to the final distinct count of 30.

The one-shot route collector exceeded its existing 210 s local deadline on this machine. All 24 routes were then measured in three bounded batches using the **unchanged collector**, two cold samples at each of 390/1440, the same populated fixtures and provider-blocking policy. Every batch and the merged evidence used the same verified build fingerprint, with duplicate Home measurements required to agree. The normal `check_route_budgets.py` gate accepted the complete evidence. No route ceiling, sample count, viewport or collector timeout was relaxed.

Independent code review identified and verified fixes for queued saves after navigation and ambiguous legacy administrative prefixes. Both fixes have observed failing-then-passing tests.

Repository changes are ready for review/merge with the full-suite timing caveat above. Production recovery still requires a separately authorized backend release; live-provider acceptance has not been claimed.

## Files changed

| File | Responsibility |
| --- | --- |
| `frontend_next/lib/workspace/administrative-area-repair.ts` | Pure administrative-only repair policy |
| `frontend_next/lib/case-storage.ts` | Locked, version-bound and cancellation-guarded repair save |
| `frontend_next/components/workspace/location/administrative-area-repair-panel.tsx` | Explicit Recheck and Confirm interaction |
| `frontend_next/components/workspace/location/location-view.tsx` | Show repair only for a confirmed incomplete anchor |
| `frontend_next/components/workspace/market/market-price-view.tsx` | Link incomplete-area notice to Location |
| `frontend_next/lib/workspace/location-confirmation.ts` | Export existing bounded prefix check for reuse; parsing unchanged |
| `frontend_next/lib/workspace/location-confirmation-copy.ts` | Four-locale repair copy |
| `tests/fixtures/location_market_google.json` | Shared Google-shaped and expected serialized response fixtures |
| `tests/test_location_market_admin_contract.py` | Actual provider/API contracts and exact incident rejection |
| `frontend_next/lib/workspace/administrative-area-repair.test.ts` | Acquisition-to-Market contract and repair safety tests |
| `frontend_next/scripts/case-storage-roundtrip.test.cjs` | Repair persistence, write failure, cancellation, and preserved evidence |
| `frontend_next/e2e/location-market-admin.spec.ts` | Two-address/mobile/locale journeys and request ledgers |
| `docs/superpowers/plans/2026-10-23-location-market-admin-context.md` | Contract map, constraints, decisions and execution ledger |
| `docs/operations/location-market-admin-context-v1.md` | Root cause, release evidence, acceptance and recovery guidance |

## Production follow-up (not executed)

An authorized owner must release the current backend contract and verify the deployed response schema carries county/district before live acceptance can be claimed. After that, use one explicit Start/Confirm for a new case or Recheck/Confirm for an affected existing case. Do not run repair on page load and do not bulk-modify stored anchors. This PR does not deploy or merge anything.
