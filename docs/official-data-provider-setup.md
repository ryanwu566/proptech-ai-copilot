# Official Terrain and Tax Data Setup

This document records the source boundary for the official-data package. The
application does not call a provider merely because it is registered. A source
is shown as `not_checked` until an operator has validated an official snapshot
or run an explicitly approved canary.

## Verified source references

Terrain references:

- NLSC Land Survey and Mapping Center, National Land Use / Taiwan base-map
  services: <https://maps.nlsc.gov.tw/pro/sysinfo.jsp> and the Taiwan base-map
  standard at <https://www.nlsc.gov.tw/cp.aspx?Create=1&n=15899>.
- Agriculture and Rural Development and Water Conservation Agency open-data
  catalog, including debris-flow reference datasets: <https://data.ardswc.gov.tw/Data/OpenData/Api>.
- National Science and Technology Center for Disaster Reduction data hub:
  <https://datahub.ncdr.nat.gov.tw/>.

The only retained live-query endpoint is the NLSC WMTS GetCapabilities path
documented by the [NLSC service manual](https://maps.nlsc.gov.tw/downloaddoc/UserManual.pdf): `https://wmts.nlsc.gov.tw/wmts` with the
standard WMTS `GetCapabilities` request. It is an opt-in canary only; the
application does not call it during a normal page load. ARDSWC and NCDR remain
manual-download sources in this repository because no stable, verified query
contract is claimed here.

Tax references:

- Ministry of Finance House Tax Act: <https://law-out.mof.gov.tw/LawContent.aspx?id=FL006141>.
- Ministry of Finance Land Tax Act: <https://law-out.mof.gov.tw/LawContent.aspx?id=FL006135>.
- Ministry of Finance eTax house-tax guidance:
  <https://www.etax.nat.gov.tw/etwmain/tax-info/understanding/tax-saving-manual/local/house-tax/5qYVKWW>.

These are source references, not evidence that a current live query or a
particular jurisdictional rate is available. No rate is invented in this
repository. Local rules must be imported with an exact jurisdiction and
effective date.

## Credentials and application steps

The selected public source references do not require an API key for this
metadata and manual-snapshot workflow. No new credential environment variable
is required. If an agency later requires an approved application for a live
adapter, the operator must:

1. Apply through the agency's own official portal.
2. Confirm permitted format, rate limits, attribution and coverage.
3. Store credentials only in the deployment secret manager.
4. Run a bounded canary and record the returned schema/version without storing
   tokens, raw payloads, coordinates or provider errors.

## Offline validation and refresh

The commands accept files already downloaded by an operator. They are dry-run
by default and do not call an external provider or mutate a database:

```text
python scripts/import_official_terrain.py --input <local-geojson> --provider-id ardswc_debris_flow_reference
python scripts/import_official_tax_rules.py --input <local-rule-json>
python scripts/check_official_data_status.py --domain all
python scripts/canary_official_data.py --provider-id nlsc_base_map --allow-network
```

Each validation reports a checksum, version fields, accepted count and
rejected count. Duplicate rule keys and invalid date ranges are rejected.
There is no destructive overwrite flag; a future persistence adapter must
retain the previous version and provide an explicit rollback operation.

## Runtime and privacy boundary

- Terrain evidence is reference-only. A match is not a safety conclusion, and
  `not_matched_in_loaded_layer` is not “no risk”. Existing Terrain scoring is
  unchanged.
- Terrain uses existing runtime geocoding and explicit analysis actions. A
  result is not automatically attached to a Property Case. Case attachment
  may contain only the reduced evidence contract, never raw coordinates,
  geometries, tile URLs or provider payloads.
- TaxOracle remains a deterministic preliminary screening and document
  checklist. TX001–TX009 are stable product rule identifiers, not government
  codes or personal tax records. Output is not an official assessment, bill or
  legal opinion.
- Missing local tax rules return `jurisdiction_data_unavailable`; another
  jurisdiction or a national fallback is never silently selected.
- Source availability is separate from frontend availability. `not_checked`,
  `not_configured`, `unavailable`, `stale` and `partial` remain visible states.

## Runtime status endpoints

- `GET /terrain-risk/sources` returns registered Terrain source metadata and
  conservative runtime status.
- `GET /taxoracle/sources` returns TaxOracle rule-source metadata and the
  preliminary-calculation boundary.

Neither endpoint calls an external provider.

The canary is separate from the runtime endpoints. It has a 20-second timeout,
reads at most one megabyte of capabilities data, validates the WMTS capability
marker, and reports only status/schema fields. It is not run by tests, builds,
or the quality gate. Current canary status for this environment: `not_run`.
