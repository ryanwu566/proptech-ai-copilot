# Professor-server staged cutover (proposal only)

Current state: **Stage A preparation; production NO_GO.** The current Render
backend remains fail-closed without a valid dedicated usage URL. No production
cutover, Render configuration change, public exposure, remote server access,
resource creation, DNS change or push is authorized by this package.

Cloud production and professor staging remain separate. Preserve immutable
reviewed source/build identities and existing Wave 1B controls at every stage.
Advancement requires a separately authorized operation and recorded acceptance;
no automation promotes a stage or falls back to local quota enforcement.

## Stage A: private staging / research / recovery rehearsal

**Entry:** Actual hardware/Ubuntu/network/storage/ownership inventory complete;
verified SSH recovery path, non-root sudo operator, approved private tailnet ACLs,
Docker/TLS/secrets configured. Empty named PG17 volumes and fresh dedicated usage
instance confirmed. Bootstrapping immutable021 and direct runtime provisioning
pass; runtime password installed securely. App schema/Auth migration design
remains an explicit gate for business features.

**Ingress/DNS:** Private Tailscale Serve HTTPS to loopback proxy8080; exact actual
private hostname/allowed origins. Funnel is public and excluded. No router/NAT,
public80/443, database/cache/API publication, public DNS or Vercel/Render change.
Use private staging clients only; Vercel production cannot reach this private API
and must not be repointed to it. Initial researcher diagnostics may use SSH
forwarding over the private tailnet.

**Data/sync:** New independent `proptech_app`/`proptech_api_usage`. Fixtures or
approved anonymized copies only; no legacy connection or automatic production
sync. Preserve R2 authoritative source; scoped read-only copies need separate
permission and provenance/checksum inventory. Research writers/processors use
separate paths/resources and cannot mutate production. Provider flags/credentials
stay disabled; exercise reviewed mocks/fixtures only.

**Validate:** Direct runtime guard/writer probes, FastAPI lifespan, liveness,
health-body readiness, readiness503 refusal, release identity, Host/Origin
rejection, TLS verification and non-public port inspection. Rehearse missing
usage URL startup refusal. Connectivity/SELECT1 with an empty app DB does not
certify migrations or product routes. Maintain per-check evidence and limitations.

**Backup/monitor:** Daily encrypted dumps/roles/config/manifest; independent
physical/offsite copies and disposable PG17 restoration preserving actual usage
history/RLS/grants. Host health timer checks CPU/memory/disk, all container
health/restarts, PG/API status and backup staleness. Test notification and a
cold-boot secret recovery before relying on unattended restarts.

**Rollback:** Stop private API/proxy; disable private Serve access or its tailnet
ACL. Preserve data volumes, backups and logs for diagnosis. Keep cloud resources
unchanged. Never `down -v`, DROP or weaken the usage guard as rollback.

## Stage B: isolated shadow backend

**Entry:** Stage A accepted, measured stable resource usage and verified backup
recovery. Full required app schema/Auth model has been reviewed and rehearsed;
required capability dependencies and identity/data boundaries are understood.
Define comparison cases and acceptance thresholds before collecting results.

**Ingress/DNS:** Keep private ingress and separate staging clients; no public
DNS/production frontend switch. Explicitly identify test release and data vintage.

**Data/sync:** Compare only sanitized captured fixtures/replayed read inputs or
controlled test cases. Do not automatically duplicate live requests, provider
calls, outbound notifications, billable Google/EE calls, account/evidence writes
or refresh/import jobs. A GET can still consume durable quota/telemetry or call a
provider; method alone does not make shadow traffic side-effect-free. Capture
outputs under a separate shadow identity and fresh quota namespace/database.
Use approved snapshots with provenance, never a live bidirectional sync.

**Validate:** Compare deterministic normalized outputs/latency/error contracts;
record expected differences due to data vintage. Verify disabled external dispatch,
private authentication and resource isolation under bounded representative load.
Do not infer public-ingress readiness from a private comparison.

**Backup/monitor:** Same backup requirements as A plus recovery of the exact
shadow release/data checkpoint; resource and backup alerts operational. Track
usage-ledger availability and quota behavior separately from app readiness.

**Rollback:** Stop shadow jobs/clients and remove their private route/ACL; retain
comparison evidence and isolated data. Production request path remains unchanged.

## Stage C: limited pilot traffic

**Entry:** Separately approved named pilot cohort/data policy and traffic limit;
full required application/Auth/read-model migrations proven, secure credential
custody, realistic restore drill and agreed RPO/RTO. Resolve proxy peer identity:
`--no-proxy-headers` currently groups anonymous clients behind the proxy; do not
invent a trusted-proxy env switch or trust arbitrary forwarding headers. Test
actual authenticated identities and quotas before more than a private operator.

**Ingress/DNS:** Prefer private enrolled pilot users initially. If public ingress
is separately approved, select scoped Cloudflare Tunnel or Caddy HTTPS/NAT after
institution/CGNAT/domain/TLS review; require authentication/origin protection and
an exact allowlist. Vercel pilot environment gets its own reviewed API base URL;
production frontend/Render/DNS remain unchanged unless separately authorized.

**Data/sync:** Explicit single writer for each pilot scope. Use separately approved
sanitized seed data, record source checkpoint, and prohibit writes/sync back into
legacy production. Enable each provider only with scoped credentials, cost caps,
quotas and approval; do not enable production imports/cron by accident. Pilot
usage is independent of cloud usage; document that per-instance scopes do not
create a shared cross-system provider cost ceiling.

**Validate:** Pilot acceptance scenarios, protected write authorization, actual
end-to-end business persistence, quota rejection/idempotency and provider error
handling under bounded load; verify exact SHA/contract and TLS/header behavior.
Set a time-bound observation window and numerical rollback thresholds with the
operator before admitting users.

**Backup/monitor:** Encrypted pre-pilot checkpoint, daily verified generation,
independent copy, recovery of pilot writes measured. Notify operator on failed
readiness, required usage sink, restart loops, disk pressure or stale backup;
record latency/error and provider-cost observations without secrets/PII in logs.

**Rollback:** Pause pilot writes, remove pilot route or switch only the pilot
frontend back to its accepted environment. Export/reconcile pilot records under
an approved plan before any later reimport; preserve the original pilot database.
No automatic overwrite of cloud production and no loss of accepted writes.

## Stage D: production candidate

**Entry:** Pilot acceptance, actual-host stability/security review, full migration
provenance and Auth continuity, external-provider and R2 dependency validation,
backup-key recovery, off-host copy, real restoration and capacity/UPS/reboot
behavior verified. Independently resolve legacy migration drift in its own
approved task. Define operational owner, support window, recovery destination,
RPO/RTO, DNS TTL/ingress change and rollback thresholds explicitly.

**Ingress/DNS:** Prepare the exact later-approved domain/certificate/tunnel/NAT
and Vercel configuration diff offline. Verify ownership/TLS renewal/health and
origin protection on a separate candidate hostname. No production DNS switch in
this stage without separate authorization. Avoid public monitoring/admin surfaces.

**Data/sync:** Document complete scope: app/Auth/accounts/evidence, read models,
versioned R2/local artifacts, usage quotas/history and secrets. Choose one writer,
record cut-off timestamp and checkpoints, test final bounded incremental sync or
write-freeze export/import. Reconcile row counts/integrity/provenance; prove no
ledger fabrication or duplicate side effects. Decide how quotas already spent on
cloud transfer without resetting budget. A rollback to stale usage state must
not enable overspending. Rehearse the exact data move before scheduling cutover.

**Validate:** Candidate business scenarios, load/resource envelope, restart,
private/public ingress isolation and certificate renewal as applicable, credential
rotation and guard refusal. Perform an independent security review and recovery
rehearsal using the final release and representative approved data.

**Backup/monitor:** Verified pre-cutover encrypted checkpoint, two independent
copies including physical disk; measured recovery on an independent target.
Alerts and operator handover tested. Retain cloud reference configuration and
known-compatible immutable images without purchasing another database.

**Rollback:** Rehearse removing candidate ingress/config without touching
production. If migration rehearsal writes exist, preserve them; never replay
stale snapshots over production. Post-write reversal needs an approved data
reconciliation path, not a DNS-only promise.

## Stage E: primary backend (not authorized)

**Entry:** Separate production change approval for exact SHA/config/ingress/data
plan and maintenance window; all D gates signed off by operational owner. Confirm
there is an accepted rollback destination: current fail-closed Render is not a
healthy fallback until its dedicated usage requirement is independently solved.
No fallback may bypass Wave 1B or purchase a DB without authorization.

**Ingress/DNS:** Execute only approved ingress/Vercel/DNS changes in the reviewed
order, monitor propagation and exact release identity. Retain old configuration
for reversal. Only approved public80/443/tunnel ingress; databases/cache/internal
API remain unpublished. Do not route arbitrary traffic directly to app containers.

**Data/sync:** Freeze agreed writers, take final backup/checkpoint, transfer only
approved deltas and verify integrity before single-writer promotion. Prevent old
cloud cron/background writes. Establish new backup authority and R2 continuity;
record actual accepted-write/usage checkpoints and recovery implications.

**Validate:** Immediate business/auth/readiness/guard/telemetry/release smoke,
quota and provider caps; bounded observation against predeclared thresholds.
Track actual requests/errors/latency, CPU/memory/disk/restarts, backup completion
and required usage-store availability. Observe for the agreed recovery window
before retiring any old path; decommissioning is a separate authorization.

**Backup/monitor:** Daily encrypted recovery points plus final pre-switch point,
independent off-host/physical copies, recurring restoration and key-recovery
drills, tested alerts and a named on-call operator.

**Rollback:** Stop admission/writers first; preserve every accepted write and
quota checkpoint. Switch only to a verified compatible destination after the
approved reconciliation/replay plan. Reverse the exact ingress/frontend/DNS diff
and monitor caches/TTL. Never restore over the only good copy or roll back the
security boundary to make startup green. If no consistent safe rollback exists,
enter maintenance/read-only mode and execute the approved recovery plan.
