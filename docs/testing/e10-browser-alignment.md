# E10 browser acceptance alignment

Base: `c1638c5b9ef632c28cf03db81c754dd1626221e0`, branch `feat/commercial-uiux-v1`, PR #162.

The cancelled GitHub browser job was a real test failure run. Its log declares 918 cases and contains 51 distinct failing scenarios before cancellation. The local full gates also exposed one initial-focus readiness race and one browser-context teardown incident. Every observed failure is individually recorded in [the failure inventory](e10-observed-browser-failures.csv).

| Observed failure category | Distinct scenarios | Classification | Current coverage |
| --- | ---: | --- | --- |
| Aegis primary sidebar entry | 9 | Stale test contract | Methods entry; eight invalid-input/no-request branches; bounded disclaimer |
| Locale sidebar layout | 4 | Stale test contract | Labelled global navigation, saved cases and Methods in four locales |
| Implicit default journey in causal tests | 15 | Stale test contract | Explicit optional finder; identity, invalidation, races, save/reopen and failure isolation |
| Homepage demo banner | 1 | Stale test contract | Methods reference demo; actual edits, calculation and evidence output |
| Old homepage heading in demographics | 1 | Stale test contract | Explicit finder and Location; all demographic state and race cases preserved |
| Terrain sidebar/mobile drawer | 10 | Stale test contract | Methods; point-reference bounds, tiles/CSP, coordinates, locales and 390px |
| Primary five-step journey contract | 11 | Stale test contract | Current Home, saved-case domains and outputs; optional decision semantics |
| Initial focus assumed ready after page load (local full gate) | 1 | Stale test readiness contract | Await shell's initial heading focus; require Methods focus and keyboard-open state; retain tool and output assertions |
| Browser context teardown timeout in an unchanged spec (final full gate) | 1 | Harness teardown incident; outside the stale UI / real E10 regression distinction | Product assertions did not fail; retry and installed Chrome passed; additional repetitions verify the unchanged case |

Source inspection established the supported paths before test edits. Browser verification then exercised the underlying capabilities. No runtime regression was demonstrated, and no runtime file changed. The focus race's exact timing is an inference: the initial attempt had no trace, its disclosure stayed closed, retry passed, and the shell source schedules a competing initial focus operation. The fix waits for that existing initialization and strengthens keyboard assertions without sleeps or larger timeouts.

The 18 guided acceptance cases were replaced one for one. Obsolete button counts, five primary labels and the mobile wizard layout are retired. Their behavioral equivalents now verify address entry, the real optional finder, Overview / Market / Location / Risk / Finance navigation with one saved identity, price and valuation availability, route evidence, loan and holding costs, decision attention and unknown states, Report / Compare, four-locale Home navigation and 390px reachability. The optional decision readiness count, price status, attention and localized content remain covered.

Other audited obsolete contracts included market helpers and roundtrips, smoke navigation and hero placement, Aegis scenario score/status copy, localized Methods names, cadastral upload return navigation, identity propagation, neutral source language, TaxOracle demo and pilot invitations, and hosted/provider navigation. Pilot now follows Methods → demo calculation → evidence center → invitation, preserving consent, privacy, publication review and deletion bounds.

No suite was deleted, no skip or exclusion was added, and retries/timeouts were unchanged. Provider isolation, numeric assertions, no-request validation and causal-state assertions remain. The shared fixture still rejects unexpected deterministic API requests. Existing `@hosted` / `@real-provider` exclusions remain; hosted-only changes were reviewed statically, and the untagged accessibility/navigation cases were executed.

| Verification | Final result |
| --- | --- |
| Affected Chromium | 271 distinct scenarios passed, 0 failed, 0 skipped; corrected suites supersede their earlier failed runs; includes all 14 commercial UI cases after the focus fix |
| Affected installed Chrome | 271 passed, 0 failed, 0 skipped; includes the 257-case run and all 14 commercial UI cases after the focus fix; both exit 0 |
| Keyboard focus stability | 10 additional repetitions passed in each browser, 0 failed, 0 flaky; original retries retained |
| Unchanged stale-identity case after teardown incident | 10 additional repetitions passed in each browser, 0 failed, 0 flaky; no test or runtime repair |
| TypeScript | Exit 0 |
| ESLint | Exit 0; 0 errors, 24 warnings in unchanged files |
| Independent coverage review | Completed; scoped Methods summary issue corrected; no remaining actionable findings |
| Full Production Release Operations browser command | Completed on final code, exit 0; 911 passed, 0 failed, 1 flaky, 6 existing skips; all 918 distinct cases reached final results; reported duration 1.8h |

The full command is unchanged from CI, with `CI=true`, `NEXT_PUBLIC_API_BASE_URL=http://e2e.test` and `NEXT_PUBLIC_APP_ENV=test`:

```powershell
npm --prefix frontend_next run test:e2e -- --workers=1
```

The first full run completed with exit 0: 911 passed, 1 flaky and 6 skipped, accounting for all 918 cases. The one flaky case exposed the focus-readiness issue described above. After fixing and verifying it, the entire CI command is rerun on the final test code. The six skips are existing Google Maps browser-key conditions in an unchanged spec, three per browser; none was added by this work.

The final full run's one flaky case was `commercial-workspace-property-context.spec.ts:88`: `Tearing down "context" exceeded the test timeout of 30000ms` and `browserContext.close: Test ended`. No product assertion failed. Its initial attempt reports 1.3h, and the complete runner reports 1.8h; the cause of that long interruption is unproven. Its original retry passed in 3.1s and Chrome passed in 1.6s. Ten additional repetitions then passed in each browser, with no failures or flakies. This is recorded separately from the 52 stale UI/readiness contracts, without claiming an E10 defect or hiding the flaky result. Neither that spec nor browser configuration was changed. Both keyboard cases passed on their first attempts in the final gate.

Local raw evidence is retained in `.local/e10-browser-alignment/`: `github-browser.log`, `baseline-representatives.log`, `affected-chromium.log`, `affected-followup-chromium.log`, `affected-chromium-final-results.json`, `affected-chrome.log`, `commercial-uiux-chromium.log`, `commercial-uiux-chrome.log`, `keyboard-repeat-chromium.log`, `keyboard-repeat-chrome.log`, `full-ci-browser.log`, `full-ci-browser-final.log`, `full-ci-browser-final-results.json`, `focus-initial-error-context.md`, `context-teardown-error-context.md`, `context-repeat-chromium.log`, `context-repeat-chrome.log`, `lint.log`, and `typecheck.log`. Earlier failed runs document reproduction and test-authoring corrections; final status is determined by the subsequent complete verification.

Files changed are listed below. The helper and documentation are new; the 29 spec files are modified. Application code, fixtures, Playwright configuration, package files and GitHub workflows are unchanged.

- `docs/superpowers/plans/2026-10-08-e10-browser-alignment.md`
- `docs/testing/e10-browser-alignment.md`
- `docs/testing/e10-observed-browser-failures.csv`
- `frontend_next/e2e/aegis-real-form-acceptance.spec.ts`
- `frontend_next/e2e/b2-b5-locale-recertification.spec.ts`
- `frontend_next/e2e/closed-loop-causal-ab.spec.ts`
- `frontend_next/e2e/commercial-uiux.spec.ts`
- `frontend_next/e2e/competition.spec.ts`
- `frontend_next/e2e/demographics-insight.spec.ts`
- `frontend_next/e2e/geospatial-evidence-cadastral-tgos.spec.ts`
- `frontend_next/e2e/guided-journey-real-ui-acceptance.spec.ts`
- `frontend_next/e2e/helpers/commercial-navigation.ts`
- `frontend_next/e2e/i18n-smoke-runtime.spec.ts`
- `frontend_next/e2e/journey-identity-propagation.spec.ts`
- `frontend_next/e2e/market-final-closure.spec.ts`
- `frontend_next/e2e/market-insight-analysis.spec.ts`
- `frontend_next/e2e/market-insight-east-west-identity.spec.ts`
- `frontend_next/e2e/market-insight-metric-semantics.spec.ts`
- `frontend_next/e2e/market-search-submit.spec.ts`
- `frontend_next/e2e/market-segmentation-comparables.spec.ts`
- `frontend_next/e2e/market-ui-certification.spec.ts`
- `frontend_next/e2e/nongeo-final-ux-cert.spec.ts`
- `frontend_next/e2e/parcel-geometry-upload.spec.ts`
- `frontend_next/e2e/pilot-evidence.spec.ts`
- `frontend_next/e2e/production-reality-trust-ui.spec.ts`
- `frontend_next/e2e/production-smoke.spec.ts`
- `frontend_next/e2e/real-provider-ui.spec.ts`
- `frontend_next/e2e/release-smoke.spec.ts`
- `frontend_next/e2e/ris-hosted-acceptance.spec.ts`
- `frontend_next/e2e/taxoracle-human-presentation.spec.ts`
- `frontend_next/e2e/terrain-map-ux-performance.spec.ts`
- `frontend_next/e2e/trust-closure-regression.spec.ts`
- `frontend_next/e2e/valuation-holding-reliability.spec.ts`
