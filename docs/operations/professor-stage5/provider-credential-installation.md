# Provider credential migration and operator installation

**Superseded policy:** the empty required set below described the earlier narrow
runtime profile. The user now requires backend provider credentials to migrate
even while disabled. Use [required provider migration](required-provider-migration.md)
and `--migrate-all`; this document remains historical workflow evidence.

**Current required install set: empty. No operator installation is needed.**
The current six API credential files and DB-only administrator mounts have
accepted Stage2/4 metadata evidence. No file content was read to prepare this
plan. Actual live cloud inventories remain incomplete; unknown is not missing.

The names-only [migration JSON](../../../reports/professor-stage5-ingress/credential-migration-plan.json)
and [CSV](../../../reports/professor-stage5-ingress/credential-migration-matrix.csv)
classify every one of the 333 prior-audit environment/config identifiers and 9
file-only contracts using the requested classes:

- ALREADY_ON_PROFESSOR_SERVER: accepted receipt evidence for the named current
  credential/public verification metadata or DB-only admin mount. Not a fresh
  privileged host inspection.
- BROWSER_PUBLIC_ON_VERCEL: frontend-only public contract/destination; actual
  deployed Vercel environment-name inventory is still unknown.
- OPTIONAL_NOT_ENABLED: not required/admitted by the accepted profile; presence
  in protected/cloud stores is not inferred absent.
- MISSING_REQUIRED: explicit confirmed absence and a reviewed required backend
  consumer. **None confirmed.**
- LEGACY_CLOUD_ONLY: deployment/legacy contracts, not new Professor API mounts.
- READY_TO_RETIRE: **none**; public cutover and retirement approval have not passed.
- UNKNOWN_LIVE_METADATA: unresolved deployment/dependency or future nonsecret
  configuration; do not infer a missing or production-critical credential.

## Provider decisions

| Provider/configuration | Current migration class | Destination / rule |
|---|---|---|
| App, usage, valuation and user DB URLs; usage peer HMAC; pilot session signing key | ALREADY_ON_PROFESSOR_SERVER | Keep six existing files and separate principals; no password/signing rotation or provisioning |
| `SUPABASE_URL`, `SUPABASE_JWT_ISSUER`, `SUPABASE_JWT_AUDIENCE` | ALREADY_ON_PROFESSOR_SERVER | Public backend trust metadata/JWKS; no signing/service-role secret |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | BROWSER_PUBLIC_ON_VERCEL | Existing frontend identity config; preserve Supabase users |
| `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY` | BROWSER_PUBLIC_ON_VERCEL | Independently restricted browser key; never substitute server key |
| Google geocoding, Places, Routes: `GOOGLE_MAPS_API_KEY` | OPTIONAL_NOT_ENABLED | One canonical server-key contract; remain disabled without separate admission |
| `GOOGLE_APPLICATION_CREDENTIALS`, `EARTH_ENGINE_PROJECT` and documented EE identity | OPTIONAL_NOT_ENABLED | ADC identity/IAM review required; attached Cloud Run metadata ADC is not a portable local file |
| `TGOS_APP_ID`, `TGOS_API_KEY` | OPTIONAL_NOT_ENABLED | Canonical protected pair; legacy ADDR/MAP/THEME aliases are not automatically mapped |
| `TDX_CLIENT_ID`, `TDX_CLIENT_SECRET` | OPTIONAL_NOT_ENABLED | Future admitted snapshot producer only; never add to current API mounts |
| R2 credentials and bucket/endpoint/region contract | OPTIONAL_NOT_ENABLED | Local NLSC/WRA need none; archive/upload/CI consumers must be inventoried before retirement |
| Government local/open contracts | No missing credential established | Preserve supported runtime/archive distinction; no provider invented or enabled |
| GCP deployment keys/workload identity, Render deployment/base/build aliases, privileged legacy Supabase/cloud controls | LEGACY_CLOUD_ONLY or UNKNOWN_LIVE_METADATA per exact matrix name | Never copy into the API profile or revoke a shared identity without caller proof |
| Future public host/CORS configuration | UNKNOWN_LIVE_METADATA here | Owned by parallel hardening; no network or configuration change from this workflow |

See [deployed evidence](deployed-cloud-evidence.md) for the documented service
account, historical Render revision and explicit live/repository/unknown limits.

## One stored-only operator entry point

`scripts/ops/professor_provider_credentials.py` reuses the existing Stage2
hidden-TTY, protected-file import, credential validators and atomic root-owned
store writer. It adds no Docker, Compose, cloud, database, mount, stage,
generation, replacement or activation operation.

Read the current plan without root or secret access:

```bash
python3 -B scripts/ops/professor_provider_credentials.py --plan
```

The checked-in `config/professor-provider-install.plan.json` has `required: []`.
It is a reviewed fixed plan, not a discovery that every cloud credential has
migrated. Do not populate it merely because a cloud field is UNKNOWN.
No sudo command is required now, and the agent did not execute installation.

## Only after a missing required credential is proven

This is a future workflow, not authorization to install optional providers.

1. Record the exact consumer/requirement, names-only absence evidence, canonical
   Stage2 name and separate consumer/admission approval. Update and review the
   fixed plan entry as MISSING_REQUIRED, with `required_consumer_approved: true`,
   `absence_confirmed: true`, and input mode `hidden` or `protected_file`.
2. Use only a supported canonical **backend** credential. The validator rejects
   browser/legacy names, unknown fields, duplicates, optional/unapproved entries,
   and unsupported Stage4 user-DB recovery. Do not edit the allowlist to force
   unsupported recovery through the Stage2 installer.
3. For ordinary single-line provider credentials, the one operator command is:

   ```bash
   sudo python3 -B scripts/ops/professor_provider_credentials.py --install-required
   ```

   Values are entered directly in the operator terminal with echo disabled.
   No pipes, shell tracing, values in arguments/environment, agent chat or
   clipboard/evidence exports. ADC JSON requires a protected file instead.
4. Protected imports use the **same entry point**, adding one path-only option
   per planned file input:

   ```bash
   sudo python3 -B scripts/ops/professor_provider_credentials.py --install-required --from-file GOOGLE_APPLICATION_CREDENTIALS=/root/protected-provider-import/earth-engine.json
   ```

   This example applies only to a separately approved missing ADC file; no such
   file is currently required. The source must already be a private regular
   operator/root-owned file, mode0400/0600, outside Git, `/dev`, and X9. Existing
   Stage2 checks reject unsafe ownership, parents, symlinks, links and storage.
   Do not create a new service-account key just to satisfy the example.
5. Core DB/HMAC/session recovery requires protected-file mode and the **same
   accepted backup material**, never newly generated passwords or signing keys.
   `PROFESSOR_USER_DATABASE_URL` remains the Stage4-specific recovery boundary;
   the wrapper refuses it. If it is actually lost, prepare one narrowly reviewed
   Stage4 restore rather than provisioning again or substituting an admin URL.
6. All destinations are checked for absence before asking for values; all inputs
   validate before any secret is written. New files use Stage2 root:root0600
   under `/etc/proptech-selfhost/secrets` with root-owned0700 directory. Existing
   files, including symlinks, are refused; replacement is not supported.
7. Output contains only fixed status/reason codes and credential **names**. If
   a write fails partway, `stored_names` identifies successful stored-only files.
   Nothing activates; do not delete secrets or bypass existing-file refusal on
   retry. Review the remaining missing set before another operator run.

Stored-only completion does not create `/run` files, mount secrets, alter runtime
configuration, admit a provider, call a provider or recreate any container.
Secrets remain outside Git/build context/image layers and frontend configuration.
A separate reviewed consumer/mount/image/log validation and controlled activation
must precede use. market_ops and paid/optional providers remain disabled.

No credential is ready for retirement. Preserve all cloud services/credentials
until the [cutover gates](provider-cutover-dependencies.md) and explicit approval.
