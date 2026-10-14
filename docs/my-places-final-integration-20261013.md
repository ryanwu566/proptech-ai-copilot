# My Places final integration — 2026-10-13

This report records local integration and deterministic/synthetic acceptance. No push, merge or deployment was performed. Browser/regression results below are finalized before the feature commit.

PR #186 follow-up: the [Decision Room correction report](decision-room-price-race-20261013.md) records the authoritative CI failure as a premature storage read after asynchronous Save, its test-only correction, stronger regression coverage and fresh validation. The original integration counts below remain historical; the amended commit also includes that follow-up evidence.

## Identity and integration

1. Latest fetched `origin/main`: `79ed9a6d6abcd7f904dc1be6ec4d97d754e065ad`.
2. Original feature: `63e49712e4b3618bd3e0406d58ce169c791b3b26`; preserved as `backup/my-places-before-final-integration-20261013`.
3. Final integrated SHA: the single commit containing this report; resolve with `git rev-parse HEAD` after committing. The exact SHA is returned in the final chat report, avoiding a self-referential commit hash.
4. Required final topology: `origin/main` → one feature commit; verified after committing.
5. Changed files: 42 files, listed below. Dependencies are unchanged; provider calls use the existing API seam.
6. Three replay conflicts: global header retains Preference and adds Places using the small entry catalogue; workspace navigation retains localized main sections, Scenario Lab and Decision Room and adds Planner; case route layout bypasses the snapshot-writing shell for Report, Decision Room and Planner. No merge commit or blind rebase.

## Behavior and contracts

7. `/places`: direct entry, add/edit/remove/order up to 20 reusable destinations. Label, category, address, available normalized coordinates, transport mode, weekly visits and priority persist in their dedicated store. Authored text stays verbatim across locale changes. Address edits discard old normalization/coordinates.
8. `/cases/[caseId]/commute-planner`: direct entry and current case navigation; reads case identity/evidence without writing it. Explicit per-case destination selection, Calculate/Refresh, known subtotal and unknown list, provider source/check time, unavailable/stale states and case switching.
9. Persistence: version 1 at `proptech.my-places.v1` (20 places), `proptech.case-commute.v1` (200 route results, 100 case selections, 20 selected IDs each), `proptech.locale.v1` (one UI setting). Stores reject corruption, oversize documents and future versions; failed saves remain visible and preserve prior data. Route records whitelist fields on read/write, excluding credentials and raw provider payloads. No event/history store is introduced; no Saved Case/frozen evidence writer changes.
10. Modes: driving, transit, walking, through the existing Google Routes API only. Coordinate destinations take precedence, then normalized address, then authored address. Backend's mutually exclusive destination fields are preserved.
11. Weekly burden: deterministic `one-way minutes × 2 × weekly visits`, with round-trip symmetry stated in localized limitations. Frequency is an integer from 0 to 21. No LLM arithmetic, valuation adjustment, ranking or purchase verdict.
12. Unknown: missing/unresolved/unavailable, invalid, mock, fallback, partial, wrong-mode, contradictory failure reason or unconfirmed-origin evidence has nullable weekly minutes and appears in the unknown list. Valid known zero-trip evidence contributes zero; unknown zero-trip destinations remain unknown. The displayed total is explicitly the known subtotal.
13. Stale: keys bind case, property identity/address/coordinates/confirmation, place ID, destination address/normalization/coordinates, and requested mode. Changed context invalidates current status without refreshing. Historical address/mode/source/check time remain labeled stale and excluded from totals. Late responses stay attached to captured fingerprints; later batch routes stop after context changes. Case A never supplies current facts to Case B.
14. Provider behavior: zero calls on opening/editing/locale switching; Calculate/Refresh only, at most 20 destinations per action, zero-trip inputs skipped and Calculate skips usable current evidence. Exact payloads deduplicate within a batch and across concurrent callers. At most 20 distinct pending requests, 30-second client deadline with abort, no retries/background work. A fresh persisted case/selection/frequency/location/mode check prevents paid calls from outdated displayed inputs. RSC exceptions reuse main's shared classifier and require same origin, GET, `rsc=1`, `_rsc` and a known exact route; real API/external requests remain detectable.
15. Focused provider attempts: 67 explicitly initiated intercepted requests per browser (64 locale/width matrix, 1 late-response test, 2 duplicate/unavailable refreshes); 134 combined. Zero automatic requests and zero live commercial requests. Storage, context-race and keyboard checks make no provider calls. Existing map-tile fixtures in legacy case tests remain explicitly mocked and separate from analysis acquisitions.
16. Locales: zh-TW, en, ja, ko. Typed complete copy; authored labels/addresses retained. The isolated locale preference survives reload; simulated case evidence remains unmodified.
17. Widths: 390, 430, 1024, 1440 in each locale and both browsers; no horizontal page overflow. Keyboard form entry/calculation, connected labels, 3px visible focus, loading/status and storage alerts verified.

## Verification

18. Frontend: 17 focused model/locale/classifier tests; all 406 deterministic frontend tests pass. Measurement harness: 13 tests; route/source/security focused Python contract tests: 59. Typecheck passes; lint has 0 errors and 23 existing warnings. Standard production build and final optimized production E2E build pass.
19. Chromium: final focused My Places acceptance 22/22 plus the separate keyboard/labels matrix 1/1, retries disabled. Final critical regressions 157/157 pass; original broad run and classifications are documented below.
20. Chrome: final focused My Places acceptance 22/22 plus separate keyboard/labels matrix 1/1, retries disabled. Final critical regressions 157/157 pass.
21. Python: 75 focused provider/workspace/storage/locale tests pass; strongest practical full suite 3,706 passed, 32 skipped, one upstream Starlette deprecation warning.
22. Broad failures: classified individually below. Initial in-progress registry failures were corrected by the fixed supplemental entries; two obsolete locale source contracts now assert isolated persistence and no provider coupling. Initial frontend runner test started during a build without `BUILD_ID`; the final full run passes. The storage browser test's ambiguous role matched Next's route announcer; narrowing to the feature main resolves it without relaxing the error assertion.

## Performance Budget v2

| Requested item | Bytes |
| --- | ---: |
| 23. `/places` final cold production measurement | 859,534 |
| 24. `/places` fixed supplemental baseline | 859,080 |
| 25. `/places` ceiling | 1,030,896 |
| 26. Commute Planner final measurement | 1,148,774 |
| 27. Commute Planner fixed baseline | 1,148,320 |
| 28. Commute Planner ceiling | 1,377,984 |
| 29. Homepage | 1,906,909 |
| 30. Global static | 3,134,654 / 8,000,000 |
| 31. Largest client JS | 602,295 / 900,000 |

32. Existing ceilings changed? **NO**. All 12 existing route entries and global checker remain unchanged. Both new routes are required and enforce their own fixed baseline + min(20%, 300,000), without auto-ratcheting. Missing routes/attribution remain unknown and fail coverage; no borrowed/zero ceilings. The dead aggregate 3 MB homepage gate is absent.

The [asset evidence](my-places-integration-assets-20261013.json) binds cold samples to the final optimized build fingerprint; two cold contexts at each 390/1440 use synthetic populated destinations and saved cases. API/provider/prefetch traffic is blocked. The final sample uses the existing production compiler with a test API origin and is not a hosted/provider claim. First-candidate baselines remain fixed before a later 454-byte-per-route persistence-compaction increase. All 14 route gates, global budget, security/performance release gate, source/release contracts, npm production audit, existing audit exception policy, repository hygiene and diff checks pass. Homepage assets contain none of the feature store keys, `route_capacity`, or full-catalogue “Known weekly commute” marker; only the small navigation entry and locale setting join shared code.

33. Independent review: four feature Important findings reproduced and fixed: ignored normalized destination coordinates, indefinite/unbounded pending requests, pre-click fresh frequency/selection race, and extra route fields retaining credentials. A fifth Important validation finding exposed a blanket external-request fixture bypass in a legacy acceptance test; it was removed, leaving only explicit OSM raster-image fixtures. Reviewer rechecked all fixes, classifier/navigation, unchanged ceilings, final asset evidence and homepage markers; no unresolved Critical/Important/Minor findings.
34. Hosted/live-provider claims: unproven. No deployment, fresh paid Google Routes lookup, hosted persistence validation or live latency/quota acceptance was performed. Synthetic intercepted provider responses prove UI contracts and attempts, not provider availability.
35. Clean tree: post-commit check; exact result returned in the final chat.
36. Exactly one ahead / zero behind: post-commit check; exact result returned in the final chat.
37. Safe to create PR? **YES**, with the original broad-run results and classified failures disclosed. Final focused/critical regressions and all release/performance gates are green. No PR is created here.
38. Exact push command (not executed): `git push -u origin feat/my-places-multidestination-v1`.

## Broad browser outcomes and changed files

The final critical pack covers Preference, Decision Room, Scenario Lab, Overview Save/Reopen, Compare/Report, frozen manual evidence, provider-zero-call flows, pilot evidence and production responsive/accessibility acceptance: **314 passed**, 157 per Chromium/Chrome, retries 0, failures 0. With the separate My Places and keyboard/label matrices, final acceptance is **180 passed per browser**.

The original full Chromium run completed **588 passed, 69 failed, 3 intentional skips and 13 blocked serial tests**. It ran before legacy classifiers and locale expectations were corrected; it is not presented as a green full run. The [machine-readable validation report](my-places-integration-validation-20261013.json) lists and classifies every failed test individually:

| Category | Original browser failures | Evidence and disposition |
| --- | ---: | --- |
| A ? My Places regression | 0 unresolved | Four implementation findings fixed before the final pack; regression tests and review pass. |
| B ? current-main regression | 0 claimed | Three shared timing cases pass on exact clean current main `79ed9a6`, as well as this branch. |
| C ? deterministic test/readiness bug | 64 | 51 duplicated classifier false positives for complete Places RSC; 12 hardcoded Chinese unavailable expectations after persisted locale; 1 simulation storage expectation after an explicit locale-setting write. Assertions now use the shared classifier/current catalogue and permit only the exact isolated setting write. Final critical pack and locale contract rechecks pass. |
| D ? infrastructure/timing flake | 5 | Two Places cases, one demographics readiness case and two trust locale/async cases pass unchanged in focused no-retry runs; the three shared cases also pass clean main. |
| E ? unproven | 0 remaining | No unexplained broad-suite failure is omitted. |

The demographics serial suite recheck passes **17/17**, recovering all 13 blocked cases. Three Google-browser-embed cases retain their existing optional skips; no live embed/hosted/provider result is claimed. A corrected 20-test case/locale recheck initially had 17 passes and three timing/navigation failures; those same three pass isolated without retries, altered assertions or raised timeouts (31.8s, 38.5s, 41.1s). Other classifier rechecks pass 6/6 in both browsers.

Initial full Python validation exposed 14 incomplete-budget integration failures (A) before supplemental baselines were populated and two superseded runtime-only locale source contracts (C). All are fixed; final full Python is 3,706 passed/32 skipped. Initial native frontend runner verification started while the production build lacked `BUILD_ID` (C readiness/order); the final full run passes 406/406. Full source/performance/i18n contract recheck passes 65/65; measurement harness 13/13. No ceilings, retry settings, assertion deadlines or application behavior were relaxed to make a gate green.

The clean-main comparison worktree and raw local logs/JSON/browser artifacts remain under ignored `.local/my-places-integration/` for reproduction. Its source is clean and dependencies match the same lockfile; an unsupported junction was replaced by physical local dependency files before its successful production build and comparison. No shared branch or external state was changed.

Changed files:

```text
docs/my-places-final-integration-20261013.md
docs/my-places-integration-assets-20261013.json
docs/my-places-integration-validation-20261013.json
docs/my-places-multidestination-v1.md
docs/performance-budget-v2-baseline.json
docs/performance-budget-v2.md
docs/superpowers/plans/2026-10-13-my-places-final-integration.md
frontend_next/app/cases/[caseId]/commute-planner/page.tsx
frontend_next/app/places/page.tsx
frontend_next/components/commercial-global-header.tsx
frontend_next/components/experience-locale-provider.tsx
frontend_next/components/places/commute-planner.tsx
frontend_next/components/places/places-manager.tsx
frontend_next/components/places/places.module.css
frontend_next/components/workspace/case-route-layout.tsx
frontend_next/components/workspace/workspace-navigation.tsx
frontend_next/e2e/api-cost-journey.spec.ts
frontend_next/e2e/commercial-compare-report.spec.ts
frontend_next/e2e/commercial-trust-acceptance.spec.ts
frontend_next/e2e/evidence-checklist.spec.ts
frontend_next/e2e/final-production-acceptance.spec.ts
frontend_next/e2e/guided-case-simulation.spec.ts
frontend_next/e2e/helpers/provider-request.ts
frontend_next/e2e/hosted-case-market-closure.spec.ts
frontend_next/e2e/my-places-commute.spec.ts
frontend_next/e2e/preference-tradeoff.spec.ts
frontend_next/lib/api.ts
frontend_next/lib/locale-setting.test.ts
frontend_next/lib/locale-setting.ts
frontend_next/lib/my-places-copy.ts
frontend_next/lib/my-places-entry-copy.ts
frontend_next/lib/my-places-query.ts
frontend_next/lib/my-places.test.ts
frontend_next/lib/my-places.ts
frontend_next/scripts/provider-request.test.mjs
scripts/analyze_next_bundle.py
scripts/measure_route_assets.cjs
scripts/measure_route_assets.test.cjs
tests/test_experience_architecture_v3_phase5_8.py
tests/test_full_runtime_i18n_and_journey_cleanup.py
tests/test_route_budgets.py
tests/test_runtime_i18n_coverage.py
```
