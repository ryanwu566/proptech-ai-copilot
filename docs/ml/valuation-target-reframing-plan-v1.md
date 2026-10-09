# Target reframing implementation plan v1

User-authorized implementation scope: the Wave 1 request. Starting SHA:
`95018f6fc2a366656cb798414dc54860d009e536`; isolated worktree and required branch
verified clean. Exactly one final commit; no production changes or training.

Design: preserve Target A. Target B predicts a recorded transaction's gross
NTD per transferred registered building ping in a conservative no-parking
residential subset. A reported one-building transaction is not a proved dwelling.
Unknown complete rights and unresolved private/common detail multiplicity remain
explicit limitations. Candidate discovery is separate from revision-qualified,
point-in-time selection and approved chronological training membership.

1. Inspect exact local 112S3/115S2 bytes, embedded schemas, complete Taipei/New
   Taipei detail joins and current official explanatory sources. Copy only the
   existing two archives and acquisition metadata into this worktree's ignored
   artifact root. Preserve retrieval timestamps; do not download archives.
2. Add `observed-transaction-target-v1.json` and `observed_transaction.py`.
   Interfaces: `classify(item, cutoff)`, `build_candidates(items, cutoff)`,
   `feature_values(item, target)` and `baseline_history(...)`. Reuse strict raw
   parser, parking diagnostics, Decimal target arithmetic and full-ledger as-of
   selector. Test semantics, no-parking conflicts, unknown unit/rights labels,
   count/area/price errors, geography, leakage and row conservation RED→GREEN.
3. Extend chronological proposals with a separate explicit cohort selector,
   preserving the existing default for A. Test B-specific historical membership,
   duplicate families, future versions, publication boundaries and baseline
   frozen fitting membership. No random or forced four-block partitions.
4. Add `audit_target_reframing.py`: exact-source preflight verification → existing
   raw parsing → normalized staging → candidate ledger → revision/PIT checks →
   conservative split proposal. Outputs are create-only and ignored. Commit only
   bounded aggregates; manifest pins sources, schema, registry, code, contract,
   features, cutoffs and every output hash. Test source tampering, privacy and
   deterministic synthetic builds; perform two real clean offline builds.
5. Run all ML regression tests and the full Python suite. Obtain an independent
   review of semantic/temporal boundaries, code and reports; fix substantive
   findings with regressions. Record exact verdicts and evidence in the requested
   Markdown/JSON report. Verify privacy, git diff and sole bounded commit.

Review focus: candidate rights/unit ambiguity must never turn into property
valuation claims; detail joins must not inflate rows; future ineligible revisions
must not resurrect an older eligible row; current observations must not backdate
publication; baseline inputs must use B and frozen version membership.

Validation: `python -m pytest tests/test_ml_*.py -q` (expand filenames in
PowerShell); `python -m pytest -q`; two fresh outputs from the audit CLI must match
all hashes and include nonzero candidates without granting training approval.

Execution evidence: 53 focused tests and all 244 ML tests passed. Both final real
builds matched all 14 files, with 2,267 nonempty research candidates and zero
approved rows. Source-manifest availability bindings, output hashes, line-count
conservation and privacy passed. Independent code/report review found one
Important provenance defect and one normalization defect; both were reproduced
and corrected with regression tests, independently rechecked, with no unresolved
findings. Full final Python validation and final commit checks are recorded in
the delivery report and machine evidence.

User requirements supersede skill defaults: use the existing isolated worktree,
implement the supplied scope directly, retain it, and create only one final
bounded commit. No extra approval round, per-task commits or integration menu.
