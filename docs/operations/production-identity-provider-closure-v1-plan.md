# Production identity and provider closure implementation plan

Starting SHA: `b4eb441a8ccf90965102f0646006dc4b0e145491`.
Branch: `fix/production-identity-provider-closure-v1`.
The supplied implementation specification authorizes execution in this worktree
and exactly one final commit. No intermediate commits, push, merge, deployment,
production writes, ML training, satellite generation or automatic provider probes.

Goal: extend existing release evidence with bounded, independently scoped evidence
that Final Production Acceptance v2 can consume without inferring success.

Architecture: immutable backend build JSON supplements the existing release
endpoint; a private local acceptance collector projects configuration, the existing
provider contracts, an authoritative artifact inventory and scoped audit reports.
The frontend build SHA remains an independent hosted-smoke observation. Local
files and configuration never establish deployed state or authorization.

- [x] Identity: failing tests for absent/malformed metadata, environment override,
  bounded allowlisted fields and frontend/backend separation; build writer uses
  git or trusted CI checkout SHA, build timestamp and content identity. Wire Docker
  and Render builds and the existing `/release-version` endpoint.
- [x] Configuration/providers/artifacts: failing tests for placeholders, unknown
  dates, checksum mismatch, oversized inputs, missing remote evidence, fixture PASS,
  disabled providers and live kill switches. Reuse existing validators and sources;
  registry records actual R2, API, database and local dataset storage contracts.
- [x] Runtime audit: collect separate Python manifest, frontend production/dev,
  and machine-global evidence with manifest hashes and tool/runtime identities.
  Reject empty/malformed audit reports. Preserve every finding; no new exceptions.
- [x] Acceptance: extend `generate_release_evidence.py` with an optional v2 closure
  bundle; require complete, versioned evidence sections, preserve blocker lists,
  never issue product GO. Collect bounded committed local JSON.
- [x] Verify: focused tests, full suite, hygiene, release/security gates, diff check;
  prove any starting failures on starting source. Read-only independent review,
  fix Critical/Important findings, report exact inventory/results and owner actions.

Review focus: arbitrary metadata leaking secrets; runtime SHA overriding immutable
build; fixtures or missing audits becoming PASS; local artifacts represented as
active production datasets; unknown/stale/future publication dates becoming fresh;
unbounded provider calls and hidden dependency findings.

Execution ledger and final results are in the companion implementation report.

All implementation tasks and targeted verification completed. Production owner evidence remains explicitly blocked; see the report and machine-readable JSON. Exactly one final commit is required after independent review.
