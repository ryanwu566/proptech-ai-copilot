# Professor-server bootstrap (future authorized session)

This is a preparation runbook. No professor server connection or deployment has
been made. Run it only in a later separately authorized Ubuntu host session after
reviewing the exact commit and current Compose/scripts. It does not authorize
Render, DNS, cloud resources or production access. Commands target a fresh
Ubuntu 24.04 LTS host (conservative baseline;26.04 LTS requires target validation); stop on unexpected existing users, workloads, data or firewall
rules rather than replacing them.

## 1. Inventory, recovery access and operator account

Record `cat /etc/os-release`, `uname -m`, `lsblk -f`, `df -h`, `free -h`,
`lscpu`, `ip route`, `sudo ss -lntup`, `sudo ufw status verbose`, disk SMART
health, host serial and available out-of-band console. Verify power/UPS,
reboot plan, disk encryption, time sync and institution/tailnet policy. Determine
CPU architecture before selecting image digests. Choose an operator account;
commands below use `proptech`. Keep the current administrative session open.

```bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install -y ca-certificates curl git ufw fail2ban openssl age rsync python3
id proptech >/dev/null 2>&1 || sudo adduser --disabled-password --gecos '' proptech
sudo usermod -aG sudo proptech
sudo passwd proptech
sudo install -d -o proptech -g proptech -m 0700 /home/proptech/.ssh
```

`passwd` sets a local password for sudo, not a permission to use password SSH.
Transfer the operator's verified public key using the existing trusted channel.
Install a new `authorized_keys` as `proptech:proptech` mode0600 if absent; if it
exists, inspect and add only the verified missing key without overwriting keys.
Never install a private key on the server. **Open a second, fresh key-based SSH
session and successfully run `sudo -v` there before the following hardening.**
If either fails, fix key/sudo access while retaining the original session.

```bash
sudo install -d -m 0755 /etc/ssh/sshd_config.d
sudo tee /etc/ssh/sshd_config.d/00-proptech-hardening.conf >/dev/null <<'SSH'
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
SSH
sudo sshd -t
sudo sshd -T | grep -E '^(pubkeyauthentication|passwordauthentication|kbdinteractiveauthentication|permitrootlogin) '
sudo systemctl reload ssh
```

Inspect effective settings for the actual user/address if Match blocks exist
(`sshd -T -C user=proptech,host=HOST,addr=CLIENT_IP`). Reload only after syntax
passes. Test a **third** fresh key/sudo session before closing either known-good
session. On failure, revert only this new drop-in from the retained session or
console; do not restart/reboot into an unverified SSH configuration.

## 2. Firewall and fail2ban

On the verified fresh host, preserve SSH access first. `OpenSSH` below assumes
port22; inspect the actual listener and allow its exact port/source before enable.

```bash
sudo ufw allow OpenSSH
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
sudo ufw status verbose
sudo tee /etc/fail2ban/jail.d/proptech-sshd.local >/dev/null <<'JAIL'
[sshd]
enabled = true
backend = systemd
JAIL
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

Do not allow80/443 in Option D. Never allow5432,6379 or an internal API port.
Tailscale ACLs and host integration must be tested from an authorized client;
add only reviewed interface/source-specific rules if required. Docker-published
ports can bypass UFW forwarding rules, so the concrete protection here is no
DB/API publication and proxy binding **127.0.0.1 only**. Inspect Compose and
`ss` after every change. Review Docker's actual firewall backend before any
later DOCKER-USER rules; do not disable Docker's firewall management.
[Docker firewall guidance](https://docs.docker.com/engine/network/packet-filtering-firewalls/)

## 3. Official Docker Engine and Compose v2

The following repeatable repository setup follows the
[official Ubuntu installation instructions](https://docs.docker.com/engine/install/ubuntu/).
On an existing machine, inspect conflicting `docker.io`/Podman/containerd packages
and stop for a migration plan rather than blindly removing another workload.
Use the host release codename; verify it is supported by Docker before install.

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
```

Record installed versions and test updates before promotion. Prefer explicit
`sudo docker` for the operator; Docker-group membership grants root-equivalent
host control and is not a least-privilege sandbox. Containers use their dedicated
non-root identities; this bundle does not claim the daemon itself is rootless.
Do not mount the Docker socket into the API or monitoring containers.

## 4. Checkout, persistent paths and secret custody

```bash
sudo install -d -o proptech -g proptech -m 0750 /srv/proptech
sudo install -d -o root -g root -m 0750 /etc/proptech-selfhost
sudo install -d -o root -g root -m 0700 /var/backups/proptech-selfhost
sudo install -d -o root -g root -m 0750 /var/log/proptech-selfhost
```

As the operator, clone only if `/srv/proptech/repo` is absent, then checkout the
reviewed exact commit with a clean working tree; on repeat runs inspect the
existing checkout and do not reset/clean it. Clone URL:
`https://github.com/ryanwu566/proptech-ai-copilot.git`. Use the final reviewed
selfhost package SHA, not an assumed moving `main`. Record `git rev-parse HEAD`
and verify it against the approved value. Root Docker data remains under its
configured data-root with distinct named volumes; do not manually chown or copy
live volume files. Logs and encrypted backups have separate capacity budgets.

Split `.env.selfhost.example` into two outside-checkout operator files:

- `/etc/proptech-selfhost/compose.env`: NEW infrastructure inputs only, including
  `SELFHOST_RUNTIME_ENV_FILE=/etc/proptech-selfhost/runtime.env`, absolute
  `SELFHOST_SECRETS_DIR=/run/proptech-selfhost/secrets`,
  `SELFHOST_TLS_DIR=/run/proptech-selfhost/tls`, immutable backend/proxy image
  references, and any other explicit `SELFHOST_*` inputs used by current Compose.
- `/etc/proptech-selfhost/runtime.env`: supported non-secret runtime settings only;
  replace dummy origins/hosts with exact private frontend/backend hostnames;
  retain localhost and127.0.0.1 in API_ALLOWED_HOSTS for local healthchecks.
  Exclude secret URL/HMAC/signing/token/provider values. The wrapper supplies the
  four required secret values; Compose fixes preview/postgres/required-ledger
  controls. Set mode0640 root:10001 if mounted; root can read the Compose env file.

Do not `source` these files as shell scripts. `ENVIRONMENT` is unsupported.
Do not fill optional provider credentials or reuse legacy database URLs.

```bash
sudo install -d -o root -g root -m 0755 /run/proptech-selfhost
sudo install -d -o root -g root -m 0755 /run/proptech-selfhost/secrets
sudo install -d -o root -g root -m 0755 /run/proptech-selfhost/tls
sudo install -d -o root -g root -m 0755 /run/proptech-selfhost/tls/app
sudo install -d -o root -g root -m 0755 /run/proptech-selfhost/tls/usage
```

Populate files through the operator's secure local credential mechanism with
shell tracing disabled; never print, put secret values in CLI arguments/history,
or write them inside the checkout. Do not create real secrets during preparation.
`/run` is volatile: provision a boot-time recovery procedure from an encrypted
vault before autostart; an empty mount must fail closed.

| File below secrets directory | Consumer / source ownership |
| --- | --- |
| `app_database_url` | API only; root:10001 mode0440; fresh `app_runtime` on `postgres_app/proptech_app` |
| `usage_database_url` | API only; root:10001 mode0440; direct `proptech_usage_runtime_v1` on `postgres_usage/proptech_api_usage` |
| `usage_peer_hmac_key` | API only; root:10001 mode0440; valid64-hex, unique to this isolated staging system |
| `pilot_session_signing_key` | API only; root:10001 mode0440; strong >=32-character secret |
| `app_admin_password`, `app_runtime_password`, `usage_admin_password`, `usage_migration_password` | DB initialization only; root:70 mode0440 (PG17-alpine OS postgres UID/GID70) |
| `usage_bootstrap_database_url` | `usage_ops` only; root:10001 mode0440; direct TLS `usage_migration` URL |
| `usage_runtime_password` | `usage_ops` only; root:10001 mode0440; credential matching percent-encoded password in usage runtime URL |

Confirm UIDs from the actual pinned images before setting ownership. `api` mounts
only four named secret files, not their parent directory. No bootstrap/admin
credential goes into its environment/mounts. Compose secrets here are file bind
mounts, not an encrypted secret store; host root/Docker administrators remain
trusted. Root-owned parent directories are traversable; individual files deny
other users. UID10001 must have no Docker-group membership.

TLS files: `tls/app/server.crt`, `tls/app/server.key`,
`tls/usage/server.crt`, `tls/usage/server.key`, and `tls/ca.crt`. Server private
keys root:70 mode0440, certificates/CA mode0444. Use distinct server keys and
certificates signed by a trusted private CA, with DNS SANs `postgres_app` and
`postgres_usage` respectively. Keep CA signing key offline, never mounted into
containers. API runtime URLs use verify-full with mounted CA; bootstrap retains
the original `sslmode=require`. Test certificate validity/expiry and verify-full
hostname checks before accepting data. Password characters in URL files require
correct percent encoding; never construct or display URLs in a public command.

## 5. Build, validate and initialize private databases

From `/srv/proptech/repo`, use only the reviewed selfhost file and fixed project:

```bash
dc() { sudo docker compose --project-name proptech-selfhost --env-file /etc/proptech-selfhost/compose.env -f /srv/proptech/repo/docker-compose.selfhost.yml "$@"; }
dc config --quiet
```

Build the backend base from `Dockerfile.cloudrun` with `BACKEND_BUILD_COMMIT`
equal to the reviewed40-hex checkout SHA. Compute and review a named local
`tag@sha256:digest` reference for `SELFHOST_BACKEND_IMAGE`; BuildKit does not
accept a bare sha256 image ID as this FROM input. Preload the reviewed architecture
compatible pinned PostgreSQL17/proxy images; proxy reference must be an immutable
digest in `SELFHOST_PROXY_IMAGE`. Compose does not silently pull unknown images.
Then `dc build --pull=false api` builds the shared non-root secret-loading API/usage_ops image.

```bash
sudo docker build --pull=false -f Dockerfile.cloudrun --build-arg BACKEND_BUILD_COMMIT="$(git rev-parse HEAD)" -t proptech-selfhost-backend:preparation .
backend_tag=proptech-selfhost-backend:preparation
backend_id=$(sudo docker image inspect "$backend_tag" --format '{{.Id}}')
backend_reference="$backend_tag@$backend_id"
printf '%s\n' "$backend_reference"
# Record this reviewed named digest as SELFHOST_BACKEND_IMAGE with sudoedit,
# verify the exact SHA and preloaded proxy digest, then build the extension.
dc build --pull=false api
```

A fresh host needs reviewed dependency download access for this build; an
offline build additionally requires preloaded base images/package artifacts.
Do not silently switch digests or claim an offline build when dependencies are missing.

```bash
dc up -d postgres_app postgres_usage
dc ps
# No DB port may appear in the PORTS column or in host listeners.
sudo ss -lntup
dc --profile usage_ops run --rm --no-deps usage_ops preflight
dc --profile usage_ops run --rm --no-deps usage_ops bootstrap
```

The last command is the unchanged bootstrap's database-free plan, not execution.
Expect `database_contacted=false` and immutable021 SHA256
`00ed7d4b78de6d92c285ab8cd87241d1477bee2ce6e97caef6bbf6e2f43b98af`.
Preflight contacts only the dedicated local usage database using bounded reads;
it is evidence for a later bootstrap, not a substitute for bootstrap checks.
If an initialization script failed, inspect bounded logs and preserve the volume;
init scripts do not rerun on an existing volume. Never fix a partial target by
`down -v`, DROP, forged history or automatic privilege widening.

## 6. Exact future Wave 1B sequence

Execute only on the verified fresh dedicated professor usage cluster in the
later authorized session. Direct actor `usage_migration` must own the DB and be
LOGIN/CREATEROLE/NOSUPERUSER/NOBYPASSRLS/NOREPLICATION. Keep it distinct from the
cluster-wide `proptech_usage_*` roles. Replace the release token below with the
reviewed SHA (non-secret). Each refusal means stop and preserve evidence.

```bash
dc --profile usage_ops run --rm --no-deps usage_ops bootstrap --execute --acknowledge-fresh-dedicated --expected-database proptech_api_usage --release-version REVIEWED_40_HEX_SHA
dc --profile usage_ops run --rm --no-deps usage_ops bootstrap --operation provision-runtime --execute --acknowledge-fresh-dedicated --expected-database proptech_api_usage
dc --profile usage_ops run --rm --no-deps usage_ops activate-runtime
```

`bootstrap` forwards to `python -B scripts/bootstrap_usage_database.py`. The
first operation creates actual immutable021 objects and private bounded history;
the second creates runtime LOGIN with guard/writer only and **null password**.
The explicit `activate-runtime` infrastructure operation audits installed security,
grants only database CONNECT and sets the SCRAM runtime credential from its
ops-only secret, then audits again in one transaction. It does not change the
repository bootstrap provisioner. Stop if it refuses; do not substitute a broader
manual grant. URL files must contain no query parameters; TLS/CA is fixed by the
wrapper. Ensure usage_runtime_password matches the securely populated runtime
URL before starting API. Never grant reader/executor,
object ownership, CREATE, role administration or privileged memberships to API.

Full application migration is a separate unresolved gate: the global runner
includes021 and013/020 require `auth.users`/`auth.uid()`. Do not run that runner
on usage, invent a cutoff or insert fake ledger rows. Empty `proptech_app` can
support a connectivity/startup rehearsal; it is not a migrated product database.
Before business/pilot routes, approve and rehearse the full app/Auth migration
model and least-privilege app object grants.

```bash
dc up -d api reverse_proxy
dc exec -T api python -B scripts/ops/selfhost_runtime.py runtime-probe
curl --fail --silent --show-error --max-time 10 -H 'Host: api.staging.example.invalid' http://127.0.0.1:8080/liveness
curl --fail --silent --show-error --max-time 10 -H 'Host: api.staging.example.invalid' http://127.0.0.1:8080/health
curl --fail --silent --show-error --max-time 10 -H 'Host: api.staging.example.invalid' http://127.0.0.1:8080/readiness
```

Replace dummy Host with the actual exact allowlisted private API name in all
checks. Runtime probe authenticates directly, validates guard and transactional
writer probe; it is distinct from app SELECT1 readiness. Inspect health/readiness
bodies and release SHA, not only HTTP200. Keep provider flags disabled and do
not run business requests that call paid APIs. No public API listener is allowed.

## 7. Private access, monitoring and backup schedule

Enroll Tailscale only under the approved account and institution policy in that
future session. Configure private Serve HTTPS to `http://127.0.0.1:8080` with exact
actual tailnet hostname in `API_ALLOWED_HOSTS` and private frontend origin in
`CORS_ALLOWED_ORIGINS`. Review current installed `tailscale serve --help` and
verify access from an allowed identity and refusal from a disallowed identity.
Do not use Funnel, router forwarding or public DNS changes. Preserve incoming
Host and disabled Uvicorn forwarded-header trust; review anonymous-peer sharing
before a multi-user pilot. For operator diagnostics, an SSH local port forward
through Tailscale to loopback8080 also keeps ingress private.

Install root-owned systemd oneshot services/timers after reviewing script CLI
and the initial manual health/backup/restore results. Health every5minutes;
daily backup with randomized delay/persistent missed-run catch-up. Use absolute
script paths, fixed project/env arguments, private `UMask=0077`, restricted logs,
execution timeouts and an operator notification action on failure. Do not put
secret values in units. Timer execution requires actual secrets restored after
boot; fail closed if absent. Root reads host metrics/Docker locally, with no
socket mounted in app. See exact script invocations in the maintained plan;
record backup success/staleness, disk/memory/CPU, restart counts, PostgreSQL and
API health, then test a controlled failure notification.

Encrypt daily backups of both databases with separate recipient-key custody;
retain7daily/4weekly/12monthly verified points. No automatic pruning. Copy
immutable encrypted generations to an identified external drive and another
independent location, verify checksums and rehearse in disposable PG17 only.
Do not call a dump or healthy container a successful recovery. Do not enable
pilot traffic until migration/Auth, restore, monitoring and ingress gates pass.


## Exact host-only backup/health interface

The operations wrappers intentionally ignore checkout dotenv and inherited DB
credentials. Supply only these reviewed non-secret infrastructure inputs in the
root/operator execution environment. This example contains paths and dummy image
references only; use the same immutable image values recorded in `compose.env`.
Do not use `sudo -E` with an uncontrolled user environment or `source` env files.

```bash
# In a future authorized root maintenance shell; values contain no credentials.
export SELFHOST_SECRETS_DIR=/run/proptech-selfhost/secrets
export SELFHOST_TLS_DIR=/run/proptech-selfhost/tls
export SELFHOST_RUNTIME_ENV_FILE=/etc/proptech-selfhost/runtime.env
export SELFHOST_BACKEND_IMAGE=proptech-selfhost-backend:preparation@sha256:REVIEWED_LOCAL_BACKEND_DIGEST
export SELFHOST_PROXY_IMAGE=nginx@sha256:970364228b1e4f932abc22d321932816782cca8a20b85a77552a7cfe9acfb3b5
cd /srv/proptech/repo
bash scripts/ops/selfhost-health-check.sh --backup-dir /var/backups/proptech-selfhost --project proptech-selfhost --url http://127.0.0.1:8080 --max-age-hours 30
bash scripts/ops/selfhost-backup.sh --output-dir /var/backups/proptech-selfhost --recipients-file /etc/proptech-selfhost/backup-recipients.txt --project proptech-selfhost
bash scripts/ops/selfhost-restore-rehearsal.sh --backup-dir /var/backups/proptech-selfhost/EXACT_COMPLETED_GENERATION --identity-file /run/proptech-recovery/age-identity.txt
```

The recipient file contains public age recipients; keep decryption identity on a
separate custody channel and mount temporarily only for a recovery exercise.
Restore accepts no target URL/database/container and creates only UUID-owned
local disposable PG17 targets. The rehearsal is intentionally bounded to
512 MiB PGDATA per target and at most 64 MiB total encrypted input; it verifies
small fixtures, not production-volume recovery capacity or RTO. Direct runtime
LOGIN is tested through local trust authentication in the isolated target;
that proves role identity and authorization, not operator password/SCRAM custody.
It does not restore passwords. Never set
`SELFHOST_RESTORE_MODE=1` on an established service; that NEW optional input is
for fresh empty recovery initialization only and is not a repair/cleanup mode.
Root/operator timers need the same explicit non-secret infrastructure environment
and absolute paths; no secret value belongs in a timer/unit or command argument.
Host health now calls the bounded read-only API helper to verify usage guard,
writer grants/RLS and HTTP readiness; `USAGE_GUARD=PASS` records that available
contract. Missing writer privileges fail this check without telemetry writes.
Run the separate transactional direct-runtime probe after changes and investigate
failures independently of app readiness; a successful read-only health check is
not proof that a provider request or durable ledger write just succeeded.

After a completed encrypted backup and identified external drive mount, create
a new destination directory with a unique generation name. Verify mount UUID,
mountpoint and free capacity before copying; refuse an absent/unexpected mount.
Use `rsync -a --ignore-existing SOURCE_GENERATION/ NEW_DESTINATION/`, then verify
the manifest checksums in that destination. No `--delete`, filesystem formatting,
partitioning or retention removal is part of this runbook. Verify an independent
copy before safe unmount; keep the only decryption key off that drive.

For optional R2 copies, prepare a scoped read-only rclone remote outside the repo
and use `rclone copy R2_REMOTE:BUCKET/PREFIX /VERIFIED_DISK/NEW_VERSIONED_PATH`
followed by `rclone check`. Copy existing object versions/provenance where the
source policy provides them; do not claim a latest-object copy preserves deleted
history. Never `rclone sync --delete`, change source policy or upload back into
R2 during a backup exercise.




Backup configuration recovery covers the allowlisted infrastructure source files,
release/image identities and enumerated safe runtime flags only. It deliberately
excludes hostnames, CORS and other free-form runtime/operator settings. Preserve
those settings, Compose input paths, TLS material and actual secrets in a separate
encrypted operator recovery package with independently held decryption custody;
the generated metadata is not a complete server configuration backup.

During logical backup, quiesce schema/role/administrative changes so catalog and
role metadata remain consistent. Ordinary application writes may continue within
each database dump snapshot; the catalog fingerprint excludes mutable row counts.
The four database/role archives have no shared atomic cross-database snapshot or
PITR. A cross-database invariant or cutover checkpoint still requires an explicitly
coordinated write freeze/consistent export plan.
