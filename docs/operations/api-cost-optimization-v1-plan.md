# API cost optimization v1 implementation plan

Goal: reduce proven duplicate provider work while preserving evidence, failure,
freshness and property identity contracts from the supplied implementation brief.
Starting SHA: a27bbdead6e3f4196426a6016a20ddff6f86f1f1.
Branch: perf/api-cost-optimization-v1 (existing isolated linked worktree).

No push, merge, deploy, live provider measurement, infrastructure, migrations,
ML, anti-abuse or UI redesign. Exactly one commit only after all gates pass.

## Tasks and verification

- [x] Record mocked baseline at actual adapter/service boundaries before changes.
- [x] Implement and test shared synchronous `BoundedRequestCache.run(key,
  operation, cacheable=..., size_of=...)`: TTL, LRU entry/byte bounds, single-flight,
  independent keys, copied results and failure cleanup. Fixed-label cost metrics
  distinguish logical operations, actual physical calls and reuse events.
- [x] Google: bound category/route caches, suppress duplicate categories and
  coalesce full fan-out plus identical geocoding; preserve field-mask fields
  consumed by UI, address acceptance, partial categories and route query inputs.
- [x] Satellite: explicit action, synchronous submit guard and stale-property
  isolation; cache complete embedded imagery with strict byte/entry bounds and
  full dataset/window/configuration identity; coalesce concurrent generation.
- [x] Terrain: prove repeated tile retrieval/decode and point/layer calls;
  reuse bounded successful results with complete configuration/version/admin
  identities; document local artifact and secondary snapshot dispositions.
- [x] Integrate mocked representative journey and Satellite/Places/Routes call
  budgets; verify reopen/Compare/Report create zero analysis provider calls.
- [x] Run full Python suite, frontend unit/browser commercial regressions,
  Chromium/Chrome/390px, lint/typecheck/build, audits and three release gates.
- [x] Independent trust/resource/privacy review; fix Critical/Important findings.
- [x] Write bounded implementation report and commit once if every gate passes.

Review focus: exact property identity despite coordinate proximity; expiry and
configuration change; failed coalesced owner cleanup; partial/no-match versus
success; stale UI responses on switch/reopen; cache memory and private telemetry.

Execution decisions: user supplied implementation scope authorizes execution;
additional design approval and intermediate commits from skill defaults conflict
with the requested autonomous implementation and exactly-one-commit contract.
Parallel workers own separate Google, Satellite/frontend and terrain file groups;
coordinator owns shared cache/metrics, integration, report and final verification.
