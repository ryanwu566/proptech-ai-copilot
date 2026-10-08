# Commercial UI/UX Implementation Plan

> Execute inline using superpowers:executing-plans. The user requires one final commit after all gates; no push, merge, or deploy.

**Goal:** Make the existing property evidence workflow usable in a client meeting, desktop and mobile.
**Architecture:** Reuse E2 primitives and E3–E9 models. Change presentation and navigation only. Use the existing case repository, journey selection, source status and print guards.
**Tech stack:** Next.js, React, TypeScript, CSS, Playwright; no new dependencies.
**Spec:** User's attached E10 implementation request, read in this session.

## Global constraints

- Work only in C:\Projects\proptech-commercial-uiux on feat/commercial-uiux-v1, starting at 23a325e2db732fd63be477ad613973b56e4c97d1.
- Missing, unknown, no-match, unavailable, stale and saved snapshots retain their meanings.
- No score, ranking, recommendation, ML, provider closure, math/state changes or new automatic provider requests.
- Validate 1440, 1024 and 390 pixels, Chromium, Chrome and A4 print with deterministic mocks.

## Review focus

- Long addresses, amounts and multilingual controls wrap without hiding content.
- Storage failure never appears as a successful save or an empty repository.
- Reopened evidence remains a snapshot and never gains a current/safe indicator.
- Navigation reaches all existing methods with keyboard and mobile clicks.
- Compare/Report retain zero provider requests and print excludes the global shell.

## Tasks

- [x] 1. Add commercial-uiux.spec.ts acceptance: task-oriented homepage, advanced access, shared save, source-first risk, responsive widths, print and zero provider requests. Run red against the baseline.
- [x] 2. Strengthen design-tokens.css and shared shell/navigation; replace the visible homepage hero with a concise start form and repository-backed recent cases. Preserve journey actions and accessibility utilities.
- [x] 3. Move context/save to property-context-header.tsx, put blockers first in Overview, reorder Market evidence, place Location map and commute at 2:1, put Risk sources first, and clarify Finance summary/assumptions.
- [x] 4. Align saved cases, Compare and Report typography, density, mobile/print presentation. Translate Google/Satellite status surfaces and defer secondary visual loading.
- [x] 5. Run E3–E9 node/browser contracts, new acceptance, lint/type/build/audit and all three release gates. Inspect local screenshots and A4 PDF. Fix Important/Critical findings from an independent reviewer.
- [x] 6. Record exact validation results and residual issues, git diff --check, then exactly one commit: feat: professionalize commercial ui and ux. Confirm clean status; stop.
