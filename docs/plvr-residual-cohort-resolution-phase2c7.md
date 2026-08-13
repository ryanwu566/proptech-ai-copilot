# PLVR Residual Cohort Resolution Phase 2C.7

## Decision

`READY_FOR_SHADOW_CUTOVER_DESIGN`

This decision permits design work only. It does not authorize a production
repair, migration, aggregate rebuild, table swap, or cutover. Production
execution remains blocked until an approved replacement plan, rollback and
validation procedure, and policies for bounded identity ambiguity exist.

## Safety and evidence

- Base main: `23b5520b06207641c661dc9d25776b47cc2103f5`
- Reused production snapshot SHA-256:
  `d18823a8e9953fd78598f3aa428b43e302dd1af1ce6d6338ca4ceabbaa6b9d33`
- Snapshot rows: `451672`
- Snapshot transaction read-only state: `on`
- Clean shadow rows: `517195`
- Phase 2C.7 production connections, writes, changed rows, migrations, and
  schema changes: `0`

The analysis reads the verified Phase 2C.6 SQLite snapshot, clean shadow, and
reconciliation database using read-only attachments. Its row-level analysis
database remains under ignored local storage. Committed artifacts contain only
safe aggregate counts, classifications, and bounded regional summaries.

## Corrected Tier-C semantics

Tier C is an exact normalized fact match, not proof of an official identity.
Topology now determines whether it is a match or a duplicate:

- One production candidate and one clean candidate:
  `STRONG_FACT_MATCH_1_TO_1`
- Multiple production candidates for one clean transaction:
  `STRONG_FACT_DUPLICATE_1_TO_MANY`
- Ambiguous exact-fact groups: `CONFLICTING`

This separates `162196` one-to-one matches from `268` actual duplicate rows.
The duplicate rows form `134` two-row groups, so duplicate excess rows and
duplicate clean transactions are both `134`. No authoritative or three-plus
duplicate group was found.

## Revised row conservation

Production buckets conserve `451672 / 451672` rows:

| Bucket | Rows |
| --- | ---: |
| AUTHORITATIVE_MATCH | 157608 |
| STRONG_FACT_MATCH | 162196 |
| GEOGRAPHY_CORRUPT_MATCH | 1 |
| DUPLICATE | 268 |
| NOT_IN_CLEAN_SOURCE | 131140 |
| FUTURE_ANOMALY | 1 |
| CONFLICTING | 458 |
| UNCLASSIFIED | 0 |

Clean buckets conserve `517195 / 517195` rows:

| Bucket | Rows |
| --- | ---: |
| PRESENT_AUTHORITATIVELY | 157608 |
| PRESENT_BY_STRONG_FACT | 162196 |
| PRESENT_BUT_PROD_CORRUPT | 1 |
| MISSING_FROM_PROD | 196796 |
| DUPLICATED_IN_PROD | 134 |
| SOURCE_CONFLICT | 0 |
| UNCLASSIFIED | 460 |

The `460` clean unclassified rows all have the explicit reason
`BOUNDED_FACT_GROUP_AMBIGUITY`. They are the clean candidates in bounded
conflict groups, not unknown lineage. They are `0.0889%` of the clean shadow,
below the `0.1%` design materiality threshold, and remain execution-blocking.

## Conflict topology

The `458` production conflict rows form `193` exact-fact groups. None was
promoted beyond the available evidence:

- `439` rows in `183` single-artifact groups are
  `INSUFFICIENT_EVIDENCE`.
- `19` rows in `10` multi-artifact groups are
  `SOURCE_REVISION_AMBIGUITY`.
- Resolved rows: `0`.
- Materially unresolved rows: `458`.

Candidate official source identities are distinct within these groups.
`building_age_years` was checked as an auxiliary fact but did not uniquely
distinguish any candidate. The groups are bounded sufficiently to design a
shadow replacement, but individual production-to-clean permutations must not
be guessed.

## Residual classifications

The formerly unresolved production-only cohort conserves `5017 / 5017`:

| Reason | Rows |
| --- | ---: |
| LEGACY_IMPORT_TRANSFORMATION_ERROR | 4988 |
| IDENTITY_LOSS | 5 |
| SOURCE_RECORD_NOT_REACQUIRED | 9 |
| INSUFFICIENT_EVIDENCE | 15 |

The canonical-invalid cohort conserves `126087 / 126087`:

| Reason | Rows |
| --- | ---: |
| LEGACY_IMPORT_TRANSFORMATION_ERROR | 114740 |
| RECOVERED_AUTHORITATIVE_CITY_LEVEL | 10974 |
| CONFLICTING_GEOGRAPHY_CANDIDATES | 367 |
| CLEAN_SOURCE_MISSING | 6 |

The `10974` residual was a predicate mismatch: Tier-B official identities
reconstruct successfully, and the clean rows are city-level records. The
production district repeating the city name is therefore not treated as an
unresolved district record. No production geography was changed.

## Historical and future cohorts

- The original Phase 2B planner reproduces the supporting-evidence count at
  `109236`; status: `REPRODUCIBLE`.
- The historical duplicate cohort is `PARTIALLY_REPRODUCIBLE`. The original
  broad predicate reproduces `57544`, while the published `57350` included a
  `194` aggregate-only adjustment whose row membership was not retained. This
  does not block design but does block execution relying on that membership.
- The single `2026-10` row is a `STRONG_FACT_FUTURE_SOURCE_MATCH` tied to the
  locally retained authoritative artifact. It remains excluded from
  publishable output.

## Aggregate attribution and materiality

Canonical county alias normalization is applied consistently before comparing
scopes. The result contains `11017` production scopes and `9606` clean-shadow
scopes:

- Exact scopes: `3883`
- Mismatched scopes: `9242`
- Fully explained: `9121` (`98.6908%`)
- Partially explained: `121` (`1.3092%`)
- Unexplained: `0` (`0.0000%`)

The attribution matrix covers production-only legacy imports and outside-window
rows, clean rows missing from production, strong-fact duplicates, invalid and
canonical geography semantics, bounded identity conflicts, missing source
records, future exclusion, source-scope differences, and other known matched
fact differences. Zero-count reasons remain in the artifact so the contract is
stable.

Absolute transaction-count delta is `348773` for fully explained scopes and
`3161` for partially explained scopes. Absolute total-value delta is
`511885933.08` and `5739175.37`, respectively. Unit-price delta mean, median,
and maximum are recorded by explanation status in the safe aggregate artifact.

The rule is deliberately fixed before the gate result: aggregate differences
are material when unexplained scopes exceed `0.1%` of mismatched scopes, or any
golden region has an unexplained latest publishable period. The result is
`IMMATERIAL_BOUNDED`; bounded partial scopes remain visible rather than being
called fully explained.

## Golden regions

All seven required golden regions have `35` periods, latest publishable period
`2026-07`, an internally consistent clean shadow, and a fully explained latest
period:

| County | District |
| --- | --- |
| Taipei City | Zhongzheng District |
| Taipei City | Nangang District |
| Taichung City | Beitun District |
| Taoyuan City | Pingzhen District |
| Taoyuan City | Zhongli District |
| Kaohsiung City | Xiaogang District |
| Kaohsiung City | Sanmin District |

The artifacts retain canonical Chinese names plus membership and aggregate
deltas. Shadow output is not required to equal contaminated production output;
it must be authoritative, internally consistent, and explainably different.

## Cutover boundaries

Design blockers: none.

Execution blockers:

- `no_approved_shadow_cutover_plan`
- `production_mutation_not_authorized`
- `rollback_and_validation_procedure_not_designed`
- `bounded_identity_ambiguities_require_execution_policy`
- `historical_57350_row_membership_not_reproducible`

No production cutover or mutation is part of Phase 2C.7.
