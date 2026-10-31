# Credential audit closure — values never exported

Repository/configuration audit is available. The live Cloud Run, Render, Vercel
and GitHub Actions inventories are **UNKNOWN**. Cloud Run/Render/Vercel have no
suitable authenticated tools here. The GitHub reader now supports repository,
branch and workflow-run metadata, but explicitly excludes secrets APIs and
cannot list the required credential scopes. Do not install/login to another account
or copy API tokens into the agent to bypass that boundary. No production changes,
provider admission, credential rotation or cloud retirement are requested.

## Accepted Professor evidence

Six API secret files are proven by the accepted Stage4A apply receipt and matching
host/container inode/UID/GID/mode metadata. Five sanitized files (acceptance,
host and container secret metadata, container mounts, database probe) are checked
against the already accepted22-file SHA256 manifest before reuse. This proves
the accepted snapshot; it is not a fresh privileged filesystem inspection.
Current permission denial isUNKNOWN, notmissing. If accessible present metadata
cannot establish the same accepted identity, it remains unverified.

The canonical names are DATABASE_URL, API_USAGE_DATABASE_URL,
API_USAGE_PEER_HMAC_KEY, PILOT_SESSION_SIGNING_KEY, VALUATION_DATABASE_URL and
PROFESSOR_USER_DATABASE_URL. The first five use Stage2; the last uses the Stage4
entrypoint/separate user DB principal. Database admin files are DB-only;
initialization-only passwords are not runtime API mounts. No new credential is
evidenced missing for the accepted current profile.

The Supabase connector was used only for the existing public project URL and
Edge Function list. URL matches the accepted authority; function list is empty.
No key endpoint, auth-user list, log dump, password, token, SQL mutation or service
credential was requested. Identity verification requires the public issuer,
audience and JWKS, not a signing/service-role secret. See
[Supabase JWT verification](https://supabase.com/docs/guides/auth/jwts).

## Required live cloud evidence

Use the operator's **existing** authorized console. Read names/metadata only; do
not reveal values, download complete service/variable exports or use `env pull`.
No screenshot containing keys or token-bearing URLs should be supplied.

| Platform/resource | Names-only evidence scope |
|---|---|
| Cloud Run:proptech-earth-engine-api | Actual service project/region; serving and retained revisions; environment names; referenced Secret Manager resource names; attached service-account identity; any ADC/workload-identity dependency. No secret versions/payloads. |
| Render:proptech-ai-copilot-api | Actual service environment names and linked environment-group/file names across retained deploy scopes; configuration presence only. No reveal/copy of values or secret-file content. |
| Vercel:proptech-ai-copilot | Production/Preview/Development and branch overrides; environment names and scope. Confirm server credentials are absent from NEXT_PUBLIC names. No decrypted values or browser key values. |
| GitHub:ryanwu566/proptech-ai-copilot | Repository/org-inherited and every referenced Environment secret/variable NAME; workflow permissions and scope. No secret values, workflow credential execution or provider refresh. |

Check workflow environments separately: production-identity-smoke-read,
production-identity-smoke-write, production-market-import and other environments
declared by the checked-in workflows. The generated matrix lists exact source
references; a name in source is not proof it exists in any control plane.

An operator may create one JSON per platform containing **only**:

```json
{"platform":"cloud_run","source":"operator_control_plane_metadata","resource":"proptech-earth-engine-api","environment_scope":"all_deployments","environment_names":[],"secret_reference_names":[],"values_exported":false}
```

This empty example is a schema example, not a negative inventory. Do not claim
all_deployments until all scopes above were reviewed. Other platform/resource
pairs are render/proptech-ai-copilot-api, vercel/proptech-ai-copilot and
github_actions/ryanwu566/proptech-ai-copilot. For CI, the marker includes repository,
organization inheritance and all referenced Environments; it is not main-only.
Record public service-account/project identifiers in an accompanying sanitized
observation, not credential JSON fields. The strict importer accepts names only
and rejects value fields, token-shaped literals and resource/scope mismatches.

Run locally after names-only observations exist:

```bash
python3 -B scripts/ops/professor_stage5.py --dependency-matrix --cloud-metadata /tmp/professor-stage5-cloud-run-names.json --cloud-metadata /tmp/professor-stage5-render-names.json --cloud-metadata /tmp/professor-stage5-vercel-names.json --cloud-metadata /tmp/professor-stage5-github-names.json
```

This command audits only. It neither uploads values nor invokes cloud APIs.
Do not use metadata imported from a partial or guessed resource to retire cloud
access. Deployment fields, literal credentials, live IAM restrictions, refresh
jobs and credential presence still need their specific evidence.

## Conditional missing-credential procedure

No install or adoption is needed now. Do not rerun adopt-existing, stage,
provisioning or activation merely to improve an audit status. For an actual
missing required core file, first stop and recover the **same** credential from
protected accepted backups using an operator-owned session. Never generate a new
DB password/signing key or change a role to match a missing URL.

For a separately approved canonical provider, use the existing hidden-TTY
installer or a protected file transfer directly to root-owned server storage:

```text
sudo python3 -B scripts/ops/professor_server_secrets.py install GOOGLE_MAPS_API_KEY
sudo python3 -B scripts/ops/professor_server_secrets.py install TGOS_APP_ID
sudo python3 -B scripts/ops/professor_server_secrets.py install TGOS_API_KEY
sudo python3 -B scripts/ops/professor_server_secrets.py install TDX_CLIENT_ID
sudo python3 -B scripts/ops/professor_server_secrets.py install TDX_CLIENT_SECRET
sudo python3 -B scripts/ops/professor_server_secrets.py install R2_ACCESS_KEY_ID
sudo python3 -B scripts/ops/professor_server_secrets.py install R2_SECRET_ACCESS_KEY
sudo python3 -B scripts/ops/professor_server_secrets.py install GOOGLE_APPLICATION_CREDENTIALS --from-file <protected-root-owned-ADC-JSON>
```

These are mutually scoped future procedures, not a request to run them all.
Never pass values on the command line or to an agent; never use shell tracing,
echo/cat, broad exports, plaintext clipboard/evidence archives or --replace on an
existing accepted credential. Copy/adopt directly from the authorized source to
the operator's protected server file; do not route it through Vercel or Git.

Google Places/Routes/geocoding share the actual GOOGLE_MAPS_API_KEY consumer in
this repository; do not invent separate key aliases. Browser Maps uses its own
restricted NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY on Vercel only. ADC requires the
correct service identity/project/IAM/quota approval; a CI deployment credential
is not automatically a runtime ADC credential. TGOS legacy ADDR/MAP/THEME names
are not automatically mapped. TDX is a dedicated refresh consumer, not a new API
mount. Local NLSC/WRA need no R2 network credential. Supabase public config stays
on the frontend; JWT verification uses public configuration, no service-role key.

PROFESSOR_USER_DATABASE_URL is **not supported by the Stage2 installer**; retain
the accepted Stage4 user-credential restore path and request a narrowly reviewed
restore if it is actually lost. Do not rerun Stage4 provisioning or substitute
app/valuation/administrator URLs. Other supported core names can use their exact
Stage2 installation contract only for an approved recovery of existing values.

Install is stored-only. No provider is mounted/enabled until separate admission,
restrictions/quotas, exact mount/image/log scans and controlled recreation have
passed. Keep root-owned0700 stores, root:root0600 persistent files and exact
root:10001/0440 staged API files. Preserve DB admin/runtime separation. None of
these operations was executed during Stage5 preparation.

Nothing is READY_TO_RETIRE. See [retirement gate](cloud-retirement.md): direct
HTTPS, Preview/Production E2E, user persistence, ML/GIS, all credential dependencies,
reboot survival and rollback must pass before cloud-specific access is retired.
