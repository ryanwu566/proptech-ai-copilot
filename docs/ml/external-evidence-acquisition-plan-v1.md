# ML-0 external authoritative evidence acquisition

Baseline: `c9ab5f61a45f7f704326af66cb0bea02740b9927`; branch
`research/ml-external-evidence-acquisition-v1`. User specification is the
attached Parts A–N. This extends existing offline research flows in
`scripts/ml`; it has no production, database, UI, training or evaluation path.
The supplied worktree is already isolated. All work goes in one final commit.
Delivery ancestry audit: the branch reflog records an earlier rebase onto
`origin/main`; the actual precommit parent is
`ef1c49c55a58eb0ab63beefe0cd2ddc1f2f9717b`, with two upstream commits after the
supplied baseline. Preserve that ancestry and create one new research commit;
report the distinction rather than claiming one total ancestor from the baseline.

Design: preserve ML-A3 selectors and target contracts; validate four external
receipt types against retained, hashed proof material, then adapt reviewed
receipts into existing publication, identity, event, history and rights inputs.
Unreviewed, synthetic, current-only, ambiguous, unknown-license or incomplete
inputs cannot grant real eligibility. Format/hash checks do not authenticate
government authority: an accountable human review of retained official material
is required. Replacement across namespaces remains quarantined by the selector.

1. Research a bounded list of official MOI/PLVR/catalog/NLSC/local land/building
   sources. Retain available small metadata responses privately with URL, time,
   size, SHA-256, terms and purpose; report failed transports without fake hashes.
   Produce the E1–E5 acquisition map and Chinese request drafts. Never send them.
2. Write synthetic receipt and adverse-input tests first; observe RED. Implement
   `external_evidence.py`, a machine-readable contract and metadata capture shell.
   Cover missing time, hash, current-only, identity ambiguity, event completeness,
   cancellation, replacement, rights roles, privacy, license and artifact bounds.
3. Freeze admission policy in `contracts/ml-b-admission-v2.json`: retain existing
   21 contiguous months, >=20 rows/month, 12/3/3/3 TRAIN/VALIDATION/CALIBRATION/TEST,
   >=20 rows per district/type per block, with >=20 rows per city per month and
   >=840 PIT rows across both cities; complete publication/lineage coverage,
   per-freeze certificates, privacy, determinism and unchanged target contracts.
   These are minimum feasibility safeguards, not power or accuracy guarantees.
4. Implement `refresh_external_evidence.py`: deterministic offline receipt
   ingestion, full-ledger gate/chronology refresh, aggregate-only output and
   input/output hashes. Restore the two inherited archives read-only and rehash;
   no new transaction dataset download. Empty real receipts must still yield 0.
   Future broader chronology uses a bounded private staging ledger, with every
   archive/member/schema hash checked. No synthetic flag on the real CLI.
5. Run focused/all-ML/full Python tests, deterministic independent rebuilds,
   privacy and repository hygiene. Dispatch one independent reviewer for the
   user's Part N, resolve Critical/Important findings and record evidence.
   Run `git diff --check`, then make exactly one local research commit.

Shared interfaces: contract ↔ validator ↔ adapter must agree on common fields,
time precision, byte scope and receipt types; refresh ↔ existing gate must
preserve full-ledger-before-target selection and cutoff-specific certification.
No intermediate commits; the user's exactly-one-commit requirement takes
precedence over workflow defaults. No redundant design approval is required
for implementing the supplied detailed specification under session authority.

Review focus: no inference from URL quarter, archive member time, local mtime,
transaction date or current metadata time; no derived ID relabeling; no later
correction/cancellation leaking backward; no row disappearance inference; no
license propagation from catalogs to requested confidential products; no
personal payloads in committed aggregates; no synthetic real evidence; no
threshold relaxation and no positive cohort from incomplete provenance.
