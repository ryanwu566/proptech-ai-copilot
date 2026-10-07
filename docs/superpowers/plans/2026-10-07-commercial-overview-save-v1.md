# Commercial Overview and Save v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an evidence-bounded commercial Overview that explains what is known, unknown, stale, or next for one browser-local property case, and makes explicit save/reopen behavior reliable without automatic provider execution.

**Architecture:** Extend `PropertyCaseWorkspace` as the sole Overview input and derive a pure `OverviewModel` from the normalized E4–E7 handoffs. Reuse the existing compact `SavedCase` as the persisted snapshot, add an identity-guarded repository re-save operation, and render the model with E2 primitives. Overview and reopen remain read-only with respect to providers; refresh actions stay in the detailed workspaces.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5, browser `localStorage`, Node test runner, Playwright.

**Spec:** `C:/Users/吳奕陽/.codex/attachments/1d3a7acc-0e63-4698-98d1-07e33795292d/Pasted text.txt`, constrained by `docs/superpowers/specs/2026-09-27-commercial-ux-master-architecture.md`

## Global Constraints

- Work only on `feat/commercial-overview-save-v1`; do not push, merge, deploy, or rebase.
- Keep `/workspace/[caseId]` unchanged and do not implement Compare, Report, ranking, recommendations, or any overall score.
- Use `PropertyCaseWorkspace`, `SavedCase`, `JourneyPropertyIdentityAnchorV1`, and the E4–E7 normalized models; do not create parallel identity or evidence stores.
- Overview and saved-case reopen make zero external analysis requests and never silently refresh stale, unavailable, or absent evidence.
- Preserve asking price, active price, Market evidence, and Valuation as separate concepts; unavailable and missing values never become zero.
- Preserve Google route and secondary transit independence, source-specific risk semantics, and Finance calculation/affordability independence.
- The journey anchor is browser correlation only, never parcel, building, ownership, boundary, title, zoning, or legal identity.
- Save may succeed for partial evidence when identity is valid; save means preserving the snapshot, not declaring analysis complete.
- At 390 px, keep one document scroll owner, no body overflow, usable links/save action, readable wrapped statuses, and no tiny tables.
- Create exactly one final commit: `feat: build commercial overview and save workspace`.

## Review Focus

1. A valid partial case with unavailable providers must save and reopen without upgrading those providers to `not_started`, current, safe, or numeric zero.
2. Property revision/address/anchor mismatch must block re-save with a concrete correction while preserving the in-memory and existing saved data.
3. A Google route must remain visible when TDX evidence is unavailable, and one risk-source failure must not erase sibling results.
4. Saved summary timestamps must be presented as snapshot/check metadata and never as proof that evidence is live or freshly recalculated.
5. Rendering Overview or reopening a case must issue no Market, Valuation, Routes, TDX, Terrain, Satellite, Tax, Loan, or Holding Cost request.

---

### Task 1: Normalize the complete E4–E7 workspace snapshot

**Files:**
- Modify: `frontend_next/lib/workspace/workspace-model.ts`
- Modify: `frontend_next/lib/workspace/legacy-case-adapter.ts`
- Modify: `frontend_next/lib/workspace/risk-evidence-model.ts`
- Test: `frontend_next/lib/workspace/workspace-model.test.ts`
- Test: `frontend_next/lib/workspace/risk-evidence-model.test.ts`

**Interfaces:**
- Consumes: `MarketPriceModel.overview`, `buildLocationOverviewHandoff(workspace)`, stored `terrainReference`, `FinanceModel.overview`, existing `WorkspaceEvidenceState`.
- Produces: one `PropertyCaseWorkspace` carrying a bounded `risk` snapshot/handoff alongside Market, Location, and Finance; no provider payload reconstruction.

- [ ] **Step 1: Write failing adapter tests**

Add cases for all-domain saved evidence, valuation attempted-unavailable, stored risk no-match versus unavailable/limited, Google route with unavailable secondary transit, Finance calculated with unassessed affordability, and identity-stale reopening.

- [ ] **Step 2: Run the focused model tests and verify RED**

Run: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test lib/workspace/workspace-model.test.ts lib/workspace/risk-evidence-model.test.ts`

Expected: failures show the missing risk workspace field/handoff and any state that cannot currently round-trip.

- [ ] **Step 3: Add the minimal normalized risk snapshot interface**

Expose a stored-risk overview adapter from `risk-evidence-model.ts`, populate it in `legacy-case-adapter.ts`, and add the field to `PropertyCaseWorkspace`. Preserve stored summaries as `saved_summary`/limited and retain source-layer no-match/unavailable meaning without treating either as safe.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the command from Step 2; expected all tests pass.

### Task 2: Build the pure evidence synthesis and task-readiness model

**Files:**
- Modify: `frontend_next/lib/workspace/overview-model.ts`
- Create: `frontend_next/lib/workspace/overview-model.test.ts`

**Interfaces:**
- Consumes: `PropertyCaseWorkspace`, `MarketPriceModel.overview`, `LocationOverviewHandoff`, `RiskOverviewHandoff`, `FinanceModel.overview`, E1 `resolveTaskReadiness`.
- Produces: `buildWorkspaceOverview(workspace): WorkspaceOverviewModel` with property context, up to five findings, unknowns, blockers, three-to-five next actions, four bounded domain summaries, named readiness, freshness/provenance rows, and an unresolved-item count.

- [ ] **Step 1: Write the E8 truth-table tests**

Cover: all evidence available; one-module-only; valuation attempted-unavailable; risk no-match not safe; risk unavailable remains unknown; Google route plus secondary unavailable; Finance calculated plus affordability unassessed; saved snapshot not live; stale identity; and Property A evidence never appearing in a Property B model.

- [ ] **Step 2: Run the Overview model tests and verify RED**

Run: `node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test lib/workspace/overview-model.test.ts`

Expected: missing `WorkspaceOverviewModel` sections and synthesis behaviors fail.

- [ ] **Step 3: Implement the pure model**

Use only normalized handoffs and explicit state branches. Cap findings/actions, keep module-local failures local, generate exact detail routes, and compute task readiness for named tasks without a percentage, universal readiness, recommendation, or score.

- [ ] **Step 4: Run Overview plus E1–E7 model suites and verify GREEN**

Run the Overview test plus commercial state/readiness/formatter/provenance, workspace, market, location, risk, finance calculation/model/persistence, identity/invalidation, valuation, and monetary tests.

### Task 3: Add identity-guarded snapshot save/re-save

**Files:**
- Modify: `frontend_next/lib/case-storage.ts`
- Modify: `frontend_next/lib/workspace/case-repository.ts`
- Create: `frontend_next/lib/workspace/case-repository.test.ts`
- Modify: `frontend_next/lib/workspace/workspace-model.ts`

**Interfaces:**
- Consumes: the existing compact `SavedCase`, `getDraftSaveMissingFields`, `compactCaseData`, and current anchor/address/coordinate expectations.
- Produces: a repository save result discriminated as `saved` or `blocked` with a localized actionable reason; successful re-save recompacts only the current case row, updates `updatedAt`, dispatches `CASE_UPDATED_EVENT`, and makes no provider call.

- [ ] **Step 1: Write failing save/reopen tests**

Cover valid complete case, valid partial case, attempted-unavailable preservation, stale/revalidation identity blocking, anchor/address/coordinate mismatch blocking, missing case, and bounded compact re-save.

- [ ] **Step 2: Run the repository/storage tests and verify RED**

Run the new repository test with existing production-handoff and workspace adapter contract tests.

- [ ] **Step 3: Implement the bounded save operation**

Do not create a new snapshot schema. Reuse the saved row, validate the current browser anchor, re-run compaction, update only the matching case, and surface exact correction text for each blocked condition. Never discard the prior saved row on failure.

- [ ] **Step 4: Run save/reopen and identity tests and verify GREEN**

Include `commercial-production-handoff-contract.spec.ts`, journey identity contracts, workspace model tests, and the new repository tests.

### Task 4: Render the calm Overview and bounded cases-list enhancements

**Files:**
- Modify: `frontend_next/components/workspace/overview/overview-view.tsx`
- Create: `frontend_next/components/workspace/overview/overview-section.tsx`
- Create: `frontend_next/components/workspace/overview/overview-view.module.css`
- Modify: `frontend_next/components/workspace/property-context-header.tsx`
- Modify: `frontend_next/components/workspace/saved-cases-entry.tsx`
- Modify: `frontend_next/components/workspace/saved-cases-entry.module.css`
- Modify only if required: `frontend_next/components/workspace/workspace-shell.module.css`

**Interfaces:**
- Consumes: `WorkspaceOverviewModel` and repository save result.
- Produces: the required hierarchy—property/current posture, decision summary, Market, Location, Risk, Finance, unknowns/blockers/actions, and save/freshness/provenance—with direct module links and accessible save feedback.

- [ ] **Step 1: Add component/browser assertions for the rendered contract**

Assert semantic heading order, distinct price concepts, unavailable valuation wording, route/transit independence, no-match language without “safe,” calculated/unassessed Finance separation, saved-snapshot disclosure, exact section links, keyboard-accessible disclosures, and `aria-live` save status.

- [ ] **Step 2: Implement the view with E2 primitives**

Use `SummaryStrip`, `MetricRow` or compact definition rows, `StatusLabel`, `Message`, `Section`, `Panel`, `ActionSection`, and `DetailsDisclosure`. Avoid duplicate analysis controls and provider-first hierarchy.

- [ ] **Step 3: Add the explicit save action and cases-list summaries**

Keep save reachable, show `saving`/`saved`/blocked feedback without calling providers, and add only saved date/freshness plus a limited unresolved description to `/cases`. Preserve the empty-state path to case creation.

- [ ] **Step 4: Verify component lint/type safety and focused browser behavior**

Run lint/typecheck plus the E8 Playwright file created in Task 5.

### Task 5: Add deterministic E8 browser regression coverage

**Files:**
- Create: `frontend_next/e2e/commercial-overview-save.spec.ts`
- Modify only if a reusable fixture is needed: `frontend_next/e2e/fixtures.ts`

**Interfaces:**
- Consumes: the browser-local saved-case schema and mocked route interception.
- Produces: deterministic Chromium/Chrome acceptance for `/cases`, Overview, save/reopen, navigation, partial/unavailable/stale states, property switch isolation, 390 px, accessibility basics, and zero automatic external analysis requests.

- [ ] **Step 1: Create the representative 臺中市西屯區臺灣大道三段100號 fixture**

Include Market evidence, Google route to 臺中車站, secondary commute unavailable, bounded mixed Risk evidence, Valuation attempted-unavailable, and Finance calculation with missing monthly income.

- [ ] **Step 2: Write and run the failing browser scenarios**

Track all analysis endpoints and assert zero calls while opening Overview and reopening a saved case. Assert save/reopen fidelity, module links, unknown preservation, no fabricated values, and Property A→B isolation.

- [ ] **Step 3: Complete 390 px and accessibility assertions**

Assert no document-level overflow, reachable save and detail links, wrapping statuses, logical headings, named interactive elements, keyboard disclosure operation, and status text independent of color.

- [ ] **Step 4: Run serial Chromium and installed Chrome projects**

Use the repository runner/configuration with `--workers=1`; retain exact evidence if Chrome is unsupported in the environment.

### Task 6: Full regression, trust review, independent review, and one commit

**Files:**
- Review all changed files only; fix Critical/Important findings with focused RED/GREEN tests.

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: a release-ready bounded E8 branch and one commit.

- [ ] **Step 1: Run the required Node regression suites**

Run E8, save/reopen, identity, E3 workspace, E4 Market, E5 Location/Commute, E6 Risk, E7 Finance, production-handoff, reliability, and monetary tests.

- [ ] **Step 2: Run deterministic browser regression**

Run the E8 spec plus existing commercial routing/property-context/Market/Location/Risk/Finance/production-handoff suites serially in Chromium and Chrome where supported.

- [ ] **Step 3: Run static, build, dependency, and repository gates**

From `frontend_next`: `npm run lint`, `npm run typecheck`, `npm run build`, `npm audit --omit=dev --audit-level=high`, and `python ../scripts/npm_audit_gate.py`. From repository root: `python scripts/security_performance_release_gate.py --json` and `git diff --check`.

- [ ] **Step 4: Run the changed-code trust scan**

Search changed user-facing code for `safe`, `安全`, `推薦`, `recommended`, `best`, `最佳`, `winner`, `贏家`, `good`, `official appraisal`, `官方估價`, `overallScore`, and `overall_score`. Justify benign occurrences and remove any investment/safety/ranking overclaim.

- [ ] **Step 5: Perform independent review**

Request a fresh review for fabricated synthesis, stale evidence, missing-to-zero, unavailable-to-not-started, identity overclaim, implicit API calls, save/reopen dishonesty, unsafe risk language, affordability overclaim, accessibility, and mobile overflow. Fix every Critical/Important finding and rerun affected gates.

- [ ] **Step 6: Verify final repository state and create exactly one commit**

Confirm the diff is bounded and `git diff --check` passes, then commit once:

```bash
git add <bounded E8 files>
git commit -m "feat: build commercial overview and save workspace"
```

- [ ] **Step 7: Record final evidence**

Capture starting SHA, branch, architecture/handoff behavior, changed files, every requested test/gate result, commit SHA, final `git status --short`, remaining non-blocking issues, PR safety, and E9 readiness. Do not push, merge, or deploy.
