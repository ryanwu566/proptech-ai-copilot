# Commercial UX Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a case-first commercial property workspace that preserves current provider capability, maintains one reliable property context, exposes truthful evidence and units, supports local failure recovery, and passes broker-pilot acceptance on desktop and 390 px mobile.

**Architecture:** A route-scoped browser-case repository supplies one `JourneyPropertyIdentityAnchorV1`, assumptions, and independent evidence slices to five primary views under `/cases/[caseId]/[section]`. Typed presentation adapters separate query, evidence, completeness, risk, identity, and task-readiness states; shared design primitives render those contracts. The authenticated VNext `/workspace/[caseId]` route remains separate. Compare is cross-property and Report is a current-case output.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5, Tailwind CSS 3/CSS Modules, current REST and VNext identity clients, Node tests, Playwright, Leaflet/React Leaflet.

**Spec:** `docs/superpowers/specs/2026-09-27-commercial-ux-master-architecture.md`

## Global Constraints

- Do not change provider truth, calculations, or persistence schemas inside presentation epics unless the owning engineering closure explicitly requires it.
- Primary workspace views are exactly Overview, Market & Price, Location & Commute, Risk & Environment, and Finance & Costs.
- Compare is limited to two or three cases and contains no rank, winner, top candidate, or composite score.
- Report is a current saved case revision and uses browser print for v1.
- Query, evidence, completeness, risk, identity, and task readiness remain independent.
- Missing/unavailable financial values never become zero; all financial values state currency, unit, period, and basis.
- Every result commit is guarded by case revision and input fingerprint; stale responses are discarded.
- Provider and evidence failures are local and preserve unrelated valid evidence.
- Existing production providers, calculations, case compatibility, authenticated VNext boundaries, and API contracts are non-regression requirements.
- At 390×844 there is no document-level horizontal overflow and the document is the only normal vertical scroll owner.
- No implementation branch begins from the documentation branch. Each begins from the then-current integrated `origin/main` SHA after required predecessors merge.
- E1 cannot begin until this documentation branch has been reviewed and merged through the repository's normal process; this plan does not authorize that merge now.

## Review Focus

1. Property identity changes during an in-flight request: the old result cannot attach to the new revision.
2. Legacy reopened cases without compacted detail: summaries are labeled limited and missing detail is not reconstructed.
3. Missing area, income, or cost input: the UI shows the exact missing reason and never a silent zero or affordability conclusion.
4. Query success with no match/no coverage: evidence and risk remain explicitly non-equivalent to safety.
5. Compare/report across different price bases, stale evidence, and partial provider availability: non-comparable/unknown states remain visible and client-safe.

---

## 1. Prerequisite engineering closures

Current closure tips observed during this review:

| Closure | Current branch tip | Shared files | Commercial gate |
|---|---|---|---|
| Geological Sensitivity | `39e6e723f3f14fbf99f2d7fb32d3e7235948b536` | Backend terrain service/provider/tests; no direct frontend delta yet | Risk model waits for final layer/result contract |
| Valuation / Holding Cost reliability | `dbc196a34a038e9493a17ee8ffc2181119ac9c66` | `app/page.tsx`, `lib/api.ts`, `closed-loop-journey.ts`, `property-case.ts`, `risk-summary.ts`, valuation/holding files | Market/Price, Finance, state/unit adapters wait |
| Commute production closure | `f360e37dcae0bc29777daec8f2ab0236d082f25a` | `app/page.tsx`, `lib/api.ts`, `case-storage.ts`, `closed-loop-journey.ts`, `property-case.ts`, guided Location files | Location & Commute waits |
| Journey Property Identity closure | `8da030f089dd806225989c66a795a98781bf05f6` | `app/page.tsx`, `case-storage.ts`, `closed-loop-journey.ts`, guided stages | Browser-case repository/header/shell cutover waits; it does not supply a durable VNext entity |

Recommended closure merge order:

1. **Geological Sensitivity** — mostly backend-isolated; establishes the risk contract with the least shared-file disruption.
2. **Valuation / Holding Cost reliability** — highest financial truth impact; establishes canonical monetary/null behavior before other shared-state integrations.
3. **Commute production closure** — rebase/merge onto reliability so shared `api`, journey, case, and page code resolves against the new financial contracts.
4. **Journey Property Identity closure** — rebase/merge last among closures so its browser journey anchor and invalidation changes incorporate the final commute and financial case fields. Do not relabel the anchor as a VNext entity.

Each closure must pass its own focused tests plus repository-required typecheck/lint before the next shared-file closure is rebased. Do not rebase an active branch after review has begun without coordinating with its owner; prefer a fresh integration branch or merge-main workflow agreed by the repository.

## 2. Dependency graph and allowed parallelism

```text
Geological ─┐
Reliability ├─> Commute ─> Identity ─> E1 State contracts ─┬─> E2 Design foundations
            │                                               └─> E3 Workspace repository/shell
            └──────────────────────────────────────────────────────────────┐

E2 + E3 ─> E4 Market & Price ─> E7 Finance & Costs ─┐                     │
        ├> E5 Location & Commute ────────────────────┼─> E8 Overview/Save ├─> E9 Compare/Report
        └> E6 Risk & Environment ────────────────────┘                     │
E3 + E4..E9 ─> E10 Entry/Mobile/Acceptance ─> hosted acceptance ─> broker pilot
                                      └─> E11/E12 pilot-driven P1 work
```

Safe parallel work:

- E1 and isolated parts of E2 may run in parallel after all closure contracts are inspected.
- After E2 and E3 merge, E4, E5, and E6 may run in parallel only when each branch owns new domain files and does not independently edit `app/page.tsx`, shared copy registries, or shared UI adapters.
- E7 waits for E4's active-price interface. E8 waits for normalized evidence from E4–E7. E9 waits for E8 and normalized case snapshots.
- E10 is sequential and owns root entry, global navigation, release flag, and broad responsive acceptance.

## 3. Priority model

| Priority | Meaning | Epics |
|---|---|---|
| P0 | Required before a credible commercial MVP pilot/demo | E1–E10 |
| P1 | Valuable after MVP evidence; does not block the first controlled pilot | E11 Advanced evidence/diagnostics; E12 pilot-driven report and workflow refinements |
| P2 | Cleanup or expansion after repeated-use proof | E13 legacy-shell removal and portfolio/enterprise follow-ups |

P0 is large because the source pilot explicitly requires the end-to-end loop; P1/P2 are deliberately excluded from the gate so the label is not inflated.

## 4. Epic plan

### E1 — Commercial state, language, and numeric contracts (P0)

**Purpose / value:** Give every domain the same truthful state axes and unit grammar before layouts migrate.
**Branch:** `feat/commercial-state-contract-v1`
**Files:** create `frontend_next/lib/commercial/state.ts`, `state.test.mjs`, `formatters.ts`, `formatters.test.mjs`, `provenance.ts`, `readiness.ts`; adapt `lib/experience-architecture.ts`, `market-result-state.ts`, `valuation-result-state.ts`, `property-case-evidence.ts`; do not yet mass-edit pages.
**Dependencies:** all four closure contracts inspected; final formatter fields use Reliability.
**Backend changes:** none.
**Conflict risk:** HIGH in state adapters; LOW in new files.
**Tests:** full state truth table; null/zero/negative boundaries; `999/1000 m`; `59/60 min`; prices/bases; periods; provenance layer serialization; named readiness.
**Acceptance:** no generic presentation `status`; no missing-as-zero; all axes and zh-TW labels match the master spec.
**Rollback:** new adapters can be removed while current domain enums remain intact.

- [ ] Write failing state/formatter/provenance/readiness tests.
- [ ] Implement pure types and formatters without production callers.
- [ ] Add compatibility mappings for current enums.
- [ ] Run Node tests, `npm run typecheck`, `npm run lint`, and `git diff --check`.

### E2 — Essential commercial design foundations (P0)

**Purpose / value:** Establish semantic tokens and accessible primitives without a page-wide class rewrite.
**Branch:** `feat/commercial-design-foundations-v1`
**Files:** create `app/design-tokens.css`; create focused components under `components/design-system/` for button, field/unit input, status, message, async state, section/panel, summary strip, disclosure, data table, chart frame, map frame, navigation; modify `app/globals.css`, `tailwind.config.ts`, `components/ui.tsx`, `components/product-ui.tsx` as compatibility adapters.
**Dependencies:** E1 semantic roles.
**Backend changes:** none.
**Conflict risk:** HIGH in global CSS/shared primitives; keep adoption narrow.
**Tests:** token contract, component accessibility, status grayscale/no-color semantics, numeric alignment, long locale fixtures.
**Acceptance:** one action color; no default shadow; 6/8/12 px radius rules; 40/44 px controls; no semantic raw palette in new primitives.
**Rollback:** legacy exports continue to render; remove token import and adapters.

- [ ] Add tokens/formatters fixture with no intentional product-page change.
- [ ] Add compatibility adapters one primitive at a time.
- [ ] Verify focus, contrast, reduced motion, and long zh-TW/EN/JA/KO text.
- [ ] Run typecheck, lint, focused component/E2E tests, and diff check.

### E3 — Browser-case repository, identity anchor, routes, and property shell (P0)

**Purpose / value:** Make one browser-saved case and journey-anchor revision the explicit v1 UI scope and make navigation URL-native without weakening VNext authorization.
**Branch:** `feat/commercial-workspace-foundation-v1`
**Files:** create `lib/workspace/workspace-model.ts`, `case-repository.ts`, `legacy-case-adapter.ts`, `invalidation.ts`; create `components/workspace/workspace-shell.tsx`, `workspace-navigation.tsx`, `property-context-header.tsx`, `evidence-state-boundary.tsx`; add `app/cases/[caseId]/layout.tsx` and section routes under `app/cases/[caseId]/`; modify the existing `app/cases/[caseId]/page.tsx`, `lib/case-storage.ts`, `lib/closed-loop-journey.ts`, and landed `journey-property-identity.ts` only through adapters. Do not modify or redirect the authenticated, feature-gated `app/workspace/[caseId]/page.tsx` in this epic.
**Dependencies:** Identity closure, E1; E2 for final rendering.
**Backend changes:** none. `SavedCase.id` is an opaque browser-case route key. A VNext bridge is P2 and requires a separate case-ID mapping, authentication, authorization, redirect, and data-migration contract.
**Conflict risk:** VERY HIGH.
**Tests:** repository CAS/fingerprint tests, legacy compaction migration, address/coordinate/price invalidation matrix, route redirect/deep link/Back/Forward, unauthorized case, local boundary.
**Acceptance:** same browser case and bounded journey anchor across five routes; stale responses rejected; saved summaries reopen honestly; old root flow still works; VNext route tests remain unchanged.
**Rollback:** remove new nested routes/provider; retain `/`, `/cases/[caseId]`, and current professional shell.

- [ ] Define repository interfaces and failing invalidation/legacy tests.
- [ ] Implement storage-independent repository and identity adapter.
- [ ] Add layout/header/navigation/local evidence boundary.
- [ ] Prove route refresh and Back/Forward behavior before domain composition.

### E4 — Market & Price (P0)

**Purpose / value:** Put asking price, transaction-based estimate, observed market evidence, and active finance basis in one trustworthy view.
**Branch:** `feat/commercial-market-price-v1`
**Files:** extract root-defined Market/Valuation from `app/page.tsx` into `components/market/market-insight.tsx` and `components/valuation/valuation-analysis.tsx`; create `components/workspace/market/*`; modify `app/cases/[caseId]/market/page.tsx`, `market-segmentation-panel.tsx`, valuation visuals, `lib/valuation-share.ts`; consume landed `lib/monetary-units.ts` if Reliability provides it.
**Dependencies:** Reliability closure, E1–E3.
**Backend changes:** none.
**Conflict risk:** VERY HIGH in `app/page.tsx`; extraction is a dedicated first commit and preserves legacy imports/test IDs.
**Tests:** market/valuation independent failure, no data/limited/stale, price bases, comparable units, late response, 390 px table strategy.
**Acceptance:** comparable table is primary; estimate never reads as official appraisal; missing values are explicit; legacy route retains behavior.
**Rollback:** new route renders extracted legacy blocks or is feature-flagged off.

### E5 — Location & Commute (P0)

**Purpose / value:** Reuse one confirmed location for map, POIs, routes, and demographics.
**Branch:** `feat/commercial-location-commute-v1`
**Files:** create `lib/workspace/location-context.ts`, `components/workspace/location/*`; modify `location-insight.tsx`, `map/geo-map.tsx`, landed `commute-evidence-panel.tsx`, `commute-route-card.tsx`, `commute-livability-card.tsx`, and `app/cases/[caseId]/location/page.tsx`.
**Dependencies:** Commute closure, E1–E3.
**Backend changes:** none; consume the final route contract.
**Conflict risk:** HIGH in guided Location and map integration; this branch does not edit guided stage composition.
**Tests:** shared geocode/deduplication, rejected geocode, two destinations, local route failure, origin change invalidation, attribution, map/list synchronization, mobile gestures/focus.
**Acceptance:** map is dominant; route failures do not remove location evidence; demographics remain secondary; no competing geocodes.
**Rollback:** controlled wrappers removed; existing standalone components remain.

### E6 — Risk & Environment (P0)

**Purpose / value:** Present each environmental layer as explainable evidence with coverage, date, and next check.
**Branch:** `feat/commercial-risk-environment-v1`
**Files:** create `lib/workspace/risk-evidence-model.ts`, `components/workspace/risk/*`; modify `terrain-risk-analysis.tsx` to expose controlled results, reuse terrain/cadastral map and `satellite-evidence.tsx`; modify `surface-copy.ts` through E1 adapters and `app/cases/[caseId]/risk/page.tsx`.
**Dependencies:** Geological closure, E1–E3.
**Backend changes:** none; map final backend layer states without changing them.
**Conflict risk:** HIGH in terrain presentation; LOW in backend.
**Tests:** every matched/no-match/no-coverage/unavailable/stale state per layer; flood-only failure; geological unavailable; no aggregate score; parcel-point limitation; mobile map/table.
**Acceptance:** unknown never appears safe; available layers survive a sibling failure; source details are secondary; manual checks are actionable.
**Rollback:** unified adapter/view removed; current Terrain surface remains.

### E7 — Finance & Costs (P0)

**Purpose / value:** Explain cash required, monthly payment, known holding cost, missing categories, sensitivity, and preliminary tax scope.
**Branch:** `feat/commercial-finance-costs-v1`
**Files:** create `lib/workspace/finance-model.ts`, `components/workspace/finance/*`; modify `loan-calculator.tsx`, `holding-cost-calculator.tsx`, finance visual models, `taxoracle-presentation.ts`; extract root TaxOracle to `components/taxoracle/taxoracle.tsx`; modify `app/cases/[caseId]/finance/page.tsx`.
**Dependencies:** Reliability closure, E1–E4.
**Backend changes:** none.
**Conflict risk:** VERY HIGH around units/null handling and `app/page.tsx`; Tax extraction is isolated and legacy-compatible.
**Tests:** each price basis, missing area/income/cost, valid zero, basis change, stale results, Tax failure isolation, explicit periods and units.
**Acceptance:** calculation completion and affordability remain separate; unestimated costs are named; TaxOracle is contextual and preliminary.
**Rollback:** controlled wrappers fall back to current calculators; Tax remains under Advanced.

### E8 — Overview, next actions, save and reopen (P0)

**Purpose / value:** Give the broker one evidence-backed preparation cockpit and reusable case loop.
**Branch:** `feat/commercial-overview-save-v1`
**Files:** create `lib/workspace/overview-model.ts`, `components/workspace/overview/*`; modify Overview route, `case-manager.tsx`, repository save state, selected parts of `decision-summary.ts`, `risk-summary.ts`, property-case models; do not reuse `overallScore`.
**Dependencies:** E3–E7 normalized evidence.
**Backend changes:** none; browser-local persistence remains explicit. Durable/team persistence requires a later approved contract.
**Conflict risk:** HIGH in overlapping decision/readiness models.
**Tests:** optional unopened modules, identity conflict, missing area/price, valuation failure with market available, stale risk, save failure, refresh/reopen, exact next-action links.
**Acceptance:** maximum five findings/actions; blockers are task-specific; saved case restores identity, assumptions, evidence states, and honest freshness.
**Rollback:** simple case summary replaces Overview while repository remains readable.

### E9 — Compare and Report (P0)

**Purpose / value:** Support material cross-case decisions and client discussion without declaring a winner.
**Branch:** `feat/commercial-compare-report-v1`
**Files:** create `lib/workspace/comparison-model.ts`, `report-model.ts`, `components/compare/*`, `components/workspace/report/*`, `app/compare/page.tsx`, report route; modify `case-manager.tsx`; deprecate ranking portions of `lib/case-comparison.ts`, `lib/property-comparison.ts`, ranking cards, duplicate export paths, and valuation-led HTML only after parity.
**Dependencies:** E3, E8, normalized evidence from E4–E7.
**Backend changes:** none.
**Conflict risk:** MEDIUM/HIGH in persisted snapshots and current comparison/report components.
**Tests:** one/two/three/four cases, duplicates, unauthorized IDs, unlike bases, missing values, material deltas, current revision, nine report sections, forbidden diagnostics, print media, mobile metric-first layout.
**Acceptance:** no score/rank/winner fields; non-comparable values are explicit; report is source/date aware and client-readable.
**Rollback:** new routes disabled; old exports retained for one release.

### E10 — Entry cutover, responsive/accessibility, and commercial acceptance (P0)

**Purpose / value:** Complete the three entry paths and prove the commercial experience on the hosted candidate.
**Branch:** `feat/commercial-entry-acceptance-v1`
**Files:** create `app/properties/new/page.tsx`, `app/explore/page.tsx`, `app/cases/page.tsx`, entry components; modify `app/page.tsx` to entry/recent cases only, `property-finder.tsx`, `app-shell.tsx`, `sidebar.tsx`, `topbar.tsx`, `globals.css`, Playwright specs and acceptance docs.
**Dependencies:** E1–E9 and all closure merges.
**Backend changes:** none expected.
**Conflict risk:** VERY HIGH; this is the only epic that owns global cutover and broad shell composition.
**Tests:** all three entries; full acceptance matrix in §7; viewport matrix; keyboard/focus/reduced motion; professional-language scan; production build; hosted/real-provider suites in approved environment.
**Acceptance:** commercial release flag passes full gate; legacy root remains a one-release rollback target.
**Rollback:** switch Home to legacy journey; new case routes remain readable so no saved context is lost.

### E11 — Advanced evidence, methodology, and diagnostics (P1)

**Purpose / value:** Improve expert traceability after the primary flow proves useful.
**Branch:** `feat/commercial-advanced-evidence-v1`
**Files:** advanced source/diagnostic disclosures, VNext identity review, cadastral detail, Tax rule trace, support reference surfaces.
**Dependencies:** E10 and pilot findings.
**Backend changes:** only if a missing authorized support read is separately approved.
**Risk:** MEDIUM.
**Acceptance:** diagnostics never leak into primary results; authorization and source attribution remain intact.
**Rollback:** hide Advanced routes/disclosures.

### E12 — Pilot-driven workflow/report refinements (P1)

**Purpose / value:** Implement only repeated broker evidence, such as editable report wording or faster return-use actions.
**Branch:** `feat/commercial-pilot-refinements-v1`
**Files:** determined from observation matrix; likely Overview, recent cases, Compare, and Report only.
**Dependencies:** six valid pilot sessions and roadmap review.
**Backend changes:** separate approval if durable collaboration is actually evidenced.
**Risk:** LOW/MEDIUM when kept evidence-bound.
**Acceptance:** every change maps to an observed repeated pattern and a measurable rerun criterion.
**Rollback:** revert the bounded refinement without changing contracts.

### E13 — Legacy removal and post-proof expansion (P2)

Remove root `setPage`, duplicate journey/readiness panels, compatibility exports, old ranking/export code, and obsolete CSS only after one stable release and `rg` proves zero consumers. Portfolio, CRM, documents, permissions, AI chat, server PDF, and >3-property analysis require separate validated specs.

## 5. Branch and worktree strategy

- Use one isolated worktree per active epic; never reuse the four closure worktrees.
- Branch names are exactly those listed per epic unless repository owners rename them before creation.
- Record `git status --short`, branch, HEAD, `origin/main`, and required predecessor merge SHAs before editing.
- Base each branch on the current `origin/main` after all required predecessors merge; record that base SHA in the PR description and plan execution notes.
- Parallel E4/E5/E6 branches must not edit shared root composition or shared locale registries. A small sequential integration branch owns those joins after domain branches merge.
- Refresh from main before first substantive edit and again before review if predecessor contracts changed. Do not repeatedly rebase branches under active review; merge current main or create a fresh successor branch according to repository policy.
- Do not copy uncommitted files from another worktree. Resolve conflicts from committed branch output only.

## 6. One recommended merge sequence

1. **After this review only**, merge `docs/commercial-ux-integration-v1` through the normal repository process so all approved source documents and these three master contracts are present on main. No merge is performed by this task.
2. `feat/geological-sensitivity-etl-v1` — establishes the new risk evidence contract with low frontend collision.
3. `fix/valuation-holding-reliability-v2` — closes financial truth and unit/null handling before commercial adapters.
4. `fix/commute-production-closure-v1` — integrates route independence/provenance onto the reliability baseline.
5. `feat/property-identity-production-closure-v1` — makes the browser journey anchor/revalidation contract authoritative after other case fields stabilize.
6. `feat/commercial-state-contract-v1` — freezes presentation axes, provenance, readiness, and units.
7. `feat/commercial-design-foundations-v1` — supplies tokens/primitives without route cutover.
8. `feat/commercial-workspace-foundation-v1` — establishes browser-case route/repository/header ownership while leaving VNext unchanged.
9. `feat/commercial-market-price-v1` — extracts the largest root modules and establishes active price basis.
10. `feat/commercial-location-commute-v1` — consumes final commute/location contracts.
11. `feat/commercial-risk-environment-v1` — consumes final geological and terrain contracts.
12. `feat/commercial-finance-costs-v1` — consumes active price and reliability contracts.
13. `feat/commercial-overview-save-v1` — synthesizes stabilized domain evidence and completes reuse.
14. `feat/commercial-compare-report-v1` — aligns normalized case snapshots and creates outputs.
15. `feat/commercial-entry-acceptance-v1` — owns global cutover, mobile/accessibility closure, and release flag.
16. Hosted commercial acceptance; then six-session broker pilot.
17. P1 branches only from documented pilot findings.

This order optimizes correctness and regression safety: truth contracts precede presentation; case identity precedes routing; domains precede synthesis; synthesis precedes cross-case/output; global cutover comes last.

## 7. Acceptance test matrix

| Gate | Required invariant | Primary owner |
|---|---|---|
| Desktop | Five views, one property header, one primary action per section, no card soup | E2–E10 visual/E2E |
| 390 px | No body overflow; 44 px controls; maps/tables/forms/compare/report usable | E10 mobile suite |
| Known address | Address → confirmation → Overview without Finder | E10 entry spec |
| Area exploration | Candidate uses same confirmation/case contract | E10 entry spec |
| Property identity | Same revision across routes; conflict blocks unsafe synthesis | E3 identity/property-context spec |
| Market | Scope, period, sample, units, no-data/partial/stale explicit | E4 market spec |
| Valuation | Range/comparables/confidence; malformed/null local failure | Reliability + E4 |
| Location | One accepted geocode; map tied to active property | E5 location spec |
| Commute | Origin/destination/mode/time basis; local route failure | Commute closure + E5 |
| Risk | Layer independence; no-match/no-coverage/unavailable distinct | Geological closure + E6 |
| Finance | Basis, cash, monthly/annual units; missing costs named | Reliability + E7 |
| Decision | Findings/unknowns/blockers/actions; no overall score | E8 overview spec |
| Save/reopen | Identity, assumptions, compact evidence state/freshness restored honestly | E3/E8 repository spec |
| Compare | 2–3 cases, same-basis alignment, no winner/rank | E9 compare spec |
| Report | Current revision, nine sections, known/estimated/unknown, browser print | E9 report spec |
| Property switch | Invalidation preview; old results stale/cleared by matrix | E3 invalidation E2E |
| Price change | Only dependent finance/tax/decision/report recompute/stale | E3/E7/E8 |
| Missing area | Area-dependent costs unestimated, never zero | Reliability + E7 |
| Valuation failure | Other domains remain usable; alternative basis available | E4 |
| Commute failure | Map/location remain; failed route locally retryable | E5 |
| Risk partial coverage | Available layers remain; unknown never reads safe | E6 |
| Identity revalidation | Persistent header warning; report blocked until safe | E3/E8/E9 |
| Back/Forward | Correct route/header/context; no silent committed-state loss | E3/E10 |
| Language | No raw API/HTTP/enums/English fragments in primary zh-TW | E1/E10 contract scan |
| Units | Every comparable value has basis/unit/period; missing != zero | E1 + domain specs |
| Visual hierarchy | Testable criteria in §8 | E2/E10 screenshots/manual review |
| Accessibility | WCAG AA basics, focus, landmarks, native tables, reduced motion | E2/E10 accessibility spec |

Tests assert invariant behavior and fixture-controlled state, not exact live provider numbers.

## 8. Visual acceptance

- No generic card nested inside another generic card.
- No page or section has competing filled primary buttons.
- No ambiguous financial, area, time, or distance unit.
- No raw provider/debug string in a primary result.
- Green appears only for completed/verified process state, never property quality or safety.
- Primary maps have minimum height 520 px on desktop and 360 px on mobile; at 390 px their width fills the 358 px content area inside 16 px gutters.
- Comparable/risk/financial evidence is aligned, readable, and keyboard navigable.
- Numbers use tabular figures; comparable numeric columns align right.
- One material warning appears at the affected result boundary; warnings are not repeated.
- Every surface has one clear primary task and one coherent reading order.
- 390 px workflows require no body-level horizontal scroll or nested vertical scroll trap.
- Keyboard focus is visible and restored after dialogs/drawers; state never relies on color alone.
- Print removes navigation/forms/buttons and remains monochrome-safe with page-break-aware evidence rows.

## 9. Production acceptance and broker-pilot handoff

- [ ] Run each epic's focused Node/Playwright tests, `npm run typecheck`, `npm run lint`, production build where relevant, and root `git diff --check`.
- [ ] Run full `npm run test:e2e`, workspace/VNext contract suites, Google map suites, and hosted/real-provider tests only in their approved environment.
- [ ] Complete `docs/commercial-acceptance-checklist-v1.md` against the exact frontend/backend SHAs and store evidence references without payloads/secrets.
- [ ] Any wrong-property carryover, missing-as-zero, unknown-as-safe, confidential-data exposure, or fabricated evidence is NO-GO.
- [ ] Recruit only after all core checklist sections pass; `PARTIAL` or `NOT TESTED` permits at most a limited pilot.
- [ ] Run six sessions using `docs/templates/broker-pilot-observation-sheet-v1.md` and keep observed behavior separate from opinion.
- [ ] Stop immediately on reproducible wrong-property, unknown-as-safe, or privacy incidents.
- [ ] Map findings to E12 using the Product Decision ↔ Pilot Evidence rules in the master architecture.
- [ ] Do not label Commercial Beta from a single-session or six-session pilot; require repeated multi-week use.

## 10. Final plan self-review

- **Coverage:** every master-spec section maps to E1–E10 or an explicit P1/P2 defer.
- **File ownership:** root composition, shared state, and global styles each have one sequential owner; parallel domains primarily create isolated files.
- **Type consistency:** E1 defines presentation axes; E3 defines repository/revision/fingerprint; E4 defines price basis; E4–E7 produce evidence consumed by E8/E9.
- **Failure coverage:** identity races, legacy compaction, provider partial failure, missing financial inputs, and incompatible comparison bases have named tests.
- **Proportion:** tasks describe decisions, interfaces, tests, acceptance, and rollback without prescribing implementation bodies.

Plan execution must wait for review of this document and the dependency matrix. No branch creation, merge, rebase, push, or production-code edit is authorized by this documentation change.
