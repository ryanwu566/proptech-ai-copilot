# Decision Room asking-price race correction

> Execute inline using systematic debugging and verification-before-completion. Obtain an independent read-only review of the final fix.

**Goal:** Prove and correct PR #186's asking-price failure while preserving per-field provenance and exactly one feature commit.

**Spec:** User's PR #186 CI failure request (2026-10-13). Verify the proposed dirty-state hypothesis against the authoritative failure location. Locally edited 2350 must survive reload, and successful persistence must merge the latest untouched provenance.

**Constraints:** No My Places or route-budget changes; no sleeps, retries, raised timeouts or weakened assertions; preserve optimistic cross-tab conflict and latest untouched provenance; amend c838076 only; no push.

- [x] Verify clean tree, exact remote/base topology and create pre-amend backup.
- [x] Inspect authoritative GitHub logs and reproduce the premature storage expectation with a real held Web Lock; remove speculative product changes and temporary instrumentation.
- [x] Synchronize the exact existing test with the existing save-success signal, retaining its exact stored-price and provenance assertions. Add real-lock coverage for pending/completed persistence, pristine reload, dirty price/note merges, successful reset and subsequent external update.
- [x] Verify case isolation through application client navigation, unchanged saved-case bytes and zero provider calls.
- [x] Run full Decision Room and My Places suites in Chromium/Chrome, retries disabled; repeat the exact previously failing test at least 20 times per browser.
- [x] Run frontend deterministic/store tests, full practical Python, production build/typecheck/lint and unchanged route/global/security/release/hygiene gates.
- [x] Independently review and document proven cause/results and exact force-with-lease command without executing it.

Final actions: amend the existing commit and verify clean 0 behind/1 ahead; exact SHA/topology are recorded in the final task response.

## Ledger

- Base and latest fetched main: 79ed9a6d6abcd7f904dc1be6ec4d97d754e065ad.
- Current/remote feature: c838076069edbacd05d72095fa71b5071ff68a87; clean, 0 behind/1 ahead.
- Backup: backup/my-places-before-decision-price-race-20261013.
- Original PriceForm is byte-identical on main. Initial dirty-state instrumentation and speculative changes did not establish the CI sequence and were removed.
- Authoritative browser job 115275931420 (run 38391187108, head c838076) fails at the raw persisted-price assertion, line 288, after the UI 2350 assertion already passed. Save awaits `navigator.locks.request`; Playwright click does not await the asynchronous handler.
- A real held room lock reproduces Expected 2350 / Received 2390 in both browsers while the input remains 2350. The final regression expects pending storage 2390, releases the lock in `finally`, then checks successful persistence of exact price 2350 plus latest untouched provenance.
- Proven correction is test save-completion synchronization. Product PriceForm/store, My Places, finance/checklist tests, deadlines, retry configuration and budget ceilings remain unchanged.

- Final browser evidence: Decision Room 31/31 each browser with client A-B-A navigation; My Places/commute 23/23 each; exact original test 20/20 each, retries 0, failures/flaky results 0.
- Final regressions: frontend 406/406; store/adapter 13/13; Python full 3,706 passed/32 skipped; final contracts 94/94; measurement harness 13/13; production/E2E builds, typecheck, lint and all unchanged gates pass.
- Final independent review: no Critical, Important or remaining Minor findings.
