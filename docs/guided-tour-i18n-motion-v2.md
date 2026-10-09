# Guided tour: locale and motion v2

Original implementation baseline: `b4eb441a8ccf90965102f0646006dc4b0e145491`.
Integration baseline: `602830c8d4d405bb401afa902d5bf69f2c61066f`.
Original feature commit: `1472a09899e929a4e429d51e60ca1b4abd61cf71`.
Branch: `feat/guided-tour-i18n-motion-v2`. Work is restricted to this worktree;
one final commit, no push, merge, or deployment.

## Original architecture and pain points

`AppShell` owns a manually opened `OnboardingTour`. The entry is inside the
header Methods → Accessibility disclosure. No automatic first-use trigger is
mounted. The existing five-step modal teaches cases, tax, map, price/loan and
report, with floating/pulsing mock results and a large two-column preview.
It resolves runtime keys through `ExperienceLocaleProvider`, but blocks access
to the header language selector while open. Some Japanese tour copy remains
English, and hardcoded report/mock-result labels leak into the tour. It lacks
Escape, focus containment, initial focus and focus restoration. Its final
actions navigate to tax/map tools, so guidance can cause unrelated tool loads.

The provider stores locale in React state, defaults to zh-TW, and updates the
document language. Locale is intentionally not persisted. `SUPPORTED_LOCALES`
is zh-TW, en, ja, ko. `copy()` resolves `runtime-copy.ts` and overrides on each
render. Old persistence is `proptech_onboarding_seen=true` plus version `2`;
it conflates skipped and completed and has an unused exported reader.
Other guided-property journey and intro components are actual workflow/intro
surfaces, not replacements for the existing tour, and remain outside this lane.

## Interaction and implementation plan

Keep the existing manually invoked tour. Replace decorative mock results with
a concise seven-step contextual workflow card, using E10 tokens and buttons.
Use a native modal dialog for focus containment, background inertness and
Escape; put the existing locale selector inside the modal. Keep stable header
and footer controls, a scrollable body, readable workflow context, and a
restrained 160 ms fade/4 px entrance. Mobile uses a bottom card with safe-area
padding. No target lookup or tool navigation: the contextual card is safe even
when a workflow target is unmounted, hidden, resized or removed.

Steps: establish property/case; inspect market evidence; check location/commute;
review terrain/risk; evaluate finance; verify missing evidence; save/compare/report.
Each step has a semantic ID and runtime-copy keys, not stored prose.

Implementation sequence:

1. Add failing deterministic coverage and browser scenarios for live locale,
   persistence, keyboard, responsive, reduced motion and zero provider calls.
2. Add typed four-locale resources to existing runtime-copy infrastructure and
   a bounded persistence utility; implement the contextual dialog.
3. Remove tour workflow callbacks, localize the restart entry, and retain manual
   opening. Verify unit and browser behavior, review screenshots.
4. Run complete deterministic frontend tests, lint/typecheck, production build,
   dependency audit, static/route budgets, hygiene and diff checks. Perform an
   independent read-only review; resolve Critical/Important findings.
5. Complete this evidence report and create exactly one final commit.

## Locale and persistence contracts

All guide prose, step headings, controls, title, progress, restart and assistive
labels resolve through `copy()` for the current locale at render time. Switching
locale changes no step ID, open state or persisted status, does not reload the
application and does not replay entrance motion. The language selector itself
uses existing localized labels; its options use the repository's locale names.

New bounded record: `proptech_onboarding_state` contains exactly
`{version: "3", status: "skipped" | "completed"}`. No locale, evidence, personal
data or prose. Old version 2 records are retained but never interpreted as v3
completion. Invalid/obsolete records are ignored. Storage denial is harmless.
Open/restart begins at the first step and does not rewrite the last outcome;
there is intentionally no resume. Escape records skipped; Finish completed.
Changing locale after skip/completion or reopening the browser preserves the
outcome. The app's locale still defaults to zh-TW after reload, as before.

## Original implementation verification evidence

The baseline was built from the starting product source after restoring locked
dependencies with `npm ci --ignore-scripts --no-audit --no-fund`. No package or
lockfile changes were made. The new locale-control unit test failed on the old
code, and the Chromium live-switch browser test failed because the open modal
had no locale selector. Both regression tests then passed with the new guide.

### Accessibility, motion and responsive behavior

The native `dialog.showModal()` puts background content outside the interaction
scope. Initial focus goes to the step heading. Next/Back focuses the new heading
with its progress and description associated by `aria-describedby`. The step
count is a polite, atomic status announcement. Locale changes preserve focus
on the language selector and do not remount the step. Controls have localized
text names and inherited visible focus styles. Tab and Shift+Tab cycle through
enabled controls; Escape records skipped and returns focus to the opener.
Closing restores the previous body overflow. There is always a reachable Skip.

Entrance/step motion is a 160 ms fade with a 4 px transform; progress changes
use the same restrained timing. No loops, pulses, bounce, staged previews or
autoplay remain in the guide. `prefers-reduced-motion: reduce` removes all tour
animations and minimizes transitions while retaining every step and control.

Responsive acceptance exercises all seven steps in all four locales at
390×844, 1024×844 and 1440×844. Each dialog, language selector, Skip and Next/
Finish is within the viewport; dialog and document have no horizontal overflow.
The scrollable body keeps controls outside its scrolling area. Mobile is a
bottom card with dynamic viewport sizing and safe-area spacing. Desktop shows
a static workflow list with semantic current-step indication. The E10 product
uses light tokens and `color-scheme: light`; no separate dark theme was added.

Screenshot review at 390 and 1440 confirms readable wrapping, restrained
hierarchy, E10 button priorities/radii, consistent spacing and overlay opacity.
Playwright captures successful English final-step screenshots at all three
widths in both browser projects. Generated screenshots/report remain ignored
using the repository's existing artifact workflow.
Local reviewed copies: `.local/guided-tour-390.png`,
`.local/guided-tour-1024.png`, `.local/guided-tour-1440.png`. Full acceptance log:
`.local/guided-tour-browser-final.log`; deterministic log:
`.local/guided-tour-unit-final.log`.

### Provider isolation and browser observations

Open, Next, Back, in-dialog locale change, Skip, Escape, Finish and Restart have
no API, provider, navigation or calculation callback in the component contract.
Request monitoring rejects every fetch/XHR or external request except known
shell frontend route payloads: same-origin GET, `rsc=1`, `_rsc` query, and path
`/`, `/cases` or `/vnext/property-identity`. Those are existing Next Link
prefetches; no Google, Earth Engine, TDX, terrain, satellite or property
calculation request was observed. The frontend fixtures abort unexpected
provider requests; requests are observed before routing, so mocking cannot
hide a tour request.

The first expanded browser run exposed three issues, all subsequently resolved:

- The reload observer counted Next's startup same-document history event.
  A separate reproduction showed the document token and step survived. The
  test now asserts document identity directly, rather than event count.
- An overbroad network observer counted shell RSC prefetches as providers.
  Only the explicitly bounded frontend payloads above are excluded.
- Native Tab navigation briefly reached browser chrome after the last control.
  Explicit boundary cycling now keeps DOM focus in the dialog, with Escape
  still releasing the modal. Forward and reverse boundaries are tested.

No test timeout was increased, no retries were used for acceptance, and the
viewport, copy, semantic-state, keyboard and provider assertions remain active.
Browser reopen is tested by destroying/recreating a browser context with its
persisted storage snapshot, then switching locale and restarting the guide.
A later responsive test run reached the unchanged 30-second test deadline
while other deterministic tools were running. The same per-element geometry
and overflow checks were batched into one browser round trip per step, with
positive-dimension and computed-visibility assertions added. All widths,
locales and steps remain covered; the complete 24-case rerun then passed.
The final computed-visibility assertion was subsequently verified in all six
responsive scenarios against the normal production build.

### Tests and gates

- Complete deterministic frontend suite: 43 `.test.ts/.test.mjs/.test.cjs`
  files, 262 tests passed. Includes four new guided-tour contract tests and
  existing design-system, provider, trust and runtime copy contracts.
- All legacy translation values and original coverage still match the release
  fingerprint. The newly added `guide.*` keys have independent explicit
  four-locale coverage, interpolation and fallback checks.
- `test:workspace-contract`: pass. `test:vnext-hardening`: 35 checks passed.
  `test-professional-workspace-flag-off.mjs`: pass.
- Related Python frontend/localization contracts: 36 passed across five files.
- Browser acceptance: `node e2e/run-e2e.cjs e2e/onboarding-tour.spec.ts
  e2e/i18n.spec.ts e2e/navigation.spec.ts --workers=2 --retries=0` — 24 passed:
  12 Chromium and 12 installed Chrome, including seven tour scenarios per browser.
  Live zh-TW→English and English→Japanese/Korean switches passed without a reload,
  semantic step reset or completion change.
- Final normal-production responsive verification: six passed (all three
  widths in Chromium and installed Chrome, every locale and step, with explicit
  computed visibility and positive geometry checks). Command:
  `node e2e/run-e2e.cjs e2e/onboarding-tour.spec.ts --grep='card has reachable
  controls' --workers=2 --retries=0`. Log:
  `.local/guided-tour-production-browser.log`.
- Typecheck: pass. Lint: zero errors, 23 existing warnings; no suppression added.
- Production build and test build: pass.
- Production `npm audit --omit=dev --audit-level=high`: zero vulnerabilities.
  Existing dev-only audit exception gate passes unchanged, expires 2026-11-04.
- Repository hygiene and diff check: pass.

### Production asset result

Both measurements use normal `npm run build`, not a comparison between test
and production environments. `scripts/check_frontend_bundle_budget.py` measures
all static assets and all JavaScript files; its `initial_javascript_bytes`
field is an aggregate, not measured first-page network transfer.

| Metric | Starting build | Final production build | Change |
| --- | ---: | ---: | ---: |
| All static assets | 2,997,356 B | 2,998,717 B | +1,361 B (+0.045%) |
| All JavaScript | 2,848,255 B | 2,851,882 B | +3,627 B (+0.127%) |
| Largest JavaScript chunk | 608,747 B | 597,008 B | −11,739 B (−1.93%) |
| Static asset count | 53 | 54 | +1 |
| JavaScript file count | 42 | 43 | +1 |

The guide is now loaded on demand in a 4,509 B minified chunk. No dependency,
animation library or budget constant was added/changed. Static budget (8 MB,
900 KB largest chunk), all existing route budgets and public-asset content
checks pass. The existing homepage route gate uses a 3,000,000 B aggregate
limit; 1,283 B remain, so the combined production lanes need to rerun it.
Route analyzer output is `.local/guided-tour-production-route.json`; it reports
`server_route_only` for its route-manifest breakdown, so the aggregate gate is
the asset evidence here rather than a claimed route-specific transfer size.

### Independent review

A separate read-only reviewer inspected the whole scoped diff and ran the seven
targeted onboarding/deduplication checks. Initial and follow-up reviews found
no Critical or Important issues. The optional request-monitoring suggestion
was resolved with an in-dialog Japanese switch. Follow-up coverage suggestions
were resolved with actual post-Skip/post-Finish language changes and explicit
Shift+Tab assertions. The reviewer confirmed the bounded RSC exemption,
document-continuity assertion and focus boundary implementation.

### Limitations and integration

This is a contextual workflow guide, not a tooltip tied to a live DOM target.
It neither opens workflow tools nor completes evidence checks. Manual opening
and the existing Methods → Accessibility entry are preserved; it does not
automatically re-offer onboarding or resume a partial tour. Locale does not
persist across app reloads, matching the existing provider architecture.

Browser automation covers Chromium and installed Chrome. Physical mobile
browser chrome, other browser engines and manual screen-reader sessions were
not tested. No live provider credentials or production backend were required.
Legacy tour keys used elsewhere remain intact; unused legacy keys are retained
to keep unrelated runtime-copy consumers unchanged.

The original implementation was suitable for a scoped PR after its recorded
gates, subject to integration against the final production lanes. The actual
integration and its fresh validation are recorded separately below. This lane
makes no statement about production closure or ML readiness.

### Changed-file inventory

1. `frontend_next/components/onboarding-tour.tsx`: replaces the existing tour.
2. `frontend_next/components/app-shell.tsx`: loads it on demand; removes actions.
3. `frontend_next/components/topbar.tsx`: localized restart entry.
4. `frontend_next/app/page.tsx`: removes tour workflow callback wiring.
5. `frontend_next/app/globals.css`: restrained motion and responsive E10 styling.
6. `frontend_next/lib/guided-tour.ts`: semantic steps and bounded persistence.
7. `frontend_next/lib/guided-tour-copy.ts`: 31 guide keys in all four locales.
8. `frontend_next/lib/runtime-copy.ts`: joins existing catalogue/resources.
9. `frontend_next/scripts/onboarding-tour.test.cjs`: deterministic contracts.
10. `frontend_next/scripts/runtime-copy-deduplication.test.mjs`: keeps original
    release fingerprint for all legacy keys and delegates new-key coverage.
11. `frontend_next/e2e/onboarding-tour.spec.ts`: targeted browser acceptance.
12. `docs/guided-tour-i18n-motion-v2.md`: architecture, plan and evidence report.

## Post-integration validation — 2026-10-09

### Baselines and safe integration

- Original implementation baseline: `b4eb441a8ccf90965102f0646006dc4b0e145491`.
- Integration baseline: `602830c8d4d405bb401afa902d5bf69f2c61066f`.
- Backup branch: `backup/guided-tour-i18n-motion-v2-1472a09`, pointing at the
  original feature commit `1472a09899e929a4e429d51e60ca1b4abd61cf71`.
  It was created before resetting or cherry-picking.
- Fetched `origin/main`, verified its required SHA, reset the clean feature
  branch to it, then cherry-picked the original feature commit. The integration
  commit existed before amending the implementation report.
- No conflicts occurred. All 19 files changed by PR #170 remain byte-identical
  to the integration baseline. The integrated frontend patch matches the
  original feature exactly; no implementation or test change was necessary.
- A second fetch after browser acceptance confirmed the baseline is still
  current. `git rev-list --left-right --count origin/main...HEAD` returned
  `0 1`. The feature remains a single commit with the integration baseline as
  its parent; the report is amended into that commit.

### Fresh deterministic, release and security evidence

- Guided-tour and translation-deduplication checks: 7 passed.
- Complete frontend deterministic suite: all 43 test files, 262 tests passed,
  no failures, cancellations or skips. Original legacy translation fingerprint
  remains unchanged; explicit guide coverage passes in all four locales.
- Workspace contract: pass. VNext hardening: 35 passed. Workspace flag-off
  checks for unset, false and unknown values: pass.
- Relevant Python frontend, locale, PR #170, provider acceptance, privacy,
  accessibility and release contracts: 168 passed across 16 files. One existing
  Starlette/httpx deprecation warning; this was a scoped run, not the complete
  backend suite.
- `npm run typecheck`: pass. `npm run lint`: zero errors, 23 existing warnings.
- Normal production build and dedicated acceptance build: pass.
- Production `npm audit --omit=dev --audit-level=high`: zero vulnerabilities.
  The unchanged dev-only exception gate passes for GHSA-vfj7-8cjw-p6xm,
  expiring 2026-11-04; its exception scope was not broadened.
- `security_performance_release_gate.py --json`: pass for environment,
  migration, persistence, required files, route budgets and threat model.
- `release_quality_gate.py --skip-tests --skip-frontend-build`: all nine
  contracts pass. Its embedded Python/build fields truthfully remain `not_run`;
  actual scoped tests and frontend builds were run separately above.
- Static bundle budget, unchanged 3,000,000-byte homepage aggregate ceiling,
  largest-chunk ceiling, other route budgets and public-asset content checks:
  pass. No budget, timeout, retry or accessibility requirement was relaxed.
- Repository hygiene and `git diff --check`: pass.

Logs are retained locally under `.local/guided-tour-integration-*`, including
`unit.log`, `targeted.log`, `python.log`, `typecheck.log`, `lint.log`,
`flag-off.log`, `release.json`, `security.json` and `hygiene.log`. Generated
artifacts are ignored and are not included in the feature commit.

### Browser acceptance and provider boundary

Command, against the dedicated acceptance build:

```text
node e2e/run-e2e.cjs e2e/onboarding-tour.spec.ts e2e/i18n.spec.ts e2e/navigation.spec.ts e2e/final-production-acceptance.spec.ts --workers=2 --retries=0
```

78 passed: 39 Chromium and 39 installed Chrome. This includes 14 tour cases,
6 locale cases, 4 navigation cases and all 54 PR #170 acceptance cases.
All widths (390 / 1024 / 1440), all four guide locales and all seven steps are
covered. Live locale switches retain the document, semantic step and outcome;
post-Skip/post-Finish switches and a reopened browser preserve completion
independently of locale. Keyboard-only completion, Tab/Shift+Tab containment,
Escape/focus restoration and reduced motion pass.

PR #170 acceptance confirms overflow, visible labels, focus indicators,
heading contrast, reduced motion and saved-case/finance provenance, including
A4 PDFs at all three widths in both browsers with the unchanged 20-page limit.
The 390px and 1440px tour screenshots were also visually reviewed for wrapping
and reachable controls.

Zero provider calls were observed in the tour lifecycle/locale journey and
PR #170 journeys. The tour observer remains active before routing; only the
existing bounded same-origin frontend RSC prefetches are exempt. Fixtures and
request interception provide local acceptance, not live-provider certification.
Log: `.local/guided-tour-integration-browser.log`; retained screenshots and PDFs:
`.local/guided-tour-integration-e2e-artifacts/`.

After restoring a fresh normal production build, an additional 12 browser
tests passed: all six responsive tour scenarios (every locale and step at all
three widths in both browsers), plus all six PR #170 A4 PDF/Save/Reopen cases.
Retries remained disabled and the final static size was rechecked afterward.
Command:

```text
node e2e/run-e2e.cjs e2e/onboarding-tour.spec.ts e2e/final-production-acceptance.spec.ts --grep="card has reachable controls|saved Taipei transit fixture" --workers=2 --retries=0
```

Log: `.local/guided-tour-integration-production-browser.log`.

### Final normal-production asset measurement

After the full acceptance suite, a fresh normal `npm run build` passed and was
measured again. This is not the dedicated E2E build. The complete build result
is **2,998,938 bytes**, below the unchanged **3,000,000-byte** ceiling by
**1,062 bytes**. The earlier 2,998,717-byte feature result belongs to the
original implementation baseline; integration adds 221 bytes to that result.

| Metric | Post-integration production build |
| --- | ---: |
| All static assets | 2,998,938 B |
| All JavaScript files | 2,851,844 B |
| Largest JavaScript chunk | 597,008 B |
| Static asset count | 54 |
| JavaScript file count | 43 |
| Homepage ceiling | 3,000,000 B |
| Remaining headroom | 1,062 B |

The route gate was explicitly asserted to return `pass`, with its homepage
ceiling still equal to 3,000,000. Public-asset admin, road-catalog and test-fixture
marker lists remain empty. The analyzer still reports `server_route_only` for
route breakdowns; aggregate asset size is not an initial-transfer measurement.
No implementation, dependency, test or budget was altered to obtain this result.
Evidence: `.local/guided-tour-integration-build-final.log`, `bundle-final.json`,
`route-final.json` and `production-assets.json`, with the same local prefix.

### Independent integration review and limitations

A fresh read-only reviewer compared the integration baseline, original feature
and integrated diff and ran all seven tour/deduplication checks independently.
No Critical or Important findings remain. The review checked stale locale text,
step resets, locale-specific completion, PR #170 preservation, provider calls,
accessibility, budget constants, duplicated i18n copy and global client loading.
The guide component remains loaded on demand; only 31 keys per locale join
the existing runtime catalogue. No animation library or large global client
logic was added, and the original translation fingerprint still passes.

Physical mobile browsers, other browser engines, manual screen readers,
hosted release validation and live-provider certification were not rerun.
The existing PR #170 production NO-GO and its owner/backend/deployment closure
requirements remain in force. These local checks establish software PR
readiness, not production acceptance. No push, merge or deployment occurred.
