# ML-A3 authoritative source and lineage plan

Original implementation baseline: `8469c1f22b64a0e03be03a0099c59a8483d9e0c8`.
Latest integration baseline: `c2ddf1890897f44659b91079a563691fe337295e`
(includes PR #173 Production Guardrails). The completed research commit
`35fa74c8da3d18bba34bf99b03f502a01f90e7d8` was backed up and cherry-picked
without conflicts. Research code, contracts, source notes and five deterministic
artifact bytes retain the original implementation provenance. Integration checks
are recorded separately in the validation JSON; no conclusion changes.
The supplied ML-A3 request is the binding specification. Execute inline in
the existing worktree; exactly one final commit, no push, merge, deployment,
production changes, model training or ML UI. Zero approved rows is acceptable.

Architecture: extend `historical.py`, the existing staging parser and the
five-artifact aggregate builder/verifier contract. Preserve Target A/B and
the existing 21-month, 20-row maturity thresholds. No parallel framework.

- [x] Inventory the 17 known releases, stored manifests, schemas, official
  catalogs, change-service lead and existing cadastral/building adapters.
  Restore only previously hashed local bytes. Capture at most eight official
  metadata documents, 1 MiB/document, one attempt, 20 seconds/request.
- [x] RED then GREEN: exact-byte historical-proof conversion; dependency
  availability after version selection; lineage classifications; namespace
  ambiguity and explicit derived label; conjunctive ML-B Admission Gate v1.
  Cover originals, revisions, cancellations, replacements, multiple revisions,
  duplicates, conflicts, collisions and events after the prediction cutoff.
- [x] Add the ML-A3 aggregate builder using existing staging/distributions;
  emit marginal counts and sequential waterfall including chronological
  viability, month profiles, source classes, owner actions and provenance.
- [x] Run two create-only builds with identical frozen inputs; compare all
  five artifact bytes, hashes and privacy. Publish bounded JSON and report.
- [x] Independent read-only final reviewer: fabricated historical availability,
  identity/collision/revision/cancellation/replacement leakage, future data,
  thresholds, target/parking semantics, privacy and licensing. Resolve every
  Critical/Important issue using regression tests.
- [x] Run focused tests, all ML tests, full Python suite, repository hygiene,
  privacy and diff checks; document exact changed-file inventory and commit once.

Review focus: a dated URL/catalog update is not an exact-byte certificate;
current capture hashes cannot be backdated; selected correction with unavailable
dependencies must exclude without resurrecting its predecessor; future revisions
must not change earlier results; syntax does not authenticate external attestations.

Ruling: the detailed user specification authorizes implementation and one final
commit; additional approval rounds/intermediate commits conflict with that scope.
Use ignored `artifacts/ml/plvr-source-recovery/` for captures, logs and rebuilds.
Keep evidence rather than deleting verification material. Independent review is
explicitly requested; no implementation delegation.

Original implementation verification ledger: initial RED 28 missing-contract
failures; dependency hash and duplicate-conflict tests RED then GREEN;
machine-proof integration/hash/clock
tests RED then GREEN; builder and owner/contact privacy RED then GREEN. Independent
review: zero Critical/Important, one Minor superseded-duplicate classification
issue reproduced RED and fixed, including input-order invariance. Final focused
suite: 134 passed. Initial all-ML: 324 passed before the final review regression;
final all-ML: 325 passed. Two clean post-fix builds matched all five artifact
bytes and hashes with privacy PASS. Full Python: 3573 passed, 32 skipped, one
Starlette test-client deprecation warning, zero failures. Skips require explicit
disposable PostgreSQL targets, which were not configured. No pre-existing
failure claim was made. Public JSON privacy, repository hygiene and diff checks
passed. Exactly one final local research commit is the authorized finish;
preserve this worktree and all ignored evidence. No merge/push/deploy.
