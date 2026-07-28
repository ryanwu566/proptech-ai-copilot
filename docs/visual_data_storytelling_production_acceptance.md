# Visual Data Storytelling Production Acceptance

This is a manual Phase 5A checklist. It starts in a not-yet-accepted state and
does not call production services or store production response data.

## Deployment gate

- `PENDING`: Pull request CI is green.
- `PENDING`: The intended commit is merged to `main`.
- `PENDING`: Frontend deployment is ready in the configured hosting dashboard.
- `PENDING`: Backend deployment dashboard is healthy.
- `PENDING`: The deployed frontend uses its configured API boundary and the
  health check is reachable without browser credentials.

## Full-site desktop flow

- `PENDING`: Property Finder is the primary first action.
- `PENDING`: Location Insight, Terrain Risk, Commute Livability, Market
  Insight, Valuation, Aegis Credit, Holding Cost, TaxOracle, comparison, and
  decision report remain reachable.
- `PENDING`: Initial, loading, available, no-data, unavailable, partial,
  stale, unknown, missing, blocked, and demo states use their exact meaning.
- `PENDING`: Source, freshness, and calculation evidence are disclosed by
  explicit controls and do not replace the primary result.
- `PENDING`: A partial case remains printable with its incomplete-data notice;
  no module turns missing data into a fabricated value or recommendation.

## Responsive and keyboard flow

- `PENDING`: Check 320px, 375px, and 768px widths.
- `PENDING`: No principal chart requires horizontal page scrolling; dense
  detail tables are inside explicit disclosures.
- `PENDING`: Keyboard-only tab order, visible focus, labels, summaries,
  disclosures, and live loading/error announcements are usable.
- `PENDING`: Reduced-motion preferences preserve information and state copy.

## Privacy and recovery

- `PENDING`: No address, coordinates, raw payload, response body, token,
  credential, SQL, stack trace, or raw provider error is exposed in the UI or
  copied into evidence.
- `PENDING`: No new localStorage, sessionStorage, cookie, URL query, or URL
  hash persistence is present.
- `PENDING`: Unavailable is not presented as no data or low risk; unknown is
  not presented as safe; partial is not presented as complete; demo is not
  presented as official.
- `PENDING`: Retry, corrected input, or an unavailable module does not break
  unrelated analysis or alter decision rules.

## Signoff rule

Until all required checks above are manually verified, record:

```text
RELEASE_DECISION=NO_GO
```

Do not put real deployment values, secrets, addresses, coordinates, URLs,
provider payloads, or production response bodies in this document.
