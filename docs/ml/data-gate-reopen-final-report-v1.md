# Data Gate Reopen v1 final report

**ML-B AUTHORIZED: NO.** Target A remains BLOCKED. Target B remains BLOCKED for
training/evaluation. The real rebuild retains 2,267 research candidates, zero
PIT-valid observations, zero chronological observations and zero approved cohort.
No model was trained, no production valuation/UI was changed, and nothing was
deployed or pushed. No new official receipt or historical proof was obtained.

| # | Requested result | Evidence/result |
| --- | --- | --- |
| 1 | Starting SHA | `9832e8b3f88104441475c82a49d192b838090d07` |
| 2 | Final fetched origin/main SHA | `9832e8b3f88104441475c82a49d192b838090d07` |
| 3 | Files changed | 14; exact inventory below. Changes remain confined to offline ML research, tests, documentation and LF attributes for the three canonical aggregate artifacts. |
| 4 | Pipeline map | Official source → private original/manifest → receipt/schema/hash/authority/scope validation → source/schema/detail registry → full version/cancellation/replacement history → Target B/PIT selection → freeze-specific chronology → frozen admission → private approved cohort only on PASS. Exact existing function owners are in the [runbook](data-gate-reopen-runbook-v1.md#pipeline-and-ownership). |
| 5 | E1 | IMPLEMENTED VALIDATION; MISSING REAL EVIDENCE. No authenticated historical hash/publication binding for the two retained archives or a complete expanded panel. |
| 6 | E2 | IMPLEMENTED VALIDATION; MISSING REAL EVIDENCE. Namespace uniqueness/reuse/correction/cancellation/replacement semantics remain unverified. |
| 7 | E3 | IMPLEMENTED VALIDATION; MISSING REAL EVIDENCE. Full authoritative revision/cancellation/replacement/duplicate events and per-freeze completeness certificates are absent. Cross-namespace replacement acceptance remains MISSING SOFTWARE: existing quarantine is preserved, and unresolved edges now block the entire admission. |
| 8 | E4 | IMPLEMENTED VALIDATION added for the exact provider manifest, explicit predecessor order, dates, scope, no gaps and complete-through cutoff. MISSING REAL EVIDENCE: no complete release-continuity attestation or historical panel. |
| 9 | E5 | Existing rights/unit mapping validation is preserved. NOT REQUIRED FOR TARGET B; MISSING REAL EVIDENCE and still required for Target A. |
| 10 | Current real dry-run decision | **BLOCKED**; both complete operator invocations exit 1 as documented. [Machine decision](data-gate-reopen-dry-run-v1.json), [human summary](data-gate-reopen-dry-run-v1.md). |
| 11 | PIT-valid count | **0**. Chronological count also **0**. |
| 12 | Approved cohort count | **0**; no real frozen cohort exported. |
| 13 | ML-B authorized | **NO** (`false`). |
| 14 | Synthetic contract tests | **27 passed**, software behavior only. An 840-row, 21-month, two-city synthetic panel satisfies unchanged numeric thresholds and four disjoint blocks. Missing authority, cancellation/replacement chain, changed-ID predecessor, continuity, corrupt bytes, future revisions, family duplication, private output and frozen artifact corruption are exercised. The archive/parser boundary is substituted in the synthetic double-rebuild orchestration test; actual source integrity/parser behavior is separately tested and exercised by the real rebuilds. |
| 15 | All ML test files | **403 passed, 0 failed** using PowerShell-expanded `tests/test_ml_*.py`. |
| 16 | Privacy | **27 passed, 0 failed** under `python -m pytest -q -k privacy`. Actual aggregate output vocabulary/hash checks also pass. No raw government transaction rows, addresses, official transaction tokens, applicant details or proof bodies are committed. |
| 17 | Deterministic double run | **PASS**: two operator invocations, four fresh raw-source rebuilds, all three emitted files byte-identical. Both report `double_build_equal=true`; indexed output bytes also survive Windows autocrlf filtering unchanged. |
| 18 | Full Python suite | **3,993 passed, 104 skipped, 0 failed**, one existing Starlette/httpx deprecation warning. No worker-pool failure occurred, so no baseline-flake classification or unrelated ML workaround was needed. Skips comprise 102 cases requiring explicit disposable PostgreSQL and two platform cases (symlink creation unavailable; Unix identity permissions). |
| 19 | Independent review | Separate read-only reviewer: **0 remaining Critical, 0 remaining Important**. Fixed full-history/dangling-predecessor admission closure, ordered explicit intake provenance, and bounded hash diagnostic classification. Final reviewer checks: **10 passed**. No claim of independent government authentication is made. |
| 20 | Remaining external evidence | E1 exact original bytes/version hashes with trustworthy historical publication bounds; E2 authoritative namespace/reuse/change-key rules; E3 all original/revision/tombstone/replacement/duplicate edges and exact full-visible-ledger completeness at final and every fold cutoff; E4 all overlapping original/full-refresh/version releases, explicit links, coverage and no-gap attestation through the observation cutoff. For Target A additionally E5 registered unit counts, private/common object roles, numeric required/transferred building and land interests and exact PLVR linkage, with non-personal proof and lawful reuse. |
| 21 | ML-2 handoff | Defined: approved cohort; frozen train/validation/calibration/test memberships; frozen allowlisted features and labels with their contracts; source manifest; chronology; PASS decision; summary and complete hash manifest. The guard independently rebuilds and compares every artifact; missing/extra/tampered artifacts or self-asserted PASS cannot authorize ML-2. Exact filenames and commands are in the runbook. No ML-2 branch or training implementation was created. |
| 22 | No model trained | **CONFIRMED. NO MODEL WAS TRAINED.** No estimator was fitted and no accuracy/error/prediction claim was generated. |
| 23 | Final SHA | The single local commit containing this report; its exact SHA is supplied in the delivery response. Embedding its own commit SHA would change that SHA. |
| 24 | Clean tree | Verified after the delivery commit; research branch/worktree retained. Raw originals and runtime verification logs remain private/untracked. |
| 25 | Safe for research PR | **YES**, based on local verification and corrected independent review findings. This is research PR readiness, with ML-B still unauthorized. No PR, push, merge or deployment was executed. |
| 26 | Exact push command | `git push -u origin research/ml-datagate-reopen-v1` — supplied only; not executed. |

Exact changed files:

- `.gitattributes`
- `scripts/ml/audit_target_reframing.py`
- `scripts/ml/external_evidence.py`
- `scripts/ml/reopen_data_gate.py`
- `scripts/ml/check_training_authorization.py`
- `tests/test_ml_data_gate_reopen.py`
- `docs/ml/contracts/data-gate-bundle-v1.schema.json`
- `docs/ml/contracts/release-continuity-v1.schema.json`
- `docs/ml/data-gate-reopen-runbook-v1.md`
- `docs/ml/data-gate-reopen-dry-run-v1.json`
- `docs/ml/data-gate-reopen-dry-run-v1.md`
- `docs/ml/data-gate-reopen-output-hashes-v1.json`
- `docs/ml/data-gate-reopen-validation-v1.json`
- `docs/ml/data-gate-reopen-final-report-v1.md`

The [validation record](data-gate-reopen-validation-v1.json) records commands,
Python/contract versions, source/receipt/bundle/admission/code/chronology hashes,
all output hashes, private test-log/XML hashes, counts and review closure. The
public hash manifest preserves the command's original `decision.json` and
`summary.md` names; they correspond respectively to the tracked
`data-gate-reopen-dry-run-v1.json` and `data-gate-reopen-dry-run-v1.md`.

Real inputs were private copies of the previously captured exact 112S3 and
115S2 archives with their original recorded retrieval metadata. The explicit
logical observation remains 2026-10-11 and the evaluation cutoff remains
2026-06-30 23:59:59 Asia/Taipei. No new execution/publication timestamps were
manufactured. The current bundle contains **zero** receipts. These inputs were
not promoted to historical publication evidence. The owner must obtain and
review the missing official material before any future admission can change.
