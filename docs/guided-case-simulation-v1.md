# Guided Case Simulation & Narrative Onboarding V1

Starting SHA: `8469c1f22b64a0e03be03a0099c59a8483d9e0c8`.
Original implementation baseline: `8469c1f22b64a0e03be03a0099c59a8483d9e0c8`.
Latest integration baseline: `c2ddf1890897f44659b91079a563691fe337295e`.

## Design and implementation plan

Goal: demonstrate what to do next and why, using one fictional Taiwan-style
property, seven narrative stages and an explicit synthetic-data boundary.

Architecture: extend `OnboardingTour`, its semantic `TOUR_STEPS`, modal lifecycle,
completion contract and existing `ExperienceLocaleProvider`. Load the simulation,
its local copy catalogue and CSS only when the example entrance is activated.
Keep the ordinary guide available. Use simulated section state rather than
navigating real provider-backed routes. Do not mount workspace analysis views.

The existing workspace uses `WORKSPACE_SECTIONS`, browser case repositories,
domain evidence models, checklist persistence and frozen report snapshots.
Those components can read/write cases or request providers; the simulation
therefore teaches their concepts through bounded presentation cards, without
injecting synthetic values into any of those models. Its fixture is neither a
`SavedCase` nor a `PropertyCaseWorkspace` and has no coordinates/provider IDs.

Tasks (executed inline; one final commit as requested):

- [x] Add RED tests for seven semantic stages, complete locale coverage, fixture
  isolation and browser entrance. Implement one immutable fixture and a local
  catalogue through the existing locale provider.
- [x] Extend the shared modal with optional stage presentation, restart and exit.
  Implement deterministic typing, creation, evidence cards, finance scenario,
  local manual review and report preview. Add a secondary homepage entrance.
- [x] Run complete frontend deterministic checks, persistence/locale tests,
  Chromium and Chrome acceptance, typecheck, lint, audit and production build.
  Preserve the 3,000,000-byte aggregate homepage ceiling through size optimization.
- [x] Obtain independent read-only review, fix Critical/Important findings,
  document exact evidence and changed files, check hygiene and create one commit.

Review focus: denied storage; locale changes during typing; returning to a stage;
restart while timers are active; short mobile viewports; focus restoration;
unknown evidence remaining unknown after manual review; background route prefetch
distinguished from provider requests; no production state changes.

## Contracts

Seven stages reuse the current IDs: property entry/case creation, market,
location/commute, risk, finance, Overview/checklist, report preview. The first
stage contains the simulated entry and case formation; no eighth tooltip.

All values are synthetic. No geocoding, Places, Routes, Google, GEE, TDX,
terrain, satellite, analysis API or DB operations. No report snapshot, provider
cache, Saved Case, recently opened case, compare or real checklist mutation.
Only the existing locale-independent onboarding completion record may change.

Locale contract: zh-TW/en/ja/ko; semantic IDs stay stable. Switching language
preserves stage, input progress, scenario and local review state, updates visible
copy immediately and does not replay motion or mark onboarding complete.

Motion uses CSS transforms/keyframes and one bounded deterministic typing timer.
Navigation and restart interrupt it. Reduced motion shows the complete input
immediately and removes animated transitions. No new dependencies.

The native dialog keeps keyboard operation, Escape, focus restoration, visible
focus and semantic progress. A scrolling body keeps disclosure and actions
reachable. Validate every stage at 390, 1024 and 1440 pixels.

User authorization supplies the design constraints and execution scope; this
document records implementation decisions without introducing extra approval
or intermediate commits.

## Architecture details

`CommercialHome` exposes one secondary example button. `AppShell` owns the
open/close state and provides a direct callback through context; the simulation
is dynamically imported with SSR disabled. The entrance DOM element is captured
at activation, so delayed loading cannot change its focus-restoration target.
Initial shell heading focus respects an already focused control; real page
changes still transfer focus to their heading. This avoids listener/focus
hydration races and preserves the real homepage input draft. It does not
automatically open for new or returning users. The ordinary guide remains in
Methods → Accessibility.

`OnboardingTour` accepts optional presentation content and retains the original
semantic stages, locale switcher, Next/Back/Skip/Finish controls, native modal,
progress and completion version 3. Demo Exit/Escape simply unmount it; Skip and
Finish use the existing `proptech_onboarding_state` contract. Restart replaces
only the local demo draft and remounts the stage presentation. Focus returns to
the example entrance, including after Finish and Escape.

`useExperienceLocale().copyFrom()` renders typed, route-local catalogues through
the existing locale context and interpolation implementation. Demo resources
load with the simulation. Six stage narratives reuse current guide descriptions;
the final stage uses report-preview copy. All fixture labels, boundaries,
actions, finance values and screen-reader context resolve in the active locale.
Native language names remain in the language selector intentionally.

The one frozen fixture is `demo:guided-case:v1`, with a frozen comparable array,
a fictional localized address, three comparable prices, schematic travel times,
unknown risk and illustrative finance assumptions. It cannot satisfy either
saved-case or workspace types. The down-payment slider calculates only local
cash/principal shares; it is not a valuation or provider-backed mortgage result.
Local manual review does not change the displayed unknown risk.

Motion: 32 semantic typing ticks at 35ms (about 1.12 seconds), a 280ms case-card
formation/report reveal, 260ms evidence-card entrance with 55ms stagger, 420ms
comparison-bar growth and 400ms schematic path reveal. Shared stage/progress
transitions remain 160ms. No looping effects or new dependencies. All timers
clean up when interrupted. Reduced motion reveals the final address immediately,
turns off animation and transitions, and still allows completion.

Desktop retains the shared progress rail. Mobile shows the current semantic
stage and step count above a scrolling narrative panel. Disclosure and actions
sit outside the scroll body; wrapping controls and the existing dynamic viewport
height/safe-area rules keep them reachable. Native Tab/Shift+Tab cycling includes
the read-only input, slider and checkbox. This is a dismissible modal, with
Escape and focus restoration, rather than a trapping page workflow.

## Bundle approach

The normal starting build measured 2,999,729 static bytes in this environment,
different from the previously recorded 2,998,938. Its JS was 2,852,635 bytes and
largest chunk 597,008 bytes. Only 271 bytes remained under the unchanged
3,000,000-byte homepage aggregate ceiling.

Copy catalogue prefixes are expanded once through a typed helper. Canonical
dictionary keys now supply runtime registration, retaining the original order
and exact string-literal types. Source contracts for wizard/risk labels are
preserved. Existing runtime/experience override dictionaries use the same
prefix compaction. No translation, fallback, interpolation, supported locale,
dependency or budget constant changed. The unchanged release fingerprint guards
all legacy outputs; duplicate checks inspect both flat and grouped resources.

Final normal production build: **2,999,483 static bytes**, **2,847,869 JS bytes**,
largest JS chunk **597,609 bytes**. The aggregate decreased by **246 bytes** and
leaves **517 bytes** under the unchanged 3,000,000-byte ceiling. The lazy demo
stylesheet is 4,520 bytes; it is absent from the initial prerendered HTML.

The aggregate gate counts every static asset, including lazy chunks. It is not a
measurement of initial browser transfer. Browser acceptance separately asserts
that simulation JavaScript and CSS are absent until the example button is activated.

## Original implementation independent review

A separate read-only reviewer found no Critical or Important issues. Reviewed
provider/state isolation, trust semantics, locales, timers, modal accessibility
and bundle boundaries. The reviewer independently compared all three compacted
internal dictionary sets with the starting SHA and verified 951 exact runtime
copy key types. Five targeted unit/fingerprint checks passed independently.
Two Minor findings were fixed: Korean buyer-equity terminology and an unused
copy-key import. A final focused review of the asynchronous-loading focus fix
also found no Critical or Important issues. No deferred code findings remain.

## Original implementation verification results

Executed on 2026-10-10 in the current worktree. Verification logs are local,
ignored artifacts in `frontend_next/.local/`.

| Check | Result / command / evidence |
| --- | --- |
| RED → GREEN | Two fixture/locale tests initially failed on missing modules; browser entrance initially failed against the original build. Final targeted set: 9 passed. |
| Complete frontend deterministic suite | 264 passed across all `lib/` and `scripts/` `.test.ts/.test.mjs/.test.cjs` files, using Node's test runner. `all-unit-final.log`. Includes existing guide, saved cases, workspace finance/checklist persistence, locale coverage and unchanged legacy fingerprint. |
| Frontend Python contracts | 274 passed; all `test_frontend_*.py` plus bundle/release/security contracts. `frontend-python-final.log`. See the PR #176 follow-up below for the later resolved-copy contract repair and full-suite run. |
| Workspace contract / VNext hardening | `node scripts/test-professional-gis-contract.mjs`: pass; `node scripts/test-vnext-hardening.mjs`: 35 passed. |
| Typecheck | `npm run typecheck`: pass (`typecheck.log`). Production build also runs TypeScript. |
| Lint | `npm run lint`: zero errors, 23 existing warnings; no suppression added (`lint.log`). |
| Normal production build | `npm run build`: pass (`production-build-final.log`). |
| Production audit | `npm audit --omit=dev --audit-level=high`: zero vulnerabilities. Locked dependency tree valid. Existing dev-only audit exception gate passes unchanged, expires 2026-11-04 (`production-audit.log`, `audit-gate.log`, `dependency-tree.log`). |
| Static and route budgets | Both scripts pass, including the 3,000,000-byte homepage aggregate. `static-budget-final.json`, `route-budget-final.json`. |
| Release / security | `release_quality_gate.py --skip-tests --skip-frontend-build` and `security_performance_release_gate.py --json`: pass. Initial verification used frontend tests/build; the later PR #176 follow-up also ran the full Python suite. `release-gate.log`, `security-gate.log`. |
| Repository hygiene / whitespace | `check_repository_hygiene.py`: pass after staging all 18 files; `git diff --cached --check`: pass. `hygiene-final.log`. |

### Browser acceptance

Targeted suite is `e2e/guided-case-simulation.spec.ts` plus the unchanged existing
`e2e/onboarding-tour.spec.ts`. Command: `node e2e/run-e2e.cjs
e2e/guided-case-simulation.spec.ts e2e/onboarding-tour.spec.ts --workers=2
--retries=0`. No timeout or assertion was relaxed. Both Chromium and installed
Chrome are used. Test-build verification passed 32/32. Final normal-production
verification passed **34/34**, 17 per browser, including the added lazy-loading
focus regression (`production-browser-final.log`).

The demo suite covers A–I: complete zh-TW journey; zh-TW/English middle-stage
switch; Japanese/Korean continuation; every stage/locale at 390/1024/1440;
keyboard-only finance/review/Finish/Escape; reduced motion through Finish;
mid-demo Exit with seeded real cases; restart resetting typed/scenario/review
draft; zero provider calls through Start/Next/Back/locale/Restart/Exit/Finish.
Additional tests cover denied storage, unloaded demo JS/CSS before activation,
and deterministic focus movement while the lazy module is intentionally held.
The latter failed against the pre-fix production build and guards restoring the
initiating button after asynchronous loading.

Fresh 390px market and 1440px report screenshots were also visually inspected;
progress, disclosure and controls remain visible, with mobile content scrolling
inside the bounded panel.

Zero-provider monitoring starts before homepage navigation. It distinguishes the
initial document/static assets and narrowly identified existing Link RSC
prefetches from fetch/XHR or external requests. No real provider requests are
mock-fulfilled by the simulation suite. Browser snapshots compare all local and
session storage except the allowed onboarding record; instrumented storage
writes and real-case events must remain empty. A real property-entry draft is
preserved. Review, finance and report preview remain entirely local.

## Limitations and original integration status

This is a presentation-only example, with illustrative price/finance numbers,
not an analysis, saved case, report snapshot or real verification. Actual
provider-backed calculations and route navigation are deliberately outside the
demo. Manual screen-reader/device testing was not performed; browser semantics,
keyboard, geometry and reduced-motion behavior are automated. No production
infrastructure, backend, valuation semantics or ML files changed.

Exactly one final commit is created in the requested worktree/branch. No push,
merge, deployment or PR creation. Before merging onto then-current main,
integrate changes and rerun deterministic/browser/security/bundle gates; the
small remaining aggregate budget is particularly sensitive to combined changes.

## PR #176 localization CI follow-up

The fresh GitHub quality job ([run 38063414411](https://github.com/ryanwu566/proptech-ai-copilot/actions/runs/38063414411/job/114246099409))
checked the feature commit `3e8d942e2acc4e12dbb59df3326ee3f2c7e1768c`
against the starting main SHA. Python stopped with 4 failures, 3,531 passes and
33 skips; build/budget steps were skipped. The same four tests failed locally
before any repair (`localization-ci-red.log`).

Root cause: tests counted five full-key source literals (one registration array
plus four dictionaries) or required full keys in particular source files. Key
registration now derives from the canonical catalogue, and prefix expansion
generates full keys at runtime. All required locale data and resolved output
were already correct. No production implementation, copy, provider URLs,
dependency or asset ceiling changed for this repair; no duplicate strings were
introduced.

`tests/runtime_copy_probe.py` imports/transpiles the real TypeScript modules,
including `expandCopyGroups`, overrides and translation functions. Updated
tests check registration, explicit own-locale coverage, nonempty translated
output, absence of raw keys/unresolved interpolation and the expected script.
The English confidence semantic check also uses the actual English output.
Provider tile URLs, rendered copy calls and map/navigation invariants retain
their existing assertions. Three experience-copy entries are similarly checked
through their actual resources/overrides; identical legitimate wording does
not count as fallback (Japanese `距離`, and the existing `Terrain Risk` label).

All 16 required runtime keys are proved in **zh-TW, en, ja and ko** (64 resolved
combinations, with no missing own-locale entries):

| Group | Keys checked in every locale |
| --- | --- |
| Confidence | `riskSummary.confidenceHighMessage`, `riskSummary.confidenceMediumMessage`, `riskSummary.confidenceLowMessage` |
| Location/price | `riskSummary.titleLocationSupportsPrice`, `riskSummary.titleLocationNotSupportsPrice` |
| Map | `map.baseStandard`, `map.baseLight`, `map.baseSatellite`, `map.selected`, `map.distance`, `map.rating` |
| Shared surfaces | `location.title`, `commute.title`, `loan.title`, `tax.title`, `case.title` |

Resolved values are recorded in the ignored local artifact
`frontend_next/.local/localization-runtime-proof.json`. Four originally failing
tests now pass; all localization tests pass **48/48**, and frontend deterministic
tests pass **264/264**. A separate read-only reviewer independently ran the
16-key/four-locale probe plus three experience keys and found no findings.
Full Python passed **3,536 tests, 32 skipped, zero failures** using
`VALUATION_DEMO_MODE=false python -m pytest -q --basetemp
frontend_next/.local/pr176-pytest` (`pr176-full-python.log`). No tests were
deselected. This local run uses Windows/Python 3.13.14/Node 24.14.1; the inspected
GitHub run uses Ubuntu/Python 3.12.15/Node 24.21.0. Both collect 3,568 tests; the
local run has one more executed test and one fewer skip.

Typecheck passes; lint has zero errors and the unchanged 23 existing warnings.
Production npm audit has zero vulnerabilities; locked-tree and existing npm
exception gates pass. Strict `pip_audit -r backend/requirements.txt --strict`
passes with no known vulnerabilities. On Windows, `PYTHONUTF8=1` and
`PYTHONIOENCODING=utf-8` were set for pip-audit's child-process encoding.
Repository hygiene, production operations, provider-free local production smoke
and SBOM generation pass.

Fresh normal production build passes (`pr176-production-build.log`). Remeasured
static assets remain **2,999,483 bytes**: **517 bytes** under the unchanged
**3,000,000-byte** homepage ceiling. JS remains 2,847,869 bytes; largest client
chunk remains 597,609 bytes. Both static/route budget scripts, release quality
and security/performance release gates pass (`pr176-static-budget.json`,
`pr176-route-budget.json`, `pr176-release-gate.log`, `pr176-security-gate.json`).
The gates reuse the freshly completed full suite/build via their skip flags;
no required validation is omitted.

Fresh live-switch browser regression command: `node e2e/run-e2e.cjs
e2e/guided-case-simulation.spec.ts e2e/onboarding-tour.spec.ts --grep
'live locale switching|live zh-TW' --workers=2 --retries=0`: **4/4 passed**
across Chromium and installed Chrome (`pr176-live-locale-browser.log`).
Guided Simulation and ordinary onboarding preserve stage/focus while switching
zh-TW/en/ja/ko. The earlier full 34-test browser acceptance remains recorded above;
this follow-up changes only tests and documentation.

GitHub PR #176 was rechecked: still one commit at the original feature SHA,
base unchanged, unmerged. The existing feature commit is amended locally only.
No push, merge, deployment, remote PR update or workflow rerun is performed.
Remote CI must run on the amended SHA after a guarded force-update; local green
equivalent commands do not imply that the old remote checks have changed.

## Integration onto latest main including PR #173

Fetched `origin --prune` and verified `origin/main` exactly matched
`c2ddf1890897f44659b91079a563691fe337295e`. The feature worktree was clean at
`3ef88b694da54b306c68aa3d41faf76e1ad9dfa4`. Created backup branch
`backup/guided-case-simulation-v1-before-main-3ef88b6` at that commit, reset the
feature branch to verified main, then cherry-picked that amended feature commit.
No conflicts occurred; no semantic resolutions or stale literal-copy restoration
were needed. `git rev-list --left-right --count origin/main...HEAD` is `0 1`.

All 40 files introduced/changed by PR #173 match latest main byte-for-byte under
Git comparison. The Guided Simulation feature changes 21 separate files and
retains grouped copy, the resolved localization contracts and its isolated local
draft. Fresh combined-tree validation is recorded below.

### Fresh combined-tree validation (2026-10-11)

All checks below ran on the integrated tree. Browser and asset checks used the
fresh normal production build.
Only this documentation changed after validation; no runtime implementation,
dependency, backend file, test assertion, timeout or bundle ceiling was changed
to obtain these results. Ignored artifacts are under `frontend_next/.local/`.

| Check | Fresh result | Artifact |
| --- | --- | --- |
| Four previously failing localization tests | 4 passed | `integration-localization-four.log` |
| All localization/locale/i18n Python tests | 48 passed | `integration-all-localization.log` |
| Relevant workspace and production guardrail Python tests | 160 passed | `integration-workspace-python.log` |
| Complete frontend deterministic suite, including Guided Simulation and existing Guided Tour | 264 passed, zero failures | `integration-all-unit.log` |
| Professional GIS contract / VNext hardening | pass / 35 passed | `integration-workspace-contract.log`, `integration-hardening.log` |
| Full Python suite | 3,568 passed, 32 skipped, zero failures | `integration-full-python-ci-temp.log` |
| Typecheck / lint | pass / zero errors, 23 existing warnings | `integration-typecheck.log`, `integration-lint.log` |
| Normal production build | pass | `integration-production-build.log` |
| npm production audit / locked dependency tree / existing audit exception gate | zero vulnerabilities / pass / pass | `integration-production-audit.log`, `integration-dependency-tree.log`, `integration-audit-gate.log` |
| Strict Python dependency audit / SBOM generation | no known vulnerabilities / pass | `integration-python-audit.log`, `integration-sbom.json` |
| Static / route asset budgets | pass / pass | `integration-static-budget.json`, `integration-route-budget.json` |
| Release contract / security-performance gates | pass / pass | `integration-release-gate.log`, `integration-security-gate.json` |
| Production operations gate / provider-free local smoke | pass / pass | `integration-operations-gate.json`, `integration-production-smoke.json` |
| Repository hygiene / whitespace | pass / pass | `integration-hygiene.log`, `git diff --check` |
| Chromium and installed Chrome targeted browser acceptance | 34 passed, zero retries | `integration-browser.log` |

The full-suite command was `VALUATION_DEMO_MODE=false python -m pytest -q
--basetemp <system-temp>/proptech-pr176-integration-full`. No tests were
deselected. The temporary directory is outside the repository, matching CI's
runner-temp approach. One existing Starlette deprecation warning remains.

Earlier attempts are retained for transparency. The initial run, concurrent with
other validation jobs, reported four Earth Engine worker startup/replacement
failures (3,564 passed, 32 skipped; `integration-full-python.log`). All 26 worker
tests subsequently passed alone (`integration-worker-isolated.log`). A serial
run with repository-local temporary files reported two different failures:
spatial timing of 500.925 ms against its unchanged 500 ms limit, and Windows
`WinError 5` denying an atomic manifest-file replacement (3,566 passed, 32 skipped;
`integration-full-python-serial.log`). Both affected modules passed all 53 tests
alone (`integration-backend-isolated.log`). The final complete run then passed
with the CI-style temporary directory. These failures were not reproduced in
that run; backend code, limits and assertions remain unchanged from latest main.

Release gate skip flags reuse the freshly completed full suite and build,
exactly as the GitHub workflows do. The operations gate includes PR #173's
`guardrail_evidence_contract` and preserves main's `external_guardrails=BLOCKED`
and `production_decision=NO_GO`. A passing local contract gate does not certify
external production evidence or authorize deployment.

Remeasured combined assets: **2,999,483 bytes**, with **517 bytes** remaining
under the unchanged **3,000,000-byte** homepage ceiling. JavaScript is
2,847,869 bytes; the largest client chunk is 597,609 bytes. Both budget scripts
measure the freshly rebuilt `.next/static` output.

The full browser command was `node e2e/run-e2e.cjs
e2e/guided-case-simulation.spec.ts e2e/onboarding-tour.spec.ts --workers=2
--retries=0`. Both browser projects passed all seven stages and all four locales
at 390/1024/1440, zh-TW to English and English to Japanese/Korean live switching,
keyboard operation, focus restoration, lazy loading, reduced motion, blocked
storage and timer cleanup. Full-journey observers recorded **zero provider
requests**, **zero non-onboarding storage writes** and **zero real case events**.
Seeded real Saved Cases, compare selection, holding-cost result and the real
address draft were preserved. Fresh mobile market and desktop report screenshots
were visually inspected. Manual screen-reader and physical-device tests were
not performed.

A fresh independent read-only reviewer found no Critical, Important or Minor
findings requiring changes. Its source AST comparison confirmed unchanged legacy
translations in runtime resources and both override sets; it also independently
verified all 40 PR #173 paths, one-commit topology, resolved locale contracts,
provider/storage isolation and accessibility lifecycle handling. Test/build/browser
results above are separate fresh validation evidence.

Only the final feature commit is amended for this documentation. The backup is
retained. No push, merge, deployment or remote workflow rerun is performed;
GitHub CI must run on the final SHA after a guarded force-update of PR #176.

## Exact changed files relative to latest integration baseline (21)

1. `docs/guided-case-simulation-v1.md`
2. `frontend_next/components/app-shell.tsx`
3. `frontend_next/components/commercial-home.tsx`
4. `frontend_next/components/experience-locale-provider.tsx`
5. `frontend_next/components/onboarding-tour.tsx`
6. `frontend_next/components/guided-case-simulation.tsx`
7. `frontend_next/components/guided-case-simulation.css`
8. `frontend_next/lib/copy-catalogue.ts`
9. `frontend_next/lib/guided-case-simulation.ts`
10. `frontend_next/lib/guided-case-simulation-copy.ts`
11. `frontend_next/lib/guided-tour-copy.ts`
12. `frontend_next/lib/runtime-copy.ts`
13. `frontend_next/lib/runtime-copy-groups.ts`
14. `frontend_next/lib/runtime-copy-overrides.ts`
15. `frontend_next/lib/experience-i18n-overrides.ts`
16. `frontend_next/scripts/guided-case-simulation.test.cjs`
17. `frontend_next/scripts/runtime-copy-deduplication.test.mjs`
18. `frontend_next/e2e/guided-case-simulation.spec.ts`
19. `tests/runtime_copy_probe.py`
20. `tests/test_factor_localization_correctness.py`
21. `tests/test_map_localization_mobile_search.py`
