# Risk provider artifact rollout

This branch establishes deterministic local contracts. It does not establish
deployed provider health, full Taiwan coverage, current official vintage or
production artifact availability. No rollout step below was executed against
production during implementation.

Terrain summaries preserve positive hazard warnings when another layer is
incomplete. `limited` is partial evidence. Successful no-match, unavailable,
unknown and skipped layers cannot establish low overall risk. Active Fault
remains **MANUAL VERIFICATION ONLY** through the official GeologyCloud source
and competent authority. GSMMA active-fault geological-sensitivity designations
are a distinct legal/source category and do not automate active-fault safety.

## Local acceptance

Run from the repository root. Config-only mode reports missing variable names
without printing credentials and performs no provider requests:

```powershell
python scripts/provider_acceptance.py --capability wra --mode config-only
python scripts/provider_acceptance.py --capability gsmma --mode config-only
```

Required artifact access variables are `R2_ACCESS_KEY_ID`,
`R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT`, `R2_BUCKET`, `R2_REGION`.
GSMMA additionally requires `GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION` as an
exact immutable identifier. `latest`, empty values and unsafe paths fail closed.
The WRA runtime uses the existing immutable `processed/wra/flood/v1` prefix and
one explicit scenario; the default is `24h-350mm`. There is no mutable latest
pointer. Processing version `v1` is not a dataset vintage.

Validate operator-owned local outputs through the actual runtime checksum,
metadata, geometry and spatial-index loaders, without network access:

```powershell
python scripts/provider_acceptance.py --capability wra --mode offline-fixture --manifest artifacts/provider-acceptance/wra/24h-350mm/manifest.json --artifact artifacts/provider-acceptance/wra/24h-350mm/features.json.gz --scenario 24h-350mm --fixtures-json artifacts/provider-acceptance/wra-fixtures.json
python scripts/provider_acceptance.py --capability gsmma --mode offline-fixture --manifest artifacts/provider-acceptance/gsmma/EXACT_VERSION/manifest.json --artifact artifacts/provider-acceptance/gsmma/EXACT_VERSION/features.json.gz --dataset-version EXACT_VERSION --fixtures-json artifacts/provider-acceptance/gsmma-fixtures.json
```

Use at most three fixture entries, for example
`[{"lon":121.0,"lat":25.0,"matched":true,"label":"known-positive"}]`.
Choose known positive, known negative and exact saved boundary points from the
accepted dataset and preserve their independent provenance. A negative fixture
proves only absence of a match in that saved dataset/scenario. Validate positive
and negative fixtures before rollout; a checksum/index-only result with
`fixtures_verified=false` is incomplete operational evidence. The helper reports
`production_readiness=unproven` even on local acceptance.

Without supplied local files, offline-fixture mode exercises deterministic
synthetic fixtures. Synthetic fixture success cannot accept a real artifact or
prove hosted R2/IAM configuration.

## WRA preparation and rollout

1. Obtain the official SHP ZIP using the documented official download contract.
   Record its exact URL, acquisition date, source vintage and SHA256. Do not
   infer vintage from a processing timestamp or file name. Preserve raw source
   outside git. Confirm the intended rainfall duration/depth scenario.
2. Build locally with the source checksum and explicit vintage:

   ```powershell
   python scripts/build_wra_flood_artifact.py --input-zip artifacts/provider-acceptance/source/flood.zip --scenario 24h-350mm --source-url OFFICIAL_DOWNLOAD_URL --source-vintage VERIFIED_OFFICIAL_VINTAGE --expected-sha256 SOURCE_SHA256 --output-dir artifacts/provider-acceptance/wra --write
   ```

3. Require `quality_status=verified`, a positive accepted count, the declared
   WGS84 CRS and scenario, matching checksum and accepted-count/index validation.
   Review all rejected/repaired geometries and source coverage explicitly.
   Old manifests without source vintage may load with `unknown` provenance but
   fail operator artifact acceptance. Verify the original acquisition evidence;
   do not invent a vintage to satisfy the validator.
4. Run the local acceptance command above with independently known fixtures.
   Record acceptance JSON and review evidence before accepting the artifact.
5. An authorized operator may upload **new immutable objects only** under
   `processed/wra/flood/v1/24h-350mm/manifest.json` and `features.json.gz`.
   If objects already exist, compare hashes and reuse exact accepted bytes.
   Never replace different bytes at an existing immutable key. A genuinely new
   release needs a separately reviewed runtime/prefix contract; this branch
   does not silently introduce a new WRA release prefix.
6. Configure artifact access, deploy the reviewed backend release and perform
   one bounded smoke for the default scenario. Record deployed SHA, scenario,
   object keys/checksum, vintage, query outcome/status, UTC time and exact
   request count. Confirm a known positive remains visible and source failure
   remains unavailable/error. Do not scan many scenarios or properties.

WRA is point intersection, including a polygon boundary, with a saved rainfall
scenario. `radius_m` does not expand flood matching. It provides no whole-parcel
or whole-building coverage claim. Other rainfall scenarios and real drainage
conditions remain outside that result.

## GSMMA preparation and rollout

1. Obtain the official CSV index and mapped source packages. Record source
   URLs, index/package checksums, official vintage and exact dataset version.
   For externally extracted RAR/7z packages, preserve approved extraction and
   directory checksum evidence. Reuse the existing builder's schema, per-package
   CRS checks, transformation and quarantine behavior.
2. Build locally:

   ```powershell
   python scripts/build_gsmma_geological_sensitivity_artifact.py --index artifacts/provider-acceptance/source/index.csv --package-map artifacts/provider-acceptance/source/packages.json --dataset-version EXACT_VERSION --source-vintage VERIFIED_OFFICIAL_VINTAGE --expected-index-sha256 SOURCE_INDEX_SHA256 --output-dir artifacts/provider-acceptance/gsmma
   ```

3. Review `manifest.json` and `quarantine.json.gz`. Runtime admission requires
   `quality_status=accepted`; rejected features set `review_required` and cannot
   be silently admitted. Resolve the source/schema/CRS cause and rebuild rather
   than editing the quality flag. Require manifest/artifact exact version,
   supported schema, finite coordinates within WGS84 geographic bounds,
   positive feature count and valid SHA256. A CRS label alone cannot admit
   projected coordinates.
4. Run local acceptance with positive, negative and saved boundary fixtures.
   Record artifact SHA256, index/package provenance and acceptance output.
5. An authorized operator uploads accepted bytes to
   `processed/gsmma/geological-sensitivity/v1/EXACT_VERSION/manifest.json`,
   `features.json.gz` and the retained quarantine evidence. Never overwrite an
   existing version with different bytes. Keep prior accepted versions available.
6. Configure `GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION=EXACT_VERSION`, deploy
   the reviewed backend SHA and perform one bounded smoke. Record deployed SHA,
   exact version, source vintage, checksum, source status and actual request
   count. A process cache cannot switch version in place: deploy/restart for the
   new exact version. Revert to the prior accepted version/release for recovery.

GSMMA is coordinate-point intersection with saved sensitivity polygons. A
negative match is not a safety, soil-liquefaction, building condition or
active-fault conclusion. Geological sensitivity, liquefaction and manual Active
Fault remain independent capabilities; failures must not erase another result.

## ARDSWC operational boundary

The existing configured layer vintage remains `113年度（官方公開 MVT）`
(`113-public-mvt`). No newer vintage was verified or configured in this branch.
Each sublayer carries its layer ID, source endpoint, vintage and match semantics:
polygon intersection with the query radius versus stream proximity within that
radius. Polygon/MultiPolygon interior holes retain their owning polygon; a point
inside a hole matches only when its query radius reaches a polygon boundary.
Stream closure does not convert a line into an area. Sublayer results
retain requested/successful/failed tile counts and bounded error examples.

The contract caps each MVT layer at 36 tiles, workers at six, each request at
1.5 seconds and the query budget at 2.5 seconds, with ten-minute tile caching.
Already-running requests finish within their request timeout after the budget;
the budget is not a strict total-wall-clock deadline. There are no retries.
Partial tile failures produce `limited` and preserve any positive matches;
unmatched partial queries cannot confirm the full radius. All tile failures
produce `error`. No-match in a successful saved/current layer still does not
mean no hazard, and a tile service cannot establish whole-parcel coverage.

Record deployment/version and one bounded positive/negative official comparison
before provider acceptance. The deterministic tests do not establish nationwide
completeness, freshness or official endpoint uptime. Vintage upgrades require
independent verification of the official layer contract.

## Evidence and recovery

Keep operator acceptance output, deployed release identity, configuration name
checks, actual artifact keys/versions/checksums, independently known fixtures,
official acquisition provenance, reviewer decision, smoke time and exact request
count together. Store no secret values in those records. A missing configuration,
missing real artifact or unknown deployed SHA remains an explicit blocker.

On checksum/schema/CRS mismatch, stop using that artifact; do not downgrade the
failure to no-match or patch a manifest to match damaged bytes. Roll back the
exact accepted version/deployed release, retain failed evidence for investigation
and re-run local validation before any next rollout. This implementation made
zero live provider requests and performed no upload, deployment or secret change.
