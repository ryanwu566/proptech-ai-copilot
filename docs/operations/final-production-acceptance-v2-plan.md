# Final Production Acceptance v2 plan

**Goal:** Decide Controlled Beta readiness for frozen candidate `c9ab5f61a45f7f704326af66cb0bea02740b9927`.

**Architecture:** Reuse `scripts/generate_release_evidence.py`, production smoke, provider/closure contracts, migration registry, and guardrail evidence validation. Record hosted observations separately from local and synthetic browser evidence. Evidence files are the only committed deliverables; application behavior stays frozen.

**Constraints:** Current worktree and branch only; no production writes, deployments, provider-account changes, ML-B, relaxed tests, or bundle ceiling changes. Exactly one acceptance commit; no push or merge. Satellite generation is excluded. Browser contexts are disposable, and unexpected provider or mutation traffic is blocked and counted.

1. Freeze branch, clean status, exact SHA, commit message, remote main, and timezone-aware timestamp.
2. Execute Python and deterministic frontend suites, typecheck, lint, build, dependency audits, hygiene, release/security/operations/migration/bundle gates. Record commands, exits, counts, and failure classifications.
3. Observe production identity, health, compatibility, source/config projections with bounded read-only requests.
4. Exercise deployed Homepage and Demo without fixtures, then separately exercise deployed saved-case rendering using explicitly synthetic browser-local snapshots. Never infer real provider acceptance from these snapshots. Record untested live acquisition and durable hosted persistence honestly.
5. Inspect actual A4 PDFs, responsive/locales, accessibility samples, and provider-request traces. Retain binary evidence locally with hashes.
6. Review authoritative provider/artifact registries, control scopes, migration inventory, recovery evidence, and ML boundaries.
7. Aggregate categorical gates through the existing evidence generator; add detailed v2 validation and owner actions. Obtain independent read-only review and resolve acceptance-evidence defects.
8. Validate evidence, inspect the diff, recheck frozen identity and remote main, and create the single acceptance commit.

**Review focus:** False GO; reported SHA versus runtime mismatch; synthetic data mistaken for production acceptance; intercepted requests mistaken for zero attempts; local controls/rehearsals mistaken for fleet or hosted proof; unverified provider provenance; changing candidate or tests to obtain a pass.
