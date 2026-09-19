# NLSC Requested Service Integration Matrix v1

- Audit date: 2026-09-19
- Branch: `audit/nlsc-24-service-matrix`
- Baseline: `origin/main` at `9e5eaa4d4a42fec15f0652299c9ea0d93e9168fb`

## Decision

**NO-GO. Zero of the 24 requested NLSC service codes is production-live, gateway-ready, implemented by a service-code-specific adapter, or covered by a service-code-specific test.**

The repository has useful NLSC-adjacent foundations, but they do not implement any requested code:

- `services/adapters/nlsc_gateway_adapter.py` is a Render-side client for the repository-specific `/nlsc/terrain/point` contract. It contains no requested NLSC code or NLSC endpoint mapping.
- `services/landsect_context.py` exposes the public `LANDSECT` WMTS layer and explicitly labels it section context rather than a parcel boundary. It is not `TILE_001`.
- `services/parcel_geometry.py` contains a disabled future `NlscCadastralProvider`; no NLSC endpoint, authorization, or resolver is configured.
- `services/vnext/property_graph.py` registers `nlsc-cadastral` as `metadata_only`, and `services/vnext/identity_resolution.py` explicitly excludes current NLSC implementations from Property Identity.
- Existing address resolution uses Google/TGOS and existing routing uses Google Routes or a mock. These are not NLSC `ADR_*` or `ROU_*` integrations.

Accordingly, generic transport, a domain model, a public non-requested WMTS layer, or a functionally similar provider is not credited to a requested service code.

## Evidence and classification rules

Repository code and tests were inspected first. A repository-wide exact-code search found no occurrence of `TILE_001`, `CAD_001`–`CAD_011`, `LUI_001`–`LUI_002`, `ADR_001`–`ADR_007`, or `ROU_001`–`ROU_003` before this document was created.

Official names and API function codes come from the current [NLSC API list](https://maps.nlsc.gov.tw/S09SOA/pro/Api_ajax_list.jsp). Service type, response format, binding modes, and applicant groups come from NLSC's [application service integration table](https://maps.nlsc.gov.tw/S09SOA/Download.action?fileName=%E7%94%B3%E8%AB%8B%E6%9C%8D%E5%8B%99%E4%BB%8B%E6%8E%A5%E8%AA%AA%E6%98%8E%E8%A1%A8.pdf), dated 2024-01-03 in the published document. No credential-requiring API call was made for this audit.

Status is assigned per requested service code:

- `NOT_STARTED`: no code-specific endpoint mapping, request schema, adapter, normalized response, or test.
- `DOMAIN_MODEL_ONLY`: a model explicitly names the service code, but no external request exists.
- `TRANSPORT_READY`: the code-specific gateway path and request/response contract exist and pass offline contract tests, but no production connection is proven.
- `ADAPTER_PARTIAL`: a code-specific adapter exists but at least one required layer is incomplete.
- `TEST_ONLY`: code-specific behavior exists only as a fixture, mock, or test contract.
- `PRODUCTION_LIVE`: the requested code is deployed, configured, observable, and proven against NLSC in production.

No requested code meets even `DOMAIN_MODEL_ONLY`, because the repository's models and placeholders are family-level rather than service-code-specific.

`Taiwan gateway required = YES` below is a PropTech deployment requirement, not a claim that NLSC's public table itself proves geographic residency. The checked-in deployment architecture requires a separately evidenced Taiwan-resident fixed host/IP before application. NLSC's table shows URL/IP binding for these application services. `services/production_config.py` validates only fixed HTTPS destination syntax and cannot prove Taiwan residency.

## Gate 1 — 24-code inventory

In the implementation columns, `None` means no file, adapter, route, test, or frontend surface refers to that requested service code. Related-but-non-equivalent repository assets are listed after the inventory and are deliberately not credited.

### TILE

| Code | Official name | Domain | Request/output category | Intended PropTech use | Implementation files | Adapter/provider | Backend route | Tests | Frontend exposure | Taiwan gateway required | Production-connected | Status | Missing work | External blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `TILE_001` | 地籍圖磚 | Cadastral map | WMS/WMTS tile request → tile image | Parcel/GIS cadastral overlay and Professional Workspace visual context; never identity proof by itself | None | None | None | None | None | YES | NO | `NOT_STARTED` | Map approved layer/CRS/tile matrix; implement gateway tile proxy, cache policy, attribution, browser projection, and failure state | NLSC approval; registered URL/IP; Taiwan host evidence; the published applicant list does not include private institutions, so PropTech eligibility requires an NLSC decision |

### CAD

| Code | Official name (API function) | Domain | Request/output category | Intended PropTech use | Implementation files | Adapter/provider | Backend route | Tests | Frontend exposure | Taiwan gateway required | Production-connected | Status | Missing work | External blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `CAD_001` | 指定地號查詢位置 (`CadasMapPosition`) | Cadastral | Land number → XML location | Validate and map-focus a Property Identity parcel candidate | None | None | None | None | None | YES | NO | `NOT_STARTED` | Endpoint mapping, identifier schema, XML parser, normalized location/provenance contract, route, tests, identity link | NLSC approval; registered URL/IP; Taiwan host evidence; private-sector eligibility not established by the published applicant list |
| `CAD_002` | 指定地號查詢著色圖 (`CadasMapImage`) | Cadastral | Land number → JSON coloured-map payload | Highlight a selected parcel in Parcel/GIS and Professional Workspace | None | None | None | None | None | YES | NO | `NOT_STARTED` | Endpoint mapping, JSON contract, image/render handling, attribution, route, tests, UI state | Same CAD-family approval, binding, Taiwan-host, and applicant-eligibility blocker |
| `CAD_003` | 單點坐標查詢地段號 (`GetLandNO`) | Cadastral | Point coordinate → XML land-section/land-number result | Generate parcel identity candidates from a selected map point | None | None | None | None | None | YES | NO | `NOT_STARTED` | Coordinate/CRS request schema, XML parser, ambiguity handling, normalized parcel candidate, route, tests, identity link | Same CAD-family approval, binding, Taiwan-host, and applicant-eligibility blocker |
| `CAD_004` | 地段號查詢坐標 (`GetLandPositionLongitudeLatitude`) | Cadastral | Land-section/land number → XML coordinate | Locate a known parcel identifier and cross-check identity evidence | None | None | None | None | None | YES | NO | `NOT_STARTED` | Identifier/CRS schema, XML parser, coordinate validation, normalized provenance, route, tests | Same CAD-family approval, binding, Taiwan-host, and applicant-eligibility blocker |
| `CAD_005` | 坐標查地段號 (`QryTileMapIndex(1)`) | Cadastral | Coordinate → JSON land-section/land-number result | Coordinate-based parcel/section lookup for Parcel/GIS | None | None | None | None | None | YES | NO | `NOT_STARTED` | Prove distinction from `CAD_003`, map request parameters, normalize JSON and ambiguity, route, tests | Same CAD-family approval, binding, Taiwan-host, and applicant-eligibility blocker; detailed service contract is not present in the repository |
| `CAD_006` | 地段號宗地定位 (`QryTileMapIndex(2)`) | Cadastral | Land-section/land number → JSON parcel positioning result | Focus a Professional Workspace map on a parcel | None | None | None | None | None | YES | NO | `NOT_STARTED` | Map identifier schema, normalize positioning result, route, tests, UI interaction | Same CAD-family approval, binding, Taiwan-host, and applicant-eligibility blocker |
| `CAD_007` | 指定地號查詢土地標示資料 (`CadasAttrQuery`) | Cadastral | Land number → JSON land-description attributes | Add official parcel attributes to Property Identity evidence | None | None | None | None | None | YES | NO | `NOT_STARTED` | Attribute dictionary/version, request schema, fail-closed JSON normalization, provenance, route, tests, evidence integration | Same CAD-family approval, binding, Taiwan-host, and applicant-eligibility blocker; approved attribute scope/terms needed |
| `CAD_008` | 地段代碼回傳測繪段籍屬性 (`GetLandSecInfoNlsc`) | Cadastral | Land-section code → XML survey/cadastral-section attributes | Normalize section metadata used by parcel identifiers and GIS search | None | None | None | None | None | YES | NO | `NOT_STARTED` | Section-code schema, XML parser, reference-data cache/versioning, route, tests | Same CAD-family approval, binding, Taiwan-host, and applicant-eligibility blocker |
| `CAD_009` | 指定門牌查詢地號 (`AddressQueryLand`) | Cadastral/address linkage | Address → XML land-number result(s) | Resolve an address into Property Identity parcel candidates | None | None | None | None | None | YES | NO | `NOT_STARTED` | Canonical address request, XML parser, multiple/no-match handling, provenance, route, tests, candidate review UI | Same CAD-family approval, binding, Taiwan-host, and applicant-eligibility blocker |
| `CAD_010` | 指定範圍查詢地號清單 (`CadasLandNoQuery`) | Cadastral/GIS | Spatial range → JSON land-number list | Multi-parcel discovery inside a Professional Workspace area of interest | None | None | None | None | None | YES | NO | `NOT_STARTED` | Bounds/CRS/size limits, pagination or result caps if supported, JSON normalization, route, tests, selection UI | Same CAD-family approval, binding, Taiwan-host, and applicant-eligibility blocker; approved query limits needed |
| `CAD_011` | 指定地號查詢建號列表與土地權利人類別 (`CadasLandInfo`) | Cadastral/building | Land number → JSON building-number list and land-right-holder category | Create reviewable parcel↔building candidates and rights-category evidence | None | None | None | None | None | YES | NO | `NOT_STARTED` | Define privacy-safe fields, JSON normalization, parcel↔building evidence semantics, provenance, route, tests, review UI | Same CAD-family approval, binding, Taiwan-host, applicant-eligibility, and permitted-use/privacy blocker |

### LUI

| Code | Official name (API function) | Domain | Request/output category | Intended PropTech use | Implementation files | Adapter/provider | Backend route | Tests | Frontend exposure | Taiwan gateway required | Production-connected | Status | Missing work | External blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `LUI_001` | 指定國土利用現況調查成果圖比較 (`LandUseCompare`) | Land-use survey | Specified comparison request → XML comparison | Planning/Zoning due-diligence context and Professional Workspace comparison; not statutory zoning proof | None | None | None | None | None | YES | NO | `NOT_STARTED` | Prove request parameters/comparison semantics, XML parser, classification dictionary/version, provenance, route, tests, comparison UI | NLSC approval; registered URL/IP; Taiwan host evidence; published applicant list does not include private institutions; permitted classification/year coverage needed |
| `LUI_002` | 歷年（或指定年分）國土利用現況調查成果圖屬性 (`LandUsePointYears`) | Land-use survey | Point plus year selection → XML historical/specified-year attributes | Planning/Zoning context and land-use change review; not a legal zoning determination | None | None | None | None | None | YES | NO | `NOT_STARTED` | Point/year schema, XML parser, classification/version normalization, no-data rules, provenance, route, tests, timeline UI | Same LUI-family approval, binding, Taiwan-host, applicant-eligibility, and coverage blocker |

### ADR

| Code | Official name (API function) | Domain | Request/output category | Intended PropTech use | Implementation files | Adapter/provider | Backend route | Tests | Frontend exposure | Taiwan gateway required | Production-connected | Status | Missing work | External blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ADR_001` | 模糊檢索（含通用電子地圖地標、門牌等） (`TextQueryMap`) | Address/map search | Fuzzy text → XML map/address matches | General property/location search with explicit NLSC provenance | None | None | None | None | None | YES | NO | `NOT_STARTED` | Request schema, XML parser, typed result kinds, ranking/ambiguity rules, provenance, route, tests, search UI | NLSC approval; registered URL/IP; Taiwan host evidence; production quota/terms and sample contract |
| `ADR_002` | 門牌服務－模糊檢索 (`TextQueryAddress`) | Address | Fuzzy address text → XML address matches | Canonical address candidates for Address Resolution and Property Identity review | None | None | None | None | None | YES | NO | `NOT_STARTED` | Address schema, XML parser, normalization/ranking, ambiguity review, provenance, route, tests | Same ADR-family approval, binding, Taiwan-host, quota/terms, and sample-contract blocker |
| `ADR_003` | 門牌服務－路名清單 (`ListRoad`) | Address reference | Road-list request → XML road list | Structured road selection/autocomplete for address resolution | None | None | None | None | None | YES | NO | `NOT_STARTED` | Prove required administrative inputs, XML parser, reference cache/version, route, tests, selector UI | Same ADR-family approval, binding, Taiwan-host, quota/terms, and sample-contract blocker |
| `ADR_004` | 門牌服務－巷弄清單 (`ListRoadLaneAlley`) | Address reference | Lane/alley-list request → XML lane/alley list | Structured lane/alley selection for address resolution | None | None | None | None | None | YES | NO | `NOT_STARTED` | Prove parent-key inputs, XML parser, reference cache/version, route, tests, selector UI | Same ADR-family approval, binding, Taiwan-host, quota/terms, and sample-contract blocker |
| `ADR_005` | 坐標回傳門牌服務－點坐標 (`PointQueryAddr`) | Reverse address | Point coordinate → GeoJSON/JSON/XML address results | Reverse-resolve a selected property point with NLSC provenance | None | None | None | None | None | YES | NO | `NOT_STARTED` | Coordinate/CRS schema, select one approved format, geometry/address normalization, ambiguity rules, route, tests, UI | Same ADR-family approval, binding, Taiwan-host, quota/terms, and sample-contract blocker |
| `ADR_006` | 坐標回傳門牌服務－線坐標 (`LineQueryAddr`) | Spatial address | Line geometry → GeoJSON/JSON/XML address results | Find addresses along a Professional Workspace corridor | None | None | None | None | None | YES | NO | `NOT_STARTED` | Geometry/CRS/vertex limits, select format, bounded feature normalization, route, tests, GIS result UI | Same ADR-family approval, binding, Taiwan-host, quota/terms; approved geometry/result limits needed |
| `ADR_007` | 坐標回傳門牌服務－面坐標 (`PolygonQueryAddr`) | Spatial address | Polygon geometry → GeoJSON/JSON/XML address results | Find addresses within a Professional Workspace area | None | None | None | None | None | YES | NO | `NOT_STARTED` | Geometry/CRS/area/vertex limits, select format, bounded feature normalization, route, tests, GIS result UI | Same ADR-family approval, binding, Taiwan-host, quota/terms; approved geometry/result limits needed |

### ROU

| Code | Official name (API function) | Domain | Request/output category | Intended PropTech use | Implementation files | Adapter/provider | Backend route | Tests | Frontend exposure | Taiwan gateway required | Production-connected | Status | Missing work | External blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ROU_001` | 路徑規劃服務－距離最短路線 (`RoutesQueryByDist`) | Routing | Route request → KMZ/JSON/KML shortest-distance route | Distance-prioritized accessibility analysis and Professional Workspace route display | None | None | None | None | None | YES | NO | `NOT_STARTED` | Prove request/mode schema, choose JSON or KML contract, geometry/distance normalization, route, cache/rate rules, tests, UI | NLSC approval; registered URL/IP; Taiwan host evidence; production quota/terms and sample contract |
| `ROU_002` | 路徑規劃服務－時間最短路線 (`RoutesQueryByTime`) | Routing | Route request → KMZ/JSON/KML shortest-time route | Time-prioritized accessibility analysis and commute evidence | None | None | None | None | None | YES | NO | `NOT_STARTED` | Prove request/mode/time semantics, choose format, duration/geometry normalization, route, cache/rate rules, tests, UI | Same ROU-family approval, binding, Taiwan-host, quota/terms, and sample-contract blocker |
| `ROU_003` | 路徑規劃服務－節點查詢 (`RoutesNodes`) | Routing reference | Node query → CSV nodes | Route-network diagnostics or waypoint preparation in Professional Workspace | None | None | None | None | None | YES | NO | `NOT_STARTED` | Prove node-query semantics, bounded CSV parser/schema, cache/versioning, route, tests, GIS UI if justified | Same ROU-family approval, binding, Taiwan-host, quota/terms, and sample-contract blocker |

## Gate 2 — exact counts

Counts are requested-code-specific. Shared transport and analogous providers are excluded.

| Measure | Count | Rule |
|---|---:|---|
| Requested service codes | **24** | 1 TILE + 11 CAD + 2 LUI + 7 ADR + 3 ROU |
| Implemented adapters | **0/24** | No adapter maps or names a requested service code |
| Test-only | **0/24** | No test or fixture names a requested service code |
| Gateway-ready / transport-ready | **0/24** | The generic terrain gateway contract maps none of the requested codes |
| Production-live | **0/24** | No code-specific production connection exists |
| Not started | **24/24** | All 24 have status `NOT_STARTED` |

**0/24 production-live.**

| Family | Requested | Adapter | Test-only | Transport-ready | Production-live | Not started |
|---|---:|---:|---:|---:|---:|---:|
| TILE | 1 | 0 | 0 | 0 | 0 | 1 |
| CAD | 11 | 0 | 0 | 0 | 0 | 11 |
| LUI | 2 | 0 | 0 | 0 | 0 | 2 |
| ADR | 7 | 0 | 0 | 0 | 0 | 7 |
| ROU | 3 | 0 | 0 | 0 | 0 | 3 |

## Gate 3 — transport architecture

Target flow:

```text
Browser
  -> Render FastAPI product route
  -> NLSC service-code adapter
  -> Taiwan-resident gateway route
  -> NLSC bound service endpoint
```

Current repository state:

```text
Terrain UI / POST /terrain-risk/analyze
  -> NlscTerrainProvider
  -> NlscGatewayAdapter
  -> POST {NLSC_GATEWAY_BASE_URL}/nlsc/terrain/point
  -> gateway implementation absent from this repository
  -> requested NLSC service mapping absent
```

| Layer | Evidence | State for the 24 requested codes | Required closure |
|---|---|---|---|
| Transport | Fixed HTTPS gateway origin, backend bearer token, four-second timeout, no redirects, bounded terrain input, and fail-closed handling exist in `services/adapters/nlsc_gateway_adapter.py`; env slots exist in `render.yaml` | Shared foundation only; **0/24 transport-ready** | Implement and deploy the Taiwan gateway, health/observability, service-specific paths, and prove Taiwan fixed-IP residency |
| Service endpoint mapping | Only repository-specific `/nlsc/terrain/point` exists | None | Map each approved NLSC function code and upstream endpoint explicitly; never use a generic provider label as proof |
| Request schema | Only `{lat, lng, radius_m}` for terrain exists | None | Add code-specific Pydantic/domain schemas, CRS rules, identifier rules, bounds, size limits, and allowlists |
| Response normalization | Only slope/elevation terrain output is normalized | None | Parse XML/JSON/GeoJSON/KML/KMZ/CSV/tile responses into versioned, bounded product contracts |
| Provenance | Generic `source: NLSC` and source metadata exist | Insufficient | Record service code, provider, retrieval time, upstream version/date when supplied, query coverage, gateway request/correlation ID, and transformation version |
| Caching | No NLSC-specific application cache exists | None | Define per-service TTL, key canonicalization, negative caching, invalidation, storage location, and NLSC-term compliance; never cache sensitive/unpermitted fields |
| Authentication | Render→gateway bearer configuration exists; the value is backend-only | Partial shared foundation | Establish gateway secret rotation and NLSC-side URL/IP binding or other approved authentication without exposing secrets to the browser |
| Rate controls | Adapter has a timeout and fail-closed behavior but no NLSC-specific limiter, retry budget, concurrency cap, or circuit breaker | None | Enforce product-user limits at Render and upstream quotas/concurrency at the Taiwan gateway; add metrics and bounded retry policy only if permitted |
| Browser projection | CSP permits `wmts.nlsc.gov.tw`; LANDSECT can render in the terrain/cadastral UI | Not a requested-code integration | Expose only normalized product routes or approved tile URLs; retain attribution, unavailable states, and no credential leakage |
| Property Identity integration | `nlsc-cadastral` is `metadata_only`; the identity engine deliberately does not adapt NLSC | None | Create reviewable candidates/evidence, source lineage, ambiguity states, and explicit human confirmation; never auto-promote a visual tile or local parcel model to official identity |

The current generic transport is valuable because its fixed-origin and secret-handling boundaries can be extended. It is not sufficient because the Taiwan gateway server, NLSC binding, service-code endpoints, code-specific schemas, normalization, cache/rate policy, and production evidence are all absent.

## Gate 4 — PropTech product mapping

This is a value map, not an implementation claim.

| Product domain | Relevant requested codes | Intended role | Boundary |
|---|---|---|---|
| Property Identity | `CAD_001`, `CAD_003`–`CAD_009`, `CAD_011`; `ADR_002`, `ADR_005` | Address↔parcel candidate resolution, parcel location/attributes, parcel↔building candidates | Candidates require provenance and human confirmation; tiles and local models are not identity proof |
| Parcel/GIS | `TILE_001`; `CAD_001`–`CAD_010` | Cadastral visual context, coordinate/land-number lookup, section metadata, bounded multi-parcel discovery | Raster tiles are not legal vectors; requested `MAP_*`/`WFS_*` services are outside this audit |
| Building | `CAD_011` | Building-number candidates associated with a land number and rights-holder category evidence | Not a building polygon, permit record, owner identity, or ownership determination |
| Planning/Zoning | `LUI_001`, `LUI_002` | Current/historical land-use survey context and comparison | Observed land use is not statutory zoning or a legal development-right conclusion |
| Terrain | None of the 24 | No requested code has a proven terrain/slope/elevation meaning | The repository's generic terrain gateway cannot be reassigned to LUI or CAD |
| Professional Workspace | `TILE_001`, `CAD_002`, `CAD_006`, `CAD_008`, `CAD_010`, `LUI_001`, `LUI_002`, `ADR_006`, `ADR_007`, `ROU_001`–`ROU_003` | Layer display, parcel selection, temporal comparison, corridor/area address search, route display/diagnostics | Each result remains source-coded and bounded; no bulk export or redistribution is assumed |
| Address resolution | `ADR_001`–`ADR_007`; `CAD_009` | Text/autocomplete/reverse/spatial address resolution and address→land-number linkage | Google/TGOS results do not satisfy this mapping |
| Routing | `ROU_001`–`ROU_003` | Shortest-distance/time routes and routing-node lookup | Google Routes and mock estimates do not satisfy this mapping |

## Gate 5 — next three implementation slices

These are the next slices **after** a controlled Taiwan host/fixed IP is available and the named services are approved. Each slice must remain unavailable until its own NLSC authorization and contract are proven.

### 1. Property Identity: address to parcel candidate (`CAD_009` + `CAD_001`)

- **Dependency:** NLSC approval for both service codes; confirmed private-sector eligibility and permitted use; registered gateway URL/IP; production XML samples and parameter/CRS documentation; Taiwan gateway health and secret rotation.
- **Adapter needed:** a backend `NlscParcelIdentityAdapter` with `address_to_land_numbers` (`CAD_009`) and `land_number_to_position` (`CAD_001`), backed by two explicit Taiwan-gateway routes and surfaced through a bounded Property Identity candidate endpoint.
- **Normalization needed:** canonical input address; county/town/section/land-number components; zero/one/many candidate states; validated EPSG:4326 position; service code, retrieval time, upstream identifiers, source record ID, coverage, and transformation version. Malformed or ambiguous data must not confirm identity.
- **Tests:** offline XML fixtures for one/many/no match and malformed/oversized responses; request/CRS validation; fixed-origin/no-redirect/secret-leak tests; gateway 401/429/5xx/timeout tests; provenance assertions; identity test proving candidates remain unconfirmed; production smoke test with a non-sensitive approved address.
- **Production acceptance criterion:** an approved real address produces reviewable NLSC land-number candidate(s), and a selected candidate is cross-checked by `CAD_001`; both observations display the exact service code and provenance, remain unconfirmed until user review, and fail closed to unavailable without approved production configuration.
- **Explicit out of scope:** legal parcel boundary geometry, ownership identity, `CAD_007` attributes, `CAD_011` building links, bulk resolution, automatic identity confirmation/merge, and storage of raw upstream payloads.

### 2. Planning/Zoning: historical land-use context (`LUI_002`)

- **Dependency:** NLSC approval and applicant eligibility for `LUI_002`; registered gateway URL/IP; documented point CRS, supported years, classification dictionary/version, XML schema, coverage, and permitted caching/display.
- **Adapter needed:** a `NlscLandUseAdapter.point_years` method through a dedicated gateway route and a bounded backend Planning context route keyed by validated coordinate and optional year selection.
- **Normalization needed:** observation year, official classification code/label, point/coverage metadata, no-data versus unavailable distinction, retrieval timestamp, service code, classification version, and the explicit statement “land-use survey context, not statutory zoning.”
- **Tests:** XML fixtures across supported years/classes; unknown classification and missing-year behavior; coordinate/year bounds; malformed/oversized response; timeout/quota/auth failures; cache-key and TTL tests; provenance and UI caveat tests; approved production smoke point.
- **Production acceptance criterion:** an approved Taiwan point returns real NLSC year-specific observations with exact `LUI_002` provenance and classification version; missing/unavailable evidence is never rendered as compliant zoning, and no response is relabeled as a legal zoning result.
- **Explicit out of scope:** `LUI_001` comparison, zoning-law ingestion, development-right decisions, parcel-boundary intersection, nationwide preload, bulk export, and legal advice.

### 3. Professional GIS Workspace: cadastral tile overlay (`TILE_001`)

- **Dependency:** NLSC approval and applicant eligibility for `TILE_001`; approved WMS/WMTS binding mode; registered gateway URL/IP; layer identifier, CRS, tile matrix, zoom bounds, attribution, cache and redistribution terms; capacity budget for tile traffic.
- **Adapter needed:** an allowlisted gateway tile endpoint plus a Render-side `NlscCadastralTileAdapter`/proxy route that accepts only bounded `z/x/y` (and an approved matrix), never arbitrary upstream URLs, and emits safe cache/content headers.
- **Normalization needed:** tile-matrix/coordinate translation, content-type and size validation, transparent unavailable/error tile behavior, attribution, service code, layer version/date when supplied, and request correlation metadata outside the image payload.
- **Tests:** coordinate and zoom bounds; SSRF/path traversal rejection; content-type/size checks; no redirects or credential exposure; 401/404/429/5xx/timeout behavior; cache headers/TTL; tile alignment visual regression at approved control points; frontend attribution and unavailable-state tests.
- **Production acceptance criterion:** the Professional Workspace can toggle a correctly aligned real `TILE_001` overlay at approved zooms; every tile request follows Render→Taiwan gateway→NLSC, attribution is visible, secrets never reach the browser, quota/cache metrics are observable, and failure does not masquerade as an empty legal parcel map.
- **Explicit out of scope:** WFS/vector boundaries, parcel click-identify, offline download, printing/export/redistribution, legal-boundary claims, `LANDSECT` substitution, and all other CAD/MAP services.

## Final gate

**FINAL: NO-GO**

Go requires at minimum: external approval/eligibility for the selected codes, a proven Taiwan-resident fixed gateway, code-specific endpoint mappings and contracts, normalization/provenance, offline and production acceptance tests, browser/product integration where applicable, and production observability. None of those conditions is complete for any requested code today.
