# Geological Sensitivity Evidence Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic GSMMA geological-sensitivity ETL, immutable artifact runtime, fail-closed provider, and Terrain Risk integration without changing Liquefaction or Active Fault semantics.

**Architecture:** Dedicated dataset, artifact, runtime, and provider modules keep announced geological-sensitivity polygons separate from the live GeologyCloud API. A thin composite provider delegates geological sensitivity to the offline runtime and delegates Liquefaction and Active Fault to the existing provider. Runtime selection requires an explicit immutable dataset version and returns every overlapping official designation with `level=unknown`.

**Tech Stack:** Python 3, pytest, pyshp, Shapely 2, pyproj, boto3-compatible R2 client, gzip/JSON.

**Spec:** `docs/superpowers/specs/2026-09-27-geological-sensitivity-evidence-pipeline-design.md`

## Global Constraints

- Work only in `C:\Projects\proptech-geological-sensitivity` on `feat/geological-sensitivity-etl-v1`; do not switch branches or alter another worktree.
- Follow red-green-refactor: every production behavior starts with a focused failing test and its expected failure is observed.
- Preserve exact `official_category` and a separate explicitly mapped `canonical_category`.
- Runtime requires `GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION`; there is no default and no mutable `latest` path.
- Parse the official index as strict UTF-8 with optional BOM (`utf-8-sig`); do not guess Big5, CP950, or any other encoding.
- Deterministic outputs must exclude absolute/local/temp paths, drive letters, filesystem mtimes, and other machine-specific metadata.
- `matched=true` means intersection with an announced polygon and always uses `level=unknown` unless the official source later supplies a defensible severity field.
- Return every distinct overlapping official designation; never choose one scientific or legal primary result.
- Only a successfully loaded and queried artifact can return a no-match.
- Preserve `source_unavailable`, `checksum_mismatch`, `artifact_invalid`, `unsupported_dataset`, `crs_invalid`, and `query_error` as fail-closed outcomes.
- Do not change GeologyCloud Liquefaction semantics or promote Active Fault beyond its existing unavailable path.
- Add no archive dependency; ZIP is handled safely, while RAR/7z require operator extraction and fail clearly as direct inputs.
- Commit no official packages, large processed artifacts, credentials, or secrets.
- Do not upload, deploy, configure production, merge, or mutate production systems.
- Make one final bounded commit only: `feat: add geological sensitivity evidence pipeline`.

## File Structure

- Create `services/gsmma_geological_sensitivity_dataset.py`: index parsing, category and metadata normalization, CRS validation/transformation, geometry repair/quarantine, normalized models and statistics.
- Create `services/gsmma_geological_sensitivity_artifact.py`: safe package reading, shapefile decoding, deterministic artifact/manifest/quarantine serialization and loading.
- Create `services/gsmma_geological_sensitivity_runtime.py`: immutable R2 keys, explicit version selection, integrity validation, cache, STRtree, and point query.
- Create `services/terrain_risk_providers/gsmma_geological_sensitivity_provider.py`: Terrain Risk mapping for matches, misses, and typed failures.
- Create `services/terrain_risk_providers/gsmma_geology_provider.py`: thin three-layer composite.
- Create `scripts/build_gsmma_geological_sensitivity_artifact.py`: non-networked operator CLI and runbook output.
- Modify `services/terrain_risk_providers/__init__.py`: export new providers.
- Modify `services/terrain_risk_service.py`: use the composite as the default geology provider.
- Create `tests/test_gsmma_geological_sensitivity_dataset.py`: normalization, geometry, CRS, and determinism tests.
- Create `tests/test_gsmma_geological_sensitivity_artifact.py`: archive, SHP, artifact, manifest, and corruption tests.
- Create `tests/test_gsmma_geological_sensitivity_runtime.py`: version, R2, cache, integrity, overlap, miss, and query-failure tests.
- Create `tests/test_gsmma_geological_sensitivity_provider.py`: provider and composite contracts plus service visibility.
- Modify `tests/test_terrain_risk_providers.py`: explicit Liquefaction and Active Fault regression coverage through the composite.
- Modify `tests/test_terrain_risk_service.py`: default-composite wiring and matched-unknown evidence coverage where needed.
- Modify `docs/terrain-disaster-risk-public-source-audit-v1.md`: implementation and rollout-state truth.
- Modify `docs/terrain-disaster-risk-capability-matrix-v1.json`: implemented provider/runtime path without claiming an artifact or live rollout.

## Review Focus

- A valid `.prj` that conflicts with the index CRS declarations must fail `crs_invalid`, not be trusted or guessed; Task 1 tests this.
- A ZIP containing traversal, duplicate/case-colliding sidecars, excessive expansion, or multiple unselected SHPs must fail safely; Task 2 tests this.
- A manifest from another immutable version or with `review_required` quality must fail before geometry is queryable; Task 3 tests this.
- Many polygon fragments for one announcement must consolidate without discarding a different overlapping announcement; Task 3 tests this.
- A composite request for Liquefaction alone must not touch R2, while a geological-sensitivity failure must not alter Liquefaction or Active Fault output; Task 4 tests this.

---

### Task 1: Pure source-index, metadata, CRS, and geometry normalization

**Files:**
- Create: `services/gsmma_geological_sensitivity_dataset.py`
- Create: `tests/test_gsmma_geological_sensitivity_dataset.py`

**Interfaces:**
- Produces: `IndexRecord`, `NormalizedFeature`, `QuarantineRecord`, `NormalizationStats`, `parse_index_csv(payload: bytes) -> list[IndexRecord]`, `resolve_source_crs(prj_wkt: str, declared_crs_values: tuple[str, ...]) -> CRS`, and `normalize_feature(...) -> FeatureNormalizationResult`.
- Consumes: Shapely geometries, `pyproj.CRS`, and exact official index fields from the approved spec.

- [ ] **Step 1: Read the test-quality rules**

Read `superpowers/test-driven-development/writing-good-tests.md` from the installed skill directory before adding tests.

- [ ] **Step 2: Write failing CSV and metadata tests**

Test exact UTF-8 field names, a BOM-prefixed UTF-8 index, rejection of non-UTF-8 bytes, all four official-to-canonical category mappings, preservation of official values, whitespace/date normalization, original attributes, deterministic index ordering, missing fields, unknown categories, and conflicting duplicate announcement identifiers.

- [ ] **Step 3: Run the metadata tests and verify RED**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_dataset.py -k "index or metadata or category"`

Expected: collection/import failure because the dataset module and interfaces do not exist.

- [ ] **Step 4: Implement the minimal index and metadata models**

Implement strict UTF-8 CSV parsing, explicit field aliases, exact official-category preservation, stable canonical keys, required-field validation, date normalization, and deterministic records. Unknown source meanings raise `UnsupportedDatasetError`.

- [ ] **Step 5: Run the metadata tests and verify GREEN**

Run the Step 3 command and require zero failures.

- [ ] **Step 6: Write failing CRS tests**

Cover EPSG:3825, 3826, 3827, and 3828 to EPSG:4326 transformations, source CRS preservation, missing `.prj`, unparseable `.prj`, ambiguous declaration, and `.prj`/index contradiction.

- [ ] **Step 7: Run CRS tests and verify RED**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_dataset.py -k "crs or twd"`

Expected: failures for missing CRS resolution/transformation behavior.

- [ ] **Step 8: Implement per-package CRS validation and transformation**

Use `CRS.from_wkt`, explicit known index-declaration normalization, `Transformer.from_crs(..., always_xy=True)`, and no fallback CRS. Raise `CrsInvalidError` for missing, ambiguous, unsupported, or contradictory CRS.

- [ ] **Step 9: Run CRS tests and verify GREEN**

Run the Step 7 command and require zero failures.

- [ ] **Step 10: Write failing geometry and statistics tests**

Cover valid Polygon/MultiPolygon, repairable bow-tie polygon, repair-produced polygonal collection, unrepairable/empty input, unsupported Point/LineString, quarantine records, all required counters, category/CRS distributions, and deterministic normalized feature identity.

- [ ] **Step 11: Run geometry tests and verify RED**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_dataset.py -k "geometry or polygon or stats or quarantine"`

Expected: failures for missing normalization behavior.

- [ ] **Step 12: Implement geometry normalization and audit statistics**

Accept only polygonal source types, use Shapely validity repair, retain polygonal repair output only for polygonal inputs, transform to EPSG:4326, preserve audit fields, and quarantine rejected features without aborting unrelated records.

- [ ] **Step 13: Run all Task 1 tests**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_dataset.py`

Expected: all pass.

### Task 2: Safe package ingestion and deterministic processed artifact

**Files:**
- Create: `services/gsmma_geological_sensitivity_artifact.py`
- Create: `tests/test_gsmma_geological_sensitivity_artifact.py`

**Interfaces:**
- Consumes: Task 1 records and normalizers.
- Produces: `PackageInput`, `ShapefileComponents`, `BuildResult`, `read_package(...)`, `build_processed_artifact(...)`, `load_artifact(payload: bytes)`, and `write_build_outputs(...)`.

- [ ] **Step 1: Write failing safe-package tests**

Build tiny pyshp fixtures and test valid ZIP, extracted directory, selected relative SHP, traversal, absolute/drive paths, entry/size/ratio limits, duplicate/case-colliding sidecars, missing required sidecars, multiple ambiguous SHPs, invalid/missing encoding, and direct RAR/7z rejection with operator guidance.

- [ ] **Step 2: Run package tests and verify RED**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_artifact.py -k "package or zip or archive or shapefile or encoding"`

Expected: import or behavior failures because the artifact module is absent.

- [ ] **Step 3: Implement bounded package reading**

Read ZIP members in memory after validating names and resource limits; read extracted directories through resolved paths constrained beneath the supplied root; require explicit SHP choice when ambiguous; decode via `.cpg` or explicit encoding; return clear `UnsupportedDatasetError` for RAR/7z.

- [ ] **Step 4: Run package tests and verify GREEN**

Run the Step 2 command and require zero failures.

- [ ] **Step 5: Write failing deterministic artifact tests**

Test byte-identical repeated builds, identical source bytes/options under two different local roots producing byte-identical artifact/manifest/quarantine outputs, absence of local paths/drive letters/mtimes, stable feature ordering, schema/version, dataset version, source index/package SHA256, source vintage, counts/distributions, CRS metadata, accepted versus `review_required` quality, deterministic quarantine, artifact SHA256, write layout, successful load, malformed gzip/JSON/WKB, and manifest correctness.

- [ ] **Step 6: Run artifact tests and verify RED**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_artifact.py -k "artifact or manifest or deterministic or quarantine or corrupt"`

Expected: failures for missing build/serialization behavior.

- [ ] **Step 7: Implement deterministic build and load behavior**

Serialize canonical sorted JSON, WKB hex geometry, and gzip with fixed metadata; build the manifest from source inputs rather than wall-clock time; include checksums and all audit distributions; write only the three processed outputs beneath `<output>/<dataset-version>/`.

- [ ] **Step 8: Run all Task 2 tests**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_artifact.py`

Expected: all pass.

### Task 3: Explicit-version runtime, integrity verification, cache, and point query

**Files:**
- Create: `services/gsmma_geological_sensitivity_runtime.py`
- Create: `tests/test_gsmma_geological_sensitivity_runtime.py`

**Interfaces:**
- Consumes: Task 2 `load_artifact` and immutable object keys.
- Produces: typed runtime exceptions, `LoadedDataset`, `GsmmaGeologicalSensitivityRuntime`, `manifest_key(version)`, `artifact_key(version)`, `load_dataset()`, `query_point(lon, lat)`, and cache helpers.

- [ ] **Step 1: Write failing version and immutable-key tests**

Test missing `GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION`, safe explicit version, invalid path segment, no default/latest behavior, exact immutable keys, missing credentials, missing object, and manifest/version mismatch.

- [ ] **Step 2: Run version tests and verify RED**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_runtime.py -k "version or key or credential or missing"`

Expected: import or behavior failures because the runtime is absent.

- [ ] **Step 3: Implement configuration, keys, R2 protocol, and failure taxonomy**

Use the existing R2 environment names plus the required dataset-version variable. Validate one immutable path segment and never list objects or discover versions. Add typed exceptions carrying stable failure status and configured version where available.

- [ ] **Step 4: Run version tests and verify GREEN**

Run the Step 2 command and require zero failures.

- [ ] **Step 5: Write failing loader/integrity/cache tests**

Test manifest schema/quality/count checks, artifact checksum before decode, malformed manifest/artifact, checksum mismatch, cold load, warm cache, cache clear, and concurrent single-flight load.

- [ ] **Step 6: Run loader tests and verify RED**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_runtime.py -k "manifest or checksum or artifact or cache or concurrent or load"`

Expected: failures for missing loader and cache behavior.

- [ ] **Step 7: Implement verified loading and process-local cache**

Fetch only the configured immutable manifest/artifact, reject non-accepted manifests, verify SHA256 before decode, validate loaded records/counts/version/CRS, build an STRtree, and use a thread-safe single-flight cache.

- [ ] **Step 8: Run loader tests and verify GREEN**

Run the Step 6 command and require zero failures.

- [ ] **Step 9: Write failing spatial-query tests**

Cover one match, true no-match, boundary intersection, multiple categories, multiple announcements in one category, fragment consolidation for one designation, deterministic ordering, invalid coordinates, query exception, and defensive match-limit overflow that errors instead of truncating.

- [ ] **Step 10: Run query tests and verify RED**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_runtime.py -k "query or match or overlap or fragment or boundary"`

Expected: failures for missing indexed query behavior.

- [ ] **Step 11: Implement STRtree query and evidence consolidation**

Use indexed candidates plus exact `intersects`, group only identical designation identities, preserve all distinct evidence, return the configured version and artifact metadata, and raise `QueryError` for invalid or unsafe results.

- [ ] **Step 12: Run all Task 3 tests**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_runtime.py`

Expected: all pass.

### Task 4: Dedicated provider and thin composite provider

**Files:**
- Create: `services/terrain_risk_providers/gsmma_geological_sensitivity_provider.py`
- Create: `services/terrain_risk_providers/gsmma_geology_provider.py`
- Modify: `services/terrain_risk_providers/__init__.py`
- Create: `tests/test_gsmma_geological_sensitivity_provider.py`
- Modify: `tests/test_terrain_risk_providers.py`

**Interfaces:**
- Consumes: Task 3 runtime and existing `GeologyCloudProvider`.
- Produces: `GsmmaGeologicalSensitivityProvider.analyze(latitude, longitude, radius_m)`, and `GsmmaGeologyProvider.analyze(..., area_hint=None, include_layers=None)`.

- [ ] **Step 1: Write failing dedicated-provider tests**

Test matched evidence with all overlaps, `level=unknown`, dataset version and immutable prefix in source metadata, true no-match explanation, and exact mapping of every runtime failure to unavailable/error without a successful miss or low level.

- [ ] **Step 2: Run dedicated-provider tests and verify RED**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_provider.py -k "provider and not composite"`

Expected: import failure because the provider is absent.

- [ ] **Step 3: Implement the dedicated provider**

Map runtime results to the Terrain Risk layer contract, expose structured `value.matches`, keep match and severity separate, and produce conservative Chinese explanations and GSMMA source metadata.

- [ ] **Step 4: Run dedicated-provider tests and verify GREEN**

Run the Step 2 command and require zero failures.

- [ ] **Step 5: Write failing composite isolation tests**

Test per-layer delegation, no R2 call for Liquefaction-only requests, no HTTP call for sensitivity-only requests, unchanged Liquefaction match/miss/error payloads, unchanged unavailable Active Fault payload, and independent failure isolation.

- [ ] **Step 6: Run composite tests and verify RED**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_provider.py tests/test_terrain_risk_providers.py -k "composite or liquefaction or active_fault"`

Expected: failures for missing composite behavior.

- [ ] **Step 7: Implement and export the composite**

Delegate only requested layers, merge the new sensitivity result with exact existing GeologyCloud results, and retain placeholder results for unrequested keys without invoking their backing source.

- [ ] **Step 8: Run all Task 4 tests and Liquefaction regressions**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_provider.py tests/test_terrain_risk_providers.py`

Expected: all pass.

### Task 5: Operator CLI, Terrain Risk integration, and truthful documentation

**Files:**
- Create: `scripts/build_gsmma_geological_sensitivity_artifact.py`
- Modify: `services/terrain_risk_service.py`
- Modify: `tests/test_terrain_risk_service.py`
- Modify: `docs/terrain-disaster-risk-public-source-audit-v1.md`
- Modify: `docs/terrain-disaster-risk-capability-matrix-v1.json`

**Interfaces:**
- Consumes: Tasks 2-4.
- Produces: local-only artifact build command and default Terrain Risk composite wiring.

- [ ] **Step 1: Write failing CLI and integration tests**

Test CLI-required index, package mapping, dataset version and source vintage; local deterministic output; clear unsupported RAR/7z guidance; no network/upload behavior; default composite selection; matched-unknown evidence visibility; source failure resilience; and explicit configured version metadata.

- [ ] **Step 2: Run CLI/integration tests and verify RED**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_artifact.py tests/test_gsmma_geological_sensitivity_provider.py tests/test_terrain_risk_service.py -k "cli or geological_sensitivity or geology"`

Expected: failures for missing CLI/default integration behavior.

- [ ] **Step 3: Implement the local-only CLI**

Parse an operator package-mapping JSON, index path, immutable version, source vintage, output directory, and optional expected checksums; call the builder; print checksums/statistics/object-key destinations; never download or upload.

- [ ] **Step 4: Wire the default service to the composite**

Replace only the default geology-provider construction. Preserve the existing grouped provider seam, optional kwargs compatibility, API shape, matched evidence visibility, and scoring behavior documented in the spec.

- [ ] **Step 5: Update audit and capability documentation**

Record the exact source/index/category/package findings, implementation files, offline artifact path, explicit version requirement, semantic caveats, and rollout state. Keep `data_asset_present=false`, coverage unproven, production unconfigured, and production not smoke-tested.

- [ ] **Step 6: Run Task 5 tests**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_artifact.py tests/test_gsmma_geological_sensitivity_provider.py tests/test_terrain_risk_service.py tests/test_terrain_risk_api.py tests/test_terrain_risk_transparency.py tests/test_terrain_disaster_risk_capability_matrix.py`

Expected: all pass.

### Task 6: Full validation, bounded diff review, and single commit

**Files:**
- Review all changed files; modify only to resolve verified issues.

**Interfaces:**
- Consumes: completed Tasks 1-5.
- Produces: verified bounded commit and final state report.

- [ ] **Step 1: Run the targeted geological suite**

Run: `python -m pytest -q tests/test_gsmma_geological_sensitivity_dataset.py tests/test_gsmma_geological_sensitivity_artifact.py tests/test_gsmma_geological_sensitivity_runtime.py tests/test_gsmma_geological_sensitivity_provider.py`

Expected: all pass.

- [ ] **Step 2: Run affected Terrain Risk and Liquefaction regressions**

Run: `python -m pytest -q tests/test_terrain_risk_providers.py tests/test_terrain_risk_service.py tests/test_terrain_risk_api.py tests/test_terrain_risk_transparency.py tests/test_frontend_terrain_risk.py tests/test_wra_flood_provider.py`

Expected: all pass.

- [ ] **Step 3: Run the full Python suite**

Run: `python -m pytest -q`

Expected: all pass; report every failure if the repository baseline is not green.

- [ ] **Step 4: Run compile and structural validation**

Run: `python -m compileall -q services scripts tests`

Run: `python -m json.tool docs/terrain-disaster-risk-capability-matrix-v1.json > $null`

Run: `git diff --check`

Expected: exit code 0 for each.

- [ ] **Step 5: Inspect the complete diff and prohibited areas**

Run: `git status --short`

Run: `git diff --stat`

Run: `git diff -- services/wra_flood_offline_dataset.py services/wra_flood_artifact.py services/wra_flood_runtime.py services/terrain_risk_providers/wra_flood_provider.py`

Run equivalent `git diff --` checks for RIS demographics, Commute, and Property Identity paths discovered with `rg --files`.

Expected: only approved geological pipeline, shared provider/service integration, tests, scripts, and docs changed; no official large data or secrets.

- [ ] **Step 6: Perform whole-branch code review**

Review `origin/main...HEAD` plus the uncommitted diff against the approved spec. Resolve all Critical and Important findings, then rerun affected tests. Multi-agent review is not used unless separately authorized.

- [ ] **Step 7: Create the single bounded commit**

Run: `git add` with the explicit approved changed-file list, then `git commit -m "feat: add geological sensitivity evidence pipeline"`.

Expected: one new commit containing the design, plan, implementation, tests, script, and documentation.

- [ ] **Step 8: Capture final Git evidence**

Run: `git status --short`

Run: `git log -1 --oneline`

Run: `git diff origin/main...HEAD --stat`

Run: `git rev-list --left-right --count origin/main...HEAD`

Expected: clean worktree, requested commit at HEAD, and accurate ahead/behind counts.
