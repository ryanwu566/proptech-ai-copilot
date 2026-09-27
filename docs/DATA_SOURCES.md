# Data Sources and Integration Status

This document records the source boundary at `origin/main` commit `1095135` and dated runtime observations from 2026-09-27. It distinguishes code availability from production evidence.

## Status definitions

- **LIVE VERIFIED** — observed on the public deployment during the audit.
- **IMPLEMENTED** — source pipeline/adapter and tests exist.
- **CONDITIONAL** — requires credentials, a gateway, an imported dataset, object storage, or an operator refresh.
- **PARTIAL** — useful bounded integration exists, but coverage, freshness, authorization, or workflow closure is incomplete.
- **REFERENCE ONLY** — appropriate for context and follow-up, not authoritative legal, cadastral, appraisal, lending, or safety conclusions.
- **PLANNED / DISABLED** — design or seam exists, but it is not a current enabled capability.

## Source matrix

| Source | Purpose | Code path | Integration status | Trust and coverage note |
| --- | --- | --- | --- | --- |
| Ministry of the Interior PLVR open data | Historical sale transactions, aggregates, comparables, valuation, market trends | `official_plvr_market_pipeline.py`, `official_market_query.py`, `postgres_provider.py` | **LIVE VERIFIED; IMPLEMENTED** | Dated status reported official data across 21 cities/counties and 317 districts. Coverage is partial, composition is mixed, and outputs are not listings, appraisals, or transaction guarantees. |
| Google Geocoding | Address-to-coordinate resolution | `geocoding_adapter.py`, `location_resolver.py` | **LIVE VERIFIED configuration; CONDITIONAL** | Server-only key, quota, service terms, and request success apply. Trusted resolution avoids treating demo coordinates as official evidence. |
| Google Places | Nearby POIs and location context | `google_places_adapter.py`, `map_service.py` | **LIVE VERIFIED configuration; CONDITIONAL** | Some consumer map paths can return visibly labelled demo fallback; operational status is not proof of exhaustive POI coverage. |
| Google Routes | Travel-time and route enrichment | `routes_adapter.py`, `commute_routing_service.py` | **IMPLEMENTED; CONDITIONAL** | Requires configured Google credentials. Routing estimates are contextual and time-sensitive. |
| Google Maps Embed | Optional browser visual context | `google-maps-embed.ts` | **IMPLEMENTED; CONDITIONAL** | Uses a separate referrer/API-restricted public browser key. It is visual context, not evidence of parcel identity. |
| TGOS | Taiwan address geocoding and identity-observation seam | `tgos_geocoding_adapter.py`, `tgos_observation_provider.py` | **IMPLEMENTED; CONDITIONAL / PARTIAL** | Credentials required. Current geocoding can use TGOS; the VNext provider seam does not constitute production-accepted property identity. |
| TDX | MRT station snapshot and commute context | `tdx_mrt_client.py`, `tdx_mrt_snapshot.py`, `commute_service.py` | **IMPLEMENTED; CONDITIONAL; LIVE UNAVAILABLE during audit** | Snapshot is manually refreshed and memory-resident. The audit observed no loaded live snapshot. |
| Central Bank of the Republic of China Open Data | Mortgage/bank-rate market background | `bank_rate_service.py`, `mortgage_rate_service.py` | **IMPLEMENTED; CONDITIONAL** | Fallback/demo data exists. Published rates are context only and do not represent a borrower-specific bank offer or approval. |
| ARDSWC public MVT | Landslide, debris-flow, and related slope-hazard references | `ardswc_slope_hazard_provider.py` | **IMPLEMENTED; PARTIAL; REFERENCE ONLY** | Bounded tile queries and geometry matching exist. Repository evidence does not establish complete nationwide coverage, freshness, or continuous hosted availability. |
| Water Resources Agency flood-potential data | Flood-potential scenario evidence | `wra_flood_offline_dataset.py`, `wra_flood_artifact.py`, `wra_flood_runtime.py`, `wra_flood_provider.py` | **IMPLEMENTED; CONDITIONAL; REFERENCE ONLY** | Official downloads require offline processing. Runtime depends on a verified object-storage artifact and preserves missing/failed/limited states. Scenario data is not a property-specific flood guarantee. |
| GeologyCloud | Liquefaction potential | `geologycloud_provider.py` | **IMPLEMENTED; PARTIAL; REFERENCE ONLY** | Uses documented area/classification/bbox GeoJSON queries and point-in-polygon matching for supported official areas. It fails closed without a trusted area hint and does not prove national coverage. |
| NLSC basemaps and WMTS | Map and cadastral visual context | frontend map configuration, `landsect_context.py` | **IMPLEMENTED; REFERENCE ONLY** | Raster/tile context cannot establish parcel boundary, legal area, ownership, or land number. |
| NLSC terrain gateway | Point terrain observation | `nlsc_gateway_adapter.py`, `nlsc_terrain_provider.py` | **IMPLEMENTED; CONDITIONAL / PARTIAL** | Requires a fixed HTTPS gateway and token. Live health reported the gateway not configured during the audit. |
| NLSC cadastral gateway | Bounded cadastral observation seam | `nlsc_cad_gateway_adapter.py`, `nlsc_cad_observation_provider.py` | **EXPERIMENTAL / PARTIAL** | Supports strict normalized observation contracts and tests. It is not proof of a production-authorized, nationwide parcel resolver. |
| NLSC village boundaries | Resolve coordinates to RIS village codes | `nlsc_village_boundary_runtime.py`, `ris_village_resolver.py` | **IMPLEMENTED; CONDITIONAL** | Runtime depends on a prepared boundary artifact. Ambiguous, unresolved, and unavailable states remain explicit. |
| Ministry of the Interior RIS ODRP014 | Monthly village demographics | `ris_population_dataset.py`, `ris_population_ingestion.py`, `ris_population_query.py` | **IMPLEMENTED; CONDITIONAL** | Ingestion, Postgres query, API, and UI exist. Current production coverage and most recent loaded month were not independently verified. |
| Sentinel-2 / Copernicus through Google Earth Engine | Recent visual satellite reference | `earth_engine_adapter.py`, `earth_engine_worker_pool.py`, `satellite_reference.py` | **IMPLEMENTED; FEATURE-GATED / CONDITIONAL; REFERENCE ONLY** | Fixed 90-day window, 500 m radius, cloud masking, output limits, and fail-closed errors. Not cadastral, statutory, or parcel-boundary evidence. |
| OpenStreetMap tiles | General map context | frontend Leaflet basemap | **IMPLEMENTED** | Visual basemap subject to upstream availability and attribution; not an authoritative property record. |
| CartoDB Positron tiles | Light visual basemap | frontend Leaflet basemap | **IMPLEMENTED** | Presentation context only. |
| Esri World Imagery | Satellite-style basemap | frontend Leaflet basemap | **IMPLEMENTED** | Visual imagery context only; not the bounded Sentinel-2 evidence workflow. |
| Taipei City planning portals | User-reported planning-document reference | `taipei_planning.py`, `/v1/taipei-planning` route | **EXPERIMENTAL; FEATURE-GATED** | The system normalizes manual metadata but performs no retrieval or verification and makes no zoning, FAR, BCR, entitlement, or buildability conclusion. |
| Tax rule compatibility catalog | Deterministic TaxOracle screening | `official_tax_rules.py`, `tax_rules.py`, `tax_service.py` | **IMPLEMENTED; REFERENCE ONLY** | The active catalog does not claim jurisdiction-complete official rates. Outputs are screening aids, not legal or tax advice. |

## Live market and valuation evidence

On 2026-09-27, public status endpoints reported:

- market read model: ready, available, and partially covered;
- valuation source: PostgreSQL;
- 451,672 official PLVR rows plus 72 sample rows;
- 21 cities/counties, 317 districts, and 37,549 roads represented;
- effective trend period from 2023-10 through 2026-05;
- `is_full_taiwan: false` and `data_composition: mixed`.

These are useful production-validation facts, but they are time-bound operational state. They must not become undated promises or performance/user metrics. The service itself states that the data is not complete nationwide coverage.

## Provider behavior and failure semantics

The integration layer distinguishes:

- **available** — a usable provider result exists;
- **limited** — some evidence exists, but source or query completeness is reduced;
- **no data / no match** — the bounded query completed without suitable evidence;
- **unavailable** — configuration, dataset, provider, or dependency is not usable;
- **error** — the query failed;
- **not assessed / unknown** — the system has no defensible conclusion.

These states are not interchangeable. A provider timeout is not “no risk”; no polygon match is not legal confirmation; missing transactions are not a zero-value market; and a registered source is not an accepted integration.

## Data acquisition and operations

PLVR and RIS use controlled offline acquisition/ingestion paths with validation before durable writes. The WRA flood workflow similarly separates national download/geometry processing from request-time lookup. Heavy downloads and ETL do not run during web-service startup.

Source-specific operations are documented in:

- [Official PLVR data pipeline](official-plvr-data-pipeline.md)
- [PLVR historical import guide](plvr_historical_import_guide.md)
- [Market coverage operations](market-coverage-operations.md)
- [Commute snapshot operations](commute-snapshot-operations-v1.md)
- [Official data provider setup](official-data-provider-setup.md)
- [Terrain public-source audit](terrain-disaster-risk-public-source-audit-v1.md)

## Responsible-use boundary

The sources support preliminary property research and operational decision support. They do not replace land-office records, licensed appraisal, legal/tax advice, lender underwriting, engineering surveys, emergency guidance, or confirmation by the competent authority. Users should follow source links, dates, coverage notes, and recommended verification steps when a decision depends on a fact.
