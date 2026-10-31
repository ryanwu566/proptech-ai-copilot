# ML valuation API v1

`POST /valuation/ml/v1/estimate` serves a reported gross-transfer estimate.
`GET /valuation/ml/v1/status` identifies the active model, target, fingerprint,
fitting cutoff, support dates, manifest hash and limitations. The local companion
base URL is `http://127.0.0.1:8081`.

```json
{
  "transaction_date": "2026-10-29",
  "requested_value_basis": "reported_transfer",
  "city": "新北市",
  "district": "新莊區",
  "building_type": "公寓(5樓含以下無電梯)",
  "main_use": "住家用",
  "area_ping": 30.0,
  "floor": 3,
  "total_floor": 5,
  "building_age_years": 20.0
}
```

The area must be the registered transferred area, including its reported common/
ancillary portions. Age is at the supplied subject date. Unknown floor, total
floors and age must be omitted or null. Numeric strings, booleans as numbers,
nonfinite values, additional fields and unsupported administrative pairs are
rejected. City 臺/台 spellings normalize deterministically. Type values are exactly
`公寓(5樓含以下無電梯)`, `華廈(10層含以下有電梯)` or
`住宅大樓(11層含以上有電梯)`. No parking or ownership field is accepted.

| HTTP | `status` | Meaning |
| --- | --- | --- |
| 200 | available | Gross NTD/ping estimate and corresponding area-scaled NTD total, provenance and coverage flags |
| 422 | unsupported | Valid DTO but outside model date/support/safety scope; amounts null |
| 422 | validation response | Invalid DTO; inference never starts |
| 429 | busy | Inference slot occupied; retry after one second |
| 503 | unavailable | No configured artifact, integrity/version failure or runtime error; amounts null |

Available responses contain `model_version`, `feature_contract_version`,
`dataset_fingerprint`, `model_manifest_sha256`, `model_generated_at`,
`fitted_through`, `target`, unit and total estimates, and `coverage` with fitting
and recent fitting counts. `confidence_probability` is null. `is_actionable` and
`historical_point_in_time_verified` are false. The limitation list is part of the
response contract, not an optional UI tooltip.

Coverage flags identify sparse fitting cells, missing physical facts, dates after
fitting, numeric values beyond fitting 1st–99th percentiles, and weak observed
geographic holdout performance. They are support diagnostics, not probabilities or
prediction intervals. The service abstains below 50 fitting rows or 20 rows in
the final 36 fitting months for the city/district/type cell. Current deployment
supports dates after its fitting cutoff, no later than the current day or the
declared artifact horizon. It is not a future-price forecast.

This endpoint never invokes geocoding, a paid provider, serving-database retrieval,
market refresh or training. All responses use `Cache-Control: no-store`.

`requested_value_basis` is an API-only purpose restriction, defaulting to
`reported_transfer` for existing callers. It is not a model feature. Requests for
`whole_property`, `whole_dwelling`, `partial_rights` or `parking_exclusive` return
422 before model loading. Ownership-share and parking inputs also reject; they
are not silently ignored or imputed.

All service responses add `scope` with evidence contract version
`plvr-bounded-transfer-evidence-v1`, snapshot publication basis, uneliminated
unobserved-cancellation risk, parking excluded, whole/share values unsupported,
and the explicit unit-times-reported-transferred-area total basis. Unknown rights
are not complete dwelling rights. The response does not establish current legal
validity of source transactions. These API additions retain the existing model
version, feature contract, artifact pin and predictive values.
