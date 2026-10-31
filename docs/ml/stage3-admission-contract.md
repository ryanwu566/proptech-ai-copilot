# Stage 3 admission decision

The supplied historical staging contract is deliberately **not** a training
authorization. Its original `training_authorized=false` fields and the strict
ML-A, ML-B, Target A and Target B gates remain unchanged.

Stage 3 introduces `plvr-archive-snapshot-admission-v1` for a different estimand:
`reported-gross-transfer-ntd-per-registered-ping-v1`. Only a successful independent
full verifier and the additional cohort/split checks authorize fitting this model.
The declared meaning is a reported gross transfer amount per reported registered
building area, conditional on the declared structural attributes. It is not a
verified parking-exclusive price or complete dwelling-interest valuation. The API
marks this capability non-actionable and returns these limitations with estimates.

| Existing gate | Exact purpose | Artifact evidence | Stage 3 decision |
| --- | --- | --- | --- |
| Historical availability | Reconstruct information genuinely public at each past fitting freeze, including exact versions and cancellations | Forty consecutive release archives with exact bytes/row locators; no authenticated historical publication times or exhaustive cancellation history | Still unsatisfied for PIT evaluation. Snapshot fitting uses disjoint transaction-date blocks and source-quarter membership restrictions, without claiming publication-time availability. Current training is authorized only for retrospective archive-snapshot research/observational inference. |
| Parking | Establish no-parking target area/consideration or reliably separated parking features | Count may be reported; semantic parking basis explicitly unverified | Omit all parking features and adjustments. Preserve the unadjusted gross target. Blank or zero parking never establishes absence. Residual parking mix is unobserved error, not imputed semantics. |
| Rights/dwelling | Establish full interests in one whole dwelling and correct private/common area basis | Rights explicitly unverified; registered transferred area and gross consideration are reported | Omit rights features and complete-dwelling claims. Predict reported transfer basis only. Full residential property valuation remains unapproved. |
| Identity/revision/special notes | Prevent repeat/revised labels and related-party or ambiguous groups from contaminating labels | Canonical serials, strong-fact families, occurrence/version ledger, quarantines | Mandatory without relaxation. Verify clean-family joins, one semantic version, zero note-taint, unambiguous facts and source locators. |
| Geography | Prevent county misattribution and fabricated geographic precision | Source county and registry-checked district; two explicit city-level groups | Admit only actual district records. No inferred district, road coordinates, geocoding or city-level expansion. |
| Target | Ensure finite, positive, unit-consistent labels | Decimal gross consideration / (registered square metres × 0.3025) | Recheck exact Decimal identity. Do not replace it with the differently based official reported unit price. |

The feature contract is `plvr-gross-transfer-features-v1`. Inputs require reported
`main_use=住家用`, one of the three specified apartment building types, an actual
county/district pair, 5–200 registered ping, and an exact subject transaction date.
Floor, total floors and age are optional and remain missing if unknown. Known
values are bounded (floors 1–60, age 0–100 years), and floor must not exceed total
floors. Area uses the same registered transferred basis as the target. No household,
private-area-only, market-listing or interior-area equivalence is implied.

The six numeric features are month index, log area, floor, total floors, age at the
subject date and floor/total-floor ratio. Categorical features are city, the
city/district pair, and building type. Vocabularies come from the pre-existing
administrative registry and explicit type allowlist, independently of targets and
holdout observations. There are no target aggregates. Linear preprocessing learns
imputation/scaling from fitting data only; trees preserve missing numeric values.

The conservative archive window is **2017-01-01 through 2026-06-30**: the first
complete calendar year after release 105S4 through the completed transaction
quarter before final release 115S3. Forty consecutive releases establish archive
coverage, not full population coverage or publication dates. The older sparse
record dates, 2013 density span, and incomplete 2026 Q3 tail do not extend this
window.

Model selection uses train 2017-01-01–2024-06-30 and validation
2024-07-01–2025-06-30. Train rows must belong to source releases no later than
113S2; validation rows no later than 114S2. These are conservative source-membership
filters, not invented release timestamps. The selected configuration is refit on
train + validation, then evaluated on final holdout 2025-07-01–2026-06-30, using
the archive through 115S3. No holdout row or target is used to fit parameters,
preprocessors, medians or model selection. Exact counts and actual boundaries are
recorded in admission evidence.

Canonical identities are globally unique by full verification. Address hashes and
city/district/road groups provide additional unseen-entity temporal diagnostics.
They do not establish building/community disjointness: different units in the same
building may have different addresses, and actual community IDs are unavailable.
Geographic IDs are ordinary declared location features, shared across time; their
recurrence does not provide future target statistics. Sparse and unseen fitting
cells are diagnosed and inference abstains below declared support thresholds.

This redesign removes unnecessary **feature** requirements transparently. It does
not pretend that unavailable source semantics are resolved. Statistical calibration,
PIT historical performance and complete property valuation remain outside the
authorized contract. Regression tests cover this distinction.

## Bounded-v1 completion clarification

The follow-up Stage 3 criteria explicitly permit completion with unsupported
claims removed. The [evidence closure](stage3-bounded-evidence-closure.md) and
`reports/professor-stage3-ml/bounded-evidence-audit.json` bind the unchanged cohort
and artifact to those limits. Publication/cancellation is BOUNDED to observed
archive records; parking is EXCLUDED FROM V1; whole-dwelling rights are RESTRICTED
to reported-transfer observations. Unknown cancellation and latent partial-right
risk are disclosed, never converted into active/full-rights claims. The API
accepts only `requested_value_basis=reported_transfer` and returns these limits
in a machine-readable scope envelope. Stronger ML-A/B authorizations remain false.
