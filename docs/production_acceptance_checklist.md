# Production Acceptance Checklist

Use this checklist after the release quality gate passes. It is an operator
checklist, not an automated production call.

1. Confirm the backend deployment reports healthy through its configured
   hosting dashboard.
2. Confirm the frontend deployment uses the configured
   `NEXT_PUBLIC_API_BASE_URL` and fails closed if it is absent.
3. Confirm the browser can reach `/health` through the deployed backend.
4. Confirm market no-data and unavailable states show no fabricated numeric
   values, and show source and freshness metadata when available.
5. Confirm valuation is actionable only for trusted official PLVR evidence.
6. Confirm a partial property case remains printable with its data-incomplete
   notice and never becomes a purchase or investment recommendation.
7. Check the mobile layout and keyboard navigation for the critical flows.
8. Record the release decision and any remaining manual acceptance items.

Do not place credentials, database settings, provider payloads, addresses, or
production response bodies in this checklist or in release evidence.

## Phase 5A manual acceptance

Every item below starts as `PENDING`. The default release decision is
`NO_GO` until an operator records evidence for all required gates.

- `PENDING`: Pull request checks are green and the intended commit is merged
  to `main`.
- `PENDING`: Frontend deployment is ready in the configured hosting dashboard.
- `PENDING`: Backend dashboard reports healthy and the deployed health check is
  reachable through the configured frontend API boundary.
- `PENDING`: Property Finder is the clear primary entry point.
- `PENDING`: Location Insight, Terrain Risk, Commute Livability, Market
  Insight, Valuation, loan, holding cost, tax, comparison, and decision report
  flows remain reachable.
- `PENDING`: Initial, loading, available, no-data, unavailable, partial,
  stale, unknown, missing, blocked, and demo states preserve their meaning.
- `PENDING`: Source, freshness, and calculation evidence use explicit
  disclosures without exposing raw payloads.
- `PENDING`: Check desktop behavior and repeat at 320px, 375px, and 768px.
- `PENDING`: Principal charts do not require horizontal page scrolling and
  dense detail tables are behind explicit disclosures.
- `PENDING`: Keyboard-only navigation, visible focus, labels, disclosures,
  and live status announcements work without a mouse.
- `PENDING`: No new browser storage, cookie, URL query, or URL hash persistence
  is used by visual storytelling.
- `PENDING`: Unavailable, unknown, partial, missing, and demo data are not
  presented as successful, official, complete, or low-risk conclusions.
- `PENDING`: Retry and failure recovery do not break unrelated modules or
  change decision rules.

Record final signoff in `docs/release_signoff_template.md`. Until every
deployment, responsive, accessibility, privacy, and recovery item is checked,
use:

```text
RELEASE_DECISION=NO_GO
```
