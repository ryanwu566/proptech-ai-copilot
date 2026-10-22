# Property address accuracy implementation plan

> Execution: inline in the user-designated isolated worktree. User explicitly requires implementation, one local commit, focused validation, no push/deploy.

**Goal:** Reject contradictory geocodes and bound the location confirmation wait.

**Architecture:** Google primary with a ROOFTOP/non-partial/structural acceptance gate; at most one strict TGOS fallback. Only validated candidates enter the versioned cache. A shared client deadline aborts the request and settles independently of transport cancellation.

**Tech stack:** Python/httpx/FastAPI; TypeScript/React/Next.js; pytest, Node tests and Playwright bundled Chromium.

**Spec:** User's P0 production location accuracy implementation brief, including the 新北市新莊區中正路191號 → 樹林區 incident.

## Constraints

- Normal: one Google request, zero TGOS requests. Fallback: at most one each, no automatic retry.
- No paid enrichment, production configuration, deployment or push.
- Preserve explicit user confirmation before creating the property identity anchor.
- Approximately 10 seconds maximum client wait, preserving the saved case and address.
- Mock all location providers; focused browser files only, headless bundled Chromium, workers=1, retries=0; one heavy job at a time.

## Review focus

- Structured response fields contradict a matching formatted address.
- Postal prefixes accidentally consume house numbers.
- Section/lane/alley/sub-number mismatches survive normalization.
- Timeout followed by late success or explicit retry changes saved identity.
- Cache reuse or read-only navigation bypasses acceptance/provider-call bounds.

## Tasks

- [x] Reproduce with controlled HTTP regressions; observe failures before implementation.
- [x] Implement bounded structural comparison and provider acceptance gates; make backend regressions pass.
- [x] Add failing client deadline/admin contradiction tests; implement shared abortable deadline; make units pass.
- [x] Verify targeted API, unit, browser and typecheck contracts.
- [x] Independently review the complete diff and resolve acceptance findings.
- [x] Complete focused lint, document evidence and prepare one local commit.

## Evidence ledger

- Baseline: 13 location resolver/API tests passed.
- Accuracy RED: 32 failed, 6 passed; original fuzzy-first/high-confidence behavior reproduced.
- Client RED: 3 failed (deadline signal absent; contradictory district accepted).
- Initial GREEN: 51 backend/API tests and 17 confirmation/handoff units passed.
- Existing unsafe fixtures updated to supply a matching address and ROOFTOP precision. Missing/malformed address now correctly expects unresolved; missing administrative metadata stays unknown when formatted structure agrees.
- Independent review identified village-prefix road truncation and a TGOS ROAD field containing a contradictory house number. Both were reproduced with failing regressions before correction; follow-up review found both addressed.
- Additional failing regressions caught malformed `191-號` / `191之號` being reduced to `191號`; numeric suffix groups now require a sub-number.
- Final backend run: 67 passed, one existing FastAPI/Starlette httpx deprecation warning. This includes 49 new controlled accuracy cases, 10 existing resolver tests, 5 API tests and 3 targeted resolver/cost/cache integration tests.
- `npm run test:home-start`: 49 passed, including 18 confirmation/handoff units.
- `npm run build:e2e`: passed. `npm run typecheck`: passed.
- Targeted browser command below: 47 passed in 3.5 minutes, headless bundled Chromium, one worker, zero retries. No concurrent heavy build/browser process.
- Focused ESLint passed with `--no-ignore --max-warnings=0`, including the two normally ignored e2e files: zero errors/warnings. `git diff --check` passed.

## Implementation report

### Root cause and order

Previously TGOS ran first with fuzzy matching enabled; any globally valid coordinates were promoted by `_resolved()` to `high`. Google precision metadata and address structure were not checked. A wrong TGOS candidate prevented Google from running.

Now Google Geocoding runs first. A strong accepted candidate ends resolution immediately. Otherwise at most one strict TGOS request is attempted. Only a validated result can leave the resolver as a high-confidence candidate. Both failures return `unresolved` when a provider could search but found no accepted match; absent/unavailable providers return `unavailable`.

### Acceptance and structural rules

Google requires status `OK`, finite Taiwan-bounded coordinates (latitude 21.7–26.5, longitude 118–122.2), `ROOFTOP`, no true/invalid partial-match flag, a parseable matching formatted address and no contradictory structured address components. Missing precision, `APPROXIMATE`, `GEOMETRIC_CENTER`, `RANGE_INTERPOLATED`, partial matches and structural mismatches proceed to strict fallback.

The comparator bounds text at 500 characters. It normalizes 台/臺, whitespace/common address punctuation, leading postal/country prefixes, full-width digits and numeric segment/sub-number representations. It compares every supplied county/city, district/township, road/street, section, lane, alley and house number independently. Unprovided components are not required. A postal prefix cannot consume a house number. Unknown structural residue fails closed; floor/unit suffixes remain outside geocoding identity.

Ambiguous village/road prefixes are preserved: `仁里五街` is not `五街`. A provider-added village prefix without a neighborhood delimiter may be rejected rather than guessed away. This deliberately favors accuracy over lookup availability for ambiguous address forms. Matching formatted structure without administrative metadata remains a spatial candidate with unknown administrative fields, preserving the existing contract.

The incident `新北市新莊區中正路191號` versus `238台灣新北市樹林區金寮里中正路191號` is rejected, never high, and never cached. The matching Google ROOFTOP response is accepted with zero TGOS calls. The control `臺北市信義區市府路1號` remains covered using existing coordinate fixtures.

### TGOS request semantics

| Parameter | Before | After |
| --- | --- | --- |
| `oIsOnlyFullMatch` | `false`: fuzzy results permitted | `true`: fuzzy mechanism disabled |
| `oFuzzyType` | `0`: nearest house number | `0`, inert under full-match-only |
| `oFuzzyBuffer` | `0`: unlimited numeric error | `0`, inert under full-match-only |
| `oReturnMaxCount` | `1` | `1` |
| Endpoint / SRS / format | QueryAddr v30 / EPSG:4326 / JSON | unchanged |

TGOS also requires compatible formatted structure, Taiwan coordinates, and compatible structured COUNTY/TOWN/ROAD/SECTION/LANE/ALLEY/NUMBER fields. If response `Info.OutMatchType` is present, it must be `完全比對`. Every structural component embedded in a field is checked, including a house number embedded in ROAD. Bare numeric fields use their explicit field suffix. No nearby/fuzzy rescue or automatic retry exists.

Official semantics: [TGOS QueryAddr v30](https://addr.tgos.tw/addrws/v30/QueryAddr.asmx?op=QueryAddr), [Google Geocoding precision and partial matches](https://developers.google.com/maps/documentation/geocoding/guides-v3/requests-geocoding).

### Calls, cache and confirmation

- Normal uncached lookup: one Google Geocoding call, zero TGOS calls.
- Fallback: at most one Google and one TGOS call; unconfigured providers are skipped. Accepted cache reuse can use zero calls.
- No Places/Routes/Market/Risk enrichment was added to location resolution; tests use controlled providers.
- Resolver/cache version changed from `trusted-address-resolution-v1` to `trusted-address-google-primary-strict-v2`; Google single-flight keys use the same version. Accepted-resolution TTL remains 60 seconds and capacity 64 entries, isolated by provider configuration/namespace and strict request semantics. Only proven accepted responses are retained; raw precision payloads/internal proof stay private.
- Resolution returns a candidate only. Explicit user confirmation still creates the identity anchor; parcel/building/legal semantics are unchanged.

### Timeout behavior

The shared acquisition function schedules a 10,000 ms deadline and races it against the full request/body read. At timeout it aborts transport and returns the existing friendly unavailable/retry state, even if transport ignores cancellation. Late success cannot replace that settled state. Both Home handoff and explicit in-case retry use this function; navigating away from an in-case lookup propagates cancellation. Timers/listeners are cleared. No automatic retry occurs, and saved case/address/identity are untouched. Existing 429/503 copy remains distinct.

Controlled browser coverage proves the timeout ends loading, preserves case/address, ignores late success, allows only explicit retry and produces no new lookup on reopen/Overview/Report/Compare. Existing confirmation, localization and mobile checks also pass.

### Changed files

- `services/location_resolver.py`
- `services/trusted_address_structure.py` (new)
- `tests/test_location_resolution_accuracy.py` (new)
- `tests/test_location_resolver.py`
- `tests/test_location_resolve_api.py`
- `tests/test_google_provider_cost_optimization.py` (three resolver-related fixture/budget tests only)
- `frontend_next/lib/workspace/location-confirmation.ts`
- `frontend_next/lib/workspace/location-confirmation.test.ts`
- `frontend_next/components/commercial-home.tsx`
- `frontend_next/components/workspace/location/location-confirmation-panel.tsx`
- `frontend_next/e2e/home-location-flow.spec.ts`
- `frontend_next/e2e/location-confirmation.spec.ts`
- This implementation plan/report.

The existing resolve API response model and frontend API transport already supported the safe fields and AbortSignal; neither required changes. No production infrastructure, unrelated product logic or pending-location work was changed.

### Reproduction commands

```text
python -m pytest tests/test_location_resolution_accuracy.py tests/test_location_resolver.py tests/test_location_resolve_api.py tests/test_google_provider_cost_optimization.py::test_commute_google_destination_resolution_concurrent_budget tests/test_google_provider_cost_optimization.py::test_destination_address_reuse_avoids_all_resolution_and_changed_address_isolated tests/test_google_provider_cost_optimization.py::test_accepted_destination_cache_bounds_expiry_failures_and_configuration -q --tb=short

# From frontend_next, sequentially:
npm run test:home-start
npm run build:e2e
node e2e/run-e2e.cjs e2e/home-location-flow.spec.ts e2e/location-confirmation.spec.ts --project=chromium --workers=1 --retries=0
npm run typecheck
npx eslint --no-ignore --max-warnings=0 components/commercial-home.tsx components/workspace/location/location-confirmation-panel.tsx lib/workspace/location-confirmation.ts lib/workspace/location-confirmation.test.ts e2e/home-location-flow.spec.ts e2e/location-confirmation.spec.ts
```

One local commit is the requested deliverable; its SHA is returned in chat after creation. No push or deploy. Production smoke remains for after merge/deploy, per the user brief.
