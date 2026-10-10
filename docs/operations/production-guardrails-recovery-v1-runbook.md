# Controlled Beta guardrails and recovery runbook

Production decision: **NO-GO**. This is an owner procedure, not authorization
to change production. This branch executes no cloud writes or hosted load.
Incident/release owner must name a primary and backup privately, record their
paging route and decision authority, and demonstrate receipt before beta.
No SLA, RPO or RTO commitment is adopted by this document.

## Evidence and acceptance

Use the existing `scripts/generate_release_evidence.py`; its
`production_guardrails` extension is consumed by PR #170's Final Production
Acceptance v1 and remains an input for future v2.
`production-guardrails-contract-v1.json` lists every exact required fact,
owner role and numeric interval. The companion schema defines the bounded
summary. All 15 controls are required; NOT_APPLICABLE cannot waive them.
Missing proof is BLOCKED; invalid submitted PASS proof is FAIL. A valid owner
submission can PASS an individual control; the extension's standalone decision
stays NO_GO because it does not evaluate unrelated acceptance.

Keep raw exports, account/service identifiers, recipients, receipts and
credentials in a private evidence archive, outside Git. The owner creates one
proof JSON per control with `control`, `release_commit`, `facts` matching
the contract and `evidence_files` referencing 1–8 independently reviewed
supporting exports/receipts. Each source has `file`, `sha256`, and `kind`
(`cloud_export`, `staging_drill`, `notification_receipt`, or `owner_review`).
Every supporting file digest must match actual bytes; a proof cannot reference
itself. Create a record containing `state`, `owner_role`, `verified_at`,
`release_commit`, `proof_file` and `proof_sha256`. Hash the actual proof bytes.
Use a full 40-character release SHA, timezone-aware observation within seven
days, and a relative `.json` proof path inside the supplied proof directory.
No unknown fields, extra facts, wildcard paths or stale-release PASS.
The offline checker verifies facts and file identity; it does not authenticate
cloud exports or prove that an owner's assertions are true. An independent
owner review of supporting exports/drill receipts is required before signoff.

```text
python scripts/generate_release_evidence.py --output PRIVATE_RELEASE_JSON --release-id EXACT_RELEASE --commit FULL_SHA --schema-version EXACT_SCHEMA --guardrail-owner-records PRIVATE_RECORDS_JSON --proof-root PRIVATE_PROOF_DIRECTORY
```

The committed release JSON records the starting SHA and repository work scope;
it has no deployed-release evidence. Regenerate with the final immutable
commit for owner acceptance. Do not copy local drill PASS into an external
control. The operations gate and standalone guardrail extension never issue GO.
PR #170's acceptance mode in the same generator can issue GO or CONDITIONAL GO
only when every original acceptance gate passes and every required guardrail
proof validates. Use `--acceptance-input PRIVATE_GATE_OBSERVATIONS_JSON` with
the owner-record/proof-root options above. Both output modes use the same nested
`production-guardrails-v1` schema for future acceptance v2 consumption. The
extension's own NO_GO/UNKNOWN decision refers to its incomplete standalone
scope; the parent acceptance verdict combines it with the original scorecard.
Hashes validate archive bytes and owner assertions, not live cloud authenticity;
independent deployed evidence review remains required.

## Ingress, edge and distributed control owner actions

The browser/Vercel frontend calls `NEXT_PUBLIC_API_BASE_URL` directly. Frontend
WAF alone does not cover that backend. Determine the actual backend platform,
every domain/default URL/load balancer, worker/revision/region and runtime
command using read-only inventory. The repository includes Render and Cloud
Run entry points; neither establishes a deployed topology.

Set `API_ALLOWED_HOSTS` to 1–16 exact backend DNS/IP host names (no scheme,
port or wildcard), including the owner-approved health-probe host. Keep
`--no-proxy-headers`. The transport peer remains a coarse ingress peer; no
end-user IP is derived from XFF, Forwarded or X-Real-IP. `CORS_ALLOWED_ORIGINS`
must contain exact HTTPS frontend origins. Origin/Host admission is not
authentication or backend bypass protection. No-Origin machine requests
remain allowed; protected routes still require their existing authorization.
Production docs/OpenAPI are denied; passive health, readiness, compatibility,
release and provider status remain public categorical surfaces. Metrics require
the existing 32–512-character scrape token and are hidden when disabled.

For Cloud Run, require restricted ingress
`internal-and-cloud-load-balancing`, reviewed default URL disabling and all
custom domain paths. Attach the approved backend security policy at the load
balancer, verify effective policy attachment, then prove direct-origin denial
using owner-approved passive requests. Default URL disabling alone does not
close custom domain mappings. The read-only owner command is:

```text
gcloud run services describe SERVICE --region REGION --format=json
python scripts/verify_cloud_run_guardrails.py --export PRIVATE_SERVICE_JSON
```

Save the export privately: it can contain secret environment values. The
script prints categories only, never invokes gcloud or changes configuration;
it checks v1 JSON annotations and exact command arguments. Shell strings or
v2 formats require owner review and remain UNKNOWN. Export checks cannot
PASS trusted ingress or WAF. [Cloud Run ingress](https://docs.cloud.google.com/run/docs/securing/ingress)
documents the applicable network paths.

For Render, inventory direct service origins and plan-supported edge controls;
if they cannot prevent backend bypass, choose a reviewed ingress architecture
before beta. This run does not provision it.

Edge policy must cover the backend's actual normalized capability routes in
`backend/api/abuse_middleware.py`, including trailing slashes and refresh/admin
paths. Apply aggregate and client rates no higher than the corresponding
`POLICIES` request rate: geocoding 30/minute; Places/Routes 10/minute;
satellite 2/5 minutes; terrain/parcel 6/minute; preserve lower reviewed limits
for other routes. Enforce body limits of at most 1,000,000 bytes, with an
explicit parcel-upload exception of at most 11,000,000 bytes; app receive
timeout is 15 seconds, query limit 8,192 bytes and body capacity 16 requests.
Set bot/malformed-traffic rules, avoid challenge flows that break approved
API clients, and record a staging emergency deny/recovery test. Health probes
need a bounded separate allowance, not an unrestricted expensive-route bypass.

`ANTI_ABUSE_ENFORCEMENT_MODE=local_only` is the only implemented mode. The
`SharedAdmission` interface requires atomic reservations before dispatch,
fixed account/capability namespace, all workers/revisions, bounded retention
and database deadlines, least-privilege schema/role, and fail-503 on store
failure. No adapter is registered. Production PostgreSQL exists but a reviewed
limiter schema, pool isolation and atomic two-instance failure tests do not.
Do not enable `postgres`, `redis` or `distributed` and infer coordination.
An unavailable mode fails startup. Cross-instance enforcement stays BLOCKED.

## Provider quotas and cost

The contract proposes conservative beta upper bounds, not actual configured
quotas or prices: Google Geocoding 30/minute, Places 30 physical calls/minute,
Routes 10/minute across every credential consumer; Earth Engine daily EECU
seconds at most 3,600 and concurrent requests at most two. Owners must identify
the effective API quota metric, account/project, reset interval and accepted
override, demonstrate read-only configuration, and tighten these proposals if
their financial exposure model demands it. If a provider cannot enforce a
required limit, record BLOCKED and keep the capability disabled.

Google browser Maps/Street View have separate public keys, API/referrer
restrictions and effective quotas; backend counters do not cover them.
R2 storage/request/egress, TDX, TGOS and NLSC gateway entitlements/charges also
require inventory. No active LLM billing integration was found in the scoped
provider dispatch paths. Refresh scripts and other credential consumers must
be included in the account-level model.

Per-request resource limits, process request/operation counters and concurrency
are independent of global provider-account quotas. Local counters reset on
restart and multiply across processes, instances, overlapping revisions and
regions. A max-instance setting is not a currency ceiling. Provider attempts
and SDK work do not translate to dollars or EECU seconds.

Configure actual alerts at 50/80/100% and forecast at 100% of an approved
financial target, with primary/backup delivery receipts. Alerts-only budgets
do not stop spending. Verify any eligible spend-cap service coverage and
enforcement delay; unsupported services remain BLOCKED. Earth Engine's daily
EECU quota is approximate and can overshoot; it cannot independently close
`global_cost_ceiling`. See [budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets),
[spend-cap scope](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps),
and [Earth Engine cost controls](https://developers.google.com/earth-engine/guides/cost_controls).

## Monitoring and escalation

Use existing protected `/metrics`, HTTP latency histograms and fixed
capability/event counters; no user, address, peer, coordinate, billing ID or
request ID metric labels. Scrape every active instance/revision and handle
resets. A single instance scrape cannot represent fleet totals. Keep raw URLs,
tokens and provider payloads out of alert evidence. The deployment owner must
configure collection and notification delivery; this repository does not
install an observability service.

Proposed beta thresholds for owner adoption:

| Signal | Threshold/window | Action |
| --- | --- | --- |
| 5xx rate | >5% with at least 20 requests in 5 minutes | SEV2; verify release/provider health |
| 429 | >20% with at least 20 requests in 5 minutes | SEV2 if legitimate users impacted; inspect fixed budget reason |
| 503 | >5% with at least 20 requests in 5 minutes | SEV2; distinguish kill/capacity/guard failure |
| Provider failure/timeout | >10% of at least 10 attempts in 5 minutes | SEV2; disable affected capability if persistent |
| Provider budget exhausted | any sustained increase for 5 minutes | SEV2; inspect quotas, consumers and misuse |
| Backend latency | p95 >5 seconds over 10 minutes, at least 20 requests | SEV2; inspect saturation; do not widen budgets |
| Backend/DB readiness | two consecutive unavailable checks, 60 seconds apart | SEV2; passive DB checks use existing SELECT 1 timeout |
| Artifact freshness/checksum | any invalid/stale required artifact | block dependent capability; SEV2 if core flows affected |
| Immutable release mismatch | any frontend/backend mismatch vs approved pair | stop promotion; SEV2 |
| Runaway spend, secret exposure, data corruption | one confirmed event | SEV1; page primary and backup immediately |

Metrics: `proptech_http_requests_total`, dedicated 429/503/5xx totals,
`proptech_http_request_duration_seconds` and
`proptech_provider_cost_events_total` (`provider_failure`, `provider_timeout`,
`provider_budget_exhausted`, `capability_disabled`, `guard_unavailable`, etc.).
Freshness/identity/health are passive status checks using existing provider
acceptance and production smoke contracts; they are not new per-user metrics.
SEV3 covers isolated non-core degradation with no loss or runaway cost. The
incident owner records severity, safe release IDs, categorical evidence,
decision/approver and recovery checkpoints. Response-time targets require
separate owner adoption; no SLA is promised here.

## Backup and restore

Database owner inventories `DATABASE_URL`, valuation BLUE, Compact GREEN,
pilot compatibility DB aliases and any independently hosted datastore. A
backup of one database is not coverage of all of them. Require encrypted
off-machine/offsite snapshots/PITR, latest successful backup within 24 hours,
reviewed retention 7–90 days, access/restore proof and owner-approved RPO/RTO.
Include auth/role/IAM and schema/migration-ledger recovery in provider-specific
instructions. Object-store datasets need immutable manifests/checksums and
version/retention evidence. Never commit dumps, credentials or customer rows.

Managed-provider snapshot/PITR is the primary production backup mechanism.
A separately approved logical export can use `pg_dump --format=custom
--no-password --lock-wait-timeout=5s --file=PRIVATE_ARCHIVE`, with database
selection and credentials through a private libpq service/passfile or secret
environment; no password in shell arguments or Git. Use a client compatible
with the server and collect exit/warning evidence privately. Record scope,
timestamp, full release SHA, schema ledger, server/client major, archive size,
SHA-256, offsite locator and retention expiry. The safe local metadata check is:

```text
python scripts/backup_integrity.py --archive PRIVATE_ARCHIVE --scope production --release-commit FULL_SHA --postgres-major MAJOR --output PRIVATE_METADATA_JSON
```

The check does not contact a DB, parse every archive entry, prove offsite storage
or claim a successful restore. Verify archive listing with `pg_restore --list`
and perform a real rehearsal in a disposable/staging target. Do not restore
untrusted archives: restores execute source-defined code.
[PostgreSQL backup documentation](https://www.postgresql.org/docs/current/app-pgdump.html)
describes logical-export scope and this trust requirement.

Repository rehearsal:

```text
python scripts/postgres_recovery_drill.py --execute-disposable --output PRIVATE_LOCAL_RESULT_JSON
```

Requires a locally present PostgreSQL 16 image and a local Unix/named-pipe
Docker socket. Remote TCP/SSH contexts are rejected; the resolved socket is
pinned for every subsequent command. Resolves the image's immutable ID,
creates its own network-disabled container with memory/CPU/PID limits,
publishes no ports or host mounts, applies managed migrations plus a minimal
disposable Auth prerequisite, seeds synthetic rows/ledger, creates a custom
dump, checks hash/size/archive list, restores transactionally into a fresh DB,
checks rows/ledger/sequence/RLS/constraint inventory and actual FK/check
rejection. It removes only its own created container ID and temporary dump.
It accepts no external dump/hosted URL. A creation timeout triggers inspection
of only this run's random container name; cleanup requires its matching
run-specific ownership label. This does not validate production roles,
ACL restoration, real data volume, managed Auth service, offsite availability
or point-in-time recovery. Those remain explicit database-owner actions.

For a production-origin rehearsal, the database owner restores an approved
trusted snapshot into isolated staging, prevents app/provider dispatch and
outbound notification, validates table counts and scoped canaries, ledger,
RLS/roles/grants, application readiness and artifact compatibility, measures
recovery time/loss, then obtains recovery approval. No command in this branch
can restore a supplied production database URL.

## Rollback and incident decisions

Release owner records the current and candidate full frontend/backend SHAs,
immutable Vercel deployment IDs and backend image digests/revisions, actual
applied schema ledger and immutable artifact checksums before promotion.
Frontend and backend rollback are independent actions; verify each SHA and
the compatible pair. The offline verifier checks Git commit existence and
every registered migration hash. It refuses mutable refs, API mismatch,
schema-registry difference and missing/different artifacts. Backend runtime
API metadata must match the deployment manifest. Because there is no
release-bound frontend API contract, the local verifier additionally requires
identical frontend consumer trees. Changed frontend trees remain BLOCKED
pending separately reviewed compatibility evidence. Equal registry
does not prove the live applied ledger. Candidate artifact JSON maps bounded
names to SHA-256; the owner must verify these against real retained artifacts.

```text
python scripts/verify_rollback.py --current-frontend FULL_SHA --current-backend FULL_SHA --candidate-frontend FULL_PRIOR_SHA --candidate-backend FULL_PRIOR_SHA --current-artifacts PRIVATE_CURRENT_JSON --candidate-artifacts PRIVATE_PRIOR_JSON --output PRIVATE_ROLLBACK_RESULT_JSON
```

This is a read-only compatibility dry-run, not a deployment or hosted traffic
switch. A schema/artifact mismatch requires a reviewed recovery plan and staging
drill; no automatic down migration. Keep provider quotas, edge rules and kill
switches during rollback. A restarted worker has fresh local budgets.

| Incident | Owner / decision | Containment and recovery |
| --- | --- | --- |
| Runaway provider cost | billing + incident owners; SEV1 | preserve quota/spend evidence; disable affected capabilities and deny their edge routes across revisions; verify bounded unavailable state; restore one at a time after account-level review |
| Credential/provider failure | provider owner; SEV2 or SEV1 compromise | disable affected capability; verify status/error counters; owner repairs access in secret store under separate approval; do not widen IAM/quotas or print credentials |
| Backend outage | reliability owner; SEV2 | inspect passive health, DB and revision categories; choose compatible prior immutable backend; verify frontend contract and staging first |
| Corrupted/stale artifact | dataset owner; SEV2 | quarantine/disable dependent capability; preserve hash/vintage; select retained verified manifest; check schema/coverage/freshness before recovery |
| Bad release | release owner; SEV2 | freeze promotion; verify independent frontend/backend rollback plan, actual schema ledger and retained artifacts; staging drill then owner-authorized traffic switch |
| Database failure/data corruption | database + incident owners; SEV1/2 | enter maintenance, stop affected writes, preserve trusted backup/checkpoint; restore to isolated staging; validate rows/roles/ledger; owner approves recovery plan |
| Restore | database owner | use isolated rehearsal procedure above; record measured loss/time and independent validation; production recovery needs separate explicit approval |
| Emergency disable | incident owner | set `ANTI_ABUSE_<CAPABILITY>_DISABLED=true` for geocoding/places/routes/satellite/etc. across every active revision; use edge deny while rollout completes; already-running work may finish within its existing deadline |

`MAINTENANCE_MODE=true` is broader write containment, not a universal provider
kill switch: GET routes and background refresh workers require separate
review. Never use a restart to evade an exhausted budget. Recover by checking
account quotas, keys, read-only health, artifact/ledger integrity and approved
immutable release identity, then re-enable one capability under owner control.
