# Case Pulse route budget repair

**Goal:** Restore existing route budgets without changing live Pulse behavior, budgets, or CI.

**Architecture:** Separate the existing Decision Room reader, validation, and browser subscriptions from its writer. Pulse imports the read-only adapter; the editable room keeps its existing repository API and semantics. Import the case layout and each evidence view directly from their own client boundaries, rather than a shared barrel retaining unrelated exports. WorkspaceShell continues to supply its already-loaded workspace.

**Spec:** PR #216 follow-up request in this session. No Command Palette or Decision Room product changes.

## Checks and sequence

- [x] Measure the unchanged production build and retain requested-file evidence. Trace `evidence-entry → CaseRouteLayout → CasePulse → decision-room-store` against emitted modules.
- [x] Add reader parity and event-subscription tests; observe failure before introducing the adapter.
- [x] Extract the existing read path without relaxing validation. Preserve empty/corrupt/unsupported/blocked distinctions, case filtering, same-tab events, cross-tab storage events, and unsubscribe behavior.
- [x] Change Pulse to the read-only adapter. Compare measured assets, including Finance and Compare; do not assume a dynamic import improves the measured graph.
- [x] Pass Pulse/reader/store units, the 16 targeted bundled headless Chromium tests (one worker, zero retries), route measurement and all existing budgets, standalone typecheck, and focused lint.
- [ ] Review the focused diff, create one follow-up commit, push normally to PR #216, and inspect every new CI workflow before reporting readiness. Do not merge.

## Review focus

- Corrupt or unsupported room records must remain unavailable, never zero outstanding.
- DONE and manual follow-ups retain real saved-state counts.
- Events for other case IDs must not update the active room; listeners must be removed on cleanup.
- Saved workspace changes remain live in both shell and standalone routes.
- Retain all four locales and 390/430 wrapping, no provider calls, no polling, and no synthetic score.

## Evidence ledger

- Initial HEAD: `79dadac6e501bd3aae95f8b4490710c386b87992`; clean feature worktree.
- CI gate failed only at bundle/route budgets; the shared entry boundary includes Pulse even on Compare.
- Emitted Decision Room repository module: 6,934 bytes, including writes/history/Web Locks not used by Pulse.
- Local baseline: 1,305,504 bytes for the five shared routes; 1,357,362 for Finance (192 bytes below CI's environment).
- Reader-only measurement: 1,302,680 / 1,354,538 bytes, saving 2,824 bytes but still over budget. Ruling: also separate the layout from the evidence barrel, because its export keeps Pulse and layout dependencies reachable on Compare even when Pulse is not rendered there.
- Direct layout measurement: Finance 1,114,204 and Compare 1,259,158 pass; root/Overview/Market/Report remain at 1,303,110 (1,898 over). Ruling: finish separating the view entry points too; the original client barrel retains all of their exports on each route. Keep the scenario editor's existing dynamic wrapper.

## Final local validation

Unique uncompressed requested static bytes, same local build configuration before and after:

| Route | Before | After | Existing limit |
| --- | ---: | ---: | ---: |
| `/cases/[caseId]` | 1,305,504 | 1,110,849 | 1,301,212 |
| `/cases/[caseId]/market` | 1,305,504 | 1,113,481 | 1,301,212 |
| `/cases/[caseId]/overview` | 1,305,504 | 1,110,849 | 1,301,212 |
| `/cases/[caseId]/report` | 1,305,504 | 1,172,726 | 1,301,212 |
| `/compare` | 1,305,504 | 1,101,042 | 1,301,212 |
| `/cases/[caseId]/finance` | 1,357,362 | 1,112,313 | 1,339,100 |

- All 24 routes, attribution, coverage, and global budgets pass. Static total 3,813,053 / 8,000,000; largest JS chunk 606,864 / 900,000.
- The original CI build was 192 bytes larger per failing route than the local E2E-configured baseline; the table compares like configurations locally.
- The full local measurement twice hit its existing deadline at the final Commute Planner route. Final evidence uses the unchanged launcher in two serial batches of 12, with every route measured twice at both 390 and 1440. Build fingerprints and complete coverage were checked before running the unchanged analyzer and budget checker. No tracked measurement code, limits, or workflow changed.
- Requested JS on Compare contains neither Pulse nor the room reader/writer. Overview and Finance contain Pulse and the reader, without the writer. Decision Room retains its writer.
- 41 unit tests pass: 27 Pulse, 11 existing store, 3 read-only adapter. The three adapter tests failed before implementation.
- 16 targeted bundled headless Chromium tests pass, workers=1, retries=0: same-tab/cross-tab updates, real DONE save, unchanged saved-state storage on navigation, zero provider requests, zh-TW/en/ja/ko, 390/430, no overflow or score language.
- Production build, standalone typecheck, and focused lint pass (0 errors / 0 warnings).
- Independent read-only review of the extraction and final client boundaries found no blocking issues. No Pulse model, copy, CSS, navigation composition, Command Palette, or Decision Room product behavior changed.

The remaining integration step above is performed after this validation record is committed; PR #216's checks provide the resulting commit's CI state.
