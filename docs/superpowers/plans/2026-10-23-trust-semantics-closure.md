# Trust Semantics Closure Implementation Plan

**Goal:** Correct remaining trust wording and evidence semantics without new features.
**Spec:** User's Trust Semantics Closure request in this session.
**Architecture:** Preserve deterministic contracts and saved evidence. Correct the existing risk model, shared projections and presentation only.
**Tech stack:** TypeScript, Node native tests, Next.js/React.

## Constraints

- Work only in `feat/trust-semantics-closure-v1`, this existing isolated worktree.
- No push, merge, deployment, provider acquisition or other worktree writes.
- Main inspected at `c377ee94955429ab3d4804ffd8d8a6fae8c99a52`.
- Inspect PR #224 (`e6c3a70`) and #225 (`e0f97ab`) before edits; avoid all their changed files.
- Focused tests first; no heavy production build or full browser/backend suite.

## Tasks

1. Risk semantics: add counterexamples to `risk-evidence-model.test.ts` for unavailable/unsupported/outside-coverage positives, incomplete negatives, matched flood scenario and liquefaction classification. Verify failures, then fix `risk-evidence-model.ts`. Preserve partial positive matches. Check save/reopen and Overview/Report/Compare/Copilot consumers.
2. Affordability: reproduce income present but missing burden ratio in `finance-model.test.ts`; correct reason without changing arithmetic. Correct Overview's corresponding explanation. Check shared projection income follows the saved ratio basis. Ensure Compare cannot label an incomplete negative as no-match.
3. Copilot presentation: remove visible internal case ID, format saved/query/source dates with the existing validated date helper and locale formatter. Preserve all internal identifiers and citation bindings. Verify through targeted checks; do not modify #224-owned Risk/Overview view files.
4. Review the final diff, run focused consumer contracts, record verified defects, deferred overlaps, test results and exact recommended merge order in `docs/operations/trust-semantics-closure-v1.md`.

## Review focus

- Failed, unsupported and uncovered evidence must override inconsistent matched flags.
- A partial positive remains visible; incomplete negatives never become no-match.
- Missing coverage cannot silently become covered, including saved legacy summaries.
- Affordability income must correspond to its ratio basis; missing ratio is not missing income.
- Date display must retain unknown/source-vintage semantics and citation contracts.

## Progress

- Initial read-only inspection complete; baseline focused native tests: 82 passed.
- Tasks 1–3 implemented with failing counterexamples first. No file intersections with either open PR.
- Review correction: inconsistent but structurally valid affordability is downgraded locally, not rejected as an entire case. Diagnostic regression confirms other evidence remains visible.
- Review correction: absent terrain coverage remains unknown across save/reopen.
- Focused native contracts: 234 passed. Remaining protected presentation overlap and merge order recorded in `docs/operations/trust-semantics-closure-v1.md`.
- Task 4 complete: 69 render/storage tests and 62 Python contracts passed; final typecheck and whitespace checks passed; ESLint 0 errors with two configured E2E ignore warnings. Browser discovery only: 23 tests, no heavy suite run. Changes remain local and uncommitted.

## Integration closure after #225

- User explicitly authorized preserving changes, integrating latest main, one coherent local commit, pushing this branch and opening a PR against main. PR merge, deployment, #224 edits and other worktree edits remain prohibited.
- Fetched main `714d082ec64f12ee31e8a33f77f63531d8b94749`; #225 is merged. Preserved all 24 files with a byte-verified backup, fast-forwarded this worktree only, then reapplied the exact changes without conflicts.
- The 14 files from #225 remain identical to main. No changed-file intersections with #225 or latest #224 (`c3f866fbee4432ad86a572330d149b7384c7a35c`). No source or test changes were necessary for integration.
- Revalidated 234 trust contracts, 75 rendering/storage contracts, 34 location/Market contracts and 68 Python contracts: 411 passed. Typecheck and whitespace passed; ESLint 0 errors / 2 configured E2E ignore warnings. Browser discovery: 43 tests across 3 files; no heavy local suites.
- Deliverable is one Closure commit on the integrated main, with 24 changed files; publication and remote CI state are reported with the PR. Protected #224 follow-ups remain documented rather than edited.
