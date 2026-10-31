# Actual cloud dependency evidence and remaining unknowns

This inventory uses four explicit evidence levels, per field:

| Level | Meaning |
|---|---|
| VERIFIED_LIVE | Timestamped public/platform metadata observation, limited to the asserted field |
| VERIFIED_REPO | Tracked source/configuration fact; not proof it is configured in a deployed service |
| HISTORICAL_ONLY | Dated observation or previously accepted snapshot; not current live state |
| UNKNOWN | Insufficient evidence; does not mean absent, missing, unused or production-critical |

Machine inventory: `reports/professor-stage5-ingress/cloud-deployed-dependency-inventory.json`.
The companion `cloud-component-replacement-matrix.csv` contains 25 dependency
rows: 10 Cloud Run, 12 Render and 3 shared scheduled CI consumers. Migration
status distinguishes an accepted local replacement from verified remote caller
cutover. No remote cutover or retirement is marked verified.

## Cloud Run

The referenced `proptech-earth-engine-api` endpoint is publicly reachable for
anonymous health/readiness/OpenAPI/release metadata GETs (VERIFIED_LIVE).
The public OpenAPI advertises 109 paths. No provider operation, authenticated
request, refresh or write endpoint was executed. An anonymous successful GET
does not establish the service's configured ingress mode, invoker IAM policy,
complete caller set or existence of other services/jobs.

The referenced hostname encodes `asia-east1`; that is the repository endpoint
reference, not a control-plane region listing. No complete service/project/job
universe has been supplied. Current release metadata reports commit, release
and build timestamp as `unconfigured`. Image digest, serving/retained revision
and traffic assignment therefore remain UNKNOWN; do not substitute the current
Git branch, Vercel commit or a previous release for the cloud image identity.

Repository documentation provides a concrete **declared** Earth Engine identity:

```text
service account: proptech-render-earth-engine@project-3bd34c3e-daee-493f-ad6.iam.gserviceaccount.com
Earth Engine project: project-3bd34c3e-daee-493f-ad6
```

These are public identifiers, not credentials. The declaration was introduced
in commit `cbaa297ce034f74eae94915114afaa65c68c8673` (2026-09-21) and remains in
`docs/satellite-reference-evidence-v1.md`. It specifies attached service identity
and Cloud Run metadata ADC, without a JSON key or `GOOGLE_APPLICATION_CREDENTIALS`.
This is VERIFIED_REPO only. Current attachment, effective IAM roles/scopes,
registered project/API access and the service-project relationship are UNKNOWN.
Do not infer a portable local ADC file from that declaration or copy a CI deploy
identity into Professor API. A retained local Earth Engine capability needs a
separately approved runtime identity method; it remains optional and disabled.

Actual deployed environment names, Secret Manager reference names and secret
mounts are UNKNOWN. Source contracts and build arguments are recorded separately
in `repository-history-cloud-metadata.json`, never promoted to live presence.

## Render

`render.yaml` declares one Python web service, `proptech-ai-copilot-api`, with
34 environment-variable names and no native worker/cron declaration
(VERIFIED_REPO). That does not prove the actual service count, deployed values,
secret/group/file names or absence of native Render jobs.

Sanitized repository evidence records a successful Render release observation
on 2026-10-11 at commit `ef1c49c55a58eb0ab63beefe0cd2ddc1f2f9717b`
(HISTORICAL_ONLY). Bounded local checks and the separate public read tool could
not obtain current release/health metadata. Current live inventory is BLOCKED,
not declared empty or retired. Retained deploys, image identity, callers, native
schedules and unique state remain UNKNOWN.

The older `production-identity-provider-closure-v1-evidence.json` explicitly says
`local_checkout_not_production` and `network_requests: 0`. Its provider names and
configuration contracts are useful source evidence; its BLOCKED/local results
cannot establish whether either cloud actually has a credential.

## Callers, manual workflows and scheduled/background consumers

Existing public Vercel code contains the Cloud Run origin (VERIFIED_LIVE code
reference); successful actual browser routing, all frontend scopes and the
complete backend caller graph are unproven. GitHub workflow target **names**
are known, while their deployed URL/token values were intentionally not read.

The earlier complete visible manual-event query returned 21 runs: coverage13,
Market7 and commute1. Their source definitions remain manual, with interim
disposition C: keep existing definitions/activity unchanged. Target A is local
restricted operations if retained, after the separately documented commute
persistence and Market writer gaps are resolved. Never retarget public ops.

A new complete API-visible scheduled-event query returned **374 runs**:

| Workflow | UTC cron in matching source | Visible runs | Latest visible outcome | Replacement / validation |
|---|---|---:|---|---|
| `hosted-production-smoke.yml` | `17 */6 * * *` | 329 | success, 2026-10-30 | Retain bounded smoke against an approved Professor origin; validate actual target, release identity and cutover before any retarget |
| `authenticated-identity-smoke.yml` | `23 4 * * *` | 40 | failure, 2026-10-29 | Retain protected user-scoped smoke; diagnose in its own acceptance task and validate real auth/ownership without enabling writes |
| `import-official-market-data.yml` | `17 4 1,15 * *` | 5 | success, 2026-10-15 | Schedule emits readiness notice only; any retained import becomes a reviewed local bounded operation with explicit source/scope and restricted writer |

All 40 visible scheduled identity-smoke outcomes are failure. No job logs were
read, so no missing credential, user-auth defect or specific failure cause is
inferred. A successful hosted smoke may also be a configuration-required early
exit; job conclusion alone is not application E2E acceptance.

The latest observed scheduled-run workflow blobs match the reviewed local
source. The PLVR scheduled branch prints a readiness notice; download/import
steps require `workflow_dispatch`. Its success is **not evidence of a database
import**. The dedicated names are `PLVR_UPDATE_DATABASE_URL` and
`PLVR_UPDATE_ENVIRONMENT`, scoped to `production-market-import`. Never substitute
a serving/admin URL or replay an importer against accepted Professor tables.

The scheduled callers also reference `FRONTEND_PRODUCTION_URL`,
`BACKEND_PRODUCTION_URL`, `PRODUCTION_SMOKE_TOKEN`, expected release/commit
names, and the protected `SMOKE_*` names. They belong to the specific CI/operator
consumer, never the six-file API runtime. No schedule, workflow, URL, token,
runtime or database was changed or executed by this audit.

The 374-run query covers all API-visible schedule events at observation time.
It does not prove deleted/inaccessible history, current workflow enablement,
Cloud Scheduler inventory, Render-native cron or other external callers.

## Credentials that may retire after cutover

The JSON records eight conditional disposition groups. **Nothing is ready now.**

- Render-only deployment access/aliases and legacy refresh tokens may retire
  once their service/job/rollback consumers are migrated or explicitly retired.
- Cloud Run-only deploy keys/workload bindings and service-specific invoker
  access may retire once exclusive scope and no remaining consumer are proven.
  Do not revoke a shared identity or Earth Engine role still needed locally.
- Retain any adopted Google/TGOS/TDX/R2 provider credential needed by an approved
  local consumer. Only unused cloud-specific copies or exclusively unused keys
  become retirement candidates; local NLSC/WRA alone do not prove R2 unused.
- Preserve Supabase identity/users/public frontend configuration and Professor
  runtime credentials. Legacy privileged Supabase or remote DB access needs its
  own caller/state proof; never revoke signing authority as a migration shortcut.
- `GITHUB_TOKEN` is ephemeral job identity, not a permanent Professor secret to
  install or revoke through this retirement task.

## Exact remaining metadata boundary

No `gcloud`, Render, Vercel or `gh` CLI exists on PATH; additional common gcloud
binary locations are absent. No suitable authenticated Cloud Run/Render/Vercel
metadata connector is available. The GitHub connector supplies repository/run
metadata but explicitly excludes secret APIs. No token store, private envfile,
credential payload, raw service export or SDK authentication material was read.
No CLI was installed or authenticated to bypass that boundary.

The remaining operator-visible receipts are the existing service/revision and
names-only environment/secret/group/file inventories, actual service identity/
ADC/IAM, caller/scheduler targets and unique remote state/rollback metadata.
Use [the exact receipt checklist](provider-cutover-dependencies.md) and existing
strict names-only importer; no key values or raw deployments should be supplied.
Public cutover, reboot and hardening remain separately owned acceptance gates.
Current local-profile credentials are accepted, none confirmed missing; unknown
cloud dependencies are not labeled production-critical without evidence.
