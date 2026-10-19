# API Cost Rescue — Google Places Field Mask v1

## Scope and trace

Audited before editing on `perf/places-cost-rescue-v1`, starting at
`eaee06eb9fd95f5673d7234fbe3103dd4a70e886` (also the local `origin/main`).
This change reduces the shared Nearby Search (New) mask; it adds no
provider, request profile, detail lookup, cache, or scoring rule. Deferred
acceptance also makes unknown legacy opening labels neutral and omits empty
optional address paragraphs.

Modern flow: `services/location_insight_service.py:analyze_location` →
`services/map_service.py:get_nearby_places` →
`services/adapters/google_places_adapter.py:GooglePlacesAdapter.nearby` →
`POST https://places.googleapis.com/v1/places:searchNearby`.

Legacy `/map/nearby` uses the same adapter through `backend/api/routes_map.py`.
Its consumers are `frontend_next/app/page.tsx` (Map/Lite, category lists,
PlaceCard, nearest places) and `frontend_next/components/map/geo-map.tsx`.
These are legacy surfaces relative to the modern case workspace; they still
exist in code and are not assumed unreachable or safe to delete.

Modern `frontend_next/components/workspace/location/location-view.tsx`
renders `snapshot.poiSummary` counts and a property map with `categories={[]}`.
It does not render individual Places ratings, review counts, addresses, or
opening hours. `analyze_location` retains category/name/distance/source in
`nearest_pois`; `frontend_next/components/location-insight.tsx` also displays
that named evidence in its detail table.

## Complete field inventory (before implementation)

All field names below include the `places.` prefix. SKU classifications are
external documentation findings, not facts established by the repository.

| Requested field | Code consumer | Modern workspace / trust use | Legacy-only use | Livability dependency | Removal behavior | Field SKU |
| --- | --- | --- | --- | --- | --- | --- |
| `places.id` | `_verifiable_place`, `_normalize`, map `_place_identity` | Required validation and deduplication for accurate counts | Marker/list keys | Indirect: prevents duplicate counts | Keep; removal rejects rows or compromises identity | Pro |
| `places.displayName` | `_normalize`, `is_valid_place_type`, nearest evidence projection | Name-based trail contamination filtering; location evidence contract retains names | Labels and popups | Indirect: filtering changes counts | Keep; removal could admit contaminated names and lose named evidence | Pro |
| `places.location` | `_verifiable_place`, `_normalize`, `distance_meters` | Valid coordinates and distances | Marker positions | Direct: distance bands and radius | Keep; removal invalidates rows | Pro |
| `places.formattedAddress` | `_normalize`; map `_place_identity` defensive text fallback | None: validated Google rows have ID and coordinates, so text fallback is unused | PlaceCard and GeoMap addresses | None | Removed; Google POI addresses become empty strings | Pro |
| `places.rating` | `_normalize`; legacy page and GeoMap | None | Rating display and secondary sorting for equal distances | None | Removed; rating becomes null, hidden or no-data; tie order may change | Enterprise |
| `places.userRatingCount` | `_normalize`; legacy page | None | Review-count display and tertiary sorting for equal distances/ratings | None | Removed; count defaults to zero, rating/count badge hidden; tie order may change | Enterprise |
| `places.businessStatus` | `_normalize`, `normalize_opening_status` | None; not used for eligibility filtering or provenance quality | Fallback operational label | None | Removed; business status defaults to UNKNOWN | Pro |
| `places.currentOpeningHours.openNow` | `normalize_opening_status` | None | Current open/closed label in cards/popups | None | Removed; opening status becomes unknown when all enrichment is absent | Enterprise |
| `places.regularOpeningHours.periods` | `normalize_opening_status` | None | Hours-available label in cards/popups | None | Removed; opening status becomes unknown when all enrichment is absent | Enterprise |
| `places.types` | `_verifiable_place`, `is_valid_place_type`, map filtering | Required category-compatible, uncontaminated POI evidence | Category membership | Indirect: accepted category counts | Keep; removal rejects rows | Pro |

`build_livability_scoring` uses category weights, POI counts, distance bands,
radius limits, and evidence-quality factors/ceilings. No removed field affects
those inputs. Evidence-quality accounting uses category outcomes and
filtering/deduplication statistics; checked time/source are recorded separately.

## Masks and cost verdict

BEFORE:

```text
places.id,places.displayName,places.location,places.formattedAddress,places.rating,places.userRatingCount,places.businessStatus,places.currentOpeningHours.openNow,places.regularOpeningHours.periods,places.types
```

AFTER (current):

```text
places.id,places.displayName,places.location,places.types
```

Expected SKU before: **Nearby Search Enterprise**.
Expected SKU after: **Nearby Search Pro**.
Removing address and business status minimizes payload but does not itself
lower the SKU; removing all four Enterprise fields does.
Names/IDs remain necessary for validation and existing evidence contracts.

**EXTERNAL PRICING VERIFICATION REQUIRED** when relying on repository evidence
alone. External SKU verification was performed for this change using Google's
[Nearby Search field-mask documentation](https://developers.google.com/maps/documentation/places/web-service/nearby-search#fieldmask)
and [Place Data Fields](https://developers.google.com/maps/documentation/places/web-service/data-fields).
They classify rating, userRatingCount, currentOpeningHours and
regularOpeningHours as Enterprise, and the retained fields as Pro.
The expected downgrade is inferred from those published field tiers; no live
billing measurement, account-specific pricing, prices, or savings amounts are
claimed.

## Compatibility and verification boundary

Only the outbound field mask changes in provider code. The normalizer keeps
the existing NearbyPlace schema and optional enrichment handling. Missing
enrichment yields empty address, null rating, zero review count, UNKNOWN
business status, and an unknown opening-status label. The legacy
`opening_hours_source` default remains `businessStatus`; with `opening_status`
unknown this is a compatibility default, not observed hours evidence.
Mock/demo data is untouched. Legacy ratings, hours, POI addresses, and
rating-based distance-tie sorting therefore change for real Google results.
Modern counts, distance/name evidence, scoring, and provenance are preserved.

The adapter's existing configuration cache key includes FIELD_MASK, so the
new mask does not reuse entries from the previous request configuration.
There are still at most six physical category requests on an uncached modern
analysis and none added for enrichment. Repeated category requests keep the
existing cache behavior.

Targeted tests cover exact outgoing fields for all categories, absent optional
enrichment, score/nearest-evidence parity, modern Location counts and response
contracts, provenance, and the six-call/repeat-cache budget. HTTP is mocked;
service fan-out is replaced with synchronous execution in the new contract
test so it starts no worker pool. No live providers are queried.

Targeted result: **26 passed in 3.69s**. The updated outgoing-mask test was
first observed failing against the original ten-field mask. The passing run
included all tests in `test_google_places_adapter.py` and
`test_places_field_mask_contract.py`, the existing distance-tier scoring test,
and these existing provider-cost tests:

- `test_places_field_mask_is_minimal_for_property_analysis`
- `test_places_configuration_version_changes_key`
- `test_places_malformed_response_is_not_cached_as_successful_zero`
- `test_places_unverifiable_rows_never_become_cached_successful_zero`
- `test_places_valid_omitted_empty_collection_remains_successful_zero`

`git diff --check` also passed. The new repeat-cache assertion validates
per-request durations separately because these timings may change on a cache
hit; all returned evidence and the original observation time must match.

The initial implementation deferred heavy acceptance to a later authorized session, including
modern Location rendering and legacy Map/Lite missing-enrichment behavior.
No full Python suite, browser suite, production build, build:e2e, worker pool,
or Docker-heavy test was part of that initial validation. The deferred
acceptance results below supersede that initial boundary.

No report implementation, case-storage, or existing report test is edited.
The later legacy card presentation fix touches the shared `app/page.tsx`;
textual overlap with active Report edits remains unverified. Report snapshots
that reuse location summaries are covered by this branch's API-cost and trust
browser checks, while combining the active Report changes remains a separate
integration check. No commit, push, merge, or deployment is authorized here.

## Deferred acceptance

The public Methods entry renders `MapInsight` in `app/page.tsx` with the
heading “Map Insight Lite” and the shared `GeoMap`. `LegacyMapInsight` is an
unreferenced function, not a second accessible screen. The guided journey's
Location step remains reachable through `/?workflow=property`; its POI detail
table consumes category/name/distance/source rather than enrichment.

Initial desktop/mobile browser comparisons observed a green “營業狀態未知”
label on minimal responses. This was a misleading status color, and the new
browser test failed on that exact class at both widths (enriched reference
and guided cases passed). The bounded presentation fix uses neutral slate
for unknown status and omits empty optional address paragraphs. No provider
field or secondary request was added.

Final backend acceptance: **107 passed**, two dependency deprecation warnings.
This includes adapter/service/API, cache/concurrency, malformed-response,
commercial trust, and representative API-cost-journey tests, plus explicit
old-mask/new-mask parity for counts, scores, duplicate IDs, nearest evidence,
and call volume. Minimal named rows also retain trail and category rejection.

Before and after: six physical Google category calls initially, zero additional
calls on repeat. No rating/address/hour/review detail request is introduced.

Official SKU classification was rechecked against the Google documentation
linked above: BEFORE **Nearby Search Enterprise**; AFTER **Nearby Search Pro**.
**PRICE INPUT REQUIRED**: account-specific prices and dollar savings were not
verified or claimed.

### Observed legacy changes and classification

The enriched reference and minimal responses were compared at 1440px and
390px using the accessible Methods → Map Insight flow. Both click-through
`GeoMap` popups and cards retain place names and distances. The property
address still comes from geocoding and remains visible. Guided Location
retains its named-distance/source POI table at both widths.

| Change with minimal responses | Observed result | Classification |
| --- | --- | --- |
| POI formatted address | Omitted from card and selected popup; no empty address paragraph; property address retained | ACCEPTABLE DE-EMPHASIZED LEGACY LOSS |
| Rating | Badge and popup rating disappear; nearest summary uses its existing no-data copy | ACCEPTABLE DE-EMPHASIZED LEGACY LOSS |
| Review count | Rating/review badge absent; normalized zero is not leaked as a standalone value | ACCEPTABLE DE-EMPHASIZED LEGACY LOSS |
| Opening status / business status | Explicit unknown label in neutral slate; no operational/open-now assertion | ACCEPTABLE DE-EMPHASIZED LEGACY LOSS |
| Sorting | Tested equal-distance order changes from higher-rated B,A to provider-order A,B; distance remains primary | ACCEPTABLE DE-EMPHASIZED LEGACY LOSS |

These enrichment losses are intentional cost reductions in the secondary legacy
experience. They do not justify Enterprise fields in modern requests. No mask
split, opt-in enrichment feature, automatic lookup, or new provider was needed.
The original green unknown-hours label was corrected before acceptance.

### Completed checks

- Backend: **107 passed**, two dependency deprecation warnings; no live providers.
- Main browser run: **40 passed**, zero skipped/flaky/failed, 2.4 minutes.
  Files: `places-minimal-mask`, `commercial-location-commute`,
  `location-confirmation`, `api-cost-journey`, `commercial-trust-acceptance`.
- Focused release/map browser run: **5 passed**, 20.2 seconds. Covers Home and
  Methods navigation, Map Basic, case workspace routes, and one-geocode Map
  analysis with partial real categories.
- Browser runs: Playwright bundled Chromium only, headless, `--workers=1`,
  `--retries=0`, `--project=chromium`; installed Chrome was not launched.
- Browser checks include no horizontal page overflow, no undefined/null/NaN
  leakage, no empty optional address row, neutral unknown-hours styling,
  preserved named-distance evidence, and a provider-wide request ledger.
  Only directory/health metadata and mock basemap tiles are excluded from the
  Map ledger; entering the tool adds no analysis calls, and explicit search
  makes one `/map/search` and one `/map/nearby` call with no follow-up.
- Modern workspace checks cover counts, source/timestamp preservation,
  identity/trust boundaries, mobile layout, explicit actions, cache reuse,
  and zero analysis calls on Save/Reopen/Compare/Report navigation.
- `npm.cmd run typecheck`: passed.
- `npm.cmd run lint`: passed, zero errors and 23 pre-existing warnings.
- `npm.cmd run build:e2e`: passed after the card fix.
- `npm.cmd run build`: passed for the final production code.
- `git diff --check`: passed.

Local evidence is retained under `.local/places-mask-acceptance/` (ignored
runtime artifacts): `browser.json`, `release-browser.json`, screenshots and
budget reports. Desktop card comparison:
[enriched reference](../.local/places-mask-acceptance/screenshots/1-legacy-card.png),
[minimal response](../.local/places-mask-acceptance/screenshots/3-legacy-card.png).
Mobile card comparison:
[enriched reference](../.local/places-mask-acceptance/screenshots/6-legacy-card.png),
[minimal response](../.local/places-mask-acceptance/screenshots/8-legacy-card.png).

Git refs refreshed from origin: `origin/main` and HEAD are both
`eaee06eb9fd95f5673d7234fbe3103dd4a70e886`; behind 0 / ahead 0, excluding
the six intended uncommitted files. The current Report branch ref is
`4a17ddb91f4b7d3e5a106759ba71175619347419`, an ancestor of current main.
Its active worktree's uncommitted changes were not inspected. No report
implementation is edited here; the small `app/page.tsx` card change is a shared
frontend integration point and should be checked when combining branches.

### Final budget gate and decision

`scripts/check_frontend_bundle_budget.py` and the unchanged
`scripts/check_route_budgets.py` both passed against the final production
build. Attribution, required-route coverage, and **all 24 route ceilings**
passed. Total static assets: **3,534,458 / 8,000,000 bytes**; largest client
chunk: **605,462 / 900,000 bytes**. No ceiling or production measurement script
was changed.

The initial monolithic browser attribution failed with a `process_cleanup`
diagnostic near the sampler's built-in 210-second deadline (about 224 seconds
including cleanup); its diagnostic did not expose a specific underlying error
code. This was not recorded as a byte-budget failure or a pass. Acceptance then
ran the existing `measure_route_assets.cjs` unchanged in two sequential groups
of 12 routes. Each retained the original deadline, two samples per viewport at
390px and 1440px, cold contexts, bundled headless Chromium, and API/provider
blocking. The build fingerprint was checked before and after each group;
sample count, viewport list, and complete route coverage were checked before
combining the evidence. The existing analyzer and route-budget checker accepted
that complete evidence. The local batching helper and raw receipts are ignored
artifacts under `.local/places-mask-acceptance/`, not changes to release tooling.

**B. MINIMAL MASK ACCEPTED WITH INTENTIONAL LEGACY DEGRADATION.**

Modern functionality, livability, identity/name/type validation, contamination
filtering, deduplication, source/freshness, and provider-call volume pass the
targeted and browser contracts. The five legacy losses above are intentional,
structurally safe, and require no enriched request path.

Technically safe to commit: **YES**. Clean tree: **NO**, because the six intended
files remain uncommitted. Exact next action: review this six-file diff and await
an explicit commit instruction. No commit, push, merge, or deployment was made.
