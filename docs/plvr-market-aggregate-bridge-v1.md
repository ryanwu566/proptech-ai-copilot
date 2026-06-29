# PLVR Market Aggregate Bridge v1

## Purpose

The bridge lets Market Insight read district-level aggregates from the existing
valuation PostgreSQL data source. It does not download PLVR data, does not run
imports, and does not copy raw transactions into the repository.

## Data Flow

```text
real_price_transactions
→ read-only city/district/period aggregate
→ Market Data Foundation response contract
→ /market-insights status, regions, and query endpoints
→ Market Insight UI
```

## Read-Only Rules

- The bridge only reads rows where `source = official_plvr_opendata`.
- It only aggregates rows with valid `city`, `district`, `transaction_period`,
  `unit_price_per_ping`, `total_price`, and `area_ping`.
- It returns aggregate counts and average unit price only.
- It never returns raw rows, full addresses, coordinates, transaction IDs,
  connection details, database URLs, tokens, or provider errors.
- It must not execute imports, migrations, deletes, updates, seeds, or scope
  replacements.

## Coverage Policy

`coverage_status` is conservative:

- `partial`: aggregate candidates exist, but the current schema/import metadata
  does not prove complete Taiwan-wide coverage.
- `unknown`: no usable aggregate candidates or metadata are available.
- `nationwide`: reserved for future explicit reviewed metadata; it must not be
  inferred only from record counts.

## Data Status Policy

- `available`: the bridge can aggregate a requested county, district, and period.
- `unavailable`: database config is absent, the read query fails safely, or no
  matching aggregate candidate exists.
- `incomplete`: aggregate candidates exist but required source metadata is
  missing.
- `invalid`: aggregate output violates the public Market Data Foundation
  contract.

Unavailable, incomplete, and invalid states must not be rendered as zero price,
low price, low risk, or favorable purchase language.

## Product Boundaries

Market data is background context only. It must not automatically change:

- valuation estimates
- loan or credit results
- tax results
- legal conclusions
- case comparison ranking
- viewing decision summary
- purchase recommendations

The frontend must not store market query results in localStorage,
sessionStorage, cookies, URL query state, or hash state.
