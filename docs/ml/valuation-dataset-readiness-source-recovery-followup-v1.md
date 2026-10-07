# ML valuation readiness follow-up: source recovery v1

Decision: **BLOCKED**. ML-B may not begin. Approved cohort scope: **none**.

This decision follows ML-A and the dataset foundation without replacing either historical report. Starting SHA is `b735c52f698de0355539cdcff170e3ccde5f8d7b`, branch `research/ml-valuation-source-recovery-v1`.

Two exact quarterly sources (112S3, 115S2) now match prior hashes and restore locally. All 17 recorded sources were probed; fifteen exact objects remain un-restored. The bounded Taipei/New Taipei audit preserves 37,669 main and 159,995 detail records. Structural filters leave 13,028 residential supported-type rows, all excluded for missing full-rights evidence. The unchanged foundation lineage-first audit excludes every row for unverified lineage. Final candidate count: **0**.

No historical publication/availability instant is authenticated. Current retrieval bounds do not prove earlier availability. Full rights, one dwelling, registered-area rights basis and revision/namespace/cancellation ordering remain unproved. No approved temporal/geographic/type coverage, split, calibration cohort or point-in-time baseline exists. Age remains DEFERRED.

Two independent clean offline builds match all ten output files, including exclusion and staging ledgers. Empty membership/target/feature/split hashes prove deterministic emptiness only. This is local source/staging proof, not nonempty dataset or durable object-store readiness.

Minimum repair sequence:

1. Authenticate whole-dwelling rights/area evidence and historical source availability, identifier namespace and ordered revisions/cancellations. Do not fabricate positive context from row counts or blanks.
2. Recover only the necessary contiguous sources inside the existing ledger and rerun a conserving nonempty eligible cohort. Do not force four chronological blocks or substitute current sources for earlier vintages.
3. Prove separate chronological TRAIN / VALIDATION / CALIBRATION / TEST, point-in-time baselines and independent immutable restore.
4. Regenerate nonempty membership/targets/features/splits twice with matching model-affecting hashes, then make a new readiness decision before any ML-B work.

See the [full recovery report](valuation-source-recovery-v1.md), [aggregate evidence](valuation-source-recovery-evidence-v1.json), [source manifest](valuation-source-recovery-manifest-v1.json) and [proof manifest](valuation-source-recovery-proof-build-manifest-v1.json). Prior contracts and production systems remain unchanged. No model trained; no push, merge, deployment or production upload.
