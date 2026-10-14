# Wave 1A Final Integration Implementation Plan

> **For agentic workers:** Execute inline with superpowers:executing-plans; use a separate read-only reviewer before the final commit.

**Goal:** Integrate frozen consumer Auth/account onto main with fixed historical route budgets and fresh acceptance evidence.

**Architecture:** Retain Supabase browser sessions, asymmetric backend JWT verification, workspace authorization and database principals. Retain private authoritative account status/platform roles and server suspension enforcement. Extend existing Performance Budget v2 registries using reproduced frozen feature measurements.

**Tech Stack:** Next.js 16.3.8, React, Supabase JS, FastAPI, Python 3.12, PostgreSQL 17, Playwright.

**Spec:** User-supplied final integration request, 2026-10-14; historical feature `a0c037fc915096dc8b02665035dee21ff4b8c5ba`, main `99fe79a82af37a4783b89275b747036ce7e1e06b`.

## Global Constraints

- Do not push, merge or deploy; finish with one feature commit, clean tree, 0 behind/1 ahead.
- Preserve backup branch; no unrelated work or automatic browser-store migration.
- Existing ceilings unchanged: total static <= 8,000,000; largest JS <= 900,000 bytes.
- Auth baselines must come from a clean detached historical build; non-homepage headroom baseline + min(20%, 300,000).
- Preserve browser job timeout 45 minutes, workers, retries, test timeouts and coverage.
- Fresh full Python 3.12 run; classify all failures; hosted acceptance remains unproven.

## Review Focus

- Stale sign-in/refresh/account responses after logout or a user change.
- Malformed/missing account authority and workspace/platform role confusion.
- Direct API and database suspension bypass; tenant isolation.
- Honest duplicate-signup/reset outcomes and bounded errors.
- Route coverage failures, baseline provenance, and homepage shared assets.

### Task 1: Historical baseline and semantic integration

- [x] Preserve historical backup and reproduce production build with its lockfile in a clean detached worktree.
- [x] Measure Auth using current-main cold browser contract, with route selectors only added to an external harness; preserve fingerprints and measurements.
- [x] Replay feature onto main without committing; resolve header by retaining both entry points; verify migration 020 remains available.

### Task 2: Required route budgets

Files: `scripts/analyze_next_bundle.py`, `scripts/measure_route_assets.cjs`, `docs/performance-budget-v2-baseline.json`, `tests/test_route_budgets.py`, `scripts/measure_route_assets.test.cjs`.

- [x] Add and run failing tests for required Auth route coverage, fixed provenance/ceilings, and missing/unmeasured/oversized routes.
- [x] Register routes and selectors; pin reproduced supplemental measurements without changing existing budget entries.
- [x] Run route Python/Node contract tests; build and measure integrated production assets.

### Task 3: Fresh acceptance and repairs

- [x] Run Auth/session deterministic tests, frontend suites, typecheck, lint, production build.
- [x] Run focused Auth/JWT/authorization/security Python, disposable migration/RLS tests and full Python 3.12.
- [x] Run no-retry Chromium/Chrome Auth locale/width/keyboard flows and current feature/navigation regressions.
- [x] Run bundle, security/release, production operations, dependency audit and hygiene gates.
- [x] Classify failures before fixes; add regression tests for substantive repairs and reproduce baseline failures on clean main where practical.

### Task 4: Independent review and final evidence

- [x] Separate read-only security/compatibility/performance review; fix Critical/Important findings with regression evidence.
- [x] Record commands, results, failure classifications and hosted limitations in final acceptance report.
- [x] Verify diff and migration checksums, commit once, verify topology and clean tree; report exact unexecuted push command.
