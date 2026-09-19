# NLSC LUI_002 planning evidence slice v1

- Audit date: 2026-09-20
- Repository branch: `audit/planning-lui002-slice`
- Base: `origin/main` at `14c21f0`
- Scope: contract audit and design only; no NLSC data-service request was made
- Decision: **NO-GO for production enablement**; the offline adapter/evidence contract may be implemented behind a disabled feature flag after the acceptance prerequisites in section 13 are owned

## 1. LUI_002 PLANNING AUDIT RESULT

| Requested result | Finding |
| --- | --- |
| Official contract | `LUI_002`, API operation `LandUsePointYears`, officially means **歷年（或指定年分）國土利用現況調查成果圖屬性**: attributes from historical or a specified-year national land-use **survey** result at one coordinate. It does not return a planning/zoning designation. |
| Coverage | The survey programme covers Taiwan proper and includes Penghu, Kinmen and Matsu work, but coverage and observation year vary by area. The LUI_002 manual does not promise complete coverage for every point/year. Product coverage must therefore be recorded per returned observation and proven by a regional/year acceptance matrix. |
| Input | HTTP `GET`; required ROC/Minguo year (`0` means all available years), required `X`, required `Y`, and optional CRS code. Official CRS values are `EPSG4326` (default/WGS 84), `EPSG3825` (TWD97/TM2 zone 119, labelled Penghu), and `EPSG3826` (TWD97/TM2 zone 121, labelled Taiwan). No parcel identifier, land number, address, polygon, or PropertyEntity identifier is accepted. |
| Output | UTF-8 `application/xml`; zero or more documented `ITEM` observations containing `YEAR`, `LYEAR`, `LMONTH`, level 1/2/3 classification codes and labels, plus the highest available classification code and label. The published manual does not define an enclosing collection element, error payload, empty-result payload, ordering, uniqueness, size limit, rate limit, or publication timestamp. |
| Authority boundary | NLSC is an official source for the reported land-use survey observation. For PropTech planning/zoning use, the result is **reference-only**. NLSC states that these maps express current land condition, have no legal effect, and do not determine roads, rights, or actual boundaries. The result is not statutory zoning and requires confirmation with the competent local planning, land, and/or building authority for any consequential decision. |
| Suggested adapter | Render product route -> fixed authenticated Taiwan gateway route `POST /nlsc/lui-002/point-years` -> fixed upstream `GET /other/LandUsePointYears/...` -> strict XML parser -> `PlanningObservationResultV1`. No user-supplied upstream URL, operation name, arbitrary path, or credential crosses either boundary. |
| Suggested evidence model | One `planning.land_use_observation` evidence item per returned `ITEM`, linked to the exact `geo_reference` context node and optionally displayed beside a parcel relation. Source type is `official`, evidence status is `limited`, spatial scope is `point_only`, and authority use is `reference_only_requires_local_confirmation`. |
| Acceptance gate | **Closed.** NLSC approval/credentials, registered URL/IP, terms, exact success/empty/error fixtures, limits, coverage matrix, classification mapping, and a separately approved credentialed acceptance run are absent. The current repository has no LUI_002-specific route, adapter, model, fixture, or test. |

**FINAL: NO-GO** for production traffic or user-visible planning claims.

## 2. Authoritative sources and audit method

Official NLSC material is authoritative for this audit:

1. [NLSC API list](https://maps.nlsc.gov.tw/S09SOA/pro/Api_ajax_list.jsp) identifies `LUI_002`, its Chinese name, `LandUsePointYears`, the national-land-use API family, and that application is required.
2. [NLSC WFS/API technical manual](https://maps.nlsc.gov.tw/S09SOA/Download.action?fileName=%E5%9C%8B%E5%9C%9F%E6%B8%AC%E7%B9%AA%E5%9C%96%E8%B3%87%E6%9C%8D%E5%8B%99%E9%9B%B2%E4%BB%8B%E6%8E%A5%E6%9C%8D%E5%8B%99%E6%8A%80%E8%A1%93%E6%89%8B%E5%86%8A.pdf), dated 2024-11-01 (ROC 113-11-01), defines the URI, parameters, CRS options, XML media type and documented item fields.
3. [NLSC application-service integration table](https://maps.nlsc.gov.tw/S09SOA/Download.action?fileName=%E7%94%B3%E8%AB%8B%E6%9C%8D%E5%8B%99%E4%BB%8B%E6%8E%A5%E8%AA%AA%E6%98%8E%E8%A1%A8.pdf) classifies LUI_002 as an application API with URL/IP binding and XML output.
4. [NLSC service introduction](https://maps.nlsc.gov.tw/S09SOA/pro/intro.jsp) says that private groups and companies may apply for the national land-use survey API in the current ROC 115 service process. Eligibility is not approval; PropTech must obtain and retain its own approval.
5. [NLSC land-use survey information](https://www.nlsc.gov.tw/cl.aspx?n=13705), [work status and coverage](https://www.nlsc.gov.tw/cp.aspx?n=13711), and [survey workflow](https://www.nlsc.gov.tw/cp.aspx?n=13710) describe the survey programme, regional responsibilities, update cadence, imagery and field-survey method.
6. Official classification pages define distinct eras: [ROC 82 and 95-104](https://www.nlsc.gov.tw/cp.aspx?n=13706), [ROC 105-108](https://www.nlsc.gov.tw/cp.aspx?n=13720), and [ROC 109 onward](https://www.nlsc.gov.tw/cp.aspx?n=13721).
7. The [NLSC map notice](https://maps.nlsc.gov.tw/T09/mobilemap.action) provides the controlling use boundary: displayed land-use survey information describes land condition, has no legal effect, and questions must be taken to the producing authority.

The audit downloaded and read the official manual and inspected public documentation. It did **not** call `api.nlsc.gov.tw`, use credentials, or infer a contract from an undocumented live response. Repository findings were checked against `docs/vnext/evidence-architecture-v1.md`, `docs/vnext/data-source-registry-v1.md`, `docs/vnext/property-identity-architecture-v1.md`, `docs/nlsc-requested-service-integration-matrix-v1.md`, and the existing generic terrain gateway adapter.

## 3. Exact official contract

### 3.1 Meaning and access

`LUI_002` returns land-use survey classification attributes at a specified point for one ROC year or for all years available to the service. “Land use” here means the observed/survey-classified use of land. It must not be translated to `zoning`, `use district`, `development permission`, `buildable`, `compliant`, or `legal use`.

The service requires application. Official material describes URL/IP binding. The Taiwan-resident gateway in this design is a PropTech deployment and data-egress control; the official documents reviewed do not themselves prove or require Taiwan residency. A `.tw` hostname or syntactically valid fixed URL is not residency evidence.

### 3.2 URI and parameters

Official base and paths:

```text
GET https://api.nlsc.gov.tw/other/LandUsePointYears/{year_roc}/{x}/{y}/
GET https://api.nlsc.gov.tw/other/LandUsePointYears/{year_roc}/{x}/{y}/{crs_code}
```

| Path parameter | Required | Official meaning | Product rule |
| --- | --- | --- | --- |
| `year_roc` | yes | ROC/Minguo year; `0` requests historical/all available years | Product accepts `all` -> `0`, or a year in the acceptance-tested allowlist. No guessed minimum/current range. |
| `x` | yes | query-point X | Product derives it server-side from the selected evidence-backed context point. |
| `y` | yes | query-point Y | Product derives it server-side from the selected evidence-backed context point. |
| `crs_code` | no | `EPSG4326` default, `EPSG3825`, or `EPSG3826`; the official example uses the numeric shorthand `4326` | Slice v1 sends WGS 84 only, using the exact gateway form proven during acceptance. It does not expose CRS choice to the browser. |

The product deliberately supports less than the provider contract: V1 normalizes a stored context point to EPSG:4326 before egress. That removes browser-controlled coordinate order/CRS ambiguity while retaining island support. Coordinate conversion must be deterministic, versioned, and already supported by the point evidence; this slice does not introduce a new geocoder or cadastral resolver.

### 3.3 Response

Official media type and encoding are `application/xml; charset=UTF-8`. The manual documents repeated `ITEM` records:

| XML element | Official description | Normalized field | Rule |
| --- | --- | --- | --- |
| `YEAR` | 圖磚年度 (tile/data year) | `dataset_year_roc` | Integer source value; do not replace with request year. |
| `LYEAR` | 調查年度 (survey year) | `survey_year` | Integer source value; preserve its calendar representation. The official example uses Gregorian `2017`. |
| `LMONTH` | 調查月份 | `survey_month` | Integer `1..12`; absence or invalidity makes the observation limited/invalid, never current. |
| `Lcode_C1` | level-1 code | `classification.level1.code` | String; preserve leading zeroes. |
| `Lname_C1` | level-1 Chinese label | `classification.level1.label_zh_tw` | Source text, bounded and XML-decoded. |
| `Lcode_C2` | level-2 code | `classification.level2.code` | String; preserve leading zeroes. |
| `Lname_C2` | level-2 Chinese label | `classification.level2.label_zh_tw` | Source text, bounded and XML-decoded. |
| `Lcode_C3` | level-3 code | `classification.level3_code` | Nullable because classification depth differs by era. |
| `LCODE` | highest classification code | `classification.highest.code` | String; never interpreted without the era-specific scheme. |
| `NAME` | highest classification Chinese label | `classification.highest.label_zh_tw` | Source text; not a zoning label. |

The official example for an all-years request returns separate `ITEM` records for dataset years 106 and 108. The manual does not define an enclosing root, empty result, error document, duplicate rule, boundary-hit behavior, or ordering. Those are contract unknowns, not implementation details to guess. Production parsing remains disabled until approved fixtures establish them.

### 3.4 Geographic and temporal coverage

- Survey material describes nationwide work across Taiwan proper and the principal islands of Penghu, Kinmen and Matsu, with some attached smaller islands added after the initial ROC 95-97 survey depending on imagery.
- The programme is mosaicked from areas surveyed/updated at different times. `survey_year` and `survey_month`, not the retrieval date or a global “latest” label, determine the observation period.
- Current official programme material describes a two-year update cadence for areas maintained by the Ministry of the Interior and a five-year cadence for Forestry and Nature Conservation Agency areas. A programme cadence is not a freshness guarantee for a particular point.
- Classification definitions changed across ROC 82, 95-104, 105-108 and 109 onward. Codes and labels are not safely comparable across eras without a versioned mapping.
- LUI_002 is a point query. A returned value proves only that the service classified that coordinate for that observation period. It provides no parcel polygon, intersection percentage, boundary precision, address match, or whole-parcel coverage.
- A successful response at one point/year does not prove service completeness elsewhere. An empty or undocumented response remains `unknown` until NLSC supplies an accepted no-data contract.

## 4. Authority and product-safety boundary

The system must preserve all of these distinctions:

```text
official source != legal authority for the product question
observed land use != statutory zoning/use district
point observation != parcel-wide condition
historical survey != current condition
classification label != permitted use
no result != no restriction
```

LUI_002 evidence may support due-diligence context and a historical land-use timeline. It must never become or be used alone to derive:

- legal entitlement, land right, boundary, or ownership;
- development, subdivision, building, occupancy, or use approval;
- guaranteed zoning or a statutory urban/non-urban land-use designation;
- buildability, development potential, compliant/non-compliant use, floor-area ratio, building coverage ratio, height, setback, access, or road status;
- a safety/absence conclusion when data is unknown, missing, stale, conflicting, or unavailable.

For a planning/zoning answer, the UI and exports must require confirmation with the competent local authority and the applicable plan, zoning/use-district, land-use-control, building, and cadastral records. A future local-authority zoning source is a separate fact type and adapter, not an “upgrade” or relabel of LUI_002.

## 5. Smallest production-safe slice

### 5.1 Flow and trust boundaries

```text
authenticated PropertyEntity read
  -> selected linked geo_reference evidence
  -> optional linked parcel shown as context only
  -> Render planning application service
  -> fixed HTTPS Taiwan gateway origin + backend credential
  -> POST /nlsc/lui-002/point-years
  -> fixed GET api.nlsc.gov.tw/other/LandUsePointYears/...
  -> bounded XML transport result
  -> NlscLandUseAdapter normalization
  -> one point PlanningObservation per ITEM
  -> evidence_items + evidence_links
  -> reference-only display
```

Responsibilities:

| Unit | One responsibility |
| --- | --- |
| Product route | Authenticate, authorize workspace access, load the PropertyEntity/context links, validate request intent, return a bounded result. |
| Planning application service | Ensure the point evidence belongs to the property context, construct the gateway request, normalize outcomes, create immutable evidence, and detect conflicts. |
| Render adapter | Call one fixed gateway route with no redirects, bounded timeout/body, server credential, correlation ID, and fail-closed error mapping. |
| Taiwan gateway | Accept only the LUI_002 DTO, map it to the one fixed NLSC host/path, apply assigned NLSC binding/auth, bound the XML response, and return a transport DTO. It exposes no generic proxy. |
| XML normalizer | Defensively parse documented fields, preserve unknown codes, attach contract/classification versions, and never infer missing values. |
| Evidence writer | Persist provenance/lineage and link each observation to the exact geo-reference subject. |
| Display mapper | Render point scope, observation period, source, limitations, freshness and local-confirmation warning without zoning language. |

### 5.2 Request DTO — product

Product operation:

```text
POST /v1/properties/{property_entity_id}/planning/land-use-observations:query
```

```json
{
  "context": {
    "geo_reference_node_id": "uuid",
    "coordinate_evidence_id": "uuid",
    "parcel_node_id": "uuid-or-null"
  },
  "year_selection": {
    "mode": "all",
    "year_roc": null
  }
}
```

Contract rules:

- `geo_reference_node_id` must be linked to the path PropertyEntity in the authenticated workspace.
- `coordinate_evidence_id` must describe that geo-reference node, contain a valid EPSG:4326 point, retain its own source/status, and not be superseded or conflicting.
- `parcel_node_id` is optional display context and must be linked to the same PropertyEntity. It is never sent to NLSC and never changes point scope.
- `mode` is `all` or `specified`. `all` requires `year_roc=null`; `specified` requires an acceptance-tested ROC year.
- The browser cannot submit coordinates, CRS, provider host/path, operation name, source status, labels, or authority claims.
- Address, parcel/lot number, and free-text input are rejected by this operation. They require a separately evidenced resolver followed by explicit selection of a geo-reference.

### 5.3 Request DTO — fixed gateway

```json
{
  "request_id": "opaque-correlation-id",
  "year_roc": 0,
  "x": 121.5654,
  "y": 25.0330,
  "crs": "EPSG4326"
}
```

Gateway rules:

- route is exactly `POST /nlsc/lui-002/point-years`;
- upstream scheme/host/prefix and `LandUsePointYears` are constants;
- v1 allows only `EPSG4326`, finite coordinates inside the approved coverage geometry, `0` or an approved year, and a bounded decimal representation;
- upstream redirects are rejected; DNS/IP policy, TLS, timeouts, concurrency, rate limiting, and maximum body size are fixed configuration;
- gateway logs contain request/correlation metadata, status class, duration and response size, but no credential or full raw XML;
- raw provider XML is not returned to the browser and is retained only if approved terms and the evidence retention policy allow it.

### 5.4 Response DTO — normalized result

```json
{
  "schema": "planning-observation-result-v1",
  "request_id": "opaque-correlation-id",
  "property_entity_id": "uuid",
  "status": "available",
  "context": {
    "geo_reference_node_id": "uuid",
    "coordinate_evidence_id": "uuid",
    "parcel_node_id": null,
    "point": {"longitude": 121.5654, "latitude": 25.0330, "crs": "EPSG:4326"},
    "spatial_scope": "point_only",
    "parcel_scope": "not_established"
  },
  "observations": [
    {
      "observation_id": "uuid",
      "dataset_year_roc": 108,
      "survey_year": 2019,
      "survey_month": 11,
      "observation_precision": "month",
      "classification": {
        "scheme_id": "nlsc-land-use-roc104-v1",
        "scheme_status": "known",
        "level1": {"code": "06", "label_zh_tw": "公共利用土地"},
        "level2": {"code": "0601", "label_zh_tw": "政府機關"},
        "level3_code": "060100",
        "highest": {"code": "060100", "label_zh_tw": "政府機關"}
      },
      "evidence_id": "uuid",
      "evidence_status": "limited",
      "authority_use": "reference_only_requires_local_confirmation",
      "limitations": [
        "point_only",
        "not_statutory_zoning",
        "not_parcel_coverage",
        "freshness_unknown"
      ]
    }
  ],
  "provenance": {
    "source_id": "nlsc-land-use-survey",
    "source_type": "official",
    "service_code": "LUI_002",
    "operation": "LandUsePointYears",
    "contract_version": "nlsc-lui002-2024-11-01",
    "adapter_version": "nlsc-lui002-adapter-v1",
    "gateway_version": "deployment-version",
    "retrieved_at": "RFC3339 timestamp",
    "request_fingerprint": "sha256"
  },
  "freshness": {
    "status": "unknown",
    "reason": "provider_response_has_no_publication_or_expiry_timestamp"
  },
  "conflicts": [],
  "errors": []
}
```

Top-level `status` is one of `available`, `partial`, `no_data`, `unavailable`, `unknown`, `stale`, or `conflicting`. `available` means at least one provider record parsed; it does not weaken the observation-level `limited` evidence status or authority boundary. `no_data` is not enabled until NLSC's exact empty-result semantics are accepted.

## 6. Provenance and PropertyEntity evidence mapping

The smallest slice does not add a “zoning” property field or a planning graph node. It reuses the evidence architecture:

| PropTech stage | Mapping |
| --- | --- |
| `PropertyEntity` | Authenticated workspace aggregate used only to select and authorize context; it receives no zoning/buildability attribute. |
| `parcel/context` | Exact linked `geo_reference` plus its coordinate evidence; an optional linked parcel is display context only and does not broaden the point. |
| `planning observation` | One immutable `PlanningObservationDTO` per valid LUI_002 `ITEM`, retaining source year/month, classification and point scope. |
| `evidence` | One `planning.land_use_observation` evidence item per observation, with official provenance, limited status and lineage to the coordinate evidence. |
| `display` | Point-specific historical/reference card or timeline with source, freshness, limitations and mandatory local-authority confirmation copy. |

```text
PropertyEntity property node
  -> existing confirmed/proposed property_geo_reference relation
  -> geo_reference node + coordinate evidence
  -> LUI_002 PlanningObservationDTO (read model)
  -> evidence_item fact_type planning.land_use_observation
  -> evidence_link describes geo_reference node
  -> optional parcel node shown only as context
  -> evidence card/timeline
```

Recommended stored evidence fields:

| Evidence field | Value/rule |
| --- | --- |
| `fact_type` | `planning.land_use_observation` |
| `value_schema` | `nlsc-lui002-land-use-observation-v1` |
| `source_id` / `source_type` | `nlsc-land-use-survey` / `official` |
| `source_environment` | `production` only after the gate opens; fixtures use `test` |
| `provider` | `nlsc-lui002-adapter-v1` |
| `source_record_id` | null unless NLSC later documents a stable record ID; never synthesize one from the label |
| `value` | documented source fields plus normalized classification and observation-period precision |
| `retrieved_at` | actual system receipt time |
| `effective_from/to` | null in v1: `LYEAR`/`LMONTH` is stored as a month-precision observation period, not fabricated into an exact effective instant |
| `expires_at` | null until a reviewed fact-type freshness policy exists |
| `coverage_status` | `partial` |
| `coverage` | query point/CRS, `point_only`, coordinate evidence ID, optional parcel context, accepted region/year matrix version, and `parcel_scope=not_established` |
| `evidence_status` | `limited` for every LUI_002 planning use |
| `quality_status` | `limited`; parser validations and any unknown/missing classification depth are detailed in `quality` |
| `license_status` | `owner_review_required` until terms are approved, then `approved` for the exact stored/displayed fields |
| `lineage` | service code/operation, manual version, gateway/adapter versions, normalized request fingerprint, coordinate evidence ID, classification scheme ID, transformations and response fingerprint |
| `raw_artifact_ref` | null by default; allowed only under approved terms, encrypted retention and tenant access policy |

`nlsc-land-use-survey` must be added to both the documentation and code source registries as `metadata_only`, with request append disabled. It may move to `production_accepted` only when section 13 passes. It must not reuse `nlsc-cadastral`: the source product, semantics, approval and acceptance evidence differ.

## 7. Version and freshness policy

Use independent versions; do not collapse them into a single “latest” value:

- provider contract: `nlsc-lui002-2024-11-01` until a newer official manual is reviewed;
- normalized schema: `nlsc-lui002-land-use-observation-v1`;
- adapter/parser: `nlsc-lui002-adapter-v1`;
- gateway deployment: immutable release identifier;
- accepted coverage matrix: immutable version/date;
- classification scheme per observation:
  - ROC 82: `nlsc-land-use-roc82-v1`;
  - ROC 95-104: `nlsc-land-use-roc95-v1` (three levels, 103 level-3 classes);
  - ROC 105-108: `nlsc-land-use-roc104-v1` (the official programme output for this period was commonly maintained to level 2 even though the classification table has three levels);
  - ROC 109 onward: `nlsc-land-use-roc108-v1` (three levels, 93 level-3 classes);
  - any other/unmapped year: `unknown`, preserving source codes and marking the observation limited.

`dataset_year_roc`, `survey_year`, and `survey_month` are source data. `retrieved_at` is transport provenance. Neither is a publication/effective timestamp. The two-/five-year programme cadence must not produce a synthetic TTL. Until NLSC supplies a per-record publication/update contract and product owners approve a fact-type policy, UI freshness is `unknown`; historical facts may be displayed with their survey month but never labelled current.

A later retrieval never overwrites an earlier item. Identical content may deduplicate by a canonical content hash; changed content creates a new evidence version with `supersedes_evidence_id`, preserving both records.

## 8. Conflict handling

1. Preserve every valid `ITEM`; do not select the highest code, newest row, or first row as truth.
2. Multiple incompatible classifications for the same normalized point, dataset year and survey month create a conflict set and top-level `conflicting` status.
3. Changes across different observation periods form a timeline, not a conflict.
4. An unknown classification code/era is preserved verbatim and marked `limited`; it is not mapped to the nearest known label.
5. A superseded, conflicting, stale or no-longer-linked coordinate evidence item blocks a new request. Existing observations remain historical evidence with the old context lineage.
6. Different points associated with one property/parcel remain separate observations. The system may not vote, average, union, or extrapolate them to the parcel.
7. Local statutory zoning and LUI_002 observed use are different fact types. Different values are not automatically a source conflict, but the display must highlight a due-diligence discrepancy and must never let LUI_002 overwrite local-authority evidence.
8. Any unresolved material conflict blocks automated conclusions, report language claiming zoning/buildability, and consequential workflow transitions. An authorized human may record a review decision citing both items, but cannot convert LUI_002 into legal proof.

## 9. Unavailable and unknown states

| Condition | Result status | Evidence/display rule |
| --- | --- | --- |
| Gateway/provider not configured or NLSC approval absent | `unavailable` | No observation value; “資料來源尚未啟用”. |
| Context point absent, unrelated, superseded or conflicting | `unknown` | Do not call gateway; ask user to resolve/select a location. |
| Requested year not in accepted allowlist | request `422` | No provider call and no evidence item. |
| Point outside the accepted coverage geometry | `unknown` | “此位置的服務涵蓋尚未確認”; not “no land use”. |
| Timeout, network/TLS failure, circuit open or provider 5xx | `unavailable` | Retryable bounded error; retain no fake result. |
| Provider 401/403 | `unavailable` | Non-retryable configuration/approval incident; alert operations. |
| Provider 429/quota | `unavailable` | Respect approved backoff; do not bypass through another egress. |
| Malformed, unexpected, unsafe or oversized XML | `unknown` | Reject whole response, quarantine safe metadata, alert; never partially guess. |
| Successful accepted empty-result shape | `no_data` | Scoped only to the exact point/year query; never render “no restriction”. Disabled until an official/approved fixture exists. |
| Unknown/missing classification version with otherwise valid item | `partial` | Preserve source fields; mark observation/evidence limited. |
| Previously usable evidence outside a future approved policy | `stale` | Retain historical value and visibly require refresh/local confirmation. |
| Same-scope incompatible observations | `conflicting` | Show all and require review; no automated conclusion. |

All errors use bounded internal codes. Raw response fragments, upstream URLs with path data, credentials, stack traces and property/customer identifiers are excluded from browser payloads and ordinary logs.

## 10. UI and export contract

Required Traditional Chinese labels:

| Surface | Exact label/copy |
| --- | --- |
| Card title | `國土利用現況調查（參考）` |
| Source badge | `官方來源・僅供參考` |
| Classification field | `調查分類` |
| Dataset-year field | `圖資年度（民國）` |
| Survey-period field | `調查年月` |
| Point field | `查詢點` |
| Spatial-scope helper | `僅代表指定坐標，不代表整筆宗地` |
| Freshness unknown | `資料時效無法由服務回應確認` |
| No accepted data | `此查詢點／年度沒有可確認的調查結果` |
| Unavailable | `國土利用現況調查服務目前無法使用` |
| Conflict | `同一查詢範圍有相互衝突的調查結果，請人工查核` |
| Local confirmation | `實際管制請向所在地主管機關確認` |

Mandatory visible warning on cards, detail views, print/PDF and exports:

> 此為指定坐標的國土利用現況調查結果，不是都市計畫或非都市土地使用分區、土地使用管制、開發或建築許可，也不代表整筆宗地可建。實際管制與可建性請向所在地主管機關確認。

Forbidden labels and derived text include `土地使用分區`, `法定用途`, `合法使用`, `符合分區`, `可建築`, `可開發`, `開發強度`, `已核准`, `無限制`, and `無風險` unless a separate, accepted local-authority fact explicitly supports that exact statement. Generic headings such as `Planning/Zoning` may group evidence but must not rename the LUI_002 field itself.

## 11. Security, privacy and operations constraints

- Browser -> Render and Render -> gateway are authenticated; tenancy and property/context authorization are checked before egress.
- NLSC credentials/binding configuration exist only at the Taiwan gateway. Render receives only a gateway client credential. Neither enters source control, frontend bundles, responses or logs.
- The gateway permits one service-specific path, one upstream host/prefix and one method. SSRF-capable URL/path/header input is absent.
- Request/response sizes, XML nesting/entity expansion, item count, string length, timeouts, concurrency, retry count and total retry budget are bounded and tested. DTD/external entities and network resolution in the XML parser are disabled.
- Redirects are disabled on both hops. TLS verification is mandatory.
- Evidence values store the minimum fields necessary for display/audit. Raw XML retention and redistribution default to prohibited until owner/legal approval.
- Cache policy is `private, no-store` at the product response boundary until approved otherwise. Any gateway cache requires an approved terms/TTL/key contract including point, year, CRS, contract version and authorization scope.
- Health reporting is value-free: configured/unconfigured/reachable status only, with no host, token, coordinate or raw provider body.
- Observability distinguishes configuration, authentication, quota, timeout, malformed payload, no-data and coverage-unknown rates. Alerts never reclassify an error as an empty success.

## 12. Acceptance tests

All normal CI and contract tests are offline. A credentialed NLSC acceptance suite is separate, manually authorized and excluded from this task.

### 12.1 Official request contract

- `all` maps to numeric ROC year `0`; `specified` maps only an allowlisted ROC year.
- The adapter emits exactly one call to the fixed gateway path; the gateway emits exactly one `GET` to the fixed `LandUsePointYears` path.
- V1 always emits the accepted EPSG:4326 path form and correct X=longitude/Y=latitude order.
- Address, parcel number, browser coordinates, arbitrary CRS, host, operation and path inputs are rejected before egress.
- Invalid/non-finite coordinates, invalid year mode pairs and points outside the accepted coverage geometry do not call the provider.

### 12.2 XML and normalization

- Approved fixtures for one item, many years, every classification era, missing optional level 3, Unicode labels, leading-zero codes and maximum accepted body/item count parse exactly.
- `YEAR`, `LYEAR` and `LMONTH` remain distinct; retrieval time does not replace any of them.
- Unknown codes and unknown scheme years are retained and marked limited.
- Multiple years return a deterministic timeline without being labelled conflict.
- Same point/year/month with incompatible classifications returns all items and `conflicting`.
- Empty, error and no-match fixtures map according to the NLSC-approved contract; before that fixture exists, empty XML maps to `unknown`, never `no_data`.
- Truncated, malformed, namespace-surprise, DTD/entity, deeply nested, oversized, over-count and over-length XML fail closed with no partial evidence.

### 12.3 Evidence and lineage

- Each observation creates one immutable `planning.land_use_observation` item linked to the exact geo-reference node in the same workspace.
- Every item has source/service/operation, contract/adapter/gateway versions, retrieval time, point coverage, classification scheme, request/response fingerprints and coordinate-evidence lineage.
- Every production LUI_002 planning item is `limited`, `point_only`, `not_established` for parcel scope, and `reference_only_requires_local_confirmation`.
- Missing/unknown/unavailable never produces a value, zero, `none`, safe, compliant, unzoned or unrestricted.
- Re-query with changed content supersedes rather than overwrites; identical canonical content deduplicates safely.
- Cross-workspace property, graph-node, parcel or evidence identifiers fail at service and database boundaries.
- Test/demo fixtures cannot create production-source available evidence.

### 12.4 Transport and failure

- Missing/malformed gateway configuration makes zero network calls.
- Redirect, TLS/DNS failure, timeout, 401/403, 429 and 5xx map to distinct bounded internal errors and safe public statuses.
- Fixed-host/no-redirect/SSRF tests prove user input cannot influence the destination.
- Retry tests prove only approved transient failures retry with a capped budget; mutations/evidence writes remain idempotent.
- Logs, health output and response DTOs contain no NLSC/gateway credential, raw XML or unapproved sensitive context.

### 12.5 UI and authority boundary

- Card, detail, print and export surfaces show the exact point-scope and mandatory warning.
- Snapshot/copy tests reject the forbidden zoning/buildability/legal-entitlement terms for LUI_002 output.
- `unavailable`, `unknown`, `no_data`, `stale`, `partial` and `conflicting` have distinct labels and cannot share a success badge.
- Local zoning evidence is rendered separately; it cannot be overwritten or synthesized from LUI_002.
- Multiple points for one parcel remain separately labelled; no parcel roll-up or “dominant use” appears.

## 13. Production acceptance gate

Status on 2026-09-20: **closed / NO-GO**. Every item below requires retained evidence and named ownership:

- [ ] NLSC approves PropTech for `LUI_002` and issues the exact production endpoint/auth/binding instructions.
- [ ] Registered URL/IP and fixed egress are recorded; Taiwan gateway hosting and egress residency are independently evidenced rather than inferred from hostname.
- [ ] Current NLSC terms are reviewed for commercial use, normalized-field display, storage, cache, raw-payload retention, attribution and redistribution.
- [ ] NLSC-approved or credentialed snapshots establish success, multiple items, specified year, `0`/all years, empty/no-data, invalid year/point, authentication, quota and provider-error shapes, including the actual XML root/namespaces.
- [ ] Provider and product owners approve body/item/string limits, timeout, retry, rate/quota, cache and incident-support policies.
- [ ] A regional/year coverage matrix covers Taiwan proper, Penghu, Kinmen, Matsu, boundary/coastal points, uncovered points and representative ROC 82, 95, 104, 105, 108, 109 and current-period observations.
- [ ] Era-specific classification dictionaries and unknown-code behavior are versioned and acceptance-tested without cross-era relabelling.
- [ ] `nlsc-land-use-survey` is registered as its own source; evidence/license/freshness policies and retention/deletion controls are approved.
- [ ] Taiwan gateway, Render adapter, product route, persistence and UI pass all section 12 offline tests behind a default-off feature flag.
- [ ] A separately authorized, non-sensitive credentialed smoke run proves provenance, coverage and failure behavior. It is not run in ordinary CI and was not run for this audit.
- [ ] Product, legal/data-governance and operations owners sign the authority-boundary copy and confirm the local-authority escalation path.

Opening the gate permits only the point-observation evidence slice described here. It does not authorize parcel-wide inference, a generic NLSC proxy, LUI_001, local zoning ingestion, legal conclusions, bulk/preload/export, or any development/buildability decision.

## 14. Explicit implementation boundary

In scope after the gate prerequisites are met:

- one authenticated property-scoped read/query operation;
- one fixed LUI_002 gateway route;
- EPSG:4326 evidence-backed points only;
- all-years or one acceptance-tested ROC year;
- strict offline-fixture XML parsing;
- immutable point observations, provenance and reference-only UI.

Out of scope:

- parcel/address/lot-number input to LUI_002;
- geocoding, cadastral resolution or parcel centroid generation;
- polygon/parcel intersection, percentage or dominant-use calculation;
- LUI_001 comparison, WFS/WMS/WMTS or generic NLSC access;
- statutory urban/non-urban zoning, use-district or land-control ingestion;
- permits, buildability, development potential or legal advice;
- bulk requests, nationwide preload, public raw data export or unapproved caching;
- automatic planning conclusions, scores, recommendations or AI-generated entitlement claims.
