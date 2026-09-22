# Terrain Disaster Risk Public-Source Audit v1

Audit date: 2026-09-21

Scope: six semantic hazard layers used by Terrain Risk. Only producing-agency and Taiwan Government Open Data sources were accepted. “No” for access controls means the official documentation publishes anonymous access with no such requirement and an anonymous bounded request was possible where a live service exists; it is not an assertion about unrelated agency systems.

| Layer | Agency | Official Source | Access | Auth | Application | Geometry | Coverage | Status |
|---|---|---|---|---|---|---|---|---|
| landslide | 農業部農村發展及水土保持署 (ARDSWC) | [大規模崩塌公開 API/MVT](https://data.ardswc.gov.tw/Data/OpenData/Api); [114 年 79 處潛勢區](https://data.gov.tw/dataset/172540); [影響範圍](https://data.gov.tw/dataset/172541) | MVT; downloadable SHP | No | No | Polygon | Live MVT documents 113-year 65 listed areas; 114-year downloads contain 79. Listed zones only, not continuous nationwide coverage. | `LIVE_NOW` |
| debris_flow | ARDSWC | [土石流公開 API/MVT](https://data.ardswc.gov.tw/Data/OpenData/Api); [attributes](https://data.gov.tw/dataset/7279); [114-year SHP](https://data.gov.tw/dataset/172537) | MVT; REST/JSON attributes; downloadable SHP | No | No | Line and polygon | Live MVT documents 1,736 listed streams for year 113; year-114 SHP contains 1,745. Listed streams/impact areas only. | `LIVE_NOW` |
| flood | 經濟部水利署 (WRA) | [淹水潛勢圖](https://data.gov.tw/dataset/25766); [official resource catalog](https://opendata.wra.gov.tw/api/v2/de9578fe-b014-4f00-b8ca-e6280324f08d?format=JSON&sort=_importdate+asc) | REST/JSON catalog; downloadable SHP/7z | No | No | Polygon | 20 jurisdiction packages and 10 design-rainfall scenario SHPs; the official record limits coverage to each model-construction extent. | `DOWNLOAD_ETL_REQUIRED` |
| geological_sensitivity | 經濟部地質調查及礦業管理中心 (GSMMA) | [地質敏感區範圍數值檔](https://data.gov.tw/dataset/27744); [official download index](https://www.gsmma.gov.tw/uploads/1719480931378tHI9XTJa.csv) | CSV index; downloadable SHP archives | No | No | Polygon | Announced sensitive areas only, split by type and announcement; not continuous nationwide classification. | `DOWNLOAD_ETL_REQUIRED` |
| liquefaction | GSMMA | [土壤液化潛勢圖資群組](https://data.gov.tw/dataset/28691); [official OpenAPI](https://www.geologycloud.tw/geohome/DataService/swagger/api); [GeoJSON API](https://www.geologycloud.tw/api/v1/zh-tw/liquefaction) | REST/GeoJSON; JSON/GeoJSON download | No | No | Polygon | Live provider coverage is limited to explicitly supported trusted-city → official-area mappings within the named assessed regions. Coordinates-only requests without a trusted `area_hint` fail closed; nationwide coverage is not claimed. | `LIVE_NOW` |
| active_fault | GSMMA | [活動斷層分布圖 WMS](https://data.gov.tw/dataset/6697); [official map](https://fault.gsmma.gov.tw/About/Fault_map) | WMS raster; downloadable JPG; separate sensitive-area SHP | No | No | Raster rendering of lines; separate sensitive-area polygons | Official 2021 revised map lists 36 land faults; the public WMS is non-queryable. | `UNKNOWN` |

All six principal data.gov.tw records above state free use under the **Government Open Data License, version 1.0**. The ARDSWC MVT catalog labels the four live slope-hazard layers as open data. No audited source documents an API key, account application, fixed-IP allowlist, or private credential for these public resources.

## Spatial operations supported by the official data

| Layer | Point-in-polygon | Nearest distance | Official class/value lookup |
|---|---|---|---|
| landslide | Yes, from the MVT/SHP polygons | Yes, from polygon geometry | Partial: annual SHP documents `Risk`; the audited MVT page does not separately document its property schema |
| debris_flow | Yes, for impact-area polygons | Yes, for stream lines and impact-area boundaries | Partial: annual SHP documents `Risk`; the audited MVT page does not separately document its property schema |
| flood | Yes, after offline SHP ingestion | Yes, after ingestion/indexing | Yes, inundation-depth class per design-rainfall scenario |
| geological_sensitivity | Yes, after offline SHP ingestion | Yes, after ingestion/indexing | Designation type/name only; no generic risk class |
| liquefaction | Yes: accepted address geocoding → trusted city → official GeologyCloud area → three bbox-bounded GeoJSON queries → strict point-in-polygon | No; the production path uses strict point-in-polygon only | Yes: official `低潛勢` / `中潛勢` / `高潛勢` classifications |
| active_fault | No verified feature operation for the 2021 fault-line WMS | No verified vector geometry for distance | No; former categories represented age evidence, not risk level |

## Can integrate immediately

- **Landslide and debris flow are already integrated.** The official ARDSWC catalog documents anonymous GET MVT services for the [potential landslide polygon](https://gis.ardswc.gov.tw/api/ardswc/vectortiles/shp/potential_landslide/{z}/{y}/{x}.pbf), [potential landslide impact polygon](https://gis.ardswc.gov.tw/api/ardswc/vectortiles/shp/potential_landslide_affect/{z}/{y}/{x}.pbf), [debris-flow line](https://gis.ardswc.gov.tw/api/ardswc/vectortiles/shp/debris_flow/{z}/{y}/{x}.pbf), and [debris-flow impact polygon](https://gis.ardswc.gov.tw/api/ardswc/vectortiles/shp/debris_affect/{z}/{y}/{x}.pbf). The live catalog identifies these as year-113 data. Newer annual downloads do not justify silently changing the live provider’s vintage.
- **Liquefaction is integrated with partial regional coverage.** The production provider accepts address-geocoded coordinates, requires a trusted city to route to an explicitly supported official GeologyCloud `area`, and makes three documented bbox-bounded GeoJSON requests for `低潛勢`, `中潛勢`, and `高潛勢`. Each request uses only `area`, `classify`, and `bbox`; `all` is omitted, and no undocumented `all=false` behavior is used. Matching is strict point-in-polygon. Unsupported or ambiguous areas return `unavailable`; incomplete official queries return `limited` or `error` and are never interpreted as low risk. When all three queries complete but the point matches no polygon, the result is `available`, `matched=false`, `level=unknown`; this is not proof of no liquefaction risk. Coverage remains limited to explicitly supported official regional mappings, with no nationwide claim, and coordinates-only requests without a trusted `area_hint` fail closed.

## Needs offline download/ETL

- **Flood:** the public JSON endpoint is a resource catalog, not a coordinate-risk API. It links 20 regional archives dated 2018-10-31 and ten SHP scenarios dated 2022-08-12: 6-hour 150/250/350 mm, 12-hour 200/300/400 mm, and 24-hour 200/350/500/650 mm. The future ingestion job should download once, verify checksums, normalize CRS and depth attributes, build scenario-aware spatial indexes, retain WRA build dates, and serve immutable versioned snapshots. It must preserve the official restriction that the map is for disaster-prevention reference and not a land-use-control determination.
- **Geological sensitivity:** the [official CSV index](https://www.gsmma.gov.tw/uploads/1719480931378tHI9XTJa.csv) links individual RAR/ZIP/7z packages for active-fault, landslide, groundwater-recharge, and geological-heritage sensitive areas. A future ETL should fetch each package once, retain type/number/name/announcement date/document number, normalize TWD67/TWD97 central meridians, validate geometry, and create a versioned spatial index. The data.gov.tw metadata was updated 2024-06-27 and declares irregular updates.

## Requires application/access approval

None of these six audited public sources documents an application, fixed-IP allowlist, or private credential requirement. NLSC terrain gateway access remains separate and out of scope.

## Unknown / needs further verification

- **Active fault analytical access:** data.gov.tw documents the official MapGuide WMS base. A bounded `GetCapabilities` request returned HTTP 200 and listed `WMS/25K_Geomap_fault_2021` plus `WMS/Sensitive_area_fault`, but both have `queryable=0`. The WMS can render maps but does not provide verified feature geometry for nearest-fault calculations or `GetFeatureInfo`. The official active-fault site says the 2021 revised geometry contains 36 faults; an October 2025 revision removed the former first/second labels without changing count, length, or position. The separately downloadable active-fault **sensitive-area** polygons in [dataset 27744](https://data.gov.tw/dataset/27744) are legally defined zones, not a substitute for the complete fault traces. Raster color inspection and private GIS endpoint reverse engineering are excluded.

## Exact flood SHP resources

The WRA catalog currently publishes these exact scenario downloads:

- <https://gic.wra.gov.tw/gis/gic/API/Google/DownLoad.aspx?fname=flood_150mm_6hr&filetype=SHP>
- <https://gic.wra.gov.tw/gis/gic/API/Google/DownLoad.aspx?fname=flood_250mm_6hr&filetype=SHP>
- <https://gic.wra.gov.tw/gis/gic/API/Google/DownLoad.aspx?fname=flood_350mm_6hr&filetype=SHP>
- <https://gic.wra.gov.tw/gis/gic/API/Google/DownLoad.aspx?fname=flood_200mm_12hr&filetype=SHP>
- <https://gic.wra.gov.tw/gis/gic/API/Google/DownLoad.aspx?fname=flood_300mm_12hr&filetype=SHP>
- <https://gic.wra.gov.tw/gis/gic/API/Google/DownLoad.aspx?fname=flood_400mm_12hr&filetype=SHP>
- <https://gic.wra.gov.tw/gis/gic/API/Google/DownLoad.aspx?fname=flood_200mm_24hr&filetype=SHP>
- <https://gic.wra.gov.tw/gis/gic/API/Google/DownLoad.aspx?fname=flood_350mm_24hr&filetype=SHP>
- <https://gic.wra.gov.tw/gis/gic/API/Google/DownLoad.aspx?fname=flood_500mm_24hr&filetype=SHP>
- <https://gic.wra.gov.tw/gis/gic/API/Google/DownLoad.aspx?fname=flood_650mm_24hr&filetype=SHP>

## Classification rule used

- `LIVE_NOW`: a documented anonymous public service returns usable geometry now.
- `DOWNLOAD_ETL_REQUIRED`: official usable geometry exists only as download files that require controlled offline ingestion.
- `APPLICATION_REQUIRED`: the official source requires approval, credentials, or allowlisting.
- `METADATA_ONLY`: only descriptive/catalog information is available, without usable hazard geometry.
- `UNKNOWN`: official public material exists, but the audited access does not support the spatial operation required by Terrain Risk and no safe official alternative was verified.
