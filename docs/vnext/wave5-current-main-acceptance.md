# Wave 5 current-main acceptance — 2026-10-16

## Integration record

- Repository: `ryanwu566/proptech-ai-copilot`.
- Worktree: `C:\Projects\proptech-documents-citation-evidence-v1`.
- Branch: `feat/documents-citation-evidence-v1`.
- Starting HEAD: `785250f5013e9554a9b5abbc2998e90ab0d2b15f`; clean tree.
- Remote inspection: `git ls-remote --heads origin refs/heads/feat/documents-citation-evidence-v1 refs/heads/main` returned main only; feature unpublished.
- Backup: `backup/wave5-pre-current-main-20261016`, pointing to starting HEAD.
- Fetched main: `26f1b40b3be1b8984a2b587b799ac1451fb3845d`.
- Original merge base: `59631992e03c05ff01e67fb691710c738fcc6d1b`.
- Main advanced six commits; the starting feature had one commit.
- Three overlapping files: `components/decision-room/decision-room.tsx`, `components/evidence/report-view.tsx`, and `components/workspace/case-route-layout.tsx` under `frontend_next`.
- Rebase completed. Report retains main's Copilot link alongside Wave 5 references. Case layout retains main's `key={caseId}` remount and adds evidence to independently read routes. Decision Room combined automatically and was reviewed.
- No push, merge commit, deployment, migration file or migration registration.

## Acceptance work

- [x] Inspect and back up unpublished branch; rebase onto fetched main.
- [x] Review quarantine intake, scoped metadata, graph, references, Report and active Copilot boundaries.
- [x] Reproduce missing-field citation defect with failing tests; fix generation and resolution.
- [x] Add dangling-source/version, scope, zero, stale-history and Copilot projection regressions.
- [x] Independently review security and distinguish active paths from future adapters.
- [x] Finish browser, build, Python and performance validation; record results below.
- [x] Consolidate into one feature commit; verify parent, remote refs and clean tree at finish.

## Implemented foundation and future seams

The active evidence page and Report use the saved browser snapshot projection.
Stable IDs bind case, saved edition and observation; missing-field placeholders
remain gaps without citation IDs. Historical observations can still be referenced,
with stale state and no current authority. The resolver requires an existing
observation/version and, for documents, minimized metadata matching case/workspace.
Deleted cases and unavailable versions do not silently bind to another snapshot.

Active Grounded Copilot retains Wave 3's deterministic case-scoped references and
provenance UI. A regression checks that its selected snapshot facts also resolve
through the Wave 5 graph. This does **not** activate document consumption or replace
the conversation's references with `proptech-citation-v1`. Its scenario and Decision
Room seams remain bounded existing inputs. No model output becomes evidence.

Document intake and document graph functions are unexposed future server adapters.
The intake consumes at most 10 MiB, validates names/signatures/strict metadata and
returns only an immutable quarantine receipt. It performs no filesystem read,
URL ingestion, remote fetch, extraction, OCR, scanning, storage or SQL. Signature
screening is explicitly not malware validation. Documents remain pending/unverified.
Future authorization must validate membership, case assignment and purpose before
reading metadata or bytes. Browser isolation is not hosted tenancy/RLS proof.

No durable document vault or hosted persistence is claimed. The future schema
proposal remains in [the foundation document](documents-citations-evidence-v1.md).
Local saved editions retain the existing case + savedAt guarantee; out-of-band
changes reusing that timestamp are outside that browser revision contract.

## Independent security review

An independent read-only reviewer examined the rebased diff and follow-up fixes.
No Critical findings were identified. One Important finding was reproduced and
fixed: empty/not-run fields previously minted resolvable citations. Regression
tests first failed, then passed after filtering missing values and checking linked
observations, versions and document scope. A minor historical-value display issue
was also reproduced in Chromium before fixing the detail view to show the retained
value with an explicit stale label. The independent follow-up review found no
remaining Critical, Important or actionable Minor issues.

| Acceptance question | Reviewed behavior |
| --- | --- |
| Can documents inject Copilot authority? | No active ingestion/model transport; deterministic answers and minimized future reasoning requests do not interpret evidence as instructions. |
| Can nonexistent evidence resolve? | Invented IDs, missing observations, wrong versions and missing/mismatched document metadata return null. Empty snapshot fields have no citations. |
| Can A's evidence appear in B? | Active reads select exact case; resolver requires case and exact document workspace. Future durable authorization remains required. |
| Can stale sources appear live? | Snapshot origin stays saved; stale/superseded/failed/unknown references cannot become current support. |
| Can Report/Copilot opening call providers? | Their reads/answers are local; browser provider interception checks navigation, locale changes and reopen. |
| Can a user URL cause backend fetching? | No network or URL input in intake. Canonical metadata URLs are validated links only. |
| Can content execute HTML/script? | React text rendering, no content HTML sink or download route; active PDF name tokens rejected but receipt stays quarantined. |
| Can metadata expose secrets? | Strict minimized DTO keys; no filename/raw bytes/artifact/storage paths; extra private intake metadata rejected with bounded errors. Future prose/URL publication requires reviewed inputs. |
| Are unsupported capabilities honest? | UI/docs explicitly distinguish saved snapshots, unsupported/unavailable evidence, unimplemented extraction/OCR/scanning and future storage/authorization. |

## Validation

| Check | Result |
| --- | --- |
| All native frontend model tests (`node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test` over `frontend_next/lib/**/*.test.ts` and `*.test.mjs`) | 314 passed; includes 32 document/case/report tests and 19 Grounded Copilot tests |
| `npm --prefix frontend_next run test:consumer-auth` | 25 passed |
| `npm --prefix frontend_next run test:e2e:runner` | 1 passed after build |
| Relevant Python integration tests | 198 passed, 4 database-gated skips; one existing Starlette deprecation warning |
| Final `python -m pytest tests/test_document_intake.py -q` | 43 passed; includes 5 new private-metadata rejection cases |
| `npm --prefix frontend_next run typecheck` | Passed after final application changes |
| `npm --prefix frontend_next run lint` | Passed; zero errors, 23 unchanged warnings outside the Wave 5 diff; final changed-file lint also passed without warnings |
| `npm --prefix frontend_next run build:e2e` | Passed; Turbopack, TypeScript, static generation and new evidence route |
| Chromium and installed Chrome, retries=0 | 65 passed per browser, 130 total, no failures/skips/retries; one uninterrupted 13.8-minute run |
| Full `python -m pytest -q --tb=short` | 3,883 passed, 104 skipped, 11 failed; 1 existing warning; 1,028.45 seconds. All failures are in unchanged Earth Engine worker startup/lifecycle tests, listed below. |
| Existing route/global budgets | All 17 routes and coverage passed after fresh production-browser measurement; total static 3,323,152 / 8,000,000 bytes, largest JS 602,295 / 900,000 bytes |
| New evidence route | 1,154,638 client asset bytes; two cold samples each at 390px and 1440px; measured separately because the existing budget catalog has no evidence-route baseline |

The focused Python invocation covered `test_document_intake.py`,
`test_vnext_property_graph.py`, `test_vnext_parcel_evidence.py`,
`test_report_service.py`, `test_api_usage_quota.py`, `test_api_usage_ledger.py`,
`test_usage_durable_guard.py`, `test_selfhost_runtime.py`,
`test_ops_backup_tools.py` and `test_vnext_authorization.py`. The 198-test run
preceded the five additional intake security cases; the final 43-test intake run
includes them. These are overlapping suites, not additive distinct-test totals.

The final browser command uses `node e2e/run-e2e.cjs` inside `frontend_next`, with
`document-evidence.spec.ts`, `grounded-property-copilot.spec.ts`,
`commercial-compare-report.spec.ts`, `commercial-overview-save.spec.ts`, and
`property-scenario-lab.spec.ts`, and flags
`--project=chromium --project=chrome --workers=1 --retries=0 --timeout=120000 --max-failures=1`.
No assertions, retry counts, performance ceilings or timeouts were weakened.
Each browser covered 6 Wave 5 evidence cases, 8 Grounded Copilot cases, 25 Saved
Case/Compare/Report cases and 26 Scenario Lab regressions. Coverage includes
prompt injection, malformed storage/evidence, missing/deleted sources, historical
stale values, unsupported states, actual source resolution, locale stability,
case switching, provider-free reads, mobile keyboard navigation and Report print.

The initial combined route measurement failed at navigation to the final route,
`/cases/[caseId]/commute-planner`, under the helper's 210-second whole-run cap.
The same official measurement helper was then run in groups of 6, 6 and 5 routes,
with unchanged two cold samples per viewport (390px/1440px), provider blocking,
route-view checks and deadlines. All batches passed. Their receipts were combined
only after checking the build fingerprint remained identical, then evaluated by
the unchanged route-budget checker. No threshold or baseline was increased.
The evidence route's separate measurement uses the same sampling/network policy
with a selector for the new page; no new persistent budget baseline is claimed.

The first build caught nullable feature imports in new tests; those guards were
corrected before the passing final typecheck/build. An initial runner guard test
was started while the build had removed BUILD_ID; rerunning it after build passed.
The intentional browser red test reproduced the historical-value defect, then the
final application build was regenerated. None of these preliminary runs is
represented as a passing final run.

### Full Python failure classification

The full suite is **not green**. Every failure is in
`tests/test_earth_engine_worker_pool.py`; its implementation and test blobs match
authoritative main exactly. Most failures report the spawned worker manager still
`unavailable` rather than `available`; the replacement-generation and credential
reason assertions also depend on startup completing. An isolated rerun of
`test_result_with_wrong_request_id_or_generation_is_rejected` reproduced the same
readiness failure. These are classified as unchanged Windows worker-startup /
lifecycle failures, not suppressed or repaired by changing timeouts in Wave 5.
The same named test also failed with the same unavailable/available assertion in
an isolated archive of authoritative main (`26f1b40`), containing only main's
services/config, test and conftest. That baseline run failed in 12.21 seconds,
without importing Wave 5 code. The baseline log is retained locally under
`.tmp/wave5-main-worker-baseline-result.log`.

Failing tests:

- `test_physical_generation_metric_counts_worker_dispatch_not_startup`
- `test_result_with_wrong_request_id_or_generation_is_rejected`
- `test_manager_captures_project_once_and_never_accepts_per_request_project`
- `test_crashed_worker_is_joined_and_replaced_once_without_request_replay`
- `test_timeout_kills_worker_before_one_bounded_replacement`
- `test_failed_replacement_cleans_other_worker_and_all_pipes`
- `test_startup_failure_maps_to_truthful_allowlisted_reason[credential_unavailable-credential_unavailable]`
- `test_two_active_two_queued_and_fifth_fails_closed`
- `test_cancelled_queued_request_never_acquires_worker_or_sends_ipc`
- `test_repeated_queued_cancellation_does_not_accumulate_executor_work_items`
- `test_admission_slot_is_released_exactly_once_in_cancel_race`

The full run collected 3,998 tests before the five extra intake security tests
were added; those five are covered by the final 43-test intake run. No full-suite
rerun is claimed after adding them. Full logs remain in the system temp directory
as `wave5-full-python-20261016.log`; summarized failures are retained here.

## Changed files

Nineteen files comprise the final feature relative to main:

- `docs/vnext/documents-citations-evidence-v1.md`
- `docs/vnext/wave5-current-main-acceptance.md`
- `frontend_next/app/cases/[caseId]/evidence/page.tsx`
- `frontend_next/components/decision-room/decision-room.tsx`
- `frontend_next/components/evidence/citation.tsx`
- `frontend_next/components/evidence/document-evidence-page.tsx`
- `frontend_next/components/evidence/document-evidence.module.css`
- `frontend_next/components/evidence/report-view.tsx`
- `frontend_next/components/workspace/case-route-layout.tsx`
- `frontend_next/components/workspace/workspace-navigation.tsx`
- `frontend_next/e2e/document-evidence.spec.ts`
- `frontend_next/e2e/helpers/provider-request.ts`
- `frontend_next/lib/workspace/compare-report-model.ts`
- `frontend_next/lib/workspace/document-evidence-copy.ts`
- `frontend_next/lib/workspace/document-evidence.test.ts`
- `frontend_next/lib/workspace/document-evidence.ts`
- `frontend_next/package.json`
- `services/vnext/document_intake.py`
- `tests/test_document_intake.py`

Auth/account, quota, selfhost/Professor preparation and existing scenario/route
implementation files remain identical to main. Their relevant behavioral checks
are included above; inherited full-suite failures are classified separately.

## Final local disposition

The feature is consolidated as one commit above
`26f1b40b3be1b8984a2b587b799ac1451fb3845d`, with subject
`feat: add documents citation and evidence graph foundation v1`. The final SHA
is reported by `git rev-parse HEAD` in the handoff; it is not embedded in its own
commit. The original feature remains on the backup branch recorded above.

The final remote check still returned main only, with the authoritative SHA;
the feature branch remains unpublished. Final checks verify the direct parent,
one-ahead/zero-behind topology, 19 changed files, no migration changes and clean
tracked/untracked status. Ignored local measurement/baseline artifacts are not
part of the feature commit.

Safe to publish this feature branch: **YES**, with the full-suite baseline failures
explicitly disclosed above. This is bounded foundation acceptance; document
ingestion/hosted persistence remain future work. No push, merge or deployment
was performed.
