# Nationwide Market Read Model v1

## Purpose

Nationwide Market Read Model v1 separates the standard public Market Insight
status and catalog GET reads from raw PLVR transaction storage. Those GET
endpoints use prepared aggregate metadata and rows instead of querying
`real_price_transactions`.

Interactive POST queries use a separate bounded, read-only path. Both
district-only and road-aware POST queries read existing official PLVR
transaction rows. District-only queries calculate safe SQL aggregates and
history; road-aware queries read a privacy-safe district projection so the
rolling window, post-filter sample threshold, and exact road identity can be
applied at request time. Neither POST path assumes a road aggregate exists in
the prepared read model.

The read model stores aggregate market fields only. It does not store raw
transaction rows, addresses, coordinates, building names, provider payloads,
database connection details, or credentials.

## Data Flow

```text
existing PLVR valuation database
-> protected POST /market-insights/refresh
-> market_district_period_aggregates
-> market_read_model_metadata
-> GET /market-insights/status
-> GET /market-insights/catalog
-> GET /market-insights/regions
```

GET endpoints read only the read model tables. They do not read
`real_price_transactions`.

The interactive query flow is separate:

```text
existing official PLVR transaction rows
-> POST /market-insights/query { county, district, road? }
-> validate canonical region and bounded road identity
-> district-only: execute bounded aggregate and history queries
-> road-aware: read an address-free district projection
-> road-aware: apply rolling 36-month filters and select ROAD -> DISTRICT -> NOT_AVAILABLE
-> return aggregate statistics and safe provenance only
```

The road evidence projection contains only transaction period, canonical
county/city, district, road, unit price per ping, total price, area, source, and
import timestamp. It excludes address text, coordinates, row identifiers,
provider payloads, and raw notes. The query is not truncated before the
post-filter threshold is calculated.

## Read Model Tables

`market_district_period_aggregates` contains district-period aggregate rows:

- `county`
- `district`
- `period`
- `average_unit_price`
- `transaction_count`
- `record_count`
- `source_name`
- `source_updated_at`
- `coverage_status`
- `data_status`
- `aggregation_method`
- `built_at`

`market_read_model_metadata` contains refresh and coverage metadata:

- `read_model_version`
- `refresh_status`
- `coverage_status`
- `source_name`
- `source_updated_at`
- `earliest_period`
- `latest_period`
- `available_county_count`
- `available_district_count`
- `aggregate_region_count`
- `built_at`
- `caveat`

Coverage is reported conservatively. Distinct county or district counts are
metadata, not proof of nationwide completeness.

## Protected Refresh

The protected refresh endpoint is:

```text
POST /market-insights/refresh
```

It requires the request header:

```text
X-Market-Read-Model-Refresh-Token
```

The backend runtime reads the expected token from:

```text
MARKET_READ_MODEL_REFRESH_TOKEN
```

If the token is missing from runtime configuration, the endpoint returns a safe
unavailable response and performs no database work. If the request token is
incorrect, the endpoint returns forbidden and performs no database work.

Refresh is the only write path. Public Market Insight status, catalog, region,
and query endpoints are read-only. The road evidence path performs no import,
refresh, migration, or provider call.

## GitHub Actions Manual Workflow

The manual workflow is:

```text
.github/workflows/refresh-market-read-model.yml
```

It is intentionally `workflow_dispatch` only. There is no scheduled refresh.

Configure GitHub Actions repository secrets:

- `RENDER_API_BASE_URL`
- `MARKET_READ_MODEL_REFRESH_TOKEN`

Do not put real values in source code, documentation examples, frontend code,
URLs, logs, or screenshots.

Manual operation:

```text
GitHub repo
-> Actions
-> Refresh Market Read Model
-> Run workflow
-> Run workflow
```

Successful safe log output is limited to:

```text
MARKET_READ_MODEL_REFRESH=success
MARKET_READ_MODEL_HTTP_STATUS=200
```

The workflow must not print the Render URL, token, request header, response
body, station names, addresses, coordinates, PLVR rows, or provider errors.

## Unavailable and Incomplete Data

When the read model is missing, stale, unavailable, incomplete, or invalid,
Market Insight must show conservative unavailable messaging. It must not fill
missing periods, interpolate history, or display mock market metrics as if they
were official data.

`POST /market-insights/query` returns history only for periods supported by
the direct official query, with at most six periods in the public history
shape.

For a road-aware query, the same public `history` shape is derived only from
the selected effective scope's valid official rows. It is never built from the
explanatory road or district sample counts. The request does not widen beyond
the rolling 36-month window when a threshold is not met.

## Product Boundary

Market Insight is a market background explorer. Its aggregate data does not automatically change, drive, or override:

- valuation results
- loan or credit calculations
- tax analysis
- legal analysis
- case comparison
- viewing decision summaries
- purchase or viewing recommendations

It must not be described as a formal appraisal, legal conclusion, loan
approval, safety guarantee, or purchase advice.

Road results are historical transaction analysis. They do not represent
active listings, available inventory, or a community finder.
