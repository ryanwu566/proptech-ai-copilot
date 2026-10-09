# Evidence verification checklist V1

Implementation record for `feat/evidence-verification-checklist-v1`, based on
`95018f6fc2a366656cb798414dc54860d009e536`. Date: 2026-10-09 (Asia/Taipei).

## Implementation plan and contracts

The supplied direct-implementation specification authorizes execution in the
existing worktree. There is one final commit, with no push, merge or deployment.

- [x] Add failing deterministic checklist tests, then implement a pure projection
  of `CaseEvidenceModel.gaps`, fields and provenance. Group repetitive fields into
  allowlisted actions; retain individual material risk sources and identity limits.
- [x] Add a version 1 manual-review envelope inside `SavedCaseData`, with case and
  identity binding, bounded entries and size, strict validation and allowlisted
  serialization. Preserve prior review dates when evidence changes; never change
  source evidence. Test legacy, malformed, copied, stale and switched records.
- [x] Add draft review controls and explicit Save to the Overview workflow using
  the existing browser case repository and snapshot concurrency guards. Show
  storage failures and unsaved state. Add a frozen read-only report summary.
- [x] Exercise Chromium and installed Chrome, 390/1024/1440px, keyboard labels,
  Save/Reopen, switching, frozen report and A4 PDF; watch for provider requests.
- [x] Run frontend/model regressions, relevant Python regressions, lint,
  typecheck, production build/audit, release gates, unchanged 3,000,000-byte
  static budget and diff checks. Independently review trust and persistence.
- [x] Record exact outcomes for the requested single-commit handoff.

Review focus: external edits with unsaved drafts; malformed manual records;
identity changes followed by restoring an old identity; newly resolved gaps with
historical manual actions; browser storage failures without successful-save UI.

## Feature and reused evidence

`buildEvidenceChecklist` derives at most 19 domain actions from existing
`CaseEvidenceModel.gaps`, `EvidenceField`, `EvidenceSource`, risk match metadata,
`missingReason`, `limitation`, `nextAction` and case workspace `href`. It groups
repetitive market, POI, commute and finance fields, preserves each material risk
source, and includes the existing browser-identity boundary as an explicit gap.
Active price provenance and secondary demographics belong to existing actions.
Unknown, unsupported, no-match and numeric zero remain independent source states.
A usable matched hazard still requires its own verification action. There is no
score, safety clearance or readiness percentage from manual actions.

## Manual review, persistence and invalidation

`SavedCaseData.checklistReview` is an optional additive version 1 envelope:
`{ version: 1, caseId, entries }`. Entry fields are allowlisted `id`, `state`,
`identityToken`, `evidenceToken`, `reviewedAt` and `updatedAt`. States are
`not_checked`, `pending`, `reviewed`, `recheck`; a missing record is not checked.
Only the 19 known IDs are accepted, within a hard maximum of 24 entries and
8,192 serialized UTF-8 bytes per normalized envelope. Existing storage remains
`proptech.savedCases.v1`, limited to 10 cases; there is no additional database.
Unknown properties are stripped. Invalid versions, IDs, states, timestamps,
tokens, duplicate entries and copied case bindings quarantine the saved record
through existing diagnostics. Legacy cases without the envelope still reopen.

Tokens are bounded local change detectors, not authentication or verification
proof. They cover case/identity association and relevant field values, gaps,
source versions, check/update dates, scope, limitations and risk match metadata.
Evidence and identity changes project old actions as requiring recheck, retaining
the previous review date. Application writes also conservatively latch changed
domains to `recheck`, so restoring a former identity does not restore completed
checks. Report reads do not persist invalidation. An externally edited record
restoring all previous content has no independent audit authority: browser-local
manual actions are self-reported, not authenticated evidence.

New-case creation clears inherited manual records; resaving an existing case
retains them. Save uses the repository and existing identity/revision guards.
Malformed storage blocks snapshot writes instead of replacing damaged records.
Storage exceptions leave the draft visible and explicitly announce failure.
No provider payload, credentials, notes, photos or added personal information is
stored in the new envelope. Only the latest bounded action/date is retained,
rather than an unbounded audit log.

## Overview, report and user workflow

Overview shows three priority outstanding checks, then an expandable full list
grouped by Identity, Risk, Market, Location and Finance. Each action shows source
status, missing/limited reason, significance, saved source name/public URL when
available, next action, workspace link and explicitly user-provided review state.
Existing E2/E10 Section, Disclosure, Message and Button components are reused.

Open a saved case, open the complete checklist, mark a checkbox or choose a
review state, then use **保存人工核對**. Reopening that case restores the saved
state. Clearing a checkbox restores not-checked while retaining any prior review
date as history. The ordinary snapshot button saves already persisted case data;
manual checklist drafts have their own explicit Save and unsaved notice. A newer
external snapshot blocks a stale draft; reload the persisted state before editing
again. Switching cases discards unsaved local marks and uses that case's records.

The report adds a bounded read-only manual summary to the existing next-actions
section, retaining E9's nine-section and frozen-snapshot contracts. Sources,
unknown/unavailable evidence and user actions remain separate. Changing stored
manual records produces the existing newer-snapshot notice; only explicit newer
snapshot loading replaces the viewed report. Browser printing neither writes
reviews nor performs queries/recalculations. A4 print styles preserve readable
manual entries and suppress interactive controls.

## Bundle and independent review

Starting compiled production assets: **2,999,750 bytes**, largest JavaScript
chunk **608,747 bytes**. The initial build reached optimized compilation, then
correctly failed typecheck on the newly written RED feature tests; no feature
code was imported into those baseline assets. Final measurements below use
completed builds, with the existing **3,000,000-byte** strict ceiling unchanged.

Safe reductions: route Overview/Report/Compare through the existing shared
`evidence-entry` client boundary, separate read-only report rendering from editable
controls, and delete 442 translation literals whose later overrides always win
(314 resource literals, 88 runtime override literals, 40 experience override
literals). Four-locale outputs, interpolation and coverage exactly match the
starting release's SHA-256 fixture. No provider or ML architecture changed.

Independent read-only review checked official-verification claims, stale marks,
case contamination, missing/zero/no-match semantics, corruption, retention,
provider calls, frozen report semantics, styles and bundling. It found one
Important omission of usable matched hazards; a failing regression demonstrated
the omission and the fix passed. Additional match-metadata invalidation and
stale-draft browser tests were added. Final reviewer sign-off: no unresolved
Critical/Important findings; 19/19 feature/locale checks and diff check passed.

## Verification results

| Check | Result |
| --- | --- |
| Frontend deterministic regression | 258/258 passed, including 16 checklist and 3 exact translation-output checks. Initial feature tests failed before implementation as required. |
| Relevant Python regressions | 103 passed for case storage, commercial/location trust, decision-case boundaries, API cost, terrain/Google cost and anti-abuse; another 19 localization checks passed. |
| Broad browser regression | 214 executed across Chromium/Chrome: 212 passed, 1 flaky retry passed, 1 failed from the combined report/PDF test's 30-second total timeout. |
| Final checklist browser acceptance | 18/18 passed with one worker and **zero retries** in Chromium and installed Chrome. Split frozen-report operations and real A4 printing into focused tests, retaining assertions and the original timeout. This also passed the formerly flaky freshness journey. |
| Viewports/accessibility | Both browsers passed 390/1024/1440px without body overflow; native checkbox/select labels, Space-key interaction, disabled unsafe saves, status notices and storage-failure alerts passed. |
| Provider requests | Request watchers observed zero Google/GEE/TDX or analysis calls through opening, marking, saving, reopening, compare, report and real PDF generation. Deterministic read-only report checks also passed. |
| Actual A4 PDF | Both browsers produced 31-page existing reports, 595.92 × 842.88 PDF points. The bounded manual summary fits page 28. Extracted text stays within page bounds; both rendered summary pages were visually inspected and readable. Frozen text and stored data stayed unchanged. |
| Production build/typecheck | `npm run build` and separate `npm run typecheck` passed. E2E build also passed. |
| Strict production static budget | **2,997,356 bytes** total, largest JS **608,747 bytes**; **2,644 bytes** below the unchanged 3,000,000 ceiling. E2E static total was 2,997,060 bytes. Baseline-to-production reduction: 2,394 bytes despite the added feature. |
| Lint | Passed with zero errors and 23 existing unused-variable warnings; none introduced by the checklist. |
| Production npm audit | `npm audit --omit=dev --audit-level=high` passed with **zero vulnerabilities**. The all-dependency audit policy gate passed using the existing dev-only GHSA-vfj7-8cjw-p6xm exception, expiring 2026-11-04. |
| Security/performance release gate | Passed environment, migration, persistence, required files, route budgets and threat-model checks. |
| Diff/hygiene checks | `git diff --check` and `python scripts/check_repository_hygiene.py` passed. |

Reproduce frontend regressions from `frontend_next` with
`node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test lib/*.test.ts lib/*.test.mjs lib/workspace/*.test.ts lib/commercial/*.test.ts scripts/*.test.mjs scripts/*.test.cjs`.
For browser acceptance, run `npm run build:e2e`, then
`node e2e/run-e2e.cjs e2e/evidence-checklist.spec.ts --workers=1 --retries=0`.
Restore the normal production build with `npm run build` before measuring
`python scripts/check_route_budgets.py` from the repository root.

The full `release_quality_gate.py --skip-frontend-build` **failed** with
`python_tests_failed`; its nine source/deployment/privacy/accessibility contracts
passed. A diagnostic full pytest run stopped at 286 passed / 1 failed:
`test_physical_generation_metric_counts_worker_dispatch_not_startup` could not
start its mock Earth Engine workers before their existing deadline. A separate
worker-suite run passed 25 / failed 1 at
`test_timeout_kills_worker_before_one_bounded_replacement`. The same suite in an
isolated archive of the **starting SHA** passed 24 / failed 2, including that
timeout test and `test_crashed_worker_is_joined_and_replaced_once_without_request_replay`.
These worker tests and services are byte-for-byte unchanged by this branch.
This establishes a pre-existing worker lifecycle/timeout problem on this machine;
it does not establish that the full Python suite is green. No timeout, skip or
test expectation was relaxed. Resolve and rerun the full gate before merging.

No hosted acceptance or live-provider suite was run; provider-free behavior was
tested with saved fixtures and request interception. No push, merge or deployment
is performed. The branch can be pushed for a **draft review**, but is not ready
for release approval while the full Python release gate fails.
The frozen release candidate must not include this branch before its current
Final Production Acceptance completes, and requires renewed acceptance after
this feature is merged.

## Changed files (26)

- Documentation: `docs/README.md`, this implementation record.
- Commercial routes: `frontend_next/app/cases/[caseId]/overview/page.tsx`,
  `frontend_next/app/cases/[caseId]/report/page.tsx`, `frontend_next/app/compare/page.tsx`.
- Evidence UI: `components/evidence/evidence-entry.tsx`, `report-view.tsx`,
  `checklist-view.tsx`, `checklist.module.css`, `manual-review-summary.tsx`;
  Overview: `components/workspace/overview/overview-view.tsx` (all under `frontend_next`).
- Persistence/evidence: `frontend_next/lib/case-storage.ts`; under
  `frontend_next/lib/workspace`, `workspace-model.ts`, `legacy-case-adapter.ts`,
  `saved-case-diagnostics.ts`, `case-snapshot-save.ts`, `case-repository.ts`,
  `case-evidence.ts`, `checklist-persistence.ts`, `evidence-checklist.ts`.
- Equivalent translation reductions: `frontend_next/lib/runtime-copy.ts`,
  `runtime-copy-overrides.ts`, `experience-i18n-overrides.ts`.
- Regression tests: `frontend_next/lib/workspace/evidence-checklist.test.ts`,
  `frontend_next/e2e/evidence-checklist.spec.ts`,
  `frontend_next/scripts/runtime-copy-deduplication.test.mjs`.

Temporary baseline archives, PDFs, screenshots and diagnostic logs are ignored
local artifacts, not committed assets. No dependencies or budget constants changed.
