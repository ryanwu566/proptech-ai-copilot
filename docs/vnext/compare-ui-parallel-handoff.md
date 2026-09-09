# Track D — Property Comparison Presentation Handoff

## Scope and result

Track D adds a non-ranked, presentation-only workspace for comparing two or three explicitly selected property cases. It does not choose a winner, calculate a score, persist selection state, enumerate saved cases, or create a new decision engine.

The local-only preview is `/dev/property-compare-preview`. Every preview scenario is deterministic and visibly labelled as synthetic. The server page calls `notFound()` in production before dynamically importing the preview client, so production requests do not render or preload fixture content.

## Existing code inspected and reused

- `lib/case-storage.ts`: reuses the existing `SavedCase` and stored data shape by type only. The Track D component never calls its read, write, load, clear, or delete functions.
- `lib/property-case-evidence.ts`: the adapter reuses valuation, loan, holding-cost, location, stored-terrain, and tax evidence helpers.
- `lib/terrain-reference-evidence.ts`: reuses `TerrainReferenceState`, stored terrain evidence, state labels, layer coverage, notice, and source metadata semantics.
- `lib/property-comparison.ts`: reuses the existing minimum and maximum selection constants (2 and 3).
- `lib/vnext-identity-contract.ts`: reuses `CaseDTO`, `CaseAttachmentDTO`, and `PropertyDTO` types for an optional, genuinely supplied identity context.
- `lib/terrain-safety-gate.ts` and `lib/viewing-decision.ts`: inspected to preserve the rule that unknown, unavailable, `no_match`, partial, or limited terrain evidence is not an all-clear.
- `lib/case-comparison.ts`, `lib/property-case-comparison.ts`, and the existing comparison components were inspected but are not called. Their ranked/scored and storage-owning behavior is deliberately excluded from Track D.

Existing comparison engines, comparison components, SavedCase persistence, storage keys, identity contracts, and evidence helpers remain unchanged.

## New presentation contract and adapter

`lib/vnext-compare/types.ts` defines the parent-supplied presentation contract:

- stable `caseId`, bounded title/location summary, case update time;
- explicit identity status and optional confirmed PropertyEntity identity;
- metrics carrying value, state, unit, currency, period, and semantic basis;
- transferable valuation range/status;
- location, terrain, tax, warnings, sources, coverage, retrieval/effective times, limitations, and next checks.

The parent remains responsible for authorization and the supplied dataset. Reusable components receive only typed props and do not fetch or enumerate cases.

`adaptSavedCaseForComparison()` is a narrow bridge for existing SavedCase data. Deliberate differences from existing presentation helpers:

- it never calls the ranked comparison path and never copies score, rank, `bestCaseId`, or recommendation output;
- it requires stored valuation evidence to be `trusted`, `official_valuation`, and `transferable`, then separately validates a finite positive stored range. This follows the existing storage contract: compacted SavedCase valuations intentionally omit comparables, so re-running the original raw-result gate alone would reject valid compacted evidence;
- it does not treat a SavedCase ID, address match, or nearby coordinate as a PropertyEntity ID;
- it marks identity confirmed only when supplied Case, CaseAttachment, and Property records cross-match and the Property confirmation is human-confirmed;
- it treats saved terrain as a reference, keeps its original state, and never infers a fresh risk level from it.

## Selection, order, reference, and difference behavior

- Initial selection is always empty; there is no automatic case or winner selection.
- Zero and one selected cases show explicit next guidance.
- A fourth selection is rejected with an accessible explanation.
- Removing a comparison column only changes local selected-ID state; the supplied case remains in the picker.
- Reordering moves stable case IDs and never rekeys by array position, title, address, or coordinate.
- Filtering affects only the picker; selected comparison columns remain stable.
- The user can show all fields or differences only.
- Differences-only always retains warnings, source/coverage limitations, freshness, next checks, missing/stale/conflicting states, untrusted valuations, and terrain uncertainty/high-risk content.
- A user-selected reference case produces arithmetic deltas only. It is explicitly described as neither canonical nor recommended.

## Evidence, value, unit, and missing-data rules

- Missing numeric values remain `null`; they are never formatted as zero.
- NaN, Infinity, negative amounts, and zero values not allowed by the field contract become `malformed`. Zero is retained only for the down-payment basis, matching the existing loan visualization contract.
- Money units distinguish base currency units from ten-thousand currency units. Currency is explicit (`TWD` or `USD`). Area distinguishes `ping` and `sqm`; periods distinguish one-time, monthly, and annual values.
- No unit, currency, or period conversion is performed.
- A delta requires both metrics to be finite and `known`, with matching semantic basis, unit, currency, and period. Otherwise the UI shows `無法比較` with the exact incompatibility reason.
- Asking price and transaction price have different bases. Official valuation, down payment, mortgage payment, holding cost, and floor area are also distinct bases.
- Down payment is labelled as a down-payment amount, with a visible note that it is not complete initial cash required.
- Case `updatedAt` is displayed separately from source retrieval and effective times. Missing provenance dates remain missing.
- `unknown`, `unavailable`, `partial`, `limited`, `stale`, `conflicting`, `no_match`, `not_assessed`, `unverified`, and `malformed` remain distinct presentation states.
- `no_match` terrain explicitly says it is not proof of no hazard. Stored terrain explicitly says it is not a fresh assessment.
- Tax content presents only the supplied reference status and limitation; Track D adds no tax calculation.
- Duplicate and empty case IDs are rejected rather than renamed, merged, or used as unstable keys.

## Components and responsive presentation

- `components/vnext-compare/property-compare-workspace.tsx`: selection, filtering, local ordering, reference selection, difference visibility, aligned desktop matrix, mobile cards, disclosures, and accessible controls.
- `components/vnext-compare/property-compare-workspace.module.css`: comparison-scoped visual system and responsive layout; no global styles changed.
- Desktop uses aligned columns with a sticky case-context row.
- At 860px and below, the matrix becomes contained per-case cards. A 390×844 browser assertion confirms the document has no horizontal page overflow.

## Synthetic preview scenarios

Fixtures live outside reusable components in `lib/vnext-compare-preview/fixtures.ts`:

1. two supplied cases with compatible known fields;
2. four candidates from which the user can select up to three, including missing/untrusted valuation, unknown payment, partial costs, `no_match` terrain, known high risk, stale source data, conflicts, and long text;
3. incompatible currency, currency-unit scale, area unit, monthly/annual period, and asking/transaction-price basis;
4. duplicate IDs, empty ID/title/location, legacy identity, valid/invalid zero behavior, NaN, and Infinity.

The fixtures make no live calls and claim no real authority. Their sources are labelled synthetic/non-official or explicitly describe a simulated post-gate state.

## Local preview and focused validation

From `frontend_next`:

```powershell
node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3104
```

Open `http://127.0.0.1:3104/dev/property-compare-preview`.

Focused browser tests, using a dedicated runner and port:

```powershell
node scripts/compare-preview/run-browser-tests.mjs
```

Other validation commands:

```powershell
npm.cmd run typecheck
.\node_modules\.bin\eslint.cmd components/vnext-compare lib/vnext-compare lib/vnext-compare-preview app/dev/property-compare-preview playwright.compare-preview.config.ts
npm.cmd run build
node scripts/compare-preview/verify-production-preview.mjs
git diff --check
```

Validation completed during implementation:

- TypeScript: passed.
- Track D scoped ESLint: passed with zero warnings/errors.
- Playwright Chromium: 7 passed, 0 failed, 0 skipped (31.3 seconds on the recorded final full run).
- Production build: passed.
- Production preview exclusion: passed with HTTP 404 and `fixture_content=false` after the guarded dynamic import.
- Static forbidden-call scan: no storage read/write, SavedCase mutation, live fetch, Supabase, NLSC, or geocoding calls in reusable/preview source paths.
- Static ranking scan: no ranked comparison engine, `bestCaseId`, winner, or recommendation reference in reusable/preview source paths.
- Visual inspection: passed at 1440×1000 desktop and 390×844 mobile. Desktop columns remained aligned; mobile cards were contained and readable. Generated screenshots stayed in ignored test output and are not part of the commit.
- Known local-development-only artifact: the repository-wide Content-Security-Policy blocks React development `eval`, causing Next's development issue badge/warning. Production does not use this development behavior. Track D did not change shared CSP/configuration.

These are deterministic synthetic frontend browser tests, not production E2E against customer data or live providers.

## Remaining real-data integration

- An authorized parent surface must choose which cases it may supply and adapt them to `PropertyCompareCase` (or call the SavedCase adapter on an already-authorized subset).
- Real confirmed identity display requires the parent to provide cross-matching VNext CaseAttachment and Property records; legacy SavedCase data alone remains unverified.
- Source retrieval/effective dates, coverage, limitations, and compatible price bases must come from real evidence contracts. The UI intentionally does not infer missing provenance.
- Product navigation, production enablement, persistence, analytics, export/print, maps, and single-property reports are not part of Track D.

Track A GIS/database paths, Track B map paths, Track C report/print paths, Hero/homepage/navigation/sitemap, backend, global CSS/locales, shared test configuration, production flags, auth, and deployment configuration were not modified.
