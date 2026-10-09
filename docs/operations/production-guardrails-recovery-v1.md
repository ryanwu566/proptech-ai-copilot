# Production guardrails and recovery v1

Date: 2026-10-09 (Asia/Taipei). Starting SHA:
`b4eb441a8ccf90965102f0646006dc4b0e145491`.
Branch: `ops/production-guardrails-recovery-v1`. Scope: current worktree only.
Production decision remains **NO-GO**. No push, merge, deployment, cloud
billing/DNS/WAF changes, credential rotation or production restore/load test.

## Architecture and existing controls

The Next/Vercel browser client calls a configured backend origin directly.
The deployment documents name Render as the intended backend. `render.yaml`
and the alternative `Dockerfile.cloudrun` are repository entry points; the
actual deployed ingress/edge topology is unverified.
Both disable Uvicorn forwarding-header trust. FastAPI calls PostgreSQL
datastores, local/versioned datasets, Google Geocoding/Places/Routes, optional
Earth Engine, R2-backed official artifacts, TDX, TGOS and NLSC gateway
providers. Google browser Maps/Street View are separate browser consumers.
There is no proven Vercel-to-backend-only transport or direct-origin exclusion.

Existing endpoint admission, concurrency semaphores, attempted-operation
budgets, body/query/deadline bounds, provider-specific limits, caches,
coalescing, capability kill switches, 429/503/Retry-After and bounded provider
metrics remain intact. Public status is passive; protected metrics and
administrative/refresh routes retain their existing authorization. Existing
SQLite backup/restore drills are explicitly local and never proved hosted
PostgreSQL durability. Existing migration registry and release evidence are
reused rather than replaced.

## Threat and cost model

Anonymous direct backend calls, forged forwarding headers/Origin/Host,
distributed retries, revision overlap/restarts, provider errors and expensive
uncached fan-outs can multiply cost. CORS and host allowlists restrict browser
admission but do not authenticate machines or establish network origin
protection. A shared ingress peer can aggregate legitimate clients into one
coarse rate bucket. Local operation counts are units, not currency/EECU.
Browser keys, scripts, background refresh and other projects/credential
consumers require account-level inventory. Provider quotas and alert-only
budgets do not automatically create a strict global monetary ceiling.
Backup corruption, missing offsite access, live-ledger drift and unavailable
retained releases/artifacts can prevent recovery even when local tests pass.

## Added repository controls

- Production/preview/serverless startup requires 1–16 exact
  `API_ALLOWED_HOSTS`. Unsupported distributed modes fail startup; only
  `local_only` is implemented. Production overrides cannot raise current
  request/operation/concurrency ceilings or shorten their windows.
- ASGI ingress admission rejects invalid/duplicate/unapproved Host and Origin
  before routes, hides production docs/OpenAPI, preserves transport-peer
  identity and keeps rejection metrics/security headers/CORS integration.
  Origin parsing now handles malformed IPv6/ports without an exception.
- A `SharedAdmission` protocol specifies atomic coordination and fail-503;
  there is deliberately no unreviewed shared adapter. Existing PostgreSQL
  lacks a reviewed limiter schema, role and atomic concurrency tests.
- Existing metrics gain an unlabelled dedicated 503 counter; no new high
  cardinality labels or monitoring platform.
- Release evidence gains `production_guardrails`, a 15-control release-bound
  evidence extension. The bounded contract/schema and owner template make
  missing evidence BLOCKED, malformed/stale/wrong-release PASS proof FAIL,
  and prevent required-control waiver. The operations gate validates this
  repository contract separately from production acceptance.
- Offline read-only Cloud Run export checks verify ingress/default-URL
  annotations and exact proxy flags without printing export values. WAF and
  direct-origin exclusion remain BLOCKED pending independent proof.
- PostgreSQL custom-dump integrity metadata and an opt-in isolated recovery
  rehearsal cover managed migrations, synthetic rows/constraints/ledger,
  sequence and RLS inventory; no hosted URL/external dump accepted. CI adds
  the same disposable drill. Dump extensions are ignored by Git.
- Read-only rollback compatibility checks require full commit SHAs, actual
  Git objects, migration file digests, API contract equality and nonempty
  equal artifact manifests. No down migration or traffic mutation.

## Acceptance and owner actions

| Area | Repository result | External acceptance |
| --- | --- | --- |
| Trusted ingress | host/origin/forwarding contract implemented and tested | BLOCKED: actual topology and all backend bypass paths |
| Cross-instance enforcement | fail-closed mode/interface; local protections retained | BLOCKED: atomic shared control implementation/infrastructure |
| Edge/WAF | exact route/body/rate requirements; offline export inspection | BLOCKED: attached effective rules, bot controls, bypass and emergency drill |
| Provider quotas | critical local overrides bounded at startup; account expectations | BLOCKED: Google server/browser quotas, GEE effective quotas and other metered inventory |
| Billing/global cost | explicit independent alert/cap states | BLOCKED: recipients/delivery, enforceable service coverage and overshoot model |
| Kill switch | existing process switches preserved; safe local regressions | BLOCKED: rollout/recovery across actual active revisions |
| Monitoring | bounded HTTP/provider signals including dedicated 503 | BLOCKED: fleet collection, status checks and delivered alerts |
| Backup | integrity metadata and real local PostgreSQL dump | BLOCKED: production coverage/retention/offsite/encryption/access |
| Restore | synthetic disposable PostgreSQL PASS | BLOCKED: production-origin staging restore, roles/ACLs, real scale and RPO/RTO |
| Rollback | immutable compatibility dry-run | BLOCKED: actual hosted releases, applied ledger and staging traffic drill |
| Incident escalation | concise thresholds/decisions/recovery runbook | BLOCKED: named primary/backup, authority and paging receipt |

See [owner runbook](production-guardrails-recovery-v1-runbook.md) for exact
requirements, safe commands, quota limitations, backup/restore procedures and
independent frontend/backend/schema/artifact rollback decisions. All 15
external controls in the committed evidence start BLOCKED; no external
owner action is marked complete. Full production acceptance includes unrelated
blockers and remains NO_GO regardless of repository contract tests.

## Original implementation verification record

Focused new/existing regression run: 42 passed (one upstream Starlette
deprecation warning). The isolated PostgreSQL 16 drill passed 15 managed
migrations, custom dump/hash/list verification, transactional restore,
synthetic rows/ledger/sequence/RLS/constraint inventory and actual FK/check
rejection. Cleanup passed; production connections: zero. Constraint SQL text
is not a semantic checksum because PostgreSQL flattens equivalent conjunctions
on restore; validation uses inventories and actual rejection behavior.
Production role/ACL restore is not tested, and no production-data RTO is claimed.

Final full Python suite: **3407 passed, 32 skipped, 1 warning**
in 404.23 seconds (`python -m pytest -q`). Existing opt-in PostgreSQL
integration tests skipped without their dedicated disposable URL contracts;
the new isolated PostgreSQL dump/restore drill ran separately and passed.
The first full run had one rollback regression failure while review fixes
were underway (3,402 passed, 32 skipped); corrected focused tests passed,
then the final stable full suite above passed. No limits were weakened.

Post-review focused run: **44 passed**. Existing anti-abuse regressions cover
429, provider budget exhaustion, kill switches and recovery with fake clocks
and local transports; the real ASGI bounded load (`--loops 2`) passed ordinary
and overload stages. Its deterministic streamed-body probe rejected four
requests with 503/Retry-After, kept health available and admitted all sixteen
requests after recovery. No production/provider load was executed.

Passed: optimized frontend build (including TypeScript), release-quality
contract gate, security/performance gate, production-operations gate,
route/bundle budgets, provider-free production smoke, evidence JSON Schema,
Python compile checks, repository hygiene and diff check. Route/bundle
measurement: 2,997,356 total static bytes and 608,747 largest JS bytes. No
frontend source was changed, so frontend lint/browser suites were not rerun.
The npm audit gate passed with the existing unchanged development-only
`GHSA-vfj7-8cjw-p6xm` exception, expiring 2026-11-04. This is not a
zero-advisory claim; no dependency policy was relaxed or package upgraded.

Immutable local rollback PASS: current frontend/backend
`b4eb441a8ccf90965102f0646006dc4b0e145491`, candidate pair
`9d680023618538ba6815ed3f217a1f9ea33bb565`, identical frontend consumer trees,
runtime/API manifest agreement, historical registry/inventory/checksum
agreement and a synthetic retained-artifact manifest. A changed frontend tree
remains BLOCKED without separate compatibility evidence. No hosted traffic
switch, live applied-ledger verification or real artifact restoration occurred.

Independent read-only review: zero Critical findings; one Important rollback
compatibility finding and one Minor hard-link metadata overwrite finding were
fixed and independently reverified. Additional reasonable safety expectations
were addressed: local Docker socket pinning, ownership-bound cleanup after a
creation timeout, full historical migration registry/inventory validation and
malformed evidence state/NaN rejection. Final reviewer reports no remaining
Critical or Important findings. Cloud state, proof authenticity, hosted rollback
and production-origin recovery remain external owner responsibilities.

The [bounded validation JSON](production-guardrails-recovery-v1-validation.json)
records these results. CI execution is not claimed: its recovery job is added
but no remote workflow was triggered. Before any future deployment the owner
must supply the new exact host allowlist; absent or excessive critical settings
fail startup by design. Safe for PR review: **yes**; production GO: **NO**.
The final commit identity is reported in the final handoff (it cannot be
embedded in its own committed content).

## Original implementation changed-file inventory

36 changed files, including this report and bounded local evidence.

- `.github/workflows/production-release-ops.yml`
- `.gitignore`
- `backend/api/ingress_middleware.py`
- `backend/api_main.py`
- `docs/backup-restore.md`
- `docs/deployment-production.md`
- `docs/environment-matrix.md`
- `docs/hosted-rollback-runbook.md`
- `docs/operations/production-guardrails-contract-v1.json`
- `docs/operations/production-guardrails-evidence-v1.schema.json`
- `docs/operations/production-guardrails-owner-template-v1.json`
- `docs/operations/production-guardrails-recovery-v1-evidence.json`
- `docs/operations/production-guardrails-recovery-v1-local-restore.json`
- `docs/operations/production-guardrails-recovery-v1-local-rollback.json`
- `docs/operations/production-guardrails-recovery-v1-plan.md`
- `docs/operations/production-guardrails-recovery-v1-runbook.md`
- `docs/operations/production-guardrails-recovery-v1-validation.json`
- `docs/operations/production-guardrails-recovery-v1.md`
- `docs/production-backend-deployment-v1.md`
- `docs/production_acceptance_checklist.md`
- `render.yaml`
- `scripts/backup_integrity.py`
- `scripts/generate_release_evidence.py`
- `scripts/migration_registry.py`
- `scripts/postgres_recovery_drill.py`
- `scripts/production_ops_gate.py`
- `scripts/verify_cloud_run_guardrails.py`
- `scripts/verify_rollback.py`
- `services/guardrail_evidence.py`
- `services/metrics.py`
- `services/production_guardrails.py`
- `services/security.py`
- `tests/test_commute_route_api.py`
- `tests/test_guardrail_recovery.py`
- `tests/test_production_guardrails.py`
- `tests/test_production_readiness.py`

## Post-integration validation

Original implementation baseline: `b4eb441a8ccf90965102f0646006dc4b0e145491`. Original completed
feature: `f0baa31af02c93908c2b27719470b75413c88b77`. Integration baseline:
`602830c8d4d405bb401afa902d5bf69f2c61066f`. The original verification and 36-file inventory
above remain historical records; they have not been relabelled as integration
results. Backup branch `backup/production-guardrails-recovery-pre-integration`
retains the original completed feature commit. Fetch verified the required
origin/main identity before reset; the clean feature branch was reset to that
base and the original Lane E commit cherry-picked.
PR #170's committed acceptance/evidence snapshots remain unchanged historical
records; integration does not relabel their earlier validation or owner state.

One file conflicted: `scripts/generate_release_evidence.py`. Resolution keeps
PR #170's `date` import, acceptance observations, pinned frontend/backend
SHA/version checks, exact source metadata and owner evidence checks alongside
Lane E's `sys` import and bounded proof reader. Both existing CLI modes accept
`--guardrail-owner-records` and `--proof-root`; both expose the same nested
`production-guardrails-v1` schema. Acceptance's original scorecard remains
intact, with NO-GO enforced when any required guardrail proof is missing or
invalid. The original 64,000-byte acceptance cap remains; duplicate JSON keys
and nonstandard numbers are rejected, and invalid input yields a bounded
category without printing private input. No second acceptance framework was
added. Future v2 can consume this same extension. Proof hashes validate an
offline archive and owner assertions, not live cloud authenticity.

Post-integration focused security/operations/anti-abuse/recovery/hosted launch/
acceptance/provider regressions: **195 passed, 1 warning**. Seven new acceptance
regressions prove that a complete categorical scorecard cannot bypass missing
guardrail proof, the combined CLI consumes submitted proof, malformed JSON
fails without output, valid synthetic archives retain GO/CONDITIONAL GO
semantics, and altered archive bytes force NO-GO. Synthetic test PASS values
are not production evidence.

Final full Python suite: **3459 passed, 32 skipped, 1 warning**
in 258.45 seconds (`python -m pytest -q`). Skips remain the opt-in PostgreSQL
integration contracts. The first integrated full run recorded
1 failure, 3458 passed and 32 skipped:
the existing Earth Engine cancellation-race test failed during worker startup
(unavailable before the cancellation scenario), while a fresh frontend build
was also running. All 26 unchanged worker-pool tests then passed
independently; the complete suite above passed after the build finished.
Resource contention is a possible contributor, not an established root cause.
No source fix, assertion, timeout or budget change was needed for that result.

Passed: release-quality contract, security/performance, operations, provider-free
local smoke, both generated guardrail extension shapes against the shared
JSON Schema, Python compile checks, repository hygiene and diff check. The
release-quality command skipped duplicate Python/build runs because both were
executed independently. Frontend source is unchanged against the integration
base; additional validation nevertheless passed 65 deterministic checks plus
the workspace contract, typecheck, lint (0 errors, 23 existing warnings), a fresh
production build, npm audit gate and route/bundle budgets. Browser suites were
not rerun. Static bytes: 2,997,577; largest JS chunk:
608,747. The unchanged development-only npm
exception `GHSA-vfj7-8cjw-p6xm` expires 2026-11-04; this is not a zero-advisory
claim. No dependency policy, security threshold or performance budget changed.

The real disposable PostgreSQL 16 restore was rerun: **PASS**, all **15 managed
migrations**, custom dump integrity/list, transactional restore, synthetic rows,
ledger, sequence, RLS/constraint inventory and FK/check rejection. Owned cleanup
passed, production connections were zero, and the synthetic restore took
4.55 seconds. Production backup/restore remain BLOCKED;
production roles/ACLs remain NOT_TESTED. Local immutable rollback compatibility
also passed: frontend/backend `fb0b78c5754c1c13dcabc28a7cf1c3c80051f7fc` against
candidate pair `602830c8d4d405bb401afa902d5bf69f2c61066f`, with equal frontend trees,
verified API metadata/migration checksums and an explicitly synthetic retained
artifact map. Hosted traffic, applied production ledger and real retained
artifacts were not verified. The documented current SHA is the reviewed code
commit before the documentation-only amendment; final commit identity is
reported in the handoff. Local bounded load passed: four controlled streamed-
body 503 rejections with Retry-After and sixteen successful recovery admissions.

Independent read-only review found **0 Critical, 0 Important, 0 remaining Minor**
issues. It confirmed that #170's validation body was preserved, both generator
modes share the extension, all owner controls require proof, forwarding headers
remain untrusted, metrics remain bounded, and restore/rollback retain their
production boundaries. Checklist/runbook text was reconciled to distinguish the
standalone extension's NO_GO/UNKNOWN scope from the parent acceptance verdict.

Integration inventory: **37 changed files** against origin/main; the additional
file beyond the historical inventory is `tests/test_final_production_acceptance.py`.
Exactly one final Lane E commit is retained by amending only the integrated
feature commit; required topology is `0 1`. All 15 external controls remain
BLOCKED, unrelated production proof remains outstanding, and production GO is
**NO**. No push, merge, deployment, cloud write, hosted test or remote CI run was
performed. Before any future rollout the owner must supply `API_ALLOWED_HOSTS`
and independently verify deployed ingress, fleet enforcement, edge rules,
provider-account quotas/cost protection, delivered alerts, recovery/rollback
and incident authority. Bounded post-integration results are in the validation
JSON's `post_integration` object; original results remain unchanged.

## Latest-main integration and migration investigation (2026-10-10 Asia/Taipei)

This section records the latest integration; all preceding implementation and
first-integration results remain historical. No push, merge, deployment,
production connection, cloud write or hosted provider probe was performed.

| Identity | SHA |
| --- | --- |
| Original implementation baseline | `b4eb441a8ccf90965102f0646006dc4b0e145491` |
| First integration baseline | `602830c8d4d405bb401afa902d5bf69f2c61066f` |
| Latest integration baseline | `8469c1f22b64a0e03be03a0099c59a8483d9e0c8` |
| Original Lane E commit | `f0baa31af02c93908c2b27719470b75413c88b77` |
| Previous integrated commit | `726b66c8a74c6ddc868ebc51c647bbfc1996da82` |
| Final latest-main integrated commit | Resolve `git rev-parse ops/production-guardrails-recovery-v1`; the actual final SHA is recorded after amendment in the handoff and `.local/latest-main-integration/final-handoff.json`. A commit cannot embed its own SHA. |

Fetch verified the required main SHA and clean feature worktree. The backup
branch `backup/production-guardrails-recovery-pre-latest-main` points exactly
at the previous integrated commit. The already isolated worktree was reset to
the required main and that feature commit cherry-picked. One file conflicted:
`scripts/generate_release_evidence.py`. Resolution combines #170's complete
acceptance validation, #172's closure projection and Lane E's required bounded
guardrail archive through the existing shared `build_evidence`/CLI path.
All three CLI inputs can be supplied together. A valid synthetic guardrail
archive plus a complete scorecard still yields NO-GO for blocked/forged closure.
Both generated extension shapes pass the existing JSON Schema. No second
production-acceptance framework was introduced.

### Migration failure evidence and classification

The original [GitHub migration job](https://github.com/ryanwu566/proptech-ai-copilot/actions/runs/37955394478/job/113904493407)
validated all 15 managed migrations inside a rollback transaction and passed
its three migration/backup contract tests. It failed only at the subsequent
disposable recovery drill's `database_ready` stage, with cleanup PASS and zero
production connections. The historical checkout was the PR merge against
`602830c8d4d405bb401afa902d5bf69f2c61066f`, not a conflicted checkout. None of the managed migrations, registry,
production runner, rollback validator, disposable Auth bootstrap or operations
workflow changed between that baseline and the latest main.

The unmodified drill passed locally on Windows and Linux, including the exact
CI image digest `sha256:ca0bd484cb98bf4b24eb1010e73fb3fcbd6714d240fbc1a10eea5b7dbecb641d`.
Thirty unmodified Linux startup repetitions also passed. Consequently this
report does **not** claim to have reproduced the exact historical exception,
or classify it as transient infrastructure or a stale-base migration regression.
The original log retains a stage/category, not the underlying Docker/SQL error;
the exact historical cause remains unproven. Fresh GitHub CI is required to
validate the final branch and cannot recover the lost historical exception.

A real official-image characterization, holding its normal initialization
phase open with a synthetic `pg_sleep(6)` init script, demonstrated a confirmed
**E: readiness/test contract defect**: Unix-socket `pg_isready` returned ready
while `listen_addresses` was empty and TCP readiness returned not-ready. The
official entrypoint then stops this temporary server and starts the final
server. The old drill could advance during that initialization/shutdown window.
This mechanism is consistent with the historical stage and short failure
duration, but that consistency is an inference, not proof of that exact event.

The fix selects `127.0.0.1` TCP for readiness and validation SQL inside the
same network-disabled, port-unpublished owned container. Thirty attempts,
0.5-second intervals and existing subprocess timeouts are unchanged. A
deterministic temporary-server regression failed before this fix and passed
after it; an unready-server test proves bounded rejection/cleanup. The
corrected Linux restore passed with the exact historical CI image: all 15
managed migrations, custom dump/list/digest, transactional restore, exact
synthetic row/ledger/sequence/RLS/constraint inventory and actual FK/check
rejection; restore time 1.117 seconds, cleanup PASS, production connections 0.
Production data, roles/ACL restore and production-scale RPO/RTO remain unverified.

The expanded opt-in database run exposed two separate stale fixture contracts:
the production rehearsal still assumed 14 migrations/no 019, and Stage 1
acceptance fixtures installed Stage 2 migration 018 even though that operator
deliberately refuses the later catalog. The rehearsal now derives counts and
exact ledger digests/schema versions from the unchanged authoritative registry,
requires the RIS table and tests checksum-drift refusal. Only Stage 1 operator
fixtures use the through-017 catalog; all other RLS fixtures still include 018.
No production operator, migration SQL, ordering, assertion or gate was weakened.
The first expanded harness also omitted the separate `market_e2e` database;
that local setup error was corrected without changing market source/tests.

### Final validation and CI parity

Authoritative inventory: **20 registry entries, 15 managed production-runner
migrations**, terminal `schema-019`, next sequence `020`; intentional legacy/
operator registrations remain distinct. The exact rollback validator command
ran twice on a fresh disposable PostgreSQL 16 database, with emptiness verified
after each rollback. The production runner exercised fresh apply, prefix upgrade,
repeat, exact ledger/catalog/RLS checks and checksum-drift rejection. The
expanded PostgreSQL suite passed **32 tests, zero skipped**, with owned cleanup.

Full Linux Python 3.12.14 / repository-pinned Node 24.21.0 suite: **3567 passed,
33 skipped, 155 warnings**, 275.2 seconds. The first Windows full run had 2
worker-replacement failures, 3566 passes and 32 skips while other validation was
running. The unchanged worker-pool file passed all 26 tests separately.

The Windows full rerun without concurrent heavy checks still had 4 failures,
3564 passes and 32 skips. These results do not establish concurrent-check
contention as the sole explanation; the Windows verification gap remains
unresolved, and no same-environment main control was run to establish whether it
predates this integration. No worker source, assertion, test or timeout was
changed.

The default suite retains its environment/safety skips. Linux's one additional
skip is the optional formal ML JSON Schema check because jsonschema is absent
from backend workflow requirements; that exact test separately passed with
jsonschema installed, with zero skipped. The separate disposable database run
exercised 32 real PostgreSQL tests with zero skipped. Final focused
identity/provider/guardrail/recovery/hosted/ML regression run: **464 passed**.

Focused commands/results and final bounded evidence are recorded in the
validation JSON's `latest_main_integration` object. Production identity,
artifact/provider/runtime closure, hosted acceptance, ingress, rate/anti-abuse,
cost, backup/restore/rollback, operations and ML regressions pass. ML and frontend
source/evidence are unchanged against latest main: Target A/B remain BLOCKED,
PIT-valid and approved training cohort remain 0, and ML-B MAY NOT BEGIN.

Frontend typecheck, 30 deterministic checks plus the workspace contract,
production build, `npm ls --all`, production npm audit and the existing audit
gate passed. Lint: 0 errors, 23 existing warnings. Production npm findings: 0;
the unchanged development-only `GHSA-vfj7-8cjw-p6xm` exception expires 2026-11-04.
Static total: **2,998,938 bytes**, largest client JS **597,008 bytes**; the
**3,000,000-byte** ceiling remains unchanged. Browser tour suites were not rerun
because frontend source is unchanged, as explicitly allowed by this integration
request. Release-quality, security/performance, production operations, route/
bundle budgets, provider-free local smoke, strict Python dependency audit,
SBOM generation, compile checks, hygiene and whitespace checks passed.
The release-quality command skipped duplicate Python/build execution because
the complete Linux Python command and local production build ran separately. Bounded local load passed with four
controlled 503/Retry-After rejections and sixteen successful recovery admissions.

CI parity commands:

| Command | Environment/dependencies | Result and parity |
| --- | --- | --- |
| `python scripts/validate_postgres_migration.py --database-url postgresql://postgres@127.0.0.1:<owned-port>/proptech_test` | Python 3.12.13, backend requirements, owned PostgreSQL 16 service, trust auth and fresh proptech_test | PASS twice with rollback/empty catalog; identical repository semantics, loopback ephemeral port replaces Windows-reserved 5432 |
| `python -m pytest -q tests/test_production_postgres_ops.py` plus migration/RLS/RIS/market E2E files | Same backend requirements and pytest >=8,<9; explicit disposable URL/name/confirmation contracts | 32 PASS, zero skipped; includes workflow contract tests and real migration E2E |
| `python scripts/postgres_recovery_drill.py --execute-disposable --local-image postgres@sha256:ca0bd484cb98bf4b24eb1010e73fb3fcbd6714d240fbc1a10eea5b7dbecb641d --output /tmp/postgres-recovery-drill.json` | Disposable Linux helper, Python 3.12, Docker 28 CLI, same exact CI PostgreSQL digest, shallow source snapshot plus reviewed TCP fix | PASS, 15 managed migrations, no published ports/network, owned cleanup; same recovery command/contract, image explicitly pinned to historical CI bytes |
| `python -m pytest -q --basetemp /tmp/production-release-pytest` | Owned Debian 13.7 Linux helper, Python 3.12.14, Node 24.21.0, backend requirements and pytest >=8,<9, exact reviewed source and portable TypeScript dependency | Full suite PASS; GitHub uses ubuntu-latest and historical Python 3.12.15, so distro/patch parity is disclosed |
| `npm --prefix frontend_next run build`; release/operations/security/smoke/audit/budget/hygiene commands | Windows Python 3.12.13, Node 24.14.1 vs repository CI pin 24.21.0 | Local gates/build PASS; full Windows Python suite FAIL remains separately disclosed; GitHub has not rerun |

The recovery Linux helper read only the disposable checkout and local Docker socket;
the recovery container itself has no mounts, published ports or external network.
The full-suite helper copied the exact reviewed source snapshot and shallow Git
metadata into its own ephemeral filesystem, used Python 3.12.14 and Node
24.21.0, and reused the portable TypeScript package from the completed Windows
`npm ci`. Its archive input was read-only and its network disabled.
No workflow timeout/dependency/security/release/migration gate was removed,
skipped or relaxed. GitHub CI on the final commit is still required.

Immutable offline rollback passed against the latest-main candidate using
actual full Git frontend/backend SHAs, equal frontend trees, exact migration
inventory/checksums and API metadata, and an explicitly synthetic retained
artifact map. This is not hosted traffic, production-ledger or real artifact
restoration proof. The final handoff records a rerun against the amended SHA.

### Independent review and remaining owner work

Independent read-only whole-branch review (including working-tree fixes):
**0 Critical, 0 Important, 0 actionable Minor findings**. It confirmed preserved
#170 checks, #172 supplied closure veto, all required guardrail proof, bounded
metrics, local/production recovery boundaries, immutable rollback, unchanged
workflow gates/ML/frontend/bundle ceiling, and exact migration evidence.
The historical failure's unresolved exact exception is explicitly retained.

All 15 external guardrail controls remain BLOCKED. Owners must supply actual
deployed frontend/backend build identities, production configuration, active
artifact/provider acceptance and runtime dependency evidence; exact allowed
backend hosts and ingress/bypass proof; fleet-wide atomic admission; deployed
edge/WAF rules; all provider-account quotas and effective global cost controls;
delivered monitoring/billing alerts; production backup retention/offsite/access,
staging restore/RPO/RTO and immutable hosted rollback; incident authority and
primary/backup paging receipt. Local tests do not close these controls.

Final inventory: **40 files** changed against the latest integration baseline.
Only the feature commit is amended; topology must be `0 1` and the worktree
clean. Safe to update PR #173 with a lease after this local verification; PR
merge remains conditional on all required GitHub checks for the actual final
head/merge result passing and normal review/branch rules. Production GO: **NO**.
