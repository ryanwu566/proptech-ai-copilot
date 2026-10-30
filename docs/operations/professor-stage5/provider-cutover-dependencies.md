# Provider and cloud cutover dependency closeout

This document owns credential/dependency preparation only. The parallel session
owns NGINX, firewall, auth edge, logging, service persistence and security
acceptance. Nothing here installs or alters those components, credentials,
databases, cloud services, workflows or frontend settings.

Subsequent [deployed cloud evidence](deployed-cloud-evidence.md) adds explicit
VERIFIED_LIVE / VERIFIED_REPO / HISTORICAL_ONLY / UNKNOWN labels, a documented
Earth Engine identity and dated Render release, and the full visible scheduled
CI history. The replacement matrix now adds three shared scheduled callers to
the earlier 22 platform rows; no remote cutover or retirement is verified.

## What the new observations establish

- The referenced Cloud Run origin responds to unauthenticated GET health and
  readiness. Its public OpenAPI advertises **109 paths**. Only path/method names,
  HTTP status and response hashes were retained. No provider calculation,
  authenticated request, refresh or write endpoint was invoked.
- Render health/readiness/OpenAPI were unavailable within bounded requests.
  This does **not** prove retirement, absence, loss of data or lack of callers.
- GitHub's repository workflow-run API, filtered to `workflow_dispatch`, returns
  all **21 API-visible manual runs** at the observation time: coverage **13**,
  Market refresh **7**, commute **1**. Latest visible coverage and commute runs
  succeeded; latest Market refresh failed. No logs, artifacts or secret APIs
  were requested. These are historical outcomes, not present credential tests.
- Public Vercel code previously observed at release `9cc40d6` references Cloud
  Run. That is a deployed code reference, not a browser request trace. No actual
  Vercel environment inventory or production change was made.

Evidence: `public-route-observation.json`,
`maintenance-dispatch-history.json`, `public-caller-references.json` under
`reports/professor-stage5-ingress`. Earlier 50-run sampling and failed
per-workflow endpoint observations remain historical evidence; the complete
manual-event query supersedes that sample **for visible manual-run history
only**. Current workflow activation, deleted/inaccessible history and other
schedulers/callers remain unverified.

## Inventory authority and exact missing receipts

The names matrix covers 333 repository configuration identifiers, including 83
credential/public/legacy identifiers, plus 9 file-only contracts. Six API files
have accepted hash-bound Stage4A ownership/mount evidence. This is not a fresh
root inspection or proof of every cloud production requirement. No current
local-profile credential is confirmed missing. No additional credential is
requested, installed, compared by value or admitted automatically.

Only these bounded **sanitized metadata** receipts are still needed for deployed
dependency closure. Obtain them in an already authorized operator console; do
not supply raw service JSON, environment exports, screenshots of values, logs,
tokens, keys, passwords or downloaded credentials to an agent.

| Receipt | Exact non-secret metadata | What it resolves |
|---|---|---|
| CR-SERVICES | Project/region, all in-scope service/job names, serving and retained revision identifiers, image digests and traffic split | The observed one referenced origin is not proof of a complete deployed service inventory |
| CR-NAMES | Environment **names**, Secret Manager reference resource **names**, secret-file mount names, scopes for serving and retained revisions | Actual Cloud Run credential/config inventory; names alone do not prove usable credentials |
| CR-IDENTITY | Attached service-account identifier, ADC source category, effective role names, role scope, Earth Engine project/API access and API-key restriction categories | Whether metadata ADC, workload identity or a protected credential file is needed; deployment identity is not runtime identity |
| CR-CALLERS | Caller/service principal identifiers, invoker policy, scheduler/job names and target paths, background consumers, build/deploy integrations | No unique caller or background consumer is silently abandoned |
| RENDER-SERVICES | Service/job/cron/environment-group names and identifiers, deployed/retained revision identities, persistent disk presence | Actual runtime/job universe rather than `render.yaml` declarations alone |
| RENDER-NAMES | Environment names, linked-group names, secret-file **names** and per-service/deploy scopes | Render-only credentials or aliases; never reveal values or file content |
| RENDER-CALLERS | Active callers, webhooks/schedules/job names and target paths, current disposition of the three manual workflows | Whether each operation must migrate, retire explicitly, or remain temporarily external |
| FRONTEND-CI | Vercel Production/Preview/Development and branch-override environment **names**; GitHub repo/org-inherited/Environment secret and variable **names** | Browser routing/config scope, deployment identities and maintenance-token dependencies |
| STATE-ROLLBACK | Database/schema/store identifiers, whether unique mutable writes exist, protected backup verification result and retained rollback identity | A names-only matrix cannot prove that all remote user/usage/application state has migrated |

Record explicitly reviewed empty scopes as reviewed empty. An absent receipt is
UNKNOWN, never empty. Preserve the source/time/resource/scope for each receipt.
Public issuer/project/service-account identifiers are allowed metadata;
authorization headers and access/signing keys are not.

For the four credential-name receipts, use the existing strict names-only JSON
contract and importer in [credential evidence collection](credential-evidence-collection.md).
Keep IAM/callers/state receipts separate: marking names `all_deployments` cannot
approve account authority, runtime ADC, migration completeness or retirement.
The available GitHub connector explicitly excludes secret APIs; Cloud Run,
Render and Vercel have no suitable authenticated inventory connector here.
No CLI login or credentials are requested to bypass that boundary.

## Provider/alias migration decisions

The [full matrix](../provider-credential-matrix.md) is the name-by-name source of
truth. The following decisions explain dependencies that must not be copied by
matching an alias or cloud role name.

| Names / contract | Professor or frontend replacement | Admission / retirement rule |
|---|---|---|
| `GOOGLE_MAPS_API_KEY` | Stage2 `google_maps_api_key`, approved backend consumers only | Shared geocoding/Places/Routes key contract; optional/paid consumers remain disabled |
| `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY` | Vercel browser-public config only, independently browser-restricted | Never substitute the server key; no Vercel change in this task |
| `GOOGLE_APPLICATION_CREDENTIALS`, `EARTH_ENGINE_PROJECT` | Protected `earth_engine_adc_json` plus reviewed public project config; admitted Earth Engine worker only | Cloud Run implicit metadata ADC cannot be copied; review least-privilege runtime identity separately |
| `GCP_SERVICE_ACCOUNT_KEY`, `GCP_SA_KEY`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT` | Deployment/operator identity only if still needed | Not automatically runtime ADC; never mount a CI deployment credential into API |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Unsupported legacy alias; no automatic Professor mapping | Verify actual consumer/format before a separately approved ADC adoption |
| `TGOS_APP_ID`, `TGOS_API_KEY` | Stage2 `tgos_app_id`, `tgos_api_key`, canonical admitted adapter | Optional, no automatic activation |
| `TGOS_ADDR_API_KEY`, `TGOS_MAP_API_KEY`, `TGOS_MAP_KEY`, `TGOS_THEME_API_KEY`, `TGOS_THEME_KEY` | Unresolved legacy spellings; no automatic canonical substitution | Actual live consumer/scope must be reviewed; unknown is not missing |
| `TDX_CLIENT_ID`, `TDX_CLIENT_SECRET` | Restricted local snapshot producer only, protected `tdx_client_id`, `tdx_client_secret` | Commute persistence adapter is not implemented by this audit; do not add API mounts |
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, R2 endpoint/bucket/region config | Optional approved archive/upload/remote-artifact consumer | Local NLSC/WRA need none; prove remaining upload/archive/CI consumers before revocation |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Vercel browser-public identity config | Same accepted Supabase authority/users; no password/key migration |
| `SUPABASE_URL`, `SUPABASE_JWT_ISSUER`, `SUPABASE_JWT_AUDIENCE` | Existing backend public issuer/audience/JWKS verifier | No service-role or signing secret required |
| `SUPABASE_JWT_SECRET`, `SUPABASE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_URL` | Legacy/operations contracts; not Professor API runtime secrets | Inventory remote consumers before retiring; no import into six-file profile |
| Six accepted API runtime credentials | Existing app/usage/valuation/user URLs and peer/session files in accepted Stage2/4 profile | Restore the same protected credentials only if actually missing; no new passwords/role changes |
| `POSTGRES_PASSWORD`, DB admin/init files, `DB_ACTOR_PASSWORD` | DB-only or narrowly scoped operator/test contract | Never replace SELECT-only serving/user principals with administrator identity |
| `COMMUTE_REFRESH_TOKEN`, `MARKET_READ_MODEL_REFRESH_TOKEN`, `RENDER_API_BASE_URL` | Approved local restricted operations, or explicit job retirement | Historical jobs exist; do not retarget them to public Professor maintenance URLs |
| `GITHUB_TOKEN` | Ephemeral workflow-scoped identity generated by GitHub | Never copy into Professor; usage metadata is not proof of permanent secret presence |
| `RENDER_API_KEY`, `VERCEL_TOKEN`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_TUNNEL_TOKEN` | Legacy deployment/operator contracts only, subject to actual consumer inventory | No external tunnel introduced; shared account-level credentials are not automatically retirement-safe |
| `OPENAI_API_KEY`, `NLSC_GATEWAY_CLIENT_TOKEN`, `MAPBOX_API_KEY` | Optional/unadmitted or unresolved source references | No provider activation; require actual retained consumer and approved contract first |
| Government local/open datasets and public APIs | Existing local NLSC/WRA/RIS and supported public contracts | No additional credential requirement established; archives do not imply a runtime adapter |

Preserve `UNKNOWN` in the full matrix where a reference is not an admitted
runtime dependency. This table explains disposition and does not override live
presence or invent a credential requirement.

## Credential installation/adoption procedure

No installation is required for the accepted current profile. Do not rerun
Stage2 adoption/staging or Stage4 provisioning. For a **confirmed missing and
separately approved** provider credential, use only the reviewed hidden-TTY or
protected-file commands in [credential evidence collection](credential-evidence-collection.md).
The operator enters/transfers the value directly in an operator-owned terminal,
never through Codex, command arguments, logs or Git.

Before mounting a newly admitted provider: record consumer/required scope,
restrictions/quotas and protected backup; install without replacing existing
files; validate ownership/permissions without content; retain optional-disable
state; then prepare a separately reviewed minimal mount/recreation proposal.
Installation alone is neither activation nor a successful provider test.
`PROFESSOR_USER_DATABASE_URL` uses the accepted Stage4 recovery contract, not
the Stage2 installer. No speculative privileged script is needed now.

## Cutover and retirement dependency checklist

- [ ] All nine receipts above reviewed for exact resource/scope and contradictions.
- [ ] Every still-required server credential/ADC identity has an approved local
  consumer, protected destination and named non-paid validation result; no unique
  required cloud secret remains. Browser-public config stays frontend-only.
- [ ] All callers and unique remote state accounted for; authority/backup and
  rollback evidence accepted. Preserve existing Supabase users and Professor data.
- [ ] Three maintenance jobs receive explicit final disposition. Current target
  A is local migration if retained; interim C preserves remote definitions and
  activity. No inference of disuse from age/failure. No new timer is implied.
- [ ] Commute producer/API snapshot persistence and Market restricted-writer
  adapters pass focused acceptance before claiming replacement. No public ops,
  administrator API credential, raw deletion, bootstrap replay or market_ops.
- [ ] Parallel hardening session supplies its accepted external HTTPS, security,
  reboot/renewal and rollback receipts. This document does not implement them.
- [ ] Vercel Preview then Production authenticated E2E proves the Professor API
  origin, session/profile/Saved Cases persistence and cross-user denial, Market,
  Valuation, Trend, Finder, GIS and ML behavior/limitations. Localhost/public
  OpenAPI availability cannot satisfy this gate.
- [ ] Approved observation window demonstrates no remaining old-origin caller
  or job. Keep old deployments and credentials unchanged until that proof.
- [ ] Obtain explicit retirement approval before disabling a job/service,
  deleting retained state or revoking cloud-specific/shared credentials.

Separate platform matrices: `cloud-run-retirement-matrix.csv` and
`render-retirement-matrix.csv` in the Stage5 reports directory. All rows remain
retirement-ready NO. The missing inventory receipts are independent of WAN and
parallel hardening; credentials are not yet declared ready for cutover.
