# ML valuation source recovery and cohort proof v1

## Executive verdict

**BLOCKED. ML-B may not begin. Approved cohort: zero rows and no geographic/time/property scope.**

Starting SHA: `b735c52f698de0355539cdcff170e3ccde5f8d7b`; branch: `research/ml-valuation-source-recovery-v1`. Initial HEAD equalled origin/main and the worktree was clean. Prior ML-A/foundation reports and contracts were read and reused unchanged. The legacy counts (451,672 rows, 351,286 type proxies, 115,113 invalid city/district pairs) are historical audit evidence, not a fresh recount or repair.

Two of the 17 previously recorded official archives were recovered with exact historical hashes. A bounded Taipei/New Taipei audit preserves 37,669 main records and 159,995 detail records. Structural residential filters reach 13,028 rows; all lack defensible full-rights evidence. The existing identity-first foundation audit independently excludes all 37,669 for unverified lineage. Historical availability, dwelling and area-basis evidence also remain unavailable. Matching empty training outputs cannot establish readiness.

## Source recovery and checksum proof

All 17 expected identities, filenames, labels, official URLs, sizes and hashes were read from the existing ledger before downloading. One bounded metadata probe per entry completed first. Only the earliest/latest quarterly packages were selected to prove exact bytes and inspect schema/time differences without mass acquisition. Ten other quarterly endpoints remain potentially recoverable but not checksum-verified; no narrower ready cohort justified downloading them now.

| Source | Expected bytes | Probe bytes | Recovery | Checksum |
|---|---:|---:|---|---|
| current-20260811 | 1,388,987 | 1,036,247 | SOURCE_CHANGED | UNVERIFIABLE |
| history-20260701 | 14,661,814 | 441 | SOURCE_CHANGED | UNVERIFIABLE |
| history-20260711 | 16,324,679 | 441 | SOURCE_CHANGED | UNVERIFIABLE |
| history-20260721 | 16,233,603 | 441 | SOURCE_CHANGED | UNVERIFIABLE |
| history-20260801 | 14,505,303 | 441 | SOURCE_CHANGED | UNVERIFIABLE |
| season-112S3 | 14,876,099 | 14,876,099 | RECOVERABLE_EXACT | EXACT_MATCH |
| season-112S4 | 16,714,295 | 16,714,295 | RECOVERABLE_BUT_IDENTITY_UNCERTAIN | UNVERIFIABLE |
| season-113S1 | 16,498,147 | 16,498,147 | RECOVERABLE_BUT_IDENTITY_UNCERTAIN | UNVERIFIABLE |
| season-113S2 | 19,127,935 | 19,127,935 | RECOVERABLE_BUT_IDENTITY_UNCERTAIN | UNVERIFIABLE |
| season-113S3 | 20,978,409 | 20,978,409 | RECOVERABLE_BUT_IDENTITY_UNCERTAIN | UNVERIFIABLE |
| season-113S4 | 16,051,231 | 16,051,231 | RECOVERABLE_BUT_IDENTITY_UNCERTAIN | UNVERIFIABLE |
| season-114S1 | 13,718,336 | 13,718,336 | RECOVERABLE_BUT_IDENTITY_UNCERTAIN | UNVERIFIABLE |
| season-114S2 | 14,868,369 | 14,868,369 | RECOVERABLE_BUT_IDENTITY_UNCERTAIN | UNVERIFIABLE |
| season-114S3 | 15,018,542 | 15,018,542 | RECOVERABLE_BUT_IDENTITY_UNCERTAIN | UNVERIFIABLE |
| season-114S4 | 13,872,186 | 13,872,186 | RECOVERABLE_BUT_IDENTITY_UNCERTAIN | UNVERIFIABLE |
| season-115S1 | 14,252,348 | 14,252,348 | RECOVERABLE_BUT_IDENTITY_UNCERTAIN | UNVERIFIABLE |
| season-115S2 | 14,705,972 | 14,705,972 | RECOVERABLE_EXACT | EXACT_MATCH |


Totals: **2 RECOVERABLE_EXACT; 10 RECOVERABLE_BUT_IDENTITY_UNCERTAIN; 5 SOURCE_CHANGED; 0 NOT_FOUND; 0 UNKNOWN**. Checksums: **2 EXACT_MATCH; 15 UNVERIFIABLE; 0 downloaded HASH_MISMATCH; 0 RECOVERED_NO_PRIOR_HASH**. Fifteen exact historical objects remain locally absent. Metadata classification is a present observation: four history URLs returned 441-byte HTML and the moving current URL advertised changed size. This does not prove permanent historical loss or a downloaded hash mismatch. Same filename and matching size never establish exact identity.

- 112S3: 14,876,099 bytes, SHA-256 `4d9fa7be16bc9aba99e79c0f86ca27b32f46755de04e98e1dd2c8d8297b466c1`; current verified retrieval finished `2026-10-07T12:42:51.542987+00:00`.
- 115S2: 14,705,972 bytes, SHA-256 `6b4c148bad106a235dddf214001d605ff9ffa45ac50561f7125c6d7fa795d4da`; current verified retrieval finished `2026-10-07T12:42:54.766874+00:00`.

The machine [source manifest](valuation-source-recovery-manifest-v1.json) preserves every expected hash and URL, actual hashes/paths, request metadata, original retrieval claims, schema/member identity and explicitly unknown availability. Its historical ledger canonical hash remains `8423f6ec5c7149bdc131878c477e58e325075016237093334067f5055af84d42`. Exact archives passed checksum, ZIP CRC and required-package/schema validation. No newer object substitutes for a missing historical one.

Acquisition accounting: 17 bounded probes, two selected archive downloads and one unintended successful duplicate 112S3 download during review. The review test used an ignored basetemp inside the allowed acquisition root, so its assumed invalid destination passed. The duplicate started `2026-10-07T12:53:29.904145+00:00`, finished `2026-10-07T12:53:33.051442+00:00`, and matched the same 112S3 hash. It adds no source identity or cohort evidence. The fixture now uses a guaranteed outside-root destination and a NoNetwork transport. No failed download was retried. Original private attempt records remain preserved. A disposable schema-export request used `MANIFEST.CSV` after successful acquisition; correcting it to actual `manifest.csv` required no download retry. One official download page and its advertised history-list endpoint were inspected once; neither supplied the missing historical bytes. No crawl or brute-force expansion occurred.

## Schema semantics and strict parsing

Both packages contain the same four reviewed schema identities. Associated `manifest.csv` binds each member to its schema and county; `build_time.xml` supplies registration/contract windows, not publication instants. Sixteen scoped main/detail CSV members were read completely. UTF-8 BOM handling, exact headers, one exact English descriptor row, blank-record counts, CSV field-count failures and physical line/record locators are explicit. Malformed records are preserved/excluded; syntax/encoding/schema failures abort rather than emit partial success.

| Schema member | SHA-256 |
|---|---|
| schema-build.csv | `2d77ea26d2470eb8db72791e62c0720c459a4b866ac5649edbafd686328cd116` |
| schema-land.csv | `77e2a663340c7ecefd280dad742c634871b6664b1761accedeb9dbd23fd31158` |
| schema-main.csv | `6103a05ac97f9b308d346d6a8b038d022ff5fbbfbbd090dccded77e03377d12a` |
| schema-park.csv | `97eb5f6523255a9c8049b905368c02e2c53380b4ee1d2d8bea8cbae9e37b745e` |


| Meaning | Exact recovered source fields | Eligibility interpretation |
|---|---|---|
| Date / completion | 交易年月日; 建築完成年月; detail 建築完成日期 | Strict ROC parser; preserve precision; no current-year age |
| Target / use / type | 交易標的; 主要用途; 建物型態 | Separate exact predicates, never type-as-use |
| Transferred area / price / unit price | 建物移轉總面積平方公尺; 總價元; 單價元平方公尺 | Registered transferred sqm; NTD; unit price diagnostic |
| Floor | 移轉層次; 總樓層數; detail 建物分層 | Strict single above-ground floor; 28,529 diagnostic valid / 9,140 ambiguous |
| Counts / rights | 交易筆棟數; detail 移轉情形; land 權利人持分分子/分母 | Land fractions exist; whole-dwelling building fraction/identifier absent |
| Parking | 車位類別; 車位移轉總面積平方公尺; 車位總價元; park 車位價格/車位面積平方公尺 | Main/detail/count/notes agreement required |
| Special conditions / identity | 備註; 編號; 移轉編號 | Notes cannot attest absence of special terms; IDs stay private |

Full raw-field nonblank counts are in [aggregate evidence](valuation-source-recovery-evidence-v1.json). The [official MOI dataset catalog](https://data.gov.tw/dataset/25119) documents these source families; the exact embedded schemas, not legacy normalized columns, bind this audit.

## Main/detail join proof

The join key is **archive SHA-256 + sale county member family + raw 編號**. It is release-local and county-local; never a nationwide assumed key. All main keys in this scope are present and unique, all detail keys parse completely, and zero orphan detail rows were observed. Main-to-detail relationships are zero-to-many, not one-to-one. Repeated identical detail records are retained, counted and never used to multiply the main cohort.

| Release / county | Main | Building | Land | Parking | Repeated detail excess (B/L/P) |
|---|---:|---:|---:|---:|---|
| 112S3 / 臺北市 | 6,391 | 14,014 | 9,685 | 2,883 | 130 / 23 / 645 |
| 112S3 / 新北市 | 14,143 | 30,089 | 20,694 | 7,547 | 198 / 30 / 850 |
| 115S2 / 臺北市 | 5,607 | 12,981 | 8,384 | 3,437 | 269 / 14 / 1116 |
| 115S2 / 新北市 | 11,528 | 26,858 | 16,624 | 6,799 | 426 / 7 / 857 |


Combined record counts: main 37,669; building 83,942; land 55,387; parking 20,666; total 197,664. Each join's full cardinality histogram and missing-detail counts are recorded in evidence. Missing parking detail alone proves nothing; missing building evidence, nonunique key, malformed/incomplete details or disagreements fail closed.

## Residential use, transaction target, rights and dwelling

Exact raw `主要用途 = 住家用` occurs in 24,771 of all main records; 5,029 uses are blank. After day-valid/exact-target filtering, 13,573 pass residential use, and 13,028 pass supported apartment types. `住宅大樓`, `華廈` and `公寓` are building types, not use evidence. Mixed/commercial/unknown uses exclude.

Raw targets: `房地(土地+建物)` 16,689; `房地(土地+建物)+車位` 15,417; `土地` 4,230; `建物` 95; `車位` 1,238. The offline foundation exact classifier is reused: only exact existing-building/no-parking sale target proceeds; land-only, parking-only, mixed-parking and ambiguous targets exclude. No rental/presale file family was selected. Production's previously documented mixed-token defect is untouched; it is not reused for ML.

Full rights and one residential dwelling remain **UNPROVEN**. Building details contain `全筆移轉` 31,629, `持分移轉` 52,199 and blank 114; land details contain 3,003 whole and 52,384 fraction transfers. Shared/common land/building entries can have fractions and multiple rows: neither one building row nor `全筆移轉` on a row proves whole-dwelling rights. Blank notes, one address, one building count or one target also cannot attest this. A future eligible record must carry authoritative full-rights and one-dwelling evidence under the existing foundation context contract. All ambiguous cases exclude. No new positive attestation was manufactured.

## Parking proof

Diagnostic counts over **all raw main records**, not an approved residential intersection:

| Classification | Rows |
|---|---:|
| NO_PARKING_CONFIRMED | 13,433 |
| PARKING_PRESENT | 16,662 |
| PARKING_SEMANTICS_AMBIGUOUS | 7,311 |
| UNKNOWN | 263 |

No-parking requires explicit main parking count zero, numeric area/price zero, blank parking type, complete scoped detail parsing, a unique main join, no parking detail and sufficient non-parking building-use evidence. Any parking token in main notes/building descriptions, conflicting positive detail/count evidence, or missing building-use descriptions withholds confirmation. Blank prices are never interpreted as zero. Tests cover zero, one/multiple spaces, price-only, area-only, missing details and disagreement. Only confirmed absence could enter v1; rights and lineage prevent any actual admission here.

## Area and target proof

`建物移轉總面積平方公尺` is **registered transferred building area**, which may include private, shared/common and ancillary portions. It is not interior, usable or net living area. The [official MOI FAQ](https://lvr.land.moi.gov.tw/R11/jsp/qa.jsp) explains registered-area and separately reported parking price/area unit-price treatment. The detail schemas do not establish the full-rights/dwelling area basis required by the current target contract.

Raw positive finite price/area diagnostic: 33,427 positive pairs and 4,242 invalid/nonpositive pairs. No approved real target is produced. The existing tested contract is `area_ping = Decimal(area_sqm) * Decimal("0.3025")`, then `unit_price_ntd_per_ping = total_price_ntd / area_ping`, then natural logarithm, only for positive finite values and evidenced rights/area/confirmed no-parking. No unit guessing or gross parking-price subtraction is performed. Foundation tests verify bad/missing/negative/zero numeric inputs, NaN/infinity and parking contamination fail closed. Raw numeric positivity alone does not prove parking-exclusive total property price.

## Date, age and source geography

37,668 transaction dates parse with day precision; one is invalid and excludes. No observed month-only transaction is upgraded to a fake day. Foundation tests cover month-only cutoff ambiguity. Transaction-time age diagnostics parse for 24,165 records and are unavailable for 13,504; precision is month-based where supplied. Age remains **DEFERRED**, with no age feature output. No wall-clock year participates in historical transformation.

Source county is pinned by embedded manifest and `a_lvr_land_a.csv` = 臺北市 / `f_lvr_land_a.csv` = 新北市, then raw district is validated against the existing versioned registry. All 37,669 pairs are canonical: Taipei 11,998 across 12 districts; New Taipei 25,671 across 29 districts. Raw source cells and member/registry identity remain in private staging; raw/source county, raw district, normalized county/district and normalization reason/version are explicitly preserved in each private exclusion record together with all three identity levels. Aggregate district counts are recorded; no district-only county repair occurred. No historical registry ambiguity was observed here. Existing municipality rules keep 新竹市/嘉義市 city-level-only observations ineligible for Model A and never invent a district. They are regression-tested, not newly observed in this two-member scope. The prior 115,113 invalid legacy pairs were not repaired.

## Identity, revisions and availability

Foundation identity functions generate provisional `transaction_family_id` (county + official ID), content-based `source_record_version_id`, and physical occurrence identity (archive/member/record locator). All 37,669 occurrences remain preserved. There are 37,669 distinct provisional families; zero repeated main families, exact-main republications, changed-payload families or observed collisions in these two selected packages. Repeated detail rows are a separate phenomenon.

Zero observed repeats is not proof of global identifier namespace stability, revision completeness or absent cancellations. No source-attested supersession/cancellation examples were found; `cancelled = false` is a parser default, not a negative cancellation attestation. Existing `select_as_of`/revision tests cover exact republication, later corrections, post-cutoff changes, cancellation, collisions and distinct transactions sharing rounded facts. Unproved identity evidence remains null and actual foundation selection fails closed.

For every source `release_published_at`, `public_available_at` and `system_available_at` remain **null**. Historical availability is authenticated for **0 of 17 sources**. Exact two retrievals provide current HTTPS observation upper bounds only; the other fifteen have no archive-retrieval bound. Previously recorded August retrieval strings are retained as unauthenticated historical claims, never promoted to public availability. Release labels, Last-Modified/ETag, registration-window XML and official schedule do not establish historical first publication. Effective transaction day is distinct from availability. No later correction can rewrite an earlier cutoff without proof.

## Real cohort funnel and coverage

This structural semantic funnel profiles physical records and unique release-local keys; its identity stage is not a namespace/revision approval. The unchanged foundation audit applies identity/availability first and independently rejects all 37,669 as `lineage_unverified`. Both outputs are published so the diagnostic ordering cannot be mistaken for actual trustworthy selection.

| Stage | Input | Accepted | Excluded | First reason |
|---|---:|---:|---:|---|
| schema | 37,669 | 37,668 | 1 | TRANSACTION_DAY_REQUIRED: 1 |
| identity | 37,668 | 37,668 | 0 | — |
| geography | 37,668 | 37,668 | 0 | — |
| target | 37,668 | 16,689 | 20,979 | INVALID_TARGET: 20,979 |
| use | 16,689 | 13,573 | 3,116 | UNKNOWN_OR_NONRESIDENTIAL_USE: 3,116 |
| type | 13,573 | 13,028 | 545 | UNSUPPORTED_PROPERTY_TYPE: 545 |
| rights | 13,028 | 0 | 13,028 | RIGHTS_UNPROVEN: 13,028 |
| dwelling | 0 | 0 | 0 | — |
| parking | 0 | 0 | 0 | — |
| price_area | 0 | 0 | 0 | — |
| revision | 0 | 0 | 0 | — |
| pit | 0 | 0 | 0 | — |


First exclusions sum to 37,669, each stage conserves input = accepted + excluded, and every occurrence has a stable first/all-reasons private exclusion entry. After rights excludes all 13,028 survivors, later zero-input stages are **not positive proofs** of dwelling, parking, target/area, revision or PIT.

Final trustworthy cohort **0**. Approved cities/districts/months/types and lag distribution are empty/undefined. Raw scope only: two quarterly nationwide packages, processed only Taipei/New Taipei members. Raw dates span 2013-06 through 2026-06 with sparse old effective dates, not a complete continuous historical panel. Evidence contains every raw month/district/type histogram and missingness. Raw types: 18,649 住宅大樓, 7,122 公寓, 5,465 華廈 and 6,433 unsupported. These are diagnostic coverage, not nationwide readiness or approved type counts. Availability lag cannot be measured without authenticated publication time.

## Chronological viability and baseline readiness

**BLOCKED.** No chronological TRAIN / VALIDATION / CALIBRATION / TEST dates are chosen, and split output is empty. Calibration remains separate in the inherited contract. Two registration-window packages plus zero eligible rows cannot prove mature contiguous evaluation history. No random split is substituted. Historical global median, district/type median and comparable baselines are all **not ready** at a defensible point-in-time cutoff. No model or baseline was trained.

## Two-build reproducibility and storage proof

Two independent processes built fresh `delivery-build-a` and `delivery-build-b` from the same exact ZIPs, original ledger, pinned code/registry/source contract and explicit configuration. Logical snapshot and cutoff are `2026-10-07T12:58:22.826828+00:00`; this is configuration, not a fabricated shared process-completion time. Per-execution wall-clock timestamps are excluded. Python version/code/registry/schema hashes are bound in the [proof build manifest](valuation-source-recovery-proof-build-manifest-v1.json).

All **10 files match byte-for-byte**: source/proof manifests, evidence and seven JSONL outputs. Canonical JSON object hashes below exclude presentation whitespace/trailing newline; evidence separately reports actual file-byte hashes. Target/features/membership/splits contain zero bytes: their matching empty SHA proves only deterministic emptiness, not a nonempty dataset build.

| Artifact / canonical object | SHA-256 |
|---|---|
| Source manifest (canonical JSON) | `be20e41e5fe78f9be7860122094060d9d7e4bf07a5711167033e5f0bcfd3ed27` |
| Proof build manifest (canonical JSON) | `fc1d9df39554cf51694bbc87de6220c19796b39be53221cc63da266d7f7c7e47` |
| cohort-membership.jsonl (file bytes) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| exclusions.jsonl (file bytes) | `a7702c0dcc6223ac243c2eafeb730cf026f5cb6b0c6806194011f2086fef9618` |
| features.jsonl (file bytes) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| occurrences.jsonl (file bytes) | `36fbfc5b266fc8d99881cbf41f2481de8e74dc7240b6cd472684f780cff2aea6` |
| source-records.jsonl (file bytes) | `449c16c4c8a987b4a0523e5cd91307365d6a8695ce28f0afe871a5610144a681` |
| splits.jsonl (file bytes) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| targets.jsonl (file bytes) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |


Both exact ZIPs were copied into ignored local restore paths and rehashed successfully. Staging/exclusions regenerate from immutable input bytes; the empty candidate result regenerates, but usable final dataset regeneration remains unproved. No production object-store upload occurred. Eventual store contract: private content-addressed source keys containing SHA-256, create-only immutable writes, independently hashed download/restore, manifests binding archive/member/schema/config hashes, retention and restore separate from serving-data pruning, and access controls excluding credentials/raw rows from Git. Durable independent retention/restore is still a prerequisite, not a provisioned service claim.

Offline reproduction from preserved private acquisition evidence (use a new output directory every run):

```powershell
$env:PYTHONUTF8='1'
python -m scripts.ml.source_recovery
python -m scripts.ml.audit_source_recovery --output artifacts/ml/plvr-source-recovery/new-proof --cutoff 2026-10-07T12:58:22.826828+00:00 --observation-at 2026-10-07T12:58:22.826828+00:00
python -m pytest tests/test_ml_source_recovery.py tests/test_ml_plvr_raw_parser.py tests/test_ml_dataset_foundation.py -q
```

The archive paths and `preflight.json`/`downloads.json` are ignored local inputs; cloning this commit alone cannot restore raw sources. Build destinations must remain ignored, and existing destinations reject overwrites.

## Validation, privacy and independent review

Focused ML tests: **122 passed** (89 unchanged foundation regressions + 13 recovery tests + 20 parser/real-detail tests). Full repository suite: **2,969 passed, 31 skipped, 0 failed**, one existing Starlette TestClient deprecation warning. An initial full run exposed missing existing locked frontend dependencies and Windows subprocess encoding; local `npm ci --ignore-scripts` with workspace-local cache plus `PYTHONUTF8=1` resolved them without tracked application/dependency changes. No CatBoost, LightGBM or XGBoost was installed.

Manifest/ledger/schema identity, per-stage conservation, input/output checksums, two clean builds, local restores and aggregate privacy are verified. Raw ZIPs, all main/detail cells, addresses/official transaction IDs, occurrence/exclusion records and JSONL outputs remain under ignored `artifacts/ml/plvr-source-recovery/`. Committed source/release IDs and hashes are archive-level metadata, not raw transaction identifiers. Tests use tiny synthetic values only. Tracked paths are restricted to ML scripts/tests/docs and inspected for large/raw files.

Independent review found and fixed two Important issues: parking notes/blank building-use descriptions could falsely confirm absence; retrieval manifest validation accepted invalid HTTP/timestamps/attempt metadata. Red tests preceded fixes. The outside-root fixture/network incident and minor conditional availability wording are also fixed. Re-review of code, aggregates, final human reports and final provenance outputs found **0 remaining Critical/Important findings**. Evidence records the final disposition. No production logic, provider API, database/migration, UI, R2, deployment or model artifact changes are included.

## Remaining blockers and final recommendation

| Blocker | Evidence gained | Exact remaining requirement |
|---|---|---|
| B1 | Raw schemas/use/target/parking diagnostics | Authoritative full residential rights, one dwelling, registered-area basis and clean target |
| B2 | Exact two current retrievals; unknown dates explicit | Historical public availability, namespace and ordered revisions/cancellations |
| B3 | Two-member county + district reconstruction | Namespace proof; separate source-backed legacy geography repair if needed |
| B4 | Exact two archives, local restore, deterministic staging | Missing fifteen exact objects as necessary; durable independent retention; nonempty dataset restore |
| B5 | Real conserving 37,669-row audit | Nonempty eligible volume, mature contiguous history and chronological four-way viability |
| B6 | Strict real parsing/details/date and fail-closed gates | Evidence-qualified real target/features/splits and nonempty two-build proof |

Minimum next repair: obtain authoritative building-rights/dwelling/area evidence and authenticated historical availability/namespace/revision evidence first. If the official material cannot support the current target, explicitly revise the research question rather than invent attestations. Then recover only necessary contiguous ledger releases, prove a nonempty cohort and PIT baselines, and repeat nonempty dataset/restore checks. **Final gate: BLOCKED; ML-B forbidden; approved experiment scope: none.**

New decision: [source-recovery readiness follow-up](valuation-dataset-readiness-source-recovery-followup-v1.md). Historical ML-A/foundation reports are unchanged. The sole delivery commit is `research: recover ml valuation sources and prove cohort`; its SHA and clean status are reported after creation. No push, merge, deployment or training is authorized by this report.
