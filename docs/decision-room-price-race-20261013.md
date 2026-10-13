# PR #186 Decision Room save-completion correction

## Proven cause and correction

This is a **test readiness race**. The [authoritative GitHub browser job](https://github.com/ryanwu566/proptech-ai-copilot/actions/runs/38391187108/job/115275931420), on remote head `c838076069edbacd05d72095fa71b5071ff68a87`, failed the raw storage assertion at `decision-room.spec.ts:288`: Expected 2350 / Received 2390. The preceding input-value assertion of 2350 had already passed. All three attempts in each browser failed at that persisted-value assertion.

The Save click starts an asynchronous handler. The repository awaits `navigator.locks.request` before validating the latest revision and writing storage. Playwright's completed click does not imply that this asynchronous save has finished. The test read the previous stored 2390 before persistence completed; that observation does not establish that the UI draft reverted.

The exact existing test now waits for the existing room status **“Saved in this browser”** after Save and before reading storage. Both exact assertions remain: stored price 2350 and source note “Latest written quotation”. Explicit reload clears `savedAt`, and the pending/error paths do not display saved success, so this wait cannot match a previous operation's success.

Product code is unchanged. Temporary dirty-state instrumentation and a speculative draft controller were discarded after the authoritative failure location contradicted the initial diagnosis. Natural local repetitions passing before the correction are not presented as a deterministic reproduction of a UI race.

## Deterministic characterization and invariants

The added browser regression acquires the actual case room Web Lock from the second tab. While the first tab's save waits, its disabled price input remains exactly 2350 and storage remains exactly 2390 with the newer source note. Temporarily expecting persisted 2350 at that point reproduced the CI's Expected 2350 / Received 2390 in both browsers on the unchanged product. The final test releases the lock in `finally`, waits for saved success, and asserts the exact merged asking-price object. No sleep, raised timeout, retry change, application hook or relaxed assertion is used.

The existing `mergeRoomRecord` compares the draft with its original base and applies only edited fields to the latest explicitly loaded record. Consequently an edited price remains local while an untouched source note comes from the latest room at save. An edited source note likewise survives a later external price/date update. Optimistic revision checks and the room lock still reject stale writes; the test also attempts Save during a conflict and verifies the stored bytes do not change.

The new regression verifies:

| Invariant | Evidence |
| --- | --- |
| Pristine reload adopts latest price | 2390, then a subsequent 2450 update |
| Dirty price survives newer provenance and explicit reload | Input remains 2350 |
| Untouched provenance merges on save | Exact stored 2350 + latest source note + source URL |
| Dirty source note survives external update | Buyer-authored note + latest 2550 and checked date |
| Successful save resets dirty state | Following external price/note reload refreshes pristine inputs |
| Stale tab cannot overwrite silently | Conflict Save preserves newer room bytes |
| Case switching does not leak a draft | Next Links A → Cases → B overview → B room → Cases → A overview → A room; a window sentinel proves navigation stays in the same document; B is blank and A restores its saved values |
| Persistence/provider boundaries remain intact | Core saved-case bytes unchanged; zero provider requests across both tabs |

## Final validation

All browser runs use `--retries=0` with the existing assertion deadlines and test timeout. The final Decision Room run includes the stronger client navigation check. My Places tests and application behavior are unchanged by this correction.

| Check | Result |
| --- | --- |
| Exact previously failing test, Chromium | 20/20; 0 retries, failures or flaky results |
| Exact previously failing test, Chrome | 20/20; 0 retries, failures or flaky results |
| Full Decision Room, Chromium | 31/31 |
| Full Decision Room, Chrome | 31/31 |
| Full My Places/commute, Chromium | 23/23, including keyboard/label matrix |
| Full My Places/commute, Chrome | 23/23, including keyboard/label matrix |
| Frontend deterministic suite | 406/406 |
| Relevant Decision Room store/adapter tests | 13/13 |
| Practical full Python | 3,706 passed, 32 existing skips, one upstream Starlette warning |
| Final Python source/security/release/route contracts | 94/94 |
| Route measurement harness | 13/13 |
| Standard production build and production-mode E2E build | Pass after restoring original product code |
| Typecheck | Pass |
| Full lint | 0 errors, 23 existing warnings |
| Changed browser spec lint, explicitly including ignored E2E path | Pass; 0 errors/warnings (`--no-ignore`) |
| Route/global/security/release/hygiene/diff gates | Pass |
| Production operations contract and local provider-free smoke | Pass; smoke reports `external_provider_called=false` |
| Production dependency audit | 0 vulnerabilities |
| Existing complete npm audit policy | Pass with existing dev-only GHSA-vfj7-8cjw-p6xm exception, expiring 2026-11-04 |
| Independent final review | No Critical, Important or remaining Minor findings |

The release gate's `--skip-tests --skip-frontend-build` avoids duplicating the independently completed full Python and production build; its source checks all pass. Operations gate success verifies repository contracts; its existing external guardrails remain BLOCKED / production decision NO_GO. No deployment or fresh hosted CI result is claimed.

## Performance Budget v2

Fresh cold production measurements are committed in [asset evidence](decision-room-price-race-assets-20261013.json). All 14 registered routes pass against unchanged fixed baselines/ceilings. The final product build has exactly the same measured asset sizes as the pre-correction integration:

| Item | Bytes | Ceiling |
| --- | ---: | ---: |
| `/places` | 859,534 | 1,030,896 |
| `/cases/[caseId]/commute-planner` | 1,148,774 | 1,377,984 |
| `/cases/[caseId]/decision-room` | 1,176,751 | 1,409,828 |
| Homepage | 1,906,909 | 2,066,966 |
| Global static assets | 3,134,654 | 8,000,000 |
| Largest client JS | 602,295 | 900,000 |

Build ID: `aCh7hp931X0dSjTp-Q6WP`; fingerprint: `5ce9a1fc25337debe6a4d031c790e98ae4e385af8e7728551ad0d5acc793a813`. The browser measurement uses the existing populated synthetic cases/destinations and blocks provider/API requests. No budget baseline, checker, My Places logic, finance test or evidence-checklist test changes belong to this correction.

## Reproduction and integration

From `frontend_next`, after `npm run build:e2e`:

```powershell
node e2e/run-e2e.cjs e2e/decision-room.spec.ts --project=chromium --project=chrome --workers=2 --retries=0
node e2e/run-e2e.cjs e2e/decision-room.spec.ts --grep 'reload refreshes pristine asking price and preserves untouched newer provenance' --repeat-each=20 --project=chromium --project=chrome --workers=1 --retries=0
node e2e/run-e2e.cjs e2e/my-places-commute.spec.ts --project=chromium --project=chrome --workers=2 --retries=0
```

Compact machine-readable results are in [validation evidence](decision-room-price-race-validation-20261013.json). Raw local JSON/logs and the temporary red probe remain under ignored `.local/decision-price-race/`.

Base/fetched main: `79ed9a6d6abcd7f904dc1be6ec4d97d754e065ad`. Original remote head is preserved by `backup/my-places-before-decision-price-race-20261013`. The existing feature commit is amended; the final amended SHA and clean 0-behind/1-ahead check are returned in the final task response. No second feature commit, push, merge or deployment is performed.

Manual push command, **not executed**:

```powershell
git push --force-with-lease=refs/heads/feat/my-places-multidestination-v1:c838076069edbacd05d72095fa71b5071ff68a87 origin HEAD:refs/heads/feat/my-places-multidestination-v1
```
