# Commercial Property Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the root-page tool collection with a case-scoped, route-driven commercial property workspace that preserves existing analytical capability and supports known-address entry, saved cases, comparison, and client-readable reports.

**Architecture:** A nested Next.js workspace layout loads one case through a storage-independent repository and exposes independent evidence slices to five route sections. Existing domain components are extracted and wrapped behind case-aware adapters; legacy local cases remain supported until the VNext durable case and PropertyEntity contracts become authoritative.

**Tech Stack:** Next.js App Router, React, TypeScript, Tailwind/CSS modules, existing REST clients and VNext identity contracts, Playwright, ESLint, TypeScript compiler.

**Spec:** `docs/superpowers/specs/2026-09-27-commercial-property-workspace-design.md`

## Global Constraints

- Do not expose provider names, API paths, HTTP status, raw payloads, internal IDs, or internal readiness enums in primary commercial UI.
- The only primary workspace sections are Overview, Market & Price, Location & Commute, Risk & Environment, and Finance & Transaction.
- Compare is limited to 2–3 cases and must not rank, score, declare a winner, or use a black-box recommendation.
- Risk & Environment must not calculate or imply a single property safety score.
- `asking`, `estimate`, and `manual` price bases remain visibly distinct and use `萬元`; monthly costs use `NT$/month`; area uses `坪`; rate uses `%`.
- Optional unopened modules do not count as blockers or incomplete work.
- Each evidence slice owns its loading, available, partial, stale, no-data, unavailable, retry, freshness, and invalidation state.
- A failure or retry in one evidence slice must not clear another slice.
- Late results whose case revision/input fingerprint is stale must be ignored.
- At 390×844 there is no page-level horizontal overflow and the document is the sole normal scroll owner.
- Preserve the current feature gate and authentication boundary for VNext capabilities until the approved Property Identity closure changes it.
- Do not begin domain extraction from files owned by an active closure until that closure is merged and its final contract is reviewed.

## Review Focus

1. **Property revision changes during an in-flight request:** the late result is discarded and evidence for the new property remains unchanged; covered in Phase 1 repository/invalidation tests.
2. **Reopened legacy case lacks compacted raw evidence:** the workspace renders honest `not_requested` or typed `partial` states and never fabricates detail; covered in Phase 1 adapter and reopen tests.
3. **One provider fails while prior evidence exists:** the local boundary shows the failure plus dated previous evidence and does not erase sibling slices; covered in Phase 1 and each domain phase.
4. **Unlike price bases or missing units in comparison:** the row is marked non-comparable instead of calculating a delta; covered in Phase 7 comparison-model tests.
5. **390 px keyboard/map/table interaction:** no page overflow, nested scroll trap, obscured CTA, or inaccessible focus; covered in Phase 8 Playwright acceptance.

---

## Dependency and branch gate

Before each phase:

- [ ] Record `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, and `git rev-parse origin/main`.
- [ ] Work in an isolated feature worktree created for that phase; do not modify or reuse another active worktree.
- [ ] Rebase/merge from current `origin/main` using the project’s approved workflow, then review newly merged contracts and tests.
- [ ] Confirm no uncommitted user changes overlap the phase files.

Phase-specific merge gates:

| Closure | Blocking phases | Contract review |
|---|---|---|
| Journey Property Identity anchor | Phase 1 durable identity integration | VNext case attachment, PropertyEntity propagation, workspace route and auth boundary |
| Valuation / Holding Cost reliability | Phase 3 and Phase 6 | result status, invalidation, price/holding units, failure semantics |
| Commute production closure | Phase 4 | address lookup, route status, mode/duration/distance, source fallback |
| Geological Sensitivity | Phase 5 | layer identifier, assessment/coverage/freshness states, runtime failure behavior |

## Planned file structure

### New route files

```text
frontend_next/app/properties/new/page.tsx
frontend_next/app/explore/page.tsx
frontend_next/app/cases/page.tsx
frontend_next/app/compare/page.tsx
frontend_next/app/workspace/[caseId]/layout.tsx
frontend_next/app/workspace/[caseId]/page.tsx
frontend_next/app/workspace/[caseId]/overview/page.tsx
frontend_next/app/workspace/[caseId]/market/page.tsx
frontend_next/app/workspace/[caseId]/location/page.tsx
frontend_next/app/workspace/[caseId]/risk/page.tsx
frontend_next/app/workspace/[caseId]/finance/page.tsx
frontend_next/app/workspace/[caseId]/report/page.tsx
```

### New workspace units

```text
frontend_next/components/workspace/workspace-shell.tsx
frontend_next/components/workspace/workspace-navigation.tsx
frontend_next/components/workspace/property-context-header.tsx
frontend_next/components/workspace/evidence-state-boundary.tsx
frontend_next/components/workspace/entry/address-entry.tsx
frontend_next/components/workspace/entry/property-confirmation.tsx
frontend_next/components/workspace/overview/overview-view.tsx
frontend_next/components/workspace/market/market-price-view.tsx
frontend_next/components/workspace/location/location-commute-view.tsx
frontend_next/components/workspace/risk/risk-environment-view.tsx
frontend_next/components/workspace/finance/finance-transaction-view.tsx
frontend_next/components/workspace/report/case-report.tsx
frontend_next/components/compare/case-picker.tsx
frontend_next/components/compare/case-comparison-view.tsx
frontend_next/lib/workspace/workspace-model.ts
frontend_next/lib/workspace/case-repository.ts
frontend_next/lib/workspace/legacy-case-adapter.ts
frontend_next/lib/workspace/invalidation.ts
frontend_next/lib/workspace/overview-model.ts
frontend_next/lib/workspace/comparison-model.ts
frontend_next/lib/workspace/report-model.ts
```

Each file has one responsibility: route files select the section; the layout loads case context; views compose domain evidence; pure models determine derived states; repositories own persistence and concurrency.

## Phase 1: Workspace shell, property context, route and state foundation

**Scope:** Introduce canonical nested routes, storage-independent case/evidence types, a legacy adapter, selective invalidation, one property header, and route navigation. Keep the old root journey available behind the current entry until parity is proven.

**Files:**

- Create: `frontend_next/lib/workspace/workspace-model.ts`
- Create: `frontend_next/lib/workspace/case-repository.ts`
- Create: `frontend_next/lib/workspace/legacy-case-adapter.ts`
- Create: `frontend_next/lib/workspace/invalidation.ts`
- Create: `frontend_next/components/workspace/workspace-shell.tsx`
- Create: `frontend_next/components/workspace/workspace-navigation.tsx`
- Create: `frontend_next/components/workspace/property-context-header.tsx`
- Create: `frontend_next/components/workspace/evidence-state-boundary.tsx`
- Create: `frontend_next/app/workspace/[caseId]/layout.tsx`
- Create: the five section route placeholders listed above
- Modify: `frontend_next/app/workspace/[caseId]/page.tsx` to redirect to `overview`
- Modify: `frontend_next/lib/case-storage.ts` only through the compatibility adapter contract
- Modify after closure merge: VNext case/identity client files only if the approved contract requires an adapter
- Test: `frontend_next/lib/workspace/workspace-model.test.mjs`
- Test: `frontend_next/lib/workspace/invalidation.test.mjs`
- Test: `frontend_next/e2e/commercial-workspace-routing.spec.ts`
- Test: `frontend_next/e2e/commercial-workspace-property-context.spec.ts`

**Interfaces:**

- Produces `WorkspaceSection`, `EvidenceState<T>`, `PropertyCaseWorkspace`, `PropertyCaseRepository`, `WorkspaceError`, `EvidenceKey`, and `InputFingerprint` exactly as defined by the spec.
- `PropertyCaseRepository` exposes `getCase(caseId)`, `subscribe(caseId, listener)`, `updateIdentity(caseId, expectedRevision, identity)`, `updateAssumptions(caseId, expectedRevision, assumptions)`, `setEvidence(caseId, key, fingerprint, state)`, and `save(caseId)`.
- The legacy adapter consumes current `SavedCase` and returns honest `partial` states for usable compacted summaries or `not_requested` when no transferable evidence exists.

- [ ] **Step 1: Write model and legacy-adapter tests**

  Assert valid evidence-state transitions, explicit summary-only migration, active price-basis preservation, and rejection of malformed/unknown saved values.

- [ ] **Step 2: Run the focused model tests and verify they fail**

  Run: `cd frontend_next; node --test lib/workspace/workspace-model.test.mjs`

  Expected: FAIL because workspace model/adapter exports do not exist.

- [ ] **Step 3: Implement the model, repository interface, and legacy adapter**

  Keep persistence behind the interface. Do not add direct `localStorage`, `sessionStorage`, or window-event reads to view components.

- [ ] **Step 4: Write invalidation and stale-response tests**

  Cover identity, property facts, asking price, active price basis, income, commute destination, and risk-layer changes. Assert stale fingerprints cannot commit.

- [ ] **Step 5: Implement `computeInvalidation()` and repository compare-and-set behavior**

  Port the valid rules from `closed-loop-journey.ts`; do not delete that file yet.

- [ ] **Step 6: Write route/header Playwright tests**

  Assert redirect from `/workspace/[caseId]`, five real links, deep-link refresh, Back/Forward, same header identity on every section, sticky compact header, and route-level invalid/unauthorized states.

- [ ] **Step 7: Build the nested layout, shell, navigation, header, and local evidence boundary**

  The boundary accepts exactly one evidence slice and never catches/clears the whole workspace.

- [ ] **Step 8: Run Phase 1 verification**

  Run: `cd frontend_next; npm run typecheck; npm run lint; npm run build:e2e; node e2e/run-e2e.cjs e2e/commercial-workspace-routing.spec.ts e2e/commercial-workspace-property-context.spec.ts`

  Expected: all commands PASS; direct route refresh and Back/Forward are demonstrated.

**Dependency:** Property Identity closure must merge before selecting the final durable repository implementation. Non-overlapping pure models and route tests may start earlier.

**User-visible outcome:** A saved case has a stable URL, persistent property context, five navigable destinations, and local error boundaries.

**Rollback boundary:** Remove the new nested layout/routes and adapter; the old `/` journey and `/cases/[caseId]` remain untouched and usable.

## Phase 2: Overview & Next Actions

**Scope:** Create one deterministic synthesis of major findings, material unknowns, blockers, and next useful actions. Do not remove old decision surfaces until acceptance parity passes.

**Files:**

- Create: `frontend_next/lib/workspace/overview-model.ts`
- Create: `frontend_next/components/workspace/overview/overview-view.tsx`
- Modify: `frontend_next/app/workspace/[caseId]/overview/page.tsx`
- Reuse/consult: `frontend_next/lib/risk-summary.ts`, `decision-summary.ts`, `decision-case-journey.ts`, property-case models
- Test: `frontend_next/lib/workspace/overview-model.test.mjs`
- Test: `frontend_next/e2e/commercial-workspace-overview.spec.ts`

**Interfaces:**

- Produces `OverviewModel { posture, findings[0..5], unknowns, blockers, actions[0..5] }`.
- Every item includes `id`, `label`, `reason`, `sectionHref`, `evidenceKeys`, and `priority`; findings require available evidence, blockers require a materially blocked user task.

- [ ] **Step 1: Write failing overview-model tests**

  Cover empty optional modules, identity conflict, missing area, missing asking price, valuation failure with market evidence, unavailable flood evidence, income absent, stale evidence, and actionable navigation targets.

- [ ] **Step 2: Implement the minimal deterministic overview model**

  Reuse fact extraction where safe. Do not reuse `overallScore`, readiness percentage, or “all modules complete” semantics.

- [ ] **Step 3: Write and implement the Overview view**

  Render the four required groups in order and cap primary findings/actions. Each item links to its section.

- [ ] **Step 4: Add Playwright coverage**

  Assert optional unopened modules are absent from unknowns, blockers precede normal actions, provider terminology is absent, and a local domain failure does not replace Overview.

- [ ] **Step 5: Verify Phase 2**

  Run focused model/E2E tests plus `npm run typecheck` and `npm run lint`.

**Dependency:** Phase 1 workspace contract.

**User-visible outcome:** Opening a case answers what matters, what is unknown, what blocks interpretation, and what to do next without repeated readiness cards.

**Rollback boundary:** Route can fall back to a simple case summary while old decision panels remain on `/`.

## Phase 3: Market & Price

**Scope:** Extract Market and Valuation from `app/page.tsx`, combine their presentation, preserve independent service states, and make price provenance explicit.

**Files:**

- Create: `frontend_next/components/market/market-insight.tsx` from the root-defined component
- Create: `frontend_next/components/valuation/valuation-analysis.tsx` from the root-defined component
- Create: `frontend_next/components/workspace/market/price-summary.tsx`
- Create: `frontend_next/components/workspace/market/price-range-comparison.tsx`
- Create: `frontend_next/components/workspace/market/comparable-evidence-table.tsx`
- Create: `frontend_next/components/workspace/market/market-price-view.tsx`
- Modify: `frontend_next/app/workspace/[caseId]/market/page.tsx`
- Modify: `frontend_next/app/page.tsx` to import extracted legacy components without changing old behavior
- Modify after reliability merge: valuation visual/result files and `lib/api.ts` only as required
- Test: `frontend_next/lib/workspace/market-price-model.test.mjs`
- Test: `frontend_next/e2e/commercial-workspace-market-price.spec.ts`

**Interfaces:**

- Consumes independent `market` and `valuation` evidence states plus case assumptions.
- Produces `PriceSummaryModel` with separately labeled `askingPrice`, `estimatedRange`, `comparableMedianRange`, `scope`, `sampleCount`, `period`, `confidence`, and `activeBasis`.

- [ ] **Step 1: Wait for and review Valuation/Holding reliability closure**

  Update planned status mappings to its final result contract before moving code.

- [ ] **Step 2: Write model tests for price provenance and unavailable states**

  Assert asking, estimate, and observations never substitute for one another; `0` is not rendered for missing evidence; mismatched units are rejected.

- [ ] **Step 3: Extract Market and Valuation without behavior change**

  Move code out of `app/page.tsx`, preserve existing test IDs and legacy imports, and run the current market/valuation test suites before composing the new route.

- [ ] **Step 4: Implement summary, range comparison, comparable table, trends, and disclosures**

  Comparable table is primary; filters/methodology/provider details are advanced disclosures.

- [ ] **Step 5: Add independent-failure E2E scenarios**

  Test market-only, valuation-only, both available, stale/partial, retry, late replacement, explicit price-basis changes, and 390 px behavior.

- [ ] **Step 6: Verify Phase 3**

  Run current market certification tests, valuation reliability tests, new E2E, typecheck, lint, and `git diff --check`.

**Dependency:** Phase 1 and Valuation/Holding closure.

**User-visible outcome:** One price page explains asking price, estimated range, observed comparables, confidence, scope, period, and chosen finance basis.

**Rollback boundary:** The new route can render extracted legacy Market and Valuation blocks independently; the old root routes continue importing them.

## Phase 4: Location & Commute

**Scope:** Create one resolved-location controller and map-first experience combining map, actual POIs, commute, and contextual demographics.

**Files:**

- Create: `frontend_next/lib/workspace/location-context.ts`
- Create: `frontend_next/components/workspace/location/location-commute-view.tsx`
- Create: `frontend_next/components/workspace/location/location-map-panel.tsx`
- Create: `frontend_next/components/workspace/location/poi-evidence-list.tsx`
- Create: `frontend_next/components/workspace/location/commute-destinations.tsx`
- Modify: `frontend_next/components/location-insight.tsx` to accept controlled resolved context
- Modify: `frontend_next/components/map/geo-map.tsx` for controlled layers/full-screen mode
- Modify after closure merge: commute components and `lib/api.ts`
- Modify: `frontend_next/app/workspace/[caseId]/location/page.tsx`
- Test: `frontend_next/lib/workspace/location-context.test.mjs`
- Test: `frontend_next/e2e/commercial-workspace-location-commute.spec.ts`

**Interfaces:**

- Produces one `ResolvedLocationContext { fingerprint, enteredAddress, normalizedAddress, center, acceptance }` per case revision.
- Commute evidence is keyed by `{ originFingerprint, destination, mode }` and cannot alter property identity.

- [ ] **Step 1: Wait for and review Commute production closure**

- [ ] **Step 2: Write shared-location and request-deduplication tests**

  Assert Location and Map use the same accepted geocode, rejected geocoding blocks downstream POIs, and identity is unaffected by destination changes.

- [ ] **Step 3: Implement the controlled location context and adapt existing components**

  Preserve current race cancellation and geocoding acceptance behavior.

- [ ] **Step 4: Implement desktop map/panel and evidence hierarchy**

  Lead with facility/distance/time/status. Put generic scores and demographics after actual evidence; provider details live in disclosure.

- [ ] **Step 5: Implement mobile map and in-flow results sheet**

  Default map height 300 px, full-screen escape route, no simultaneous nested scrollers.

- [ ] **Step 6: Add failure and mobile E2E tests**

  Commute failure retains POIs/demographics/map; one destination failure retains another; 390 px has no overflow and keyboard focus is visible.

- [ ] **Step 7: Verify Phase 4**

  Run current map, commute, demographics, geocoding-race tests and new E2E plus typecheck/lint.

**Dependency:** Phase 1 and Commute closure.

**User-visible outcome:** Users inspect one property map, meaningful nearby evidence, saved commute destinations, and area context in one view.

**Rollback boundary:** Controlled wrappers can be removed while standalone Location, Map, and Commute components remain intact.

## Phase 5: Risk & Environment

**Scope:** Unify environmental/geological evidence into one map and ordered evidence table while preserving independent layer semantics and advanced parcel/satellite detail.

**Files:**

- Create: `frontend_next/lib/workspace/risk-evidence-model.ts`
- Create: `frontend_next/components/workspace/risk/risk-environment-view.tsx`
- Create: `frontend_next/components/workspace/risk/risk-evidence-map.tsx`
- Create: `frontend_next/components/workspace/risk/risk-evidence-table.tsx`
- Create: `frontend_next/components/workspace/risk/manual-checklist.tsx`
- Modify: `frontend_next/components/terrain-risk-analysis.tsx` to expose controlled layer results without one monolithic presentation
- Reuse: terrain/cadastral Leaflet map, `SatelliteEvidence`, terrain reference evidence
- Modify after closure merge: geological-sensitivity contracts and `lib/api.ts`
- Modify: `frontend_next/app/workspace/[caseId]/risk/page.tsx`
- Test: `frontend_next/lib/workspace/risk-evidence-model.test.mjs`
- Test: `frontend_next/e2e/commercial-workspace-risk.spec.ts`

**Interfaces:**

- Produces one `RiskEvidenceRow` per layer with `finding`, `matchOrDistance`, `state`, `coverage`, `observedAt`, `nextCheck`, and optional map geometry/reference.
- Ordering is matched concern → unknown/partial → observed clear/no-match → unavailable/not-assessed.

- [ ] **Step 1: Wait for and review Geological Sensitivity closure**

- [ ] **Step 2: Write risk model tests for every layer state**

  Distinguish matched, no match, covered, not covered, unknown, partial, unavailable, not assessed, and stale. Assert there is no aggregate numeric safety score.

- [ ] **Step 3: Adapt terrain results into independent evidence rows**

  Preserve parcel-point limitations, satellite non-statutory notice, source dates, and layer-specific retry.

- [ ] **Step 4: Implement evidence map, ordered table, and manual checks**

  Provider/agency metadata appears only in row details/source disclosure.

- [ ] **Step 5: Add partial-provider E2E tests**

  Fail flood while landslide/geological/satellite remain; assert unknown is not displayed as safe and retry touches only flood.

- [ ] **Step 6: Verify Phase 5**

  Run current terrain, parcel, satellite tests and new risk tests plus typecheck/lint.

**Dependency:** Phase 1 and Geological Sensitivity closure.

**User-visible outcome:** One explainable risk investigation view shows matched evidence, unknowns, coverage/date, and manual checks without a safety score.

**Rollback boundary:** The unified adapter/view can be removed while `TerrainRiskAnalysis` and its current routes remain operational.

## Phase 6: Finance & Transaction

**Scope:** Combine price basis, loan, cash required, monthly holding cost, conditional affordability, sensitivity, and contextual tax.

**Files:**

- Create: `frontend_next/lib/workspace/finance-model.ts`
- Create: `frontend_next/components/workspace/finance/finance-transaction-view.tsx`
- Create: `frontend_next/components/workspace/finance/finance-summary.tsx`
- Create: `frontend_next/components/workspace/finance/cost-composition.tsx`
- Create: `frontend_next/components/workspace/finance/finance-assumptions.tsx`
- Create: `frontend_next/components/workspace/finance/transaction-tax-details.tsx`
- Modify: `frontend_next/components/loan-calculator.tsx` for controlled inputs/results
- Modify after closure merge: `frontend_next/components/holding-cost-calculator.tsx` and related view models
- Extract: TaxOracle from `app/page.tsx` into `components/taxoracle/taxoracle.tsx`
- Modify: `frontend_next/app/workspace/[caseId]/finance/page.tsx`
- Test: `frontend_next/lib/workspace/finance-model.test.mjs`
- Test: `frontend_next/e2e/commercial-workspace-finance.spec.ts`

**Interfaces:**

- Consumes the active price basis and independent loan/holding/tax slices.
- Produces `FinanceSummaryModel { cashRequired, monthlyPayment, monthlyKnownHoldingCost, unestimatedCosts, affordability }`; `affordability.status` is `not_assessed` unless income is present.

- [ ] **Step 1: Review final Valuation/Holding reliability contract**

- [ ] **Step 2: Write finance-model unit/absence tests**

  Cover each price basis, no income, zero/invalid input, unestimated costs, loan-only, holding-only, stale result after basis change, and explicit units.

- [ ] **Step 3: Adapt Loan and Holding Cost to controlled case state**

  Preserve current visual panels and sensitivity charts; stop new workspace views from relying on session events.

- [ ] **Step 4: Extract and contextualize TaxOracle**

  Keep standalone advanced access but remove it from primary navigation. Show it only when the transaction scenario calls for it or the user opens transaction details.

- [ ] **Step 5: Implement summary, composition, assumptions, and sensitivity**

  Display calculation completion separately from affordability assessment.

- [ ] **Step 6: Add E2E scenarios**

  Assert missing income never yields affordable/unaffordable; changing price basis invalidates dependent finance only; TaxOracle failure leaves loan/holding results.

- [ ] **Step 7: Verify Phase 6**

  Run reliability, tax human-presentation, new finance E2E, typecheck, and lint.

**Dependency:** Phase 1, Phase 3 active price basis, and Valuation/Holding closure.

**User-visible outcome:** Users understand cash required, monthly known cost, assumptions, missing costs, sensitivity, and conditional affordability in one place.

**Rollback boundary:** Controlled wrappers can fall back to current calculators; tax stays available through Advanced tools.

## Phase 7: Compare and Report integration

**Scope:** Replace weighted ranking with explainable case differences, add a route-backed compare flow, and create one case report/print model.

**Files:**

- Create: `frontend_next/lib/workspace/comparison-model.ts`
- Create: `frontend_next/lib/workspace/report-model.ts`
- Create: `frontend_next/components/compare/case-picker.tsx`
- Create: `frontend_next/components/compare/case-comparison-view.tsx`
- Create: `frontend_next/components/workspace/report/case-report.tsx`
- Create: `frontend_next/components/workspace/report/case-report.module.css`
- Modify: `frontend_next/app/compare/page.tsx`
- Modify: `frontend_next/app/workspace/[caseId]/report/page.tsx`
- Modify: `frontend_next/components/case-manager.tsx` to link to compare route
- Deprecate after parity: ranking portions of `lib/case-comparison.ts`, old valuation HTML export, duplicated decision report exports
- Test: `frontend_next/lib/workspace/comparison-model.test.mjs`
- Test: `frontend_next/lib/workspace/report-model.test.mjs`
- Test: `frontend_next/e2e/commercial-workspace-compare-report.spec.ts`

**Interfaces:**

- `buildComparisonModel(cases)` produces aligned metrics, deterministic material differences, missing/non-comparable states, and no rank fields.
- `buildCaseReport(workspace)` produces the nine report sections and source/date notes without internal diagnostics.

- [ ] **Step 1: Write comparison tests before replacing ranking**

  Cover 1/2/3/4 cases, duplicates, missing values, unlike price bases, material 10% financial deltas, 10-minute commute deltas, risk-state differences, and no score/winner fields.

- [ ] **Step 2: Implement compare route, picker, grouped desktop and mobile views**

  The URL contains safe case IDs; invalid/unauthorized IDs are reported individually without breaking valid cases.

- [ ] **Step 3: Write report-model tests**

  Assert all nine sections, current revision, unknowns, checklist, dates, and absence of internal terms/IDs/API paths.

- [ ] **Step 4: Implement report route and print stylesheet**

  Hide application chrome and controls in print; preserve headings, units, table headers, evidence states, and page-break-safe blocks.

- [ ] **Step 5: Add route, mobile, and print E2E coverage**

  Test compare deep link/refresh, responsive metric grouping, report refresh, print media snapshot/DOM, and client-readable terminology.

- [ ] **Step 6: Retire old ranking/export entry points after parity**

  Keep compatibility functions for one release only if existing saved links require them; label them deprecated and add removal issue.

- [ ] **Step 7: Verify Phase 7**

  Run comparison/report current and new tests, typecheck, lint, production build, and `git diff --check`.

**Dependency:** Phases 1–6 provide normalized evidence; the report may ship with explicit unavailable sections while later domains are still gated.

**User-visible outcome:** Users compare 2–3 cases through material differences and print a professional current-case report.

**Rollback boundary:** New routes are removable without changing stored cases; current comparison/export components remain until final acceptance.

## Phase 8: Entry cutover, responsive, accessibility, and commercial acceptance

**Scope:** Add the three entry paths, cut global navigation to the commercial IA, complete 390 px/accessibility behavior, and retire obsolete primary shells only after full regression.

**Files:**

- Create: `frontend_next/components/workspace/entry/address-entry.tsx`
- Create: `frontend_next/components/workspace/entry/property-confirmation.tsx`
- Modify: `frontend_next/app/page.tsx` to become the entry/recent-case page
- Modify: `frontend_next/app/properties/new/page.tsx`
- Modify: `frontend_next/app/explore/page.tsx`
- Modify: `frontend_next/app/cases/page.tsx`
- Modify: `frontend_next/components/property-finder.tsx` to hand off into confirmation/case creation
- Modify: `frontend_next/components/app-shell.tsx`, `sidebar.tsx`, `topbar.tsx`, and `app/globals.css`
- Modify/deprecate: guided-journey presentation shells and old root `AppPage` navigation
- Test: `frontend_next/e2e/commercial-entry-paths.spec.ts`
- Test: `frontend_next/e2e/commercial-workspace-mobile.spec.ts`
- Test: `frontend_next/e2e/commercial-workspace-accessibility.spec.ts`
- Test: `frontend_next/e2e/commercial-language.spec.ts`

**Interfaces:**

- Known-address confirmation creates/attaches a case then returns its canonical Overview URL.
- Property Finder selection uses the same confirmation contract.
- Saved case selection routes directly to the case Overview.

- [ ] **Step 1: Write the three entry-path tests**

  Known address must never require Property Finder; exploration must remain independent; saved-case selection must open Overview in one action.

- [ ] **Step 2: Implement entry and confirmation flows**

  Show entered/normalized identity, mismatch/candidate states, and the explicit confirmation action. Do not auto-run all analyses.

- [ ] **Step 3: Cut over global navigation**

  Primary shell links to Home/Saved Cases and case routes. Move TaxOracle, Aegis, pilot, evidence, and technical identity review under Advanced/internal routes.

- [ ] **Step 4: Write and pass 390×844 tests for every primary workflow**

  Check header, nav chips, maps, tables, comparison, forms, evidence disclosures, sticky CTA, keyboard focus, and no body overflow.

- [ ] **Step 5: Complete accessibility tests and fixes**

  Validate landmarks, heading order, route-change focus, current-page semantics, dialog/sheet focus containment, escape behavior, live error announcements, chart/table alternatives, and reduced motion.

- [ ] **Step 6: Add professional-language scan**

  Scan primary visible text for forbidden API/HTTP/internal/provider implementation terms while allowing bounded source-note regions.

- [ ] **Step 7: Remove obsolete primary presentation shells**

  Remove only after route parity: root `setPage` navigation, duplicate journey headers/status/readiness panels, standalone Market/Map/Valuation/Terrain/Tax primary nav items, rank cards, and old dashboard narrative. Retain domain components and advanced/internal routes.

- [ ] **Step 8: Run full commercial acceptance**

  Run: `cd frontend_next; npm run typecheck; npm run lint; npm run build; npm run test:e2e`

  Also run targeted real-provider/hosted suites required by the release workflow and `git diff --check` from repository root.

**Dependency:** Phases 1–7 and all four closure merges.

**User-visible outcome:** The product opens with a single commercial promise, supports all three entry situations, and delivers the full case workspace on desktop and mobile.

**Rollback boundary:** Keep a release flag that routes Home to the legacy journey for one release. The new workspace routes and repository remain readable so rollback does not lose case data.

## Final acceptance matrix

| Requirement | Owning phase/test |
|---|---|
| Known address bypasses Finder | Phase 8 `commercial-entry-paths.spec.ts` |
| Same property across surfaces | Phase 1 property-context E2E |
| Selective property-change invalidation | Phase 1 invalidation unit/E2E |
| Local provider failure | Phase 1 boundary plus Phases 3–6 domain E2E |
| Explicit units | Phases 3, 6, and 7 model/E2E |
| Save and reopen | Phase 1 adapter/repository and routing E2E |
| Meaningful 2–3 case compare | Phase 7 comparison tests |
| Client-readable report | Phase 7 report/print tests |
| Back/Forward/deep link/refresh | Phase 1 routing E2E |
| 390 px workflows | Phase 8 mobile suite |
| Professional language | Phase 8 language scan |

## Final verification and handoff

- [ ] Confirm all phase-specific closure branches are merged and no planned adapter contradicts their contracts.
- [ ] Run the full frontend typecheck, lint, production build, E2E, hosted/real-provider suites required by release policy, and `git diff --check`.
- [ ] Inspect `git status --short` and verify only intended implementation/docs/tests changed.
- [ ] Review the product manually at 1440×900 and 390×844 for all three entry paths and five sections.
- [ ] Verify a saved case can be reopened after browser refresh and a local provider outage.
- [ ] Verify comparison contains no winner/rank/score and Risk contains no safety score.
- [ ] Verify print preview contains no application chrome, controls, API paths, internal IDs, or engineering diagnostics.
- [ ] Record any retained legacy compatibility code and its removal issue before enabling the commercial route by default.
