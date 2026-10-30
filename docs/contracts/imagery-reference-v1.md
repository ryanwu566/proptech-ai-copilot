# Bounded imagery reference contract

`POST /terrain/satellite-reference` continues accepting only finite `latitude`
(-90 through 90) and `longitude` (-180 through 180). Extra fields, including
provider, layer, URL, year, dates and geometry, receive HTTP 422. All provider
controls belong to the operator. No endpoint or frontend contract for other
capabilities changes.

Successful request admission returns HTTP 200 with `status` equal to
`available`, `limited` or `unavailable`. Unavailable has no image. It never
means safe or outside a hazard. Existing auth, quota, concurrency and disabled
capability errors keep their HTTP 401/403/429/503 contracts; this route does not
disable those controls or turn on providers.

| Field | Meaning |
|---|---|
| `provider` | `nlsc_photo2`, `csrsr_spot`, `earth_engine`, or `unknown` |
| `source_type` | `orthophoto`, `satellite`, or null when unconfigured |
| `source` | Source identifier, including its official service URL for Taiwan adapters |
| `dataset_or_layer` | PHOTO2 or capabilities-confirmed annual SPOT layer; empty if unconfirmed |
| `observation_date` | Null unless an actual observation date is supplied; Taiwan sources return null |
| `vintage` | Annual SPOT year, otherwise null; never synthesized from retrieval time |
| `date_precision` | `unknown`, `year`, `range`, or `day`; Taiwan sources use unknown/year |
| `retrieval_time` | UTC request/retrieval check time, not an acquisition timestamp |
| `aoi_radius_m`, `center` | Fixed 500 m contextual extent and accepted latitude/longitude |
| `bbox`, `bbox_crs` | Four `[minx,miny,maxx,maxy]` bounds in EPSG:3857, or null without a result |
| `processing_method` | Actual WMS reencoding, WMTS composition/crop, or EE median processing |
| `image_reference` | Bounded embedded JPEG data URI, or null; no upstream URLs/tokens |
| `attribution`, `limitations`, `disclaimer` | Display and retain the source restrictions and evidence limits |
| `usage_restriction` | CSRSR noncommercial/competition restriction; nullable |
| `status`, `reason_code` | Explicit image availability and fixed sanitized outcome |

Existing `dataset`, `window_start`, `window_end`, `composite_method` and
`cloud_filter_percent` remain for compatibility. `dataset` aliases the layer;
`composite_method` describes actual processing. Window and cloud fields are
**null** for Taiwan imagery. EE retains its real collection, 90-day window and
35% cloud filter; these are never attached to PHOTO2 or SPOT. The UI accepts
older responses without new fields and recognizes legacy EE only from its
explicit Copernicus dataset. Its initial/error presentation is provider neutral.

PHOTO2 with valid imagery returns `limited / vintage_unknown` because the
capture date is unknown. Show the image as orthophoto/aerial reference. SPOT
with a valid image returns available annual historical satellite reference;
this does not assert freshness. Display year, annual mosaic limitation and
noncommercial restriction. A mosaic year is not a single-day observation.

Examples of unavailable reasons include `configuration_error`,
`licensing_not_accepted`, `tls_verification_failed`, `provider_timeout`,
`provider_capacity_exhausted`, `outside_coverage`, `no_data`,
`layer_unavailable`, `invalid_capabilities`, `tile_limit_exceeded`,
`unexpected_mime`, `response_too_large`, `invalid_image`, and `provider_error`.
No raw exception, credentials, signed URLs or upstream error bodies are returned.
Provider failure has no fallback to a different source or to EE.

The frontend fetches only on the explicit user action after coordinate
acceptance, never mount, disclosure or coordinate change. Results stay in
component memory and are invalidated for a different case/location. No raw
image bytes are persisted in Saved Cases or localStorage. The image has no
effect on risk scores, risk interpretation or statutory conclusions. It proves
neither cadastral limits, ownership, building legality, disaster safety nor
lawful land use, and is never described as real-time imagery.
