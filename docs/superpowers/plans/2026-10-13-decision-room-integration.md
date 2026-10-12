# Decision Room final integration plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task.

**Goal:** Preserve Decision Room on current main with fixed Performance Budget v2 evidence and exactly one local feature commit.

**Architecture:** Keep the versioned per-case sidecar and read-only case adapter. Reuse shared navigation and request classification. Measure cold production assets with the existing supplemental baseline mechanism.

**Tech Stack:** Next.js, React, TypeScript, Playwright, Python/pytest.

**Spec:** User's final integration request for PR #184, supplied 2026-10-13.

## Constraints and review focus

- No push, merge, deployment, provider refresh, or Saved Case writer changes.
- Existing route ceilings and 8,000,000 / 900,000 byte global protections stay fixed.
- Check case isolation, stale/corrupt/blocked storage, manual evidence semantics, unknown values, URLs, bounded history, keyboard/mobile behavior and asset attribution.

### Task 1: Replay and shared navigation

- [x] Verify clean topology and preserve historical commit in a backup ref.
- [x] Replay the sole feature commit; preserve current Scenario navigation and shared navigation components.

### Task 2: Performance and acceptance contracts

- [x] Add required Decision Room route measurement, populated-view validation, and fixed supplemental baseline.
- [x] Test internal RSC classification while rejecting arbitrary APIs, fetch/XHR and external requests; reuse the shared classifier.
- [x] Extend acceptance for shared navigation, locale preservation and keyboard workflow as needed.

### Task 3: Verification, review and documentation

- [x] Run all library/script tests, typecheck, lint, production build, zero-retry focused Chromium/Chrome acceptance and relevant regressions.
- [x] Run full practical Python/browser regressions and operations/quality/hygiene gates; classify failures and reproduce on base when practical.
- [x] Obtain separate read-only review, fix important findings and record measured evidence and unproven hosted claims.
- [x] Amend to one feature commit, verify clean 0-behind/1-ahead topology, report exact lease command without executing it.

Execution evidence and retained failure classifications: `docs/property-decision-room-v1.md` and `docs/decision-room-integration-validation-20261013.json`. Broad Chromium failures were investigated and retained, rather than used to change retry/timeout policy. The user explicitly requested one local commit and no push/merge/deploy.
