# Stage 3 valuation implementation plan

> **For agentic workers:** Execute inline with superpowers:executing-plans. The user explicitly authorizes autonomous implementation and local commits; no routine approval gates.

**Goal:** A bounded offline-trained CPU valuation capability with independently admitted data, honest evaluation, reproducible artifacts, and a separate FastAPI endpoint.

**Architecture:** Keep strict ML-A/B historical and no-parking/whole-dwelling contracts unchanged. Introduce an explicitly different archive-snapshot gross-transfer contract. Shared typed input and feature transformation drive offline training and inference. Stream immutable staging to compact arrays; select models using validation only; evaluate the frozen winner once on the final holdout. Persist a native tree model, JSON preprocessing, reports, hashes, and provenance outside Git. Inference loads only trusted local artifacts and limits concurrency and thread count.

**Tech stack:** Python 3.12 in project-local environment, NumPy/SciPy/scikit-learn baselines, LightGBM CPU trees, FastAPI/Pydantic. No system Python installation or changes.

**Spec:** User's Stage 3 request; `docs/operations/plvr-local-history-staging.md` describes the supplied canonical artifact.

## Global constraints

- Preserve `frontend_next/next-env.d.ts` byte-for-byte and exclude it from all commits.
- No push, external PLVR download, production table writes, source-data changes, optional providers, or privileged operations.
- Never infer historical publication times from releases; never infer parking absence or complete dwelling rights.
- At most two CPU threads; nice 15 for long jobs; stream rows, checkpoint phases, keep >2 GiB available RAM and >8 GiB free disk.
- Explicit unavailable/unsupported outcomes; no calibrated confidence probabilities or property-rights/no-parking value claims.
- Run focused tests and broader relevant ML/valuation/API/Stage 1/2 regressions, not the entire repository suite.

## Review focus

- Newer source-release membership cannot enter fitting splits; archive evaluation must disclose unavailable historical-publication and cancellation evidence.
- Unknown categories, unsupported dates/structures, sparse support, malformed/nonfinite inputs must never yield an unqualified estimate.
- Model files, contract, preprocessing, dataset provenance and runtime version must agree and pass hashes before load.
- Concurrent requests, corrupt/missing artifacts and missing ML dependencies must fail safely without affecting health or deterministic valuation.
- Related-party serving reference 38652 / serial RPWNMLNKNHLGFBF78EA must have zero admitted or model rows.

### Task 1: Dataset admission and feature/split contracts

Files: reviewed historical staging module/CLI/tests; `services/valuation_ml/{admission,contract}.py`; `tests/test_stage3_ml_admission.py`; admission JSON and gate rationale.

- [x] Review preparation commit ancestry/diff; integrate only reusable verifier/schema/provenance code and tests.
- [x] Write and run failing admission/feature/split tests, implement explicit contract without changing strict ML gates, rerun.
- [x] Independently verify all artifact checksums, fingerprint, every record, SQLite lineage, exclusions and canonical identity; derive continuous window from release coverage.
- [x] Commit reviewed contract and admission implementation/evidence.

### Task 2: Offline training, evaluation and artifacts

Files: `scripts/ml/train_stage3.py`; `services/valuation_ml/{training,artifact}.py`; `tests/test_stage3_ml_training.py`; evaluation/model card/manifests.

- [x] Test training-side encoders, temporal membership, support policy, metric arithmetic, artifact reload and tamper rejection before implementation.
- [x] Stream and checkpoint compact arrays and identity/address/road group audit. Train deterministic medians, regularized linear baseline, and at most two rational boosting candidates with bounded resources.
- [x] Freeze model selection on validation; score untouched temporal holdout plus unseen address/road slices, drift and category/geography support. Record all rows/windows and failure modes.
- [x] Export and verify native model + exact feature contract + preprocessing + versioned manifest and hashes. Commit bounded reports/code only.

### Task 3: Bounded FastAPI and acceptance

Files: `backend/api/routes_valuation_ml.py`; router registration; `services/valuation_ml/inference.py`; `tests/test_stage3_ml_api.py`; API/runbook/limitations/acceptance JSON.

- [x] Write and run failing API tests for unavailable, strict invalid input, deterministic estimates, provenance, unsupported/sparse inputs, integrity and concurrency boundaries.
- [x] Implement one-at-a-time lazy inference with no provider or training calls and explicit observational valuation semantics.
- [x] Verify real artifact with loopback-only standalone API process; keep port 8080 healthy. Do not require live API replacement/restart merely to expose ML.
- [x] Run broader relevant regressions, obtain final code review, fix substantive defects with regression coverage, produce truthful acceptance and local commits.

## Execution ledger

- Initial HEAD ff3b1df; branch `ml/stage3-valuation-20261029`. Preparation 0ed5538 is its direct child; integrate four reusable files, not unrelated generated reports.
- Initial frontend file SHA256: 0f70629890b72a0a82e91972cc032c04b658b26c265373cb711cf576bfbf8fcc.
- Initial live loopback 8080 health ready. Host available RAM ~8.4 GiB, swap already full, disk free ~60 GiB.
- Ruling: system Python 3.14 lacks ensurepip; install a local managed Python 3.12 via uv, no sudo/system changes.
- Ruling: v1 predicts reported gross transfer NTD/ping, not parking-exclusive/whole-dwelling residential value. Strict earlier gates remain unchanged. Snapshot temporal evaluation cannot claim historical publication availability.
- Task 1 complete: a4d12a1. Full independent verification PASS, 1,321,059 canonical rows; 716,413 reduced-cohort rows. Train 633,457 (actual 2017-01-01–2024-05-31), validation 39,552 (actual 2024-07-01–2025-06-02), holdout 43,404 (2025-07-01–2026-06-30). Source-release filtering accounts for fitting-boundary gaps; dates are not silently filled.
- Ruling: broader tests reproduced a pre-existing migration-registry mismatch from Stage 1. 7b98021 freezes separately operated 023 as `legacy_operator`, never automatically replayed. Registry/provisioning tests 70 PASS; broader relevant tests 447 PASS after repair. No SQL executed.
- Initial training from frozen b8cb57e: two boosting capacities, final 63 leaves / 500 rounds. Validation MAE 48,405 vs market median 76,191 and ridge 64,815. Holdout MAE 47,731, RMSE 73,722, median AE 32,038 NTD/ping; MAPE 14.856%. Peak RSS 632,938,496 bytes, nice 15, two threads, 159 seconds. No holdout-based tuning.
- Independent review identified three Important defects: stale checkpoint/provenance binding, incomplete artifact metadata validation, and nonfinite validation-error serialization. All reproduced in new regressions and repaired in d6299ce; 74 Stage 3 tests PASS. Invalid DTO no-store header was also repaired. Native checkpoints are atomically certified, invalid work quarantined for safe refitting, and model publication is atomic. Exact input/authorization/provenance/support metadata must agree before native load.
- A second run from frozen corrected sources repeats the same predeclared comparison to validate the repaired pipeline and restart behavior. No new candidate or holdout-based parameter selection is allowed. First-run artifact remains immutable and retains its original code provenance; final acceptance will name the corrected run's artifact.
- Final review: independent reviewer cleared all three Important findings and the no-store issue in d6299ce. No remaining substantive code blocker. Remaining historical PIT and whole-property claims are explicitly outside authorization.
- Corrected frozen run: 152.21 seconds, peak RSS 639,385,600 bytes, nice 15/two threads; exact same arrays, native model hash and evaluation as initial run. Native version `plvr-gross-v1-bccf2ec1bc-dcc6587c76b3-6493b5f7`. Manifest SHA256 `54eba6a04069b0f8d569c2fe62bbe1ca70771b5594cb220e908e9f7e3524fac4`.
- Resume verification: 21.33 seconds; certified candidates/final fit and immutable published artifact reused. No refit; no holdout-based retuning.
- Final tests: 74 focused Stage 3, 517 ML regressions, 462 broader valuation/API/Stage 1/2/migration tests passed. Counts overlap. Each run has one existing Starlette/httpx deprecation warning; entire repository suite was not run.
- Live acceptance: loopback-only 8081 companion PID 4081522; 25 identical requests, p50 2.21 ms / p95 3.26 ms. Sparse/date/nonfinite abstentions verified; concurrency burst 16 HTTP200 / 2 HTTP429. Existing 8080 health ready and official comparable endpoint available/actionable; no restart. Training-time health p95 102 ms; available RAM stayed above 8.16 GiB in sampled probes.
- Serving-support analysis: 42,853/43,404 holdout rows supported (98.73%); 551 abstained. Supported-only MAPE 14.75%, MAE 47,899 NTD/ping. All-holdout results remain primary and include rejected cells.
- Final status: Stage 3 PARTIAL overall, PASS for complete bounded observational engineering/inference. Missing publication/cancellation, parking-basis and whole-dwelling-rights evidence blocks broader claims. No operator action required for local capability; companion remains running. No push, privileged work, source/serving-table mutation or frontend modification.
- Final independent acceptance review: PASS, no remaining Critical/Important findings. Reviewer verified published/current-source hashes, support counts, metrics, live model status and both health endpoints, tests and frontend preservation. One factual median-baseline wording correction applied. Boot/public deployment is not claimed; unresolved PIT/whole-dwelling scope remains unapproved.

Follow-up closure: the user explicitly permits COMPLETE for a rigorously bounded v1. The dedicated bounded-closure plan and audit/tests/API/review now close Stage 3 for reported-transfer inference. The earlier PARTIAL verdict is historical; stronger PIT/whole-property features remain excluded rather than current v1 blockers. Model, cohort, splits and original metrics are unchanged; no retraining occurred.
