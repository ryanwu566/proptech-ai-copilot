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
