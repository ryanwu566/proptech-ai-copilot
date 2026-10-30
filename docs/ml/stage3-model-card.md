# PLVR gross-transfer v1 model card

**Status: COMPLETE for bounded local observational v1; full-property valuation and historical
point-in-time performance are excluded from this contract.** The exact active version, paths,
hashes and generated timestamp are in
`../../reports/professor-stage3-ml/model-artifact-manifest.json` and acceptance JSON.

The model predicts reported gross transfer consideration in **NTD per registered
transferred building ping**, conditional on subject date, location, registered area
and structural facts. The corresponding total multiplies this amount by the
supplied registered area. Parking consideration/area and ownership rights are not
separated. Neither a complete dwelling, private interior area, parking-free value
nor arm's-length market value is established. Output is always non-actionable.

Intended use is local analysis of ordinary-looking disclosed transfers within the
admitted scope, alongside the existing comparable estimator and its evidence.
Do not use this model alone for lending, collateral, taxation, legal rights,
purchase pricing, or future-price forecasting. Its support diagnostics are not
confidence probabilities or calibrated intervals.

The immutable canonical dataset has 1,321,059 independently verified rows from 40
consecutive archives 105S4–115S3. Fingerprint:
`bccf2ec1bc19110b9f55e35c3eaec284c2ad57a97318acea7381c5be5002ccee`.
The conservative release-supported date window is 2017-01-01–2026-06-30. Sparse
pre-2016 observations and the incomplete latest-quarter tail are excluded.

The reduced cohort contains **716,413 rows**, restricted to explicit reported
`住家用`, actual districts, three specified apartment types, 5–200 registered ping,
and bounded consistent physical facts. All note-tainted/ambiguous/revised identities
are excluded upstream. The known related-party serial corresponding to legacy row
38652 has one raw occurrence and zero clean/admitted rows. No demo or future data,
source archive modification or serving-table mutation is involved.

| Block | Planned transaction dates | Actual dates after source cap | Rows | Latest source release |
| --- | --- | --- | ---: | --- |
| Train | 2017-01-01–2024-06-30 | 2017-01-01–2024-05-31 | 633,457 | 113S2 |
| Validation | 2024-07-01–2025-06-30 | 2024-07-01–2025-06-02 | 39,552 | 114S2 |
| Final holdout | 2025-07-01–2026-06-30 | Same | 43,404 | 115S3 |

The validation-selected configuration is refit on **673,009 train + validation
rows** before scoring holdout. No holdout target trains parameters, preprocessing,
baseline medians or model selection. Exact historical publication times and full
cancellation evidence are absent: source-quarter caps are membership filters, not
proof of what was publicly known at a past freeze. The corrected rerun validates
integrity/reproducibility of this same experiment; it is not another independent
holdout experiment.

Feature contract `plvr-gross-transfer-features-v1` uses month index, log registered
area, floor, total floors, age at the subject date, floor ratio, city, city/district
pair and building type. Missing physical values remain missing. Categorical
vocabularies come from the existing registry/allowlist independently of targets.
No road, address, coordinates, community identity, parking, rights, official unit
price or target aggregate is a feature.

The selected model is deterministic CPU **LightGBM log-target L1 regression, 63
leaves, 500 boosting rounds**, learning rate 0.06, minimum leaf support 100,
maximum bin count 127, seed 20261029. The only alternative capacity was 31 leaves.
The comparison also included global median, recent district/type median and
regularized log-linear ridge. There was no neural model or grid search.

Holdout MAE is **47,731 NTD/ping**, RMSE **73,722**, median absolute error **32,038**,
MAPE **14.86%**, median APE **10.56%**, and WAPE **13.37%**. The recent district/type
median baseline MAE is **79,669** (40.09% relative MAE reduction). Full slice metrics,
tails and serving-support coverage are in the evaluation report and JSON evidence.

Material failures include 76.06% MAPE for actual prices below 100,000 NTD/ping,
46.46% MAPE in 桃園市大園區, 20.60% unseen-road MAPE, and expensive upper-tail absolute
errors. The p95 absolute percentage error is 41.33%; p99 is 80.85%. These are
observed errors, not estimated individual uncertainty. Address/road-disjoint
temporal diagnostics do not prove building/community independence.

Inference abstains for unsupported input/date or inadequate fitting cell support
(50 fitting / 20 recent rows minimum); 50–199 fitting rows are flagged. Missing
physical facts, structural percentiles, extrapolation and weak geographic
holdout performance are disclosed. The tree time response is constant beyond its
fitting dates. Geographic/temporal drift and unobserved property quality remain.

Artifacts use native model text plus JSON preprocessing/contract/metadata, verified
hashes and exact package versions. Model and dataset binaries remain outside Git.
Training uses two CPU threads at nice 15; inference uses one row/thread and one
concurrent slot. The Stage 2 API remains independently healthy. See the
[inference runbook](../operations/stage3-ml-inference-runbook.md) and
[failure-mode documentation](stage3-limitations.md).

The closure audit rechecked artifact bytes and all canonical observations, with
identical admitted identities/splits and no feature change. Parking count is
descriptive only: its price/area basis is unknown. Rights remain unknown, and
undisclosed partial interests or unreported cancellations may persist. No active
legal register or complete dwelling is claimed. The API permits only
`requested_value_basis=reported_transfer`, rejects whole/share/parking-exclusive
claims, and returns `plvr-bounded-transfer-evidence-v1` scope. The model artifact
and prior metrics are retained without retraining. See
[evidence closure](stage3-bounded-evidence-closure.md) for the actual proof boundary.
