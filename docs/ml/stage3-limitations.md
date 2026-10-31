# Stage 3 limitations and failure modes

The released capability is an **observational gross-transfer estimator**. It does
not authorize a complete residential property valuation or a historical
point-in-time performance claim. Strict earlier ML admission contracts remain
blocked on their original evidence requirements. Those stronger future product
claims are excluded from v1. The follow-up completion criteria permit a COMPLETE
bounded capability after audit, focused validation and independent review.

| Failure mode | Evidence or boundary | Behavior / interpretation |
| --- | --- | --- |
| Parking mix and transferred rights | Source does not establish parking basis or whole-dwelling interests | No parking/rights feature, adjustment, absence assumption or full-property claim; amounts use gross reported consideration / registered transferred area |
| Historical availability/cancellation | Exact archive bytes and 40 consecutive source releases; authenticated past publication times and exhaustive cancellation ledger unavailable | Source-quarter membership restrictions reduce future-source contamination; evaluation remains retrospective archive-snapshot generalization |
| Incomplete historical ends | Sparse older dates; thin latest-quarter tail | Admit 2017-01-01–2026-06-30; do not describe 2011 or 2013 as continuous source coverage |
| Fitting boundary gaps | Train source cap 113S2 and validation cap 114S2 | Actual final train date 2024-05-31 and final validation date 2025-06-02; report actual dates separately from planned blocks |
| Selection bias | Blank-note, unambiguous identities, reported residential use, three multifamily types and registered-area bounds only | No generalization to flagged/related-party deals, land, commercial use, townhouses, city-only records or undisclosed population |
| Missing property facts | Optional floors/age can be null; no community ID, coordinates or interior condition | Preserve missing values and flag them; no zero/new-building imputation, geocoding or invented structural precision |
| Entity overlap | Normalized address hashes and roads can recur across temporal blocks | Report seen/unseen temporal diagnostics; full building/community disjointness is unproved; no address/road/identity feature |
| Sparse or unseen fitting cell | Fewer than 50 fit rows or 20 rows in the final 36 fitting months for a geography/type cell | Abstain with 422 and null amounts; 50–199 rows receive low-support flag |
| Extreme or unusual structural input | Area outside 5–200 ping, age outside 0–100, floors outside 1–60, inconsistent floor pair | Invalid DTO rejects; valid values outside fitting 1st–99th percentiles receive coverage flags; joint structural support is not calibrated |
| Temporal extrapolation | Model fitted through early June 2025; trees cannot extend a learned price trend beyond fitting dates | Mark every supported later estimate as extrapolation; reject dates after current day or artifact horizon; no future-price forecast |
| Distribution drift | Age/area/type/geographic mix can change, as can the market | Report fitting-vs-holdout distributions; time-feature shift is expected under a chronological split and does not by itself quantify market drift |
| Heavy error tails | Global averages conceal low-price errors and luxury/outlier absolute losses | Report p90/p95/p99 errors, fixed price bands and trimmed sensitivity; no invented confidence probability or calibrated interval |
| Weak geographic slice | Fixed warning rule: heldout geography MAPE above 35% with sufficient reported slice support | Return warning; this is retrospective error evidence, not subgroup calibration or a prediction probability |
| Invalid/corrupt/missing model | Missing variables, wrong manifest pin, corrupt bytes, wrong authorization/schema/runtime/provenance | Sanitized 503, no fallback. Native text only, size bounds and semantic validation before parser; failure cached until restart |
| Concurrent requests | Single inference slot and single native prediction thread | Return 429 when slot occupied; companion Uvicorn caps connections and request body middleware bounds bytes/deadlines |
| Interrupted offline work | Partial files, stale configuration or code/runtime/data mismatch | Verify bindings and hashes before reuse; quarantine invalid checkpoints and refit that phase; atomic certificates and artifact directory publication |

Final numeric evidence is in `stage3-evaluation-report.md` and
`../../reports/professor-stage3-ml/evaluation.json`. Overall metrics cover all
admitted holdout rows, including cells that the serving support policy rejects.
`serving-coverage-evaluation.json` reports the supported subset separately. The
corrected pipeline rerun is a reproducibility and integrity check of the same
experiment, not a new independent holdout experiment.

Future changes to target basis, source-publication evidence, property scope,
features, support policy, fitting dates or artifact format require a new version
and admission review. None can be enabled by changing `training_authorized` on
the original staging records.

The closure audit explicitly acknowledges that unreported cancellation/replacement
events and undisclosed partial interests may remain in frozen observations. This
is a reported-transfer model, not a currently valid legal transaction register.
Parking counts do not supply consideration/area semantics. The API-only requested
basis accepts exactly `reported_transfer`; whole-property, share-specific and
parking-exclusive requests reject, and responses state these limits through
`plvr-bounded-transfer-evidence-v1`. No model data, features, weights or metrics
changed during closure. See `stage3-bounded-evidence-closure.md`.
