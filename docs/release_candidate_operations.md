# Release Candidate Operations

The release quality gate is a hermetic repository check. Run it from the
repository root with:

```text
python scripts/release_quality_gate.py
```

It checks the canonical Taiwan registry, safe market and valuation contracts,
property-case trust boundaries, deployment declarations, privacy boundaries,
and frontend recovery/accessibility files. The command may run local tests and
the existing frontend build, but it does not call production services,
providers, or a database.

For a contract-only check, use:

```text
python scripts/release_quality_gate.py --skip-tests --skip-frontend-build
```

The output is limited to allowlisted pass/fail/not_run fields. An optional JSON
report may be written atomically to a system temporary path with
`--json-output`; it must not be written into the repository.

Exit codes:

- `0`: the candidate passed all requested checks.
- `1`: a requested test or frontend build failed, or an internal gate failure occurred.
- `2`: a release contract failed.

The gate does not deploy, refresh market data, import PLVR data, reconcile
coverage, or change any environment setting.

## Phase 5A handoff

After the local gate passes, an operator must complete the manual production
acceptance checklist. Confirm frontend readiness, backend dashboard health,
responsive layouts, keyboard use, data-state copy, evidence disclosures, and
failure recovery in the deployed environment. A local build or green
automated test is not production acceptance.

The handoff starts with:

```text
PR_CI=PENDING
MERGED_TO_MAIN=no
VERCEL_PRODUCTION_READY=pending
BACKEND_DASHBOARD_HEALTHY=pending
RELEASE_DECISION=NO_GO
```

Only an operator with deployment access may change these fields after checking
the actual deployment. This document contains no production URL, secret,
credential, response body, or provider payload. The frontend must not carry
backend refresh credentials, and sensitive values must not enter logs or
evidence.
