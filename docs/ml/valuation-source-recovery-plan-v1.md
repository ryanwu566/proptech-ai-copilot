# ML source recovery execution plan v1

Goal: recover bounded official inputs and re-evaluate B1–B6 without training.
Specification: the user-supplied ML SOURCE RECOVERY & COHORT PROOF request;
existing ML-A, foundation, source, identity, geography and dataset contracts apply.
Starting SHA: `b735c52f698de0355539cdcff170e3ccde5f8d7b`.

Architecture: extend `scripts/ml/` with recovery validation and an evidence-first
raw package audit. Reuse foundation semantics, identity and as-of selection;
keep raw packages and row staging under ignored `artifacts/ml/plvr-source-recovery/`.
Use Python standard library plus the existing official HTTPS transport.

- [x] Verify required clean branch/SHA and read prior contracts/evidence.
- [x] Inspect every recorded URL once before acquisition; freeze preflight evidence.
- [x] Validate selected exact archives and record hashes without replacing expected hashes.
- [x] Test checksum, scope, missing/schema/changed-source and one-attempt behavior first;
  implement `scripts/ml/source_recovery.py` and focused tests.
- [x] Inspect main/build/land/park schemas. Test malformed CSV, detail multiplicity,
  missing details and contradictions before implementing `scripts/ml/plvr_raw_parser.py`.
- [x] Build bounded private staging for Taipei/New Taipei only from exact bytes;
  measure raw semantic profiles and a conserving fail-closed funnel. Full rights,
  dwelling, namespace and historical availability stay unknown unless evidenced.
- [x] Perform two independent offline audit/staging builds. Distinguish this proof
  from a nonempty eligible dataset/split build; never manufacture empty-data readiness.
- [x] Write aggregate evidence, recovery manifest, human report and a new readiness
  follow-up; preserve historical reports and source ledger unchanged.
- [x] Run focused and foundation tests, manifest/count/determinism/privacy checks,
  fresh independent review, and fix Critical/Important issues.
- [x] Prepare the reviewed delivery for exactly one bounded commit with the requested message; no push/merge/deploy.

Review focus: filename reuse is not identity; observation time is not historical
publication; absence of rights evidence excludes; detail joins cannot multiply
main rows; mismatched/repeated detail keys cannot establish parking absence;
no raw IDs or addresses in tracked evidence; deterministic hashes cover all outputs.

No production edits, database mutation, object-store upload, ML dependencies,
model training or model artifacts. All writes remain inside this workspace.
