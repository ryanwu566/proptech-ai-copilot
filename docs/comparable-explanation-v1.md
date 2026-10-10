# Comparable Explanation V1

Starting SHA: `8469c1f22b64a0e03be03a0099c59a8483d9e0c8`.
Worktree: `C:/Projects/proptech-comparable-explanation`; branch: `feat/comparable-explanation-v1`.

The starting SHA above and the original acceptance ledger below describe the first implementation. PR #175 has subsequently been integrated onto newer main, currently `0b2e74a87adfc0f0bac57d30afedff7955233d61`; current-base validation is recorded in the integration ledger at the end of this document. Earlier acceptance numbers are historical checkpoints rather than substitutes for validation after main's frontend changes.

## Design and implementation plan

Goal: expose existing deterministic comparable decisions without changing selected rows, weights, confidence, or valuation prices. Use Python selection instrumentation, a bounded JSON projection, native accessible disclosures, the existing locale context, and the existing saved-summary/report pipeline. No new dependency, provider request, ML, adjustment, or persistence store.

- [x] Capture fixed-date demo and official-provider valuation baselines and ordinary production asset size.
- [x] Add RED Python tests for actual scope/window/eligibility/outlier/rank decisions, unknowns, fallback, bounds and deterministic order. Instrument those decision points; preserve baseline outputs.
- [x] Add RED native TypeScript tests for safe trace projection, repeated save/reopen and frozen report evidence. Add optional versioned trace to the existing valuation summary whitelist.
- [x] Add localized Market inclusion/exclusion disclosure and concise frozen Report summary. Preserve existing evidence gaps; explanation never verifies evidence.
- [x] Validate focused/full suites, build, audit, unchanged budgets, release/security/hygiene gates and both browsers at 390/1024/1440 px. Inspect A4 PDF output.
- [x] Independent read-only trust review, fixes and final changed-file inventory. Finish with exactly one local commit; preserve this branch/worktree. No push/merge/deploy.

Review focus: restored outliers must explain their final inclusion; absent provider attributes must not become zero; counters cover only returned candidates; old snapshots must never reconstruct missing trace; report trace must freeze with its evidence fingerprint.

## Existing architecture

PLVR import/read models feed BLUE PostgreSQL or the opt-in compact GREEN adapter. Both bound acquisition to 200 district candidates; SQL filters period/geography (and BLUE finite-positive official metrics) before LIMIT. The service then enforces source, positive price/total/area, rolling 36-month UTC eligibility and road-first scope (minimum three rows), with district/city fallback. Demo uses community (600 m), road/district/city/fallback hierarchy.

Scoring uses location, normalized building type, area, age, approximate straight-line distance and recency. Service ordering uses road/source, building type, absolute area difference, transaction period and similarity. IQR filtering uses Q1/Q3 +/- 1.5 IQR, may preserve official rows, and restores all scored candidates if fewer than three remain. Final selection retains at most ten. Prices use the existing weighted mean/median and P25/P75 calculation unchanged.

Floor, parking, duplicate identity and transaction-target classification are not selection filters in this engine. They must not acquire invented exclusion reasons. Acquisition exclusions are not observable from delivered rows; SQL-wide counts remain unknown. Existing adapter age/floor zero coercion is retained for valuation compatibility and separately marked missing for explanations.

## Validation ledger

### Trace architecture and rules

`ComparableDecisionTrace` observes the existing preparation, geographic scope, IQR result and final ranking decisions. It never selects a candidate or computes a valuation adjustment. Request-local ordinals distinguish repeated observations without fabricating a duplicate filter. Only these public comparison values cross the boundary: location, normalized comparable building type, area, known age, approximate distance, period/age in months, price, known floor, unknown parking and community reference distance. No raw note, provider payload, source identifier, coordinates or credentials are retained.

The thirteen explained criteria are: official source; required finite-positive area/total/unit metrics; official 36-month window; geographic hierarchy and its three-row minimum; demo community 600 m radius; road/source ranking priority; normalized building-type ranking/score; area ranking/score; age weighting; approximate target-distance weighting; period ranking/weighting; IQR outliers and restoration policy; final ten-row cap. Floor and parking are context only. A type/area mismatch is a ranking difference, never an invented hard exclusion. The composite similarity tie-break and weight formula are disclosed, not sold as confidence.

Each candidate has an inclusion/exclusion status, deterministic reason codes, target/comparable/difference fields, stage role and actual numeric bounds where applicable. Early rejected rows label unreached ranking dimensions as context. Counters count rows received by this service; overlapping reasons may sum above the excluded count. Five first-observed exclusions are retained in deterministic decision-stage/input order, not advertised as nearest or exhaustive. All final selected rows (at most ten) receive explanations. Output and durable storage retain at most fifteen safe candidate projections; no audit log is accumulated.

Eligibility/time/scope reasons are recorded during their real decisions. Outlier exclusions are finalized only after the existing restoration branch; candidates restored to the valuation are never described as excluded. SQL acquisition filters and its 200-row cap are unchanged; unseen transactions, exclusion counts and censuses remain unavailable. Provider acquisition cannot be rerun by opening this disclosure.

### Save/Reopen/Compare/Report and trust

The optional `comparable_decision_trace` is added to the existing actionable-valuation summary whitelist. Full raw `comparables` still remain session-only. Runtime projection validates version, roles, periods, bounded arrays, unique observation IDs, totals, selected-count agreement with valuation samples, and reason counters against example frequencies. It removes unknown fields; malformed traces become unavailable. Missing numeric values remain null and genuine zero remains zero. Adapter missing-field metadata preserves unknown age/floor despite their inherited valuation defaults. Parking stays unknown, with no new deductions.

Repeated compaction preserves the trace byte-for-byte in semantic JSON. `CaseEvidenceModel.comparableExplanation` becomes part of the existing content fingerprint. Report freezes it with the original case evidence, notices newer snapshots, and replaces it only through the existing explicit newer-load action. Compare still consumes the existing saved evidence model. No second checklist is created; the existing missing raw-comparable evidence gap remains, and explanation rendering never verifies an item. Old saved cases lacking a trace get localized unavailable text rather than reconstruction or refresh. Non-actionable valuations retain the existing rejection/storage boundary; their trace can be inspected in the API but is not promoted into usable saved valuation evidence.

The official window reference uses the engine's UTC month; recency uses its existing server-local `date.today()` month. Both references are frozen separately and explicitly labeled. The browser date is not used. Distances use the existing approximation `round(111000 * sqrt(delta_lat² + (0.91*delta_lng)²))`, with no walking/road-distance claim. Only demo community scope has a 600 m cutoff, measured from its community reference, separately from target distance.

All new prose/resources support zh-TW, en, ja and ko through the existing `ExperienceLocaleProvider` and route-local localized resources. Locale changes re-render the whole explanation. Canonical calculations remain ping/metres/months; the current workspace has no selectable area-unit preference. Display reuses `formatAreaPing` precision and localized unit labels, with no parallel conversion or price normalization.

### Baseline and automated validation

Fixed reference date: 2026-10-10. Eight baseline cases captured before service edits preserve exact selected rows/order, weights, confidence, price distribution, unit/total estimates and range: official, missing source age/floor/distance, scope, outlier, no data, demo road, demo community and demo district. No numeric valuation changes were accepted.

| Case | Before total (NT$10k) | After total (NT$10k) |
|---|---:|---:|
| Official top ten | 1,926.0 | 1,926.0 |
| Unknown attributes | 1,836.0 | 1,836.0 |
| Scope | 1,836.0 | 1,836.0 |
| Outlier | 1,890.0 | 1,890.0 |
| No data | null | null |
| Demo road | 2,268.0 | 2,268.0 |
| Demo community | 2,268.0 | 2,268.0 |
| Demo district | 2,292.0 | 2,292.0 |

- New focused trace suite: 10 passed. Related valuation/provider/market suite: 150 passed.
- Full Python: 3,546 passed, 32 skipped, one pre-existing Starlette/httpx deprecation warning (`python -m pytest -q`).
- Full native frontend library suite: 236 passed; explanation/save/report/locale/review suite: 6 passed. Design foundations: 12 passed; VNext hardening: 35 passed; professional GIS and E2E runner contracts pass.
- Independent read-only reviewer: zero Critical, one Important (malformed exclusion counters), one Minor (missing community-distance units). Both reproduced RED and fixed GREEN; full native suite green afterwards. No deferred findings.

### Bundle strategy and remaining limits

Ordinary baseline static assets: 2,998,934 bytes, captured from the compiled static output before product frontend edits. Its TypeScript stage encountered intentionally RED feature tests; final product typecheck/build are validated separately. First feature build: 3,052,681 bytes (rejected). Reusing the existing shared E9 client boundary for Market and the case layout removes duplicated repository/projection/locale code without changing provider lifecycles. No thresholds, tests, timeouts or dependencies are weakened.

Final ordinary production build (`npm run build`): passed. Static assets: **2,973,882 bytes**, a reduction of 25,052 bytes, with **26,118 bytes** remaining under the unchanged 3,000,000-byte ceiling. Largest JavaScript chunk: 597,008 bytes (unchanged). All route budgets pass. This is the ordinary production measurement, not the separately configured E2E build's 2,973,586-byte measurement.

Typecheck passes; lint passes with zero errors and 23 existing warnings. Production dependency audit reports zero vulnerabilities. Release contracts pass (`release_quality_gate.py --skip-tests --skip-frontend-build`); its skipped work was verified by the separate full Python suite and final production build. Security/performance gates, repository hygiene and `git diff --check` pass. Locked dependencies, budgets and timeouts are unchanged.

### Browser and print acceptance

Chromium and installed Chrome exercised saved Market, exclusions, all four locales, keyboard focus/Enter disclosures, 390/1024/1440 px layouts, explicit refresh/save, reopen, Compare, frozen Report, explicit newer-snapshot loading and legacy unavailable states. There was no horizontal overflow at any tested width. Status and reasons have text labels; the existing E10 native details/summary components provide keyboard semantics.

The regression run included the new feature journeys plus commercial Market, commercial Compare/Report and Evidence Checklist: 62 of 64 passed initially. The two failures exposed an invalid new test fixture: its second case reused the first case's finance identity and the repository correctly removed it. The fixture now uses the existing independent `e9Case("case-b")` contract. The corrected feature suite passes **10/10**, five in each browser. Together, **64 unique browser checks pass**: 54 unchanged regression checks plus the corrected 10 feature checks. This is evidence from two runs, not a claim that the initial run was entirely green.

Opening/expanding explanations, locale changes, save/reopen, Compare and Report produced **zero automatic analytical/provider requests**. Each explicit refresh journey made exactly one mocked valuation request and one mocked trend request; no additional refresh followed. The stored trace remained identical after reopen, and Report retained its frozen reference month until the explicit newer-load action. Live provider acquisition was not part of browser acceptance.

Both browser-generated PDFs contain **17 A4 pages** (595.92 x 842.88 points), with the concise explanation on page 4. PDF text inspection found zero blank pages and zero text rectangles outside the established printable bounds. Rendered summary/last pages and mobile/tablet/desktop screenshots were inspected: explanation text was readable and unclipped. Existing long-report A4 regression checks also pass in both browsers. Representative exclusions remain in Market disclosure rather than adding report pages.

### Exact changed-file inventory

21 files; no manifest, lockfile, deployment, ML, threshold or timeout changes:

1. `docs/comparable-explanation-v1.md` — design, rules, validation and limitations.
2. `services/comparable_decision_trace.py` — bounded observer and safe candidate projection.
3. `services/valuation_service.py` — instrumentation at existing decisions.
4. `services/compact_green_query.py` — preserve missing age/floor metadata for explanations.
5. `services/valuation_providers/postgres_provider.py` — preserve missing age/floor metadata for explanations.
6. `frontend_next/lib/api.ts` — optional trace response type.
7. `frontend_next/lib/workspace/comparable-explanation.ts` — versioned runtime whitelist/validation.
8. `frontend_next/lib/comparable-explanation-copy.ts` — four-locale copy and existing-unit formatting.
9. `frontend_next/lib/workspace/market-price-persistence.ts` — bounded saved-summary trace.
10. `frontend_next/lib/workspace/case-evidence.ts` — frozen evidence/fingerprint integration.
11. `frontend_next/components/workspace/market/comparable-explanation.tsx` — accessible disclosure and concise report summary.
12. `frontend_next/components/workspace/market/market-price-view.tsx` — Market integration.
13. `frontend_next/components/evidence/report-view.tsx` — frozen Report integration.
14. `frontend_next/components/evidence/evidence-entry.tsx` — shared client boundary exports.
15. `frontend_next/app/cases/[caseId]/layout.tsx` — reuse shared layout entry.
16. `frontend_next/app/cases/[caseId]/market/page.tsx` — reuse shared Market entry.
17. `tests/fixtures/comparable-valuation-baseline.json` — eight pre-change deterministic valuation baselines.
18. `tests/fixtures/comparable-explanation-result.json` — actual service-generated bounded official-provider fixture.
19. `tests/test_comparable_explanation.py` — trace and exact valuation regression tests.
20. `frontend_next/lib/workspace/comparable-explanation.test.ts` — projection, unknowns, locales, persistence/freeze and review regressions.
21. `frontend_next/e2e/comparable-explanation.spec.ts` — both-browser responsive and frozen-provider acceptance.

## PR #175 latest-main integration ledger

Fetched and verified `origin/main` at **`c2ddf1890897f44659b91079a563691fe337295e`**, containing PR #173. Preserved original feature commit **`728b5477c255c42df789541e5777e58bdbe48140`** in local branch `backup/comparable-explanation-v1-before-main-integration`. Reset only this feature branch to verified main, then cherry-picked the Comparable commit. No conflicts occurred. All 21 feature file blobs matched the original commit before this documentation update. `git rev-list --left-right --count origin/main...HEAD` is **`0 1`**. The final commit may be amended for this documentation ledger only; no push, merge or deployment is part of this task.

Main subsequently advanced during the full browser validation: PR #177 added twelve product-research files, with no application, frontend, test, dependency, configuration or existing gate-script changes. Fetched and verified the newer main at **`14e7aaa36f2c0930b88ce78669ae11343b4b8a85`**, preserving the first integrated commit `e66944f867e090d221c814480c9c0526e46fb843` on `backup/comparable-explanation-v1-on-c2ddf18`. Rebuilt this feature branch on that latest main and cherry-picked the original Comparable commit again, conflict-free, restoring **`0 1`**. Application, frontend, tests and gate scripts are byte-identical between the two integrated candidates; the completed browser matrix therefore validates the same runtime code. The partially completed isolated Python run on the first base was stopped deliberately (not counted as a completed result), and a new isolated full run was required on that base. Focused Python and frontend deterministic suites were rerun on the newer base; research-artifact validation is run read-only without rewriting main's frozen research evidence.

Satellite test and component remain byte-identical to the original implementation baseline, original feature head and integrated candidate. The earlier PR failure (expected one request, observed zero in the duplicate-click/stale-property test) is not classified as pre-existing. Its integrated browser results and investigation are recorded below.

First/second-base Satellite result: **20/20 passed**, ten each in Chromium and installed Chrome, within the full one-worker matrix. The exact previously failing duplicate-click/stale-property test passed on the first attempt in both projects. Classify the earlier PR #175 `Production Release Operations Gate / browser` failure as **non-reproducing on that integrated application tree**. This is not a claim that PR #173 fixed Satellite or that the older failure was pre-existing; the timing hypothesis remains unconfirmed. No Satellite component or test changes were made. Acceptance after PR #176 is recorded separately below.

Fresh integration review found no confirmed Critical or Important product defect. It verified unchanged selection/valuation code, bounded trace semantics, saved/report lifecycles, shared layout lifecycle and separation from main's ingress guards. Its documentation finding is addressed by this ledger. A possible Satellite test timing issue was identified from code inspection only; it is not a reproduced cause or grounds to change the test.

First-base validation checkpoint: 150 focused Python tests (including all eight exact valuation baseline fixtures), 236 frontend deterministic tests, design-system/workspace/VNext/E2E-runner contracts, typecheck, lint (zero errors, 23 existing warnings), production audit (zero vulnerabilities), production operations contract gate and local provider-free production smoke passed. The operations gate passes its repository contract while retaining external guardrails `BLOCKED` / production decision `NO_GO` from main. Historical second-base completion results follow below.

Python investigation checkpoint: the first full run, overlapping frontend compilation, ended with 4 worker lifecycle failures / 3,574 passed / 32 skipped; the second, overlapping the browser matrix, ended with 3 replacement failures / 3,575 passed / 32 skipped. The worker file alone passed 26/26. Full collection with only worker tests selected reproduced the three replacement failures (23 passed, 3 failed, 3,584 deselected), so earlier test execution is not required for this reproduction. An ignored read-only timing probe passed all 26 and measured successful generation-two readiness at 1.503 and 1.6394 seconds within the unchanged 2-second test budget. These observations suggest Windows worker-startup timing sensitivity; they do not establish a product regression or replace a clean uninstrumented full-suite result. No worker, Satellite, test or timeout code has been changed. A clean uninstrumented full run followed browser completion without a competing build/browser workload.

Historical uninstrumented full Python run on **`14e7aaa36f2c0930b88ce78669ae11343b4b8a85` plus Comparable**: **3,578 passed, 32 skipped, one existing Starlette/httpx warning**, exit 0, 303.25 seconds (`python -m pytest -q`). The browser runner had stopped and no frontend build was running concurrently. Earlier local worker failures did not recur; the measured timing headroom and isolated pass support a load-sensitive Windows startup explanation, without proving the precise cause of every earlier failure. No fixture, timeout, worker lifecycle or Satellite behavior was adjusted to obtain this result.

Historical Comparable browser acceptance: 10/10 passed, five each in Chromium and installed Chrome, within the full one-worker CI-style matrix. All three widths, four locales, selected/excluded reasons, keyboard disclosures, save/reopen, Compare, legacy unavailable and frozen/newer Report behavior pass. Zero automatic analytical/provider requests were observed; explicit refresh alone makes the expected one mocked valuation and one mocked trend request per browser. Both new PDFs are 17 A4 pages (595.92 x 842.88 points), with explanation on page 4, zero blank pages and zero printable-bound violations. Summary pages were visually inspected and remain readable and unclipped.

Historical full integrated browser matrix: **1,064 passed, 6 skipped, zero failed, zero retries**, exit 0, in 50.2 minutes on this Windows workstation (`node e2e/run-e2e.cjs --workers=1 --output=../.tmp/integration/browser-results`). Each project has 532 passed and three existing key-gated Google Maps tests skipped; no Comparable or Satellite check was skipped. Chromium and installed Chrome ran against the dedicated production-mode E2E build. Existing workflow timeouts and Playwright configuration were not changed; fresh GitHub CI must verify its own runner and job deadline. This full matrix preceded PR #176's frontend changes.

Historical completion on `14e7aaa...` plus Comparable: focused Python **150 passed** (10 new trace tests, eight exact baseline fixtures); full Python **3,578 passed / 32 skipped**; frontend deterministic **236 passed**. Typecheck, lint (zero errors / 23 existing warnings), ordinary production build and production dependency audit (zero vulnerabilities) pass. Ordinary production assets remain **2,973,882 bytes**, largest chunk **597,008 bytes**, leaving **26,118 bytes** under the unchanged 3,000,000-byte ceiling. The original and final eight valuation fixture outputs, selected rows/order, weights and confidence remain identical; the before/after table above is unchanged.

Historical release, security/performance, production operations contracts, local provider-free smoke, read-only research validation, repository hygiene and whitespace checks passed on that application tree. Release-gate test/build skips only avoid duplicating the completed standalone full suite and ordinary build. Production operations still reports external guardrails `BLOCKED` / deployment decision `NO_GO`; no owner proof or deployment readiness was fabricated. The final Comparable commit is amended only to record this documentation. A fresh GitHub CI run on the final SHA is required before any merge decision, with latest main ancestry rechecked if main advances again. No push, merge, deployment, Satellite change, threshold relaxation or ML implementation occurred.

### Refresh after PR #178 and PR #176

Main advanced again to `a05264f800309288d0d0e06c9f486988758061e9` (PR #178, offline ML lineage audits), then `0b2e74a87adfc0f0bac57d30afedff7955233d61` (PR #176, Guided Case Simulation). The latter changes frontend runtime code, so the earlier browser/build numbers are retained above as historical evidence only. Preserved the second integrated commit `07ff19bdbb25358a38a36e62d20705d030b17e00` in `backup/comparable-explanation-v1-on-14e7aaa`, reset this feature branch to newer main and cherry-picked the original Comparable commit without conflicts. Topology remains `0 1`; implementation blobs remain those of the original feature commit. Existing ML lineage audits are inherited from main; no ML-B, training, data acquisition or provider work was started.

Fresh read-only integration review found no confirmed Critical or Important defect. Main's added `copyFrom` helper retains the same locale provider and does not replace Comparable's own locale resources. Guided simulation is explicitly opened on the homepage and uses only local synthetic state; it does not import real evidence/repository/provider APIs or mount inside saved-case workspace/report layouts. Satellite implementation and test remain unchanged. Current-base focused Python, frontend deterministic contracts, full Python, both-browser acceptance and ordinary production assets are revalidated separately below.

Current-base Python: focused **150 passed**, including the ten trace tests and all eight exact before/after valuation fixtures. Full uninstrumented suite: **3,615 passed, 32 skipped, one existing Starlette/httpx warning**, 293.50 seconds (`python -m pytest -q --basetemp .tmp/integration/pytest-0b2e74a`). The unique worktree-local temp directory avoids shared Windows temp collisions; no tests were deselected or instrumented, and no frontend build/browser workload ran concurrently. Worker lifecycle tests passed without timeout or implementation changes. Additional offline lineage tests arrived through main; their passing audits do not authorize ML-B.

Current-base frontend: **236 native library tests passed**; main's simulation/copy-deduplication contracts **5 passed**; design foundations **12 passed**; VNext hardening **35 passed**; professional GIS and E2E-runner contracts passed. Typecheck passed, lint passed with zero errors and 23 existing warnings, dedicated E2E production build passed, and production dependency audit reported zero vulnerabilities. Comparable implementation and baseline fixture blobs remain identical to the original feature commit, preserving selected rows/order, weights, confidence and prices.

Current-base browser acceptance: **118/118 passed**, 59 in Chromium and 59 in installed Chrome, zero skipped, failures or retries, exit 0, 7.0 minutes. Command: `node e2e/run-e2e.cjs e2e/comparable-explanation.spec.ts e2e/satellite-evidence.spec.ts e2e/commercial-market-price.spec.ts e2e/commercial-compare-report.spec.ts e2e/evidence-checklist.spec.ts e2e/guided-case-simulation.spec.ts e2e/onboarding-tour.spec.ts --workers=1 --output=../.tmp/integration/browser-current-main-results`. This freshly rebuilt acceptance set covers the Comparable/saved-case/report/Satellite paths and main's changed simulation/onboarding/locale interactions. It is distinct from the historical full 1,070-check matrix above; fresh GitHub CI must run its complete workflow on the final SHA.

Current-base Comparable tests: **10/10 passed** across both browsers, preserving inclusion/exclusion explanations, four locales, all three widths, keyboard disclosures, save/reopen, Compare, legacy unknown states and frozen/newer Report behavior. Opening/rendering these flows made **zero automatic analytical/provider requests**; each explicit refresh alone made one mocked valuation and one mocked trend request per browser. Both fresh browser PDFs contain **17 A4 pages** (595.92 x 842.88 points), explanation on page 4, zero blank pages and zero printable-bound violations. Both summary pages were visually inspected and are readable and unclipped.

Current-base Satellite suite: **20/20 passed**, with the exact duplicate-click/stale-property-A test passing first attempt in both projects. The previous PR #175 `Production Release Operations Gate / browser` failure is **non-reproducing on the latest-main integrated candidate**. No evidence establishes the cause of the older failure; neither a pre-existing defect nor a fix in PR #173 is inferred. Satellite component/test, Playwright configuration and timeouts remain unchanged.

Current-base ordinary production build (`npm run build`) passed. Final static assets: **2,974,397 bytes**, largest client chunk **597,609 bytes**, leaving **25,603 bytes** under the unchanged **3,000,000-byte** ceiling; every existing route budget passed. These are measured from the ordinary production build after the browser runner stopped, rather than from its separately configured E2E build. No dependency, lockfile, threshold or timeout changes were made by Comparable integration.

Current-base release, security/performance and production operations contract gates passed, along with local provider-free production smoke, read-only product-research validation, repository hygiene and whitespace checks. Release-gate `--skip-tests --skip-frontend-build` avoids repeating the completed standalone full Python run and ordinary production build. Operations retains main's external guardrails `BLOCKED` and deployment decision `NO_GO`; repository gate success does not create deployment approval or missing owner evidence.

Integration is ready for a guarded force-update of PR #175, followed by fresh complete GitHub CI on the final SHA. Merge assessment is conditional on that CI passing and latest-main ancestry remaining current. The feature branch contains exactly one Comparable commit ahead of verified main (`0 1`), with no conflicts; the final amend records only this documentation. Original feature backup remains at `728b5477c255c42df789541e5777e58bdbe48140`. No push, merge or deployment was performed.

Remaining limitations: acquisition-level rejected transactions and their counts are unavailable; legacy summaries cannot recover trace; no authoritative parking treatment; floor and duplicate rejection rules are absent; inherited adapter zero defaults still affect valuation and are disclosed; source data quality, transaction target, and comparable correctness require professional verification. Browser acceptance uses a production-service-generated deterministic official-provider fixture and real saved-case repository contracts, not live provider acquisition. ML-A2 remains blocked; no ML-B work, training, or AI similarity was introduced.
