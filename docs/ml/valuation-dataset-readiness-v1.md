# ML-A — Residential valuation dataset readiness v1

Audit date: **2026-10-07, Asia/Taipei**. Gate identifier: ML-A (the supplied request also calls this E9A). Repository: `ryanwu566/proptech-ai-copilot`. Workspace: `C:\Projects\proptech-ml-dataset-readiness`.

Starting commit: `79e96f6baf94ea3b99151c219d79c58b3ba66f4d`. Branch: `research/ml-valuation-dataset-readiness-v1`. Initial `git status --short` was empty; HEAD equalled the local `origin/main` reference. No fetch was performed, so this verifies the requested local reference equality, not a newer remote state.

## Executive verdict

**BLOCKED. ML-B may not begin.**

The accessible database contains **451,672 official PLVR transactions**, but its normalized schema cannot establish a parking-exclusive residential target, genuine residential use, complete transaction identity, historical release availability, or reproducible historical row versions. This is a semantic and temporal gate failure, not a shortage-of-rows conclusion.

A strict no-parking apartment cohort is a defensible proposed contract after raw-source and release repairs. Its usable count is **unknown**, not 351,286: that number is only the count of three building-type labels. No narrower trustworthy cohort can presently be demonstrated from the available columns.

The audit created documentation and aggregate evidence only. It did not train or evaluate models, install ML packages, build `services/valuation_ml`, change APIs or production valuation, mutate databases, refresh providers, reactivate the paused GREEN project, download transaction archives, push, merge, or deploy.

The companion [aggregate evidence](valuation-dataset-audit-evidence-v1.json) contains every observed city, district, building-type and month count, metadata counts, duplicate diagnostics, local-source inventory and a copy of historical artifact metadata. It contains no transaction rows, addresses, credentials, model artifacts, or training dataset.

## Evidence boundaries and source inventory

Evidence classes used throughout:

- **Verified now:** bounded, read-only database aggregate/schema queries or local inspection at the starting commit.
- **Historical evidence:** existing dated reports and metadata; their recorded counts are not newly recounted source rows.
- **Proposed contract:** future offline behavior; its design does not establish that build inputs exist.

Database queries used the connected Supabase project named `proptech-valuation-db`, `BEGIN READ ONLY`, and statement timeouts of at most 20 seconds. Results were aggregates and column metadata only. Queries ran in separate transactions; they are not an immutable, atomic row snapshot. The independent count/profile/district queries agreed on the official count. The first count observation was 2026-10-07 12:23:21 Asia/Taipei (04:23:21 UTC); the count and lineage-metadata observation timestamps are retained in the JSON. Individual profile, duplicate and district query timestamps were not retained; those observations are dated to this audit day only.

| Source/store | Verified status | Role and limitation |
| --- | --- | --- |
| MOI Department of Land Administration PLVR sale-main Open Data | Authoritative transaction source; official catalog verified online | Free release archives, with county sale-main CSVs and source schemas; not the demo CSV |
| BLUE Supabase `public.real_price_transactions` | 451,744 rows: 451,672 official + 72 `real_price_sample` | Accessible normalized transaction store; missing critical raw semantics and release joins |
| `valuation_import_runs` | 57 rows, all completed | Import summaries; not per-row source manifests |
| `market_district_period_aggregates` | 11,018 rows | Derived market read model, not individual valuation labels |
| Migration 010 generation tables | Tables exist; 0 generations, 0 generation transactions, 0 active pointers | Schema availability does not prove a populated authoritative generation |
| Migration 008 rich market release/artifact/transaction tables | `official_market_releases`, `official_market_artifacts`, `market_transactions` absent in accessible BLUE | Richer contract is represented in code/DDL; no usable data in these tables was demonstrated |
| Connected `proptech-valuation-green` | Project is INACTIVE | No query/restart attempted; current GREEN row count and schema population remain unverified |
| Local official ZIP / SQLite / Parquet transaction sources | None under `data/` or `artifacts/` | Raw archives and clean-shadow row database are unavailable in the authorized workspace |
| `data/real_price_sample.csv` | 72 rows, 2 cities, 3 districts, 3 roads | Explicit demo source; exclude all rows from ML and baselines |
| Local ignored `artifacts/plvr_source_manifest.json` | 17 artifact descriptions; metadata hash recomputed and matched | Filenames/checksums describe archives; archive bytes are absent |
| R2 / government-data object storage | No PLVR archival key contract found; R2 endpoint/key/bucket environment absent | Existing R2 code for demographics, hazards and village data does not prove historical PLVR archives exist |

The official catalog identifies the national sale data and packaged schema files. The supply website distinguishes static release downloads from its dynamic transaction query service. These are evidence of source authority and release behavior, not evidence of repository-specific usable counts. [MOI sale-data catalog](https://data.gov.tw/dataset/25119), [MOI supply-system description](https://plvr.land.moi.gov.tw/Index).

`VALUATION_DATABASE_URL` and `COMPACT_GREEN_DATABASE_URL` were not set locally. A generic PostgreSQL `DATABASE_URL` was present but was not used or printed; project identity was resolved through the connector. Hosted runtime configuration and its active provider flag were not inspected, so project availability must not be presented as proof of the deployed application's current backend selection.

### Actual ingestion and storage paths

1. [PLVR importer](../../scripts/import_plvr_to_postgres.py), using [normalization](../../services/plvr_import_service.py), reads local sale-main CSV/ZIP inputs. It maps county filenames, converts transaction dates to months, rounds area/prices, builds v2 hashes and writes legacy transaction rows. It excludes detail `*_park.csv`, `*_build.csv` and `*_land.csv`, rental and presale inputs.
2. [Clean-shadow rebuild](../../services/plvr_clean_shadow_rebuild.py) and the acquisition/build scripts verify official artifact hashes, keep raw date/source-row identity metadata and derive a local SQLite shadow. They still call the legacy valuation normalizer for price, area, floor and age. The SQLite row artifact is absent here.
3. [Official market pipeline](../../services/official_plvr_market_pipeline.py) defines release metadata, exact transaction dates, parking fields, special-transaction flags and NTD units. Its publisher corresponds to migration 008. These tables are absent in the accessible database. The richer dataclass also omits main use, and completion/floor aliases are not preserved as its corresponding normalized fields.
4. [PLVR market bridge](../../services/plvr_market_aggregate_service.py) derives administrative monthly averages from the normalized transaction store. [CSV market importer](../../scripts/import_market_data.py) is another aggregate path. Neither yields raw target semantics or historical availability.
5. [Updater skeleton](../../scripts/update_valuation_data.py) explicitly does not implement automatic ZIP ingestion. The refresh-market-read-model workflow invokes an aggregate refresh; it is not evidence of continued historical transaction acquisition.

A synthetic read-only probe also confirmed that the richer market pipeline's `classify_transaction()` classifies the standard `房地(土地+建物)` label as `land`, because it checks the land token before resolving mixed land/building sales. This audit leaves production code untouched. Reusing that pipeline for a future residential builder requires a separately tested classification repair.

## Existing production comparable estimator

Reviewed [estimate_property and helpers](../../services/valuation_service.py), [Postgres retrieval](../../services/valuation_providers/postgres_provider.py), [GREEN retrieval](../../services/compact_green_query.py), [valuation routes](../../backend/api/routes_valuation.py), [result validation](../../services/valuation_result_contract.py), community matching and the transaction/market DDL and migration registry.

The current production foundation is explainable comparable sales:

- Official mode selects a configured Postgres provider; the CSV requires explicit demo mode. The inactive PLVR adapter is a wrapper, not the authoritative ingestion route.
- For normal requests containing city and district, BLUE immediately retrieves one district pool of up to 200 rows; it ranks by road/district/type, area/age differences, optional coordinates and recency. Its road/district/city/all fallback query loop applies only to incomplete geographic requests. GREEN uses a frozen generation, geography dictionaries, a generation maximum period and a 200-row district cap.
- The official candidate pool requires `source = official_plvr_opendata` and finite positive area, price and unit price. It chooses at least three same-road transactions, otherwise at least three other-road district transactions, otherwise a city-labelled scope within the already retrieved rows. For a normal district request, that last branch does not fetch a wider city pool. This is not a residential-use or parking eligibility test.
- Building-type aliases normalize long official apartment labels. Similarity combines geography, probable community, building type, area, age, distance and a wall-clock recency score. Weights have a 0.05 floor.
- IQR filtering uses P25/P75 ± 1.5 IQR for at least four candidates, with a preserve-official branch. Final ordering prioritizes scope/type/area/period before similarity; up to ten comparables are retained. If filtering leaves fewer than three, the pre-filter scored pool is retried.
- The midpoint is the mean of weighted mean and weighted median, rounded to 0.1 **萬元/坪**. Total estimates multiply this by subject area. Public range bounds use min(P25, midpoint) and max(P75, midpoint), then multiply by area.
- Official actionability requires validated provenance, at least three comparables, positive finite estimates, ordered positive ranges and a bounded confidence score. These runtime checks do not establish ML label purity, historical availability, or calibrated uncertainty.

BLUE excludes official months after the current UTC month; service checks use `date.today()`. GREEN retrieval uses the frozen generation maximum. Neither exposes prediction-time publication/version filtering. Calling this API today with a past subject date would therefore be an invalid historical baseline. Its P25/P75 comparable range is not a conformal interval. The estimator, actionability, selection, active price and saved commercial evidence remain unchanged.

## Actual verified row counts and coverage

### Funnel and quality observations

| Observation | Verified count | Interpretation |
| --- | ---: | --- |
| All legacy transaction rows | 451,744 | Includes demo rows |
| Official candidates | 451,672 | Sale-building import population, not proven residential |
| Three-type residential proxy | 351,286 | Building-type allowlist only |
| After genuine residential-use filter | Unknown | Main use, ownership and building-count semantics absent |
| After exact target-quality filter | Unknown | Full raw price/area basis absent |
| After proven no-parking filter | Unknown | Parking presence/count/price/area absent |
| Distinct official legacy dedupe hashes | 451,672 | No duplicate hashes; not proof of distinct business transactions |
| After official identity/revision deduplication | Unknown | Official IDs and version history absent |
| Point-in-time training-ready rows | Unknown | No row availability/version contract |
| Nonpositive stored area/total/unit price | 0 | Positivity is insufficient |
| Stored unit prices outside importer 1–500 萬元/坪 bounds | 0 | Bounds are a code policy, not proof of physical validity |
| Gross total / transferred area differs from stored unit price by >1% | 76,210 | Mixed basis or rounding/import/revision risk; cannot attribute every mismatch to parking |
| Nonpositive/missing-as-zero floor | 102,720 | Aggregated before residential filtering |
| Age zero | 8,700 | Unknown completion and new buildings are conflated |
| Identical legacy dedupe-key collision groups | 0 | Does not address corrected rows with changed facts |
| Rounded fact collision groups / rows / excess | 457 / 1,026 / 569 | Same city, district, month, address, type, 2-decimal area/total/unit price; ambiguity, not proven duplicates |

No count is silently substituted for an unavailable funnel stage. All available subgroup counts describe the legacy population, not the proposed clean residential cohort. The 569 excess rows must not simply be deleted: separate real transactions can share rounded facts.

### Geography

There are 21 stored city labels, 539 city/district label pairs and 37,549 city/district/road keys. No accepted 連江縣 row is present.

| City label | Official rows | District labels |
| --- | ---: | ---: |
| 南投縣 | 3,823 | 12 |
| 台中市 | 50,542 | 29 |
| 台北市 | 44,137 | 12 |
| 台南市 | 114,594 | 104 |
| 台東縣 | 1,877 | 9 |
| 嘉義市 | 3,997 | 1 |
| 嘉義縣 | 1,716 | 15 |
| 基隆市 | 7,509 | 7 |
| 宜蘭縣 | 8,138 | 12 |
| 屏東縣 | 9,251 | 29 |
| 彰化縣 | 9,089 | 26 |
| 新北市 | 93,633 | 29 |
| 新竹市 | 6,977 | 1 |
| 新竹縣 | 9,899 | 11 |
| 桃園市 | 36,655 | 97 |
| 澎湖縣 | 375 | 1 |
| 花蓮縣 | 3,636 | 11 |
| 苗栗縣 | 6,078 | 16 |
| 金門縣 | 315 | 5 |
| 雲林縣 | 4,686 | 20 |
| 高雄市 | 34,745 | 92 |

Validation of all 539 aggregate label pairs through the repository's **current** administrative registry found:

| Current-registry category | Pairs | Rows |
| --- | ---: | ---: |
| Canonical county/district labels | 322 | 325,585 |
| Invalid or not district labels | 215 | 115,113 |
| 新竹市/新竹市 and 嘉義市/嘉義市 city-level labels | 2 | 10,974 |

The last two city-level labels correspond to a documented source city-level case; they must not be fabricated into districts. A full district-feature Model A excludes them. The invalid set includes cross-county combinations such as 台南市/中壢區 (5,056 rows). Even a registry-valid pair is only plausible: an erroneous county can share a legitimate district name. Repair must trace source county identity rather than map by district text.

Full per-district counts, type-only proxy counts and registry classifications are in `by_district` in the JSON. Across all groups, min/max counts are 1/11,615; 101 groups have fewer than 30 rows. Largest groups include 新北市/淡水區 11,615, 板橋區 10,596, 新莊區 9,030, 中和區 8,850 and 三重區 8,766. These are counts, not guarantees of cohort eligibility or geographic completeness.

### Building types and transaction coverage

| Stored building type | Official rows |
| --- | ---: |
| 住宅大樓(11層含以上有電梯) | 201,797 |
| 華廈(10層含以下有電梯) | 87,776 |
| 公寓(5樓含以下無電梯) | 61,713 |
| 透天厝 | 100,257 |
| 農舍 | 27 |
| 其他 | 23 |
| 廠辦 | 22 |
| 工廠 | 22 |
| 套房(1房1廳1衛) | 17 |
| 店面(店鋪) | 10 |
| 倉庫 | 6 |
| 辦公商業大樓 | 2 |

Official rows span stored transaction months **2023-07 through 2026-05**, plus **one 2026-10 row**. There are no official rows for 2026-06, 07, 08 or 09. This is a data-store observation, not proof those months had no market transactions.

| Year | Official rows |
| --- | ---: |
| 2023 (Jul–Dec) | 34,899 |
| 2024 | 244,340 |
| 2025 | 159,707 |
| 2026 (Jan–May plus anomalous Oct) | 12,726 |

Full monthly counts are in `official_profile.months`. For context, 2026-01/02/03/04/05 counts are 6,817 / 1,348 / 2,454 / 1,919 / 187. The one October record was already present in June imports; earlier forensic reports matched a source-confirmed future-date anomaly. October's arrival does not establish that its effective date is now valid. Exclude pending source revalidation; do not turn a previously quarantined future row into an eligible label merely because the wall clock catches up.

All-source min/max months are 2023-01/2026-12 because of demo data. Six local demo rows are in future 2026-12; all 72 demo rows are excluded regardless of date. Official import timestamps span 2026-06-07 to 2026-06-08 UTC. This observation does not demonstrate later transaction refresh.

### Historical artifacts are not current usable row data

The later [coverage reconciliation summary](../plvr-coverage-reconciliation-summary-v1.json) records a clean-shadow-v2 rebuild with 1,106,777 raw rows, **517,195 accepted building-sale rows**, 21 cities, 325 geographic units (323 districts plus two city-level units), months 2023-09 through 2026-07 and 9,606 aggregates. It records two resolved official revision groups and ten excess repeated source identities.

Its source manifest describes 17 ZIPs (253,796,255 bytes): seasons 112S3–115S2, history releases 20260701/11/21 and 20260801, and current 20260811. Manifest SHA256 is `18203c6347cd2e7c0fd4f274ec1c6e6b3f49cef8d4f890099a01ccacb9d0aa06`; shadow SHA256 is `2ee0cf968d769a9dd8261031f3f13f6d7c5fcb4c0c33316a22120070806cef57`. The local manifest metadata checksum matches; the ZIP and shadow dataset checksums could **not** be reverified because bytes are absent.

The older clean-shadow-v1 summary reports 501,785 accepted rows and 19 cities. These are different rebuild contracts, not interchangeable counts. The compact GREEN runbook's expected 517,195 facts/evidence rows and 9,606 aggregates are not current verified GREEN counts. Historical v2 coverage is complete only through 2026-05; June/July were partial in that report. Neither the historical building-sale count nor a coverage percentage proves residential/no-parking ML readiness.

## Exact initial cohort contract

Proposed cohort ID: `residential-apartment-no-parking-v1`. This contract is **not currently executable from the legacy table alone**. Apply it only to verified raw sale-main releases, with retained source schemas and subordinate detail joins where needed.

All of the following must hold:

1. Official existing sale, raw transaction target exactly `房地(土地+建物)`; no presale, rental, building-only, land-only or parking-only sale. Missing target is excluded. Do not use token matching as proof.
2. Raw main use exactly `住家用`, subject to the matching release's schema vocabulary. Mixed residential/commercial use, commercial/industrial/agricultural use, unknown use and other vocabularies are excluded pending an explicitly versioned mapping.
3. Building-type family is 住宅大樓, 華廈 or 公寓. Accept only the short label or the exact official aliases already mapped in `normalize_building_type()`: 住宅大樓(11層含以上有電梯), 住宅大樓(11層含以上), 華廈(10層含以下有電梯), 公寓(5樓含以下無電梯). No fuzzy prefix mapping.
4. One dwelling transaction with full rights and one building unit. Retain and parse transaction counts and rights evidence; multi-building bundles, partial rights, ground-right-only interests and ambiguous ownership are excluded. Land-parcel count need not equal one if the dwelling's land shares are clear.
5. Proven no parking: target excludes parking; parsed parking count is zero; parking details and type show no space; area/price contain no positive parking quantity. Blank or zero price alone is insufficient. Blank area/price are accepted only when the source-schema meaning and independent zero-count/no-parking evidence agree.
6. Valid full transaction date from raw source; finite positive raw total price and transferred registered building area; target reconciliation rules below pass.
7. A single unambiguous above-ground transferred floor: integer 1 ≤ floor ≤ total floors ≤ 100. Raw multi-floor, whole-building, basement, blank and unrecognized floor descriptions are excluded; do not use the legacy first-number parser to establish this.
8. Registered transferred area is **5–150 ping inclusive**. Computed unit price is **10,000–5,000,000 NTD/ping inclusive**. These are deliberately narrow v1 scope policies, not claims that all values outside are impossible or invalid. No winsorization, label replacement or IQR cleaning of evaluation targets.
9. Source-proven county/district with versioned administrative semantics and an unambiguous official transaction identity. Exclude city-level-only rows and unresolved county/district or identity conflicts.
10. Raw special-transaction notes are blank and no source/detail flag indicates related parties, auction, renovation/furniture bundles, multiple properties, cancellation or correction ambiguity. Nonblank notes are excluded conservatively as `special_note_requires_review`; blank notes do not independently prove market-normal transactions.
11. Row version, release publication/availability, import batch and raw bytes are traceable and satisfy the temporal contract. Availability is required for historical training/baseline use; it is not imputed from transaction date.

Initial geographic scope is the set of source-proven district pairs with sufficient eligible chronological coverage after all filters. It is not automatically nationwide, not automatically the six municipalities, and not simply the 322 current-registry-valid pairs. No counts per approved geography can yet be promised.

Deterministic funnel order: verify source archive/schema and extract raw identity/availability → select the latest evidenced version as of the applicable cutoff → apply cancellation/conflict state → transaction type/time → residential use/rights → building type → no parking → area/price/target → floor/geography → special-note/other ambiguity → remove repeated occurrences of the selected version. Preserve every raw version, including canceled or cohort-ineligible versions, in the version ledger before cohort filtering. A selected newer version that fails eligibility excludes the logical transaction; never resurrect an older qualifying version. Keep both the first reason in this order and all reasons; each stage records remaining rows and newly excluded rows. Suggested reason codes include `unsupported_source`, `identity_missing`, `availability_unknown`, `cancelled_as_of_cutoff`, `non_residential_use`, `ambiguous_rights`, `unsupported_building_type`, `parking_present`, `parking_unknown`, `invalid_price`, `invalid_area`, `scope_area_limit`, `scope_unit_price_limit`, `unit_basis_mismatch`, `floor_ambiguous`, `geography_unverified`, `special_note_requires_review`, `revision_ambiguous` and `duplicate_version`. An exclusion ledger is part of a future build, not a silent cleanup.

## Target semantics and exact target contract

Target version: `residential-unit-ntd-ping-log-v1`. Area basis: `registered-transferred-building-including-aux-common-no-parking-v1`. Price basis: `whole-rights-land-and-residential-building-sale-no-parking-v1`.

For a row proven to belong to the no-parking cohort:

```text
P = raw 總價元, in NTD (land plus residential building interest)
A = raw 建物移轉總面積平方公尺, in square metres
q = Decimal("0.3025") ping per square metre
area_ping = A * q
residential_unit_price_ntd_ping = P / area_ping
target_log_unit_price = natural_log(residential_unit_price_ntd_ping)
```

Parse finite decimal quantities from raw fields and retain their precision. Compute without pre-rounding; serialize numeric features/target consistently (float64 with a pinned computation contract), and retain raw decimal values for independent checking. Never take the log of 萬元/坪 while labelling it NTD/坪. The legacy stored `total_price` and `unit_price_per_ping` are in **萬元** and **萬元/坪**; multiplying them by 10,000 repairs units but cannot repair unknown parking or area basis.

The official service uses gross total / transferred area when parking is not separately supplied; when both parking price and area are supplied, it subtracts both. Hence an official unit-price field may embed a different denominator from the stored gross area. [MOI unit-price explanation](https://lvr.land.moi.gov.tw/R11/jsp/qa.jsp).

If the raw official per-square-metre unit price U is present and positive, require `abs(U - P/A) <= max(1 NTD/m², 0.001 * P/A)` in the proposed no-parking cohort. This 0.1%/one-NTD tolerance is an explicit v1 QA policy, not an official guarantee; log the discrepancy and reject violations rather than replacing U. If U is missing, compute from verified raw P/A and mark `target_method = gross_total_over_verified_no_parking_area`; missing U is not itself fatal after full basis proof. Present malformed/nonfinite/nonpositive U is excluded. A computed match does not prove no parking.

The legacy normalizer uses an available official unit price, otherwise gross total/area, with no field indicating which formula or parking basis applied. It stores rounded area/prices, drops original unit price and does not check gross-versus-net consistency. The 76,210 mismatch observation is diagnostic only. The richer pipeline uses 3.305785 m²/ping while valuation uses 0.3025 ping/m²; a future builder pins one versioned conversion rather than combining both chains.

This is a **land-and-residential-building package price per registered transferred building ping**, not the building-only construction cost, usable interior price, or a parking-inclusive property total. Subject predictions must use the same area/price basis. An eventual additive ML estimate must not silently be multiplied by a gross parking-inclusive subject area.

## Area semantics

The valuation `area_ping` derives from **建物移轉總面積平方公尺**, not land area, net interior area, or necessarily main-building area. Official guidance describes registered transferred area and warns that unregistered additions can make it differ from physical usable area; common-area and parking registration also varies. [MOI area guidance](https://lvr.land.moi.gov.tw/R11/jsp/qa.jsp).

The proposed v1 denominator includes transferred registered main, auxiliary and allocated common building area; it excludes parking by cohort proof. Do not reinterpret it as 主建物 or indoor-only ping. Preserve separate main/auxiliary/common areas and release-specific definitions when supplied; reconcile totals within source precision. Missing components do not authorize reconstructing them from gross price or unit price. If the no-parking total cannot be validated from source definitions/detail, exclude `area_basis_unresolved`.

The current valuation schemas have no sqm/raw area, no area-basis flag and no main/auxiliary/common/parking area components. The richer market schema preserves gross sqm and parking sqm but does not establish main use or component/rights proof. Missing components and different ownership shares prevent proving equivalent denominators across all existing records.

## Parking verdict

**BLOCKED for current row data; exclude all parking transactions from proposed v1.**

Price is separable only where the raw transaction explicitly supplies a separate parking amount. Area is separable only with a separately defined transferred parking-area share. A space count/type without both does not justify subtraction. Zero/blank parking price must not be treated as a free parking space or as absence.

Existing PLVR unit prices cannot be assumed uniformly parking-exclusive. The valuation normalizer ignores parking entirely; the legacy, generation and compact GREEN normalized facts omit parking fields and target-basis flags. In a synthetic probe, adding explicit parking price/area left valuation normalization output identical.

A future extension could compute `(P - P_parking) / ((A - A_parking) * q)` only when both are positive, complete, compatible and cover all spaces, with 0 < P_parking < P and 0 < A_parking < A. For multiple spaces, price/area may be transaction totals: verify detail reconciliation and multiplicity, never multiply an already-total amount by count. This extension needs a new cohort/target contract and is deferred. No current count of zero-, single- or multi-space eligible rows can be established.

## Transaction-time age and floor verdicts

**Exclude age from Model A v1.** `normalize_row()` computes `max(0, date.today().year - completion_year)`, even when an `as_of` is passed. Unknown completion becomes zero. Completion date is dropped, so the stored age cannot defensibly be reversed into transaction-time age.

Synthetic fixture: June 2021 transaction, January 2011 completion → stored age 15 in 2026, versus transaction-year difference 10. The legacy date converter accepts February 31 as a month and a multi-floor value `3,4` is reduced to floor 3. Its `roc_date_to_period()` is a day-shaped digit parser, not a validated completion-year/month parser.

If raw, valid transaction/completion year-months can later be restored, define optional `age_months = 12*(transaction_year-completion_year) + transaction_month-completion_month` and `age_at_transaction = age_months/12`; require nonnegative duration, distinguish missing from zero and retain date precision. Do not fabricate a completion day or subtract present age from transaction year. Completion after transaction is rejected for this existing-building cohort. An exact-day age definition would need its own version; the month formula must not be advertised as exact days.

Floor is a plausible physical feature only after strict raw parsing proves one floor and source total-floor consistency. Current stored floor positivity alone does not supply that proof.

## Identity, duplicates and revisions

Legacy database `id` is an ingestion surrogate. `dedupe_key v2` hashes source, city/district, transaction month, optional official serial, address, type and rounded area/total/unit price. The official serial is not retained as a separate legacy column. Natural-key staging guards also compare rounded facts and use `ON CONFLICT ... DO NOTHING`.

Consequences:

- A changed price, area, address or geography can create a new hash for the same transaction correction.
- Hash uniqueness does not prove business transaction uniqueness; the observed 1,026 rounded-fact collision rows require identity evidence.
- Natural-key equality can collapse distinct official transactions; counts of collisions are not authorized deletions.
- Import-run `source_period` means covered transaction months; it is not a source release timestamp. `updated_rows` can refer to dedupe backfill, not revision maintenance.
- The clean shadow preserves county-scoped official IDs/source identities, raw row hashes and artifact hashes. It resolves compatible revisions by choosing highest `artifact_sequence` and a hash tie-break, after grouping revision anchors. This creates a latest snapshot, not a historical version table.
- Two previously resolved revision groups demonstrate that revisions exist. Historical reconciliation also records ambiguity in legacy-to-source matching; those reports do not prove current per-row resolution.

Future deterministic rule:

1. Store every occurrence by `(source_dataset_identity, artifact_sha256, member_path, physical_row_number)`, its raw payload hash, source official ID(s), source county and release schema.
2. Namespace logical transaction identity by source/type/source county and official identity semantics. Verify ID reuse across releases; never use a price-dependent hash as sole identity.
3. For any cutoff C, discard versions whose evidenced availability is after C **before** selecting versions. Missing availability is not eligible. Select over the full identity/version ledger, including canceled, invalid and cohort-ineligible payloads; apply effective-time and cohort filters only after selection. An unknown-availability or unordered revision that prevents proving the applicable version quarantines the logical identity rather than allowing fallback to an older version.
4. Identical same-ID/same-payload occurrences are duplicates. Keep an earliest-availability representative with deterministic artifact/member/row tie-break; retain all lineage edges.
5. Same-ID changed-payload occurrences are revisions. Select the latest officially ordered version available by C; preserve prior versions and first-seen/effective/availability times. Unordered conflicting versions are quarantined, never selected by import time alone.
6. Distinct official IDs with identical rounded facts are retained unless direct source evidence proves duplication. Missing-ID rows and unresolved multi-identity groups are excluded from v1.
7. Explicit cancellations invalidate a row only from their evidenced availability. Do not use later cancellations or corrections to rewrite earlier training/baseline eligibility silently. Related transaction versions must not cross split boundaries as different examples.

Reacquisition time and highest artifact sequence are insufficient substitutes for official publication order. A correction first observed in 2026 cannot be used as a 2024 training label at a 2024 cutoff without evidence of that earlier version.

## Release lineage and availability contract

| Required lineage element | Legacy accessible rows | Clean-shadow / other code | V1 requirement |
| --- | --- | --- | --- |
| Source dataset | Generic `official_plvr_opendata` | Artifact source agency/type | Dataset/type/schema identity |
| Original county/file | Not separately persisted | Artifact/member metadata | Preserve, verify geography |
| Official transaction ID | Lost outside hash | Retained in shadow/generation/evidence schemas | Separate logical ID, verified namespace |
| Raw transaction day | Lost to YYYY-MM | Shadow raw date / richer market date | Validated date + precision |
| Release ID and checksum | No per-row join | Shadow artifact metadata / migration 008 design | Mandatory release/content join |
| Publication/availability | No row field | Optional publication in rich design; shadow retrieval timestamp | Evidenced timestamp/upper bound + provenance |
| Import batch | Import summaries, no transaction FK | Generation/load metadata | Per-occurrence import batch link |
| Price/area/use/parking raw values | Absent | Partial preservation only | Full target/QC inputs |
| Transformation/dedupe version | Not row-persisted | Shadow normalizer/dedupe version | Pinned source commit, params and versions |
| Revision/cancellation history | No | Latest-shadow resolution | Append-only version/availability ledger |

Choose and record the prediction framing:

- **Public-information research framing:** predict at T using subject physical attributes supplied as facts known at T, and public historical transactions whose evidenced publication/availability is ≤ T. Retrospective subject attributes from a later declaration are only proxies; document that they are assumed observable before price negotiation and validate them against independent pre-sale evidence before making an operational historical-performance claim.
- **Operational-system replay framing:** historical transactions must additionally have been imported/accessible to this system by T. Define `system_available_at = max(evidenced_public_available_at, first_successful_system_import_at)`. With imports only demonstrated in June 2026, a 2024 operational replay is not supportable.

Default future v1 research framing uses validated transaction date as subject prediction day and explicitly supplies transaction year/month from the prediction clock. If only month precision is ever admitted, use the first day of that month as the feature cutoff and strictly earlier comparable months; it is a separate precision restriction, not an invented day. Current legacy months alone do not pass the complete target/lineage contract.

For each occurrence, preserve public release time, archive capture time, import time and availability evidence separately. A nominal quarterly label or a registration-window description is not an exact publication date. When only an authenticated upper bound is known, using that later bound is conservative; a hypothetical universal 30/60-day lag is not proof. If only 2026 reacquisition is evidenced, it cannot support earlier historical availability. Documented immutable original packages plus official historical release-time evidence may establish a defensible earlier bound after verification. Free packaged releases and dynamic live revisions must not be mixed. [MOI release behavior](https://lvr.land.moi.gov.tw/R11/jsp/qa.jsp).

Training cutoff C controls which historical versions and labels are allowed into training; target scoring labels may mature later under a separately frozen `label_observation_cutoff`. A scoring label observed after T is not a feature, but it must not train a model or historical median that was supposedly available at T.

## Point-in-time leakage audit

| Input/process | Current risk | V1 rule |
| --- | --- | --- |
| Later comparable transactions | BLUE uses current month; GREEN uses frozen max, not T | Filter effective time < T and availability ≤ T before candidate ranking/capping |
| Current market aggregates | Built from current retained/imported membership, possibly same/future outcomes | Do not consume current aggregates; rebuild only from eligible historical rows |
| Current/import-time age | Wall-clock derivation, completion lost | Block stored age; omit age from Model A |
| Revised records | Latest-shadow selection can overwrite old facts | As-of version ledger; later revisions cannot flow backward |
| Current county/district/road registry | Present boundaries and aliases can remap older places | Source-proven historical geography plus pinned mapping |
| Current GIS/POIs/MRT | Runtime lookup/cached snapshot does not establish historical validity | Defer until effective and availability intervals exist |
| Google Routes/commute | Current departure conditions, personalized inputs, current topology | Defer; no provider API loop in dataset construction |
| Hazard/environment layers | Artifact/version/checked_at can show today's provenance, not pre-T existence | Defer pending historical layer validity and reproducible joins |
| Community index | Current completion/year/location/matching metadata | Do not borrow current index for age or historical baseline without as-of proof |
| Retention/import state | Rows that survive today's pruning may not represent history at T | Frozen offline archive, explicit retention and coverage; no survivor-only historical claims |
| Source IDs/raw address/full coordinates | Can memorize outcomes or encode row identity | Audit-only lineage; not Model A/B inputs |
| Price-derived columns | Total, unit price, target, price/area reconciliations reveal outcome | QA/label-only; never features |
| LLM outputs/user behavior | Uncontrolled timing, personalization and derived outcomes | Defer from v1 |
| Category/scaler/outlier fitting | Whole-dataset fitting leaks future distribution/labels | Fit transformations on training only; freeze for later blocks |

Immutable source snapshots are necessary but insufficient: the join must meet both effective-time and availability conditions. Even a legitimately published hazard layer may not represent conditions at T. Present runtime `checked_at`, `built_at`, import timestamps and `source_updated_at` are not interchangeable with physical effective validity.

## Initial feature approval matrix

Approval refers to the proposed repaired contract. It does not override this gate's BLOCKED verdict or approve extraction from the current legacy table.

| Feature/input | Classification | Reason and restrictions |
| --- | --- | --- |
| District (county + district tuple) | APPROVED WITH RESTRICTIONS | Source-proven historical geography, no fabricated city-level district; training-fitted categories and explicit unknown |
| Building type | APPROVED WITH RESTRICTIONS | Exact approved aliases plus raw residential-use/rights proof; type alone is insufficient |
| `area_ping` | APPROVED WITH RESTRICTIONS | Verified registered transferred no-parking denominator, unrounded conversion, cohort scope |
| Floor | APPROVED WITH RESTRICTIONS | Raw single-floor parsing and total-floor validation; ambiguous legacy parsed values excluded |
| Transaction year | APPROVED V1 | Derive from validated subject prediction/effective date, never release/import year |
| Transaction month | APPROVED V1 | Same date/clock; calendar encoding pinned; not publication month |
| `age_at_transaction` | DEFER | Completion and precision not available for defensible reconstruction; omit Model A |
| Stored `building_age_years` | BLOCKED | Current-year age and missing-as-zero encoding |
| Road / Model B | DEFER | Cardinality and memorization risk; identity/geography/availability and clean-cohort profiling must first pass |
| Total price, official unit price, target, target reconciliation ratio | BLOCKED as features | Outcome or deterministic target relation; allowed only for label/QC |
| Official ID, source hash, dedupe key, raw full address | BLOCKED as features | Row identity/memorization; lineage-only |
| Personalized commute / Google Routes duration | DEFER | No historical reproducible routing/individual framing |
| Current POIs | DEFER | No historical store/closure/location intervals |
| Current MRT topology | DEFER | Current snapshot is not historical network proof |
| Current hazard layers | DEFER | No demonstrated historical effective/availability coverage for each subject |
| Current environmental/runtime scores | DEFER | Derived current state, no historical transformation inputs |
| Current market aggregates / comparable-derived features | DEFER | Must be reconstructed exclusively from as-of eligible history |
| LLM outputs | DEFER | Reproducibility, temporal availability and outcome contamination unproven |
| User behavior data | DEFER | Prediction framing and pre-T capture/selection not established |

**Model A:** conditional candidate set is district, type, verified area, verified floor and prediction year/month. No age. All labels/cohort/lineage blockers apply.

**Model B:** Model A plus road is a future experiment, not an approved v1 model. Current all-official profiling gives 37,549 geography/road keys, 10,062 singleton keys, 32,254 keys with fewer than 20 transactions, and 145,585 rows in those sparse groups. These counts include corrupt geography and unapproved types; clean training-only cardinality and unseen-road rate remain unknown.

Future road experiment must namespace road by county/district, preserve a pinned source-derived normalizer, count only training rows and pool keys with fewer than 20 training examples into an explicit rare class. Unknown roads receive a fixed unknown class. Do not fit vocabularies or target encodings on validation/calibration/test. If target encoding is ever used, it must be time-ordered and availability-safe within training; it is outside this gate.

Predeclare held-out-road and held-out-district diagnostics in addition to chronological evaluation. Count unseen/rare categories in each block; compare Model A/B errors and coverage without tuning on calibration/test. Road inclusion requires a reproducible improvement under those diagnostics; no improvement threshold is asserted before trustworthy data exist.

## Chronological split and calibration contract

**Design only; no split dataset or fitted model was produced.** Calendar ranges are not fixed from the corrupt legacy table or an unavailable shadow.

1. Freeze source releases, eligible transaction versions, coverage and label maturity. Select a contiguous interval of demonstrably usable complete months; do not fill empty/incomplete months with other cities' data or assume late reporting has settled.
2. Reserve the newest three complete mature months as **test**, the preceding three as **calibration**, the preceding three as **validation**, and earlier complete months as **train**. Require at least twelve usable training months. Prefer at least 24 eligible complete months overall, with additional months as required for maturity/embargo.
3. Choose any gaps/embargo from evidenced reporting/revision lag before looking at outcomes. Use half-open date ranges and one month/day boundary for each identity group; record excluded gap rows. If fewer months or district/type cells have adequate data, the build remains blocked or narrows its declared scope; it does not fall back to random splitting.
4. At the train→validation boundary, training labels and their selected versions must already be available. Validation outcomes used for selection must be available before the next model freeze. Calibration outcomes must be available before test begins. The row's effective block does not exempt it from these availability/maturity checks.
5. Validate choices only on validation. A final future fit may use train + validation only after those labels have matured by the calibration boundary. Fit preprocessing/category vocabularies on that fitting set only, and freeze the model before calibration.
6. Calibration labels are never used for model fitting, feature choice, hyperparameter choice or test-driven subgroup selection. Freeze calibrated intervals before test; test labels remain scoring-only.
7. Keep revisions of one transaction in one effective-time group and prevent duplicate examples across blocks. Building/entity repeat-sale group checks require defensible entity identity; masked source addresses cannot be claimed to guarantee such grouping.

For a future 90% split-conformal design, choose alpha = 0.10 in advance; on the separate calibration block compute `s_i = abs(log_price_i - frozen_prediction_i)`. Use the order statistic at `ceil((n_cal + 1) * (1-alpha))`, not an arbitrary interpolated percentile. If that rank exceeds n_cal, the finite-sample conservative quantile is unbounded; do not silently clamp it. Log-space intervals exponentiate to positive NTD/ping bounds.

Temporal drift can violate exchangeability. Report empirical chronological test coverage and width, including district/type/rare/unseen-road diagnostics; no unconditional coverage guarantee or subgroup calibration claim follows from the split alone. Do not repurpose current comparable P25/P75 ranges as conformal calibration.

## Leakage-safe baseline contracts

No baseline was evaluated. Prices below refer to the same no-parking target contract in NTD/ping.

Define `H(T,C)` by first selecting each identity's version **as of min(T,C)** over the full raw ledger, then applying cancellation, effective-time and cohort rules. Its rows must be verified eligible, differ from the subject identity, have effective time < T, public/system availability ≤ T under the selected framing and labels available by C. Never let a later scoring-label cutoff add records to H, and never fall back to an older version when the selected version is canceled or ineligible. In the primary comparison, C is the frozen model fitting cutoff and H is restricted to the fitting population for every validation/calibration/test prediction.

| Baseline | Exact contract |
| --- | --- |
| 0: global historical median | Median NTD/ping of H(T,C), then log for log-target comparison. No history → abstain; no sample/mock fallback. |
| 1: district/type historical median | Same median within source-proven county/district/type, minimum 20 eligible rows; fall back to global median when insufficient. Threshold fixed before evaluation. No post-T count or median. |
| 2: historical comparable estimator | Offline adapter using the normal-request district pool, current documented road/type/area ordering, 200 candidate cap, ≥3 comparables, IQR/top-ten/weight/mean-median/range rules over H(T,C). Apply as-of filtering before ranking/capping. The service's final city-labelled fallback remains limited to that district pool; do not silently expand retrieval citywide. Convert monetary units explicitly. Replace wall-clock recency with T. Never call the live estimator/provider during historical evaluation. |

Baseline 2 must use subject physical attributes legitimately supplied at T. Roads are allowed only as declared baseline matching rules from verified historical subject/source attributes, not automatically as an approved Model B feature. Current age, community index and current coordinates/GIS cannot be borrowed. If age and historical community/distance evidence are unavailable, explicitly use `historical-comparable-v1-no-age-no-runtime-enrichment`, with omitted age/distance/community bonuses and ranking terms; this is a documented restricted variant, not a claim of exact production parity.

All medians, outlier fences, similarity weights and fallback decisions depend only on H(T,C). Exclude the subject and all its revisions/duplicate occurrences. For month-only restricted data, use strictly earlier months. Do not include its same-month peer prices without day/availability proof.

An expanding-history deployment baseline is a separate optional experiment: advance C to T only as new outcomes genuinely become available, record every update, and compare models under the same update policy. Do not mix an updating median with a supposedly frozen historical information set without disclosure. Baseline ranges are diagnostic until separately calibrated.

## Versioned offline dataset build contract

This is an offline specification, not a production-runtime payload or an implemented builder.

| Identifier | Proposed semantics |
| --- | --- |
| `dataset_version` | `residential-valuation-v1.<build-id>`; new immutable ID for any source membership, cutoff, cohort, transform or split change |
| `feature_schema_version` | `residential-model-a-v1`; district/type/area/floor/year/month; no age or road |
| `target_version` | `residential-unit-ntd-ping-log-v1`, with explicit area/price basis versions |
| `source_dataset_identity` | MOI PLVR existing-sale-main + source schema version + verified county member identity |
| `transformation_version` | Offline builder commit SHA + explicit normalizer/dedupe/date/units/QA policy versions and dependency lock |
| `training_cutoff` | Latest availability time admissible for fit labels/versions; not max transaction month, latest import, or audit date |
| `feature_cutoff` / `prediction_as_of` | Subject prediction time T; every feature and historical join respects it |
| `label_observation_cutoff` | Scoring-label maturity/version freeze, separate from fit availability |
| `source_snapshot_id` | Ordered immutable artifact/member/hash manifest; explicit timezone, release and system/public availability framing |

Each accepted row conceptually includes:

| Group | Columns/invariants |
| --- | --- |
| Target | `residential_unit_price_ntd_ping`, `target_log_unit_price`, `target_method`, raw target QA provenance; finite and positive before log |
| Features | `county_code`, `district_code` as district namespace, normalized building type, verified `area_ping`, strict floor, transaction/prediction year and month |
| Time | Effective transaction date and precision, prediction_as_of, evidenced public_available_at, system_available_at if required, release_published_at, first_imported_at, selected_version_available_at |
| Identity | `logical_transaction_id`, `source_record_version_id`, occurrence/raw-payload hash, dedupe identity/version, revision-parent references |
| Lineage | Source dataset, release ID, artifact SHA256, member name/hash, physical row locator, source schema, import_batch_id, transformation version |
| Eligibility | Cohort/area/price/parking basis versions, included flag, first/all reason codes, relevant quality flags |
| Split | Train/validation/calibration/test or embargo status, split version and model fitting/label observation cutoffs |

Targets and QC price columns are not passed into feature matrices. Road appears only in a separately versioned experimental schema. Raw full addresses and official IDs remain restricted audit lineage, never model feature vectors. Public/documented aggregate evidence is separate from eventual private row artifacts.

Build manifest must contain ordered source artifacts and hashes, verified availability evidence, cohort parameters, feature/target/transform versions, explicit Asia/Taipei-to-UTC rules, cutoffs, split identities, inclusion/exclusion totals, per-district/type/month counts, missingness/cardinality, checksum of canonical sorted output and exclusion ledger, and checksums of feature vocabularies/preprocessing. The output checksum must cover all model-affecting columns and membership; a hash omitting age/floor would not protect a model using them.

A build fails closed on unknown source identity, unresolved price/area/parking basis, missing availability, unordered revisions, identity conflict, invalid dates, incomplete declared coverage, or impossible chronological/maturity splits. Each stage's count conservation and final identity uniqueness are checked. All storage is offline, versioned and independent of production retention/provider caches.

## Reproducibility verdict

**Not reproducible now for the proposed ML dataset.**

Useful foundations exist: reviewed schemas/migration registry, bounded importer and clean-shadow scripts, artifact and source-row checksums, normalizer/dedupe versions, and historical aggregate evidence. They do not replace missing bytes or missing release-time semantics.

[Rolling retention policy](../plvr_retention_policy.md) and [pruning script](../../scripts/prune_valuation_data.py) permit deletion of official rows older than an inclusive rolling 36-month cutoff, retaining import summaries/demo/community metadata. At the audit month that policy cutoff is 2023-11, but earlier official rows still exist; policy is not evidence pruning actually happened. Pruning was not run. A live database subject to this policy cannot act as the permanent ML source archive.

The market canary deletes temporary raw staging by default. Historical acquisition records retrieval in August 2026, not first public availability. No verified PLVR R2 object-key/immutability/retention/restore contract was found. ZIP filenames and their historic URLs cannot establish that exact old bytes are still recoverable today.

The clean-shadow output checksum excludes build timestamps but also omits some physical columns such as stored age/floor; age depends on today's year. Therefore even recovering archives and matching that checksum would not prove reproducibility of every potential feature. A future no-age builder must still pin and hash its own included floor/feature columns.

Minimum reproducibility evidence: archive bytes recoverable by exact checksums, matching embedded source schemas, verified historical release ordering/availability, a source-occurrence/revision ledger, and two independent offline builds yielding identical feature/target/membership/split hashes with unchanged raw inputs and explicit cutoffs.

## Known blockers and minimum repairs before ML-B

| Blocker | Minimum offline repair | Acceptance evidence |
| --- | --- | --- |
| B1: raw residential/target/area/parking semantics absent | Restore a bounded explicitly scoped set of existing-sale raw archives plus schemas/details; preserve main use, target, counts/rights, exact date, raw prices/areas, parking and notes | A nonempty strict residential/no-parking cohort with raw row locators, exact target reconciliation and reasoned funnel |
| B2: historical availability/version lineage absent | Verify release timestamps or conservative evidenced upper bounds; create append-only occurrence/revision/cancellation/import ledger | Every training/baseline row meets availability cutoff; no post-cutoff revisions selected |
| B3: geography/identity ambiguity | Source-county-based reconstruction; retain official IDs; quarantine unresolved conflicts; exclude city-level-only rows from district model | Source joins validate geography and identity; rounded-fact collisions individually resolved or excluded |
| B4: reproducible source storage absent | Establish controlled immutable PLVR raw storage with checksum/schema/retention/restore manifest; no production schema change required | Exact bytes restored and two offline no-age dataset builds match full output hashes |
| B5: trustworthy cohort volume/chronology unknown | Run bounded offline funnel profiling after B1–B4; measure per district/type/month and mature contiguous blocks | Actual post-filter/dedupe counts, coverage/lag evidence, usable train/validation/calibration/test blocks |
| B6: raw date/floor/classification transforms unsuitable | Build/test strict offline date and single-floor parsers, correct mixed land/building classification and explicit units; omit age | Fixtures cover invalid dates, floor ranges, no/multi-parking, corrections and identity reuse; no silent coercion |

Road, age and runtime enrichment are not minimum prerequisites: they remain omitted/deferred. Repairing the production estimator or loading/reactivating GREEN is not required to pass this **offline** gate. Start with a bounded source-proven regional cohort, not a new nationwide download. If historical availability can only be demonstrated from 2026 onward, accumulate a prospective archive and design future splits; do not invent past release dates to unlock ML-B.

Re-run ML-A after these repairs. It may then pass with a narrower cohort if target, lineage, temporal consistency and reproducibility are demonstrated. ML-B remains prohibited until that new gate verdict is recorded.

## Validation and audit reproduction

No audit script or production code was added. Synthetic inline probes exercised existing normalizers and asserted ignored parking, lost dates, wall-clock age, multi-floor truncation, invalid-day month acceptance and mixed land/building misclassification. These probes diagnose contracts; they are not an approved dataset transformation.

Document/evidence checks verify count conservation across city/type/month/district profiles, the 351,286 type-only proxy sum, geography partitions, duplicate arithmetic, JSON parsing, local references, expected changed-file scope, absence of row/private artifacts and `git diff --check`. No frontend/browser regression is needed for documentation-only changes. Git state/commit SHA are reported in the final delivery rather than embedded in a document that would require a second commit to update.

For future read-only recounts, use the bound database identity, READ ONLY and a bounded statement timeout. The following recipes return safe aggregate diagnostics; they do not create a training cohort:

```sql
BEGIN READ ONLY;
SET LOCAL statement_timeout = '20s';
SELECT source, count(*) AS rows,
       min(transaction_period) AS period_min,
       max(transaction_period) AS period_max
FROM public.real_price_transactions
GROUP BY source ORDER BY source;
COMMIT;
```

```sql
BEGIN READ ONLY;
SET LOCAL statement_timeout = '20s';
SELECT city, district, count(*) AS official_rows,
       count(*) FILTER (WHERE building_type IN (
         '住宅大樓(11層含以上有電梯)', '住宅大樓(11層含以上)', '住宅大樓',
         '華廈(10層含以下有電梯)', '華廈',
         '公寓(5樓含以下無電梯)', '公寓'
       )) AS type_only_residential_proxy_rows
FROM public.real_price_transactions
WHERE source = 'official_plvr_opendata'
GROUP BY city, district ORDER BY city, district;
COMMIT;
```

```sql
BEGIN READ ONLY;
SET LOCAL statement_timeout = '20s';
-- Run each SELECT separately if the connector returns only the last result.
SELECT building_type, count(*) AS rows
FROM public.real_price_transactions
WHERE source = 'official_plvr_opendata'
GROUP BY building_type ORDER BY rows DESC;
SELECT transaction_period, count(*) AS rows
FROM public.real_price_transactions
WHERE source = 'official_plvr_opendata'
GROUP BY transaction_period ORDER BY transaction_period;
COMMIT;
```

```sql
BEGIN READ ONLY;
SET LOCAL statement_timeout = '20s';
WITH facts AS (
  SELECT count(*) AS n
  FROM public.real_price_transactions
  WHERE source = 'official_plvr_opendata'
  GROUP BY city, district, transaction_period, address_text, building_type,
           round(area_ping, 2), round(total_price, 2),
           round(unit_price_per_ping, 2)
)
SELECT count(*) FILTER (WHERE n > 1) AS collision_groups,
       coalesce(sum(n) FILTER (WHERE n > 1), 0) AS collision_rows,
       coalesce(sum(n-1) FILTER (WHERE n > 1), 0) AS collision_excess
FROM facts;
COMMIT;
```

Counts are snapshots: a later recount can differ. To reproduce a dataset rather than these aggregate observations, first satisfy the source-storage and cutoff contracts.

## Final gate verdict

**BLOCKED**

**ML-B may not begin.** Critical unresolved semantics are raw residential/rights/area/parking proof, historical availability and row revisions, source-correct identity/geography, immutable recoverable input bytes, and actual eligible chronological volume. Minimum repairs are B1–B6 above. There is no authorization in this gate to train despite these blockers.
