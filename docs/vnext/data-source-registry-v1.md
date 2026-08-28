# VNext Data Source Registry v1

Status: Stage 0 feasibility registry; registration is not production approval

## 1. Status vocabulary

- `production_accepted`: real source, authorization/license, coverage, freshness and failure
  acceptance have all been recorded for the exact use. No source in this first VNext registry
  receives this status merely because current code exists.
- `prototype_partial`: an adapter/pipeline exists, but production reachability, coverage,
  freshness, license or downstream acceptance remains incomplete.
- `metadata_only`: source metadata or a disabled placeholder exists, not usable data.
- `not_integrated`: no source contract/adapter is approved.
- `partner_required`: commercial agreement and technical acceptance are both absent.
- `user_input_partial`: a bounded user-input path exists, but durable VNext evidence/storage
  does not.

Unknown legal, commercial, redistribution, rate-limit or coverage answers remain
`owner_review_required`. They are not inferred as allowed.

## 2. Registry

| source_name | domain | official / partner / user | access_method | license | commercial_use | redistribution | authentication | rate_limit | coverage | update_frequency | sensitive | current_status | owner_action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MOI/DLA PLVR open-data batch | Market, valuation, property observations | official | HTTPS public ZIP discovered from official catalog/allowlisted route; offline pipeline | Repository records `official_open_data_terms`; exact terms/version and attribution evidence must be retained per release | owner_review_required before VNext reuse beyond current approved aggregate/valuation purpose | Public product should expose aggregates/allowlisted comparable traces only; raw redistribution owner_review_required | none for current public resource | publication/host limits not codified; bounded client required | Catalog says Taiwan; actual loaded release/region coverage must be proven and never inferred from catalog scope | periodic, commonly 1/11/21 when published | raw addresses/transaction details are sensitive for product exposure | `prototype_partial` | Legal/attribution review; record release license; production pipeline/coverage/freshness acceptance; confirm VNext fact reuse semantics |
| TGOS address service | Identity, address, spatial | official | backend HTTPS address API | TGOS service/application terms; repository has no approved license record | owner_review_required | raw provider payload/coordinates not redistributable without reviewed terms; expose minimum normalized result | app ID + API key, backend only | owner must confirm account quota and retry policy | Taiwan address service; exact input/precision coverage requires acceptance cases | live query; source update cadence unknown | exact addresses/coordinates | `prototype_partial` when credentials exist; otherwise not configured | Complete TGOS application/configuration, terms review, real-provider acceptance, quota/coverage/failure evidence |
| NLSC map/cadastral services | Parcel, map, terrain, spatial | official | public OGC/download metadata; future verified parcel vector endpoint | NLSC attribution/use rules by dataset | owner_review_required per layer | owner_review_required; raw/legal boundary distribution not assumed | some base services none; parcel adapter requires verified endpoint and authorization decision | unknown by layer | official published layer scope; current parcel/terrain coverage unknown | dataset-specific | parcel/legal boundary, exact coordinates | `metadata_only`; current parcel provider is disabled and terrain provider unavailable | Select exact dataset/layer, verify endpoint and authorization, license/attribution, CRS/version/coverage, snapshot/update and acceptance matrix |
| TDX MRT/transit | Commute, transport | official | backend API -> protected in-memory snapshot | TDX terms/version must be recorded | owner_review_required | only allowlisted derived station/commute results; raw redistribution owner_review_required | OAuth client credentials, backend only | plan/quota owner_review_required | depends on TDX MRT datasets; repository snapshot is not proof of all-transit/nationwide coverage | operator-triggered snapshot today; source cadence dataset-specific | station/location data; user address remains private | `prototype_partial` | Confirm TDX application/terms/quota, durable snapshot strategy, coverage and scheduled refresh acceptance |
| ARDSWC open data/MVT | Terrain and slope hazard reference | official | current bounded external MVT adapter; manual download/snapshot is alternative | Official open-data attribution/use terms require versioned record | owner_review_required | derived reference only until terms reviewed | none evidenced for current route | unknown; bounded tile client required | repository cannot prove nationwide layer coverage | published dataset/year; exact refresh unknown | property location and hazard intersection | `prototype_partial` | Verify live endpoint/terms, layer definitions, data version, nationwide coverage, freshness and multi-region real-provider acceptance |
| Local planning data | Planning, zoning | official/local government | jurisdiction-specific API/download/manual source; no unified adapter | owner_review_required per jurisdiction/dataset | owner_review_required | owner_review_required | varies | varies | fragmented by municipality and plan/effective date | varies | planning constraints can be consequential | `not_integrated` | Build jurisdiction registry; approve source/license/effective-date/version/coverage and appeal/manual verification path |
| Urban renewal data | Redevelopment, planning | official/local government | jurisdiction-specific portal/data; no adapter | owner_review_required per dataset | owner_review_required | owner_review_required | varies | varies | fragmented; project/status semantics vary over time | varies | project/site and potentially party data | `not_integrated` | Select pilot jurisdiction, define temporal status model, legal/attribution and coverage acceptance |
| Building data | Building intelligence | official and/or partner, undecided | source/partner API or licensed batch, not selected | no approved license | owner_review_required | not allowed until agreement says so | undecided | undecided | unknown | unknown | building/unit and possibly occupancy/permit information | `not_integrated` | Decide authoritative sources and identifiers, access rights, sensitivity, update and correction workflow |
| Title/land registry partner | Title, documents, owner due diligence | partner/official procurement channel | paid procurement/API/manual partner workflow; none selected | contract and statutory use restrictions required | not approved | prohibited by default; no public redistribution | high-assurance server authentication required | contractual | request-specific; not assumed nationwide | request/event based | highly sensitive legal rights, owner/contact and paid documents | `partner_required` | Select/title partner and legal basis; contract, consent, cost, identity assurance, retention, audit, signed-delivery and incident review |
| Active listing partner | Listings, market | partner | licensed API/feed only; no scraping in this contract | partner contract required | not approved | prohibited unless contract expressly allows | partner credentials, backend only | contractual | partner inventory only; never market completeness | partner-specific | seller/contact/listing content | `partner_required` | Select partner, prohibit unlicensed scraping, agree relist/dedup/takedown/retention and real-feed acceptance |
| User upload | Documents, parcel geometry, evidence | user | explicit upload; current parcel endpoint accepts bounded GeoJSON/KML/Shapefile ZIP | user representation/consent plus product terms; third-party content rights remain user responsibility | product policy review required | private by default; sharing only by explicit scoped action | authenticated workspace member in VNext | product size/rate quotas required | only uploaded content; no broader coverage claim | point-in-time | potentially title, contact, address and private documents | `user_input_partial` | Approve private Storage, malware/content validation, consent/retention/deletion, evidence status `user_provided|unverified`, tenant/audit tests |

## 3. Additional source observations

- Google geocoding/places appears as an optional current backend integration, but it is not
  approved as a VNext canonical identity source by this registry. If proposed, add a separate
  row with exact product, terms, caching/redistribution and identity limitations.
- Current NLSC, WRA and GeologyCloud terrain adapters that return unavailable are evidence of
  honest placeholders, not integrated data sources. WRA/GeologyCloud can be added as explicit
  registry rows when exact datasets and access terms are selected.
- Current PLVR schemas/pipelines remain governed by their active contracts. This registry does
  not change PLVR, valuation or market semantics.
- Listing URLs may be accepted as an input reference only for an allowlisted/licensed partner;
  they do not authorize crawling, scraping or cross-brand aggregation.

## 4. Source readiness gate

A source may move to `production_accepted` only when an owner-approved evidence pack contains:

1. exact authority/provider, dataset/product and version;
2. access method and authentication ownership;
3. license/terms version, attribution, commercial use, caching and redistribution decision;
4. rate limits, timeouts, retry/circuit-breaker policy and cost ownership;
5. geographic, temporal, subject and field coverage with known gaps;
6. update cadence, freshness/staleness thresholds and correction behavior;
7. sensitive fields, storage location, retention/deletion and public allowlist;
8. provider contract tests and separately recorded real-provider acceptance;
9. failure/no-match/partial behavior proving no fake success or false safety;
10. named business owner and operational runbook.

Until then the feature flag stays off and API responses remain unavailable/limited as
appropriate. Configuration presence by itself is not readiness.

## 5. Immediate blocking owner actions

- Supply/reconcile the missing iTaiwan deep-workflow audit.
- Complete TGOS configuration/application and terms review if TGOS is the Stage 1 resolver.
- Decide the exact NLSC parcel dataset/endpoint, authorization and license for Stage 2.
- Record PLVR license/attribution and scope for any new VNext evidence reuse.
- Confirm TDX account/quota and durable refresh approach.
- Approve ARDSWC layer/version/coverage acceptance.
- Choose planning/building pilot sources.
- Select listing and title partners before their stages.
- Approve private user-upload Storage, consent, security and retention policy.
