# ML-A2 authoritative history implementation plan

Original implementation baseline: `b4eb441a8ccf90965102f0646006dc4b0e145491`.
Integration baseline: `602830c8d4d405bb401afa902d5bf69f2c61066f`.
The supplied ML-A2 request is the binding specification. Work stays in this
worktree and this research branch; exactly one final commit, no push or deployment.

The outcome is a defensible evidence verdict, including zero approved rows.
Extend the existing full-ledger tooling through a research-only strict wrapper;
preserve existing Target A/B contracts and production code. Current captures,
release labels, Git dates and filesystem clocks never establish earlier bytes.

- [x] Inventory existing archives, manifests, official explanatory sources and
  acquisition mechanisms. Restore only the two previously hashed local archives.
  Record evidence classes and actual source/schema hashes without raw records.
- [x] Write and observe RED synthetic tests for publication binding, future
  revisions/cancellations, replacements, duplicates, conflicts, unknown lineage,
  no-parking semantics, chronological coverage and gate approval.
- [x] Implement archive-qualified as-of selection over the complete visible
  ledger, requiring explicit namespace and complete-history evidence bound to
  its cutoff and event membership. Never infer cancellation from disappearance.
- [x] Build aggregate namespace, parking, rights, distribution and chronological
  evidence; implement Data Gate v2 with both marginal diagnostics and sequential
  waterfall reasons. Approval requires qualified PIT evidence and viable frozen
  chronological folds. Prepare no new baseline contracts while blocked.
- [x] Run two independent create-only builds and compare every output byte/hash;
  record code/configuration/source/contract hashes and normalized provenance.
- [x] Run focused/all ML/full Python tests, hygiene and diff checks. Reproduce
  any claimed pre-existing failure against starting-SHA code in ignored storage.
- [x] Obtain an independent read-only review for temporal/revision/duplicate/
  cancellation leakage, privacy, parking and target semantics; resolve all
  Critical/Important findings, document evidence and make the one final commit.

Review focus: proof scope substitution; evidence timestamp ambiguity; future
events changing earlier selections; changed-identifier replacements; apparent
parking absence from blanks; nonzero counts accidentally granting ML approval.

Ruling: execute the user's already specified research work directly. Additional
design approval rounds and intermediate commits conflict with the authorized
task and its exactly-one-commit constraint. Use one independent final reviewer.

Original implementation verification: focused 97 passed; all ML 288 passed; full Python 3429 passed, 32 skipped, 1 warning. Two final clean builds matched all five aggregate artifacts with hash and privacy verification. Five Important and one Minor independent review findings resolved. No production/model changes. Earlier worker failures and original-baseline reproduction distinctions are recorded in the validation JSON.

## Integration onto the required main baseline

- [x] Preserve completed commit `6acbf4742671e8baf6201d3861f69d322a6e2ee5`
  on `backup/ml-a2-authoritative-history-original-6acbf47`.
- [x] Fetch origin and verify main remains
  `602830c8d4d405bb401afa902d5bf69f2c61066f` before the authorized reset.
- [x] Reset this clean feature branch to origin/main and cherry-pick the completed
  ML-A2 commit. No conflicts; existing gates and selector semantics preserved.
- [x] Distinguish original and integration baselines in code provenance and
  documentation; retain the original validation separately.
- [x] Rebuild twice in unused ignored directories and compare all five artifacts.
  Verify the Data Gate bytes and all aggregate research findings remain unchanged.
- [x] Rerun focused tests (97 passed), all ML tests (288 passed), full Python
  suite (3474 passed, 32 skipped, 1 warning), privacy, hygiene and diff checks.
- [x] Fold integration provenance and verification into exactly one final ML-A2
  commit ahead of main; require topology **0 1**. No push, merge or deployment.

Integration conclusion: historical publication proofs 0, PIT-valid 0, approved
training cohort 0, Target A BLOCKED, Target B BLOCKED, ML-B MAY NOT BEGIN.
