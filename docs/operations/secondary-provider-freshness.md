# Secondary provider freshness

This branch supplies deterministic local evidence. It does not deploy gateways, refresh production datasets, call live providers, or establish production readiness.

| Capability | Local contract | Remaining acceptance / P2 operations |
| --- | --- | --- |
| TDX MRT | Snapshot content SHA-256, schema version, preserved station `SrcUpdateTime`, source age and advisory stale status | Credentials and one authorized refresh; durable shared snapshot storage and cross-instance rollout remain P2 |
| RIS village demographics | Valid nonnegative integer counts; missing/invalid latest observation returns `no_data`; statistical month freshness independent of successful read | Validate deployed latest statistical month and configured boundary artifact; recurring import scheduling remains P2 |
| NLSC village identity | Existing polygon identity, `source_vintage`, configured checksum verification, no fuzzy village-name fallback | Roll out verified artifact and version configuration |
| NLSC numeric terrain | Existing independent backend gateway configuration, fixed endpoint, deadline, bounded response validation | Configure and deploy the gateway separately; WMTS visibility or village resolution does not prove numeric terrain availability |
| Satellite / GEE | Existing feature/project contract, ADC and initialization failure mapping, absolute request deadline, bounded worker admission, no request replay | Verify deployed project, ADC/IAM and one bounded optional request; core Risk remains independent |

## TDX interpretation

`snapshot_version` identifies accepted station/line content; regenerating identical content changes `generated_at`, not its version. `snapshot_schema_version` is `tdx-mrt-v1`. `source_updated_at` on snapshot status/refresh is the oldest accepted source timestamp. Missing timezone, malformed timestamps or future timestamps produce `freshness_status=unknown`.

The advisory policy uses `source_age_days > stale_after_days`, with `stale_after_days=30`. This threshold is an operator review policy, not a provider SLA. A stale snapshot can still return a successful station lookup. It does not invalidate Google Routes.

Nearest/address lookup retains the selected station's `source_updated_at`. `snapshot_source_updated_at` carries the snapshot's oldest source timestamp. Both status and lookup expose `snapshot_version`, `snapshot_schema_version`, `source_age_days`, `stale_after_days`, `freshness_status`, `freshness_reason_code` and `freshness_as_of`. Status without a loaded snapshot reports unavailable freshness. These reads make no external requests.

Snapshots remain process-local. Existing refresh replaces the process snapshot only after a valid build; this branch introduces no durable persistence or cross-instance synchronization. A refresh against one instance is not evidence that every instance loaded the same version. Operators must record instance/release identity alongside version until a shared persistence strategy is implemented.

## RIS interpretation

Demographics `status` remains `available` or `no_data`. A latest observation missing valid `total_population`, `household_count`, or ROC `statistic_yyymm` is `no_data` with `demographics_observation_invalid`; zero is preserved when it is an actual valid count. Invalid historical observations are excluded rather than filled with zero. Ratios remain null where unavailable.

For available summaries, `latest_statistic_yyymm`, `statistical_month_lag`, `stale_after_months=2`, `freshness_status`, `freshness_reason_code` and `freshness_as_of` describe the latest statistical month. Lag greater than two months is stale; a future month is unknown. Successful database access cannot make old observations current. The two-month threshold is an advisory review policy.

Village boundary `source_vintage` remains separate from the demographic statistical month. Configure `NLSC_VILLAGE_BOUNDARY_ARTIFACT_SHA256` and a local artifact path or R2 key plus credentials, and preserve source vintage/provenance. A resolved village does not imply demographic coverage. Demographics never infer residents of an individual property.

## Existing Satellite / NLSC isolation

Satellite remains optional: `EARTH_ENGINE_SATELLITE_REFERENCE_V1=true` and `EARTH_ENGINE_PROJECT` are required; backend ADC/IAM must be accepted separately. Existing request timeout is eight seconds, worker admission is two active plus two queued, and stale/expired/cancelled requests fail closed without replay. Credential failure, initialization failure, timeout and provider errors return unavailable secondary evidence. No cadastral, parcel, hazard or legal conclusion is derived from imagery.

NLSC numeric terrain requires its backend gateway base URL and client token; village boundaries and public WMTS tiles are separate capabilities. Existing offline adapters validate fixed endpoint use, four-second gateway deadline and malformed responses. No gateway is deployed by these checks.

## Offline verification

Run `python -m pytest tests/test_secondary_provider_freshness.py tests/test_tdx_mrt_snapshot.py tests/test_tdx_mrt_client.py tests/test_commute_service.py tests/test_commute_api.py tests/test_commute_address_lookup.py tests/test_commute_routing_service.py tests/test_commute_route_api.py tests/test_ris_village_resolver.py tests/test_ris_demographics_api.py tests/test_ris_population_query.py -q`.

Reuse `tests/test_satellite_reference.py`, `tests/test_earth_engine_worker_pool.py`, and the NLSC gateway adapter suites for deterministic configuration, failure and isolation acceptance. Fixtures and local HTTP servers do not constitute live provider acceptance. No secrets or raw provider payloads belong in acceptance reports.

## Rollback

The change adds metadata and makes invalid demographic counts fail closed. It creates no database migration or new infrastructure. Rollback can restore code and API types together; keep the previous accepted TDX snapshot and RIS/boundary artifacts until the deployed release and replacement evidence are verified. Never rollback by replacing missing demographics with zeros or requiring TDX for Google Routes.
