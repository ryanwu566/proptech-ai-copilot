# NLSC TILE_001 TEST seam

Status: TEST/non-production observation seam only. This is not production
acceptance, a product route, a UI integration, or an accepted identity
provider.

## Official contract

The official NLSC service name is **地籍圖磚**, service code `TILE_001`.
The application integration table classifies it as WMS/WMTS cadastral tile
imagery. This seam selects the WMTS `GetTile` representation only.

The official NLSC WMTS material documents this REST path shape:

```text
https://wmts.nlsc.gov.tw/wmts/{layer}/default/EPSG:3857/{TileLevel}/{TileRow}/{TileCol}
```

For `TILE_001`, the official layer list supplies these fixed values:

| Field | Official value used by this seam |
|---|---|
| Layer | `DMAPS` |
| Style | `default` |
| CRS / matrix-set identifier | `EPSG:3857` |
| Tile level | integer, maximum `19` |
| Tile row | integer `y`, bounded by the selected level |
| Tile column | integer `x`, bounded by the selected level |
| Response format | PNG (`image/png`) |

The application, style, CRS, matrix set, format, layer, and upstream origin are
not caller inputs. The application accepts only `z`, `x`, and `y`, with
`0 <= z <= 19` and `0 <= x,y < 2**z`.

Official sources:

- [NLSC application integration table](https://maps.nlsc.gov.tw/S09SOA/Download.action?fileName=%E7%94%B3%E8%AB%8B%E6%9C%8D%E5%8B%99%E4%BB%8B%E6%8E%A5%E8%AA%AA%E6%98%8E%E8%A1%A8.pdf)
- [NLSC WMTS layer list](https://maps.nlsc.gov.tw/S09SOA/pro/Wmts_ajax_list.jsp)
- [NLSC WMTS FAQ and path template](https://maps.nlsc.gov.tw/S09SOA/pro/faq_ajax_list.jsp)
- [NLSC service eligibility](https://maps.nlsc.gov.tw/S09SOA/pro/intro.jsp)
- [NLSC cadastral-map description](https://maps.nlsc.gov.tw/pro/get_map_message.jsp)
- [NLSC terms of use](https://maps.nlsc.gov.tw/pro/use_clause.jsp)

## Documented limits and unknowns

The official cadastral-map description says the imagery is approximate and
for relative spatial reference. Source surveys, coordinate systems, scales,
sheet transformations, edge matching, and update timing can differ. Questions
about actual rights boundaries require boundary verification by the competent
land office. NLSC describes monthly updating as a principle, not a per-tile
freshness or currency guarantee.

The reviewed official material does not document a precise geographic
completeness boundary for `TILE_001`, a per-tile freshness value, or a
machine-readable distinction between a blank/no-data tile and other valid PNG
imagery. Therefore:

- `coverage` is always `unknown`;
- blank and nonblank PNGs have identical reference-only semantics;
- the seam makes no parcel-existence, parcel-absence, identity, legal-boundary,
  current-cadastral-truth, ownership, building, area, perimeter, or planning
  claim; and
- unexpected, malformed, empty, or non-PNG responses fail closed rather than
  being relabeled as no-data.

The official terms do not provide a stable TILE_001 error schema. They disclaim
availability/immediacy guarantees and reserve service, volume, and bandwidth
limits. This seam consequently exposes bounded local error categories only;
it does not present them as official NLSC error codes.

## Attribution and resource policy

The normalized observation carries this source notice:
`內政部國土測繪中心－國土測繪圖資服務雲`.

NLSC permits lawful public display but prohibits bulk download. Its terms say
NLSC identification/copyright marks must not be altered, removed, or obscured,
and the WMTS FAQ warns against bulk server caching and redistribution. Until
TILE_001-specific cache and redistribution approval exists, this seam:

- uses no disk, memory, CDN, or negative cache;
- sends and returns explicit `no-store` policy;
- never creates a URL-derived cache key; and
- performs a gateway request for every call.

## TEST transport contract

The application calls only this fixed backend-gateway path:

```text
GET {NLSC_GATEWAY_BASE_URL}/nlsc/tiles/TILE_001/{z}/{y}/{x}
```

`NLSC_GATEWAY_BASE_URL` must exactly match one HTTPS origin in
`NLSC_TILE001_TEST_GATEWAY_ORIGINS`. Wildcards, suffix matches, malformed
origins, and all `nlsc.gov.tw` origins are rejected. The allowlist is backend
configuration and is never supplied by a caller. The bearer credential remains
backend-only.

The adapter disables redirects, uses a four-second timeout, requests identity
content encoding, accepts only `image/png`, rejects non-identity response
encoding, and reads at most 524,288 response bytes. PNG validation checks the
signature, chunk framing, ordering, CRCs, IHDR fields, IDAT presence and zlib
stream, decoded scanline size and filter bytes, and terminal IEND with no
trailing bytes. The four-second HTTPX value bounds connect, read, write, and
pool inactivity operations; it is not represented as an end-to-end freshness
or latency guarantee. A response that literally reflects the backend bearer
credential fails closed, and binary response content is excluded from result
representations.

All production-like and serverless runtimes are disabled even when an origin
is allowlisted. No live NLSC request or live credential is part of this seam.

## Normalized observation

Only these source fields are normalized:

```text
source=NLSC
service_code=TILE_001
retrieved_at=<timezone-aware gateway retrieval time>
crs=EPSG:3857
layer=DMAPS
z=<tile level>
x=<tile column>
y=<tile row>
content_type=image/png
attribution=<NLSC source notice>
notice=<reference-imagery-only warning>
coverage=unknown
```

The binary PNG and local no-store policy are carried beside the observation,
not promoted into Property Identity, parcel evidence, or planning facts.
