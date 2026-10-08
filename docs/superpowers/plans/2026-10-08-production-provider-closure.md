# Production Provider Closure Implementation Plan

**Goal:** Close locally fixable provider defects and supply bounded acceptance and rollout procedures without claiming deployed readiness.

**Architecture:** Preserve the merged provider isolation, accepted-property context, evidence contracts and E10 presentation. Extend existing query metadata, artifact validation, operational commands and release smoke; no new global cache, ML, infrastructure or UI redesign.

**Spec:** User-supplied Production Provider Closure implementation request, sections 1–60.

**Global constraints:** Work only in `C:\Projects\proptech-provider-closure`, branch `fix/production-provider-closure-v1`, verified starting SHA `d06ed4f062a212fed4ce0adf092c2fdc515a3f62`. No push, merge, deployment, production writes, artifact upload, secret changes or provider retries. Exactly one commit only after all local exit criteria pass.

**Execution:** Independent domain agents implement Market/Valuation, PLVR operations and risk contracts under the parallel-agent skill; primary implements Location and acceptance integration. All implementation is already authorized by the request. Shared-file ownership is explicit.

## Review focus

- A provider exception must not become empty/no-data evidence; reset per-query diagnostics.
- Missing categories and incomplete/no-match hazard evidence must not become zero, good or safe.
- Frozen GREEN evidence must still respect the current rolling 36-month window and actual capability provenance.
- Failed or duplicate PLVR releases must not partially write or refresh apparent freshness.
- Acceptance must expose only safe metadata, make no offline network requests, and require deployed identity for hosted claims.

## Tasks

- [x] Verify all five starting-state checks and inspect merged implementation before editing.
- [x] Market/Valuation: write and observe failing Finder quartile/SQL, Trend SQL, BLUE/GREEN retention/provenance tests; fix the corresponding provider/service/API contracts; run affected suites. Parent preserves frontend unavailable semantics and suppresses insufficient ranges.
- [x] Location: reproduce 4/6 failure promotion; cover complete, partial, successful zero, total failure and demo evidence; propagate category states, query time, source and coverage through API and UI. Reuse cache, concurrency and dedupe.
- [x] Risk: reproduce unsafe aggregate; retain partial positive alerts with bounded confidence and unknown incomplete/no-match summary. Cover liquefaction admin context and independent failures. Validate WRA/GSMMA artifacts locally and ARDSWC layer/tile semantics, preserving configured vintage.
- [x] PLVR: replace updater skeleton with verified, checksummed release processing, dry-run, transactional idempotent import, acceptance and separate auditable retention; exercise temporary database fixtures and write recovery/runbook.
- [x] Acceptance: implement `scripts/provider_acceptance.py` with configuration-only, offline fixtures and explicitly bounded live modes; record capability, source, SHA, versions, freshness, reason and check time without secrets/payloads. Reuse local artifact helpers and production smoke.
- [x] Operations: extend `config/hosted-environment-manifest.json`; validate exact versions, release SHA and capability prerequisites; distinguish hosted `configuration_required` before requests and validate frontend/backend identities; preserve passive provider health.
- [x] P2: verify TDX/RIS freshness metadata, NLSC independent capability contracts and satellite failure isolation; document durable persistence/scheduling external work where scope would expand.
- [x] Regression: run full Python suite, focused frontend unit suites, deterministic E3–E10 Chromium/installed Chrome/mobile acceptance, lint/typecheck/build, production audit and repository release/security/operations gates.
- [x] Fresh review: inspect final diff for all user-listed failure semantics and privacy/isolation problems; fix all Critical/Important findings and rerun affected checks.
- [x] Finalize `docs/operations/production-provider-closure-v1.md` with every capability scorecard, exact evidence, external steps and live request count. If all local gates pass, create exactly one `fix: close production provider integration gaps` commit and stop.
