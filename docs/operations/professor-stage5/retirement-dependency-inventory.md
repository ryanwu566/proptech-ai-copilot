# Cloud Run / Render dependency inventory

Inventory of all accessible repository references is prepared. **Neither cloud
service nor any credential is approved for retirement.** Actual deployed env
names, secret references, service identities and unique remote data remain
unverified. Missing access is independent of router/WAN status.

The [field-by-field deployed inventory](deployed-cloud-evidence.md) distinguishes
current public metadata from source declarations and historical observations.
It adds all visible scheduled CI consumers, which are separate from the three
manual Render maintenance workflows. The complete cloud-native scheduler/job
universe is still UNKNOWN.

The subsequent provider-only closeout records Cloud Run's public OpenAPI path
names and all 21 API-visible manual dispatch runs: coverage13, Market7,
commute1. See [cutover dependency checklist](provider-cutover-dependencies.md).
These observations supersede the earlier 50-run activity sample for visible
manual history only; they do not establish current secret presence, workflow
activation, external callers or the complete cloud service/job universe.
Render's bounded public metadata requests were unavailable, not proof of absence.

Machine-readable graph:
`reports/professor-stage5-ingress/cloud-retirement-dependencies.json`.
Rebuild with `python3 -B scripts/ops/professor_stage5.py --retirement-inventory`.
The command reads public source declarations only; it neither calls the clouds
nor runs a maintenance workflow.

The final [adoption/retirement matrices](adoption-retirement-matrix.md) now assign
explicit dependency replacements and migrated/tested/retirement-ready fields.
All three job targets are A: move locally if retained, with C: preserve current
external definitions/activity unchanged during migration. The local coverage
bootstrap substep is not carried forward. See [local maintenance adoption](local-maintenance-adoption.md)
for the verified process-memory and write-privilege implementation gaps.

A fresh public Vercel asset observation records release9cc40d6 and a Cloud Run
origin literal. This is deployed code-reference evidence, not a successful API
call trace or a credential inventory. A sample of50/1490 GitHub workflow runs
contains no matching maintenance job; it is not evidence that those jobs are
unused. Both observations are in the final matrix evidence links.

## Cloud Run: proptech-earth-engine-api

Historical hostname:
`proptech-earth-engine-api-712372598609.asia-east1.run.app`. This identifies an
existing referenced service, not an approved new ingress or proof of current use.

| Dependency | Evidence available | Required disposition before retirement |
|---|---|---|
| Vercel/browser backend origin | Source NEXT_PUBLIC_API_BASE_URL plus historical deployed-frontend observations | Verify actual Preview/Production origin, cut over only after approved Professor HTTPS and full E2E |
| Runtime/build | Dockerfile.cloudrun, release/guardrail scripts and historical revision documentation | Record actual serving/retained revision, image digest, runtime identity and rollback receipt; do not treat an old image tag as current deployment proof |
| Google Maps/Places/Routes | Actual source shares GOOGLE_MAPS_API_KEY | Names-only actual cloud credential inventory; if separately admitted, install into Professor protected store, verify restrictions/quotas, preserve optional-disable state until approval |
| Earth Engine | ADC/project/IAM contract and optional satellite source | Identify actual attached service account/implicit ADC and approved project; a Cloud Run metadata credential is not a portable file or a CI deployment key |
| Databases and usage/evidence state | DATABASE_URL/valuation/usage/legacy aliases in source; accepted Professor local DBs | Prove no unique remote production writes/data remain, back up through approved protected procedure, preserve identity/user data |
| CORS, host/proxy policy, billing/admission | Existing hosted guardrail docs | Keep old service guarded until cutover; validate Professor equivalents and all shared credential consumers before revocation |
| Final survival/rollback | Local preparation only | Reboot, trusted TLS renewal/recovery, external and real authenticated Preview/Production acceptance, independent retirement approval |

Actual service IAM, environment, credential presence and retained revision
configuration cannot be established from public URLs or this repository. Do
not run the legacy full-service JSON export through an agent: it may contain
values. Use the names-only evidence procedure instead.

## Render: proptech-ai-copilot-api

Historical hostname:`proptech-ai-copilot-api.onrender.com`. `render.yaml` declares
the web runtime/build/start/health contract and env names. `sync:false` proves
only a declaration, not a deployed value or credential presence.

| Dependency | Source | Required disposition |
|---|---|---|
| Browser backend origin | NEXT_PUBLIC_API_BASE_URL; hosted smoke and docs | Approved Preview then Production Professor HTTPS cutover and rollback |
| Runtime credentials/configuration | render.yaml, linked configuration references | Inventory service env/group/file names and scopes; prove no unique required provider credential remains |
| Commute snapshot refresh | refresh-commute-snapshot.yml | Separate local controlled operation or explicit retirement of that job |
| Market read-model refresh | refresh-market-read-model.yml | Separate local controlled operation; never enable public market_ops |
| Market coverage maintenance | reconcile-market-coverage.yml | Reviewed local deterministic process; preserve quarantine/coverage invariants |
| Build identity | RENDER_GIT_COMMIT fallback | Preserve Professor's explicit release identity; legacy alias is not a required new Professor setting |
| Database/user/evidence state and rollback | Legacy runtime URL references | Prove no unique remote state or caller remains before any shutdown/revocation |

### Three write workflows are a separate migration

All three use `secrets.RENDER_API_BASE_URL`. Their additional secrets and paths
are recorded per workflow in the machine graph:

- Commute:`COMMUTE_REFRESH_TOKEN`, `/commute/refresh`.
- Market:`MARKET_READ_MODEL_REFRESH_TOKEN`, `/market-insights/refresh`.
- Coverage:`MARKET_READ_MODEL_REFRESH_TOKEN`, coverage bootstrap/reconcile/audit.

The future public nginx edge denies those maintenance paths. **Do not merely
change the CI base URL to Professor HTTPS**, add a public bypass, enable market_ops,
or send refresh tokens to Vercel/browser code. No workflow was modified or run.

If still needed, the backend owner must review a local operator/scheduler job
that uses a dedicated restricted operations principal and controlled local-only
maintenance. It needs explicit update scope, resource/timeout limits, a backup,
PLVR quarantine/coverage checks, sanitized results and rollback. Existing guarded
functions may be reused only after that review; do not invoke a protected refresh
blindly. If unused, retire the workflow and access only after separate approval.

## GitHub/CI and Vercel

The GitHub reader can now inspect repository/branch/workflow-run metadata. It
explicitly cannot list repository/org/Environment secrets APIs. This is a
capability limitation, not evidence of an empty secret inventory. The observed
remote main and sampled workflow run refer to9cc40d6; local Stage1–5 commits
remain unpushed. Do not confuse remote CI success with acceptance of this branch.
No job logs, secret APIs, workflow dispatch or remote writes were requested.

Inventory repository/org-inherited/Environment secret and variable **names**,
including read/write smoke and production-market-import scopes. `GITHUB_TOKEN`
is platform-generated workflow identity; do not copy it into Professor runtime.
Vercel remains frontend-only and retains browser-public Supabase/Maps config.
Its actual Production/Preview/Development/branch override inventory is pending.

See [names-only collection](credential-evidence-collection.md),
[current matrix](../provider-credential-matrix.md) and
[retirement acceptance gates](cloud-retirement.md). Reference completeness does
not establish deployed dependency closure, credential equivalence or permission
to retire a service.
