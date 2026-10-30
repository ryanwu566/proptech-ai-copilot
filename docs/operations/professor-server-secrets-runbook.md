# Professor Server Stage 2: secrets and runtime configuration

**Stage 2 is COMPLETE for the current Professor Server local profile.** The
operator completed activation run `20261029T114148Z-b7ae118d6efa` with exit 0;
final acceptance verifies the successful root-owned sanitized receipts and fresh
nonprivileged live checks. Stage 1 remains complete.

The active API image is
`sha256:035a049691b0038f7508acc00c3e9bb82c101a295c9f45edcea8d1b03b3d42a0`, built
from committed application source `d8a93492eb900550ce490990fade7726766b18da`.
The final Stage 2 commit records the reviewed operator tools and acceptance; it
does not change that accepted runtime build identity.

Private evidence:
`/var/backups/proptech-selfhost/stage2-activation/20261029T114148Z-b7ae118d6efa`.
Sanitized operator receipt:
`/tmp/professor-stage2-activation-1a7f601581fe4939a107cfe6b6d33d29`.
The complete value-free snapshot, original receipt hashes and final assertions
are retained in
[`final-activation-evidence.json`](../../reports/professor-stage2-secrets/final-activation-evidence.json);
[`acceptance.json`](../../reports/professor-stage2-secrets/acceptance.json) is the
current machine-readable status.

Do not rerun secret installation or activation for this accepted runtime.
The agent did not use sudo, open credential values, rebuild images, activate
services or enable providers during final acceptance. No public ingress or
production/frontend migration acceptance is implied.

**Never paste a key into Codex. Never put a key in a shell command, Compose
interpolation, an environment template, a Git file, a Docker build argument or
logs. Never touch `/dev/sda`.** No DNS/Vercel/Cloud Run/Render/GitHub change,
public port, ML work or frontend migration is part of this preparation.

## Inventory and current requirements

The authoritative value-free inventory is
[`config/professor-server-credentials.json`](../../config/professor-server-credentials.json).
It includes credential/public/unsupported identifiers, source references,
conditional requirements, side, purpose, Stage 1 need and retirement disposition.
Its supplementary configuration inventory lists nonsecret provider guards,
artifact paths/endpoints, release settings and operator identifiers without values.
The host metadata audit confirms the existing secret parent is `root:root`, mode `0700` and
compose/runtime env files are root-owned, mode `0640`. The successful operator host validator and post-activation mount metadata
confirm the required file permissions and staged inode identities; the agent
has not opened credential contents.

No new external API credential is required to preserve the current local data
runtime. The five API files and four PostgreSQL initialization files are
preserved in the protected persistent store. Do not regenerate existing URLs, HMAC or session keys. Credential rotation
is a separate coordinated operation; merely changing a URL does not rotate a DB
role password.

| Variable | Provider | Requirement / side | Stage 1 need | Purpose | Retirement |
|---|---|---|---|---|---|
| `ADMIN_DATABASE_URL` | Conditional PostgreSQL runtime | conditional / backend | no | Dedicated Admin principal,never use owner/serving URL | keep_if_consumer_retained |
| `ADMIN_USAGE_DATABASE_URL` | Conditional PostgreSQL runtime | conditional / backend | no | Dedicated Admin usage-plane principal | keep_if_consumer_retained |
| `API_USAGE_BOOTSTRAP_DATABASE_URL` | Restricted PostgreSQL operations | operations_only / operations | no | Usage migration/bootstrap only | keep_if_consumer_retained |
| `API_USAGE_DATABASE_URL` | Professor PostgreSQL / runtime | required / backend | yes | Dedicated usage writer/quota connection | keep_local_runtime |
| `API_USAGE_PEER_HMAC_KEY` | Professor PostgreSQL / runtime | required / backend | yes | Anonymous usage-principal HMAC; exactly64hex | keep_local_runtime |
| `CLOUDFLARE_API_TOKEN` | Future hosting administration | operations_only / operations | no | No ordinary application runtime consumer; do not transfer/retire active cloud credentials yet | later_decommission_review_only |
| `CLOUDFLARE_TUNNEL_TOKEN` | Future hosting administration | operations_only / operations | no | No ordinary application runtime consumer; do not transfer/retire active cloud credentials yet | later_decommission_review_only |
| `COMMUTE_REFRESH_TOKEN` | Protected commute operations | operations_only / operations | no | Authorization for explicit manual refresh; do not mount in local profile | keep_if_consumer_retained |
| `COMPACT_GREEN_DATABASE_URL` | Conditional PostgreSQL runtime | conditional / backend | no | Optional GREEN valuation backend; local BLUE active | keep_if_consumer_retained |
| `DATABASE_URL` | Professor PostgreSQL / runtime | required / backend | yes | Local app/RIS runtime connection | keep_local_runtime |
| `DB_ACTOR_PASSWORD` | PostgreSQL initialization | operations_only / operations | no | Initializer-only transient environment from mounted role password | never_mount_in_api |
| `EARTH_ENGINE_PROJECT` | Earth Engine | conditional / backend | no | Project identifier; satellite remains disabled | keep_if_consumer_retained |
| `GCP_SERVICE_ACCOUNT_KEY` | Future hosting administration | operations_only / operations | no | No ordinary application runtime consumer; do not transfer/retire active cloud credentials yet | later_decommission_review_only |
| `GOOGLE_APPLICATION_CREDENTIALS` | Earth Engine / Google ADC | conditional / backend | no | Path to a mounted service-account JSON; credential content is stored as a file | keep_if_consumer_retained |
| `GOOGLE_MAPS_API_KEY` | Google Maps/Places/Routes | conditional / backend | no | Server Geocoding,Places,Routes; shared existing provider interface | keep_if_consumer_retained |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Legacy bundle sentinel | conditional / backend | no | No runtime consumer; do not use inline JSON | do_not_install_inline_alias |
| `MARKET_READ_MODEL_REFRESH_TOKEN` | Protected Market operations | operations_only / operations | no | Explicit maintenance authorization; market_ops remains disabled | keep_if_consumer_retained |
| `METRICS_SCRAPE_TOKEN` | Restricted application operations | conditional / backend | no | Authenticated metrics scrape | keep_if_consumer_retained |
| `NEXT_PUBLIC_API_BASE_URL` | Browser API routing | conditional / frontend | no | Public backend URL; no credential | keep_if_consumer_retained |
| `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY` | Google Maps JavaScript/Street View | conditional / frontend | no | Separate restricted browser key; never reuse server key | keep_if_consumer_retained |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase browser Auth | conditional / frontend | no | Publishable browser credential; RLS/verified JWT remain mandatory | keep_if_consumer_retained |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase browser Auth | conditional / frontend | no | Browser Auth project origin | keep_if_consumer_retained |
| `NLSC_GATEWAY_BASE_URL` | NLSC remote gateway | conditional / backend | no | Remote gateway origin; absent in local mode | keep_if_consumer_retained |
| `NLSC_GATEWAY_CLIENT_TOKEN` | NLSC remote gateway | conditional / backend | no | Authenticated remote gateway; local NLSC→RIS does not use this | retire_if_gateway_consumers_removed |
| `OPENAI_API_KEY` | Optional explanation placeholder | conditional / backend | no | Current LLM service is deterministic template-only; no external API call | do_not_mount_while_no_live_consumer |
| `PGSSLROOTCERT` | PostgreSQL TLS | required / backend | yes | CA file path; reconstructed fixed at startup | keep_local_runtime |
| `PILOT_ADMIN_TOKEN` | Restricted application operations | conditional / backend | no | Pilot administrator bootstrap | keep_if_consumer_retained |
| `PILOT_EVIDENCE_DATABASE_URL` | Legacy app DB alias | conditional / backend | no | Compatibility alias; Professor startup refuses inherited alias | retire_alias_after_other_deployments_migrate |
| `PILOT_REVIEW_TOKEN` | Restricted application operations | conditional / backend | no | Pilot reviewer bootstrap | keep_if_consumer_retained |
| `PILOT_SESSION_SIGNING_KEY` | Professor PostgreSQL / runtime | required / backend | yes | Pilot scoped-session signing; preserve existing | keep_local_runtime |
| `PLVR_DRY_RUN_DATABASE_URL` | Restricted PostgreSQL operations | operations_only / operations | no | Disposable import rehearsal only | keep_if_consumer_retained |
| `PLVR_UPDATE_DATABASE_URL` | Restricted PostgreSQL operations | operations_only / operations | no | Dedicated official importer writer only | keep_if_consumer_retained |
| `POSTGRES_PASSWORD` | PostgreSQL image | never_in_api / database_only | no | Plaintext admin-password alternative forbidden; file reference is used instead. | do_not_install_plaintext_alias |
| `POSTGRES_PASSWORD_FILE` | PostgreSQL image | required / backend | yes | Per-service admin password path for existing DB containers | keep_until_reviewed_init_mount_retirement |
| `PRODUCTION_SMOKE_TOKEN` | Acceptance operator/CI | operations_only / operations | no | Short-lived smoke identity; not a server startup credential | expire_after_acceptance |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 | conditional / backend | no | Remote artifacts/archive writer only; NLSC/WRA are local | retire_runtime_after_all_remote_consumers_migrate |
| `R2_BUCKET` | Cloudflare R2 | conditional / backend | no | Remote storage coordinates; no credential for local mode | retire_runtime_after_all_remote_consumers_migrate |
| `R2_ENDPOINT` | Cloudflare R2 | conditional / backend | no | Remote storage coordinates; no credential for local mode | retire_runtime_after_all_remote_consumers_migrate |
| `R2_REGION` | Cloudflare R2 | conditional / backend | no | Remote storage coordinates; no credential for local mode | retire_runtime_after_all_remote_consumers_migrate |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 | conditional / backend | no | Remote artifacts/archive writer only; NLSC/WRA are local | retire_runtime_after_all_remote_consumers_migrate |
| `RENDER_API_KEY` | Future hosting administration | operations_only / operations | no | No ordinary application runtime consumer; do not transfer/retire active cloud credentials yet | later_decommission_review_only |
| `SMOKE_USER_BEARER_TOKEN` | Acceptance operator/CI | operations_only / operations | no | Short-lived smoke identity; not a server startup credential | expire_after_acceptance |
| `STAGE1_ACCEPTANCE_DATABASE_URL` | Restricted PostgreSQL operations | operations_only / operations | no | Isolated acceptance provisioning only | keep_if_consumer_retained |
| `SUPABASE_ANON_KEY` | Unsupported legacy/admin Supabase credential | conditional / backend | no | Not consumed by this application runtime; never expose to frontend | review_other_cloud_consumers_before_revocation |
| `SUPABASE_JWT_AUDIENCE` | Supabase Auth JWT/JWKS | conditional / backend | no | Public asymmetric JWT verification configuration; no signing/service-role key | keep_if_consumer_retained |
| `SUPABASE_JWT_ISSUER` | Supabase Auth JWT/JWKS | conditional / backend | no | Public asymmetric JWT verification configuration; no signing/service-role key | keep_if_consumer_retained |
| `SUPABASE_JWT_SECRET` | Unsupported legacy/admin Supabase credential | conditional / backend | no | Not consumed by this application runtime; never expose to frontend | review_other_cloud_consumers_before_revocation |
| `SUPABASE_SECRET_KEY` | Unsupported legacy/admin Supabase credential | conditional / backend | no | Not consumed by this application runtime; never expose to frontend | review_other_cloud_consumers_before_revocation |
| `SUPABASE_SERVICE_ROLE_KEY` | Unsupported legacy/admin Supabase credential | conditional / backend | no | Not consumed by this application runtime; never expose to frontend | review_other_cloud_consumers_before_revocation |
| `SUPABASE_URL` | Supabase Auth JWT/JWKS | conditional / backend | no | Public asymmetric JWT verification configuration; no signing/service-role key | keep_if_consumer_retained |
| `TDX_CLIENT_ID` | Taiwan TDX | conditional / backend | no | Protected commute refresh OAuth; market_ops stays disabled | keep_if_consumer_retained |
| `TDX_CLIENT_SECRET` | Taiwan TDX | conditional / backend | no | Protected commute refresh OAuth; market_ops stays disabled | keep_if_consumer_retained |
| `TGOS_API_KEY` | Taiwan TGOS | conditional / backend | no | Protected remote geocoding; not needed by local village resolution | keep_if_consumer_retained |
| `TGOS_APP_ID` | Taiwan TGOS | conditional / backend | no | Protected remote geocoding; not needed by local village resolution | keep_if_consumer_retained |
| `VALUATION_DATABASE_URL` | Professor PostgreSQL / runtime | required / backend | yes | Local SELECT-only valuation/Market/Trend/Finder connection | keep_local_runtime |
| `VERCEL_TOKEN` | Future hosting administration | operations_only / operations | no | No ordinary application runtime consumer; do not transfer/retire active cloud credentials yet | later_decommission_review_only |
| `VNEXT_CURSOR_SIGNING_KEY` | VNext pagination | conditional / backend | no | Independent cursor signing key,minimum32bytes; no pilot-key fallback | keep_if_consumer_retained |
| `VNEXT_DATABASE_URL` | Conditional PostgreSQL runtime | conditional / backend | no | Separate durable VNext least-privilege runtime; no core DB fallback | keep_if_consumer_retained |

NLSC village artifacts, WRA local artifacts, RIS local data and the accepted CWA
archive require no additional government API keys. ARDSWC/GSMMA/liquefaction
archive-only limitations remain explicit. Do not fill the accepted CWA 1897–1989
gap. Object keys, hashes, bucket names, public URLs and project identifiers are
configuration, not provider passwords.

The backend verifies Supabase JWTs with asymmetric public JWKS; it does not
consume a Supabase service-role key, JWT signing secret or frontend publishable
key. Browser Auth eventually uses its publishable key. Keep browser/server Maps
keys separate and restricted to their intended API/application. These boundaries
follow the existing consumers and [Supabase API-key documentation](https://supabase.com/docs/guides/getting-started/api-keys)
and [Google Maps security guidance](https://developers.google.com/maps/api-security-best-practices).
No Supabase auth implementation or frontend build is changed here.

## Storage and service isolation

| Location / material | Ownership and mode | Consumer |
|---|---|---|
| `/etc/proptech-selfhost/secrets` | `root:root`, mode `0700` | Operator persistent store only |
| Each persistent credential / protected replacement backup | `root:root`, mode `0600`; regular, single link | Operator only |
| `/run/proptech-selfhost/secrets` | `root:root`, mode `0700` | Docker daemon resolves individual sources |
| app/usage/valuation URLs, usage HMAC, pilot session key | `root:10001`, mode `0440` | API UID/GID10001; five individual mounts |
| app/usage admin-password files | `root:70`, mode `0440` | Each existing PostgreSQL UID/GID70 container receives its one required admin file |
| Initialization role-password files | `root:70`, mode `0440` | Preserved host recovery material; not mounted into ordinary initialized DB containers |
| Optional usage bootstrap/runtime password files | `root:10001`, mode `0440`, explicit `--ops` only | usage_ops profile only; never API |
| Future provider, Admin, VNext, refresh/metrics and public browser credentials | persistent root-only store; **not staged/mounted by default** | Future reviewed activation only |
| Existing `/run/proptech-selfhost/tls/{app,usage}/server.key` | `root:70`, mode `0440` or `0640` | PostgreSQL only; metadata validation never reads bytes |
| Existing CA private key, if retained online | `root:root`, mode `0600` | Operator signing only; never API/DB mount |
| CA certificate | Public nonsecret file mounted read-only | TLS clients |

Directory ownership remains root; do not broaden the host secret parent for
container traversal. Compose bind-mounts individual files into `/run/secrets`,
so host parent0700 works. Host file modes enforce access: do not rely on Compose
`uid/gid/mode` rewriting for file-backed secrets. See
[Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/) and
[the service secrets reference](https://docs.docker.com/reference/compose-file/services/#secrets).
PostgreSQL permits root-owned group-readable private keys as described in its
[SSL documentation](https://www.postgresql.org/docs/current/ssl-tcp.html).

Core container filenames remain `app_database_url`, `usage_database_url`,
`valuation_database_url`, `usage_peer_hmac_key`, `pilot_session_signing_key`.
The API receives no administrative, provider or browser credential. The prepared
override uses `!override` to replace credential lists, rather than appending to
older overrides: exactly five API files and one required admin-password file per
initialized PostgreSQL service. Initialization-role passwords stay preserved on
the host for explicit recovery/provisioning. This requires Compose 2.24.4 or newer
(the inspected CLI is 5.6.1), following [Compose merge rules](https://docs.docker.com/reference/compose-file/merge/). The root
store is never directory-mounted into any container. Backend URLs stay in
memory after startup, not in Docker/Compose configuration. Optional installation
does not mount credentials or enable their consumers.

## Operator-only installation

Run from `/home/andy/proptech-ai-copilot` in an operator-controlled terminal with
session/input recording disabled. Hidden TTY input fails closed if echo-safe TTY
input is unavailable. Protected file import is available instead; values never
go into arguments or stdout. Do not run actual-secret commands in Codex.

First preserve the currently working credentials:

The current operator has already completed adoption, staging and host validation.
The commands below are the reusable procedure, not a request to rerun them on
this server during post-install acceptance.

```bash
sudo python3 -B scripts/ops/professor_server_secrets.py adopt-existing
```

This reads only known existing root-owned credential files, validates them and
copies them to the persistent root-only store. Existing matching stored material
is preserved; conflicts stop without replacing it. The live runtime files,
database passwords, containers and providers are unchanged. It also preserves
the two usage-ops files if already present. It never reads original X9 datasets.

Optional later credentials can be stored without activation. Each command below
prompts invisibly; the values are not part of the command:

```bash
sudo python3 -B scripts/ops/professor_server_secrets.py install GOOGLE_MAPS_API_KEY
sudo python3 -B scripts/ops/professor_server_secrets.py install TGOS_APP_ID
sudo python3 -B scripts/ops/professor_server_secrets.py install TGOS_API_KEY
sudo python3 -B scripts/ops/professor_server_secrets.py install TDX_CLIENT_ID
sudo python3 -B scripts/ops/professor_server_secrets.py install TDX_CLIENT_SECRET
```

For Earth Engine, the operator provides a service-account JSON file in a protected
location outside the checkout/X9/devices. The source must be a regular single-link
root/operator-owned `0400` or `0600` file with safe ancestors. The installer accepts
bounded service-account JSON with the official Google token endpoint; it does not
use inline JSON or contact Google. This example is a filename placeholder only:

```bash
sudo python3 -B scripts/ops/professor_server_secrets.py install GOOGLE_APPLICATION_CREDENTIALS --from-file /root/protected-import/earth-engine.json
```

`VNEXT_CURSOR_SIGNING_KEY`, optional pilot/metrics/refresh tokens can be generated
locally without displaying them:

```bash
sudo python3 -B scripts/ops/professor_server_secrets.py generate VNEXT_CURSOR_SIGNING_KEY
sudo python3 -B scripts/ops/professor_server_secrets.py generate METRICS_SCRAPE_TOKEN
```

These remain stored only. Existing credentials are never replaced by default.
An explicit `--replace` requires hidden confirmation `REPLACE` and saves a `0600`
old copy under the private `backups/` directory. Replacement is not a DB password
rotation, session-preserving action or automatic activation. Review affected
consumers first. Never generate a new existing core key merely to rerun setup.

For future frontend acceptance, `install NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
and `install NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY` may hold the separate public
browser credentials in protected storage. They are never mounted into the API.
No frontend env/build/deployment is performed here. Public project/issuer/API
URLs are nonsecret future configuration, not a reason to supply server secrets.

Stage the preserved mandatory files with least-privilege permissions:

```bash
sudo python3 -B scripts/ops/professor_server_secrets.py stage
sudo python3 -B scripts/ops/professor_server_secrets.py validate-host
```

`stage` restores exactly five API and four PostgreSQL files; `stage --ops` adds
only the two explicit ops files. It recreates a missing controlled `/run` parent
after reboot. It never stages optional provider/browser credentials, starts a
service, modifies a database, generates missing core material or changes config.
All reads validate metadata; all writes use pinned directory descriptors, atomic
replacement and fixed filenames. Symlinks, hardlinks, unsafe ownership/modes,
unknown authority and prohibited backing storage fail closed. Staged/persistent
values must match without any value being returned.

TLS material is not copied or rotated by this installer. Preserve its existing
Stage 1 protected backup/recovery and certificate identity. After reboot, restore
TLS through that existing workflow before container startup; staging credentials
alone does not recreate certificates. If the metadata-only validator finds
server keys owned by the database UID rather than root, the operator can preserve
the bytes while applying the required ownership/mode:

```bash
sudo chown root:70 /run/proptech-selfhost/tls/app/server.key /run/proptech-selfhost/tls/usage/server.key
sudo chmod 0440 /run/proptech-selfhost/tls/app/server.key /run/proptech-selfhost/tls/usage/server.key
```

These permission-only commands are not executed by Codex. Keep CA private-key
material offline or root-only and restore public CA/server certificates without
changing trust unexpectedly. Validator output contains fixed categories only.
Nonsecret config files must be root-owned, mode `0600` or `0640` and contain no credential
assignments, even empty ones; security guards cannot weaken TLS/local-only flags.

## Active image, mounts and configuration

The accepted image was built from a digest-pinned official Python base, exact
working package versions and an allowlisted committed public context. Dependency
installation/build ran offline after public wheel acquisition. Installed secrets
were never build inputs. Root `.dockerignore` and `.gitignore` continue to exclude
nested dotenv files, credential directories, service-account JSON, private keys
and private backup formats. The preserved local frontend dotenv is excluded;
its contents were not inspected.

The operator's scanner passed all 18 unique historical filesystem layers,
21,549 layer members, image configs/history, OCI attestation JSON, generated
context and captured build output. Captured Compose output and all four
containers' logs were scanned in memory before the final PASS receipt. No raw
output or archive was published. Detection covers known installed values,
password/encoding variants and credential/private-key signatures; it does not
prove absence of arbitrary unknown encodings or credentials unknown to the gate.

The Stage 2 entrypoint validated the five intended credential files inside the
clean image with network disabled. Import/build-identity smoke checks passed.
The active merged model contains
`/etc/proptech-selfhost/stage2-secrets.override.yml` as its fifth file. The runner
verified actual live Compose configuration hashes before and after proxy restart;
legacy credential aliases and extra mounts could not silently survive the merge.

All four services are healthy. Only `postgres_app`, `postgres_usage` and `api`
were recreated; the same reverse-proxy container was stopped and restarted.
The database containers use their original PostgreSQL image and the same populated
`proptech-selfhost_app_data` and `proptech-selfhost_usage_data` volumes.

The API receives exactly five read-only root:10001 mode0440 files; their active
inodes match staging and differ from the old mounted inodes. Each PostgreSQL
container receives only its own root:70 mode0440 admin-password file. Initialization
role passwords remain protected on the host and are absent from ordinary database
consumers. No provider, browser, bootstrap or admin credential is mounted into API.
The startup guard and log redaction remain active in the API process; credential
URLs are reconstructed in memory rather than Docker/Compose environment values.

TLS verify-full and exact role/database identities passed after recreation.
App RIS and valuation serving objects retain SELECT-only access; usage retains
its intentional scoped writer/RLS authority. PostgreSQL has internal networks
and no published port or host5432 listener. API has no published port; proxy8080
remains `127.0.0.1` only. market_ops, paid and optional providers remain disabled.

NLSC and WRA mounts remain read-only under `/srv/proptech-data/DB`. NLSC and all
ten WRA artifact hashes/manifests/decode contracts passed inside the clean image
with zero provider calls. No active service mount references Crucial X9. Ordinary
runtime does not require X9; this acceptance does not unmount it.

Database before/after snapshots agree: 451,744 stored transactions, 451,672 official,
72 sample/demo, 0 future official rows, 117,986 deterministic exclusions and 7,500
active Market aggregate groups. Row 38652 remains physically stored once and is
absent from ordinary serving; its complete record/exclusion fingerprint is
unchanged. Coverage matches 368 canonical regions: 322 eligible and 46 unknown.
No ambiguous match was newly applied and no database source/schema mutation ran.

Twelve focused contracts passed directly and through the proxy during activation,
and passed again through loopback during final acceptance: health/readiness,
village demographics, NLSC→RIS, WRA hit/no-match, Market and special-period filtering,
valuation status/estimate, trend and finder. No full test suite was repeated.

## Ordinary startup, shutdown and verification

Use all five active Compose files for ordinary Stage 2 operations. The old
four-file profile is retained solely as recorded rollback material. The generated
fifth file already pins the accepted image/build identity; do not regenerate it
from the template or rerun activation.

For an operator-managed startup after required credentials and TLS are available:

```bash
sudo docker compose --project-name proptech-selfhost \
  --project-directory /home/andy/proptech-ai-copilot \
  --env-file /etc/proptech-selfhost/compose.env \
  -f /home/andy/proptech-ai-copilot/docker-compose.selfhost.yml \
  -f /etc/proptech-selfhost/datasets.override.yml \
  -f /etc/proptech-selfhost/valuation.override.yml \
  -f /etc/proptech-selfhost/local-frontend.override.yml \
  -f /etc/proptech-selfhost/stage2-secrets.override.yml \
  up -d --no-build --pull never
```

Use the same prefix with `stop` for an intentional shutdown; preserve volumes.
For configuration validation use `config --quiet`, not rendered environment,
Compose, inspect or secret-file dumps. The existing nonprivileged local check is:

```bash
python3 -B scripts/ops/professor_stage2_probe.py --api
```

`/run` is volatile. On a future reboot, recover the existing trusted TLS material
through the protected Stage 1 workflow, stage the persistent credentials and run
host validation before container startup. Staging does not restore TLS or rotate
DB identities. Coordinate recreation of a consumer when an intentionally replaced
staged inode requires renewal. No boot unit or automatic secret injection was
introduced. A reboot/restore rehearsal remains later operational work; no reboot
or recovery claim is part of this live Stage 2 acceptance.

## Retirement, backups and rollback

Preserve the root-only persistent credential store and its protected replacement
backups, existing trusted TLS recovery material, accepted local image and private
activation evidence. Do not publish credentials, DB backups or raw logs in Git.
The successful run's `ROLLBACK.md` and `rollback.json` record the original four-file
model, exact old images/configs and unchanged physical volumes. They are private
operator recovery material. No rollback is required now. A future recovery must
preserve PLVR exclusions and pass TLS, volume, role and focused API checks before
serving traffic; never restore a backup over live data or reset a serving volume.

No cloud credential is revoked. Local NLSC/WRA need no R2/gateway credential.
Retire remote URLs, aliases or R2 credentials only after all cloud/archive/CI
consumers are accounted for and their rollback windows close. Keep Vercel,
Cloud Run, Render, DNS and GitHub remote unchanged until their separately approved
migration stages. Supabase Auth may remain required for future frontend auth;
no service-role or JWT signing secret is needed by this backend contract.

## Completed Stage 2 checklist

- [x] Sanitized credential inventory and protected operator installation procedure.
- [x] Persistent/staged ownership, least-privilege modes and exact individual mounts.
- [x] Clean committed-context image, all historical layers/config/history and output scanning.
- [x] Clean-image secret-file validation, import and disabled-operation guards.
- [x] Five renewed API inodes and one admin-only file per PostgreSQL container.
- [x] Original database image/volumes, source population, exclusions and coverage preserved.
- [x] TLS, app/valuation SELECT-only permissions and scoped usage permissions.
- [x] Health/readiness, NLSC→RIS, WRA, Market, valuation, trend and finder contracts.
- [x] Private PostgreSQL, loopback 8080, market_ops and optional/paid providers disabled.
- [x] Local datasets independent of X9; source archive and `/dev/sda` untouched by this work.
- [x] `frontend_next/next-env.d.ts` preserved and excluded from the final commit.
- [x] Final local acceptance snapshot; no push or production/cloud/DNS change.

No additional credential is required by the current local profile. Future Maps/
Places/Routes, Earth Engine, TGOS, TDX, remote R2, frontend browser/auth, Admin/VNext,
metrics or refresh consumers need their own reviewed credential/role activation.
Installing a future credential must not enable its consumer automatically.

## Later stages and historical evidence

Stage 3+ covers local frontend/API routing and authentication acceptance, ML work
when separately requested, reviewed optional-provider activation, public TLS/ingress,
rate/abuse controls,backup/restore/reboot rehearsal and eventual cloud cutover.
These are outside this Stage 2 completion. No production-readiness claim is made.
Preserve explicit unsupported local Terrain capabilities and the accepted CWA
1897–1989 non-fill rule; missing data must remain unavailable or unknown.

Earlier refused attempts performed no runtime activation. Their sanitized reports
remain available for audit:

- [`configuration-name-diagnosis.json`](../../reports/professor-stage2-secrets/configuration-name-diagnosis.json): omitted existing nonsecret configuration identifiers.
- [`activation-failure-20261029T094222Z.json`](../../reports/professor-stage2-secrets/activation-failure-20261029T094222Z.json) and [`coverage-probe-repair.json`](../../reports/professor-stage2-secrets/coverage-probe-repair.json): coverage catalogue/eligible-count verifier repair; no data rewrite.
- [`image-scan-failure-20261029T104746Z.json`](../../reports/professor-stage2-secrets/image-scan-failure-20261029T104746Z.json) and [`image-scanner-repair.json`](../../reports/professor-stage2-secrets/image-scanner-repair.json): strict OCI 1.1 BuildKit attestation support; all byte scanning retained.

Previously executed focused source tests are recorded in acceptance history,
including 80 scanner/diagnostic/activation tests with 28 subtests and independent
review. Final acceptance reads all 16 successful receipt files and verifies 23
assertions plus 12 fresh live API contracts; it does not rerun implementation or
the full suite. Final acceptance uses operator evidence for Docker/DB state
because the agent has no direct Docker socket access. No privileged duplicate
check is required to consume the successful receipt.
