# Commercial Compare / Report implementation plan

**Goal:** Descriptive comparison of 2–4 saved cases and a defensible single-case evidence snapshot, with no ranking or automatic analysis.

**Architecture:** Existing saved-case root → diagnostic validated repository → Reality Closure workspace adapter → typed CaseEvidenceModel → ComparisonModel / ReportModel. All values come from local saved evidence. E2 primitives provide the UI. A dedicated report prints through the browser.

**Execution:** Native implementation in the user-designated existing worktree. The user supplied the complete E9 specification and authorized implementation; no additional design approval or intermediate commits. Exactly one final commit after all required gates pass. No push, merge, or deployment.

## Rebaseline

- Reuse `legacy-case-adapter`, numeric Market/Valuation contracts, origin-bound `location-context`, `risk-evidence-model`, and `restoreFinanceModelFromSnapshot`.
- Legacy revision 1 is compatibility context, not history. Fingerprint normalized visible evidence for report freezing.
- Saved timestamps do not establish check times. Preserve origin, input relation, and source time policy independently; no age threshold.
- Current read path masks storage errors. Add diagnostic reads without changing existing caller return types; reject malformed/duplicate IDs without substitution.
- Risk summaries lose unsupported state, source URL, and query context. Add optional versioned whitelist metadata, preserving conservative legacy interpretation.
- Old saved-case ranking and export entry points lead to weighted comparison / global session export. Redirect their entry actions to E9. Bounded live legacy tools remain separate.

## Tasks

- [x] 1. Repository diagnostics: tests for empty, parse/storage errors, invalid record, duplicate identity, strict core validation; implement `readSavedCasesDiagnostic` and repository diagnostic reads. No migration writes.
- [x] 2. Projection: tests for partial, zero/null, stale, failed valuation, origin mismatch, independent TDX failure, risk states, finance assumptions and gaps; implement `projectCaseEvidence(workspace)` with explicit fields and safe URLs.
- [x] 3. Models: selection tests for 2/3/4/5, duplicates and order; implement `buildComparisonModel`, `buildReportModel`, snapshot change assessment. Deterministic summary with nine fixed report sections.
- [x] 4. UI: write Playwright acceptance tests before routes; build `/compare` desktop table and mobile two-case vertical rows, `/cases/[caseId]/report`, frozen state and recovery, print styles, bounded entry actions.
- [x] 5. Verification: affected model/storage/identity tests, E3–E8 and Reality Closure browser suites, Chromium and installed Chrome, 390px, print/PDF artifact, zero-provider interception, lint/typecheck/build/audit/release/security gates and diff check.
- [x] 6. Fresh independent trust review, fix Critical/Important findings, document final evidence; exactly one bounded commit if all required gates pass.

## Review focus

- Malformed nested evidence cannot crash or silently become not-run.
- Duplicate IDs cannot select the wrong record; clear-all storage events must invalidate open reports.
- Missing/stale values cannot become primary current numbers; finance totals already include mortgage.
- Saved risk no-match/unsupported/manual verification cannot imply safety.
- Storage changes during print must stop deleted/invalid cases while updated valid reports retain the visible snapshot until explicit acceptance.

## Progress

- Starting state verified: clean branch `feat/commercial-compare-report-v1`, HEAD and local origin/main `b735c52f698de0355539cdcff170e3ccde5f8d7b`.
- No AGENTS.md found inside the designated worktree. Existing worktree confirmed; all implementation and artifacts stay here.

- Completed repository/model/UI/print work and trust fixes. Full Python 2,933 passed / 31 skipped; native library 185 passed; all 190 unique browser checks pass across full regression and corrected affected rerun; final production E9/entry/Reality 44 passed. Lint/typecheck/build/audit/release/security pass. Final independent review has zero remaining Critical/Important. See `docs/commercial-compare-report-e9-validation.md` for the requested 50-item record.
