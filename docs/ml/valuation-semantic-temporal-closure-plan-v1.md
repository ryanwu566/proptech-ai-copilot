# ML semantic and temporal closure implementation plan

Goal: extend the merged offline contracts with executable semantic and temporal
validation, then rebuild the two exact recovered releases without weakening the gate.

Authority: the user's 57-part implementation specification. Work stays in this
worktree; one final commit; no training, production changes, push, merge or deploy.
The worktree is already isolated. Existing ML baseline: 122 tests passed.

Architecture: reuse raw CSV/schema/member parsing, geography, parking, Decimal
targets and explicit revision chains. Add separate rights/dwelling, availability,
cohort and chronological-history modules. Evidence of missing semantics remains
missing; reviewed supplemental evidence must bind exact main/detail content.

## Tasks

- [x] Semantic classifiers: write failing fixtures for full/partial/mixed rights,
  denominator errors, object multiplicity, missing roles, duplicate details and
  main/detail disagreement; implement strict classifiers and target prerequisites.
- [x] Availability and revisions: test exact/date-only/conservative/first-seen
  evidence, content binding and historical cutoff rejection; implement UTC bounds.
  Extend existing selector with per-occurrence dispositions and predecessor edges.
- [x] Cohort builder: test row conservation, unique membership, semantic exclusions,
  future effective dates and deterministic output. Preserve main/details privately;
  select revisions before admitting targets; emit only reviewed Model A columns.
- [x] Chronology and baseline support: test insufficient/discontinuous history,
  month precision and release lag at block freezes; require 12 train months and
  three months each for validation/calibration/test. Implement as-of history
  selection before baseline ranking; no baseline fitting or model training.
- [x] Real builds: rehash restored 112S3/115S2, inspect complete Taipei/New Taipei
  members, persist all classifications/exclusions and aggregate coverage; run two
  clean independent processes with varied hash seed/timezone and compare hashes.
- [x] Independent review and validation: fix Critical/Important findings with red
  tests, run all ML and relevant Python regressions, privacy and whitespace checks.
  Publish aggregate evidence, full report and a new readiness gate, then make one
  bounded commit with the user's exact message.

## Review focus

Land ownership fractions are not whole-dwelling transfer fractions. Building
detail rows include common portions and omit building identifiers. Repeated
details are retained and cannot multiply or attest objects. Current archive
retrieval can provide only a conservative bound at that observation, never an
earlier publication date. Unknown identity/revision evidence quarantines a family.
Scoring-label availability does not grant training or baseline access.

Ruling: use ignored artifacts/ml/plvr-source-recovery for the execution ledger and
all private evidence, honoring the existing ignored storage contract. The supplied
implementation specification authorizes execution and the sole final commit;
additional design/plan approval commits would contradict that instruction.

Execution outcome: 122 existing + 69 new ML cases passed; full Python regression
3,035 passed, 31 skipped, one existing warning. Both delivered builds match all
13 files and bind the frozen code/contract. No real full-right or single-dwelling
confirmation exists; approved cohort remains zero and the new gate is BLOCKED.
Historical membership is independently selected at each freeze; later revision
differences refuse a proposal rather than silently rewriting training history.
The user's exact final local commit is the integration decision; preserve the
branch/worktree and ignored evidence, with no push, merge or deployment.
