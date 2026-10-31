# Independent provider installation — Stage5

Each provider can now be stored and validated independently. Earth Engine is
**PENDING_IAM** for `roles/iam.serviceAccountTokenCreator`; it is not a prerequisite
for Google, TGOS, TDX, R2 or OpenAI installation. No private-key JSON is accepted.
Supabase retains the accepted issuer/audience and application-data boundaries.

Readiness here means the operator installer is prepared and tested. No actual
credential has been read or installed by Codex, and no provider is activated.

## Operator commands

Run each command separately in a private operator terminal, without shell
tracing/session recording. Missing values use hidden TTY input; never paste
them into Codex, command arguments, environment exports, logs or Git.

```bash
sudo python3 -B /home/andy/.codex/worktrees/7d59/proptech-ai-copilot/scripts/ops/professor_provider_credentials.py --provider google
sudo python3 -B /home/andy/.codex/worktrees/7d59/proptech-ai-copilot/scripts/ops/professor_provider_credentials.py --provider tgos
sudo python3 -B /home/andy/.codex/worktrees/7d59/proptech-ai-copilot/scripts/ops/professor_provider_credentials.py --provider tdx
sudo python3 -B /home/andy/.codex/worktrees/7d59/proptech-ai-copilot/scripts/ops/professor_provider_credentials.py --provider r2
sudo python3 -B /home/andy/.codex/worktrees/7d59/proptech-ai-copilot/scripts/ops/professor_provider_credentials.py --provider openai
```

| Selection | Hidden input names | Persistent protected filenames | Configuration |
|---|---|---|---|
| google | GOOGLE_MAPS_API_KEY | google_maps_api_key | One shared server key for Geocoding/Places/Routes |
| tgos | TGOS_APP_ID, TGOS_API_KEY | tgos_app_id, tgos_api_key | No provider call |
| tdx | TDX_CLIENT_ID, TDX_CLIENT_SECRET | tdx_client_id, tdx_client_secret | No token request or job activation |
| r2 | R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY | r2_access_key_id, r2_secret_access_key | R2_ENDPOINT, R2_BUCKET, R2_REGION; region must be auto |
| openai | OPENAI_API_KEY | openai_api_key | No API request, model selection or activation |
| earth-engine | Protected keyless ADC import path | earth_engine_adc_json | EARTH_ENGINE_PROJECT; PENDING_IAM, do not run now |

The operator reports the new Professor Google server key is restricted to public
egress IP `140.119.55.43` and Geocoding API, Places API (New), Routes API. The
source adapters use respectively `/maps/api/geocode/json`,
`places.googleapis.com/v1/places:searchNearby` and
`routes.googleapis.com/directions/v2:computeRoutes`. One canonical key serves
all three; do not substitute the browser key or invent separate Places/Routes
secrets. Console restrictions, actual egress and authorized API functionality
remain separate acceptance evidence; no Google management/provider call is made
to verify them here. Store preparation is ready, paid API acceptance is NOT_RUN.

Secrets stay root:root0600 in `/etc/proptech-selfhost/secrets`; public provider
settings stay root:root0600 in `/etc/proptech-selfhost/provider-config`. Parent
directories are root0700. Staging is per provider under
`/run/proptech-selfhost/secrets/providers/{google,tgos,tdx,r2,openai,earth_engine}`,
with root0700 directories and root:10001/0440 files. Only selected provider
directories/files are created. Core/database credentials and existing providers
are preserved. Existing valid material wins; conflicts/unsafe metadata refuse,
never overwrite/rotate. This workflow does not replace an already-stored old
Google key with the newly issued one; a detected conflict requires a separately
reviewed rotation, not silent replacement.

`--from-file NAME=/protected/path` is available only for names in the selected
provider. Imports are regular single-link files, owned by root or sudo operator,
mode0400/0600, no unsafe parents/symlinks, outside Git, `/dev` and X9. Cross-provider
imports refuse before host operations. Sources are never modified.

## What every independent run verifies

- Fixed selected provider and complete selected credential/configuration set;
  all pair/config input validates before secret writes.
- Same immutable local API image, accepted Supabase authority, disabled provider
  and market_ops guards, no live provider mounts/credential aliases.
- Complete Git/image-layer/history/environment/project-log scans before writes.
  Known-secret scanning includes selected inputs, core secrets and all valid
  already-present provider material; missing unselected providers never prompt.
  A malformed or unsafe existing credential is a security refusal, not an IAM
  dependency. No actual IAM checks are made for absent Earth Engine.
- Only the selected provider's read-only files are mounted into an isolated
  existing-image probe: no network, logging, privilege, app startup or public
  ports. Only that provider's metadata/readability is accepted. Earth Engine's
  offline SDK-loader probe runs only when earth-engine is selected.
- Selected files, existing scanned-provider material, core metadata and runtime
  identity/guards are checked again. Concurrent insertion/change refuses rather
  than accepting a credential that was never scanned.

Each run writes its own sanitized `acceptance.json` under
`/var/backups/proptech-selfhost/stage5-provider-credentials/<timestamp-random>/`.
Success: `PASS_MIGRATED_PROVIDER_DISABLED`. It records selected names and files,
visibility result and provider functional tests NOT_RUN. It does not claim all
providers migrated. Earth Engine IAM remains PENDING_IAM independently.
On failure, partially stored files may remain protected and inactive with
PRESENT_NOT_VALIDATED; the next run preserves identical valid material.

No provider endpoints, OAuth token endpoints or paid APIs are called during
installation. No live API mounts/env/config, Docker services, databases, network,
firewall, NGINX, IAM, WAN/DNS or Vercel settings change. Nothing is retired/pushed.

## Provider-specific reboot staging

After the accepted core secret restoration prepares `/run/proptech-selfhost/secrets`,
the parallel hardening owner can restore each configured provider explicitly:

```bash
sudo python3 -B /home/andy/.codex/worktrees/7d59/proptech-ai-copilot/scripts/ops/professor_provider_credentials.py --stage-provider google
```

Use the same command with tgos/tdx/r2/openai only for providers successfully
stored. It reads a complete selected persistent set, preserves existing files/
inodes, refuses conflicts or missing selected material, shares the migration
lock and performs no prompts, network, Docker or service operations. It does
not require Earth Engine. No boot unit is installed/changed in this task.
Global `--stage-stored-providers` remains strict and needs all six providers;
do not use it for partial deployment. Runtime provider startup/activation stays
a separate controlled step with explicit boot ordering and acceptance.

## Earth Engine and full migration

[Keyless ADC implementation and IAM runbook](earth-engine-keyless-adc.md) remain
complete. Preserve `iam.disableServiceAccountKeyCreation`. Wait for target-account
Token Creator approval before operator ADC authentication/functional acceptance.
No policy bypass, private-key creation or fabricated IAM approval is supported.
The future selection is `--provider earth-engine`; an approved impersonation ADC
file is required, never a service-account private key. Its storage acceptance
alone cannot prove live IAM or unattended refresh/session policy.

Legacy `--migrate-all` still explicitly requires the entire provider population;
it is unnecessary for these five commands. Its failure does not invalidate a
successful separately recorded provider run. Providers remain disabled until
their own functional/security/cost acceptance is authorized and passes.
