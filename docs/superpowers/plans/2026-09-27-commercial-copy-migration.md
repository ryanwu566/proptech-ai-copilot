# Commercial Copy Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate PropTech AI Copilot to one customer-facing terminology and UX-state system without changing backend enum contracts or overstating evidence.

**Architecture:** Introduce a typed presentation layer that maps existing domain responses into independent query, evidence, completeness, risk, and task-readiness axes. Centralize locale keys and value formatters, then migrate surfaces in risk order while preserving internal IDs and moving provider/debug information behind explicit diagnostics.

**Tech Stack:** Next.js 16, React 19, TypeScript 5, existing locale resources, Node test runner, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-27-commercial-product-language-system.md`

## Global Constraints

- Primary locale is `zh-TW`; English, Japanese, and Korean must maintain key parity.
- Do not rename backend enums, API fields, routes, provider IDs, or persisted contracts as part of copy migration.
- Query execution, evidence usability, analysis completeness, risk interpretation, and task readiness are independent axes.
- No-match, no-coverage, unavailable, stale, unknown, and not-assessed must never imply safety.
- Missing numeric values must never render as zero.
- Primary UI must not expose provider adapters, endpoints, HTTP status, request IDs, raw reason/error codes, or schema-field names.
- Do not create an overall property score or winner ranking.
- Await contract-sensitive parallel branches where identified in the spec before migrating those surfaces.

## Review Focus

1. A successful query with zero matches must show `查詢完成` plus `查無符合資料`, never `查詢失敗` or a safe conclusion; cover in Task 1 state-matrix tests.
2. A missing financial input must render an explicit missing reason, never `0`, `NT$0`, or a computed burden state; cover in Task 2 formatter and finance tests.
3. A terrain/provider failure must remain risk-unknown and must not permit unrestricted positive decision wording; cover in Task 5 risk and decision tests.
4. A demo/fallback result must be visibly qualified and must not transfer as verified case evidence; cover in Task 4 evidence tests.
5. Switching to JA/KO must not reveal English fallback fragments or raw enums in primary workflows; cover in Task 7 locale-parity and Playwright tests.

---

## Dependency gates and sequencing

| Parallel stream | Gate before | Reason |
|---|---|---|
| Valuation / Holding Cost reliability | Tasks 4 and 6 finance/valuation final adapters | response status, null semantics, and confidence fields may change |
| Commute production closure | Task 4 Commute migration | fallback/freshness/travel-mode contract may change |
| Journey Property Identity | Task 3 identity header and Task 6 reports | active identity/conflict contract is authoritative |
| Geological Sensitivity | Task 5 Terrain final mapping | layer coverage and risk semantics may change |
| Commercial Workspace Architecture | Task 3 navigation | module placement and route IDs may change |
| Commercial Design System | Tasks 1 and 5 component styling | semantic tokens and alert components may change |

Before each gated task, rerun `git diff origin/main...HEAD -- <affected files>` and inspect the merged contract. Adapt presentation mappings; do not overwrite landed reliability or identity logic.

## File structure

Planned focused additions:

- `frontend_next/lib/product-language/status.ts`: canonical presentation axes and labels.
- `frontend_next/lib/product-language/formatters.ts`: money, price, distance, duration, date, period, and missing-value formatters.
- `frontend_next/lib/product-language/provenance.ts`: Level 1–4 source disclosure view models.
- `frontend_next/lib/product-language/readiness.ts`: task-specific readiness presentation.
- `frontend_next/lib/product-language/glossary.ts`: customer module and object labels.
- `frontend_next/lib/product-language/*.test.mjs`: pure contract tests.
- `frontend_next/scripts/test-product-language-contract.mjs`: static leak, locale parity, unit, and forbidden-word checks.

Existing resources remain the rendering source during migration. Overrides are retired only after their keys move into the canonical resource.

### Task 1: Canonical state axes and presentation contract

**Files:**
- Create: `frontend_next/lib/product-language/status.ts`
- Create: `frontend_next/lib/product-language/status.test.mjs`
- Modify: `frontend_next/lib/experience-architecture.ts`
- Modify: `frontend_next/components/experience-state-panel.tsx`
- Modify: `frontend_next/components/data-visualization/data-status-badge.tsx`
- Modify: `frontend_next/components/data-visualization/chart-empty-state.tsx`
- Modify: `frontend_next/components/data-visualization/chart-unavailable-state.tsx`

**Interfaces:**
- Consumes existing domain enums without renaming them.
- Produces `QueryStatus`, `EvidenceStatus`, `AnalysisCompleteness`, `RiskInterpretation`, `TaskReadinessKind`, and a `ProductLanguageState` with axis-qualified localized presentation.

- [ ] **Step 1: Write state-matrix tests**

Assert at minimum: success + no match; success + no coverage; failure + unavailable; stale evidence; query not started; risk unknown; and task-specific readiness. Assert that no generic `available`/`ready` label is returned without an axis.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `cd frontend_next; node --test lib/product-language/status.test.mjs`
Expected: FAIL because the presentation module does not exist.

- [ ] **Step 3: Implement the canonical types and pure mapping functions**

Use the exact internal states and zh-TW/English labels in specification §4. Keep color as semantic intent (`neutral`, `info`, `caution`, `danger`) rather than hard-coded Tailwind classes.

- [ ] **Step 4: Adapt shared state components**

Make each component require its axis or a complete view model. Preserve compatibility adapters temporarily for current callers and mark them for removal after Task 5.

- [ ] **Step 5: Verify state tests, typecheck, and lint**

Run: `cd frontend_next; node --test lib/product-language/status.test.mjs; npm run typecheck; npm run lint`
Expected: all commands pass.

**Dependencies:** Commercial Design System for final token names; otherwise independent.

**Regression risks:** existing callers assume one `ExperienceState`; snapshot/selectors may expect `ready`; green styling may unintentionally signal safety.

**Acceptance:** Review Focus item 1 passes; `succeeded` does not imply usable/complete/safe/ready.

### Task 2: Units, price vocabulary, dates, and missing values

**Files:**
- Create: `frontend_next/lib/product-language/formatters.ts`
- Create: `frontend_next/lib/product-language/formatters.test.mjs`
- Modify: `frontend_next/lib/valuation-share.ts`
- Modify: `frontend_next/lib/taxoracle-presentation.ts`
- Modify: `frontend_next/lib/loan-visualization.ts`
- Modify: `frontend_next/lib/holding-cost-visualization.ts`
- Modify: `frontend_next/components/map/geo-map.tsx`
- Modify: `frontend_next/components/terrain-risk-analysis.tsx`
- Modify: `frontend_next/components/terrain-cadastral-evidence.tsx`

**Interfaces:**
- Produces locale-aware `formatNtd`, `formatWan`, `formatWanPerPing`, `formatMonthlyNtd`, `formatDistance`, `formatDuration`, `formatPeriod`, and `formatMissing(reason)`.
- Consumes raw values in their existing storage units; conversions occur only at presentation.

- [ ] **Step 1: Write formatter boundary tests**

Cover `999/1000/1499/10000` metres, `59/60/75` minutes, NTD vs ten-thousand NTD, null/undefined/zero, percentages, source periods, and ROC-to-Gregorian presentation where source metadata permits.

- [ ] **Step 2: Run tests and confirm failure**

Run: `cd frontend_next; node --test lib/product-language/formatters.test.mjs`
Expected: FAIL because formatter exports do not exist.

- [ ] **Step 3: Implement formatters with explicit basis types**

Require callers to choose price basis and period. Do not infer missing as zero. Keep zero valid only where the domain explicitly proves a zero amount.

- [ ] **Step 4: Replace hand-built strings in the listed shared generators**

Preserve raw values and calculations. Generated report HTML must use the same formatters as in-app results.

- [ ] **Step 5: Verify unit tests and build**

Run: `cd frontend_next; node --test lib/product-language/formatters.test.mjs; npm run typecheck; npm run build`
Expected: pass; no raw ` m` or ambiguous financial number appears in changed customer surfaces.

**Dependencies:** Valuation/Holding Cost reliability before final field mappings.

**Regression risks:** double-converting `_wan` fields, treating a valid zero as missing, locale spacing changes, static HTML not sharing React formatters.

**Acceptance:** specification §§8–10 and Review Focus item 2 pass; `60752` can never appear under a `萬元` label.

### Task 3: Canonical glossary, homepage, journey, and navigation

**Files:**
- Create: `frontend_next/lib/product-language/glossary.ts`
- Modify: `frontend_next/lib/experience-i18n.ts`
- Modify: `frontend_next/lib/experience-i18n-overrides.ts`
- Modify: `frontend_next/lib/runtime-copy.ts`
- Modify: `frontend_next/lib/runtime-copy-overrides.ts`
- Modify: `frontend_next/components/sidebar.tsx`
- Modify: `frontend_next/components/hero-intro.tsx`
- Modify: `frontend_next/components/workflow-entry-cards.tsx`
- Modify: `frontend_next/components/guided-journey/guided-property-journey.tsx`
- Modify: `frontend_next/components/guided-journey/journey-navigation.tsx`
- Modify: `frontend_next/components/guided-journey/journey-property-context-header.tsx`
- Modify: `frontend_next/components/guided-journey/journey-progress-summary.tsx`
- Test: `frontend_next/e2e/navigation.spec.ts`
- Test: `frontend_next/e2e/mobile-sidebar-navigation.spec.ts`
- Test: `frontend_next/e2e/guided-journey-real-ui-acceptance.spec.ts`

**Interfaces:**
- Consumes approved customer names from specification §12 and identity labels from §7.
- Keeps `AppPage`, DOM IDs, routes, and analytics identifiers internal and stable unless the workspace branch explicitly changes them.

- [ ] **Step 1: Update navigation tests**

Assert customer names and absence of `Lite`, raw English tool lists, and generic `服務狀態 可用`.

- [ ] **Step 2: Run navigation tests and confirm expected failures**

Run: `cd frontend_next; npm run test:e2e:navigation`.

- [ ] **Step 3: Add glossary mappings and migrate copy**

Use the six proposed workspace labels after the architecture gate. Replace generic finish/completion language with named outcomes.

- [ ] **Step 4: Consolidate migrated keys from overrides**

Move approved values into canonical resources. Delete only override entries whose callers and all locales are verified.

- [ ] **Step 5: Verify navigation, journey, and locale smoke**

Run: `cd frontend_next; npm run test:e2e:navigation; npm run test:e2e:i18n; npm run typecheck`.

**Dependencies:** Commercial Workspace Architecture, Journey Property Identity, final brand decision.

**Regression risks:** internal page routing tied to strings, active-nav selectors, product-brand inconsistency.

**Acceptance:** navigation matches specification §12; active property is explicit; viewed progress does not imply completeness.

### Task 4: Property, Market, Valuation, Location, Demographics, Commute, and Satellite

**Files:**
- Create: `frontend_next/lib/product-language/provenance.ts`
- Create: `frontend_next/lib/product-language/provenance.test.mjs`
- Modify: `frontend_next/components/property-finder.tsx`
- Modify: `frontend_next/components/location-insight.tsx`
- Modify: `frontend_next/components/google-location-visual-context.tsx`
- Modify: `frontend_next/components/market-segmentation-panel.tsx`
- Modify: `frontend_next/components/data-visualization/market-insight-evidence-panel.tsx`
- Modify: `frontend_next/components/valuation-result-boundary.tsx`
- Modify: `frontend_next/components/valuation-data-freshness.tsx`
- Modify: `frontend_next/components/data-visualization/valuation-evidence-summary.tsx`
- Modify: `frontend_next/components/demographics-insight-card.tsx`
- Modify: `frontend_next/components/commute-route-card.tsx`
- Modify: `frontend_next/components/commute-livability-card.tsx`
- Modify: `frontend_next/components/satellite-evidence.tsx`
- Modify: `frontend_next/lib/market-result-state.ts`
- Modify: `frontend_next/lib/valuation-result-state.ts`
- Test: `frontend_next/e2e/market-final-closure.spec.ts`
- Test: `frontend_next/e2e/demographics-insight.spec.ts`
- Test: `frontend_next/e2e/satellite-evidence.spec.ts`

**Interfaces:**
- Produces `SourceDisclosure` with primary, evidence-detail, and diagnostic fields.
- Maps each domain result into canonical axes without modifying response schemas.

- [ ] **Step 1: Add fixtures for success/no-match/no-coverage/unavailable/stale/demo/fallback**

Assert primary copy contains result and period/limitation, evidence detail contains agency/dataset/method, and diagnostics-only terms do not occur in primary text.

- [ ] **Step 2: Remove or qualify visible scores**

Replace Property Finder ranking score and location risk score with raw evidence. Keep qualified indices only when formula/range can be disclosed. Show categorical `價格推估可信度`.

- [ ] **Step 3: Implement progressive source disclosure**

Use all six examples in specification §11 as fixtures. Never render backend disclaimer/reason/status text directly without stable mapping.

- [ ] **Step 4: Separate demo/fallback/user-entered evidence**

Mark it `unverified`, place qualification adjacent to values, and prevent verified-case transfer. Satellite failure produces no evidence claim.

- [ ] **Step 5: Run focused E2E, typecheck, and build**

Run: `cd frontend_next; npm run build:e2e; node e2e/run-e2e.cjs e2e/market-final-closure.spec.ts e2e/demographics-insight.spec.ts e2e/satellite-evidence.spec.ts; npm run typecheck; npm run build`.

**Dependencies:** Valuation/Holding reliability and Commute production closure.

**Regression risks:** source attribution requirements, dynamic backend strings, East/West market identity, demo fixtures used by tours.

**Acceptance:** source disclosure follows Levels 1–4 and Review Focus item 4 passes.

### Task 5: Terrain, warnings, risk interpretation, and errors

**Files:**
- Modify: `frontend_next/lib/surface-copy.ts`
- Modify: `frontend_next/lib/terrain-reference-evidence.ts`
- Modify: `frontend_next/lib/terrain-safety-gate.ts`
- Modify: `frontend_next/lib/risk-summary.ts`
- Modify: `frontend_next/components/terrain-risk-analysis.tsx`
- Modify: `frontend_next/components/terrain-cadastral-evidence.tsx`
- Modify: `frontend_next/components/risk-summary-panel.tsx`
- Modify: `frontend_next/components/official-data-status-card.tsx`
- Modify: `frontend_next/components/data-visualization/terrain-status-matrix.tsx`
- Modify: `frontend_next/app/error.tsx`
- Modify: `frontend_next/app/global-error.tsx`
- Modify: `frontend_next/app/not-found.tsx`
- Test: `frontend_next/e2e/terrain-map-ux-performance.spec.ts`
- Test: `frontend_next/e2e/trust-closure-regression.spec.ts`

**Interfaces:**
- Consumes canonical state/risk types from Task 1 and formatters from Task 2.
- Produces domain findings without a primary overall property score.

- [ ] **Step 1: Add risk truth-table tests**

Cover known high, caution, checked-scope no-signal, unavailable, no coverage, no match, stale, and not assessed.

- [ ] **Step 2: Replace composite primary score and safety shorthand**

Show domain findings, evidence state, scope, and required confirmation. Preserve internal calculations only where another contract requires them.

- [ ] **Step 3: Apply warning hierarchy and deduplicate limitations**

Give each result one owner for its material limitation. Keep methodology in disclosure and diagnostics out of normal cards.

- [ ] **Step 4: Standardize errors and empty/loading states**

Implement specification §14 across changed components.

- [ ] **Step 5: Verify trust closure**

Run: `cd frontend_next; npm run build:e2e; node e2e/run-e2e.cjs e2e/terrain-map-ux-performance.spec.ts e2e/trust-closure-regression.spec.ts; npm run typecheck`.

**Dependencies:** Geological Sensitivity and Commercial Design System.

**Regression risks:** downstream Decision/Compare score use, duplicate warnings in resources, risk colors implying safety.

**Acceptance:** Review Focus item 3 and specification §§4.4, 13–15 pass.

### Task 6: Finance, Tax, Case readiness, Decision, Compare, and Report

**Files:**
- Create: `frontend_next/lib/product-language/readiness.ts`
- Create: `frontend_next/lib/product-language/readiness.test.mjs`
- Modify: `frontend_next/components/loan-calculator.tsx`
- Modify: `frontend_next/components/holding-cost-calculator.tsx`
- Modify: `frontend_next/components/competition-taxoracle-demo.tsx`
- Modify: `frontend_next/components/data-visualization/tax-risk-gauge.tsx`
- Modify: `frontend_next/components/data-visualization/tax-decision-visual-panel.tsx`
- Modify: `frontend_next/lib/taxoracle-presentation.ts`
- Modify: `frontend_next/lib/workflow-status.ts`
- Modify: `frontend_next/lib/property-case-evidence.ts`
- Modify: `frontend_next/lib/property-case-readiness.ts`
- Modify: `frontend_next/components/property-case-readiness.tsx`
- Modify: `frontend_next/components/property-case-command-center.tsx`
- Modify: `frontend_next/lib/decision-summary.ts`
- Modify: `frontend_next/components/viewing-decision-panel.tsx`
- Modify: `frontend_next/components/decision-report.tsx`
- Modify: `frontend_next/lib/property-comparison.ts`
- Modify: `frontend_next/components/case-comparison-panel.tsx`
- Modify: `frontend_next/components/property-comparison-report.tsx`
- Modify: `frontend_next/components/print-comparison-report.tsx`
- Modify: `frontend_next/components/professional-workspace-shell.tsx`
- Test: `frontend_next/e2e/taxoracle-human-presentation.spec.ts`
- Test: `frontend_next/e2e/property-identity-review.spec.ts`
- Test: `frontend_next/e2e/nongeo-final-ux-cert.spec.ts`

**Interfaces:**
- Produces named readiness evaluations for viewing preparation, comparison, client discussion, report, and offer preparation.
- Consumes confirmed identity from the landed identity contract and canonical formatted values from Task 2.

- [ ] **Step 1: Write readiness tests from specification §4.5**

Include optional-module absence, identity conflict, different comparison price bases, calculation-complete/income-missing, and partial-report cases.

- [ ] **Step 2: Separate calculation, affordability, evidence, and task readiness**

Replace object-presence completion in `workflow-status.ts`. A loan can be calculated while affordability remains unassessed.

- [ ] **Step 3: Migrate TaxOracle**

Use `稅務條件初步檢查`, fixed-rule wording, and professional-review boundaries. Remove API/POST/TX IDs/deterministic from primary copy and replace the risk gauge with facts and review items.

- [ ] **Step 4: Migrate Case and Decision language**

Remove `provider raw data`, `Direct Market Query Mode`, `county/district`, `ready/pending`, `yes/no`, and internal enterprise names. Use evidence-supported preparation wording.

- [ ] **Step 5: Migrate comparison and reports**

Remove rank, `#1`, top candidate, winner, and composite score. Show normalized factual differences. Group reports by confirmed/estimated/unknown/next checks.

- [ ] **Step 6: Verify focused and end-to-end behavior**

Run: `cd frontend_next; node --test lib/product-language/readiness.test.mjs; npm run build:e2e; node e2e/run-e2e.cjs e2e/taxoracle-human-presentation.spec.ts e2e/property-identity-review.spec.ts e2e/nongeo-final-ux-cert.spec.ts; npm run typecheck; npm run build`.

**Dependencies:** Valuation/Holding Cost reliability and Journey Property Identity.

**Regression risks:** report print layout, persisted comparison shape, score dependencies, finance null semantics.

**Acceptance:** named readiness, preliminary tax scope, no overall winner/score, and specification §20-compliant reports.

### Task 7: Locale parity, leakage enforcement, and final certification

**Files:**
- Create: `frontend_next/scripts/test-product-language-contract.mjs`
- Modify: `frontend_next/package.json`
- Modify: `frontend_next/e2e/i18n.spec.ts`
- Modify: `frontend_next/e2e/i18n-smoke-runtime.spec.ts`
- Modify: `frontend_next/e2e/b2-b5-locale-recertification.spec.ts`
- Modify: `frontend_next/e2e/b2-b5-dynamic-states.spec.ts`
- Modify: `frontend_next/e2e/release-smoke.spec.ts`
- Modify: all locale resources touched in Tasks 1–6

**Interfaces:**
- Consumes canonical key registry and a narrow allowlist for diagnostics/proper nouns.
- Produces `npm run test:product-language`.

- [ ] **Step 1: Implement static contract checks**

Scan customer source/resources for raw state enums, API/HTTP/method/provider/payload, deterministic/mock/fallback, reason/error/source IDs, `Lite`, and accidental English statuses. Allow only code/type contexts, explicit diagnostics, and approved proper nouns.

- [ ] **Step 2: Add key and interpolation parity checks**

Assert zh-TW/EN/JA/KO have identical keys and placeholder sets. Fail on empty strings or silent English fallback in primary keys.

- [ ] **Step 3: Add commercial acceptance E2E cases**

Exercise no match, no coverage, timeout, stale evidence, identity conflict, missing income, demo/fallback, optional-module report, and unlike comparison bases.

- [ ] **Step 4: Run full certification**

Run: `cd frontend_next; npm run test:product-language; npm run lint; npm run typecheck; npm run build; npm run test:e2e:i18n; npm run test:e2e:navigation; npm run test:e2e`.

- [ ] **Step 5: Perform final visible-copy inventory**

Repeat the original keyword searches plus score/confidence/completeness/ready, units, mixed-locale fragments, and duplicate warnings. Review every allowlisted match manually.

**Dependencies:** Tasks 1–6 complete and zh-TW vocabulary frozen.

**Regression risks:** false positives in types/fixtures, contractual proper names, text expansion affecting layout.

**Acceptance:** all specification acceptance criteria and Review Focus item 5 pass.

## Phase mapping and release strategy

| Phase | Tasks | Release outcome | Main dependency | Rollback boundary |
|---|---|---|---|---|
| 1. Status vocabulary + units | 1–2 | semantic contract and formatters | design tokens optional | compatibility adapters |
| 2. Navigation/module names | 3 | task-oriented workspace language | workspace architecture, identity | copy resources |
| 3. Error/loading/empty states | 4–5 portions | actionable state messaging | provider contracts | domain adapter |
| 4. Warning/source disclosure | 4–5 | Level 1–4 provenance | geological/commute closure | disclosure component |
| 5. Financial/price wording | 2 and 6 finance | explicit bases and missing semantics | valuation/holding reliability | formatter call sites |
| 6. Full zh-TW consistency | 6–7 | commercial zh-TW workflow | preceding phases | locale resource |
| 7. EN/JA/KO parity | 7 | equivalent supported locales | canonical zh-TW frozen | locale-by-locale |

Each phase ships only when its compatibility boundary passes typecheck, focused E2E, and the product-language contract test. Do not combine navigation restructuring with domain-contract migrations in one review.

## Final acceptance checklist

- [ ] No engineering-language leakage in primary paths.
- [ ] All financial/distance/time values have unambiguous units and basis.
- [ ] Calculation completion is separate from affordability and readiness.
- [ ] No-match/unavailable/no-coverage never read as safe.
- [ ] Current property identity is visible and conflicts block unsafe synthesis.
- [ ] Primary results are readable without technical source details.
- [ ] No accidental English fragments in zh-TW except approved proper nouns.
- [ ] Every failure supplies meaning and an actionable next step.
- [ ] Demo/fallback evidence cannot appear verified.
- [ ] Reports distinguish known, estimated, unknown, period, limitation, and next verification.
- [ ] Comparison declares factual differences, not a winner.
- [ ] EN/JA/KO key and placeholder parity passes.

## Plan self-review record

- **Spec coverage:** every specification domain maps to Tasks 1–7.
- **Type consistency:** five axes originate in Task 1; formatters in Task 2; provenance in Task 4; readiness in Task 6.
- **Parallel safety:** contract-sensitive work is gated and internal IDs remain stable.
- **Test coverage:** each Review Focus condition has an owning task and explicit test.
- **Scope:** presentation and tests only; backend API/persistence contracts remain out of scope.
