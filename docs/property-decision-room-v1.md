# Property Decision Room v1

Each saved case has `/cases/[caseId]/decision-room`, entered through a localized link in the case workspace. The room supports viewing notes, editable viewing checklist items, questions, follow-up tasks, owner/due date/resolution, manual verification records, manual asking price and provenance, evidence gaps, and activity history. New interface text supports zh-TW, English, Japanese, and Korean. User-authored content is preserved as written.

## Persistence and current Saved Case boundary

`frontend_next/lib/decision-room-store.ts` owns the separate `proptech.decisionRoom.v1.<encoded-caseId>` browser-local document. No changes were made to `case-storage.ts`, `case-repository.ts`, `case-snapshot-save.ts`, or the core case schema. `decision-room-case-adapter.ts` consumes only diagnostic reads and subscriptions from the existing repository. The adapter uses current main diagnostic reads/subscriptions after PR #181; room data does not enter saved-case snapshots.

Limits are 50 viewing notes, 100 combined checklist/question/task items, 100 manual check records, the latest 200 activity events, and 1.5 million serialized characters per room. Invalid, oversized, corrupt, unsupported, blocked, full, and conflicting saves are surfaced. Corrupt or unsupported documents are preserved. Activity is derived from successful persisted changes, and no-op saves do not create events.

Browser writes acquire a per-case Web Lock, then recheck case availability and room revision before writing. Another tab's change requires explicit reload. Untouched fields merge from the latest document; pending and removed-record drafts survive reload/read failures. Inputs are disabled while a save is pending. Without Web Locks, saves fail closed. The adapter remains read-only.

## Evidence boundary

Manual checks require a topic, user-written source/check note, actual checked date, and checker. Source URLs accept only HTTP/HTTPS without embedded credentials. Manual outcomes are `user_checked` or `needs_follow_up`; neither establishes official verification. Resolved questions/tasks require a resolution. Completing work never upgrades saved evidence, legal identity, or risk states. The gap summary derives missing provenance, open work, and saved evidence limitations; it is not a score. No providers or AI fact generators are called.

## Historical feature validation — 2026-10-12

- All native frontend library tests: **249 passed**.
- E2E runner ownership test: **1 passed**.
- Focused Python case storage, manager, evidence, due diligence and accessibility regressions: **24 passed**.
- Production Chromium browser tests: **54 passed**, including **29 Decision Room tests**, 13 overview tests, and 12 comparison/report tests. All 16 locale × viewport combinations passed at 390/430/1024/1440 pixels with screenshots. The 390 and 1440 screenshots were visually inspected.
- Production E2E build, TypeScript check, changed-file ESLint and whitespace checks passed.
- Browser checks covered editable records, reload/case isolation, source URLs, required resolution, retained drafts, quota retry, corrupt/missing cases, pristine/dirty price reload, overlapping writes, remote record deletion, and case deletion while waiting for a lock. The complete room workflow produced zero requests to the configured provider API and left the core saved-case bytes unchanged.

Reproduce from `frontend_next` with `npm run build:e2e`, then:

```powershell
$files = @(rg --files lib -g '*.test.ts' -g '*.test.mjs')
node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test @files
npm run test:e2e:runner
node e2e/run-e2e.cjs e2e/decision-room.spec.ts e2e/commercial-overview-save.spec.ts e2e/commercial-compare-report.spec.ts --project=chromium --workers=2 --retries=0
npm run typecheck
```

The browser runner owns its server and selects an available port. Development mode under the existing CSP is unsuitable for this acceptance run; production output was tested without relaxing CSP.

## v1 limits

Data is specific to this browser/device, with no cloud or cross-device sync. Clearing browser storage removes it. Removing a saved case makes its room inaccessible; sidecar data is retained independently, so restoring the same case ID reopens its room. Activity history records Decision Room edits only. Manual price is a separate room record and does not change saved valuations or finance calculations. Source URLs are opened only at the user's request, and their authenticity is not automatically checked.

## Final integration — 2026-10-13

Authoritative base: `0185c81416a56b14c1dada38d959d90aeac2ecf4`, including PRs #181, #182, #185 and #183. Historical feature: `ee0c881a3dc5ab4c03b8231956aafbd9e46f6b6d`, retained at `backup/decision-room-v1-before-integration-20261013`. Only that feature commit was replayed. The sole textual conflict was shared workspace navigation: Scenario Lab and Decision Room were both retained. The original client link into Decision Room is preserved so entering it retains the selected in-session locale.

The room reuses current `WorkspaceNavigation` for Case sections, Scenario Lab, Compare, Report and Planning. Its independent route deliberately bypasses the snapshot-writing provider shell, as Report already does. Preferences remains reachable through existing global navigation. There is one shared Case navigation model; no Case writer or evidence schema was changed.

Shared section/output labels now switch with the four supported locales. Only lightweight navigation labels enter shared workspace bundles; the operational room catalogue remains within the room route. User text is never translated or rewritten.

### Performance Budget v2

`analyze_next_bundle.py` and the cold-browser measurement registry include `/cases/[caseId]/decision-room`, with populated editor and selected-case validation. The route is required. Missing attribution produces unknown bytes and a failing gate; an absent required route fails coverage.

The fixed supplemental baseline is **1,174,856 uncompressed bytes**, measured from the first actual integration candidate at 390/1440 pixels, two cold contexts per width. The pinned build ID, fingerprint, route file list and measured bytes are recorded in `performance-budget-v2-baseline.json`. The baseline remains fixed after the client-navigation correction: it is not regenerated from subsequent measurements. Existing policy produces **1,409,828 bytes** (`baseline + min(ceil(20%), 300,000)`). All existing route budgets remain identical to current main; global protections remain 8,000,000 static bytes and 900,000 bytes for the largest client JS.

### Provider and evidence contract

Acceptance uses main's shared request classifier. Only recognized same-origin GET navigation with both `rsc: 1` and `_rsc` is treated as internal route traffic. External requests, arbitrary fetch/XHR, APIs, unknown routes and POST remain counted. Classifier regressions cover these distinctions. Decision Room does not import analysis/provider clients.

Manual source URLs and checked dates are user metadata. Required dates are entered by the user; absent optional dates/URLs remain absent. A manual check never establishes government/provider/cadastral/title/legal verification. A manual asking price remains a separate sidecar assumption, not a transaction, comparable, valuation, accepted offer or recommendation. No overall score or buy/no-buy verdict is generated. Unknown evidence remains unknown after manual work.

### Independent review

A separate read-only reviewer examined case isolation, corruption/conflicts, URLs, evidence/price semantics, unknown values, history bounds, provider calls, keyboard/mobile risks and bundle boundaries. No Critical, Important or concrete Minor defect was found. A supplemental review confirmed all previous budget fields are unchanged, the fixed evidence matches the first analyzer output, absent required routes fail and one byte over the ceiling fails. Browser acceptance additionally caught and fixed the integration's plain-anchor locale reset. Native date-input Tab segments were corrected in the new keyboard test without increasing timeouts or retries.

The reviewer also checked the final shared localization catalogue and cross-tab test readiness changes. The latter waits for the second tab's persisted UI and brings the first tab forward before asserting the conflict; retained-draft and merge assertions remain intact.

### Final validation evidence

- Focused Decision Room models: **13 passed**. All frontend library models: **269 passed**. Frontend script tests: **122 passed**; root measurement scripts: **11 passed**. GIS workspace contract and 35 VNext hardening checks passed.
- Typecheck, full ESLint (**0 errors, 23 existing warnings**), optimized production E2E build, whitespace and repository hygiene checks passed. The same Next production compiler is used with explicit test origins and synthetic fixtures; CSP was not relaxed.
- Final focused production browser pack: **240 passed**, **120 Chromium + 120 Chrome**, retries disabled. This includes **30 Decision Room tests per browser**, Saved Case, Preference, Scenario, Compare/Report, provider closure and pilot regressions.
- Decision Room passed all **4 locales x 4 widths x 2 browsers**: zh-TW/en/ja/ko at 390/430/1024/1440. No document overflow; shared navigation, direct entry, reload, keyboard workflow, source validation, corruption/quota errors, case isolation, stale writes and lock races passed. Complete manual workflow and navigation produced **zero provider/API requests** and preserved core Saved Case bytes. 390/1440 screenshots were visually inspected; final localized screenshots are retained in ignored local acceptance artifacts.
- Full Python: **3,704 passed, 32 skipped**, one existing FastAPI/Starlette deprecation warning. Focused final workspace/security/budget checks are also recorded in the companion validation JSON.
- Full practical Chromium suite before final label-only adjustment: **642 passed, 3 skipped, 6 failed**. All failures are retained and classified below; no test was deleted, hidden, or given additional retries/timeouts.
- Final cold production assets: Decision Room **1,175,717**, homepage **1,906,096**, global static **3,097,889**, largest client JS **602,295** bytes. Route/global/security-performance gates pass against the fixed supplemental baseline. Homepage assets exclude the room store/editor/title markers. Detailed fingerprint, files and all measured routes are in `decision-room-integration-assets-20261013.json`.
- Release source-contract gate passed with `--skip-tests --skip-frontend-build`, as in CI; those validations ran separately above. npm audit policy passed using the existing dev-only exception expiring 2026-11-04; no dependency/policy changes. The optional pilot orchestrator's default non-executing invocation reported `not_run`; its browser tests were run in the final pack, and no aggregate pilot-orchestrator success is claimed.

### Failure classifications and remaining limits

- **A, corrected:** replacing the room entry with a full-page anchor reset the locale; restoring its original Next client link preserves the in-session selection.
- **C, corrected test assumptions:** the new keyboard test assumed a native date input has one Tab stop. The cross-tab test asserted the first tab before confirming the second tab's completed save/foreground readiness. Both keep their original functional assertions and pass in the final zero-retry pack.
- **B, reproduced on clean main:** `guided-case-simulation.spec.ts`'s 390/1024/1440 all-stage/all-locale tests exceeded their existing 30-second test limit. All three fail identically on detached `0185c81416a56b14c1dada38d959d90aeac2ecf4`; these tests and the demo implementation are unchanged by this branch.
- **D, timing inference:** the three Japanese local Hosted Case matrix failures (390/1024/1440) exhausted 90 seconds during reload/report/screenshot work. All three passed clean main and all three passed this branch on isolated zero-retry recheck (37.6/37.6/38.6 seconds). The original parallel-run failures remain recorded; their exact infrastructure trigger was not proven.
- **D, infrastructure navigation:** one repeated cross-tab diagnostic timed out in the initial `page.goto` at 60 seconds with `ERR_ABORTED`, before editing or saving. Two repeated checks passed, the unchanged original isolated check passed, and both final browser critical packs passed after readiness correction. No successful persistence claim is inferred from that failed run.

The broad Chromium run remains non-green because of the recorded failures. The final feature/cross-feature pack is green. `decision-room-integration-validation-20261013.json` records commands, counts, categories and the limits of attribution; this is local PR integration evidence, not a hosted release certification.

### Acceptance limits

Local synthetic saved-case acceptance does not prove hosted or production deployment, real provider data, cloud persistence, cross-device behavior, legal facts or source authenticity. No push, merge, deployment or live-provider certification was performed. A source link can be opened explicitly by the user; mounting and editing the room do not open it automatically.
