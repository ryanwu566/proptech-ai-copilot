# Release Signoff Template

Complete this template only after the local quality gate and manual production
acceptance are separately verified. All fields default to `PENDING`, `no`, or
`NO_GO`; blank or unverified fields do not count as approval.

```text
RELEASE_CANDIDATE_COMMIT=PENDING
LOCAL_AUTOMATED_TESTS=PENDING
PR_CI=PENDING
MERGED_TO_MAIN=no
VERCEL_PRODUCTION_READY=pending
BACKEND_DASHBOARD_HEALTHY=pending
BACKEND_HEALTH_MANUAL_CHECK=PENDING

DESKTOP_PRIMARY_FLOW=PENDING
MOBILE_320=PENDING
MOBILE_375=PENDING
TABLET_768=PENDING
KEYBOARD_ACCESSIBILITY=PENDING
DATA_STATE_COPY=PENDING
EVIDENCE_DISCLOSURE=PENDING
VALUATION_TRUST_BOUNDARY=PENDING
PROPERTY_CASE_TRUST_BOUNDARY=PENDING
PRIVACY_BOUNDARY=PENDING
FAILURE_RECOVERY=PENDING

KNOWN_LIMITATIONS=PENDING
BLOCKERS=PENDING
RELEASE_DECISION=NO_GO
```

The release decision may become `GO` only when CI, main integration,
frontend readiness, backend dashboard health, desktop/mobile/tablet behavior,
keyboard accessibility, data-state semantics, evidence disclosure, trust
boundaries, privacy, and failure recovery are all confirmed. A local test or
build alone is insufficient.

Never record credentials, database settings, provider payloads, addresses,
coordinates, tokens, raw errors, response bodies, or private deployment values
in this template.
