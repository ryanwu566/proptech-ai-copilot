# Required backend provider credential migration

This policy supersedes the earlier “optional provider, no credential needed on
server” migration policy. **All listed backend credentials must be stored on
Professor Server now, even while their providers remain disabled.** Storage,
isolated readability and provider functional acceptance are separate gates.

**Earth Engine policy update:** use [keyless ADC impersonation](earth-engine-keyless-adc.md).
Service-account private-key JSON is now rejected; preserve the organization key
creation restriction. Historical receipts do not imply a portable key exists.

**Independent installation is now preferred:** [provider commands](independent-provider-installation.md)
install/verify Google, TGOS, TDX, R2 and OpenAI one at a time. Earth Engine is
PENDING_IAM and does not block those commands. The full-mode command below is
retained for an explicitly complete population only.

The agent has prepared and tested the workflow; it has not read any real key,
run sudo, installed a credential or executed host Docker validation. Protected
provider-store metadata is inaccessible in this session. The preparation report
therefore preserves filesystem UNKNOWN. Its MISSING classification means the
required migration has not been accepted, not proof that an existing file is
absent. The root operator workflow discovers and preserves existing material
before asking for any value.

## Required protected storage

| Consumer | Canonical names | Protected filenames |
|---|---|---|
| Google server geocoding, Places, Routes | `GOOGLE_MAPS_API_KEY` | `google_maps_api_key` — shared actual backend contract, not three invented aliases |
| Earth Engine | `GOOGLE_APPLICATION_CREDENTIALS`, `EARTH_ENGINE_PROJECT` | `earth_engine_adc_json`, `earth_engine_project` |
| TGOS | `TGOS_APP_ID`, `TGOS_API_KEY` | `tgos_app_id`, `tgos_api_key` |
| TDX | `TDX_CLIENT_ID`, `TDX_CLIENT_SECRET` | `tdx_client_id`, `tdx_client_secret` |
| R2 | `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT`, `R2_BUCKET`, `R2_REGION` | `r2_access_key_id`, `r2_secret_access_key`, `r2_endpoint`, `r2_bucket`, `r2_region` |
| OpenAI | `OPENAI_API_KEY` | `openai_api_key` |

Nine secret files use the existing `/etc/proptech-selfhost/secrets` store.
Four public provider settings use the companion protected root configuration
directory `/etc/proptech-selfhost/provider-config`. Both directories are
root-owned0700 and files root:root0600. Settings are never echoed. Keeping public
settings separate avoids treating common values such as R2 region as credentials
in the existing Stage2 whole-secret-store leak scanner.
The Stage2 catalog's historical `stage1_needed` or optional-activation fields
do not exempt these credentials from this required-storage policy.

Read-only staged copies are separated by provider under
`/run/proptech-selfhost/secrets/providers/{google,earth_engine,tgos,tdx,r2,openai}`.
Directories remain root-owned0700; files root:10001/0440. Individual files are
bound into temporary verification containers. No broad directory is mounted
into the live API, and no new provider mount or environment value is installed
there. Existing core files/mounts/inodes and DB admin separation are preserved.

The six accepted runtime URLs/HMAC/session files and DB admin material are read
and validated only inside the operator process and never replaced or generated.
The accepted Supabase issuer/audience/project metadata must remain unchanged.
Supabase remains identity authority. No Supabase signing/service-role key or
user/password migration is requested.

Browser-only `NEXT_PUBLIC_SUPABASE_URL`, publishable/anon configuration, Google
browser key and `NEXT_PUBLIC_API_BASE_URL` stay on Vercel/browser. The backend's
public Supabase issuer/JWKS configuration is retained; browser keys are never
imported as server credentials. Legacy cloud deployment aliases are not runtime
ADC or API credentials; retirement remains separately gated.

## Explicit complete-population command (not required for independent providers)

Before running, have the actual existing backend credentials available in an
operator-owned terminal, and approved Earth Engine impersonation ADC
in a protected file outside Git, `/dev` and X9. Do not paste any value into
Codex. Do not put values in shell arguments, environment exports, logs or Git.
The installer never creates a Google service-account key or changes IAM. Cloud
Run attached metadata ADC is not a portable credential file. If no approved
keyless source identity exists, the workflow fails closed until that dependency is
resolved through the separately approved identity process.

```bash
sudo python3 -B /home/andy/.codex/worktrees/7d59/proptech-ai-copilot/scripts/ops/professor_provider_credentials.py --migrate-all
```

This is the complete-population mode of the same operator entry point. Use
`--provider google|tgos|tdx|r2|openai` independently while Earth Engine is pending.
The old `--install-required` mode is a
legacy narrow core-recovery plan and does not satisfy the new provider policy.
For a nonprivileged names-only preview use `--migration-plan` instead.

Existing valid persistent files win. Identical existing staged files can be
adopted. Unsafe metadata or conflicting values are refused, never overwritten,
rotated, chmodded into acceptance or replaced with a newly generated value.
Missing single-line values use the existing hidden terminal input. Missing ADC
requests a hidden **protected filename**, not JSON pasted into the terminal.
All inputs validate before secret files are written.

The first operator attempt refused during public-configuration preflight with
`provider_guard_unavailable`, before any input or provider write. The verifier
had incorrectly required the optional `SUPABASE_URL` alias; the accepted Stage4A
profile uses explicit issuer/audience. The repaired guard accepts the absent
alias while still requiring the exact canonical issuer/audience and every
disabled-provider flag. A present conflicting alias remains forbidden. The old
generic receipt does not name its failing field; the compatibility defect is
reproduced against the accepted profile, and new refusals record the missing
mandatory configuration NAME only.

The receipt confirms all13 managed provider secret/config destinations were
absent at that attempt. Approved source values still need private operator
input; no source credential or portable ADC file was discovered by the agent.
Use the existing hidden/protected-file workflow above after the repaired script
is reviewed. Workflow readiness is not proof of source availability, functional
provider acceptance or completed migration. The agent has not retried migration.

Protected file sources must be regular, single-link, mode0400/0600 and owned by
root or the sudo operator, with safe parent directories. The same command accepts
path-only imports such as `--from-file GOOGLE_APPLICATION_CREDENTIALS=/root/provider-import/adc.json`;
additional `--from-file NAME=PATH` options can replace other hidden prompts.
Existing validated server material is retained even if an import was supplied;
this workflow is not a rotation tool. Source files are read-only and preserved.

## Operator-only verification

The root process reads actual values internally; it never prints, records or
returns them or their secret-derived fingerprints. It performs no provider API
calls. Before storing new files it verifies:

1. One running local Compose API, its immutable image ID, unchanged Supabase
   public authority and disabled provider/market_ops guards. Live API mounts
   cannot cover the provider store or any ancestor/descendant of staged storage.
2. Existing core/private metadata and matching persistent/staged runtime values.
3. Full tracked current Git source bytes through pinned no-symlink reads, without
   text filters, using known credentials/encodings and private-key signatures.
4. All layers/config/history of the existing active image through the accepted
   streaming Docker/OCI scanner, without extracting or writing an image export.
   ADC's nested refresh token/client secret and their encodings are included.
   Literal private-key detection remains active independently. Public
   settings such as R2 region are excluded from known-secret matching.
5. Active Docker environment and all available Compose-project container logs,
   including stderr. Scan limits, unsupported archives, unreadable sources/logs
   or detected values fail closed; raw command output is never exported.

It then stores/stages required files and runs six temporary validation
containers, one per provider group. They use the already-local immutable image,
fixed Python entrypoint, nonroot10001:10001, read-only filesystem, network none,
no capabilities/privilege escalation, no log driver, 128MiB/0.5CPU/32PID limits
and a 45-second command timeout. Images are never built or pulled. No application
startup, Docker socket, database, dataset, public port or secret environment
variable is passed to a probe. Owned CID/receipt labels restrict cleanup to the
temporary verifier containers, including timeout/error cleanup.

The process rechecks the live API identity/guards and core metadata before
accepting. No existing service, volume or listener is recreated or changed.
Scans stream in memory; unsupported/over-limit inputs refuse rather than pass
partially. No Git/image/log scan can prove the absence of every possible unknown
encoding; the receipt records the supported known-value/signature scope.

Sanitized evidence is root-owned under
`/var/backups/proptech-selfhost/stage5-provider-credentials/<timestamp-random>/acceptance.json`.
It separates stored format/private metadata, identical read-only staging,
isolated readability, leak scans and **provider functional tests NOT_RUN**.
Success is `PASS_MIGRATED_PROVIDERS_DISABLED`. PRESENT_AND_VALIDATED here applies
to those storage checks, not an available/authenticated/paid production provider.

Failure never activates a provider or deletes/rolls back valid secrets. It may
leave newly stored/staged files protected and disabled if later visibility
validation fails; these become PRESENT_NOT_VALIDATED. The same command reuses
identical valid material on retry. Review the sanitized failure before changing
credentials; do not bypass conflict or scan gates. No automatic retirement.

Persistent files survive reboot; staged files are volatile. The prepared
`--stage-stored-providers` hook restores provider files from persistent storage
without prompts/network/Docker. The parallel hardening owner must order it after
core secret restoration and before any admitted consumer startup. This task adds no systemd,
NGINX, firewall, DNS, WAN/router or Vercel change. It does not modify `/dev/sda`,
X9, serving transactions, databases or existing Docker volumes.

For partial installation use `--stage-provider NAME` per configured provider;
the full restore hook requires all providers and is not appropriate while
Earth Engine is pending. No systemd/service change is applied by this task.
