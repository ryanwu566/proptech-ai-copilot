# Professor server self-host preparation

Status: PREPARATION ONLY. No server, cloud, Render, DNS, push, or production
operation is authorized. Initial role: Option D, private research/staging and
recovery rehearsal. Production remains blocked by the existing fail-closed
Wave 1B contract.

Baseline: `0ac46365f35b01d5f13aed978a4eb3ddf00db670`.

## Design and implementation plan

**Goal:** Maintain a runnable private Ubuntu/Docker preparation package with
separate application and dedicated usage PostgreSQL 17 clusters, recoverable
backups, safe health checks, and local-only evidence.

**Architecture:** A private reverse proxy fronts FastAPI. FastAPI joins an
egress-capable application network and a separate internal usage network.
PostgreSQL services have no published ports and distinct named volumes. The
usage cluster contains only `proptech_api_usage` and its bounded subsystem
history. Redis is deferred; no unused running container is added.

**Tech stack:** Ubuntu LTS, Docker Engine/Compose v2, existing FastAPI build,
PostgreSQL 17 pinned by digest, TLS/SCRAM, Bash/Python operations tooling.

**Authority:** The user's attached 13-phase preparation request; this document
records implementation decisions, interfaces, validation, and limitations.

### Global constraints

- Preserve migration 021, its canonical LF checksum
  `00ed7d4b78de6d92c285ab8cd87241d1477bee2ce6e97caef6bbf6e2f43b98af`,
  `scripts/bootstrap_usage_database.py`, and the startup guard unchanged.
- Never use inherited legacy database URLs or real provider credentials in tests.
- No deployment, push, remote server/database access, DNS, or paid resources.
- Never log secrets, put them in arguments, or commit them. Actual secrets are
  operator-provided runtime mounts outside the checkout; examples are empty.
- No public database/cache/API binding, Docker socket in containers, privileged
  containers, host networking, wildcard CORS, or debug/production quota fallback.
- Default profile is private staging with production-like `APP_ENV=preview`.
- The usage bootstrap actor is `usage_migration`, not a `proptech_usage_*` role;
  it must be direct LOGIN CREATEROLE, database owner, NOSUPERUSER/NOBYPASSRLS.
- Bootstrap requires TLS explicitly. Provide PostgreSQL TLS rather than changing it.
- Stop on bootstrap/security refusal; no manual repair, forged history, or cleanup
  of an operator's database. Local test containers are uniquely scoped/disposable.

### Task 1: Compose, database boundary, runtime checks, local rehearsal

Files: `docker-compose.selfhost.yml`, `infra/selfhost/*`,
`scripts/ops/selfhost_*.py`, focused behavioral tests.

- [ ] Add a separate Compose bundle with `api`, `postgres_app`, `postgres_usage`,
  `reverse_proxy`, and an explicit `usage_ops` administrative profile. Reuse
  `Dockerfile.cloudrun` through a selfhost extension if a secret-loading entrypoint
  or non-root execution requires it. Existing Compose/Render behavior is untouched.
- [ ] Use PG17 digest already proven locally, distinct project-scoped named volumes,
  TLS, SCRAM, non-superuser runtime identities, bounded healthchecks, resources,
  rotated logs, dropped capabilities, no-new-privileges, and no published DB ports.
- [ ] Runtime secret files: `app_database_url`, `usage_database_url`,
  `usage_peer_hmac_key`, `pilot_session_signing_key`; database initialization and
  TLS mounts are specified in the Compose bundle. The app entrypoint maps only
  supported application variables. Bootstrap credentials never reach `api`.
- [ ] Preserve direct repository bootstrap execution. Add bounded read-only
  freshness checks and direct-runtime security/functional probes as needed.
- [ ] Write meaningful refusal/secret-redaction tests before operations code.
- [ ] Rehearse two real local disposable PG17 containers and the real FastAPI
  lifespan/HTTP health and readiness in preview mode; prove missing usage URL
  refuses startup. Block external Python/libpq connections; no paid providers.
- [ ] Keep the full application migration boundary explicit. Do not misrepresent
  a minimal startup fixture as a production application migration solution.

### Task 2: Backup, restore rehearsal, host health

Files: `scripts/ops/selfhost-backup.sh`,
`scripts/ops/selfhost-restore-rehearsal.sh`,
`scripts/ops/selfhost-health-check.sh`, behavioral tests as warranted.

- [ ] Compose interface: root `docker-compose.selfhost.yml`, services
  `postgres_app`/`postgres_usage`, databases `proptech_app`/`proptech_api_usage`.
  Run PostgreSQL utilities through local container Unix sockets as OS `postgres`.
- [ ] Backup entrypoint takes an explicit absolute output directory; timestamp+UUID
  exclusive directories, custom-format compressed dumps, separate role metadata
  without password hashes, checksums, manifest, non-secret config, success marker.
  Mandatory age encryption for operator backups; no plaintext archive persisted.
- [ ] No automatic pruning of backups or database DROP. Document 7 daily/4 weekly/
  12 monthly retention and deletion only after verified independent copies.
- [ ] Rehearsal must use only newly created UUID-named local containers and must
  never accept a real restore target or reuse the existing PG16 recovery drill
  which forges migration ledger fixtures. Test actual usage schema/history restore
  and runtime grants/RLS; no source target mutation except bounded reads.
- [ ] Host health uses bounded Compose/container metadata, HTTP checks, and host
  CPU/memory/disk/backup freshness; never dumps container environments or secrets.

### Task 3: Repository inventory, Ubuntu bootstrap, environment, cutover

Files: this maintained plan, `docs/operations/professor-server-bootstrap.md`,
`docs/operations/professor-server-cutover.md`, `.env.selfhost.example`.

- [ ] Inventory actual startup/env/database/migrations/backups/storage/workflows.
- [ ] Explain two-cluster recommendation accurately: freshness is database scoped,
  usage roles are cluster scoped, and the current procedure requires a dedicated
  instance. Do not claim the code rejects all other databases in a cluster.
- [ ] Prefer private Tailscale access plus loopback-only proxy initially; compare
  Tunnel and public HTTPS/NAT without enabling public ingress or changing DNS.
- [ ] Document idempotent Ubuntu bootstrap, key-only SSH only after second sudo
  login proof, UFW/fail2ban, official Docker apt installation, paths/ownership,
  runtime secrets outside git, safe startup, Wave 1B commands, backup timers.
- [ ] Example includes only supported runtime keys; mark infrastructure-only NEW
  keys explicitly. `ENVIRONMENT` is not an application switch unless evidence says so.
- [ ] Stage A-E entry, validation, rollback, ingress/DNS, sync, backup, monitoring;
  no automatic promotion, live-request shadow writes, or production snapshot reuse
  without permission and anonymization.
- [ ] Document GitHub scanning already present versus recommendations requiring
  repository/account configuration. Preserve release workflows in this task.

## Validation and release gate

- [ ] Database-free bootstrap plan, exact immutable checksum.
- [ ] Local PG17 bootstrap/security and focused regression suites.
- [ ] Compose config validation with dummy inputs, shell syntax checks, behavioral
  operations tests, local startup/restore rehearsals, repository hygiene/security
  checks, `git diff --check`; report skipped/unavailable checks explicitly.
- [ ] Independent security review and covering checks after fixes.
- [ ] Local commit only after verification, no push. Report actual clean/dirty state.

## Evidence and remaining gates

Baseline local evidence before implementation: 63 bootstrap/security tests and
99 relevant regressions passed using disposable PostgreSQL 17.10. The earlier
full suite was deliberately stopped when scope changed; it is not a pass.
The usage/backend/database/test paths matched authoritative main.

Actual professor hardware/architecture, OS release, storage capacity and external
drive identity, networking/CGNAT and institutional policy, available DNS/domain,
secret custody, backup destination, application database migration/auth integration,
and recovery time must be verified on the future server. None is certified here.

## Repository evidence inventory (preparation, 2026-10-16)

| Area | Observed repository contract | Consequence for self-hosting |
| --- | --- | --- |
| Backend entrypoint | `Dockerfile.cloudrun` and `render.yaml`: `uvicorn backend.api_main:app --host 0.0.0.0 --port ${PORT:-8080} --no-proxy-headers` (Render supplies `$PORT`) | Build the FastAPI image with a verified commit identity; internal port 8080. Preserve disabled proxy-header trust. |
| Other Docker entrypoint | Root `Dockerfile` runs Streamlit `app.py` on 8501; root `docker-compose.yml` publishes 8501 and mounts `./data` | Existing Compose is not the FastAPI deployment. Maintain separate `docker-compose.selfhost.yml`; do not overwrite it. |
| Runtime configuration | `services/production_config.py`: `APP_ENV=preview` or `production` is production-like; requires PostgreSQL URL, signing key >=32 characters, non-local explicit CORS origins and public-app base URL; malformed metrics token also refuses | Preview is the initial safe mode. `ENVIRONMENT` is not an application switch. `APP_RUNTIME=standard` avoids serverless assumptions. No debug switch is added. |
| Application persistence | `DATABASE_URL` takes precedence over compatibility `PILOT_EVIDENCE_DATABASE_URL`; `backend/db.py` probes PostgreSQL with SELECT 1 in production-like mode; development uses local SQLite | Use a fresh `proptech_app` URL with a dedicated runtime login. Never inherit an inspected legacy URL; never use SQLite to claim production durability. |
| Other database boundaries | `VALUATION_DATABASE_URL`, `COMPACT_GREEN_DATABASE_URL`; `services/vnext/db_principal.py` requires `VNEXT_DATABASE_URL` and direct `vnext_api` authentication without fallback | Read models/Auth need separate review. Leaving optional data sources empty means capabilities may be unavailable. Do not redirect them to usage DB. |
| Wave 1B startup | FastAPI lifespan calls `validate_usage_startup()` and `start_usage_ledger()`; `usage_guard.py`, `usage_principal.py`, `usage_ledger.py` | PostgreSQL guard and valid 64-hex peer HMAC are mandatory in preview/production. Keep `API_USAGE_LEDGER_REQUIRED=true`; required writer failure refuses startup. No local quota fallback. |
| Usage runtime authority | Guard inspects current/session/reachable roles; rejects superuser, BYPASSRLS, executor, ownership, CREATE, role admin and predefined unsafe roles | Runtime is direct `proptech_usage_runtime_v1`, guard/writer only, SET/ADMIN false; never use admin or simulated SET ROLE. |
| PostgreSQL connection | `services/postgres_runtime.py` bounds connection timeout and uses `POSTGRES_SSLMODE`; bootstrap explicitly uses `sslmode=require` | PG17 servers must provide TLS. Runtime uses verify-full and trusted CA; bootstrap's existing require behavior stays unchanged. |
| Host/origin security | `production_guardrails.py`, `backend/api/ingress_middleware.py` enforce exact allowed Host and Origin; hide docs/OpenAPI in preview/production | Preserve Host through proxy. Explicit private DNS hostname, explicit CORS origins; no wildcard or proxy-header relaxation. CORS is not authentication. |
| Abuse admission | `production_guardrails.py` accepts only existing `ANTI_ABUSE_ENFORCEMENT_MODE=local_only`; usage PG guard is a separate durable boundary | Do not invent Redis/distributed admission support. Redis remains a deferred design placeholder without service/port. |
| Liveness | `/liveness` returns status; `/health` also reports persistence/readiness categories | A 200 from `/health` alone does not prove readiness; inspect the readiness category. |
| Readiness | `backend/api/routes_pilot.py`: `/readiness` aliases `/pilot/readiness`, checks app DB connection and runtime config; returns 503 on missing production prerequisites | Monitor both endpoints and independent usage runtime guard/writer probes; these HTTP endpoints do not continuously re-audit usage DB permissions. |
| Release identity | `/release-version` includes backend build identity and bounded release/config metadata; `/compatibility` reports API contract | Capture expected exact SHA and contract, without treating declared schema version as a migration audit. |
| Migration model | `database/migration_registry.json`, `scripts/migration_registry.py` verify canonical LF checksums; global runner imports registered `production_runner` chain including 021, maintains `public.schema_migration_ledger` and verifies VNext objects | Never target usage with global runner. No supported skip-021/cutoff flag exists; no manual ledger rows or ad hoc SQL subset is proposed. |
| Application Auth dependency | Migration 013 explicitly requires `auth.users` and `auth.uid()`; 020 references/backfills `auth.users`; `services/vnext/auth.py` verifies Supabase RS256/ES256 JWT/JWKS | Plain PostgreSQL is not a self-contained Supabase/Auth migration. Full application initialization/auth portability is an unresolved release gate. A fresh empty app DB can pass SELECT 1 but does not prove business routes are migrated. |
| Existing backup tooling | `backup_pilot_evidence.py`/`restore_pilot_evidence.py` are local SQLite only and refuse production mode; `backup_integrity.py` checks archive metadata/hash without restoring | Add separate selfhost PG17 backups, independently rehearse recovery. Integrity/hash is not recovery proof. |
| Existing recovery CI | `production-release-ops.yml` runs PG16 migration/recovery contracts; `postgres_recovery_drill.py` is a synthetic disposable drill | PG16 CI is not Wave 1B PG17 or actual-data recovery certification; new rehearsal must preserve real usage schema/history and permissions. |
| Existing release CI | `release-quality.yml`, `production-release-ops.yml`: Python suite, frontend build, release/ops gates, smoke and browser jobs; hosted smoke/identity workflows also exist | Workflow existence is not evidence that current revision or deployed production passed. Do not trigger hosted jobs during preparation. |
| Existing security CI | `security-performance.yml`: locked npm install/audit + exception gate, Python tests, repository hygiene, SBOM generation, pip-audit; actions use read-only contents permissions | Retain workflows. No CodeQL workflow, Dependabot config or dedicated secret-scanner config found. GitHub account-level secret scanning/push protection status is unknown. Recommend separately enabling/checking them, with no settings change now. |

### Storage and provider inventory

Local `data/` contains SQLite/demo and processed artifacts; the Streamlit Compose
mount is not a complete backend storage contract. New API root is read-only with
bounded temporary writable storage; do not mount an entire writable checkout or
assume every import/data-processing script belongs in the API process. Research
processing should run separately under resource limits, use staged input and
write to its own reviewed paths.

`services/provider_config_contract.py`, `wra_flood_runtime.py`,
`gsmma_geological_sensitivity_runtime.py` and `nlsc_village_boundary_runtime.py`
use R2 endpoint/access/secret/bucket/region plus versioned object references or
local NLSC artifact path/checksum/vintage/provenance. Preserve current R2 as the
source; empty credentials are intentional for local rehearsals. Capacity,
licenses, consistency, access scope and recovery of local caches/artifacts still
need inventory on the real host.

Google Geocoding/Places/Routes adapters use server-only `GOOGLE_MAPS_API_KEY`;
frontend browser Maps key remains a separate frontend build setting. Earth Engine
requires explicit feature flag, project and Application Default Credentials.
TGOS uses app ID/API key; TDX uses client ID/secret and the commute refresh token.
NLSC uses HTTPS gateway URL/client token; verify actual Taiwan fixed-IP residency
and provider enrollment rather than inferring it from URL syntax. Taipei planning
supports `manual_evidence` and an off-by-default feature. Some official sources
have no credential; that does not mean network or paid calls are authorized.
Private/shadow rehearsals use reviewed fixtures and disabled optional providers.

Auth configuration comes from `SUPABASE_URL` or explicit issuer plus audience;
JWKS verification does not provision the referenced Auth tables. Pilot signing,
admin/reviewer tokens, VNext authentication and provider credentials have distinct
purposes and must not be shared. The `.env.selfhost.example` inventories supported
keys and explicitly marks new infrastructure-only inputs. Optional secret-bearing
provider keys remain empty until scoped mounts/configuration are separately
reviewed; the initial API consumes only its four supported runtime secret mounts.

### Why two PostgreSQL 17 clusters

Use `postgres_app` and `postgres_usage`. The hosted closure procedure expressly
requires a new dedicated usage instance. Bootstrap `_fresh()` checks the current
database for unrelated schemas/objects/ACLs/extensions and checks the cluster-wide
catalog for `proptech_usage_*` roles. It does **not** scan or prohibit every other
database in the cluster. A carefully prepared single cluster might pass these
particular checks if usage roles do not exist, but shared role administration and
future usage-role collisions would violate the intended dedicated-instance
operating boundary. Two containers provide distinct role catalogs and volumes
without another cloud purchase; a host/disk failure still affects both.

| Purpose | Administration/migration | Runtime / ownership | Persistence/access/backup |
| --- | --- | --- | --- |
| App: `proptech_app` on `postgres_app` | `postgres` local bootstrap administrator; `app_migration` database owner, NOLOGIN; full migration/Auth path gated pending review | `app_runtime` LOGIN, NOSUPERUSER/NOCREATEROLE/NOCREATEDB/NOBYPASSRLS, no ownership; only reviewed app object grants added with migrations | Distinct named app volume; TLS5432 only on private app network; database dump + password-free role metadata |
| Usage: `proptech_api_usage` on `postgres_usage` | `postgres` local bootstrap administrator; direct `usage_migration` LOGIN, CREATEROLE, NOSUPERUSER/NOBYPASSRLS/NOREPLICATION, DB owner; not named `proptech_usage_*` | `proptech_usage_runtime_v1` guard/writer only; schemas/tables/history owned by migration actor; consume/prune functions owned by NOLOGIN executor; six tables ENABLE/FORCE RLS | Distinct named usage volume; TLS5432 only on internal usage network; full DB dump including actual 021 history + password-free role metadata |

No 5432/6379 or API port is published. A reverse proxy publishes only
`127.0.0.1:8080`. Networks separate app/egress from internal usage connectivity;
containers have explicit healthchecks/restart/resource/log bounds. There is no
Docker socket, privileged container or host network. Administrative `usage_ops`
is an explicit profile, with bootstrap credentials and its usage_runtime_password
mount absent from `api`. A separate audited activate-runtime operation grants
CONNECT and installs the runtime SCRAM credential; original bootstrap/provisioner
remain unchanged.

### Ingress decision

| Option | Suitability | Conditions before later use |
| --- | --- | --- |
| Private Tailscale + SSH forwarding/Serve | Initial Option D; enrolled identities and tailnet ACLs, no router/NAT opening; loopback proxy stays private | Review institutional policy/account custody and ACLs; no Funnel. SSH forwarding needs no public web listener. Private Serve requires authenticated tailnet access and an explicit hostname/Host review. |
| Cloudflare Tunnel | Later public API behind outbound tunnel; avoids inbound router forwarding/CGNAT issues | Separate domain/account approval, scoped tunnel credential, origin restrictions, API authentication, header/peer identity design, health and rollback gates; no tunnel or DNS created now. |
| Caddy/Nginx HTTPS + NAT | Later direct ingress with certificate automation and operational control | Stable reachable IP, institution/router authorization, reviewed NAT, only80/443 firewall openings, TLS renewal and origin protections; unsuitable if CGNAT blocks incoming traffic. |

[Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) is private
to the tailnet; [Funnel](https://tailscale.com/docs/features/tailscale-funnel)
exposes a service publicly and is excluded initially. Transport-peer HMAC currently
sees the proxy peer because Uvicorn ignores forwarding headers: multiple users
can share an anonymous quota principal. Preserve this safe existing behavior;
review authenticated identity and proxy trust before public/multi-user promotion.
Do not claim per-client ingress quota identity has been solved.

### Backup and observability operating policy

Daily full logical dumps of both PG17 databases, password-free roles, reviewed
allowlisted Compose/infra files, safe enumerated runtime flags, build/release
identifiers and SHA256 manifests
are stored in an exclusive UTC timestamp+UUID backup directory. age encryption is
mandatory for operator backups; keys live separately. Never overwrite/prune the
only good copy. Retain 7 daily/4 weekly/12 monthly recovery points as a policy,
with manual expiration only after verified independent copies and successful
restore rehearsals. Logical dumps from two databases are separate snapshots:
quiesce schema/role/administrative changes while capturing catalog, roles and
dumps. Ordinary application writes may continue within each per-database consistent
dump snapshot; the catalog fingerprint excludes mutable row counts. The four
archives have no atomic cross-database snapshot or PITR. Cross-database invariants
or cutover checkpoints require a reviewed consistent export/write-freeze plan. Restoring quota state also needs a policy for already spent quotas,
telemetry loss and any paused in-flight requests before pilot/production.

Copy encrypted immutable backup directories to a mounted, positively identified
external disk using non-deleting `rsync --ignore-existing` or equivalent; verify
checksums there, unmount and store separately. Optional R2 protection uses
`rclone copy` to a versioned new destination and `rclone check`, never `sync
--delete` and never edits source objects. Encrypted secret/config recovery copies
must be stored separately from recipient private keys; database password hashes
are intentionally excluded from roles dumps, so recovery must reprovision
credentials securely. A dump proves backup creation; an isolated restore with
real grants/RLS provides bounded recovery evidence. The supplied rehearsal has
512 MiB PGDATA per disposable target and a 64 MiB total encrypted-input limit:
it proves small-fixture recovery, not production-scale recovery/RTO. Its direct
runtime LOGIN uses isolated local trust, proving identity/authorization without
proving restored password/SCRAM authentication. Real operator data recovery
remains unperformed. Hostnames, CORS and other free-form runtime/operator config
are excluded from metadata; recover them from a separately encrypted operator
package with separate key custody.

Initial monitoring is a host systemd timer running `selfhost-health-check.sh`:
container health/restarts, bounded HTTP readiness, PostgreSQL readiness, disk,
CPU, memory and completed-backup staleness. A bounded read-only helper checks
usage guard and writer privileges/RLS plus actual HTTP readiness; revoked writer
grants cause health refusal without writes. Root/operator host access reads Docker
metadata; no socket is mounted into apps. Logs are bounded and private. Establish
an operator notification path and test a failure before accepting traffic. No
public dashboard is created. Uptime Kuma or node_exporter/Prometheus/Grafana can
be added only after an actual operational need and private access design exist.

### Promotion gates and limits of evidence

The [bootstrap runbook](professor-server-bootstrap.md) gives future Ubuntu and
Wave 1B commands; the [cutover runbook](professor-server-cutover.md) defines
stages A-E. All future host commands require a separately authorized server
session. No step authorizes Render access/configuration, production deployment,
DNS changes, paid resources or real-provider shadow requests.

Full application schema migration/Auth portability, real provider credentials,
hardware architecture, SSD health/capacity, UPS/power recovery, external drive
identity, kernel/rootless compatibility, institutional networking/CGNAT policy,
private ingress account/ACLs, backup custody/offsite copy, recipient-key recovery,
server egress, operational alerting and measured RPO/RTO remain actual-server or
separate design gates. Digest architecture availability must be checked before
builds. A local preview startup and healthy SELECT1 on an empty app DB prove
startup connectivity only. Neither that nor synthetic recovery certifies a
working migrated production application, hosted provider compatibility or a
successful real recovery.

### Validation evidence ownership

This inventory/documentation task did not execute host installation, remote
connections, real backups or production operations. Final local Compose,
Wave1B/startup/restore/test/security results are recorded by the integration task
only after commands complete. Checklist items above are planning/verification
gates, not proof that a remote host or full application migration has passed.
The existing base `Dockerfile.cloudrun` inherits `python:3.12-slim`; selfhost
references its reviewed locally built named tag@sha256:digest, but that is not a claim
that all upstream base-image tags are pinned by source digest. Review/rebuild and
scan pinned source images as a later supply-chain improvement.

### Final local preparation evidence ??2026-10-16

Local preparation validated; **PRODUCTION_NO_GO**. Integration-owned final
Compose rehearsal `1353a5632cf3` passed using unique API/ops image tags, two
private TLS PostgreSQL17 clusters and loopback Nginx HTTP. It proved actual
Wave1B bootstrap, direct runtime startup, read-only health refusal after writer
grants were revoked and health recovery after grants were restored, actual
FastAPI lifespan refusal without the usage URL, verify-full TLS success and
cleartext PostgreSQL refusal. Cleanup verified zero remaining owned containers,
networks, volumes or unique image tags.

Final encrypted small-fixture backup/restore passed after mutable row counts
were removed from the catalog fingerprint. A separate assertion checked exact
nonempty seeded quota rows restored. Restored runtime LOGIN used isolated local
trust authentication: role identity/authorization passed, password/SCRAM custody
was not certified. The documented 512 MiB target/64 MiB encrypted-input limits remain.

Final new Windows combined tests: 33 passed / 3 skipped (18 runtime and 18 backup
cases; two Windows platform skips and one PostgreSQL opt-in skip). Linux backup
tests: 17 passed / 1 PostgreSQL-opt-in skipped. The repository-owned PG17 harness
executed the opt-in fingerprint insertion node: 1 passed / 80 deselected in 3.20s;
Linux/opt-in runs cover the three Windows skips. Fresh existing bootstrap/security
suite: 63 passed in 88.15s. Focused existing regressions: 99 passed in 19.35s after
an earlier 98-pass/1 advisory-lock-timeout under parallel build load. The failure
did not reproduce; no tests, guards, timeouts or retry behavior changed. An earlier
interrupted full suite remains unclaimed.

Independent operations second-round review and core whole-branch source review
approved the source with no Critical/Important findings remaining. Reviewer
conditions for the final rehearsal and executable shell modes were met. Targeted
`.gitattributes` rules preserve LF for infrastructure/operations shell scripts.
Local commit and final repository hygiene/operations/shell checks remain owned by
the integrating agent and are reported in the final report; this document is not
a claim that those last checks or a commit already completed.

No professor-server or production connection, Render/configuration change,
production deployment, DNS change, cloud database/resource creation or push was
performed. Actual hardware/network/private storage, full application/Auth
migration, real credentials/providers and production-scale recovery remain future
gates. Empty-app-database readiness proves connectivity, not migrated business
features or production readiness.
