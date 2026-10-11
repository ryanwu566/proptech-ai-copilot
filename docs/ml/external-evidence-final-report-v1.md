# ML-0 final evidence report

**Target A BLOCKED; Target B BLOCKED; ML-B MAY NOT BEGIN.**

This is acquisition preparation and offline validation. Authenticated historical
proofs, real receipts, PIT rows and the approved training cohort remain zero.
No request was sent and no model was trained.

| # | Requested result | Final observation |
| --- | --- | --- |
| 1 | Starting SHA | `c9ab5f61a45f7f704326af66cb0bea02740b9927` |
| 2 | Final SHA | The commit containing this report; exact SHA supplied in the delivery response. Embedding its own SHA would change that SHA. |
| 3 | Changed-file count | 22 in the single research commit, including three CI workflow dependency fixes and the existing workflow contract test. Four operation-document files already introduced by upstream commits are excluded from this count. |
| 4 | Organizations | MOI 地政司/PLVR; MODA/data.gov.tw; NLSC; Taipei 地政局 and 建築管理工程處; New Taipei 地政局/land offices and 工務局. |
| 5 | Official sources | 19 selected URLs; five captured and rehashed metadata responses, 14 TLS failures. Browser observations and indexed leads are explicitly distinguished. |
| 6 | New authenticated historical proofs | 0. |
| 7 | Publication evidence | BLOCKED; the two rehashed ZIPs remain CURRENT_ONLY without historical byte/time authority. |
| 8 | Namespace authority | UNPROVEN; real namespace-valid count 0; IDs remain DERIVED_RESEARCH_TRANSACTION_ID. |
| 9 | Revision lineage | UNPROVEN; no authoritative version chain or complete stream recovered. |
| 10 | Cancellation lineage | UNPROVEN; no authoritative tombstones/complete cutoff stream recovered. |
| 11 | Replacement lineage | UNPROVEN; no authoritative changed-key alias/edge map recovered; cross-key replacements remain quarantined. |
| 12 | Rights/unit mapping | UNPROVEN; registered dwelling count, portion roles and required/transferred interests lack authoritative PLVR linkage. 1,440 candidates have multiple building portions; 827 have one portion, which alone does not prove a dwelling. |
| 13 | Request packages | Seven complete Chinese drafts R1–R7, with a shared non-personal/time/hash/license annex; none sent. |
| 14 | URLs/channels | Formal MOI information application/PLVR supply routing; Taipei/New Taipei land-office extract requests; NLSC map-store/service applications; municipal building-request/referral channels. Unknown intake/entitlement is marked rather than invented. |
| 15 | Receipt contracts | HistoricalPublicationReceipt; TransactionNamespaceAuthority; TransactionLineageReceipt; RightsUnitMappingReceipt, closed JSON Schema plus runtime byte/scope/time/role checks. |
| 16 | Ingestion dry-run | Real empty bundle accepted 0/rejected 0 receipts; 37,669 raw, 37,668 structurally valid, 2,267 target/parking candidates; all historical/namespace/lineage/PIT/approval stages 0. Synthetic cases exist only in tests. |
| 17 | PIT-valid count | 0. |
| 18 | Approved cohort | 0. |
| 19 | Usable months | PIT 0; contiguous PIT 0. Inherited candidate-only profile: 24 sparse months, longest contiguous run 9. |
| 20 | Frozen admission | >=840 PIT rows; >=21 usable/contiguous months; >=20 rows per city/month; both cities; >=12/3/3/3 train/validation/calibration/test months; inherited district/type block minima; frozen targets, complete publication/dependencies/lineage at every freeze, privacy and independent determinism. |
| 21 | Determinism | Two independent raw/archive/schema/detail rebuilds byte-identical; SHA-256 `4b5adfa626299ce1b226241ab1d3f830a5aebd73c9c28ece1a207544ef7f0629`. Fresh source/receipt gate verification also matches; byte-only verification cannot approve a cohort. |
| 22 | Privacy | PASS for aggregate artifacts and 11 targeted privacy tests. No new personal records or raw transaction/page bodies committed; supplement licenses remain subject to explicit review. |
| 23 | All ML tests | 425 passed, 3,273 deselected; focused receipt/regression tests 51 passed. |
| 24 | Full Python | CI dependency follow-up on clean Python 3.12: 3666 passed, 0 failed, 32 skipped. Prior exact-parent classification and serial reruns retained below. |
| 25 | Independent review | Original ML research review: 0 Critical, 3 Important, 0 Minor; all 3 Important corrected and regression-verified by author; no second review of that ML implementation claimed. Separate CI dependency-fix review: 0 Critical, 0 Important, 0 Minor. |
| 26 | External blockers | E1 exact historical bytes/time; E2 stable identity semantics; E3 complete revision/cancellation/replacement events; E4 release continuity; E5 non-personal registered-object/right linkage and explicit reuse. |
| 27 | Exact next owner action | Confirm MOI formal intake and fill statutory applicant details outside Git; submit R1/R2 with the shared annex, obtain case numbers/written proof and terms. Submit R3/R4 for lawful redacted linkage, using R5–R7 for documented supplements/referral. Retain originals privately, hash/time/review them, then rerun two offline refreshes and verify --revalidate. |
| 28 | Safe for research PR? | Local research validation passes. Merge readiness is withheld until all required fresh GitHub checks pass after the CI dependency-contract fix. Test closure does not authorize ML-B. |
| 29 | May ML-B begin? | **NO. ML-B MAY NOT BEGIN.** |

PR #180 CI follow-up: all three failing full-suite GitHub jobs on
`1c09bd81d1295c72d9efb75a46c3a3a4654611a0` reported
`ModuleNotFoundError: No module named 'jsonschema'` at the import of
`Draft202012Validator` and `FormatChecker` in `scripts/ml/external_evidence.py`.
Each actual job log records 49 failed, 3616 passed and 33 skipped. This is a CI
dependency-contract defect; it is not an algorithm or authoritative Data Gate
failure. In an isolated Python 3.12 environment, the old backend-plus-pytest
installation reproduced 49 failed and 2 passed in the focused suite.

The existing canonical `requirements-dev.txt` declares `jsonschema>=4.26,<5`
and `pytest>=9.0.3,<10`, and includes root application requirements covering
every backend requirement. All 10 workflows were audited, including indirect
release-gate invocations. Exactly three full-suite jobs now install that manifest:
`production-release-ops.yml/quality`, `release-quality.yml/quality`, and
`security-performance.yml/gate`. The duplicated backend installation in release
quality was removed. Targeted database/migration jobs and runtime-only jobs keep
their existing installation paths. The existing workflow test now checks the
canonical installation contract. Production requirements, images, admission
gates, receipt validation, readiness assertions and timeouts are unchanged.

The clean-environment canonical install resolves Python 3.12.13, pytest 9.1.1
and jsonschema 4.26.0; `pip check` and the receipt-validator import pass, and
the focused suite passes all 51 tests. All ML: 425 passed; workflow/deployment/
security contracts: 17 passed; privacy: 11 passed. Determinism revalidation
passes with approved cohort zero. Full Python: 3666 passed,
0 failed and 32 skipped. Dependency and repository hygiene
checks pass. A separate read-only CI fix review found
0 Critical, 0 Important and 0 Minor issues. Follow-up suite commands, counts,
log/XML hashes and the complete workflow audit are recorded in
[validation](external-evidence-validation-v1.json) under
`ci_dependency_contract_followup`. Fresh required GitHub checks on the amended
PR head must pass before merge readiness can be assessed. CI success cannot
authorize ML-B: PIT-valid rows and the approved cohort remain zero.

The first clean Python 3.12 full run had 3663 passed, 3 failed and 32 skipped.
Those three failures were introduced by the private verifier's encoding
configuration: UTF-8 child output was decoded using Windows cp950 by subprocess
text readers. Every exact case failed on both the branch and clean
`ef1c49c55a58eb0ab63beefe0cd2ddc1f2f9717b` parent with the mismatch, then
passed on both with aligned `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`
(12 exact executions). The corresponding test and CLI Git blobs are identical.
Each is classified **ENVIRONMENTAL**:

- `tests/test_gsmma_geological_sensitivity_artifact.py::test_operator_cli_builds_local_outputs_without_uploading`
- `tests/test_market_coverage_registry.py::test_coverage_audit_script_outputs_safe_lines`
- `tests/test_market_coverage_rollout_workflow.py::test_market_coverage_county_helper_outputs_tracked_counties_safely`

Only the private verification harness was corrected. No product/test files or
GitHub workflow encoding settings were changed to address these failures. The
final full suite uses aligned UTF-8, matching CI's UTF-8 locale behavior. Exact
commands and log/XML hashes are retained under `windows_encoding_closure` in the
CI follow-up validation record.

The prior local suite-closure history is retained below; it predates this
CI follow-up and used the previous local environment.

Full-suite closure was performed on `229348a77a41d6bde899976fb4a8ca557b49d659` after the metadata-binding
fix, using a clean detached `ef1c49c55a58eb0ab63beefe0cd2ddc1f2f9717b` parent worktree. The first post-fix full
run had 3664 passed, 2 failed and 32 skipped.
The final full run, after serial ML/receipt/privacy/determinism verification, had
**3666 passed, 0 failed and 32 skipped**.
Remaining final failures: none.

Seven exact current/historical failure cases were tested in three alternating
branch/parent rounds (42 executions), without timeout or assertion changes.
Relevant production/test/fixture Git blobs are identical and the parent remained
clean. Exact commands, log/XML hashes, per-case durations and final check records
are in [validation](external-evidence-validation-v1.json), under `full_suite_closure`.

| Exact case | Classification | Branch reruns | Clean parent reruns |
| --- | --- | --- | --- |
| `tests/test_earth_engine_worker_pool.py::test_crashed_worker_is_joined_and_replaced_once_without_request_replay` | REPRODUCIBLE_FLAKE | 3 pass / 0 fail | 2 pass / 1 fail |
| `tests/test_earth_engine_worker_pool.py::test_timeout_kills_worker_before_one_bounded_replacement` | NON_REPRODUCING_FLAKE | 3 pass / 0 fail | 3 pass / 0 fail |
| `tests/test_earth_engine_worker_pool.py::test_failed_replacement_cleans_other_worker_and_all_pipes` | NON_REPRODUCING_FLAKE | 3 pass / 0 fail | 3 pass / 0 fail |
| `tests/test_earth_engine_worker_pool.py::test_two_active_two_queued_and_fifth_fails_closed` | NON_REPRODUCING_FLAKE | 3 pass / 0 fail | 3 pass / 0 fail |
| `tests/test_plvr_provider_update.py::test_failed_acceptance_cannot_write_or_accept_any_rows[dates2]` | NON_REPRODUCING_FLAKE | 3 pass / 0 fail | 3 pass / 0 fail |
| `tests/test_earth_engine_worker_pool.py::test_result_with_wrong_request_id_or_generation_is_rejected` | NON_REPRODUCING_FLAKE | 3 pass / 0 fail | 3 pass / 0 fail |
| `tests/test_earth_engine_worker_pool.py::test_manager_captures_project_once_and_never_accepts_per_request_project` | NON_REPRODUCING_FLAKE | 3 pass / 0 fail | 3 pass / 0 fail |

NON_REPRODUCING_FLAKE means no recurrence in the bounded exact reruns; it does
not guarantee absence of future flakiness. The crash/replacement case has both
pass and fail observations on the exact clean parent, establishing a pre-existing
REPRODUCIBLE_FLAKE. No branch regression was found. No causal environmental
claim is made from timing anomalies alone.

The PLVR case retained its **30-second subprocess timeout**. All six paired
runs passed; whole-test durations were [0.78, 1.084, 1.2] seconds on the
branch and [1.328, 1.07, 0.971] on the parent. These timings include
setup/teardown and do not show that the subprocess threshold is unrealistic.
Product behavior, worker lifecycle assertions and timeout values remain unchanged.
The 32 skips still require explicitly disposable PostgreSQL integration targets;
no production database was used.

ML-0 merge readiness now also requires green fresh GitHub checks for PR #180.
No merge or production acceptance is authorized. The authoritative Data Gate still blocks Target A/B;
PIT-valid and approved cohort counts remain **0**, so **ML-B MAY NOT BEGIN**.

The minimum admission criteria are feasibility safeguards, not statistical power
or accuracy claims. All chronology uses full visible history before semantic
selection. Hashes and review flags do not authenticate a government institution;
an accountable steward must inspect original evidence and lawful scope.

Supporting artifacts: [acquisition findings](external-evidence-acquisition-v1.md),
[E1–E5 map](external-acquisition-map-v1.json),
[source registry](external-official-sources-v1.json),
[capture manifest](external-metadata-capture-manifest-v1.json),
[Chinese drafts](external-official-request-packages-v1.md),
[receipt schema](contracts/external-evidence-v1.schema.json),
[frozen admission](contracts/ml-b-admission-v2.json),
[validation](external-evidence-validation-v1.json), and
[independent review](external-evidence-independent-review-v1.md).

Exactly one research commit is the delivery boundary. The CI follow-up authorizes
amending and updating PR #180 using an explicit `--force-with-lease`; no merge,
deployment, training, prediction intervals, production valuation or ML UI change.

Ancestry note: the supplied starting SHA is retained above. The branch reflog
records a rebase onto origin/main at 2026-10-11 13:54:26 +08:00; the actual parent
of this research commit is `ef1c49c55a58eb0ab63beefe0cd2ddc1f2f9717b`.
Two upstream commits after the supplied SHA are preserved. Thus start..final
contains those two upstream commits plus the single new research commit, rather
than one total commit. This lane creates only one commit and changes 22 files
relative to its parent.
