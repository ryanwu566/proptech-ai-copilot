# Market Coverage Operations v1

This document describes the safe operating model for Taiwan-wide Market Insight coverage.

## Canonical Region Registry

The canonical county and district registry is kept in:

```text
data/taiwan-admin-areas.json
frontend_next/lib/taiwan-admin-areas.ts
```

The registry contains only county names, district names, and safe alias normalization behavior. It does not contain prices, risk scores, coordinates, raw transactions, provider responses, credentials, or source URLs.

## Coverage States

Market Insight uses conservative coverage states:

```text
covered
not_covered
coverage_unknown
```

Query results use:

```text
available
no_data
unavailable
```

Rules:

- `covered` plus a usable aggregate returns `available`.
- `covered` without a usable aggregate returns `no_data`.
- `not_covered` returns `unavailable`.
- `coverage_unknown` returns `unavailable`.
- Runtime or data-source failures return `unavailable`.

Missing data must not be displayed as zero price, low risk, no transactions, or a completed market judgment.

## Operator Coverage Audit

Operators may run the local audit script against a prepared coverage manifest:

```text
python scripts/audit_market_coverage.py --coverage-manifest <local manifest path>
```

The script prints only safe aggregate lines:

```text
MARKET_COVERAGE=FULL|PARTIAL|UNKNOWN
EXPECTED_REGION_COUNT=<count>
COVERED_REGION_COUNT=<count>
MISSING_REGION_COUNT=<count>
UNKNOWN_REGION_COUNT=<count>
MISSING_REGIONS=<county/district labels>
UNKNOWN_REGIONS=<county/district labels>
```

`FULL` exits with status code `0`. `PARTIAL` and `UNKNOWN` exit non-zero so release automation can block broad coverage claims.

## Release Gate

The production UI must not claim full Taiwan-wide market coverage unless the latest operator coverage audit reports:

```text
MARKET_COVERAGE=FULL
```

If coverage is `PARTIAL` or `UNKNOWN`, the product may still allow bounded county or district queries, but the UI must use conservative unavailable or no-data language.

## Direct Query Runtime

User-facing Market Insight queries use:

```text
POST /market-insights/query
```

This path is bounded by canonical county and optional district. It does not depend on Market Read Model refresh, GitHub Actions refresh jobs, or frontend-triggered imports.

The frontend must:

- Query only after the user clicks the market query button.
- Avoid duplicate submits while loading.
- Abort slow requests with a client-side timeout.
- Ignore stale responses after county or district changes.
- Avoid localStorage, sessionStorage, cookies, URL query state, or URL hash persistence for market results.

## Out of Scope

This workflow does not:

- Download PLVR files.
- Import transactions.
- Write to the database.
- Run the Market Read Model refresh.
- Modify valuation, loan, tax, legal, terrain, commute, comparison, or case decision logic.
- Store raw transaction data in the repository.
