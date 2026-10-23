# Location to Market administrative context implementation plan

> Execute inline using superpowers:executing-plans, with regression tests before implementation.

**Goal:** Preserve current location contracts and safely repair older confirmed cases missing administrative area.
**Architecture:** Keep the existing resolver/parser and anchor mapping. Add a compare-and-swap administrative-only repair with explicit lookup and explicit save.
**Tech stack:** FastAPI/Python, Next.js 16.4.2/React/TypeScript, Node tests, Playwright bundled Chromium.
**Spec:** User implementation request attached on 2026-10-23 (two Taipei incident addresses, no deploy or merge).

## Evidence and contract map (before changes)

`POST /location/resolve` → `GoogleAddressProvider` → `_google_administrative_area` → `_resolved` structural acceptance → `LocationResolveResult.to_safe_dict` → `LocationResolveResponse` → `api.locationResolve` → `acquireLocationResolution` → `interpretLocationResolution` → `LocationCandidate` → `buildConfirmedLocationAnchor` → `JourneyPropertyIdentityAnchorV1.administrative_location` → saved-case normalization → `hasCompleteAdministrativeArea` / `buildMarketRefreshContext` → Market refresh enabled.

Current source carries county/district end to end. Google administrative level 1 is city/county; level 2 or level 3 with a district suffix is district; villages are excluded. Structured and formatted fields must agree with the input.

Read-only production evidence: frontend release SHA `3ab03f9b2d8d4e9e947b5a5c57c6fc9cc8b8bd77`; backend live OpenAPI LocationResolveResponse has neither county nor district. Cloud Run revision `proptech-earth-engine-api-00021-saf` has 100% traffic and image tag `01207cfa1b2aa6a6582c0051753bab7c6fb618cb`; that source revision's response model also lacks both fields. Backend release SHA reports unconfigured. No live provider calls used to establish this.

## Constraints and review focus

- No production deployment, PR merge, rebase, automatic provider calls, coordinate inference, or new address parser.
- Preserve Pending Location, Google-primary/strict TGOS, 8 s server deadline, 10 s browser timeout, security version and existing workspace features.
- Old cases remain unchanged on read; failed, conflicting, late, concurrent, or incomplete repair must not mutate storage.
- Coordinate drift fails closed; administrative repair never replaces coordinates or anchor identity.
- Price estimation still requires real building facts; an address-only case cannot safely enable estimation.
- Browser scope: bundled Chromium, workers=1, retries=0; four locales at 390/430 where changed.

## Tasks

- [x] Add deterministic Google-shaped fixtures for Taipei City Hall and Zhongshan South Road; exercise provider → actual API serialization → frontend acquisition/confirmation → Market and reopen. Include level-2/3, village exclusion and cross-district incident rejection. Demonstrate current source behavior before implementation.
- [x] Add failing tests for administrative repair: explicit intent, complete trusted candidate, equivalent address, matching coordinates, partial-admin consistency, unchanged case version, preserved anchor/evidence, and safe failed writes.
- [x] Implement `planAdministrativeAreaRepair` in a focused pure module, locked save in `case-storage.ts`, and a Location repair panel with four-locale copy. Market links explicitly to Location. No effects acquire data.
- [x] Run focused unit/contracts and browser journeys; verify zero acquisition on Overview/Market/Location/Report/Compare, reload and reopen, including failed/stale backend responses.
- [x] Run typecheck, lint, build, bundle/route budgets and relevant regression suites. Record actual counts and limitations in an operations report.
- [x] Independently review the branch, fetch origin and integrate advanced main. Prepare the requested commit/PR handoff; final SHA and PR URL are delivered in the task response. Do not merge or deploy.

## Execution ledger

- Baseline resolver/API/accuracy suite: 64 passed (one upstream Starlette deprecation warning).
- Existing user-specified linked worktree verified; no additional worktree needed.
- Ruling: source already supports the observed contract; do not add speculative provider extraction or a fallback parser. Production skew is independently evidenced by live schema and Cloud Run traffic/image metadata.
- Ruling: missing building facts keep price estimation disabled; acceptance must distinguish the administrative gate from the existing valuation input gate.
- Independent review: fixed queued-save lifecycle cancellation and prefixless legacy geography acceptance, each with observed RED→GREEN tests. Follow-up review found both resolved.
- Integrated main `c377ee94955429ab3d4804ffd8d8a6fae8c99a52`, preserving demo-case changes; no rebase.
- Final Node checks: 163 domain/workspace tests + 60 storage tests passed. Shared Google/API contracts: 6 passed. Browser: 30 distinct checks passing (20 new, 10 existing), bundled Chromium, workers=1, retries=0, all four locales and 390/430.
- Full Python: 4,216 passed, 151 skipped, one unchanged worker-pool timing test failed under load and passed in quiet isolation. Exact caveat and counts recorded in the operations report.
- Typecheck, lint (0 errors / 23 existing warnings), optimized build, all 24 route budgets, global bundle budget, hygiene and diff checks passed. Batched browser attribution retained the existing protocol and build fingerprint.
