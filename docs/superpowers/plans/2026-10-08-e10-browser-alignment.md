# E10 Browser Acceptance Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete PR #162's browser gate while retaining capability, validation, trust and causal-state coverage through the E10 commercial navigation.

**Architecture:** One test-only navigation helper opens Methods or the optional official-transaction finder using real UI actions. Replace obsolete primary five-step layout assertions with saved-case workspace and output navigation. Repair runtime code only after a behavioral regression is reproduced.

**Tech Stack:** Next.js, TypeScript, Playwright Chromium and installed Chrome.

**Spec:** User attachment `072fc427-a412-439a-9ce2-6ab5df388b95/Pasted text.txt`, supplied 2026-10-08.

## Global Constraints

- Do NOT restore old UI merely to satisfy stale tests.
- Do NOT weaken input-validation assertions.
- Do NOT skip these tests simply because the tool is secondary.
- Do NOT amend c1638c5. Do NOT push, merge or deploy.
- Preserve retries, timeouts, provider isolation and bounded trust assertions.
- Run affected Chromium suites, then installed Chrome, then the complete CI browser command with one worker.
- Create exactly one follow-up commit after verification.

## Review Focus

- Invalid Aegis input must prevent requests for all eight validation branches.
- Slow, failed or blocked cadastral tiles must not invalidate Terrain evidence or create parcel geometry.
- Changed property identity must invalidate prior evidence and ignore late responses.
- All four locales and 390px navigation must remain usable without raw translation keys.
- Saved-case Overview, Market, Location, Risk, Finance, Compare and Report must preserve case identity and evidence bounds.

### Task 1: Classify and reproduce

- [x] Inspect every observed GitHub failure and inventory all remaining obsolete navigation selectors.
- [x] Reproduce representative failures without changing runtime or retry/timeout configuration.
- [x] Record stale contract versus proven runtime regression per scenario; verify underlying behavior after navigation alignment.

### Task 2: Align secondary capability navigation

**Files:** `frontend_next/e2e/helpers/commercial-navigation.ts`; Aegis, Terrain, market, smoke, locale and identity specs identified by the inventory.

**Interfaces:** `openMethod(page: Page, name: string | RegExp): Promise<void>` and `openPropertyEntry(page: Page): Promise<void>`.

- [x] Replace obsolete aside/drawer/hero navigation with scoped Methods or explicit finder actions.
- [x] Preserve validation, network, timing, causal, trust and locale assertions; update labels only where current bounded copy is intentional.

### Task 3: Replace primary five-step structural coverage

**Files:** `frontend_next/e2e/guided-journey-real-ui-acceptance.spec.ts`, closed-loop and other optional journey specs.

- [x] Test real Home entry, case workspace navigation, equivalent price/location/risk/finance capabilities, Overview decision evidence, Compare and Report.
- [x] Keep optional decision components and closed-loop behavior reachable through explicit finder entry, retaining the original semantic assertions.
- [x] Cover saved identity continuity, four-locale Home/navigation and mobile reachability.

### Task 4: Verify and conclude

- [x] Run the four minimum affected suites plus all other changed specs on Chromium, then Chrome; investigate every failure before proceeding.
- [x] Run `npm --prefix frontend_next run test:e2e -- --workers=1` with `CI=true` and capture complete final counts.
- [x] Independently review coverage, exclusions, timeout/retry preservation and runtime diff.
- [x] Run `git diff --check`, commit once using the user's prescribed message, and report final status plus all 19 evidence fields.

**Execution ruling:** The user's supplied task explicitly authorizes implementation, verification and one final commit. Continue without a redundant approval handoff. Root serializes browser runs and builds; independent test domains have disjoint editing ownership.

**Full-gate follow-up:** The first complete 918-case run found one intermittent test-readiness race with the shell's initial heading focus. Its existing competing focus lifecycle was inspected before adding readiness and keyboard-state assertions. The updated 14-case commercial UI suite passed on Chromium, then Chrome; the keyboard case also passed ten repetitions in each browser. A fresh full CI command is required on this final test code. Runtime and timeout/retry configuration remain unchanged.

**Final evidence:** The fresh full CI command completed, exit 0: 911 passed, 1 flaky, 6 existing skips, all 918 cases accounted for. The flaky result was an unchanged property-context spec's browser-context teardown timeout, with no failed product assertion; retry, Chrome and ten additional repetitions in each browser passed. The long interruption's cause is unproven and documented separately. TypeScript and lint passed; `git diff --check` passed. The affected test coverage totals 271 distinct scenarios per browser. The final local commit uses `test: align browser acceptance with e10 ux`; no push, merge or deployment is authorized.
