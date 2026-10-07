# ML valuation dataset foundation v1

Review date: **2026-10-07, Asia/Taipei**. Starting SHA: `9435233ca38843dbeabbe8327148acd199f405ee`. Branch: `research/ml-valuation-dataset-foundation-v1`. Authorized workspace: `C:\Projects\proptech-ml-dataset-foundation`. Initial worktree was clean and matched the required branch/SHA.

**Foundation tooling and contracts are implemented. Dataset readiness remains BLOCKED. ML-B may not begin.**

The historical [ML-A report](valuation-dataset-readiness-v1.md) and [evidence](valuation-dataset-audit-evidence-v1.json) remain unchanged. This follow-up consumes those findings rather than repeating the database audit. A deterministic aggregate report is reproducible; a defensible real training cohort has **not** been demonstrated.

## Deliverables and evidence classes

- [Source contract](contracts/source-contract-v1.json), [release ledger schema](contracts/release-ledger-v1.schema.json), [private staging occurrence schema](contracts/staging-occurrence-v1.schema.json), and [future dataset manifest schema](contracts/dataset-manifest-v1.schema.json).
- [Release recovery ledger](valuation-source-release-ledger-v1.json): 17 historical releases, including hashes, retrieval claims, source identifiers, periods and explicit unknown fields.
- [Aggregate foundation evidence](valuation-dataset-foundation-evidence-v1.json): source counts, reconciled geography diagnostics, unavailable cohort stages, parking/target/identity/time/lineage limitations and B1–B6 blockers.
- [Strict semantics](../../scripts/ml/semantics.py), [identity/as-of selection](../../scripts/ml/lineage.py), [contract validation](../../scripts/ml/contracts.py), [bounded audit CLI](../../scripts/ml/audit_foundation.py) and [89 focused tests](../../tests/test_ml_dataset_foundation.py).
- [Narrow readiness re-evaluation](valuation-dataset-readiness-followup-v1.md) and [execution plan](valuation-dataset-foundation-plan-v1.md).

Evidence classes are kept separate:

1. **Inherited observations:** canonical ML-A database counts and dated historical forensic/rebuild findings. No new database recount occurred.
2. **Current local inspection:** the ignored historical manifest is present, but official archives and SQLite/Parquet sources are absent under the inspected source locations. Metadata does not count as recovered bytes.
3. **Executed synthetic proof:** tests establish strict parser, target, parking, geography, revision, bounds, count and CLI behavior. Their artificial identifiers/evidence references do not qualify as actual source proof.
4. **Future contracts:** archive parsing/detail joins, authenticated attestations, complete dataset builds and storage provisioning are specified prerequisites, not completed operations.

## Source acquisition and historical recovery

The authoritative family is MOI PLVR existing-sale-main, catalog **25119**. The official catalog lists main/build/land/parking schemas and packaged releases. The schedule does not establish a particular archive's publication timestamp. [Official catalog](https://data.gov.tw/dataset/25119).

Repository paths were reviewed:

| Path | Foundation relevance |
| --- | --- |
| `scripts/acquire_official_plvr_artifacts.py` and `services/plvr_clean_shadow_rebuild.py` | Bounded inventory/acquisition, archive hashing, package validation and historical manifest support; acquisition is opt-in |
| `scripts/import_plvr_to_postgres.py` and `services/plvr_import_service.py` | Serving importer; loses raw main-use/parking/rights/completion/availability semantics; not an ML builder |
| `services/plvr_clean_shadow_rebuild.py` | Preserves more source identity but uses legacy normalization and latest-artifact resolution; not an as-of dataset |
| `services/official_plvr_market_pipeline.py` | Richer release/parking contract; canonical audit found mixed land/building classification unsuitable for this cohort; no production changes made |
| `artifacts/plvr_source_manifest.json` | Ignored local metadata; historical metadata checksum matches `18203c6347cd2e7c0fd4f274ec1c6e6b3f49cef8d4f890099a01ccacb9d0aa06`; original ZIP bytes absent |

The new ledger uses only the bounded release set already named by ML-A. Source URLs are recovery candidates, never a guarantee that today's response matches old bytes. In particular, the **current URL is moving**; fetching it now cannot recover `current-20260811` by relabeling today's archive.

| Historical release | Local recovery status | Remote exact-byte recovery | Publication/availability |
| --- | --- | --- | --- |
| 112S3, 112S4 | MISSING each | UNKNOWN | UNKNOWN |
| 113S1, 113S2, 113S3, 113S4 | MISSING each | UNKNOWN | UNKNOWN |
| 114S1, 114S2, 114S3, 114S4 | MISSING each | UNKNOWN | UNKNOWN |
| 115S1, 115S2 | MISSING each | UNKNOWN | UNKNOWN |
| 20260701, 20260711, 20260721 history | MISSING each | UNKNOWN | UNKNOWN |
| 20260801 history | MISSING | UNKNOWN | UNKNOWN |
| 20260811 current | MISSING | UNKNOWN | UNKNOWN |

Total: **17 MISSING locally**, **253,796,255 declared bytes**, **0 exact archives verified**. Each individual release is machine-recorded. The three July history increments had historically partial county coverage; that is separate from their currently absent bytes. Unlisted periods are **UNKNOWN/not inventoried**, not assumed available or missing globally. No years of data were downloaded; no source archive was downloaded in this task.

Recovery status semantics:

- `AVAILABLE`: exact expected archive checksum passes and required package/schema members and archive CRC pass; semantic onboarding and completeness still need review.
- `PARTIALLY AVAILABLE`: local candidate bytes exist but integrity, size or package requirements fail. Never eligible automatically.
- `MISSING`: bytes absent in the declared local inventory locations. Says nothing definitive about government/object-storage recovery.
- `UNKNOWN`: no evidence sufficient to classify the specified recovery location/period.

### Exact bounded recovery workflow

1. Choose **one existing quarterly release** from the ledger and an explicitly declared county scope; a full quarterly archive is the indivisible source package. Prefer a historical static release over the moving current URL. Review its declared size, expected SHA256 and county/member coverage before acquiring it. Do not loop over all 17 releases by default.
2. Restore from an already approved archive store if it exists; otherwise inspect the official season/history candidate URL with the existing allowlisted HTTPS acquisition mechanism. Keep all activity in `data/raw/plvr/ml-foundation/` or another explicitly declared ignored local source directory. The new inventory's declared locations must be extended explicitly to see that directory.
3. Stream into a new temporary file with a byte cap; validate TLS/host, archive SHA256, member CRC, expansion/member limits and embedded schema/manifest hashes. Accept **only an exact checksum match** for historical reproduction. A different response becomes a new snapshot/release identity with new acquisition evidence; never overwrite or relabel the old identity.
4. Preserve original filename/header evidence, effective registration window, package capture time, HTTP evidence and every schema/detail member. Record filename fallback separately from an authenticated server filename. Current ledger original filenames are inherited metadata claims, including possible fallback values.
5. Establish historical availability through authentic official release records or a documented conservative public observation upper bound. If only reacquisition is evidenced, admit no earlier availability. Schedule, nominal quarter, registration window and acquisition timestamp are distinct.
6. Onboard the exact main schema. Preserve all physical rows, raw UTF-8-decoded strings, encoding and physical CSV record locator. Count schema/English-description records separately from transaction records; never silently skip a transaction. Reject malformed headers/encoding with explicit counts. The strict numeric/date/floor functions exist; **a complete archive/CSV-to-staging parser is not implemented in this task**.
7. Join reviewed build/land/park details without multiplicity inflation. Establish full rights, one dwelling, registered area basis, parking absence, special state and county-scoped ID reuse semantics. Produce immutable private evidence artifacts and reference their SHA256, locator and evidence version. Missing proof excludes the row.
8. Append release/member/import counts with `raw = accepted + rejected`; retain excluded/canceled/conflicting occurrences. Never load ML staging into application packages or mutate serving data.
9. Run the bounded staging audit with explicit availability cutoff. Escalate volume to a separate streaming/offline indexed implementation only after the bounded contract passes; this tool refuses oversized inputs rather than reporting a truncated cohort.
10. After sufficient scoped releases and verified coverage exist, implement the future builder, run two independent complete builds, validate the manifest/output/exclusion/split hashes and narrowly re-run ML-A.

## Release and lineage contract

`plvr-ml-release-ledger-v1` records source dataset/release IDs, URL/catalog identifier, effective window and its **registration** basis, original/local archive filenames, SHA256, declared size, retrieval claim, publication resolution, available-at/evidence, parser/transform versions, import batch, raw/accepted/rejected counts, members, status and supersession/evidence.

For all 17 releases, publication/availability, parser/transform used for an ML import, ML import batch, ML parser counts and supersession are **null**. Current offline parser versions are pinned in the source contract; they are not retroactively assigned to historical imports. Historical per-release row counts cannot be inferred by dividing the prior nationwide rebuild totals. Acquisition in August 2026 is not first public availability.

Append a new ledger revision for new facts, retaining the old file and content hash in the artifact store. An offline manifest is sufficient; no production DB migration is needed. Contract validation rejects unknown fields, noncanonical source identities, malformed hashes/timestamps, duplicate release IDs, invalid supersession references and count discrepancies. JSON Schemas can be validated with an existing Draft 2020-12 validator; core tooling uses only Python's standard library and checks the assertion subset these schemas use.

Evidence references in staging are **inputs from the reviewed recovery process**. The audit checks their shape and consistency. It cannot authenticate a claimed file/hash or infer that a cited detail proves full rights. A positive staging count therefore is a candidate count, **never a readiness approval**.

## Transaction identity and revisions

Identity version: `plvr-county-official-family-v1`.

- `transaction_family_id`: SHA256 of explicit identity version, existing-sale source dataset, source member's verified county namespace and retained official `編號`. Price, area, address and rounded legacy facts do not define the family.
- `version_id`: SHA256 of family and canonical raw payload/cancellation state. Raw changes create a new version; changing price does not create a new family.
- `occurrence_id`: SHA256 of dataset, archive SHA256, member path and physical record number. Every occurrence remains in immutable staging.
- ID namespace/reuse evidence is required. A missing ID or unresolved reuse cannot be repaired using rounded facts. Source member and context must agree. Only the exact official existing-sale source is admitted.

Selection version: `plvr-explicit-revision-asof-v1`. Before cutoff filtering, check occurrence conflicts across **all families**, contradictory release/archive/availability metadata, member checksums and completeness of lineage/availability. A contradiction or unknown availability quarantines the affected family; there is no favorable hash tie-break.

Among versions evidenced available by C, require an explicit predecessor chain with strictly increasing available-at times. Unknown/missing parents, competing versions at one time or inconsistent semantic attestations are ambiguous. Available-at orders a **proven chain**; it is not standalone proof of correction. A version first published after C cannot overwrite the earlier selection at C.

Select the latest proven version over the full ledger **before** use/rights/parking/target rules. A selected cancellation or ineligible correction excludes the family; do not resurrect a qualifying old row. Identical occurrences in one release are `exact_duplicate`; identical payloads across releases are `republication`. Keep all source edges and count every excluded occurrence. Distinct official IDs with identical facts remain separate unless source evidence establishes an identity conflict.

Canonical ML-A's **457 fact collision groups / 1,026 related rows / 569 excess rows** remain unresolved. No actual row-level resolution, deletion or merge was applied. Historical two-revision findings are retained as historical evidence, not newly verified source versions.

## Geography findings and normalization

The full canonical aggregate partition reconciles to 451,672:

| Observable classification | Rows |
| --- | ---: |
| Current county/district registry plausible | 325,585 |
| Current registry mismatch; district exists under another county | 115,113 |
| Documented city-level-only 新竹市/新竹市 or 嘉義市/嘉義市 | 10,974 |
| Observable historical-name/encoding/malformed/unsupported label failures in this aggregate set | 0 |

**211,170 rows** use a `台` label variant. That is an overlapping lexical diagnostic, not an additional exclusion or a count of repaired county identity. The 115,113 mismatches all have a district name elsewhere in the current registry; none become authorized remaps on that basis.

Prior [production repair evidence](../plvr-production-repair-plan.md) and [lineage analysis](../plvr-lineage-collision-resolution.md) identify import county contamination, with most problematic rows concentrated in June 7 imports. They found no deterministic authoritative row-to-file/release join. Cross-county examples include 台南市/中壢區 (5,056 rows). This supports an import-geography problem, not a claim that all causes or individual corrections are source-proven. Even registry-valid shared district names can conceal an incorrect county.

The offline normalizer preserves raw city/district, normalized city/district, source county, reason and `plvr-source-county-strict-geography-v1`. It pins the checked-in registry by checksum and uses only exact official sale-main file codes. It accepts outer trim and `台`→`臺`, rejects internal whitespace/encoding damage, refuses unsupported members and source-county conflicts, quarantines historical counties and excludes city-level-only labels. It does not infer a county from district/address or strip arbitrary suffixes. Historical boundaries need a separately evidenced effective-dated mapping, not automatic modernization.

Result: reproducible failure classification and tested normalization policy; **0 actual geography repairs applied**.

## Conservative cohort and derivability

Contract: `residential-apartment-no-parking-v1`, matching ML-A's proposed scope.

| Criterion | Raw-source derivability | Accessible legacy result |
| --- | --- | --- |
| Exact existing sale `房地(土地+建物)` | RELIABLY DERIVABLE with matching main schema | Raw target absent; not reliable from building type |
| Exact main use `住家用` | RELIABLY DERIVABLE with matching vocabulary | Absent; NOT RELIABLE |
| Supported 住宅大樓/華廈/公寓 exact aliases | RELIABLY DERIVABLE as a type label | 351,286 type-only proxy; not approved residential rows |
| One building count | DERIVABLE WITH RESTRICTIONS from exact `土地N建物N車位N` grammar | Count absent |
| One dwelling and full rights | NOT RELIABLE from single-building count or blank notes alone; requires reviewed rights/detail evidence | Unavailable; every unproved candidate fails closed |
| No parking | DERIVABLE WITH RESTRICTIONS from zero count + reviewed details + schema/type/area/price agreement | All 451,672 legacy rows classified UNKNOWN |
| Verified registered transferred area basis | DERIVABLE WITH RESTRICTIONS from release schema and compatible rights/detail proof | Gross rounded area alone insufficient |
| Valid raw price/date/single floor | DERIVABLE WITH RESTRICTIONS after strict parsing/reconciliation | Raw inputs lost; legacy positivity insufficient |
| Blank notes and no special state | DERIVABLE WITH RESTRICTIONS; blank notes alone are not independent proof | Raw_note lacks this proof |
| County/district and official ID namespace | DERIVABLE WITH RESTRICTIONS from verified member/ID evidence | Per-row lineage absent |
| Historical as-of eligibility | DERIVABLE WITH RESTRICTIONS from availability and ordered revision ledger | Unavailable |

Additional policies: 5–150 registered transferred ping inclusive; 10,000–5,000,000 NTD/ping inclusive; one floor with `1 <= floor <= total floors <= 100`; no presale/rental/land-only/building-only/parking-only/bundled/mixed-use rows; exclude nonblank notes and unresolved special state. Land-parcel count can exceed one only with verified dwelling/land interest evidence. These are v1 scope policies, not definitions of every legitimate transaction.

## Target, area and parking

Target: `residential-unit-ntd-ping-log-v1`. Price basis: `whole-rights-land-and-residential-building-sale-no-parking-v1`. Area basis: `registered-transferred-building-including-aux-common-no-parking-v1`.

```text
P = raw 總價元, NTD
A = verified raw 建物移轉總面積平方公尺, m²
area_ping = A * Decimal("0.3025")
unit_price_ntd_ping = P / area_ping
target_log_unit_price = ln(unit_price_ntd_ping)
```

Use Decimal precision 28 without input pre-rounding; retain raw decimal strings. Serialize log as finite float64. Reject missing/malformed/nonfinite/nonpositive price or area, unsupported area basis, parking ambiguity and scope violations. A positive supplied official sqm price must reconcile within `max(1 NTD/m², 0.001 * P/A)`. Missing official unit price allows computation after basis proof; present invalid unit price excludes. No imputation, winsorization, target substitution or blind use of stored unit prices.

This is a land-and-residential-building package price per **registered transferred building ping**, including compatible ancillary/common allocations. It is not interior area, a building-only cost or a parking-inclusive target. The official guidance describes registered area and varying common/parking registration; it also explains that unit price subtracts parking price and area only when supplied separately. [MOI guidance](https://lvr.land.moi.gov.tw/R11/jsp/qa.jsp).

The v1 implementation performs **no parking subtraction**. `NO_PARKING_CONFIRMED` requires exact supported target, zero parsed parking count, reviewed zero parking-detail count/evidence, a present blank type field and zero price/area. Blank price/area are acceptable only with explicit reviewed source-schema meaning plus independent absence evidence. A missing field is not an explicit blank. Any positive count/type/detail/price/area is `PARKING_PRESENT`; contradictions, negative/malformed quantities or unproved blanks are ambiguous; missing count/detail/schema/evidence is UNKNOWN. All states other than confirmed absence are excluded.

Canonical legacy evidence has no parking columns: **UNKNOWN 451,672**, confirmed-present/confirmed-absent/explicit-ambiguity evidence counts each **0**. These zeros describe proof availability, not actual market composition. The prior 76,210 gross-price/area mismatches remain diagnostic and cannot be assigned wholesale to parking. Target-valid real candidates remain **unknown**.

## Age and canonical times

`age_at_transaction` can compute a versioned **month-resolution diagnostic** only from valid ROC transaction/completion dates:

`age_months = 12 * (transaction_year - completion_year) + transaction_month - completion_month`.

`age_years = age_months / 12`. Malformed/partial year-only/missing values yield missing; negative ages and exact completion days after an exact transaction day yield missing. It never uses today's year or converts stored current age backward. Tested reconstruction is not real field coverage evidence. Completion values are absent from accessible legacy facts, so **age remains DEFERRED/excluded**, as does road. Month-age is not advertised as exact-day age; ambiguous same-month completion ordering needs its own evidence before any age feature approval.

| Field | Meaning and policy |
| --- | --- |
| `transaction_effective_period` | Raw validated day/month plus explicit precision; cohort v1 requires a full day; a month date never gets a manufactured transaction day |
| `publication_date` / precision | Actual documented release date if known; unknown stays null |
| `source_release_available_at` | Evidenced exact publication timestamp or conservative authenticated public observation bound, with evidence locator/version/hash |
| `retrieved_at` | Package acquisition/capture claim; separate from first public availability |
| `ingested_at` | Successful private staging import; separate from release and effective time |
| `transformed_at` | Transformation time; never a version-order substitute |
| `availability_cutoff` | C used to select eligible versions/labels |
| `training_data_cutoff` | Effective-data boundary; must not follow availability cutoff |
| `label_observation_cutoff` | Separately frozen scoring-label maturity boundary; never grants earlier feature/train access |

All exact instants require timezone offsets; day comparisons use Asia/Taipei. Future manifest v1 pins **public-information research framing**. Operational-system replay additionally needs independently established system-availability history and is not implemented/approved here. Subject attributes must be independently available at the prediction clock; the audit cannot certify that retrospective declaration fields were known before sale negotiation.

No current POI, Routes, MRT, GIS, hazards, market aggregates, LLM outputs or current building-age enrichment is joined.

## Reproducible funnel and executable audit

Run from the workspace root:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python -m scripts.ml.audit_foundation
python -m scripts.ml.audit_foundation --ledger-only
python -m scripts.ml.audit_foundation --staging data/processed/plvr/ml-foundation/occurrences.jsonl --cutoff 2026-10-07T00:00:00+08:00 --max-rows 10000
python -m pytest tests/test_ml_dataset_foundation.py -q --basetemp=.pytest-temp-ml-foundation
```

Inventory mode reads canonical aggregate evidence and hashes/inspects only the named local source candidates. It has no DB/network/provider calls. CLI stdout is JSON; error output is a bounded generic message that does not echo private payloads. Redirect only to an appropriate aggregate-evidence destination. The JSONL mode accepts **32 MiB maximum**, defaults to **10,000 rows** and caps an explicitly requested limit at **100,000**. Blank/malformed/oversized inputs fail with no partial report. The CLI never modifies inputs or creates a dataset.

Staging order: identity/availability/revision/cancellation selection → parse/type/time → geography → residential use → rights → property type → parking → target → floor/special-state. Each sequential stage records input, newly excluded, remaining and first-reason counts; evaluated selected versions also record all semantic reasons. Identity reasons reconcile every input occurrence. Rows already excluded by identity have no asserted parking/target classification. Aggregate diagnostics are parallel profiles, not cohort stages to subtract twice.

| Actual evidence | Count |
| --- | ---: |
| Canonical total legacy rows | 451,744 |
| Demo excluded | 72 |
| Legacy official population | 451,672 |
| Type-only residential proxy (parallel diagnostic) | 351,286 |
| Raw official staging rows audited now | 0 |
| Parse-valid official raw cohort | Unknown |
| Source-proven geography-valid cohort | Unknown |
| Residential-use cohort | Unknown |
| Full-rights/single-dwelling cohort | Unknown |
| Supported-type cohort after prior criteria | Unknown |
| Parking-safe cohort | Unknown |
| Target-valid cohort | Unknown |
| Final defensible/PIT candidate cohort | Unknown |

Unknown counts are JSON null, not invented zero. Registry-plausible 325,585 and type-only 351,286 cannot be intersected from marginal aggregates. The synthetic two-row funnel test selects two identities, rejects one parking row, and retains one candidate; it is a software test only, not actual official cohort evidence.

Two fresh local inventories and aggregate audits produce byte-identical canonical JSON. Tests also verify input-order invariance and read-only CLI behavior. This proves reproducible **foundation reporting**, not the required two real dataset builds. The report pins source/evidence/registry/cohort/code hashes; registry/cohort JSON uses canonical serialization and source code normalizes UTF-8 line endings to LF so Git's Windows conversion cannot change semantic repository hashes. Archives retain exact-byte SHA256. Timestamps are not generated merely to make deterministic reports differ.

## Future dataset build and manifest

Pipeline: exact source releases + embedded schemas → validated streaming parser/detail joins → immutable raw/staging occurrences → source county normalization → complete family/revision/cancellation ledger → as-of version selection → conservative cohort → exact target/physical QC → prediction-time eligibility and frozen splits → versioned offline artifact + exclusion ledger + manifest.

The serving database is not the authoritative artifact. The complete builder, large-input indexed selection, archive/CSV parsing/detail review and chronological splits are future work; this task implements the bounded audit and contracts.

The manifest schema requires dataset/target/price/area/feature/source-ledger/parser/transform/geography/identity/selection/cohort versions; Git builder SHA and code/dependency/registry/cohort hashes; build/effective/availability/scoring-label cutoffs; timezone/prediction framing; ordered release/member/schema/checksum linkage; reconciled row/exclusion/raw counts; dataset/exclusion/split checksums; district/type/month counts; coverage and subject-availability evidence; preprocessing manifest checksum when preprocessing exists.

Model A features are exactly county/district namespace, supported type, verified area, single floor and prediction year/month. Total floors remain a QC fact; age, road, IDs, raw addresses and outcome-derived values are excluded from features. `preprocessing_manifest_checksum=null` means no fitted preprocessing exists; no downstream training run may interpret it as proof of frozen vocabularies. Any future fitted preprocessing artifact needs its own fit-cutoff/feature-vocabulary hash manifest. A dataset manifest is not a model artifact or gate verdict.

Future canonical output is UTF-8 JSONL sorted by family/version, with canonical JSON keys, explicit Decimal strings and float log values under a pinned Python/environment lock. Hash **all** output/model-affecting fields, membership, evidence, cutoffs and exclusions. Another artifact format needs a new version with canonical logical checksum rules. Retain every raw rejected version privately; publish only aggregates for review. Prevent family revisions crossing split blocks, require mature contiguous chronology per ML-A, and do not substitute random splits when chronology fails.

## Storage and retention recommendation

Repository R2 patterns exist for other government-data artifacts (`services/wra_flood_artifact.py` names `proptech-government-data`). They do not establish an approved PLVR bucket, object lock, credentials or existing backups. Use ignored local `data/raw/plvr/ml-foundation/` and `data/processed/plvr/ml-foundation/` during bounded recovery. **No upload or infrastructure change was made.**

For a later approved object store, proposed relative keys are:

```text
ml/plvr/v1/raw/<source_release_id>/<archive_sha256>/archive.zip
ml/plvr/v1/schemas/<schema_sha256>/<schema-member-name>
ml/plvr/v1/ledgers/<ledger_sha256>/release-ledger.json
ml/plvr/v1/staging/<staging_version>/<staging_sha256>/occurrences.jsonl
ml/valuation/v1/<dataset_version>/<dataset_checksum>/dataset.jsonl
ml/valuation/v1/<dataset_version>/<dataset_checksum>/manifest.json
ml/valuation/v1/<dataset_version>/<dataset_checksum>/exclusions.jsonl
```

These are proposals, not keys observed in an existing PLVR store. Release IDs are sanitized object-key components; manifests bind every checksum/member and ledger version. Require create-only immutable content, access control for IDs/address/detail/exclusion data, verified restore tests, and retention of source/schema/ledger/exclusion/build/dependency artifacts for every retained dataset and superseded version. ML archival retention must be independent of the serving DB's rolling 36-month retention; do not allow serving pruning to erase inputs for a retained research artifact. Formal retention duration/object-lock approval remains a prerequisite, rather than an unsupported claim about current architecture.

## Validation, independent review and scope

Focused verification covers geography variants/conflicts/historical names/malformed labels, valid/invalid calendar precision and floors, full-rights/use restrictions, parking absence/presence/ambiguity/missing fields, Decimal conversion and target invalids/tolerance, transaction-month age, source exclusion, occurrence collisions, duplicate/republication/correction/cancellation/as-of behavior, immutable metadata conflicts, count reconciliation, contracts/formal schemas, archive integrity, JSONL bounds, CLI privacy/input immutability and deterministic order.

Independent review identified four Important classes: arbitrary-source admission, cross-family physical locator conflicts (including a missing-ID bypass), contradictory release/member metadata before cutoff selection, and under-specified manifest/source validation. Each was reproduced with a failing test and fixed. No production-code edits were needed. Final review and verification results are recorded in the follow-up gate and final delivery.

No production valuation/API/UI/provider/Docker/infrastructure/migration code changed. No dataset, raw ZIP, database dump, credential or model artifact is committed. No training package was installed, model was trained, production data mutated, source uploaded, branch pushed/rebased/merged or deployment performed.

The final follow-up remains **BLOCKED** because real B1–B5 evidence and real-release B6 integration are still absent. ML-A can now be re-run narrowly with repeatable foundation evidence; it cannot pass on fixture results alone.
