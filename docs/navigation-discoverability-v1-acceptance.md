# Navigation & Discoverability v1 acceptance

## Scope and provenance

Worktree: `C:\Projects\proptech-navigation-discoverability-v1`.
Branch: `feat/navigation-discoverability-v1`.
Before implementation, `git fetch origin main`, `origin/main`, `HEAD` and
`git ls-remote origin refs/heads/main` agreed on
`59631992e03c05ff01e67fb691710c738fcc6d1b`.

The [IA audit and design](superpowers/specs/2026-10-16-navigation-discoverability-v1.md)
cover every requested product area. The
[execution plan](superpowers/plans/2026-10-16-navigation-discoverability-v1.md)
records the implementation and review findings.

## Product acceptance

| Requirement | Result |
| --- | --- |
| Global navigation | Persistent Home, Saved Cases, Compare and Account; native searchable disclosure groups Start, Analysis, Decisions, Personal and Supporting tools. Same structure on desktop and mobile. |
| Discover existing capabilities | Real destinations for property workflow, Market, Valuation, Location, Risk, Finance, Scenario Lab, Decision Room, Report, Preferences, My Places, Commute, Tax, Credit, Identity and Planning. Existing availability rules remain in their destination pages. |
| Saved Cases | Visible global entry; case-specific features use the current case or an explicit local-case chooser carrying an allowlisted destination. No arbitrary case substitution. |
| Orientation and recent work | Home groups capabilities and preserves its existing local recent-case ordering and storage diagnostics. No new history store or server data. |
| Workflow handoff | Analysis → Scenario Lab → Decision Room → Compare; comparison links each selected case to its Report. Contextual report links also remain available along the case workflow. |
| Empty and recovery states | Explain prerequisites and anonymous exploration; offer the real property workflow even when local storage is empty, invalid or blocked. Existing diagnostics remain visible. |
| Deep links | Tool selection, property entry and browser history use URLs. Locale changes preserve path, case, query and hash. Case IDs are encoded and chooser destinations are allowlisted. |
| Locales | zh-TW, en, ja and ko; navigation reuses canonical feature entry names. Existing English method names have localized descriptions. |
| Analytical truth | Navigation performs no analysis, repository writes or provider refreshes. Evidence projections, stale/unknown states and provider logic are unchanged. |
| Boundaries | No migration, Admin, billing or fake AI entry. Future Copilot has no actionable navigation item until implemented. Anonymous exploration and existing Auth/account flows remain. |

## UX and accessibility review

Independent static review covered destination safety, case identity, history,
storage recovery, canonical labels, shared imports and focus behavior. Findings
were fixed before acceptance. Browser checks exercise native disclosure keyboard
activation, local search, Escape focus restoration, Tab/Shift+Tab exit, visible
focus, skip links, workflow stage focus and locale switching. The menu never traps
focus. Navigation uses semantic landmarks and preserves the existing skip link.

Review exposed real failures in missing-case skip focus, keyboard workflow entry,
unbroken local case-title wrapping and guide focus restoration. Each received a
focused regression. Guide close now reveals only the original opener's disclosure
ancestors before restoring visible focus. Normal menu exit behavior remains.

Visual review inspected the product menu at 390px and 1024px, plus Saved Cases and
Compare with an unbroken 108-character title at 390px. Labels and actions remain
contained; the menu has a bounded scroll area and a visible focus outline. Automated
coverage checks all four requested widths and locales, plus actual touch taps at
390px and 430px. Review screenshots are local ignored artifacts under
`frontend_next/.tmp/navigation-ux-review/`.

Final independent source review found no additional concrete issues. This review
and browser coverage do not claim a manual screen-reader session.

## Validation

| Check | Result |
| --- | --- |
| Navigation unit tests | 5/5 passed; included in the expanded suite below. |
| Expanded Node regression suite | 242/242 passed, including workspace/evidence, Preferences, design foundations, commercial truth and Auth/account race tests. |
| Route-measurement Node regressions | 17/17 passed. |
| Focused Python route/commercial/global-budget tests | 51/51 passed. |
| Existing commercial browser pack | 186/186 passed: 93 Chromium and 93 installed Chrome; retries=0. |
| Broad browser baseline | 506/512 passed initially, 253/256 per browser; six failures investigated and resolved below. No retries or skips. |
| Post-review focused browser run | 140/140 passed, 70 per browser; retries=0, no skips or flaky results. Includes all six failed cases, full My Places/Commute, navigation, touch, overflow, guide and synthetic-example coverage. |
| Ordinary-production layout run | 8/8 passed, four widths per browser; retries=0. Saved-case chooser and Compare both remain bounded with long titles. |
| Combined accepted coverage | 546 distinct test/project cases, 273 per browser. The latest result for each case passes; no unresolved failures, skips or retries across these validation stages. This is combined coverage, not a claim that the initial baseline passed. |
| Typecheck | `npm run typecheck` passed after the final source/test changes. |
| Lint | `npm run lint` passed: zero errors, 23 existing unused-symbol warnings. |
| Production builds | Configured E2E build and final ordinary `npm run build` both passed. |
| Route/global budgets | All 17 routes and both global limits passed on the final ordinary build; ceilings and baseline registry unchanged. |
| Security/performance release contract | Passed; read-only validation of existing source/build contracts. No migration created or applied. |
| Repository hygiene / diff | Staged-source hygiene scan passed; staged whitespace/diff check passed before the local commit. |

The broad run's six failures comprised four guide integration failures (two tests
in both browsers), one Commute mock-timing race and one Decision Room fixture lock
precondition failure. The guide behavior is fixed and its original focus checks
are strengthened with visibility/viewport assertions. The guide helper now
explicitly reopens the menu after an external locale interaction closes it.
Commute mock responses use a promise barrier, released in `finally` after loading
and disabled-state assertions, instead of a 100ms observation window. The Decision
Room fixture foregrounds its manual lock owner before acquisition. Every existing
concurrency, persistence, isolation and request-count assertion remains; no timeout
was increased. All affected checks passed in the fresh 140-test run.

Local ignored evidence:

- `frontend_next/.tmp/navigation-e2e.json` and `navigation-playwright-report/`: broad baseline.
- `frontend_next/.tmp/navigation-fixes.json` and `navigation-fixes-report/`: final focused verification.
- `frontend_next/.tmp/navigation-production-layout.json` and `navigation-production-layout-report/`: ordinary-production layout verification.
- `frontend_next/.next/route-assets-v2.json`: build-bound cold-browser attribution.
- `.tmp/navigation-route-budgets.json`, `navigation-global-budget.json` and `navigation-bundle-analysis.json`: final budget results.

## Final measured performance

Unique required static asset bytes from cold route loads, using the unchanged
repository measurement protocol and populated local fixtures. Provider/API traffic
and unrelated prefetch are blocked before access. All entries below passed.

| Route | Measured bytes | Existing ceiling |
| --- | ---: | ---: |
| `/` | 1,909,583 | 2,066,966 |
| `/account` | 1,112,987 | 1,334,428 |
| `/login` | 1,112,987 | 1,334,428 |
| `/signup` | 1,112,987 | 1,334,428 |
| `/preferences` | 892,874 | 1,049,735 |
| `/places` | 860,055 | 1,030,896 |
| `/compare` | 1,146,916 | 1,301,212 |
| `/cases/[caseId]` | 1,146,916 | 1,301,212 |
| `/cases/[caseId]/overview` | 1,146,916 | 1,301,212 |
| `/cases/[caseId]/market` | 1,146,916 | 1,301,212 |
| `/cases/[caseId]/location` | 1,352,256 | 1,551,855 |
| `/cases/[caseId]/risk` | 1,340,535 | 1,538,049 |
| `/cases/[caseId]/finance` | 1,179,163 | 1,339,100 |
| `/cases/[caseId]/scenarios` | 1,161,972 | 1,337,843 |
| `/cases/[caseId]/decision-room` | 1,196,854 | 1,409,828 |
| `/cases/[caseId]/commute-planner` | 1,168,877 | 1,377,984 |
| `/cases/[caseId]/report` | 1,146,916 | 1,301,212 |

Total static assets: **3,290,584 / 8,000,000 bytes**.
Largest client JS chunk: **604,425 / 900,000 bytes**.
Navigation uses entry metadata and small entry-copy catalogues. Existing workflow
implementations stay lazy; synthetic-example JS/CSS loading was also verified.

## Reproduce

From `frontend_next`, with the unchanged lockfile dependencies installed. This
current-source command combines the broad regression and added focused coverage:

```text
npm run test:navigation
npm run typecheck
npm run lint
npm run build:e2e
node e2e/run-e2e.cjs e2e/discoverability.spec.ts e2e/navigation.spec.ts e2e/navigation-overflow.spec.ts e2e/mobile-sidebar-navigation.spec.ts e2e/commercial- e2e/property-scenario-lab.spec.ts e2e/decision-room.spec.ts e2e/my-places-commute.spec.ts e2e/preference-tradeoff.spec.ts e2e/consumer-account.spec.ts e2e/onboarding-tour.spec.ts e2e/guided-case-simulation.spec.ts --workers=1 --retries=0
npm run build
node e2e/run-e2e.cjs e2e/navigation-overflow.spec.ts --workers=1 --retries=0
```

The expanded Node regression command, also from `frontend_next`:

```text
node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test --test-concurrency=1 lib/navigation/model.test.ts lib/workspace/*.test.ts lib/preferences/profile.test.ts lib/preferences/tradeoff.test.ts scripts/commercial-design-foundations.test.mjs scripts/commercial-trust-flow.test.cjs scripts/consumer-auth.test.mjs scripts/consumer-auth-race.test.mjs scripts/account-client.test.mjs
```

From the repository root:

```text
node --test scripts/measure_route_assets.test.cjs
python -m pytest -q tests/test_route_budgets.py tests/test_commercial_trust_location.py tests/test_competition_bundle_budget.py
python scripts/analyze_next_bundle.py --measure-browser
python scripts/check_route_budgets.py
python scripts/check_frontend_bundle_budget.py
python scripts/security_performance_release_gate.py --json
python scripts/check_repository_hygiene.py
git diff --check
```

Builds on this memory-constrained Windows host use `CIRCLE_NODE_TOTAL=2` as
Next's supported worker-count hint. This changes no application configuration,
route ceilings or global budgets. Dependency extraction was recovered serially
from integrity-verified archives matching the unchanged lockfile; dependency
versions and the lockfile were not modified. Temporary setup and validation
artifacts stay in ignored directories.

## Delivery

One local commit only: `feat: improve product navigation and discoverability v1`.
No push, merge or deployment is performed. After reviewing the local commit:

```powershell
git -C C:\Projects\proptech-navigation-discoverability-v1 push --set-upstream origin feat/navigation-discoverability-v1
```
