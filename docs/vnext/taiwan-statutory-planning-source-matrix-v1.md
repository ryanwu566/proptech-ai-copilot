# Taiwan Statutory Planning Source Matrix v1

- Audit date: 2026-09-20
- Branch: `audit/statutory-planning-source-matrix`
- Baseline: `origin/main` at `14c21f0`
- Scope: source and documentation audit only; no live credentialled call was made

## Decision

**CONDITIONAL GO for a one-jurisdiction, reference-only planning observation slice. NO-GO for a nationwide statutory zoning, permitted-use, FAR, BCR, buildability, development-restriction, or development-permission conclusion.**

There is no single nationwide, parcel-current, legally conclusive Taiwan zoning API. The Ministry of the Interior (MOI) / National Land Management Agency (NLMA) maintains the official national aggregation and offers nationwide land-use zoning WMTS service, but that service is raster display and the public query system says its results are for planning reference and may not be used as proof. Urban-plan legal effect remains tied to the competent planning authority's promulgated plan, plan map, plan-specific control text, and effective announcement. Current non-urban control depends on both the parcel's current non-urban zoning and use-land designation plus the effective control rules and any approved development plan.

The first implementation should therefore create `planning.zoning_observation`, not a statutory conclusion. For Taipei City, the observation can be joined by parcel key to an official open dataset and corroborated spatially, but it must remain `REFERENCE_ONLY` until an applicable plan announcement or current official certificate is attached and reviewed.

### Non-negotiable boundary

`LUI_002` / `LandUsePointYears` and the National Land Surveying and Mapping Center (NLSC) national land-use survey are observations of actual land use. They belong only in `planning.land_use_observation`. They must never populate or substantiate:

- `planning.zoning_observation`;
- a statutory zoning, entitlement, development-permission, or buildability statement;
- `planning.permitted_use`;
- `planning.far` or `planning.bcr`.

Combining `LUI_002`, a commercial map, transaction data, or multiple other non-authoritative sources does not produce statutory zoning.

## Classification rules

| Classification | Meaning in this audit |
| --- | --- |
| `AUTHORITATIVE` | A competent public authority's promulgated law, plan, certificate, decision, or current official record for the fact asserted. Authority is limited to the record's jurisdiction, effective interval, subject, and legal purpose. |
| `REFERENCE_ONLY` | Useful official or non-official context that the source itself does not permit to stand as legal proof, or whose currency, scale, or legal linkage is insufficient. |
| `DERIVED` | A deterministic result from authoritative or reference inputs, such as point-in-polygon, parcel-to-plan joining, or rule application. A derived result never inherits greater authority than its weakest material input. |
| `NOT_AVAILABLE` | No reviewed source provides the capability at the required legal, temporal, geographic, and machine-readable level. |

`Official` and `authoritative` are not synonyms. An official open-data layer can still be `REFERENCE_ONLY` when the publishing authority says that the promulgated plan or field demarcation controls.

## 1. National sources

### 1.1 Access, keys, fields, CRS, and version

| ID | Source agency and official service | Jurisdiction / scale | Access | Input keys | Output fields or artifacts | CRS | Effective date, version, cadence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `N1` | MOI NLMA Urban and Rural Development Branch, [National Land Use Zoning Data Query System and National Land Planning Portal](https://ngis.nlma.gov.tw/) (`全國土地使用分區資料查詢系統` / `國土規劃入口網`) | Taiwan; national aggregation of urban-plan, non-urban, and national-park zoning | Public manual web query; from 2026-01-01, paid-application WMTS for urban zoning, non-urban zoning, and non-urban use-land designation | UI: administration, address, road, parcel number, or map location; WMTS: tile matrix/set, row, column, layer, style, format per unreviewed contract | Query/display map, zoning layers, measurements; WMTS image tiles only | Public pages do not state the contracted tile matrix/CRS; contract confirmation required | Portal uploads local cases on an event basis; no per-feature legal-effective field is proven. Service began paid private-sector applications on 2026-01-01. |
| `N2` | MOI NLMA, [Non-urban Land Use Zoning Map (Year 112 / 2023)](https://data.gov.tw/dataset/169538) (`非都市土地使用分區圖（112年）`) | 18 city/county datasets; national compilation, not complete for every land regime | SHP download by city/county | County/city resource selection; downstream polygon or point intersection | County/city code and name, township code and name, zoning code and zoning name, geometry | Not stated in dataset metadata; inspect and approve each resource's spatial reference before use | Snapshot year 2023; irregular update; metadata updated 2025-12-30 |
| `N3` | MOI NLMA, [Non-urban Use-land Designation Map (Year 112 / 2023)](https://data.gov.tw/dataset/169539) (`非都市土地使用地編定圖（112年）`) | 18 city/county datasets; national compilation | SHP download by city/county | County/city resource selection; downstream polygon or point intersection | County/city and township fields, use-land designation code/name, geometry | Not stated in dataset metadata; resource-level verification required | Snapshot year 2023; irregular update; metadata updated 2025-12-30 |
| `N4` | MOI NLSC, [Map Service Cloud](https://maps.nlsc.gov.tw/pro/sysinfo.jsp) zoning overlays | Taiwan; display aggregation licensed from NLMA plus NLSC basemaps | Public map/manual display; only listed NLSC core layers are openly exposed through WMS/WMTS without application. Zoning-layer OGC reuse is not established by the reviewed page. | Map extent/point/layer; OGC keys only where a layer is actually published | Map images/tiles and UI attributes; urban zoning layer is labelled by snapshot month (115/04 on audit date) | Service-specific capabilities document required | Layer snapshots; cadence not stated; all overlay results are expressly reference only |
| `N5` | MOI NLSC, requested `LUI_002` / `LandUsePointYears` | Taiwan land-use survey coverage; point-linked | Credentialled requested API; not called in this audit | Point coordinate and year selection; exact production CRS/contract still external | Historical or selected-year observed land-use classification and survey metadata | Unproven until the NLSC service contract is received | Survey year / classification version; cadence follows survey program, not planning promulgation |
| `N6` | MOI NLMA, [Urban Planning Act](https://www.nlma.gov.tw/ch/legislation/regsearch/52), relevant implementation regulations, and Urban Detailed Plan Review Principles | Nationwide legal framework; local plans and municipality/province rules supply specifics | Official law HTML/PDF/manual download | Law/article/date; plan type and competent authority | Statutory procedures, use-zone powers, plan content, implementation and control authority; no parcel geometry | N/A | Current promulgated law and amendment history; update on promulgation |
| `N7` | MOI NLMA, [Rules for Non-urban Land Use Control](https://www.nlma.gov.tw/ch/legislation/regsearch/7008) (`非都市土地使用管制規則`) and appendices | Non-urban land, excluding controls governed by another regime such as national parks | Official law HTML/PDF/manual download | Current non-urban zoning, current use-land designation, proposed use/detail, effective date, approved plan if any | Allowed-use items and conditions in Article 6 appendices; BCR/FAR maxima in Article 9; exceptions and approval paths | N/A | Current page records amendment of Article 6 and Appendix 1 on 2026-05-27; use promulgation/amendment history, not retrieval date |
| `N8` | MOI NLMA, county/city national spatial plans and draft national functional zoning (`國土功能分區`), under the [2025-01-20 Article 45 amendment](https://gazette.nat.gov.tw/EG_FileManager/eguploadpub/eg031013/ch09/type10/gov80/num31/Eg.htm) and [official transition explanation](https://www.nlma.gov.tw/uploads/files/efa20a0f0c6ad6a584c4ac339350148c.pdf) | Nationwide future land-use control regime | Manual portal, documents, and planning map | County/city, functional zone/category, location | County/city plans, draft/review functional zones, planning documents | Varies by artifact | Article 45 amendment promulgated 2025-01-20; the transition must complete no later than 2031-04-30. Draft/demonstration layers are not current statutory zoning. |
| `N9` | MOI NLMA, [Environmentally Sensitive Area Single-window Query](https://eland.nlma.gov.tw/) (`環境敏感地區單一窗口查詢平台`) | Taiwan; multi-agency restriction screening | Paid manual application; account, document upload, payment, agency replies; no reviewed public bulk/API contract | County/city, township, section, parcel number or uploaded application range; selected sensitive-area items | Per-item query replies/notice across water, geology, conservation, cultural, coast, military, agriculture and other themes | Submitted cadastral artifact / service-internal spatial processing; no public API CRS | Source-by-source updates, not a single cadence; current portal publishes item update notices |
| `N10` | MOI NLMA, [Urban Renewal Regulations Portal](https://uract.nlma.gov.tw/) (`都市更新法規`) | Nationwide legal framework; project administration is local | Official law/manual portal | Law, article, amendment date, jurisdiction | Urban Renewal Act and subordinate rules, official links; no nationwide parcel-current project feed proven | N/A | Update on promulgation; portal links local authorities |

### 1.2 Linkage, authority, access constraints, gaps, and feasibility

| ID | Parcel-linked | Point-linked | Legal/statutory status | License / access / credential / Taiwan host | Coverage gaps | Production feasibility and classification |
| --- | --- | --- | --- | --- | --- | --- |
| `N1` | UI can locate by parcel, but WMTS is not a parcel record | UI yes; WMTS only by tiles | Official aggregation, but the public system says results are planning reference and not proof; local authority promulgation remains controlling | Public UI; private-sector WMTS is paid and requires application. Terms, price, quota, cache/redistribution, attribution, credentials, CRS, and stable URLs require contract. No reviewed notice requires Taiwan-resident hosting. | Local upload delay; raster tiles have no legal-effective field or feature identifier; national-park regime is distinct | `REFERENCE_ONLY`; feasible as a paid contextual basemap, not as a zoning query or legal source |
| `N2` | No parcel key in published fields | Yes, by a product-created spatial intersection | Official historical compilation, not proof of a current parcel classification | Government Open Data License v1, free, no credential; no Taiwan-host requirement published | 2023 vintage; 18 jurisdictions; excludes urban-plan controls and other regimes; current local changes may be absent | `REFERENCE_ONLY`; feasible for bounded batch context only |
| `N3` | No parcel key in published fields | Yes, by a product-created spatial intersection | Official historical compilation; designation is one required input but snapshot is not current legal proof | Government Open Data License v1, free, no credential; no Taiwan-host requirement published | Same vintage/coverage gaps as `N2`; designation without zoning and rules is incomplete | `REFERENCE_ONLY`; feasible only alongside a current authority record |
| `N4` | No legal parcel link | Display location only | NLSC says overlays are reference only; it is not the promulgating planning authority | Public viewing. Do not assume zoning layers share the open OGC terms of NLSC core layers. Credential/Taiwan-host need is not established for public viewing. | Snapshot and local-authority lag; image/scale/edge ambiguity | `REFERENCE_ONLY`; visual corroboration only |
| `N5` | No | Yes | Land-use survey observation, never zoning or entitlement | Requested service approval, registered endpoint/IP and credentials are external blockers already documented by the LUI audit; repository policy requires a Taiwan gateway for this requested integration | Survey coverage/year/classification gaps; no legal planning semantics | `REFERENCE_ONLY` for `planning.land_use_observation`; **prohibited** for every statutory planning fact |
| `N6` | No | No | `AUTHORITATIVE` for legal framework, not for a parcel's assigned zone by itself | Public law text; no credential or Taiwan-host requirement; preserve promulgated version and official URL/artifact | Municipality rules, plan-specific controls, later amendments and approvals still apply | `AUTHORITATIVE`; production ingestion is feasible only with legal versioning and professional review |
| `N7` | No; must join to current parcel classification | No | `AUTHORITATIVE` for effective rules; parcel answer after joining is `DERIVED` | Public law text; no credential or Taiwan-host requirement | County/city may lower Article 9 limits; approved plans and purpose-agency rules can control; national parks excluded | `AUTHORITATIVE` rules / `DERIVED` property result; conditional production feasibility |
| `N8` | Draft overlays may spatially relate to parcels but are not current parcel rights | Yes, for planning display | Current plans guide planning; unpromulgated functional zoning is not current statutory land-use control | Public documents/manual portals; artifact-specific terms; no credential generally required | Transition incomplete until no later than 2031-04-30; draft status varies by jurisdiction | `REFERENCE_ONLY` for current property decisions; `NOT_AVAILABLE` as current statutory zoning |
| `N9` | Yes, by submitted parcel list/range | Not a public point API | Official multi-agency information disclosure, but the platform expressly does not replace each competent agency's confirmation procedure and is not itself an appealable decision | Paid application; membership/payment and documents. No public API or bulk license proven. No published Taiwan-host requirement found. | Item-specific outages/exclusions; current notice redirects some Hsinchu County cultural items; no single clearance meaning | `REFERENCE_ONLY` as consolidated screening; conditional manual evidence acquisition; no-go as development clearance |
| `N10` | No national project linkage | No | `AUTHORITATIVE` for renewal law; no authority for a parcel's project status without local case evidence | Public; no credential/Taiwan-host requirement for law portal | Local project IDs, boundaries, stage changes, approvals, withdrawals, and dates are outside the national law portal | `AUTHORITATIVE` law / `NOT_AVAILABLE` nationwide project feed |

The Article 45 amendment promulgated on 2025-01-20 supersedes older public transition material that still names 2025. The controlling deadline for this audit is therefore 2031-04-30; no draft functional-zone layer may be treated as effective merely because it is displayed on an official portal.

### National-source conclusion

The national services solve discovery, standardization, historical snapshots, and legal-framework retrieval. They do not close current urban zoning at parcel level. The national WMTS is especially unsuitable as the statutory read model because it returns imagery rather than versioned features and carries no reviewed per-feature plan/effective-date contract.

For non-urban land, the required source chain is:

```text
current parcel identity
  -> current local land record / official zoning and use-land designation
  -> effective Rules for Non-urban Land Use Control and appendices
  -> county/city adjustment + approved development/use plan + other competent-agency restrictions
  -> reviewed result
```

The 2023 national SHP files can seed reference observations but cannot replace the first line.

## 2. Local-government source strategy

Every supported jurisdiction needs an approved source pack. A national layer does not waive this requirement.

The pack must identify:

1. the competent urban-planning and land authorities;
2. current zoning/plan-boundary spatial data and its authority disclaimer;
3. official plan announcements, plan books, plan maps, change cases, announcement number, and legal-effective date;
4. a current parcel zoning certificate or equivalent confirmation path;
5. local/provincial land-use control regulations, permitted-use tables, BCR/FAR rules, and plan-specific overrides;
6. renewal areas, units, projects, decisions, stable case identifiers, and status history;
7. separate national-park, special-district, non-urban, and cross-agency restriction paths;
8. license, attribution, commercial reuse, cache, redistribution, credentials, source-host, and correction contacts;
9. update cadence, replacement/delta behavior, CRS, encoding, geometry precision, field dictionary, and sample acceptance cases;
10. an explicit statement of what is reference only and the professional escalation route.

### Taipei City source pack

#### Access, keys, fields, CRS, and version

| ID | Source agency and official service | Jurisdiction / scale | Access | Input keys | Output fields or artifacts | CRS | Effective date, version, cadence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `T1` | Taipei City Department of Urban Development (UDD), [Taipei City Land Use Zoning](https://data.taipei/dataset/detail?id=a132a433-db7c-4387-8085-83e6a093b17f) (`臺北市土地使用分區`) | Taipei City, parcel-indexed; excludes Yangmingshan National Park path | CSV download and Taipei Open Data API | Section code, district code/name, major section, subsection, mother lot, sub-lot | Row number and parcel-key fields plus zoning description | N/A; tabular parcel join | Six-month cadence; resource updated 2026-07-01. Dataset does not expose the controlling plan announcement/effective date per row. |
| `T2` | Taipei City UDD, [Taipei Urban Plan Land Use Zoning Map](https://data.taipei/dataset/detail?id=3bab0a01-7936-4218-8cb5-f74dfcb43dda) (`臺北市都市計畫使用分區圖`) | Taipei City; separate citywide main-plan and detailed-plan geometry | SHP download | Batch file; downstream polygon/point/parcel geometry | ID, layer, colour, block number, zoning code/short name/name/description, original zoning, prior-change code/short name/zoning, geometry | Dataset metadata does not state CRS. Audit download of the detailed-plan archive did not expose a `.prj`; source-owner confirmation is required before production. | Annual cadence; files posted 2026-04-09 but description says updated through 2025-01, so snapshot date and publication date must stay separate |
| `T3` | Taipei City UDD, [Urban Planning Integrated Query System](https://webgis.udd.gov.taipei/upis_v2) | Taipei City urban-plan area | Public manual web GIS | Parcel/cadastral selection, location, time line, plan case | Zoning display, cadastral context, time line, related cases/change-case codes/conditions, plan context | Web-map internal CRS not a reusable data contract | Event-driven operational system; no public API/license/schema was proven |
| `T4` | Taipei City UDD, [Urban Plan Announcements](https://udd.gov.taipei/announcement/biwfsm8) | Taipei City; case-specific main and detailed plans, including special-area/special-purpose controls when separately promulgated in a case | Public manual HTML/PDF/image downloads | Plan title, district, parcel references, announcement date, case search | Official announcement, main/detailed plan book, plan map, plan-specific special controls where present, announcement date, publication metadata | Artifact-specific; plan-map georeferencing is not guaranteed | Event-driven on promulgation; official announcement date and stated effective date control. No complete structured inventory of special plans was proven. |
| `T5` | Taipei City UDD, [Land Use Zoning Online Query and Certificate System](https://zone.udd.gov.taipei/new_index1.aspx) | Taipei City land, except Yangmingshan National Park | Public manual query; paid online certificate application/download | District, section/subsection, mother/sub-lot; address for map lookup; applicant/payment fields for certificate | Zoning, other applicable statements, application status, electronic zoning certificate | N/A for certificate; map display is not a reusable geometry contract | Query is current-service oriented. Published UDD material says a certificate is valid for four months; exact legal purpose and expiry must be captured from the issued artifact. |
| `T6` | Taipei City Law Registry, [Taipei City Zoning Control Self-Government Ordinance](https://laws.gov.taipei/Law/LawSearch/LawArticleContent/FL003962) and [Conditional Use Standard](https://laws.gov.taipei/Law/LawSearch/LawArticleContent/FL025529) | Taipei City urban-plan area | Official HTML/PDF/ODT/manual download | Zone/type, use group/item, proposed facts, law version/effective date | Use groups/items, allowed and conditional uses, BCR/FAR tables, exceptions, conditions, amendment history | N/A | Both reviewed pages record amendment on 2025-07-09; plan-specific text and later amendments must also be checked |
| `T7` | Taipei City UDD, [Land Use Content and Control Summary](https://data.taipei/dataset/detail?id=d61ca24b-7b2b-4e75-8004-c568902e6300) | Taipei City, aggregated by district and zoning type | CSV download/API | District and zoning label | District, zoning, parcel count, BCR percentage, maximum FAR percentage, area | N/A | Six-month cadence; updated 2026-04-09; aggregate, not parcel/version specific |
| `T8` | Taipei Urban Regeneration Office (URO), [Renewal Review Status](https://uro.gov.taipei/cp.aspx?n=E06DCE2A43AF2B4F) | Taipei City by district and renewal case | Public manual HTML | District, case ID, name/parcel text | District, stable-looking case number, case title, location, implementer, current processing status | N/A; location is textual | Operational page, current on access; cadence not published and status history is not a public API contract |
| `T9` | Taipei URO, [Approved Self-designated Renewal Unit Query](https://gis.uro.taipei/ua_frmEasyQuery.aspx), renewal-area pages, and approved-case pages | Taipei City renewal units/areas/projects | Public manual query; login only for application workflow | Designation method, case-name keyword, district/section/mother/sub-lot, or address | Case ID, district, case name, case status, details; renewal-area/approval artifacts on separate pages | No public reusable CRS/geometry contract proven | Query page updated 2026-09-14 on audit date; parcel data are expressly the application-time data |
| `T10` | Taipei City UDD, [Convenience e-service for Zoning Business and Use Items](https://luzabic.udd.gov.taipei/) and [current operation manual](https://luzabic.udd.gov.taipei/%E7%B3%BB%E7%B5%B1%E6%93%8D%E4%BD%9C%E6%89%8B%E5%86%8A%28%E4%B8%8A%E7%B6%B2%E7%89%88%29.pdf) | Taipei City urban-plan area | Manual authenticated city SSO; no public API contract | Address and business/use item plus logged-in user context | Allowed, not allowed, or conditionally allowed result and conditions | N/A | Service/rule-version field is not publicly documented; the operation manual documents the login requirement |

#### Linkage, authority, access constraints, gaps, and feasibility

| ID | Parcel-linked | Point-linked | Legal/statutory status | License / access / credential / Taiwan host | Coverage gaps | Production feasibility and classification |
| --- | --- | --- | --- | --- | --- | --- |
| `T1` | Yes, strong join key | No | Official data but expressly reference only; implementation use requires field line/urban-plan stake demarcation and land-office survey where applicable | Public/open/free; no credential for download/API; no Taiwan-host requirement published | Changes may occur between six-month releases; no plan ID/effective date; Yangmingshan National Park excluded | High feasibility for `planning.zoning_observation`; `REFERENCE_ONLY` |
| `T2` | No parcel ID; may overlay a separately proven parcel geometry | Yes, by derived spatial intersection | Official data derived from main/detailed plans, but not a promulgated plan artifact or certificate by itself | Public/open/free; no credential; no Taiwan-host requirement published | Missing explicit CRS/version linkage; annual/stale-description mismatch; edge/sliver and main-vs-detail conflicts | Medium feasibility after CRS/encoding/version acceptance; `REFERENCE_ONLY` |
| `T3` | UI/cadastral linkage | Yes in UI | Official query context, but the system's display is not the promulgated artifact | Public manual view; public reuse/API terms unproven; no Taiwan-host requirement published | No stable public feature API, bulk schema, license, or temporal export | Manual evidence discovery only; `REFERENCE_ONLY` |
| `T4` | Often names parcels but no normalized parcel API | Plan map can be manually georeferenced, but a product overlay would be derived | Announcement and attached effective plan book/map are `AUTHORITATIVE` within their scope | Public manual artifacts; laws/official acts are reusable, but document/image reuse and automated retrieval still require terms review; no credential/Taiwan-host requirement | Case-by-case documents; supersession chain and effective date may require professional reading; no complete machine-readable main/detailed/special-plan inventory or applicability map was proven | Required authoritative evidence path; feasible as manual attachment/index before automation; complete structured special-plan coverage is `NOT_AVAILABLE` |
| `T5` | Yes | Address/map query as convenience only | Issued official certificate is `AUTHORITATIVE` evidence of the authority's zoning statement for its stated purpose/date; it is not building permission, boundary survey, FAR, or BCR approval | Query public; certificate requires application, fee, and likely user/payment data; no bulk API. No Taiwan-host requirement published. | Certificate expiry; field demarcation caveat; no automated entitlement | Manual authoritative confirmation; not a production API |
| `T6` | No; join to a proven zoning/plan fact | No | `AUTHORITATIVE` law/rules. A property answer is `DERIVED` and can be displaced by plan-specific controls/conditions/approvals. | Public law registry, no credential/Taiwan-host requirement | Special plans, overlays, site facts, use definitions, discretionary approvals and later amendments | Feasible for a versioned rule reference and reviewer aid; no-go for unreviewed legal conclusions |
| `T7` | No | No | Official aggregate only; cannot establish a parcel's BCR/FAR | Public/open/free/API; no credential/Taiwan-host requirement | Aggregation loses special-plan and parcel exceptions and effective source | `REFERENCE_ONLY`; do not populate parcel `planning.far`/`planning.bcr` |
| `T8` | Case title frequently carries section and parcel numbers | No geometry API | Official administrative case-status publication; authoritative for the published status at retrieval, not for parcel overlap, future approval, zoning, or entitlement | Public manual HTML; no reusable API/schema/license/cadence proven; no Taiwan-host requirement | Status wording can be absent or change; case boundary and history not normalized | Conditional manual/HTML-source evidence; `REFERENCE_ONLY` redevelopment context in product semantics |
| `T9` | Yes, by application-time parcel query | Address search; not a point API | Official context for approved self-designation/renewal administration, but page warns parcel data may be stale and refers actual parcel data to land authority | Public query; authenticated workflow separate; no bulk/API/redistribution or Taiwan-host term proven | Application-time parcel changes; renewal areas and self-designated units are different concepts; no single current polygon feed | Conditional manual context; `REFERENCE_ONLY` |
| `T10` | Address-linked, not a canonical parcel contract | Address location only | Official service result, but rule scope, input facts, plan exceptions and any approval conditions still govern | Login required; no public API, automation terms, redistribution, or Taiwan-host requirement proven | Cannot batch or prove legal version; not all proposed uses can be reduced to a code | Manual corroboration only until an agreement/API and rule-version contract exist; otherwise `NOT_AVAILABLE` for production automation |

## 3. Capability matrix

The classification is for the best supportable **property-level product fact**, not merely for the existence of an official website.

| Capability | Controlling source chain | Product classification | Why | Implementation decision |
| --- | --- | --- | --- | --- |
| 1. Urban planning zoning / land-use district | Local effective main/detailed/special plan announcement and map; current certificate where needed | `AUTHORITATIVE` only when the controlling local artifact/certificate is attached; open/API observation remains `REFERENCE_ONLY` | National aggregation and local open layers can lag and disclaim legal use | `CONDITIONAL GO` for observations and evidence workflow; `NO-GO` for unconfirmed statutory claims |
| 2. Non-urban land-use zoning | Current local zoning + use-land designation record, `N7`, county adjustment, approved plan, other regime checks | `AUTHORITATIVE` source chain; spatial join/snapshot answer is `DERIVED` or `REFERENCE_ONLY` | Zoning alone is insufficient; the 2023 national files are stale snapshots | `CONDITIONAL GO` for reference import/manual verification; `NO-GO` for a current nationwide claim |
| 3. Permitted-use classification | Effective zone/plan + `N6`/`N7` + local ordinance/standard + plan-specific rules + proposed-use facts and approvals | `DERIVED` | No reviewed parcel feed directly supplies a complete legally applicable answer; conditional and discretionary facts matter | `CONDITIONAL GO` only as a cited reviewer aid; `NO-GO` for automatic permission |
| 4. Building coverage ratio (BCR) | Effective plan-specific control first, then applicable local/provincial/non-urban rule, approved plan and exceptions | `DERIVED` | A generic zone table is not necessarily the site's applicable maximum; bonuses/relief do not equal as-of-right BCR | `CONDITIONAL GO` for `base_control` with sources and caveats; `NO-GO` for buildable footprint |
| 5. Floor area ratio (FAR) | Same hierarchy as BCR, plus bonuses/transfers/redevelopment and development approvals kept separate | `DERIVED` | Base FAR, maximum FAR, awarded FAR and buildable floor area are different facts | `CONDITIONAL GO` for sourced base control; `NO-GO` for development yield/entitlement |
| 6. Urban planning boundary | Effective local plan map/announcement | `AUTHORITATIVE` when the promulgated map is the evidence; open-layer intersection is `DERIVED` | Geometry scale, edge precision, supersession and cadastral alignment can change the answer | `CONDITIONAL GO` for overlay/manual review; edge cases block automation |
| 7. Detailed plan / special plan | Local announcement, plan book/map, amendment chain and plan-specific control text | `AUTHORITATIVE` for an identified promulgated artifact; `NOT_AVAILABLE` as a proven complete structured inventory | National indexes help discovery but do not replace the local effective plan; Taipei's archive includes case-specific special controls but no complete applicability service was proven | `CONDITIONAL GO` for manual document evidence; no-go for automated completeness or until plan-to-parcel matching is reviewed |
| 8. Redevelopment / urban-renewal context | Local renewal case/area/unit records, decisions, effective documents, and current status | `REFERENCE_ONLY` in product semantics | Renewal context does not confer zoning, FAR, BCR, approval, schedule or investment outcome | `CONDITIONAL GO` for separately labelled context; never merge into zoning or entitlement |
| 9. Development restriction | Each competent agency's current law, boundary, permit/approval and official confirmation | `NOT_AVAILABLE` as one complete capability | `N9` is a paid consolidated information-disclosure workflow and expressly does not replace competent-agency confirmation | `NO-GO` for `clear/restricted/buildable`; allow only named, source-specific restriction observations |
| 10. Legal effective date / version | Promulgation notice, announcement number, stated effective date, plan/law amendment and supersession chain | `AUTHORITATIVE` | Dataset publication/retrieval date is not legal effective date | `GO` as mandatory evidence metadata when present; record `unknown` and block statutory display when absent |
| Land-use observation (`LUI_002`) | NLSC survey/classification version | `REFERENCE_ONLY` | Actual use is not legal zoning | `GO` only in `planning.land_use_observation`; prohibited elsewhere |
| Point-to-zoning lookup | Proven point CRS + accepted official geometry + boundary tolerance + applicable version | `DERIVED` | Point-in-polygon is a computation, and an edge/road/multi-zone parcel can make one point misleading | `CONDITIONAL GO` as a candidate observation, never parcel-wide legal proof |
| Parcel-to-zoning lookup | Current canonical parcel key + current local record/certificate | `AUTHORITATIVE` only for the current authority record; open bulk join is `REFERENCE_ONLY` | Parcel splits/merges and multi-zone parcels require time-aware identity and possibly multiple observations | `CONDITIONAL GO` in Taipei; preserve one-to-many and conflict states |

## 4. Authority hierarchy

This is an application order, not a rule that a broad law always overrides a more specific plan. A local plan-specific control can govern because the national law authorizes that specificity.

1. Effective national act and subordinate regulation for the land regime.
2. Effective municipality/province/county self-government ordinance or implementation rule.
3. Competent authority's promulgated main plan, detailed plan, special plan, plan map, plan book, plan-specific controls, announcement number, effective date, and amendment/supersession chain.
4. Approved development/use plan, permit, administrative decision, or official certificate for the subject and purpose.
5. Current official local registry/operational record, with its disclaimer and effective scope.
6. Official local open data and national compilations/tiles.
7. Deterministic joins and spatial overlays, always marked `DERIVED`.
8. Surveyed actual land use (`LUI_002`), transaction descriptions, user claims, and commercial portals as context only.

On conflict, preserve both items, prefer neither silently, and require an authorized reviewer to cite the applicable later/more-specific legal artifact. Commercial portals may help a user find a public source but are never authority.

## 5. Coverage model

```text
PropertyEntity
  -> confirmed parcel reference(s) and/or geo reference
  -> source-specific statutory planning observation(s)
  -> jurisdiction + land regime carried by each observation
  -> applicable effective plan/law/version/date candidate(s)
  -> evidence + limitations + conflicts
  -> professional review state
  -> Professional Workspace
```

Operational routing resolves jurisdiction and land regime before querying a source, but the persisted evidence chain above keeps jurisdiction and effective-version lineage on every observation rather than treating them as global assumptions.

### Required separation

| Fact type | Allowed content | Must not contain |
| --- | --- | --- |
| `planning.land_use_observation` | NLSC surveyed actual-use code/label, survey year, classification version, point/coverage | Zoning, permission, FAR, BCR, compliance |
| `planning.zoning_observation` | Source zoning code/label, main/detail flag, source parcel or geometry match, source snapshot, local-confirmation state | Permitted-use or buildability conclusion |
| `planning.permitted_use` | Proposed-use taxonomy, cited rule/plan provisions, `allowed\|conditional\|prohibited\|unknown`, derivation inputs and review state | Development permission, business approval, or uncited yes/no |
| `planning.far` | `base_control`, unit, source provisions, effective interval, exceptions not evaluated, derivation/review status | Achievable floor area, bonus/transfer award, residual development rights |
| `planning.bcr` | `base_control`, unit, source provisions, effective interval, exceptions not evaluated, derivation/review status | Buildable footprint or site-layout conclusion |
| `planning.redevelopment_context` | Renewal area/unit/case IDs, type, published stage/status, observed/retrieved date, source artifact | Zoning, entitlement, guaranteed bonus, approval, completion forecast |

### Geographic and temporal coverage states

- `in_coverage`: the source contract explicitly covers the jurisdiction/land regime and query subject.
- `out_of_coverage`: proven exclusion, such as Yangmingshan National Park for Taipei's city zoning certificate path.
- `no_record`: only when a successful, current, adequately scoped query contract proves that zero records has that meaning.
- `ambiguous_multiple`: multiple zones, plans, parcels, geometries, or cases plausibly apply.
- `boundary_uncertain`: point/parcel touches or approaches a mapped boundary, road, sliver, or precision tolerance.
- `stale`: outside the accepted source freshness policy.
- `source_unavailable`: transport/source failure; never convert to no restriction or no zoning.
- `manual_verification_required`: evidence exists but a controlling plan, certificate, agency confirmation, or professional interpretation is still needed.

Urban plan, non-urban land, national park, and future national functional zoning are separate land regimes. Coverage resolution must occur before choosing a source adapter.

## 6. Evidence semantics

Every planning evidence item must retain:

- `source_id`, agency, official service/dataset name, source record/case ID, and canonical URL;
- `jurisdiction_code` and competent authority;
- `subject_type` and canonical parcel/point/plan/case reference;
- `retrieved_at`, `dataset_snapshot_at`, `source_published_at`, `legal_effective_from`, `legal_effective_to`, and `superseded_at` as distinct fields;
- announcement number, plan title/type, law/rule version, amendment history reference, and artifact checksum where available;
- source CRS, original geometry precision/scale, transformation version, intersection method and boundary tolerance;
- `AUTHORITATIVE|REFERENCE_ONLY|DERIVED|NOT_AVAILABLE`, plus existing evidence lifecycle status;
- geographic, temporal, field and subject coverage with explicit gaps;
- license/terms version, attribution, commercial reuse, cache/redistribution decision, credential mode, and reviewed Taiwan-host requirement;
- raw artifact reference and immutable lineage, including every parent evidence ID for a derived result;
- limitations and `professional_review_status`.

### Time rules

`retrieved_at` is never substituted for legal effect. File upload date and metadata-update date are not plan effective dates. When an announcement does not clearly state the legal-effective date, store it as `unknown` and do not render the observation as current statutory zoning.

### Derivation rules

1. A point intersection produces a point-scoped zoning candidate, not a parcel fact.
2. A parcel polygon intersection can produce multiple zone candidates; do not select the largest polygon silently.
3. A parcel CSV row and a SHP intersection may corroborate each other but remain reference only when both sources carry that limitation.
4. Applying a law table produces a derived base control or rule candidate. It does not produce development permission.
5. A missing renewal/restriction record means `unknown` unless the source's negative-query semantics and coverage are proven.
6. No count or consensus of non-authoritative observations may be promoted to statutory evidence.

## 7. Proposed first jurisdiction

### Recommendation: Taipei City (`63000`)

Taipei is the best first jurisdiction after considering authority chain, identifiers, licensing, coverage, and implementation effort together.

| Candidate | Authority/effective-version evidence | Stable subject keys | License/access | Coverage and delivery | Decision |
| --- | --- | --- | --- | --- | --- |
| **Taipei City** | Official plan announcements, law registry, online zoning certificate path, main/detailed plan GIS, and renewal case IDs | Parcel-indexed zoning CSV with section code, district, major section/subsection, mother/sub-lot; renewal case number | City open data is public/free; official documents public; certificate/manual authenticated paths are clear | Six-month parcel data, annual geometry, direct official hosting; Taipei urban-plan/non-national-park subset only. Yangmingshan National Park remains `out_of_coverage` pending a separate regime adapter. | **First**: strongest end-to-end evidence chain and parcel join, despite mandatory reference-only treatment |
| [Taichung City current Year 114 GIS zoning catalogue](https://data.gov.tw/dataset/126736) | The official dataset describes useful fields including zoning, plan/date, BCR, FAR, maximum FAR, announcement number and plan name | Polygon record IDs/plan metadata; no reviewed parcel-indexed bulk table | Government Open Data License v1 | Reviewed 2026-09-20. The official [resource catalogue CSV](https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=ca87a1fc-53c6-493f-8d9f-6ef11a11b71c) declares WGS84/SHP, irregular delivery, and delegates the current file to Google Drive; weaker production endpoint stability | Second research candidate after source owner supplies an official stable download/API and update contract |
| [New Taipei City urban-plan land-use zoning and boundary dataset](https://data.ntpc.gov.tw/datasets/fe26e0a5-54c2-4876-bbc7-150243c048f5) | Official citywide zoning/range data points back to promulgated plan documents | No reviewed parcel-indexed zoning feed | Government Open Data License v1 | Reviewed 2026-09-20. Dataset explicitly says reference only; indirect download catalogue and irregular cadence | Viable later, but more source resolution work than Taipei |
| National NLMA | Official national aggregation; local plans still control | UI parcel search, but paid WMTS has tile IDs rather than parcel/plan feature IDs | Paid application/contract from 2026 | Nationwide raster display, no per-feature effective version, and reference-only system disclaimer | Not an implementation jurisdiction and not a statutory query source |

This selection is not based on convenience alone. Taichung's field model is richer for BCR/FAR and plan lineage, but the reviewed current delivery chain is less stable. Taipei wins because a property can be joined by stable parcel components to an official dataset, then escalated through official plan announcements and a certificate workflow under clear open-data access, with renewal case IDs available for a later separate context slice.

## 8. Smallest implementation slice

**Slice: Taipei parcel zoning observation with authoritative-confirmation workspace.**

1. Accept only a previously confirmed Taipei parcel reference: jurisdiction `63000`, district code, section/subsection, mother lot and sub-lot. Point-only input may create a candidate but cannot complete the parcel result.
2. Import one identified `T1` release. Preserve the raw artifact, checksum, resource URL, metadata timestamp, six-month cadence, open-data terms and the source's reference-only disclaimer.
3. Create one `planning.zoning_observation` per matched row. Store source zoning description verbatim, parcel key, retrieved/snapshot dates, `REFERENCE_ONLY`, and `manual_verification_required`.
4. Optionally intersect accepted `T2` main/detailed geometry as separate `DERIVED` corroboration only after CRS/encoding/geometry acceptance. Keep main and detailed observations separate.
5. Let a professional attach the controlling `T4` announcement/plan artifacts or an issued `T5` certificate. Capture plan title/type, announcement number, legal-effective date, supersession, source URL, artifact checksum and review note.
6. Show the evidence chain and conflicts in the Professional Workspace. Never display `permitted`, `buildable`, FAR, BCR, or `no restrictions` in this slice.
7. Fail closed for no match, multi-match, missing version, stale release, unsupported Yangmingshan land, parcel changes, source outage, and boundary uncertainty.

Acceptance requires real public-release fixtures covering: exact one-row match, multi-zone/multi-row parcel, no record, stale release, parcel split/merge mismatch, main/detail disagreement, unsupported national-park land, missing legal-effective date, and superseded plan evidence.

Explicitly excluded: non-urban land, national parks, permitted-use computation, FAR/BCR, redevelopment automation, development restrictions, yield, compliance, entitlement, permit application, and legal advice.

## 9. External blockers

1. Taipei UDD confirmation of `T1` stable resource/API behavior, field dictionary, parcel-key normalization, delta/replacement behavior, correction channel, commercial reuse/attribution and acceptable caching.
2. Taipei UDD confirmation of `T2` CRS, encoding, geometry validity/precision, scale, main-vs-detail relationship, snapshot meaning, and why the posted file date and stated 2025-01 content date differ. The reviewed detailed-plan archive lacked a `.prj`.
3. A reliable mapping from `T1`/`T2` records to controlling plan case, announcement number, legal-effective date and supersession chain. Neither open dataset supplies this per record.
4. Written acceptance criteria for when a `T5` zoning certificate is required, what it legally certifies, its four-month validity, and how certificate artifacts may be stored/displayed.
5. A production-access agreement/API or approved manual-only posture for the authenticated `T10` permitted-use service; public automation rights and rule-version semantics are unproven.
6. A local planning professional's reviewed rule hierarchy and test corpus for plan-specific controls, conditional uses, BCR/FAR exceptions, roads/building lines, overlays, bonuses/transfers and development approvals.
7. Current official parcel identity/geometry. Repository Stage 2 does not yet have production-accepted official parcel resolution; point matching alone is insufficient.
8. URO-approved API/download, license, cadence, stable case/status vocabulary, boundary geometry and history for renewal automation. Current sources are manual and parcel data can be application-time only.
9. For national WMTS: executed terms, price, quota, credentials, service URL, CRS/tile matrix, cache/attribution/redistribution rights, uptime/support and proof that commercial product use is accepted.
10. For non-urban implementation: a current local parcel zoning/use-land source, county adjustment rules, plan/approval linkage and transition plan for national functional zoning by 2031-04-30.
11. For development restrictions: per-agency sources and confirmation workflows. The paid single-window result is information disclosure, not a substitute for competent-agency decisions.
12. Taiwan-host review. No reviewed public/open source above independently states a Taiwan-resident hosting requirement. Do not infer one; separately apply repository deployment policy and any future credentialled service contract.

## 10. GO / NO-GO by capability

| Capability | Decision | Production boundary |
| --- | --- | --- |
| National statutory zoning API | `NO-GO` | No single parcel-current, feature/version-rich, legally conclusive nationwide API was found |
| Taipei zoning observation | `CONDITIONAL GO` | `T1` reference-only parcel observation with release provenance and mandatory local confirmation |
| Urban statutory zoning claim | `CONDITIONAL GO` | Only after controlling local plan/certificate evidence, effective date and professional review |
| Non-urban zoning/designation | `CONDITIONAL GO` | Reference snapshot/manual current record; no nationwide-current claim |
| Permitted use | `CONDITIONAL GO` | Cited reviewer aid only; no automatic permission or development approval |
| FAR | `CONDITIONAL GO` | Versioned base-control observation only; no yield/bonus/achievable-area conclusion |
| BCR | `CONDITIONAL GO` | Versioned base-control observation only; no buildable-footprint conclusion |
| Urban plan boundary | `CONDITIONAL GO` | Accepted local plan geometry and boundary uncertainty; promulgated map controls |
| Detailed/special plan | `CONDITIONAL GO` | Manual authoritative artifact capture and parcel applicability review |
| Redevelopment | `CONDITIONAL GO` | Separate official case/area context; no zoning, rights, bonus or outcome inference |
| Development restriction / clearance | `NO-GO` | Only named source-specific observations; no consolidated `clear` or `buildable` fact |
| Legal effective date/version | `GO` | Mandatory when source supplies it; missing means unknown and blocks statutory display |
| Parcel linkage | `CONDITIONAL GO` | Taipei `T1` join after canonical parcel confirmation; one-to-many/conflict safe |
| Point linkage | `CONDITIONAL GO` | Derived candidate only after CRS acceptance; never parcel-wide statutory proof |
| `LUI_002` land-use observation | `GO` in its own domain only | `planning.land_use_observation`; prohibited as zoning/permission/FAR/BCR evidence |

## Final audit result

| Item | Result |
| --- | --- |
| National statutory source | **None as a single parcel-current legal source.** NLMA national services are official aggregations/reference and law sources, not a substitute for local promulgated plan evidence. |
| Local authority requirement | **Mandatory for urban zoning and plan-specific controls.** Current local non-urban records are also required for current parcel classification. |
| Zoning | `CONDITIONAL GO` for source-coded observations; local authoritative confirmation required |
| Permitted use | `CONDITIONAL GO` as a versioned derived reviewer aid; no automatic legal conclusion |
| FAR | `CONDITIONAL GO` for cited base control only |
| BCR | `CONDITIONAL GO` for cited base control only |
| Redevelopment | `CONDITIONAL GO` for separately labelled context only |
| Parcel linkage | `CONDITIONAL GO` in Taipei through official open parcel keys after identity confirmation |
| Point linkage | `CONDITIONAL GO` as derived candidate evidence only |
| Recommended first jurisdiction | **Taipei City (`63000`)** |
| Suggested first slice | **Taipei parcel zoning observation plus manual authoritative plan/certificate evidence workflow** |
| External blockers | Source contracts, CRS/version lineage, official parcel foundation, plan-to-record mapping, permitted-use/renewal automation rights, professional rule review, and per-agency restriction confirmation |
| Final | **CONDITIONAL GO** |
