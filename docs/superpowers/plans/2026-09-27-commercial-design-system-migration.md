# Commercial Design System Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate PropTech AI Copilot to the commercial design system without changing analytical behavior, provider truth boundaries, or calculation results.

**Architecture:** Introduce semantic tokens and narrowly scoped primitives first, then migrate shared controls/states, analytical structures, data surfaces, and finally the workspace shell. Page migrations are incremental and protected by existing contract/E2E tests plus new visual and accessibility acceptance gates. Branch-sensitive surfaces are re-audited after their feature branches merge.

**Tech Stack:** Next.js 16, React 19, TypeScript 5, Tailwind CSS 3, CSS Modules, Playwright, Node test scripts, Leaflet/React Leaflet.

**Spec:** `docs/superpowers/specs/2026-09-27-commercial-design-system-v1.md`

## Global constraints

- Do not change backend/provider contracts, calculation logic, result-state meaning, localization keys, or data retention behavior as part of visual migration.
- Green means successfully completed query/action or verified completion; it never means safe property, good investment, low hazard, or purchase recommendation.
- Unknown, unavailable, limited, and no-coverage states must never render as zero or a positive conclusion.
- Preserve `prefers-reduced-motion`, keyboard operation, focus visibility, table semantics, and existing accessible chart summaries.
- Use semantic tokens; do not introduce direct Tailwind palette colors or arbitrary hex/radius/shadow values outside the token and approved chart-palette layers.
- One dominant action per section; no nested generic card shells.
- Use tabular numerics and explicit units on comparable analytical values.
- Keep every phase shippable and reversible. Do not perform a cross-repository “big bang” class replacement.
- Before each phase, record current `git status --short`, branch, HEAD, and merged feature-branch state. Never operate on another linked worktree.

## Review focus

- **Missing or limited data:** a completed request with no coverage must look distinct from success-with-results and must not imply low risk; pin this in state and page E2E tests.
- **Mixed numerical units/locales:** `萬`, `元/月`, `坪`, `%`, dates, and data vintages must stay explicit and correctly formatted in Chinese and other supported locales; pin this in formatter/unit tests and table snapshots.
- **390 px interaction:** primary actions, unit inputs, maps, comparison, and disclosures must remain reachable without nested horizontal page scroll; pin this in Playwright viewport tests.
- **Long translated/provider content:** labels, addresses, sources, limitations, and case titles must wrap without clipping or forcing layout overflow; pin this in locale and long-content fixtures.
- **Keyboard/reduced motion:** navigation, disclosures, drawers, map controls, and dialogs must retain focus order and stop nonessential motion; pin this in accessibility-focused E2E assertions.

## Dependency order

```text
Phase 0 merged-code re-audit
  → Phase 1 tokens + foundations
    → Phase 2 controls + state primitives
      → Phase 3 section/card consolidation
        → Phase 4 tables + maps + charts
          → Phase 5 workspace shell + navigation
            → Phase 6 responsive + accessibility closure
              → Phase 7 visual regression + commercial acceptance
```

Phase 1 may begin before the named feature branches merge because it does not restructure their pages. Phase 2 may proceed for primitives without mass adoption. Phases 3–5 must honor the branch gates below.

## File map and ownership

### New foundation files proposed

- `frontend_next/app/design-tokens.css` — semantic CSS custom properties, typography, spacing, radius, surface, border, z-index, and motion tokens.
- `frontend_next/components/design-system/types.ts` — shared variant/state types only.
- `frontend_next/components/design-system/button.tsx` — button hierarchy and sizes.
- `frontend_next/components/design-system/field.tsx` — label/helper/error structure and unit adornments.
- `frontend_next/components/design-system/status-label.tsx` — fixed status semantics and icon/text contract.
- `frontend_next/components/design-system/message.tsx` — inline limitation, material warning, confirmation, error, and system message variants.
- `frontend_next/components/design-system/async-state.tsx` — typed empty/loading/error state patterns.
- `frontend_next/components/design-system/section.tsx` — unboxed section and independently stateful panel primitives.
- `frontend_next/components/design-system/summary-strip.tsx` — KPI/metric row with numeric treatment.
- `frontend_next/components/design-system/disclosure.tsx` — standard and compact disclosures.
- `frontend_next/components/design-system/data-table.tsx` — table frame/metadata/responsive hooks; it must not hide native table semantics.
- `frontend_next/components/design-system/chart-frame.tsx` — title/question/unit/period/source/empty contract without decorative default shell.
- `frontend_next/components/design-system/map-frame.tsx` — map size, controls, attribution, and selected-detail slots.
- `frontend_next/components/design-system/navigation.tsx` — selected/hover/focus behavior for workspace navigation.
- `frontend_next/lib/presentation-format.ts` — locale-aware monetary, area, percentage, duration, date, and vintage formatting.
- `frontend_next/lib/presentation-format.test.mjs` — numerical/unit behavior.

Keep these files focused. Do not create a barrel file until import churn demonstrates a need.

### Existing files with foundational changes

- `frontend_next/app/globals.css` — import token layer, base numeric/focus/reduced-motion rules, and remove obsolete animation classes only after consumers migrate.
- `frontend_next/tailwind.config.ts` — alias semantic tokens; retain compatibility aliases temporarily.
- `frontend_next/components/ui.tsx` and `frontend_next/components/product-ui.tsx` — temporary compatibility adapters, then reduction/removal after consumers migrate.
- CSS modules for professional workspace and property identity — consume shared tokens only after branch-sensitive DOM stabilizes.

## Phase 0 — integration baseline and merged-code re-audit

**Purpose:** prevent the design-system plan from targeting DOM and state models that active branches replace.

**Branch gates:**

| Active work | Likely overlap | Gate |
|---|---|---|
| Valuation / Holding Cost reliability | calculators, result boundaries, finance visual panels, formatters | Merge before Phase 3 finance migration and Phase 4 finance charts/tables |
| Commute production closure | commute cards, Location stage, timeouts/loading/error states | Merge before Phase 3 Location and Phase 4 map/evidence work |
| Journey Property Identity | journey context/header, identity workflow and CSS modules | Merge before Phase 5 property header/workspace shell |
| Geological Sensitivity | Terrain layers, status semantics, map/evidence model | Merge before Phase 3 Risk and Phase 4 risk map/table |
| Commercial Workspace Architecture | route/shell/navigation/panel ownership | Approve/merge before Phase 5; reconcile plan if ownership differs |

**Files:** read-only audit of the files named in the spec plus any files introduced by those branches.

- [ ] Record branch, HEAD, `origin/main`, worktree status, and exact merged commits for each dependency.
- [ ] Re-run source-pattern counts and map all new/replaced components to the consolidation inventory.
- [ ] Compare final state enums/contracts for valuation, holding, commute, property identity, terrain, and workspace navigation with the spec's semantic-state matrix.
- [ ] Update only this plan/spec if file ownership changed; do not begin UI changes until conflicts are explicit.
- [ ] Run baseline commands and archive results in the implementation PR description:

  ```powershell
  cd frontend_next
  npm run lint
  npm run typecheck
  npm run test:workspace-contract
  npm run test:vnext-hardening
  ```

**Regression risk:** low, because this phase is read-only; the main risk is beginning later phases against stale assumptions.

**Visual acceptance:** baseline screenshots exist at 1440, 1024, 768, 430, and 390 px for Homepage/Journey, Market, Location/Map, Terrain/Risk, Finance, Decision/Case, Comparison, Report, and Property Identity/Workspace.

## Phase 1 — semantic tokens and foundational formatting

### Task 1.1: Token layer

**Files:**

- Create: `frontend_next/app/design-tokens.css`
- Modify: `frontend_next/app/globals.css`
- Modify: `frontend_next/tailwind.config.ts`
- Test: add a token contract script under `frontend_next/scripts/` and wire it to an explicit npm script.

**Interfaces:**

- Consumes: exact token names/values from the specification.
- Produces: CSS variables and Tailwind aliases for all later phases.

- [ ] Write a failing contract test that asserts required semantic token names, forbids missing status roles, and verifies spacing/radius/motion values.
- [ ] Run the contract test and verify it fails because `design-tokens.css` does not exist.
- [ ] Add semantic tokens and import them before base rules in `globals.css`.
- [ ] Map Tailwind names such as `bg-surface-primary`, `text-primary`, `border-subtle`, and `text-status-warning` to CSS variables; do not remove legacy names yet.
- [ ] Re-run token contract, lint, and typecheck.

**Regression risk:** medium; global cascade or Tailwind config changes can alter unrelated surfaces.

**Visual acceptance:** importing tokens alone produces no intentional screenshot diff; canvas and focus remain equivalent until deliberate migrations begin.

### Task 1.2: Numerical presentation

**Files:**

- Create: `frontend_next/lib/presentation-format.ts`
- Create: `frontend_next/lib/presentation-format.test.mjs`
- Later consumers: market, valuation, loan, holding, comparison, reports.

**Interfaces:**

- Produces named formatters for total currency in 萬/base units, monthly currency, unit price, area, percentage, distance, duration, date, and vintage.
- Every formatter returns display text plus stable unit semantics; unavailable values return `—` or the caller-selected explicit state, never `0`.

- [ ] Write tests for `NT$ 2,180 萬`, monthly currency, `72.4 坪`, `18.7%`, `650 m`, `1.4 km`, `23 min`, dates/vintages, null, zero, negative values where valid, and all supported locales.
- [ ] Verify tests fail before the formatter exists.
- [ ] Implement the minimal locale-aware formatters using `Intl.NumberFormat`/`Intl.DateTimeFormat` where appropriate.
- [ ] Add tabular-number base styling for `[data-numeric]` and numeric table cells.
- [ ] Run formatter tests, lint, and typecheck.

**Regression risk:** high when adoption begins because current values mix `萬`, raw NTD, and unlabeled counts. Phase 1 implementation alone must not mass-replace existing display output.

**Visual acceptance:** fixture page or component test demonstrates linked number/unit wrapping and aligned tabular digits at 390 and 1440 px.

## Phase 2 — buttons, forms, statuses, messages, and async states

### Task 2.1: Button and field primitives

**Files:** create `button.tsx`, `field.tsx`; modify `ui.tsx` as compatibility adapter; add component/E2E fixture coverage.

- [ ] Write tests for primary/secondary/tertiary/destructive/icon-only/disabled variants, accessible names, focus, loading label, and 36/40/44 px sizing.
- [ ] Write tests for label, required/optional text, helper, unit prefix/suffix, invalid state, `aria-describedby`, and preserved input value.
- [ ] Implement primitives with semantic classes only.
- [ ] Adapt existing `Button` to delegate to the new primitive without changing consumer behavior.
- [ ] Migrate one low-risk form fixture and confirm there is exactly one dominant action.

**Regression risk:** medium; event/disabled behavior must not change while appearance consolidates.

**Visual acceptance:** all states pass contrast/focus review; long Chinese labels wrap; unit adornments remain attached; mobile controls meet 44 px touch size.

### Task 2.2: Status and message primitives

**Files:** create `status-label.tsx`, `message.tsx`, `types.ts`; adapt `Badge`, `Notice`, `ErrorState`.

- [ ] Write a semantic test matrix for neutral/blue/amber/red/green with required icon + wording and explicit prohibition of recommendation/safety meaning on green variants.
- [ ] Implement process status separately from evidence/risk interpretation so a completed query can coexist with a risk match or no coverage.
- [ ] Implement inline limitation, material warning, confirmation required, blocking error, and system notification variants.
- [ ] Convert compatibility wrappers without changing localized strings.
- [ ] Add a lint/contract check that prevents new raw status palette classes in migrated design-system components.

**Regression risk:** high; current domain statuses overload colors and cannot be mechanically renamed.

**Visual acceptance:** status remains understandable in grayscale and with icons hidden; repeated amber blocks are not introduced by the primitives.

### Task 2.3: Typed empty/loading/error states

**Files:** create `async-state.tsx`; adapt `EmptyState`, `LoadingState`, chart state components, `AnalysisProgress`.

- [ ] Write tests for not-started, input-required, no-data/no-coverage, temporary-unavailable, unsupported, error, no-match, loading-under-threshold, delayed skeleton, and provider timeout.
- [ ] Ensure every terminal state supplies cause, severity, and next action where applicable.
- [ ] Implement local live-region behavior without clearing unrelated results.
- [ ] Adapt chart states and one calculator as proof of compatibility.
- [ ] Verify no fake progress and no raw provider/API error reaches rendered output.

**Regression risk:** high because many E2E tests locate current state text/test IDs. Preserve stable test IDs or update tests in the same task.

**Visual acceptance:** each state is visually distinct without relying on color; loading preserves property/page context; states fit without large empty boxes.

## Phase 3 — section and card consolidation

Phase 3 is split by surface so each change remains independently reviewable. Do not combine these tasks into one class-name sweep.

### Task 3.1: Structural primitives and shared migration

**Files:** create `section.tsx`, `summary-strip.tsx`, `disclosure.tsx`; adapt `Card`, `Metric`, `MetricTile`, `SectionCard`, `ResultSummaryPanel`, `DetailDisclosure`.

- [ ] Write tests for unboxed section, stateful panel, summary strip, standard/compact disclosure, heading relationships, and absence of nested default shells.
- [ ] Implement compatibility adapters and a development-only nested-panel diagnostic attribute or test helper.
- [ ] Migrate shared examples first; retain legacy wrappers until the last consumer is removed.
- [ ] Add a source contract preventing new use of legacy primitives outside an allowlist during migration.

**Regression risk:** medium; spacing can collapse and disclosures can lose accessible names.

**Visual acceptance:** plain sections establish hierarchy with spacing/dividers; panels have an explicit independent purpose; summary strip does not become individual cards on mobile.

### Task 3.2: Homepage and guided journey

**Files:**

- `frontend_next/components/hero-intro.tsx`
- `frontend_next/components/guided-journey/*`
- dashboard/hero sections in `frontend_next/app/page.tsx`
- `frontend_next/components/product-ui.tsx`
- `frontend_next/app/globals.css`

- [ ] Capture current navigation and journey-state E2E behavior before visual changes.
- [ ] Replace animated/decorative hero layers with compact orientation header and one primary action.
- [ ] Replace module-gradient tiles and hero pills with structured navigation/list patterns.
- [ ] Remove card shells inherited solely from embedding tools in journey stages.
- [ ] Retain step identity, completed/in-progress/needs-confirmation wording, focus movement, and report entry behavior.
- [ ] Remove obsolete hero animation classes only after no consumer remains.

**Regression risk:** high; `app/page.tsx` contains workflow orchestration and many test selectors. Keep changes presentation-only and small.

**Visual acceptance:** first viewport shows property/task orientation and a single next action; no continuous hero/workspace motion; journey stage does not contain card-within-card repetition.

### Task 3.3: Market and valuation

**Branch gate:** merge Valuation reliability work first.

**Files:** Market/Valuation sections in `app/page.tsx`, `market-segmentation-panel.tsx`, `data-visualization/market-*`, `valuation-*`, `valuation-result-boundary.tsx`, `valuation-data-freshness.tsx`.

- [ ] Add E2E assertions for available, no-data, limited/fallback, unavailable, stale, and mixed-source results before visual migration.
- [ ] Replace metric-card grids with summary strips and explicit units.
- [ ] Make comparable transactions/evidence the principal analytical section; move methodology/source detail to a quiet evidence disclosure.
- [ ] Remove source-colored pills and repeated result banners; preserve source and coverage text.
- [ ] Consolidate duplicate valuation result presentations in `ValuationVisualPanel` and page-local result blocks.
- [ ] Use green only for completed query state, not valuation confidence/reasonableness.

**Regression risk:** high; multiple visual/model paths currently coexist and reliability work may change boundaries.

**Visual acceptance:** Market follows summary → table → distribution/trend → source; Valuation follows estimate/range → comparables → trend → evidence. A user can state the unit and data period without opening details.

### Task 3.4: Finance

**Branch gate:** merge Valuation / Holding Cost reliability first.

**Files:** `loan-calculator.tsx`, `holding-cost-calculator.tsx`, `loan-visual-panel.tsx`, `holding-cost-visual-panel.tsx`, `affordability-status.tsx`, Tax/Aegis finance sections in `app/page.tsx`.

- [ ] Add tests for invalid inputs, null income burden, grace-period edge, calculation unavailable, and retained previous unrelated results.
- [ ] Group inputs with compact fieldsets and explicit units; remove stretched result empties.
- [ ] Replace four-card KPI grids with a financial summary strip.
- [ ] Consolidate breakdown content so the chart and table do not duplicate low-value information.
- [ ] Reduce warning repetition to one material limitation plus detailed assumptions disclosure.
- [ ] Keep one primary calculate action; transfer actions are secondary/tertiary.

**Regression risk:** high due to reliability-sensitive state and unit display.

**Visual acceptance:** at 1440 px the form is 320–360 px wide and results use remaining space; at 390 px the form is one column, units are never ambiguous, and the primary action remains visible without becoming vertically oversized.

### Task 3.5: Location, Risk, and evidence

**Branch gates:** merge Commute production closure and Geological Sensitivity first.

**Files:** `location-insight.tsx`, `commute-*.tsx`, `terrain-risk-analysis.tsx`, `risk-summary-panel.tsx`, `terrain-cadastral-evidence.tsx`, `satellite-evidence.tsx`, `official-data-status-card.tsx`, guided Location stage.

- [ ] Add state tests that distinguish completed/no match, no coverage, limited, matched risk, not checked, timeout, and provider unavailable.
- [ ] Replace flow badges and repeated cards with confirmed context + primary analysis + evidence order.
- [ ] Consolidate Terrain completeness, material findings, unknowns, source transparency, and recommended checks into summary/evidence/action/details hierarchy.
- [ ] Replace hazard/source cards with evidence rows/table; keep material risk matches always visible.
- [ ] Remove repeated amber warnings while retaining truthful limitations.
- [ ] Ensure no “not matched” or successful request is styled as “safe”.

**Regression risk:** very high; source availability and risk interpretation must remain distinct.

**Visual acceptance:** Location is map-led; Risk exposes coverage and material matches before methodology; source details are available but quieter; green appears only on completed process state.

### Task 3.6: Decision, case, comparison, and report

**Files:** `decision-report.tsx`, `viewing-decision-panel.tsx`, `property-case-*`, `case-manager.tsx`, `case-comparison-panel.tsx`, `property-comparison-report.tsx`, `print-comparison-report.tsx`, command-center/readiness components.

- [ ] Add tests for incomplete cases, two/three-case comparison, partial data, no ranking, risk blockers, and report print order.
- [ ] Merge duplicate decision conclusions into findings/unknowns/confidence/next-action structure.
- [ ] Replace recommendation pill coloring with explicit decision wording and separate process/evidence states.
- [ ] Replace ranking-card-plus-table duplication with one comparison model and expandable detail.
- [ ] Convert print report blocks to editorial sections/dividers and stable print typography.
- [ ] Ensure report evidence order and units match on screen, print, and exported HTML.

**Regression risk:** high; the UI must not convert rule output into investment advice.

**Visual acceptance:** decision has one conclusion and one primary next action; comparison supports 2–3 cases without nested scroll; report reads as a professional document, not a dashboard screenshot.

## Phase 4 — analytical tables, maps, and charts

### Task 4.1: Data table foundation and migrations

**Files:** create `data-table.tsx`; modify every current table owner identified in the spec.

- [ ] Write tests for caption/name, row/column headers, right-aligned numeric columns, unit headers, sticky header, interactive row keyboard behavior, expanded detail row, and empty body.
- [ ] Implement native semantic table composition; do not replace tables with generic div grids on desktop.
- [ ] Assign one mobile strategy to every table: stacked row, selective scroll, key-column pinning, or detail drawer.
- [ ] Migrate financial breakdown and source tables first, then comparable transactions, hazard evidence, and property comparison.
- [ ] Remove redundant “swipe” hints where stacked/pinned strategy replaces scroll.

**Regression risk:** high; responsive transformation can break semantics or hide key columns.

**Visual acceptance:** numerics align, units are stable, row density is consistent, keyboard order matches visual order, and no page has nested horizontal scroll at 390 px.

### Task 4.2: Map frame and synchronized evidence

**Branch gates:** Commute, Geological Sensitivity, and Workspace Architecture merged.

**Files:** create `map-frame.tsx`; modify `map/geo-map.tsx`, `map/terrain-evidence-leaflet-map.tsx`, `google-location-visual-context.tsx`, `terrain-cadastral-evidence.tsx`, professional workspace map composition.

- [ ] Add E2E coverage for map load/unavailable/confirmation-required, keyboard-accessible controls, attribution, selected feature synchronization, and mobile drawer.
- [ ] Implement shared height/split/overlay/attribution/detail slots without wrapping Leaflet internals in another decorative card.
- [ ] Make Location map 65/35 desktop and Risk map/evidence 55/45 or 60/40 where space permits.
- [ ] Replace full-detail Leaflet popups with summary + linked side panel/drawer for complex evidence.
- [ ] Verify page scroll remains usable over maps and no double vertical scroll exists.

**Regression risk:** very high; Leaflet sizing, tile rendering, gesture handling, CSP, and provider-state tests are sensitive.

**Tests:** existing Google Maps, terrain map performance, geospatial evidence, and professional GIS contract suites plus new viewport/keyboard tests.

**Visual acceptance:** map is visually primary, at least 520 px desktop/360 px mobile, controls do not cover findings, attribution remains visible, selected evidence stays synchronized.

### Task 4.3: Chart frame and question-led charts

**Files:** create `chart-frame.tsx`; modify chart components under `components/data-visualization/` and their panel owners.

- [ ] Write tests requiring title/question, unit, period where relevant, missing behavior, and accessible summary/table.
- [ ] Remove per-chart rounded border/background shells and let the analytical section own spacing.
- [ ] Keep price distribution, market trend, loan sensitivity, holding-cost composition, demographic trend, and comparison only where each answers a named question.
- [ ] Replace charts with compact tables/rows when fewer than three meaningful points/categories exist.
- [ ] Create an accessible categorical series palette distinct from semantic status colors.

**Regression risk:** medium-high; SVG labels, long locales, and empty states can overflow.

**Visual acceptance:** no decorative legends, units/period visible, missing values are gaps/not zero, chart remains readable at 390 px with a textual summary.

## Phase 5 — workspace shell, navigation, and identity convergence

**Branch gates:** Commercial Workspace Architecture and Journey Property Identity approved/merged; re-audit final DOM.

**Files:** `app-shell.tsx`, `sidebar.tsx`, `topbar.tsx`, `professional-workspace-shell.tsx` and module CSS, property identity workflow/review and module CSS, guided journey headers/navigation, workspace routes.

- [ ] Write navigation contract tests for `aria-current`, focus restoration, route/page title, property switcher, mobile drawer, and primary action reachability.
- [ ] Establish one compact property/context header and one workspace navigation model.
- [ ] Convert independent CSS-module color/radius/shadow variables to shared semantic tokens without changing layout state behavior.
- [ ] Remove duplicated top-level warning strips; retain one product-boundary disclosure and local material warnings.
- [ ] Limit sticky regions to the header plus at most one context panel; remove nested vertical scroll by default.
- [ ] Replace decorative mascot/help styling with a quiet optional help callout if product still requires it.
- [ ] Keep GIS-specific 1680 px layout and ordinary analytical 1440 px layout as explicit shell variants.

**Regression risk:** very high; shell/navigation changes touch all pages, mobile focus, and workspace routing.

**Tests:** `test:e2e:navigation`, `test:e2e:workspace`, `test:workspace-contract`, `test:vnext-hardening`, property identity E2E, mobile sidebar, i18n, and professional GIS acceptance.

**Visual acceptance:** navigation looks like navigation, not feature buttons; current property/task is always clear; mobile header is not oversized; shell and identity screens visibly belong to the same product.

## Phase 6 — responsive and accessibility closure

**Files:** all migrated primitives/surfaces; Playwright specs; CSS module responsive rules; global reduced-motion rules.

- [ ] Add a viewport matrix helper for 1440, 1024, 768, 430, and 390 px.
- [ ] Assert no unintended document horizontal overflow and no nested horizontal scroll except an allowlisted data table/map.
- [ ] Test zoom/reflow behavior, long Chinese/English/Japanese/Korean content, and long provider/address strings.
- [ ] Run keyboard-only flows for navigation, journey, forms, disclosures, comparison, report, dialogs/drawers, and map controls.
- [ ] Verify focus is visible/not clipped, dialogs restore focus, live regions are restrained, and form errors are associated.
- [ ] Run automated contrast/accessibility checks plus manual screen-reader spot checks on the critical journey.
- [ ] Verify reduced motion stops loops and shortens/removes transitions.

**Regression risk:** medium; fixes may affect geometry across many pages. Land them per primitive/surface owner, not as broad overrides.

**Visual acceptance:** all specification accessibility minima pass; 390 px has reachable actions and readable evidence; 200% reflow does not create two-dimensional page scrolling outside allowed analytical surfaces.

## Phase 7 — visual regression and commercial acceptance

**Files:** Playwright visual specs/snapshots, acceptance checklist/docs only; production component changes are limited to defects found by the gate.

- [ ] Capture deterministic screenshots for every priority surface and state at the viewport matrix.
- [ ] Review side-by-side against the specification, not merely pixel-diff against legacy UI.
- [ ] Run the full relevant frontend suite:

  ```powershell
  cd frontend_next
  npm run lint
  npm run typecheck
  npm run test:google-maps
  npm run test:workspace-contract
  npm run test:vnext-hardening
  npm run test:e2e:navigation
  npm run test:e2e:i18n
  npm run test:e2e:workspace
  npm run test:e2e
  ```

- [ ] Run hosted/real-provider suites only in the approved environment and verify no visual state assumes provider availability.
- [ ] Conduct commercial review with a nontechnical buyer/agent scenario: identify property, interpret market/location/risk/finance evidence, compare cases, choose next action, and export/print a report.
- [ ] Conduct a semantics audit proving every green instance is completion-only and every risk conclusion is textually explicit.
- [ ] Record accepted exceptions with owner and expiry; no undocumented palette/radius/shadow exceptions.

**Regression risk:** low for the phase itself; high-severity defects block release.

**Commercial visual acceptance criteria:**

- Reviewers describe the product as professional, quiet, analytical, credible, modern, and structured.
- The first viewport exposes context, conclusion/task, and next action without card soup.
- Major analytical surfaces are table/map/chart-led and show unit, period, coverage, and material source/vintage.
- Evidence remains discoverable without competing with conclusions.
- Reports are client-presentable in screen, print, and exported HTML forms.
- No gradients/glows/looping workspace animation, arbitrary module accent colors, decorative charts, or repeated pill headings remain.

## Migration mechanics and risk controls

### Compatibility strategy

1. Add new primitives and let legacy exports delegate to them.
2. Migrate one surface at a time with its own behavior and visual tests.
3. Remove legacy export only after `rg` confirms zero consumers.
4. Remove legacy token/animation/class only after build, E2E, and screenshot gates pass.
5. Avoid automated global class substitutions; status and evidence colors require domain review.

### Recommended review slices

- Slice A: tokens + formatter only.
- Slice B: controls/status/messages/states.
- Slice C: Homepage/Journey.
- Slice D: Market/Valuation after reliability merge.
- Slice E: Finance after reliability merge.
- Slice F: Location/Risk after Commute/Geological merges.
- Slice G: Decision/Comparison/Report.
- Slice H: tables/charts.
- Slice I: maps.
- Slice J: shell/identity after architecture merge.
- Slice K: responsive/accessibility and acceptance closure.

Each slice should preserve existing test IDs when they describe product behavior. Rename a test ID only if the underlying semantic owner changes, and update its test in the same slice.

## Consolidation completion checklist

The migration is not complete until all of these targets have one canonical owner:

- [ ] Card/section/panel
- [ ] Metric/summary strip
- [ ] Status/filter/metadata label
- [ ] Button hierarchy
- [ ] Field/input/select/unit input
- [ ] Message/warning/error
- [ ] Empty/loading/timeout state
- [ ] Disclosure
- [ ] Table and responsive row strategy
- [ ] Chart frame and accessible summary
- [ ] Map frame, controls, attribution, selected detail
- [ ] Navigation item and selected state
- [ ] Property/context header
- [ ] Market evidence layout
- [ ] Valuation result layout
- [ ] Finance summary/breakdown
- [ ] Risk evidence layout
- [ ] Decision summary
- [ ] Case comparison
- [ ] Screen/print/export report
- [ ] CSS-module token consumption
- [ ] Reduced-motion behavior

## Final verification and rollback

Before declaring any phase complete:

- run that phase's focused tests, lint, and typecheck;
- run `git diff --check`;
- inspect `git status --short` and confirm only the intended worktree changed;
- compare required viewport screenshots;
- verify the phase can be reverted without data/schema changes;
- document any accepted visual exception.

If a migrated surface fails a truth-boundary, provider-state, calculation, or accessibility test, revert that surface to its compatibility adapter rather than weakening the test or changing domain semantics. Token and primitive layers remain independently reusable while the surface is corrected.
