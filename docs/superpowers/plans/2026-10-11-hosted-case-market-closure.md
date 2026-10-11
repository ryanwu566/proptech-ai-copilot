# Hosted Case and Market Closure Implementation Plan

> **For agentic workers:** Use systematic debugging and test-driven development; execute the independent Market and browser investigations in parallel. Exactly one final commit overrides incremental commits.

**Goal:** Close the real Create/Save/Reload/Reopen/Compare/Report journey and prove a truthful official-data Market acquisition.

**Architecture:** Preserve the existing browser snapshot repository and deterministic valuation engine. Trace and repair proven boundary failures, preserve quarantined records during writes, and validate frozen evidence through actual production builds and browsers.

**Tech Stack:** Next.js/TypeScript, Playwright Chromium and Chrome, Python, PostgreSQL/official PLVR.

**Spec:** User Wave 0A attachment, `Pasted text.txt`, supplied October 11, 2026.

## Global Constraints

- Authoritative integrated Starting HEAD and remote main: `8b1367a9117e2c8c762f0bad599bba94e9eca771` (verified; user authorized the already-rebased worktree).
- The completed `ef1c49c55a58eb0ab63beefe0cd2ddc1f2f9717b` acceptance is preserved as a prior checkpoint, not final integrated evidence. Main moved before its commit; no Wave commit was created.
- The original `c9ab5f61a45f7f704326af66cb0bea02740b9927` baseline evidence remains preserved. No restart, reset, discard, or further rebase.
- No push, merge, deploy, cloud configuration changes, ML-B, invented transactions, or unrelated features.
- Exactly one final commit; do not suppress invalid-record diagnostics or discard unrelated data.
- Unknown remains unknown; manual review remains manual; only explicit acquisition actions call providers.

## Review Focus

- Serializer/read-validator drift for absent or partial optional evidence.
- Writes to a partially corrupt list silently deleting quarantined records.
- Finance/checklist case identity or provenance changing across Save/Reopen.
- Market API stripping the deterministic comparable trace.
- Browser-created cases differing from pre-seeded model fixtures.

### Task 1: Reproduce and repair snapshot boundaries

**Files:** `frontend_next/lib/case-storage.ts`, `frontend_next/lib/workspace/saved-case-diagnostics.ts`, focused `frontend_next/scripts/*.test.cjs` tests.

- [x] Record supplied production evidence and inspect reproducible serializer/read boundaries without logging private data; historical browser storage is unavailable and its cause remains NOT PROVEN.
- [x] Write failing tests through `buildJourneySaveCase`, `saveCase`, repository read, adapter, Compare and Report.
- [x] Repair only proven boundary failures; preserve IDs, evidence and source timestamps.
- [x] Test legacy/unsupported/invalid/duplicate/partial records and unavailable/quota storage without data loss.

### Task 2: Official Market acquisition and immutable valuation

**Files:** valuation API/service/provider tests, Market evidence documentation.

- [x] Capture deterministic baseline before changes.
- [x] Record original Taipei failure as ROOT_CAUSE_NOT_PROVEN; verify local configuration and provider/query contracts without inferring the deployed exception.
- [x] Test and fix proven API contract and accepted-road handoff failures without changing valuation calculations.
- [x] Exercise real official lineage data through a disposable local PostgreSQL and HTTP API; record coverage and limits.
- [x] Verify unsupported requests remain unavailable and baseline outputs are identical.

### Task 3: Two-case browser and print acceptance

**Files:** new `frontend_next/e2e/hosted-case-market-closure.spec.ts` and ignored browser/PDF artifacts.

- [x] Drive actual homepage Create and explicit acquisition UI; save A and B with distinct finance/evidence/checklist states.
- [x] Reload/reopen both; verify isolation, comparison, frozen reports and zero automatic provider calls.
- [x] Generate actual A4 PDFs and inspect content, page geometry and overflow.
- [x] Run Chromium and installed Chrome in zh-TW/en/ja/ko at 390/430/1024/1440.

### Task 4: Gates, independent review and final evidence

- [x] Run complete Python/frontend deterministic suites, typecheck, lint, production build, production audit, bundle/route budgets, release/security/operations/hygiene gates and browser tests.
- [x] Obtain independent review of persistence, Market truthfulness and provider/unknown/provenance contracts; resolve critical/important findings.
- [x] Prepare the final 28-item evidence report with honest production limits for the single enclosing Wave 0A commit; report its exact SHA in delivery.

Final verified local acceptance: 3,616 Python tests / 331 frontend tests /
48 browser tests, 68 A4 PDFs with no blank or clipped pages, and 232 frozen
operation windows with zero calls. The full release gate, standard production
build, typecheck, lint, production audit, budgets and repository contract gates
passed. Independent review has no remaining Critical or Important findings.
Production Market remains open; original production roots are NOT PROVEN.
No push, merge, deployment or cloud settings changes.

### Task 5: Integrated 8b revalidation and single commit

The user requires fresh integrated evidence after PR #180 (ML-0 research and
CI/dev-test dependency contract), without restarting implementation or ML-B.

- [x] Verify new base and preserve all prior implementation/evidence; establish an isolated environment satisfying requirements-dev.
- [x] Run the full Python inventory including ML-0 and complete frontend deterministic suite: final post-review 3,667 passed / 32 existing skips; frontend 353 passed / zero skips.
- [x] Run Chromium/installed Chrome acceptance in all four locales and widths: final 50 passed, 68 actual A4 PDFs / 1,123 nonblank/unclipped pages, 236 windows / zero automatic calls. Preserve the pre-click harness RED and focused stale-write GREEN evidence.
- [x] Reverify eight immutable fixtures, genuine supported local Market acquisition and truthful unsupported Market.
- [x] Run typecheck, lint, standard production build, production audit, budgets, release/security/operations/hygiene/whitespace gates; final staged hygiene/whitespace also precede the commit. External operations guardrails remain BLOCKED / NO_GO.
- [x] Obtain final independent integrated review for the requested data-loss/identity/schema/isolation/unknown/provider/drift/report/root-cause risks; repair the Important same-case stale-write finding with RED/GREEN coverage and a cleared targeted follow-up.
- [x] Prepare the current 25-item final report; verify unchanged remote base and create exactly one enclosing local commit, with no push/merge/deploy. Final staged hygiene/whitespace and a zero-ahead-commits check precede that commit; its exact SHA is reported in delivery.
