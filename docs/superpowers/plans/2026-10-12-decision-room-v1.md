# Property Decision Room v1

User brief is the binding spec. Implement in the existing isolated worktree and produce exactly one local commit; no push or merge.

## Design and boundaries

Each saved property gains `/cases/[caseId]/decision-room`. A read-only case adapter provides identity, saved asking price, and evidence states. A separate repository stores a versioned, bounded document per case ID under `proptech.decisionRoom.v1.*`. The core saved-case storage writer, its schema, and its repository remain untouched for concurrent PR #181.

The room contains viewing notes, editable checklist items, questions, follow-up tasks with owner/due date/resolution, manual check records with source URL/note/check date, manual asking price and provenance, a derived evidence gap list, and a bounded activity log. Completion of an item never verifies evidence. Manual checks are explicitly user records, never official verification. No provider requests, generated facts, or scores.

Persist only validated bounded data. Distinguish empty, corrupt, unsupported, unavailable, full, and conflicting storage. Failed saves retain the editable draft. Revision checks prevent overwriting a newer document; storage subscriptions detect another tab. The case adapter blocks rooms for missing or unreadable cases. UI text uses four complete catalogues (zh-TW/en/ja/ko); user-authored text remains as written. Use existing design tokens and accessible native controls, with 390/430/1024/1440 layouts.

Review rulings: serialize browser writes with per-case Web Locks, then recheck the case and room revision inside the lock. Preserve pending forms when either case or room reads fail. After explicit reload, apply only edited fields over the latest records; keep removed-record drafts available to copy or cancel. Disable controls while a save is pending. Browsers without Web Locks fail closed on saves. No core writer is involved in these safeguards.

## Execution

1. Write failing domain/repository tests. Implement the independent model, validation, gaps, revision checks, browser storage boundary, and activity retention. Verify no other storage keys change.
2. Implement the read-only case adapter and all four locale catalogues. Test that unknown/stale saved evidence remains unknown/stale after manual work.
3. Write browser acceptance tests before the UI. Build the usable route, structured editors, explicit saves, recoverable error states, conflict handling, and history. Add one localized navigation entry and narrowly bypass the old snapshot-write header for this route.
4. Typecheck, lint changed files, run frontend regression tests and focused Python architecture tests, build production E2E output, and browser-test editing/reload/case isolation/errors and all locale/viewport combinations. Inspect screenshots.
5. Review the final diff and verify storage files are unchanged. Record actual results and known limitations in an implementation note. Commit all deliverables once. Verify clean status and exactly one commit since base `8b1367a`.

## Integration after PR #181

Replace only the case context adapter or Decision Room repository to adopt the merged persistence API. Do not copy room data into saved-case snapshots. Browser-local v1 data has bounded history (latest 200 events), is device/browser specific, and is not collaborative server storage.
