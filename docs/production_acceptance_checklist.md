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
