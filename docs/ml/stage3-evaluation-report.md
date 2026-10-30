# Stage 3 evaluation report

Verdict: **COMPLETE for bounded observational gross-transfer v1; full-property / historical PIT valuation excluded.**
The final holdout was not used for selecting parameters. A corrected pipeline run reproduced identical arrays, native model bytes and metrics; it is the same experiment, not an independent holdout replication.

Active model: `plvr-gross-v1-bccf2ec1bc-dcc6587c76b3-6493b5f7`. Artifact `/home/andy/proptech-model-artifacts/plvr-gross-v1-bccf2ec1bc-dcc6587c76b3-6493b5f7`; manifest SHA256 `54eba6a04069b0f8d569c2fe62bbe1ca70771b5594cb220e908e9f7e3524fac4`.

## Target, admission and dates

Target is gross reported consideration / registered transferred ping. Parking and whole-dwelling rights remain unverified and are neither features nor adjustments. Predictions are non-actionable observational estimates.
The 40 consecutive release archives support a conservative 2017-01-01–2026-06-30 window; they do not prove past publication dates, exhaustive cancellation history or population completeness. All 1,321,059 clean rows were independently verified; the narrowed admitted cohort contains 716,413.
Train: 633,457 rows, actual 2017-01-01–2024-05-31 (planned through 2024-06-30, source cap 113S2). Validation: 39,552 rows, actual 2024-07-01–2025-06-02 (planned through 2025-06-30, source cap 114S2). Final holdout: 43,404 rows, 2025-07-01–2026-06-30 (archive through 115S3). The selected configuration refits 673,009 train+validation rows. Source-cap boundary gaps are deliberate; no dates are filled.

## Validation selection

| Model | Validation MAE (NTD/ping) | RMSE | MAPE |
| --- | ---: | ---: | ---: |
| global_median | 154,209 | 232,686 | 39.23% |
| lightgbm_log_l1_leaves31 | 49,065 | 73,880 | 15.09% |
| lightgbm_log_l1_leaves63 | 48,405 | 72,856 | 14.88% |
| recent_district_type_median | 76,191 | 106,580 | 26.52% |
| ridge_log | 64,815 | 92,807 | 19.75% |

Selected **lightgbm_log_l1_leaves63**, 500 rounds. Only two predefined capacities were tried. Both use log-target L1 boosting, no neural model/grid. Linear imputation and scaling fit training rows only; the recent district/type median baseline uses only the latest twelve fitting months. No target aggregate is a model feature.

## Frozen final holdout

| Metric | Selected model | Recent district/type median |
| --- | ---: | ---: |
| MAE NTD/ping | 47,731.31 | 79,668.87 |
| RMSE NTD/ping | 73,722.12 | 115,440.69 |
| Median absolute error NTD/ping | 32,038.09 | 58,133.75 |
| MAPE % | 14.86 | 29.51 |
| Median APE % | 10.56 | 17.87 |
| WAPE % | 13.37 | 22.31 |
| sMAPE % | 13.88 | 24.01 |

Relative MAE reduction versus the market median: **40.09%**. Signed prediction bias: -2,869 NTD/ping. These figures describe all admitted holdout rows, including rows the serving support policy rejects.

Serving policy supports **42,853/43,404 (98.73%)** and abstains on 551. On supported rows, MAE is 47,899, RMSE 73,963, median AE 32,097 NTD/ping; MAPE 14.75%. Thresholds were fixed before holdout: 50 fitting and 20 recent fitting rows per geography/type cell.

## Error distribution

| Quantile | Absolute error NTD/ping | Absolute percentage error |
| --- | ---: | ---: |
| p50 | 32,038 | 10.56% |
| p75 | 60,726 | 18.85% |
| p90 | 104,451 | 30.44% |
| p95 | 145,554 | 41.33% |
| p99 | 261,922 | 80.85% |

Maximum absolute error: 1,329,701 NTD/ping. These tails rule out treating the mean score as an individual accuracy guarantee. No calibrated interval or confidence probability is supplied.

## Geography and building type

| City/county (at least 50 holdout rows) | Rows | MAE NTD/ping | MAPE |
| --- | ---: | ---: | ---: |
| 南投縣 | 285 | 28,086 | 14.76% |
| 台中市 | 7,626 | 40,362 | 14.33% |
| 台北市 | 3,042 | 122,881 | 13.97% |
| 台南市 | 3,142 | 31,946 | 14.27% |
| 台東縣 | 136 | 36,667 | 29.32% |
| 嘉義縣 | 212 | 62,606 | 21.33% |
| 基隆市 | 1,267 | 32,337 | 17.73% |
| 宜蘭縣 | 781 | 34,155 | 15.46% |
| 屏東縣 | 1,136 | 26,174 | 16.07% |
| 彰化縣 | 691 | 28,030 | 13.82% |
| 新北市 | 8,659 | 61,608 | 14.64% |
| 新竹縣 | 1,126 | 52,548 | 16.10% |
| 桃園市 | 7,059 | 41,110 | 15.87% |
| 花蓮縣 | 317 | 31,346 | 20.69% |
| 苗栗縣 | 657 | 35,280 | 18.28% |
| 雲林縣 | 429 | 24,057 | 14.03% |
| 高雄市 | 6,746 | 32,314 | 13.40% |

| Building type | Rows | MAE NTD/ping | MAPE |
| --- | ---: | ---: | ---: |
| 住宅大樓(11層含以上有電梯) | 27,269 | 47,975 | 12.53% |
| 公寓(5樓含以下無電梯) | 4,768 | 54,134 | 23.06% |
| 華廈(10層含以下有電梯) | 11,367 | 44,460 | 17.00% |

The weakest supported district with at least 50 holdout rows is **桃園市大園區**, 470 rows, 46.46% MAPE; the API flags it. Other elevated slices include 新北市新店區 (619, 25.8%) and several sparse districts. Low-count counties/districts are not granted reliable error claims; complete reported slices and density bins are in `evaluation.json`.

## Entity leakage and support

Canonical identity and strong-fact ambiguity/revision/note checks are global admission invariants. Transaction identities cannot cross splits. Address and road are not model features. City/geographic IDs use fixed registry categories; there is no holdout/future target encoding. Shared locations across time are intentional; performance on unfamiliar local entities is reported separately.

| Diagnostic | Rows | MAE NTD/ping | MAPE |
| --- | ---: | ---: | ---: |
| seen_address: seen | 6,919 | 39,658 | 13.30% |
| seen_address: unseen | 36,485 | 49,262 | 15.15% |
| seen_road: seen | 41,112 | 47,484 | 14.54% |
| seen_road: unseen | 2,292 | 52,160 | 20.60% |

There is no complete building/community identifier. Full normalized-address hashes are imperfect proxies: different units in one building may differ. Unknown roads do not create seen/disjoint evidence. These diagnostics do not certify building/community independence.

## Recency, price bands, outliers and drift

| Actual price band NTD/ping | Rows | MAE | MAPE |
| --- | ---: | ---: | ---: |
| <100,000 | 686 | 50,983 | 76.06% |
| 100,000–<200,000 | 6,865 | 34,821 | 22.10% |
| 200,000–<400,000 | 23,791 | 34,654 | 12.09% |
| 400,000–<800,000 | 10,199 | 65,136 | 12.27% |
| >=800,000 | 1,863 | 165,828 | 15.06% |

Price bands are diagnostic labels only; actual future price is not an inference input or a serving-filter feature. The lowest band has 76.06% MAPE and the highest band has 165,828 NTD/ping MAE. Gross transfer mix, rights, unobserved condition, small denominators and outliers limit interpretation.

| Transaction quarter | Rows | MAE | MAPE |
| --- | ---: | ---: | ---: |
| 2025 Q3 | 9,869 | 47,290 | 14.75% |
| 2025 Q4 | 11,252 | 47,101 | 14.82% |
| 2026 Q1 | 10,496 | 48,048 | 15.22% |
| 2026 Q2 | 11,787 | 48,420 | 14.65% |

Removing the top 1% of holdout targets for sensitivity analysis only gives MAE 45,243, RMSE 65,198, MAPE 14.80%. No such trimming changes training, serving or the main score.

Age mix shifts from a 13.0-year median at fit to 11.08 years in holdout; fitting-bin PSI is 0.287. Area mix shifts moderately (log-area PSI 0.035); floor/total-floor PSI is small. Month-index PSI is large by construction under the ordered time split and is not itself a market-drift measurement. Trees have no learned trend response beyond fitted month ranges.

## Runtime and decision

Local live companion: `127.0.0.1:8081/valuation/ml/v1/estimate`; 25 identical requests returned identical predictions/provenance, warm p50 2.21 ms and p95 3.26 ms. Nonfinite input, unsupported past dates and sparse cells reject honestly. A concurrent burst returned bounded 200/429 outcomes; no external provider or live training occurs. The existing 8080 API remains ready and its official comparable estimator remains available/actionable.

Engineering and local observational inference pass. Full property valuation, verified no-parking/whole-dwelling value, and publication-time historical evaluation remain unapproved. See `stage3-model-card.md`, `stage3-limitations.md`, the artifact manifest, exact environment lock, and acceptance JSON.

## Bounded-v1 evidence closure

The follow-up completion criteria allow unsupported features/claims to be excluded. The new audit rehashed the existing artifact and streamed all 1,321,059 canonical records, recovering exactly the original 716,413 admitted identities and split hashes. All 31 observed conflicting families remain excluded. Publication/cancellation remains explicitly bounded: unreported cancellations or changed-identity replacements may remain, and no current legal validity or historical public-information guarantee is asserted. Parking is excluded; rights are restricted to the reported registered transfer, without share-specific or whole-dwelling valuation.

No admitted row, feature, fitted source file, preprocessing state, native model byte or predictive metric changed. No retraining or holdout rescoring occurred. The API-only requested-value-basis restriction and machine-readable scope make existing limitations enforceable. This closure is acceptance of a smaller honest v1, not resolution of missing legal/publication evidence. The completed status is governed by the updated acceptance JSON after independent review. See stage3-bounded-evidence-closure.md and bounded-evidence-audit.json.

Final closure validation: 255 focused ML/API/lineage tests passed; exact model/manifest/source hashes and predictive responses are unchanged. Updated live envelope rejects all eight unsupported purpose/share/parking cases. Independent review cleared the frozen-admission checksum-binding fix and all final evidence, authorizing COMPLETE for this bounded v1. Publication evidence is BOUNDED, parking EXCLUDED FROM V1, and whole-dwelling rights RESTRICTED. No retraining, new holdout scoring, full archive build, frontend work or 8080 restart occurred.
