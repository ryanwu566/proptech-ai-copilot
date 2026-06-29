# Taiwan Market Data Foundation v1

## Purpose

Market Insight must not expand bundled mock numbers into Taiwan-wide market
coverage. Production responses should only display prices, transaction counts,
trend values, livability signals, or ESG helper scores when a traceable
aggregate artifact exists.

## Current Policy

- `data/mock_market_insights.csv` remains a demo fixture only.
- Production Market Insight routes must not read the mock CSV as fallback.
- If no aggregate artifact exists, the API returns `data_status=unavailable`.
- Unavailable, incomplete, or invalid data must not be converted to `0`, low
  risk, low price, or favorable buying language.
- Market data is background context only. It must not create valuation, loan,
  tax, legal, or purchase recommendations.

## Minimum Aggregate Contract

Each district-period aggregate should provide:

- `county`
- `district`
- `period`
- `average_unit_price`
- `transaction_count`
- `source_name`
- `source_updated_at`
- `coverage_status`
- `data_status`
- `caveat`

Optional traceability metadata:

- `source_file_hash`
- `aggregation_method`
- `record_count`

## Allowed Status Values

`data_status`:

- `available`
- `unavailable`
- `incomplete`
- `invalid`

`coverage_status`:

- `nationwide`
- `partial`
- `unknown`

## Import Workflow

Use `scripts/import_market_data.py` only with a local CSV prepared outside the
repository. The importer does not download data and defaults to dry-run mode.

Dry-run output is limited to:

- `IMPORT_RESULT`
- `AGGREGATE_REGION_COUNT`
- `COVERAGE_STATUS`
- `DATA_STATUS`

Use `--write` only after the input source, source date, coverage, and caveat
have been reviewed. Do not commit raw transaction data.

## Frontend Behavior

When the API reports unavailable data:

- Show a clear unavailable state.
- Do not render fake average unit price, transaction count, trend, livability,
  or ESG values.
- Keep the user-facing caveat visible.

When the API reports available data:

- Show the district-period aggregate.
- Show source name, source update time, coverage status, data status, and
  caveat.

## Not Included

This foundation does not include:

- raw official transaction data
- raw provider payloads
- credentials, tokens, or API keys
- provider URLs
- database import jobs
- external API access
- browser storage
- purchasing or investment recommendations
