# Geological Sensitivity Evidence Pipeline Design

## Purpose

Implement a production-grade, offline-to-runtime evidence pipeline for Taiwan's officially announced geological sensitivity areas. The pipeline answers whether a WGS84 property point intersects one or more loaded official announcement polygons. It does not create a nationwide geological-risk map and does not infer safety, low risk, or absence of geological hazards from a no-match.

This branch delivers code, deterministic tooling, tests, and truthful documentation only. Building or uploading the real artifact, configuring a production version, deploying, and production smoke testing are separate rollout states and are out of scope.

## Official source and semantics

The authority is the Ministry of Economic Affairs Geological Survey and Mining Management Agency (GSMMA) dataset `地質敏感區範圍數值檔` and its CSV download index. The index exposes these source fields:

- `No.`
- `地質敏感區類型`
- `地質敏感區編號`
- `地質敏感區名稱`
- `公告日期`
- `文號`
- `座標系統1`
- `座標系統2`
- `下載連結`

The four currently documented official categories are:

- `地質遺跡地質敏感區`
- `地下水補注地質敏感區`
- `活動斷層地質敏感區`
- `山崩與地滑地質敏感區`

The index links announcement-level ZIP, RAR, and 7z packages containing shapefile data. Each announcement is a legal or administrative designation. Its category and name are evidence, not a high/medium/low severity class. Active-fault sensitivity polygons are also distinct from the separate, incomplete Active Fault terrain-risk layer.

## Selected architecture

Use a dedicated geological-sensitivity pipeline and provider, plus a thin composite geology provider:

```text
operator-supplied official index and packages
  -> package/index audit and explicit normalization
  -> deterministic EPSG:4326 feature artifact and manifest
  -> immutable object-storage version
  -> checksum-verifying process-local runtime and STRtree
  -> geological-sensitivity provider
  -> composite geology provider
       geological sensitivity -> new offline provider
       liquefaction           -> existing GeologyCloud provider
       active fault           -> existing unavailable GeologyCloud path
  -> Terrain Risk
```

The existing GeologyCloud liquefaction implementation remains unchanged. The composite is responsible only for routing and merging the three geology-layer results.

## Source audit and operator inputs

The build command consumes an operator-downloaded UTF-8 CSV index plus local announcement packages. It never downloads official data and never uploads artifacts.

Each index row is normalized through an explicit alias table. Missing required fields, unknown category values, malformed dates, unrecognized coordinate-system declarations, duplicate conflicting announcement identifiers, or packages that cannot be unambiguously associated with an index row fail closed as `unsupported_dataset` or `crs_invalid`; field meanings are never guessed.

ZIP extraction is implemented in-process with entry-count, expanded-size, compression-ratio, absolute-path, drive-prefix, and parent-traversal protections. RAR and 7z inputs fail with a clear operator instruction to extract them using an approved external tool and supply the extracted directory. No new archive dependency is added. Extracted directories are read without executing any content.

A package must identify exactly one ingestible shapefile dataset, or the operator must explicitly select the relative SHP path in the build input mapping. Multiple candidates never trigger heuristic selection. Required SHP sidecars are validated. Text decoding uses a valid `.cpg` declaration or an explicit operator-provided encoding; ambiguous encoding fails closed.

## Normalized feature model

Every accepted feature preserves:

- `official_category`: the exact government-provided sensitivity-area type
- `canonical_category`: a stable internal category key mapped explicitly from the official value
- `official_name`
- `sensitivity_area_no`
- `announcement_no`: the official document number (`文號`)
- `announcement_date`
- `source_agency`
- `source_url`: the index row's official download URL
- `source_index_no`
- `source_crs`
- `target_crs`: always `EPSG:4326`
- `dataset_version`: the operator-selected immutable release version
- `source_package_sha256`
- `original_attributes`: decoded source SHP attributes needed for auditability
- normalized Polygon or MultiPolygon geometry

The canonical category never replaces or rewrites `official_category`.

## CRS behavior

CRS is resolved and validated per shapefile package. A parseable `.prj` is required and is cross-checked against the index coordinate-system fields. TWD67/TWD97 and TM2 central-meridian variants are transformed with `pyproj` only after an unambiguous CRS has been established. A missing, unknown, or contradictory CRS fails as `crs_invalid`; coordinates are never reinterpreted heuristically.

Runtime geometry is EPSG:4326. The manifest records source-CRS distribution, target CRS, transformation metadata, and per-package source CRS.

## Geometry handling and auditability

Polygon and MultiPolygon inputs are supported. Empty geometry is rejected and counted. Other original geometry types are quarantined and counted as unsupported.

Invalid polygonal geometry is passed through Shapely's supported validity repair. A repaired Polygon or MultiPolygon is accepted and counted. Polygonal members may be retained from a repair-produced GeometryCollection only when the original input was polygonal; discarded non-polygonal repair remnants are recorded. An unrepairable or empty result is quarantined rather than crashing the remaining ingestion run.

The build always produces structured statistics for:

- input, accepted, rejected, empty, invalid, repaired, and unsupported counts
- official and canonical category distributions
- source CRS distribution
- geometry-type distribution
- per-package outcomes

Rejected records are written to a deterministic quarantine report. Any rejected, unsupported, empty, ambiguous, or unrepairable input sets the manifest quality state to `review_required`. The runtime refuses a non-accepted manifest; an incomplete build cannot silently become production evidence.

## Deterministic artifact

The builder emits a deterministic bundle:

- `features.json.gz`: schema-versioned normalized records with deterministic ordering and gzip metadata
- `manifest.json`: canonical JSON containing schema/version, dataset version, source-index checksum, source-package metadata and checksums, artifact checksum, feature count, category distributions, CRS metadata, geometry statistics, and source vintage
- `quarantine.json.gz`: deterministic rejected-feature audit records, empty for a clean build

Dynamic wall-clock time is not part of artifact identity. Source vintage and the explicitly supplied dataset version provide release provenance. Running the builder twice with identical inputs and options produces byte-identical artifacts and manifests.

The documented immutable storage layout is:

```text
raw/gsmma/geological-sensitivity/<dataset-version>/...
processed/gsmma/geological-sensitivity/v1/<dataset-version>/manifest.json
processed/gsmma/geological-sensitivity/v1/<dataset-version>/features.json.gz
processed/gsmma/geological-sensitivity/v1/<dataset-version>/quarantine.json.gz
```

Large official source or processed files are never committed to Git.

## Explicit runtime version selection

The runtime has no default dataset version and no `latest` pointer. Production must explicitly configure `GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION`. The value is validated as one safe immutable path segment before object keys are constructed.

Missing version configuration is `source_unavailable`; a syntactically invalid version or a manifest/version mismatch is `unsupported_dataset`. Neither can become a no-match. The loaded manifest's dataset version must exactly match the configured version. Provider source metadata exposes the configured dataset version, immutable artifact prefix, artifact checksum, and source vintage.

## Runtime loading and query behavior

The read-only runtime performs:

```text
explicit configured version
  -> immutable manifest GET
  -> manifest/schema/version/quality validation
  -> artifact GET
  -> SHA256 verification before decode
  -> feature and geometry validation
  -> STRtree construction
  -> process-local thread-safe cache
  -> exact point intersection
```

Concurrent cold loads use single-flight locking. Warm queries do not redownload objects. Runtime loading never parses official SHP packages.

A successful query returns every distinct official designation intersecting the point. Polygon fragments belonging to the same designation are consolidated into one evidence item with a matched-fragment count. Evidence ordering is deterministic. No designation is selected as a scientific or legal primary result. A defensive maximum prevents unbounded corrupt-artifact results; exceeding it raises `query_error` rather than truncating evidence.

A successful miss is:

```text
status = available
matched = false
level = unknown
```

Its explanation states only that the point did not intersect the loaded official announced polygons and that this does not establish geological safety or absence of hazards.

## Failure taxonomy

The pipeline preserves these explicit states:

- `source_unavailable`: missing configuration/credentials/object or storage access failure
- `checksum_mismatch`: downloaded bytes do not match the manifest
- `artifact_invalid`: invalid manifest, compression, schema, record, or geometry
- `unsupported_dataset`: unsupported archive/package/schema/category or non-accepted build quality
- `crs_invalid`: missing, ambiguous, contradictory, or unsupported CRS
- `query_error`: invalid query or spatial-query failure

None may be returned as a successful no-match or low risk. The provider maps source unavailability to `status=unavailable`; integrity, dataset, CRS, and query failures map to `status=error`. All retain `level=unknown` and `matched=false`.

## Provider and Terrain Risk contract

A matched geological-sensitivity result has:

```text
key = geological_sensitivity
status = available
matched = true
level = unknown
distance_m = 0
value.matches = [all distinct official designation evidence]
source.agency = GSMMA
source.dataset_version = configured immutable version
```

`matched=true` means only that the property point intersects an officially announced geological sensitivity polygon. It is separate from severity. The provider does not fabricate a numeric score or high/medium/low class.

The composite provider delegates only requested layers. It merges the new provider's geological-sensitivity result with the existing GeologyCloud results for liquefaction and active fault. Liquefaction routing, official classifications, query semantics, and failures remain unchanged. Active Fault continues to use its current unavailable/incomplete result and is not marked implemented.

Terrain Risk must keep matched geological sensitivity visible as evidence even though its level is unknown. Existing aggregate scoring remains unchanged; the legal designation is reference evidence rather than a fabricated severity contribution.

## Test strategy

Development follows red-green-refactor. Synthetic fixtures only are used.

Coverage includes:

- index aliases, official/canonical category preservation, metadata normalization, duplicate conflicts, and deterministic ordering
- Polygon, MultiPolygon, repairable and unrepairable invalid geometry, empty geometry, unsupported geometry, and quarantine statistics
- TWD67/TWD97 TM2 transformations, central-meridian variants, missing CRS, contradictory CRS, and unsupported CRS
- safe ZIP handling, traversal/size/compression defenses, clear RAR/7z errors, ambiguous SHP selection, and encoding validation
- deterministic artifacts, manifest correctness, checksum generation, quarantine output, load, corrupt artifact, and checksum mismatch
- explicit version requirement, version mismatch, cold/warm/single-flight loading, missing credentials/object, invalid manifest/artifact, all overlapping designations, consolidated fragments, true miss, and query overflow/error
- provider match, true miss, every failure class, dataset version in source metadata, and no fake severity
- composite delegation with Liquefaction regression and unchanged Active Fault behavior
- Terrain Risk visibility, missing-source resilience, fail-closed behavior, API/response compatibility, and relevant frontend contracts

Validation includes targeted geological tests, affected provider/service/API tests, Liquefaction regressions, frontend contract tests if needed, available Python compile/static checks, the full project test suite, and `git diff --check`.

## Documentation and rollout truth

The public-source audit and capability matrix will describe implementation truthfully. Without a real accepted artifact, upload, configured immutable production version, and smoke test, the layer remains not production-live.

The final report separately records:

- implementation complete
- artifact successfully built
- artifact uploaded
- production version configured
- production smoke-tested

## Scope boundaries

This work does not deploy, merge, modify production R2, change production configuration, alter Cloud Run or Vercel, touch production PostgreSQL, commit official datasets or credentials, change Flood behavior, modify RIS demographics/Commute/Property Identity, change Liquefaction semantics, or promote Active Fault to complete.
