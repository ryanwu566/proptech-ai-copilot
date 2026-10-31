# Professor Earth Engine: keyless ADC impersonation

This supersedes every Professor instruction requiring a service-account private
key. Preserve `iam.disableServiceAccountKeyCreation`. No policy exception, key
creation, IAM change, provider activation or paid computation occurs here.

Earth Engine is currently **PENDING_IAM**. Use [independent provider installation](independent-provider-installation.md)
for Google/TGOS/TDX/R2/OpenAI now. This IAM gate does not block their migration.
The commands below describe Earth Engine preparation after approval; partial
deployments use `--stage-provider NAME`, not the all-provider restore hook.

## Identity, IAM and Python support

Existing display name: **PropTech Render Earth Engine**. Repository identity:
`proptech-render-earth-engine@project-3bd34c3e-daee-493f-ad6.iam.gserviceaccount.com`.
Project: `project-3bd34c3e-daee-493f-ad6`. The validator pins this exact target;
the operator must reconcile the email/display name against the existing account.
Live IAM has not been inspected. No account is created or substituted.

The source operator identity needs `iam.serviceAccounts.getAccessToken` **on
this service account**. Normally grant `roles/iam.serviceAccountTokenCreator`
on that single account, after reviewing existing bindings. An equivalent custom
role can suffice. Service Account User/`actAs` alone is insufficient. Confirm
`iamcredentials.googleapis.com` is enabled; enabling it needs separate admin
approval and `serviceusage.services.enable`, never a runtime admin grant.
[Google's exact impersonation prerequisites](https://docs.cloud.google.com/docs/authentication/use-service-account-impersonation).

The target retains its Earth Engine project access: at least Earth Engine
Resource Viewer (`roles/earthengine.viewer`) and `serviceusage.services.use`
on the consumer project (commonly `roles/serviceusage.serviceUsageConsumer`).
Confirm Earth Engine API enablement, project registration and applicable
organization/VPC/billing policy. Do not automatically grant Owner/Editor or
asset-write privileges. [Earth Engine access requirements](https://developers.google.com/earth-engine/guides/access_control).

The adapter already calls `google.auth.default()` with Earth Engine and
cloud-platform scopes, then `ee.Initialize(credentials=..., project=...)`.
Google-auth loads impersonated ADC, refreshes the user source and requests a
short-lived target token (default3600seconds). No runtime gcloud or interactive
login process is needed. Existing single-attempt refresh and sanitized failures
remain unchanged. [Earth Engine ADC support](https://developers.google.com/earth-engine/guides/auth).

Tests exercised actual google-auth2.62.0/Earth Engine1.7.50 with synthetic
transports only. The operator migration additionally verifies `google.auth.default()`
inside the existing immutable API image, with network disabled, no refresh and
no Earth Engine initialization. Missing SDK support fails closed.

## Private operator preparation and import

No approved protected source file is confirmed. gcloud is absent from this
agent's host PATH. Use an operator machine with an approved CLI, or separately
install it on Professor Server. Nothing installs/authenticates automatically.

In a private terminal without recording/tracing, set umask077 and select a new
operator-owned0700 gcloud directory outside Git/X9 using `CLOUDSDK_CONFIG` (a
nonsecret path). Do not repurpose HOME or CODEX_HOME. A dedicated directory
prevents overwriting existing ADC. After IAM approval, the operator can run:

```bash
gcloud --project=project-3bd34c3e-daee-493f-ad6 auth application-default login --disable-quota-project --impersonate-service-account=proptech-render-earth-engine@project-3bd34c3e-daee-493f-ad6.iam.gserviceaccount.com
```

Use Google's private browser/remote-browser flow as needed. Never paste auth
URLs/codes, tokens or JSON into Codex, screenshots, logs, Git, arguments or
environment values. Do not use print-access-token or export a target token.
The command makes authentication/token requests, not Earth Engine computations.
See [ADC login behavior](https://docs.cloud.google.com/sdk/gcloud/reference/auth/application-default/login).

Output: `application_default_credentials.json` in that dedicated directory.
Expected type: `impersonated_service_account`, pinned IAM target URL, empty or
absent delegates, and nested `authorized_user` source with client ID, client
secret and refresh token. The refresh token/client secret remain protected
secrets; this is not a secret-free file. No private key or cached access token
is accepted. Bare user ADC, alternate endpoints/targets, unknown fields,
delegation chains, executable credentials and WIF currently fail closed.

Transfer through a protected operator-controlled channel if prepared elsewhere.
Proposed import path, **not an existing detected file**:
`/root/provider-import/earth-engine-impersonation-adc.json`. Parent root0700;
file root:root0600/0400, regular single-link, no symlinks or writable parents.
Only the operator importer opens it; source is read-only and preserved.

After IAM approval, that file and Earth Engine project configuration are privately available:

```bash
sudo python3 -B /home/andy/.codex/worktrees/7d59/proptech-ai-copilot/scripts/ops/professor_provider_credentials.py --provider earth-engine --from-file GOOGLE_APPLICATION_CREDENTIALS=/root/provider-import/earth-engine-impersonation-adc.json
```

Persistent destination: `/etc/proptech-selfhost/secrets/earth_engine_adc_json`,
root:root0600. Staged destination:
`/run/proptech-selfhost/secrets/providers/earth_engine/earth_engine_adc_json`,
root:10001/0440, root0700 parent. Public project config remains separate under
`/etc/proptech-selfhost/provider-config`. The whole JSON and individual refresh
token/client secret, including supported encodings, are internally scanned
against Git/image/history/environment/logs. No values or credential-derived
fingerprints are returned. No rotation, live provider mount or activation occurs.

## Unattended operation and reboot

Persistent ADC works independently of an interactive shell, tmux, gcloud cache
or Codex; Python refreshes directly and keeps access tokens in memory. However,
source grants can expire, be revoked or require organizational reauthentication.
Verify refresh/session policy before claiming unattended production acceptance;
never weaken policy. [Google reauthentication](https://docs.cloud.google.com/docs/authentication/reauthentication).

The same installer now provides a provider-only no-network boot hook:

```bash
sudo python3 -B /home/andy/.codex/worktrees/7d59/proptech-ai-copilot/scripts/ops/professor_provider_credentials.py --stage-provider earth-engine
```

It requires core secret restoration to have prepared `/run/proptech-selfhost/secrets`
and a complete protected persistent Earth Engine group. It shares the migration
lock, restores only missing provider staging files, preserves existing inodes,
refuses conflicts and never prompts, calls Docker or adopts volatile material
back into an absent store. No services/systemd units are modified here.

The parallel hardening owner must order persistent storage → accepted core
restoration → provider hook → separately accepted consumer startup. This hook
is prepared, not installed/executed. It does not renew running container binds;
future provider activation requires separately reviewed recreation. Current
disabled runtime requires no provider mounts.

Before activation: prove real refresh, renewal after target-token expiry,
restart/reboot restoration and session-policy suitability. If recurring human
login is required, keep unattended acceptance blocked and use separately
reviewed WIF with a real renewable machine subject identity. None is evidenced
here. Do not substitute a static subject token or service-account private key.

Offline format/authority/scanner/SDK/adapter/simulated-reboot tests are complete.
Live credentials, IAM, active-image probe, real authentication, provider API
availability and actual reboot remain **NOT_RUN/PENDING**. Earth Engine stays off.
