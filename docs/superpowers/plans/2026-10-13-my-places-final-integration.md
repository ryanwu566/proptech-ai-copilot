# My Places final integration plan

> **For agentic workers:** Use superpowers:executing-plans inline; request one independent final review.

**Goal:** Preserve My Places and explicit commute calculation on latest origin/main, ending with one local feature commit.

**Architecture:** Replay the historical feature onto current main and retain its isolated stores and read-only case contract. Extend the existing request classifier and Performance Budget v2 registry rather than introducing competing infrastructure.

**Tech Stack:** Next.js, TypeScript, native Node tests, Playwright, Python/pytest.

**Spec:** User's final integration request, attached Pasted text.txt; historical feature 63e49712e4b3618bd3e0406d58ce169c791b3b26.

## Global constraints

- No push, merge or deployment; exactly one feature commit ahead of origin/main.
- Maximum 20 places, 200 route results; driving, transit, walking using existing Google Routes only.
- Provider requests require explicit Calculate/Refresh; unknown evidence stays unknown, stale evidence is excluded from known weekly burden.
- Preserve user labels, frozen case evidence, existing route ceilings, global 8,000,000 static / 900,000 largest JS ceilings.
- New route baselines are fixed cold production measurements with baseline + min(20%, 300,000) headroom.

## Review focus

- Changed case/property/destination/mode during a request cannot make old evidence current.
- Malformed/future-version/denied localStorage preserves existing data and displays errors.
- Locale switching preserves authored labels and makes zero provider calls.
- Navigation uses current main and RSC exemptions retain their complete precise signature.
- Homepage assets exclude the feature model/editor/full catalogue; missing required routes fail performance coverage.

## Tasks

- [x] Preflight: fetch, verify clean tree and topology; preserve backup ref; replay without creating intermediate commits. Resolve three navigation conflicts by retaining current main entries and adding feature links.
- [x] Verify historical model/provider tests; add failing coverage for new classifier routes and required performance routes; extend existing infrastructure and browser measurement populated views.
- [x] Run focused browser acceptance with retries disabled in Chromium and Chrome, all locales/widths, storage denial, keyboard, stale response, isolation and provider attempt counts.
- [x] Build production; measure cold route assets; record fixed supplemental baselines and enforce existing ceilings without changes.
- [x] Run full deterministic frontend and Python suites, strongest practical browser regressions, typecheck/lint, source/release/security/hygiene gates. Classify and reproduce failures.
- [x] Independent review; reproduce/fix Critical and Important findings; rerun affected checks.
- [x] Record final evidence; create one local feature commit; verify clean tree and 0 behind / 1 ahead; report exact push command without executing it.

## Execution ledger

- Main: 79ed9a6d6abcd7f904dc1be6ec4d97d754e065ad. Clean isolated worktree; starting topology 6 behind / 1 ahead.
- Backup: backup/my-places-before-final-integration-20261013.
- Ruling: execute the user's complete final-integration specification directly; its explicit authorization and single-commit constraint supersede intermediate approval/commit suggestions in skills.
- Replay produced conflicts only in shared global header, case route layout and workspace navigation. Preserve Preference, Decision Room and localized current workspace labels while adding Places/Planner; bypass the snapshot-writing shell for Planner as for Report/Decision Room.

- Verification: frontend406; focused17; Python3706/32skip, focused75; source65; measurement13; final critical browser314/314; feature44 plus keyboard2. All retries0.
- Broad browser:588pass/69fail/3intentional skip/13blocked before corrected tests; each failure classified in validation JSON (64C,5D) and focused runs validate every affected flow. Demographics17/17 recovers blocked cases; shared failure comparison3/3 on clean exact main.
- Fixed baselines859080/1148320; final859534/1148774; all14route gates and unchanged globals pass. Independent review:4feature plus1validation Important findings fixed, none unresolved.
- Finalization: user-specified local single commit; no menu, push, merge, PR or deployment. Post-commit topology/tree checks are returned in final chat.
