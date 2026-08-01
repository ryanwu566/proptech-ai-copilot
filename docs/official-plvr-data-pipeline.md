# Official PLVR market data pipeline

Market Insight accepts official Ministry of the Interior / Department of Land
Administration PLVR batch releases. `config/official-market-sources.json` is a
metadata-only registry. It contains no credentials, signed URLs, downloaded
archives, or nationwide transaction rows.

The pipeline phases are discover, download, verify, extract, schema, normalize,
validate, stage, aggregate, integrity, publish, cleanup, and evidence. A release
is publishable only after schema and row validation succeeds. The prior active
release remains active if any phase fails.

## Normalization

ROC dates are parsed strictly and never replaced with ingestion dates. Prices
remain in NTD and areas remain in square metres; ping display values use the
exact constant `1 ping = 3.305785 square metres`. Sale, presale, rental, land,
parking-only, and other records are kept in separate transaction categories.
County and district names use the canonical administrative registry.

Special transaction notes produce bounded, reviewable flags. They are not
silently deleted. Raw notes and raw archives stay server-side and are not
returned by public endpoints.

## Release identity and quality

Release IDs, publication dates, schema versions, archive/file checksums, import
counts, quarantine counts, duplicate counts, and bounded reason codes are
recorded as evidence. Unknown, changed, or unavailable releases are explicit
failure states, never “no new data”.

The public read model is aggregate-only. It reports sample sufficiency,
coverage, source, freshness, and methodology. It is not an appraisal and does
not make a purchase recommendation.

## Bounded public-resource canary

The current PLVR Open Data ZIP routes are public resources. The registry first
checks the official data.gov.tw catalog, then uses the registry-owned public
route, and finally parses an official PLVR page. No owner download credential
is required for these routes. Only the exact allowlisted host, path, query
filename, ZIP signature, size limit, archive structure, and transaction schema
are accepted.

Run the bounded canary from PowerShell without passing a URL or secret:

```powershell
python scripts/plvr_market_pipeline.py canary `
  --source moi_plvr_combined_current `
  --max-parse-rows 200 `
  --output-report .local/market-canary-report.json
```

The report contains only safe release metadata and aggregate counts. Temporary
raw staging is removed when the command completes; `--retain-staging` is an
explicit operator-only troubleshooting option. A network or transport failure
must remain a network failure and must not be interpreted as an authorization
requirement or as proof that data is missing.
