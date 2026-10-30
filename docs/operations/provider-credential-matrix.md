# Provider credentials and configuration matrix — Stage5

**Current policy:** [required backend provider storage](professor-stage5/required-provider-migration.md)
supersedes the earlier optional-storage classification. All listed Google,
Earth Engine, TGOS, TDX, R2 and OpenAI credentials are required on Professor
Server even while disabled. Use the one `--migrate-all` workflow and the new
required-provider preparation receipt; earlier matrices remain dated evidence.

**Earth Engine:** the current installer accepts only [keyless ADC impersonation](professor-stage5/earth-engine-keyless-adc.md)
for the pinned existing service account and rejects private keys. The organization
key-creation policy remains enforced. Live source/IAM/unattended gates are pending.

**Install independently now:** [selected-provider commands](professor-stage5/independent-provider-installation.md)
keep Earth Engine PENDING_IAM while Google/TGOS/TDX/R2/OpenAI proceed. Migration
readiness is separate from actual installed credentials and provider activation.

The [provider migration and operator installation workflow](professor-stage5/provider-credential-installation.md)
adds the requested seven migration classes and one stored-only operator entry
point. It covers 333 environment/config names plus nine file contracts. The
reviewed required install set is empty; no credential or runtime change occurred.

The [deployed cloud evidence inventory](professor-stage5/deployed-cloud-evidence.md)
now labels every live/repository/historical/unknown assertion. It identifies the
documented Earth Engine identity, historical Render revision, three scheduled CI
consumers and conditional credential-retirement groups. Those facts do not turn
deployed credential-name inventories into verified presence.

The provider-only [cutover dependency closeout](professor-stage5/provider-cutover-dependencies.md)
adds exact deployed-metadata receipt requirements, alias/adoption decisions,
separate Cloud Run/Render retirement CSVs, public route-name observations and
complete API-visible manual workflow-run history. It changes no hardening or
runtime configuration. Actual deployed credential inventories remain UNKNOWN.

The [final adoption and retirement matrices](professor-stage5/adoption-retirement-matrix.md)
map each provider to a secret/configuration destination, local service/job,
data path/schema and API capability. They also record explicit A/C maintenance
workflow handling and all remaining proof before either cloud may be retired.
No full deployed-credential closure is inferred from names alone.

**Repository audit prepared; complete live audit remains BLOCKED.** No actual credential value, protected envfile content or private key was opened or exported. No provider, runtime, router, firewall, DNS or cloud deployment was changed.

## Exact audit scope and results

The expanded matrix records **333 environment/configuration identifiers**, plus 9 separate DB/TLS file contracts. It covers accepted Stage2 credentials/configuration, the hosted environment manifest, explicit source reads, Dockerfiles/Compose, Render declarations, Cloud Run/CI references and docs. Private env/credential paths are excluded before opening. Four tracked env examples are additionally audited by an indexed Git assignment-prefix projection: Git scans the example blobs, while Python receives names only, never RHS values. No actual host/worktree envfile or credential payload is opened by the auditor.

The accepted six active API credential files pass exact hash-bound Stage4A receipt and matching host/container metadata validation. No required current-profile secret is evidenced missing. This is accepted snapshot evidence, not a new privileged host inspection. Optional protected-store presence remains UNKNOWN where ordinary metadata access is denied.

**All four live scopes remain UNKNOWN:** Cloud Run, Render, Vercel and GitHub Actions. Cloud Run/Render/Vercel have no suitable authenticated tools here. The GitHub reader supports repository/branch/workflow metadata but explicitly excludes secrets APIs, so it cannot supply the required live credential inventory. Source declarations, `sync:false`, public HTTP responses and CLI absence never prove deployed secret presence/absence. Production-critical credentials on Professor Server remain **PARTIAL** until unique legacy-cloud dependencies are ruled out.

The Supabase connector confirms only the accepted public project URL and an empty Edge Function list. No keys, auth users, token values or database mutations were requested. Supabase stays identity authority; Professor PostgreSQL stays application-data authority.

Full sanitized matrix, with every requested column:

- [JSON dependency matrix](../../reports/professor-stage5-ingress/provider-dependency-matrix.json)
- [CSV dependency matrix](../../reports/professor-stage5-ingress/provider-dependency-matrix.csv)
- [Audit closure evidence](../../reports/professor-stage5-ingress/credential-audit-closure.json)
- [Credential-only companion matrix](../../reports/professor-stage5-ingress/provider-matrix.json) (credential subset; use expanded JSON/CSV for the complete repository dependency audit)

## Production requirement and classification

YES means required by the accepted local self-hosted profile or eventual direct browser HTTPS contract. It includes unconditional hosted-manifest requirements and accepted Stage2/4 safety configuration names. Some settings are runtime-derived/defaulted; YES does not mean a missing credential or an instruction to override defaults. Optional provider enablement remains NO and requires separate admission.

Allowed classes: PROFESSOR_SERVER_ACTIVE, PROFESSOR_SERVER_OPTIONAL, VERCEL_BROWSER_PUBLIC, LEGACY_CLOUD_ONLY, READY_TO_RETIRE, MISSING_REQUIRED and UNKNOWN. MISSING_REQUIRED requires a confirmed missing required secret, independently of old receipt availability. Inaccessible metadata stays UNKNOWN; root files unreadable by the API are unsafe. No credential is READY_TO_RETIRE.

| Credential/config | Provider / consumer | Current evidence | Target | Required production | Migration | Retirement |
|---|---|---|---|---|---|---|
| `DATABASE_URL` | Professor PostgreSQL / runtime | Professor Stage2 protected store/staging; PRESENT_ACCEPTED_RECEIPT | /etc/proptech-selfhost/secrets/app_database_url | YES | VERIFIED_ACCEPTED_STAGE4A_NOT_FRESH | NOT APPROVED |
| `API_USAGE_DATABASE_URL` | Professor PostgreSQL / runtime | Professor Stage2 protected store/staging; PRESENT_ACCEPTED_RECEIPT | /etc/proptech-selfhost/secrets/usage_database_url | YES | VERIFIED_ACCEPTED_STAGE4A_NOT_FRESH | NOT APPROVED |
| `VALUATION_DATABASE_URL` | Professor PostgreSQL / runtime | Professor Stage2 protected store/staging; PRESENT_ACCEPTED_RECEIPT | /etc/proptech-selfhost/secrets/valuation_database_url | YES | VERIFIED_ACCEPTED_STAGE4A_NOT_FRESH | NOT APPROVED |
| `PROFESSOR_USER_DATABASE_URL` | Professor PostgreSQL application-user persistence | Professor Stage2 protected store/staging; PRESENT_ACCEPTED_RECEIPT | /etc/proptech-selfhost/secrets/professor_user_database_url | YES | VERIFIED_ACCEPTED_STAGE4A_NOT_FRESH | NOT APPROVED |
| `API_USAGE_PEER_HMAC_KEY` | Professor PostgreSQL / runtime | Professor Stage2 protected store/staging; PRESENT_ACCEPTED_RECEIPT | /etc/proptech-selfhost/secrets/usage_peer_hmac_key | YES | VERIFIED_ACCEPTED_STAGE4A_NOT_FRESH | NOT APPROVED |
| `PILOT_SESSION_SIGNING_KEY` | Professor PostgreSQL / runtime | Professor Stage2 protected store/staging; PRESENT_ACCEPTED_RECEIPT | /etc/proptech-selfhost/secrets/pilot_session_signing_key | YES | VERIFIED_ACCEPTED_STAGE4A_NOT_FRESH | NOT APPROVED |
| `GOOGLE_MAPS_API_KEY` | Google geocoding / Places / Routes; same canonical server key | Professor optional protected store: UNKNOWN; actual cloud presence UNKNOWN | /etc/proptech-selfhost/secrets/google_maps_api_key | NO | NOT_ADMITTED_OPTIONAL | NOT APPROVED |
| `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY` | Google Maps JavaScript/Street View | Vercel browser/build declarations; accepted auth project metadata; actual env inventory UNKNOWN | frontend_build_configuration | NO | FRONTEND_ONLY_NO_SERVER_SECRET | NOT APPROVED |
| `GOOGLE_APPLICATION_CREDENTIALS` | Earth Engine / Google ADC | Professor optional protected store: UNKNOWN; actual cloud presence UNKNOWN | /etc/proptech-selfhost/secrets/earth_engine_adc_json | NO | NOT_ADMITTED_OPTIONAL | NOT APPROVED |
| `EARTH_ENGINE_PROJECT` | Earth Engine | Repository declarations only; live location UNKNOWN | not_admitted_or_no_runtime_file | NO | NOT_ADMITTED_OPTIONAL | NOT APPROVED |
| `TGOS_APP_ID` | Taiwan TGOS | Professor optional protected store: UNKNOWN; actual cloud presence UNKNOWN | /etc/proptech-selfhost/secrets/tgos_app_id | NO | NOT_ADMITTED_OPTIONAL | NOT APPROVED |
| `TGOS_API_KEY` | Taiwan TGOS | Professor optional protected store: UNKNOWN; actual cloud presence UNKNOWN | /etc/proptech-selfhost/secrets/tgos_api_key | NO | NOT_ADMITTED_OPTIONAL | NOT APPROVED |
| `TDX_CLIENT_ID` | Taiwan TDX | Professor optional protected store: UNKNOWN; actual cloud presence UNKNOWN | /etc/proptech-selfhost/secrets/tdx_client_id | NO | NOT_ADMITTED_OPTIONAL | NOT APPROVED |
| `TDX_CLIENT_SECRET` | Taiwan TDX | Professor optional protected store: UNKNOWN; actual cloud presence UNKNOWN | /etc/proptech-selfhost/secrets/tdx_client_secret | NO | NOT_ADMITTED_OPTIONAL | NOT APPROVED |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 | Professor optional protected store: UNKNOWN; actual cloud presence UNKNOWN | /etc/proptech-selfhost/secrets/r2_access_key_id | NO | NOT_ADMITTED_OPTIONAL | NOT APPROVED |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 | Professor optional protected store: UNKNOWN; actual cloud presence UNKNOWN | /etc/proptech-selfhost/secrets/r2_secret_access_key | NO | NOT_ADMITTED_OPTIONAL | NOT APPROVED |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase browser Auth | Vercel browser/build declarations; accepted auth project metadata; actual env inventory UNKNOWN | frontend_build_configuration | YES | FRONTEND_ONLY_NO_SERVER_SECRET | NOT APPROVED |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase browser Auth | Vercel browser/build declarations; accepted auth project metadata; actual env inventory UNKNOWN | frontend_build_configuration | YES | FRONTEND_ONLY_NO_SERVER_SECRET | NOT APPROVED |
| `SUPABASE_URL` | Supabase Auth JWT/JWKS | Professor protected nonsecret configuration per accepted Stage4A | protected_root_configuration | YES | ACCEPTED_METADATA_NO_PRIVATE_AUTH_KEY | NOT APPROVED |
| `SUPABASE_JWT_ISSUER` | Supabase Auth JWT/JWKS | Professor protected nonsecret configuration per accepted Stage4A | protected_root_configuration | YES | ACCEPTED_METADATA_NO_PRIVATE_AUTH_KEY | NOT APPROVED |
| `SUPABASE_JWT_AUDIENCE` | Supabase Auth JWT/JWKS | Professor protected nonsecret configuration per accepted Stage4A | protected_root_configuration | YES | ACCEPTED_METADATA_NO_PRIVATE_AUTH_KEY | NOT APPROVED |
| `SUPABASE_SERVICE_ROLE_KEY` | Unsupported legacy/admin Supabase credential | Legacy cloud/CI/unsupported references; actual presence UNKNOWN | Operator/CI only if separately retained; never Professor API | NO | NOT_PROFESSOR_API_RUNTIME | NOT APPROVED |
| `SUPABASE_JWT_SECRET` | Unsupported legacy/admin Supabase credential | Legacy cloud/CI/unsupported references; actual presence UNKNOWN | Operator/CI only if separately retained; never Professor API | NO | NOT_PROFESSOR_API_RUNTIME | NOT APPROVED |
| `NEXT_PUBLIC_API_BASE_URL` | Browser API routing | Vercel browser/build declarations; accepted auth project metadata; actual env inventory UNKNOWN | frontend_build_configuration | YES | AWAITING_APPROVED_PUBLIC_API_ORIGIN | NOT APPROVED |
| `API_ALLOWED_HOSTS` | application/runtime configuration | Repository declarations only; live location UNKNOWN | /etc/proptech-selfhost/runtime.env (nonsecret, reviewed consumer only) | YES | AWAITING_APPROVED_PUBLIC_API_ORIGIN | NOT APPROVED |
| `CORS_ALLOWED_ORIGINS` | application/runtime configuration | Repository declarations only; live location UNKNOWN | /etc/proptech-selfhost/runtime.env (nonsecret, reviewed consumer only) | YES | AWAITING_APPROVED_PUBLIC_API_ORIGIN | NOT APPROVED |
| `POSTGRES_SSLMODE` | application/runtime configuration | Repository declarations only; live location UNKNOWN | /etc/proptech-selfhost/runtime.env (nonsecret, reviewed consumer only) | YES | NONSECRET_CONFIGURATION_REVIEW | NOT APPROVED |
| `PGSSLROOTCERT` | PostgreSQL TLS | Professor protected nonsecret configuration per accepted Stage4A | protected_root_configuration | YES | ACCEPTED_METADATA_NO_PRIVATE_AUTH_KEY | NOT APPROVED |
| `ANTI_ABUSE_MARKET_OPS_DISABLED` | anti-abuse-market_ops | Repository declarations only; live location UNKNOWN | /etc/proptech-selfhost/runtime.env (nonsecret, reviewed consumer only) | YES | NONSECRET_CONFIGURATION_REVIEW | NOT APPROVED |
| `GCP_SERVICE_ACCOUNT_KEY` | Future hosting administration | Legacy cloud/CI/unsupported references; actual presence UNKNOWN | Operator/CI only if separately retained; never Professor API | NO | NOT_PROFESSOR_API_RUNTIME | NOT APPROVED |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | source/control-plane metadata | Legacy cloud/CI/unsupported references; actual presence UNKNOWN | Operator/CI only if separately retained; never Professor API | NO | NOT_PROFESSOR_API_RUNTIME | NOT APPROVED |
| `RENDER_API_KEY` | Future hosting administration | Legacy cloud/CI/unsupported references; actual presence UNKNOWN | Operator/CI only if separately retained; never Professor API | NO | NOT_PROFESSOR_API_RUNTIME | NOT APPROVED |
| `VERCEL_TOKEN` | Future hosting administration | Legacy cloud/CI/unsupported references; actual presence UNKNOWN | Operator/CI only if separately retained; never Professor API | NO | NOT_PROFESSOR_API_RUNTIME | NOT APPROVED |

## Provider-specific decisions

- Google geocoding, Places and Routes share the actual backend GOOGLE_MAPS_API_KEY consumer. Optional/paid consumers stay disabled. Browser Maps/Street View use the separate restricted NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY on Vercel only.
- Earth Engine uses an operator-managed ADC JSON file plus public project configuration and independently approved IAM/project access. CI deployment/workload credentials are not automatically runtime ADC. No sentinel GOOGLE_SERVICE_ACCOUNT_JSON alias is admitted.
- TGOS canonical pair is TGOS_APP_ID/TGOS_API_KEY. ADDR/MAP/THEME/APPID/APIKEY legacy spellings remain references, not automatic credential fallback. TDX keys belong only to a separately admitted snapshot-refresh consumer.
- NLSC/WRA current runtime uses immutable local bytes. R2 credentials are unnecessary for those paths, but remote/archive/CI dependencies cannot be retired without inventory evidence.
- Supabase public browser configuration remains on the frontend. Backend trust uses the accepted issuer/audience/public JWKS; no JWT signing secret or service-role key is required. Do not migrate passwords or alter existing users.
- ARDSWC/GeologyCloud existing open-data contracts and GSMMA/CWA archives do not establish an additional credential requirement. NLSC gateway credentials are optional and unadmitted. CWA1897–1989 remains unfilled.
- OPENAI_API_KEY and protected metrics/admin/refresh/cursor/acceptance credentials remain optional or operator-only. No provider admission, market refresh or market_ops enablement occurs.
- PostgreSQL serving/user/usage credentials remain separate. DB admin files are DB-only; initialization-only passwords never return to API consumers. Preserve DB/TLS identity and existing volumes.

## Installation and remaining evidence

No new credential is needed for current accepted local runtime. See [names-only evidence collection and conditional installation](professor-stage5/credential-evidence-collection.md) for exact scopes, safe hidden-TTY/protected-file commands and recovery constraints. These commands were not run.

PROFESSOR_USER_DATABASE_URL is handled by Stage4; the Stage2 installer does **not** support that name. Recover it only through a narrowly reviewed restore of accepted protected material, never by reprovisioning or substituting a privileged URL.

Cloud control-plane evidence is the remaining credential audit dependency. No cloud credential/service is approved for retirement. Keep [retirement gates](professor-stage5/cloud-retirement.md) and [Vercel cutover gates](professor-stage5/vercel-cutover.md); public ingress, production cloud config and server secrets remain untouched.

The [retirement dependency inventory](professor-stage5/retirement-dependency-inventory.md)
records exact Render refresh workflows and remaining Cloud Run/Render callers,
credentials, service identities and data gates. See the [no-WAN preparation
checklist](professor-stage5/no-wan-preparation.md): remaining blockers include
cloud/host metadata and reboot material recovery, not only router/WAN.
