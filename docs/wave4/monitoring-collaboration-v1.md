# Monitoring, collaboration and cross-device foundation v1

Wave 4 is implemented against current-main Auth and browser Saved Case contracts.
No database migration, migration registry change, hosted write, push or deployment
is part of this branch.

## Available foundation

- `/cases` distinguishes browser-local cases from account Cloud snapshots. Local
  cases are never uploaded by mounting, login/session restore, reconnect or status
  rendering. Preview and confirmation are required for each selected case.
- Upload preserves the original snapshot JSON and separate Decision Room document,
  including notes, timestamps, provenance and failed/unknown provider state. It
  bypasses historical evidence normalizers. Original local bytes remain on success
  and every failure. A changed local case/notes requires another preview.
- Personal `/v1/saved-cases` contracts cover create, owned/shared lists, open,
  title/notes updates, owner-managed memberships/preferences and activity pages.
  Owner identity comes from existing verified Auth UUID and active account status.
  Workspace roles do not confer personal case access. Collaboration is private
  account access, without public links or email invitations.
- A transactional repository seam enforces import idempotency, immutable history,
  expected-revision updates, ACL boundaries and atomic activity. Production wiring
  always reports `persistence_pending` until a real adapter is installed. The
  memory adapter is test-only; it is never a runtime fallback.
- Cloud reopening shows historical evidence/source states and original viewing
  notes without provider calls or writing a Cloud copy to browser storage. Sync
  status describes the last explicit read, with a revision and timestamp.
- Conflicts preserve drafts and require reading the latest version before retry.
  Unrelated collaboration/monitoring saves preserve metadata drafts. Offline
  disables account operations; reconnect does not retry. Account changes clear
  Cloud state and discard late requests/responses and preview hashes.
- Credentials are rejected throughout persisted imports, import keys and editable
  metadata; evidence is rejected as a whole instead of silently stripped. No new
  credential, Cloud cache, pending upload queue or sync marker is persisted locally.
  Existing Auth SDK session storage remains in its existing boundary.
- Pure monitoring contracts distinguish source content changes from render/check
  timestamps, initial baselines and unknown/failed observations. Cached-check plans
  are disabled without a worker, deduplicated and capped by batch size and quota.
  Notification event/delivery contracts contain references only and send nothing.

## Deliberately pending

Real cross-device persistence requires the future migration and PostgreSQL adapter,
with direct SQL RLS/grant tests and concurrent connection conformance tests. The
current service tests establish application contracts, not deployed RLS behavior.
Scheduled execution requires a real worker, claims/leases, cadence enforcement and
quota integration. Email/SMS require a configured provider and channel consent.
Saving monitoring preferences never claims those systems are active.

See [the persistence schema proposal](wave4-persistence-schema-proposal.md) for
tables, RLS, grants, indexes, atomic adapter requirements and migration sequencing.
Suggested 023 applies only if 022 is the highest merged migration after rebase.

## Verification commands

From repository root:

```powershell
python -m pytest tests/test_durable_cases.py tests/test_durable_cases_api.py tests/test_case_monitoring.py -q
python -m pytest tests/test_durable_cases.py tests/test_durable_cases_api.py tests/test_case_monitoring.py tests/test_vnext_auth_api.py tests/test_vnext_authorization.py tests/test_consumer_account.py tests/test_authenticated_identity_smoke.py -q
git diff --exit-code HEAD -- database/migrations database/migration_registry.json
```

From `frontend_next`:

```powershell
npm ci --no-audit --no-fund
npm run test:wave4
node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --test scripts/consumer-auth.test.mjs scripts/consumer-auth-race.test.mjs scripts/account-client.test.mjs lib/workspace/*.test.ts lib/decision-room-store.test.ts
npm run typecheck
npm run lint
npm run test:e2e:wave4
npm run build
```

Browser coverage includes explicit/raw import, failed upload retention, local
changes before confirmation, pending preview selection changes, second-device
reopening without providers/local writes, conflict drafts, unrelated settings
saves, malformed historical notes, owner/member boundaries, mobile/offline state,
unsigned upload rejection and logout while a Cloud response is pending.

## Initial verification results (2026-10-16, before integration)

- Final Wave 4 Python suite: 34 passed. The expanded Auth/account/authorization
  regression run also passed (131 tests at that stage).
- Existing frontend Auth/account/workspace/Decision Room regressions: 214 passed.
  Final focused contract/client/Decision Room run: 28 passed, including 17 new
  Cloud contract/client tests.
- Chromium Wave 4 and existing Saved Case routing: 16 passed with zero retries.
  Existing account login/restore/logout and the strengthened pending-response
  logout scenario: 2 passed, including one scenario repeated from that run.
- E2E production build, default production build and standalone TypeScript check
  passed. The standalone check reused the build cache with
  `npm run typecheck -- --declarationMap false --emitDeclarationOnly false --tsBuildInfoFile .next/cache/.tsbuildinfo`;
  no source checks were excluded.
- ESLint passed with zero errors and 23 existing warnings. Migration paths and
  the migration registry are unchanged.

Local verification encountered dependency unpacking and server startup stalls on
the memory-constrained shared Windows host. `npm ci` did not complete; dependencies
were copied from a locally installed worktree with an identical package-lock hash
into this worktree's own ordinary `node_modules` directory. The final two account
browser checks used the existing owned-server runner with only its readiness wait
extended from 60 to 180 seconds; assertions, server identity and cleanup checks
were unchanged. Neither workaround changes committed application code.

Database RLS execution, real concurrent SQL transactions, scheduled jobs and
notification delivery remain unverified until their future infrastructure exists.

## Final integration closure

- Starting branch: `feat/monitoring-collaboration-v1`, clean worktree at
  `4423f5dce4a0b23dbb7f9c8da698e982b392b946`.
- Preserved ref: `backup/wave4-4423f5d-before-integration` points to that original
  commit. Integration target, fetched and verified:
  `194d17ce721fac5fa878db3c16c1c9233348bae5` (`origin/main`).
- Original base: `59631992e03c05ff01e67fb691710c738fcc6d1b`. Main added
  `e6e3d344d3cafaa9906c6f4030abd7027f71e7aa` and its merge `194d17c`.
  Their nine changed paths concern usage database bootstrap, security audits,
  tests and operations documentation. None overlaps Wave 4's 21 changed paths.
- Rebase completed without conflicts; `git range-diff` showed an identical Wave 4
  patch before closure review. Current-main Auth, account authorization, browser
  sessions and dependency lockfile are unchanged from the original base. The
  hardened quota runtime is preserved, with no provider admission bypass or
  activation in Wave 4. Saved-case routes remain outside the existing provider
  capability allowlist; no new quota enforcement is claimed for this surface.
- Read-only security review identified a stale sharing-form recipient/role when
  switching Cloud cases. A browser regression reproduced the failure. The narrow
  closure fix resets recipient and default viewer role on case/account changes,
  retaining same-case form selections and unrelated authored drafts. No new
  feature, persistence adapter, scheduler or delivery path was added.
- Migration paths/registry remain byte-identical to main, ending at 021. Wave 4
  migration ownership remains deferred until Wave 1C settles the sequence; 023 in
  the proposal remains conditional, never reserved or registered.

Fresh closure checks on the integrated source:

| Check | Result |
| --- | --- |
| Backend Auth/account/authorization/identity smoke | 101 passed |
| Wave 4 backend | 34 passed |
| Frontend Auth/account/race regressions | 25 passed |
| Saved Case/workspace/Decision Room/roundtrip/save-feedback regressions | 255 passed |
| Wave 4 frontend contract/client | 17 passed |
| Saved Case static + quota + bootstrap unit regressions | 41 passed; 56 database-dependent tests deselected |
| Chromium: 13 Wave 4 + 4 existing case routing + 1 account login/restore/logout | 18 passed, zero retries |
| Final E2E production build | passed |
| Standalone `npm run typecheck` | passed |
| ESLint | passed, zero errors and 23 existing warnings |
| Default `npm run build` | passed |

The final browser run used the unchanged owned-server runner, one worker,
90-second test timeout, and zero retries:

```powershell
node e2e/run-e2e.cjs e2e/monitoring-collaboration.spec.ts e2e/commercial-workspace-routing.spec.ts e2e/consumer-account.spec.ts '--grep=monitoring-collaboration|commercial-workspace-routing|login,.*restore' --project=chromium --workers=1 --timeout=90000 --retries=0
```

Read-only security review and the rerun cover explicit consent/no automatic
upload, local/evidence preservation, cross-account and cross-case boundaries,
post-commit acknowledgment, expected-revision conflicts, private role semantics,
provider-free reopening/status, and inactive scheduling/delivery. No remaining
review blockers were identified. Real SQL/RLS/concurrency and delivery execution
remain outside this foundation's verified scope.

## PR #190 CI contract closure

The exact Stage 1 route gate omitted the seven intentionally approved Wave 4
routes. Auditing the command contract also found a product gap: create's import
key and update revision CAS prevent duplicate effects, but cannot substitute for
the platform's bounded `Idempotency-Key` header and committed-command replay.

The route allowlist now names exactly those seven additions; the existing test
names and route/header bounds remain intact. The command set includes methods
as well as paths, so POST create, PATCH metadata and PUT membership/monitoring are
all covered. It is checked against every approved mutation, retaining only the
existing read-only planning POST distinction. No Wave 4 exemption is introduced.

All routes retain bearer, active-account, forged-identity and no-store boundaries.
All commands require the header, with 24-hour actor/method/concrete-route scoped
receipts committed atomically with state/activity. Same-body retry returns the
current authorized projection of the original case reference; changed body
conflicts, new keys still require CAS, and replay cannot revive revoked access.
Receipt storage is a bounded, hashed-reference repository seam only. Production
still returns `persistence_pending`; the future schema proposal includes the
receipt table/RLS/indexes and concurrent-connection conformance requirements.

The client retains at most 64 hash/random-key pairs in session-scoped memory for
explicit retries. No local storage, automatic upload/retry, provider request,
scheduler, delivery integration or migration is added. See the
[approved command policy](../vnext/api-contract-v1.md#personal-saved-case-command-scope-wave-4).

Changed files for this follow-up:

```text
backend/api/durable_cases.py
services/vnext/durable_cases.py
frontend_next/lib/cloud-case-client.ts
frontend_next/scripts/cloud-case-client.test.mjs
frontend_next/e2e/monitoring-collaboration.spec.ts
tests/durable_case_fixtures.py
tests/test_durable_cases.py
tests/test_durable_cases_api.py
tests/test_vnext_stage1_exit_gate.py
docs/vnext/api-contract-v1.md
docs/wave4/wave4-persistence-schema-proposal.md
docs/wave4/monitoring-collaboration-v1.md
```

Closure verification:

- `python -m pytest -q tests/test_vnext_stage1_exit_gate.py`: 7 passed.
- `python -m pytest -q tests/test_durable_cases.py tests/test_durable_cases_api.py tests/test_case_monitoring.py`: 67 passed.
- `npm run test:wave4`: 19 passed. Existing frontend Auth/account/race and Decision
  Room checks: 36 passed.
- Chromium Wave 4, existing case routing, and login/restore/logout: 18 passed with
  default test timeout, one worker and zero retries. Mutation requests assert the
  bounded header in the browser. No runner/test timeout or retry configuration changed.
- Typecheck, lint (0 errors, 23 existing warnings), E2E build and default production
  build passed. Standalone typecheck reused `.next/cache/.tsbuildinfo` with the same
  full source checks, as documented above.
- The first full Python run under concurrent build/memory pressure produced
  3887 passed, 101 skipped and three failures in unchanged Earth Engine worker
  lifecycle tests (replacement/startup deadlines). Those exact three tests passed
  unchanged in isolation. Their code, deadlines, retries and CI workflows were not
  modified; the full command was rerun after other validation jobs completed.
- Final exact `python -m pytest -q` rerun: **3890 passed, 101 skipped, 1 existing
  Starlette deprecation warning**, exit 0, in 378.48 seconds. No tests were excluded
  or retried by pytest; optional integration skip conditions were unchanged.
- Final read-only review found no remaining important issues. Migration files,
  registry and CI workflows are unchanged; persistence and delivery remain inactive.

## Published-branch final CI closure

Starting published HEAD: `04875dff6240e52bd169992824f89a8a39120a51`.
Fetched main: `26f1b40b3be1b8984a2b587b799ac1451fb3845d`.
Backup ref: `backup/wave4-04875df-before-final-ci`.
Main was merged normally in `a31884e746c1acd75691d50ef6fb1f0104176896`;
no published commit was rebased or amended. The only overlapping/conflicted file
was `saved-cases-entry.tsx`: resolution retains both `CloudCasesPanel` and the new
Grounded Property Copilot link. Incoming professor-server preparation and Wave 1B
contracts remain intact. Incoming main did not change Auth/account/quota code.

The merged build reproduced 11 route budget failures. The shared evidence client
entry unnecessarily re-exported `SavedCasesEntry`, although `/cases` already
imports it directly. Wave 4's Cloud panel made this export pull the Auth SDK and
Cloud UI into unrelated Compare, Report and workspace routes. Removing this
unused re-export isolates the dependency without changing any feature behavior.
The baseline, measurement scripts, ceilings, timeouts and retries are unchanged.

The unchanged storage-unavailable browser test failed in both Chromium and Chrome
before the fix. Traces point to Supabase Auth's module-level debug flag:
`supportsLocalStorage()` probes writes, then an unguarded
`localStorage.getItem("supabase.gotrue-js.locks.debug")` throws under the test's
read denial. Compare hit its generic error boundary before repository diagnostics
could render. After import isolation, the same test passes in both browsers with
zero retries, including Clear All invalidating the frozen report. The existing
storage classification and expected message are unchanged. This fix isolates
evidence routes; it does not change SDK storage handling on Auth-enabled pages.

The seven routes, four bounded-header command contracts, current-permission replay
checks, revision CAS, import deduplication and atomic activity/receipt seam remain
unchanged. Production continues returning `persistence_pending`. No migration,
PostgreSQL adapter, provider refresh, scheduler or delivery activation is added.
Migration sequencing remains deferred until Wave 1C settles its sequence.

Verification on the merged source:

- Stage 1, Wave 4 backend and Auth/account focused suite: 175 passed
  (7 Stage 1, 67 Wave 4, 101 Auth/account).
- Wave 4 frontend: 19 passed. Saved Case/workspace, Compare/Report, Decision Room,
  Grounded Copilot and Auth/account unit regressions: 299 passed.
- Exact unchanged storage-unavailable browser test: 2 passed, Chromium and Chrome,
  zero retries. Full five-file browser matrix: Chrome 71 passed; final Chromium
  rerun 71 passed, both with one worker and zero retries.
- The first combined browser run had 141 passes and one incoming Copilot 390px
  post-reload visibility miss. The exact traced check and then the entire
  Chromium matrix passed unchanged. The original run had no failure trace, so
  its cause remains unconfirmed; no assertion, timeout, retry or Copilot code
  was changed to make it pass.
- Asset-measurement unit contracts: 17 passed.
- Exact Stage 1 command: 7 passed. Exact three-file Wave 4 backend command:
  67 passed, with the existing Starlette deprecation warning.
- Standard `npm --prefix frontend_next run typecheck`: passed. Lint: zero errors,
  23 existing warnings. Both E2E and default production builds passed.
- Fresh E2E measurement and unchanged budget gates: all 17 routes pass. Every
  previously failing route sheds 270,159 bytes; case entry falls from 1,400,900
  to 1,130,741 bytes against 1,301,212. Total static assets: 3,317,718 bytes against
  8,000,000; largest JavaScript: 602,295 against 900,000. The SDK marker remains
  only on login, signup and account routes, not evidence routes.

Resume inspection preserved the completed main merge and both uncommitted closure
files. No implementation change was needed after inspection. Fresh verification:

- Stage 1: 7 passed; Wave 4 backend: 67 passed; Wave 4 frontend: 19 passed.
- Compare/Report and monitoring/collaboration browsers: 50 passed, 25 Chromium
  and 25 Chrome, one worker and zero retries. This includes the exact unchanged
  storage-unavailable/Clear All test in both browsers.
- Full `python -m pytest -q`: 3,923 passed, 104 skipped, one existing Starlette
  deprecation warning, exit 0, in 366.64 seconds. No exclusions or retry overrides.
- Fresh standard typecheck, lint and E2E build passed; lint retains 23 warnings
  and zero errors. Fresh measurement-tool tests: 17 passed.
- Default production build was independently measured: all 17 routes pass;
  3,318,014 total static bytes and 602,354 largest JavaScript bytes also pass the
  unchanged global ceilings.
- Final review preserves authenticated UUID ownership, active-account and
  forged-identity checks, no-store, current ACL checks on replay, bounded
  idempotency, CAS, evidence history and local-copy preservation. There is no
  new migration, provider refresh, scheduler or notification delivery activation.

The following before/after measurements use the same E2E build configuration on
the merged source. Before: 11 failing routes. After: all 17 pass. The six other
routes are unchanged. All values are unique uncompressed static-file bytes from
two cold samples at each of 390px and 1440px, bound to the measured build.

| Route | Before | After | Unchanged ceiling |
| --- | ---: | ---: | ---: |
| `/` | 1,911,627 | 1,911,627 | 2,066,966 |
| `/account` | 1,112,625 | 1,112,625 | 1,334,428 |
| `/cases/[caseId]` | 1,400,900 | 1,130,741 | 1,301,212 |
| `/cases/[caseId]/commute-planner` | 1,422,861 | 1,152,702 | 1,377,984 |
| `/cases/[caseId]/decision-room` | 1,451,297 | 1,181,138 | 1,409,828 |
| `/cases/[caseId]/finance` | 1,433,147 | 1,162,988 | 1,339,100 |
| `/cases/[caseId]/location` | 1,606,240 | 1,336,081 | 1,551,855 |
| `/cases/[caseId]/market` | 1,400,900 | 1,130,741 | 1,301,212 |
| `/cases/[caseId]/overview` | 1,400,900 | 1,130,741 | 1,301,212 |
| `/cases/[caseId]/report` | 1,400,900 | 1,130,741 | 1,301,212 |
| `/cases/[caseId]/risk` | 1,594,519 | 1,324,360 | 1,538,049 |
| `/cases/[caseId]/scenarios` | 1,416,430 | 1,146,271 | 1,337,843 |
| `/compare` | 1,400,900 | 1,130,741 | 1,301,212 |
| `/login` | 1,112,625 | 1,112,625 | 1,334,428 |
| `/places` | 859,738 | 859,738 | 1,030,896 |
| `/preferences` | 880,224 | 880,224 | 1,049,735 |
| `/signup` | 1,112,625 | 1,112,625 | 1,334,428 |
