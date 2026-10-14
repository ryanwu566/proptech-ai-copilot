# My Places and multi-destination commute v1

## Intent and design

Buyers define reusable destinations and inspect how each saved property fits their weekly life. Evidence stays factual: no property score, ranking, preference inference, or automatic provider calls. This is an isolated subsystem on `feat/my-places-multidestination-v1`, starting at `e1d7f131c576c75841aea975dd2be60009c09392`.

`/places` manages up to 20 destinations with user labels, category, address, mode, priority, and integer weekly round trips (0–21). Keyboard-accessible move buttons preserve explicit order. `/cases/[caseId]/commute-planner` reads saved property identity without writing the case. All places initially participate; per-case selection persists separately. Mobile cards show status, current mode, route time/distance, provider, checked time, limitations, and individual weekly time.

Version-1 local stores use dedicated keys. Route evidence is bounded to 200 records and keyed by case, place, property fingerprint, destination fingerprint, and mode. Fingerprints include address/coordinates and identity anchor/revalidation state. Edited labels, priority, frequency, and order do not invalidate routes; changed locations and modes do. Previous evidence stays visible as stale, with its original destination/mode/property explicitly identified. Stale, simulated, fallback, partial, mismatched, missing, malformed, and unavailable evidence never contributes to known totals. Unknown remains an explicit list, even for zero-trip destinations without reliable route evidence. Valid zero-trip destinations contribute zero.

Existing `api.commuteRoute` is the only provider seam, supporting driving/transit/walking via Google Routes. TDX station context is not destination routing. No new providers or dependencies. One click calculates at most 20 selected routes sequentially, skipping zero-trip places and current known results unless explicitly refreshed. Identical origin/destination/mode requests share one promise within a batch, including sequential duplicate destinations. Concurrent identical requests also deduplicate across mounted planners. No retries or background monitoring. Unmounted/changed contexts cannot display a late response as current. Writes never touch accepted commute or frozen case evidence.

A pure `CommuteComparisonSummary` exposes known weekly minutes, known count, unknown place IDs, and destination facts for future Compare/Preference use. Compare, Decision Room and Preference remain separate read-only contracts. Existing performance ceilings remain unchanged; both feature routes receive their own fixed Performance Budget v2 supplemental baseline.

Full feature copy supports zh-TW, en, ja, ko. User labels/addresses remain verbatim. Locale persists through the existing context via a small versioned local setting. Discoverability uses a shared header link and a narrow case-navigation entry. Planner owns its localized case shell to avoid rendering untranslated existing workspace chrome.

## Implementation plan

1. Write failing native Node tests for versioned destination CRUD/order/validation, corruption and storage errors, bounded route persistence, isolation/stale selection, deterministic burden, provenance, and explicit request deduplication. Implement pure model, stores, and query helper; run focused tests.
2. Add complete typed locale catalogues, management form/cards, localized standalone planner shell, server routes, and narrow header/case navigation links. Keep full catalogue outside shared header bundles. Persist locale without provider effects.
3. Add browser tests across all 16 locale/viewport combinations: create three places, keyboard/focus and overflow, explicit calculation counts, loading, unknown result, reload/reopen, selection/frequency/address/mode changes, stale evidence, property switch, and immutable saved evidence. All provider endpoints are intercepted and counted; no live commercial calls.
4. Run all native frontend deterministic tests, relevant Python route/adapter/frontend regressions, typecheck, lint, production and browser builds, existing bundle budget and repository hygiene, and diff checks. Independently review provider boundaries, stale leakage, labels/locales, and evidence mutation. Resolve significant findings and create exactly one local commit. Do not push, merge, or deploy.

## Review focus

- Out-of-order asynchronous responses after property/destination changes remain scoped to their captured fingerprints.
- Storage denial, corruption, and incompatible versions surface errors instead of claiming successful saves or overwriting data.
- Mock/fallback/partial results retain provider truth and stay out of known weekly burden.
- Requests with duplicate destinations deduplicate only identical origin/destination/mode; mode mismatches fail closed.
- Locale changes never translate user labels, change route fingerprints, or trigger route requests.

## Execution decisions

The user's detailed build instruction authorizes implementation; work proceeds inline, with one independent final reviewer. The existing worktree provides isolation. Intermediate commit steps are deferred to satisfy the user's exactly-one-commit requirement.

## Independent review

A separate read-only reviewer found two Important issues and no Critical or Minor issues. Both were reproduced with failing tests and fixed:

- Sequential duplicates previously lost their in-flight deduplication entry. A batch-local result map now makes one attempt per unique route per action. A later explicit refresh creates a new batch.
- Contradictory resolved responses with failure/malformed reason codes previously counted as known. Availability now also requires the provider's success reason.

No review behavior was declined. A screenshot check also found the shared date formatter omitted the time of day; the planner now renders a localized date/time with the original ISO timestamp in a semantic time element.

## Current final integration report

The historical feature was replayed onto current main, with current navigation and Performance Budget v2 retained. The authoritative final validation and fixed route measurements are in [the 2026-10-13 final integration report](my-places-final-integration-20261013.md). Earlier feature-only counts and the former aggregate homepage checker are superseded.
