# Parallel Track C — Decision Report Presentation Handoff

Status: isolated frontend presentation and local preview; no production integration is enabled

## Scope and reuse

Track C adds a Traditional-Chinese-first viewing report and browser-native print presentation. It does not replace the existing public `DecisionReport`, decision rules, scoring, valuation, finance, tax, Terrain, identity, storage, provider, or API architecture.

The pure adapter in `frontend_next/lib/vnext-report/build-decision-report.ts` reuses:

- `buildViewingDecision` for the recommendation status, reasons, missing critical data, known risk sources, and next action;
- `classifyTerrainSafety` so known high risk remains higher priority than missing data and unknown Terrain never becomes an all-clear;
- `buildTerrainReferenceEvidence` for existing Terrain evidence status, layers, notices, and limitations;
- existing typed valuation, loan, holding-cost, location, Terrain, TaxOracle, property-search, and risk-summary results.

No algorithm is copied into the presentation layer and no new composite score or “safe to buy” verdict is produced. If a supplied decision conflicts with a fresh call to the existing decision helper, the adapter renders a bounded “無法判定” conflict state.

## Presentation contract and fixture separation

`DecisionReportAdapterInput` accepts existing result types plus report-only metadata: Case/property labels, report generation time, identity presentation, evidence source/status/times/coverage/limitations, optional section-state projections, and supplied next actions. `buildDecisionReport` returns a serializable `DecisionReportModel`. Reusable React components receive only that typed model through props and do not read browser storage, sessions, databases, providers, or fixtures.

Synthetic fixtures live only in `frontend_next/lib/vnext-report-preview/`. They cover sufficient evidence, known high risk with other gaps, unavailable Terrain, partial/stale/conflicting evidence, missing valuation and unconfirmed identity, long text, inconsistent supplied output, and all data missing. Every fixture and source label is visibly synthetic/test-only.

The future Case/Evidence integration must project the existing backend DTOs into the adapter. In particular, the real integration must supply report generation time separately from evidence retrieval/effective times, bounded evidence IDs, source labels, status, coverage, and limitations. Where those fields are absent, the report currently displays them as missing; it does not invent an API field or provenance.

## Local preview

From `frontend_next`:

```powershell
npm.cmd run dev -- --hostname 127.0.0.1 --port 3103
```

Open `http://127.0.0.1:3103/dev/decision-report-preview/` and select a synthetic scenario. The route calls `notFound()` server-side when `NODE_ENV=production`; it has no production feature flag and is not linked from production navigation. Playwright's local `next dev` test mode remains available for focused browser verification.

With that isolated preview server running, use a second terminal for focused browser tests:

```powershell
npx.cmd playwright test --config=playwright.report-preview.config.ts
```

The Track C Playwright configuration uses port 3103, one isolated worker, and an OS temporary output directory. The preview server is intentionally started separately because Playwright cannot reliably tear down Next's Windows child process on this host; stop only the Track C terminal after the run.

## Identity, uncertainty, and checklist boundaries

- `unknown`, `unavailable`, `partial`, `limited`, `stale`, `conflicting`, `no_match`, `not_assessed`, `unverified`, and provider error remain distinct display states.
- Missing numeric values render as “未提供（不等於 0）”.
- Known high Terrain risk remains visible even when other evidence is missing.
- Retrieval time never fills an absent effective time.
- Missing provenance is shown as missing.
- Human identity confirmation is explicitly not legal-title, boundary, condition, or safety assurance.
- Checklist state uses component-local React state only. Checking an item records personal review on the current page; it neither verifies evidence nor confirms identity nor persists a Case change.

## Print behavior

The report uses `window.print()` and scoped CSS only; there is no PDF service or dependency. Print media removes preview controls, retains the synthetic label, warnings, sources, missing-data messages, evidence IDs, and limitations, expands closed evidence details, applies A4 margins, avoids unsuitable page breaks, and wraps long content.

## Verification evidence

Completed in the isolated Track C worktree on 2026-09-09:

- frontend typecheck: passed;
- relevant component, adapter, preview, configuration, and ignored-by-default E2E spec lint: 0 errors, 0 warnings;
- focused Chromium browser suite: 8 passed, 0 failed, 0 skipped;
- optimized production build: passed, including Next TypeScript and route generation;
- production server exclusion: `/` returned 200, `/dev/decision-report-preview` returned 404, and preview-identifying copy was absent;
- visual review: desktop at 1440 px, mobile at 390 px, and print media at an A4-like 794 px viewport; long content wrapped without horizontal page overflow, warnings remained prominent, and closed on-screen evidence details were expanded in print.

Visual captures and Playwright traces/results were written only to the OS temporary directory and are not task files or commit content. These checks use synthetic UI fixtures and do not prove live-provider reachability or production Case/Evidence wiring.

## Integration boundary

Remaining work belongs to a later integration track: fetch authorized real Case/property/evidence DTOs, project them into `DecisionReportAdapterInput`, choose the production entry point, and define reviewed backend freshness/coverage copy. That work must preserve tenant/auth boundaries and provider provenance. Synthetic UI browser tests do not prove production end-to-end integration or live provider reachability.

Existing public report behavior is unchanged. Track A GIS/database files, Track B Map UI files, Hero/home/navigation/global styles, production flags, backend, services, database, migrations, SavedCase storage, package manifests, and shared test configuration are not modified.
