# Professor adoption and final retirement matrices

Preparation only. No runtime, credentials, database, schedule, network, Vercel, Cloud Run or Render change was made. **No service or credential is retirement-ready.**

Provider-only continuation: [cutover dependency checklist](provider-cutover-dependencies.md)
and `provider-cutover-acceptance.json` record newer public route and manual-run
observations, exact missing receipts and per-platform CSVs. Names/identity/callers
remain separate gates. Parallel hardening is outside this task's ownership.

`migrated=YES` means the specifically named local replacement exists in accepted local evidence. `tested=YES` uses the named local capability or accepted private DB probe only. Neither means production callers were cut over or all remote state was migrated. Authorized provider session/persistence and public E2E remain NO in this matrix.

Full machine material:

- [Adoption and retirement JSON](../../../reports/professor-stage5-ingress/adoption-retirement-plan.json)
- [Retirement CSV](../../../reports/professor-stage5-ingress/retirement-readiness-matrix.csv)
- [Provider-to-secret/service/job/data/API CSV](../../../reports/professor-stage5-ingress/professor-adoption-matrix.csv)

## Cloud Run

| Dependency | Replacement | Migrated | Tested | Retirement-ready |
|---|---|---|---|---|
| Private API baseline availability | accepted Professor API | YES | YES | NO |
| Local NLSC/RIS/WRA replacement | verified local datasets and existing APIs | YES | YES | NO |
| Local ML replacement | accepted pinned ML companion | YES | YES | NO |
| Supabase-backed authorized user flows | accepted Stage4 backend; real provider/caller migration acceptance pending | NO | NO | NO |
| Application/usage/valuation/user runtime credentials | existing six-file Stage2/4 profile | YES | YES | NO |
| Public deployed callers | direct NGINX HTTPS plus Vercel Preview/Production | NO | NO | NO |
| Unique remote mutable data and background users | verified Professor data authority and scoped local jobs | NO | NO | NO |
| Reboot / trusted TLS renewal / rollback | reviewed persistent restoration and service ordering | NO | NO | NO |
| Provider keys and ADC/service identity/IAM | protected optional provider files and individually approved IAM | NO | NO | NO |
| Current/retained revision and rollback inventory | verified cloud metadata plus retained Professor release artifacts | NO | NO | NO |

## Render

| Dependency | Replacement | Migrated | Tested | Retirement-ready |
|---|---|---|---|---|
| Private API baseline availability | accepted Professor API | YES | YES | NO |
| Local NLSC/RIS/WRA replacement | verified local datasets and existing APIs | YES | YES | NO |
| Local ML replacement | accepted pinned ML companion | YES | YES | NO |
| Supabase-backed authorized user flows | accepted Stage4 backend; real provider/caller migration acceptance pending | NO | NO | NO |
| Application/usage/valuation/user runtime credentials | existing six-file Stage2/4 profile | YES | YES | NO |
| Public deployed callers | direct NGINX HTTPS plus Vercel Preview/Production | NO | NO | NO |
| Unique remote mutable data and background users | verified Professor data authority and scoped local jobs | NO | NO | NO |
| Reboot / trusted TLS renewal / rollback | reviewed persistent restoration and service ordering | NO | NO | NO |
| Render provider/env-group/file inventory | verified names-only inventory and Stage2 adoption | NO | NO | NO |
| commute maintenance workflow | proposed local manual one-shot; not installed; persistent snapshot producer plus API loader/reload contract; separate CLI cannot update API process memory | NO | NO | NO |
| market maintenance workflow | proposed local manual one-shot; not installed; reviewed local operations adapter and scoped role | NO | NO | NO |
| coverage maintenance workflow | proposed local manual one-shot; not installed; reviewed local operations adapter and scoped role | NO | NO | NO |

## Credential adoption destinations

| Provider | Names only | Target consumer/service | Data path/schema | API capability |
|---|---|---|---|---|
| Professor runtime credentials | DATABASE_URL, API_USAGE_DATABASE_URL, API_USAGE_PEER_HMAC_KEY, PILOT_SESSION_SIGNING_KEY, VALUATION_DATABASE_URL, PROFESSOR_USER_DATABASE_URL | API six-file profile; admin/init secrets excluded; existing api/postgres services | proptech_app / proptech_api_usage / proptech_valuation | existing application and serving APIs |
| Google Maps / Places / Routes | GOOGLE_MAPS_API_KEY | separately admitted backend provider only; existing bounded adapters | no local credential-bearing dataset | geocoding / places / routes |
| Google browser maps | NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY | Vercel frontend only; existing browser integration | frontend public configuration only | Maps JavaScript / Street View |
| Earth Engine | GOOGLE_APPLICATION_CREDENTIALS, EARTH_ENGINE_PROJECT | separately admitted satellite worker; existing bounded Earth Engine worker pool | protected ADC file; no image-layer copy | optional satellite reference |
| TGOS | TGOS_APP_ID, TGOS_API_KEY | separately admitted backend geocoder; existing canonical TGOS adapter | no transformed source archive | optional address resolution |
| TDX | TDX_CLIENT_ID, TDX_CLIENT_SECRET | future restricted snapshot producer, never current API profile; commute persistence adapter required | /srv/proptech-runtime/commute (PROPOSED, not created) | optional commute snapshot consumer |
| Cloudflare R2 | R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY | optional archive/upload or remote-artifact consumer; separately admitted operations only | /srv/proptech-data/DB local NLSC/WRA remain sufficient | no R2 dependency for active local NLSC/WRA |
| Supabase browser configuration | NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY | Vercel frontend only; existing Supabase identity SDK | identities retained in accepted Supabase project | register/login/refresh |
| Supabase server verification | SUPABASE_URL, SUPABASE_JWT_ISSUER, SUPABASE_JWT_AUDIENCE | FastAPI public JWKS verifier; existing Stage4A identity adapter | Professor application-user schema; no Supabase signing/service-role secret | session/profile/saved cases |
| Government local/open-data and archives | No provider credential identified | existing supported GIS/RIS consumers; read-only local artifacts or existing admitted open-data contract | /srv/proptech-data/DB; RIS in proptech_app | NLSC/RIS/WRA active; unsupported archives stay explicit |
| Other optional / restricted provider credentials | OPENAI_API_KEY, NLSC_GATEWAY_CLIENT_TOKEN | separately reviewed consumer only; no new provider activation | protected Stage2 file contract if admitted | no current-profile requirement |

All persistent secret destinations use the accepted `/etc/proptech-selfhost/secrets` store. The CSV/JSON lists exact canonical file names. Only the existing six files are API mounts; optional worker credentials must use a separately reviewed, restricted worker identity and staging directory. Browser public configuration stays frontend-only. No legacy alias fallback, password migration, provider activation or new timer is introduced.

Current required files are proven by hash-bound accepted Stage4A receipts, not a fresh root inspection. Optional store presence and unique production cloud dependencies remain unverified. No required current-profile credential is confirmed missing. Existing safe recovery/install instructions are in [credential evidence collection](credential-evidence-collection.md); no new privileged installer is warranted now.

## Workflow decisions

For all three whole workflows the self-hosted migration target is **A: move to Professor Server** if the capability is retained. The **current interim decision is C: leave existing external definitions and their current activity state unchanged** until local replacements are validated. This does not request a dispatch or continuation of an inactive job. No whole workflow is selected for B retirement without usage/owner evidence. The already-provisioned coverage bootstrap substep is not carried forward to Professor Server.

| Workflow | Selected target | Interim handling | Proposed local unit | Timer |
|---|---|---|---|---|
| .github/workflows/refresh-commute-snapshot.yml | A: move | C: unchanged | proptech-commute-snapshot.service (not installed) | None; manual cadence |
| .github/workflows/refresh-market-read-model.yml | A: move | C: unchanged | proptech-market-reconcile.service (not installed) | None; manual cadence |
| .github/workflows/reconcile-market-coverage.yml | A: move | C: unchanged | proptech-coverage-audit.service (not installed) | None; manual cadence |

See [local maintenance adoption](local-maintenance-adoption.md) for the in-memory commute persistence gap, readonly serving role constraints and prohibition on copying the legacy destructive refresh. No existing serving role gains writes.

## Facts still required for full inventory

Cloud Run: actual env/secret-reference names across retained revisions; attached service-account identity; ADC source; effective IAM/API restrictions; deployed callers, schedulers/jobs/background consumers; remote mutable state and rollback identity. Source code cannot prove these deployed facts.

Render: actual service/environment-group/secret-file names and scopes; current callers, maintenance activity and provider restrictions; unique remote state and rollback identity. `render.yaml` and GitHub source references are declarations only.

The current public Vercel asset observation confirms a Cloud Run origin reference in release9cc40d6; it is not a browser API trace or secret inventory. The bounded GitHub sample contains no matching maintenance runs among50 of1490 repository runs; that is not proof the jobs are unused. Per-workflow history access was unavailable. See the saved [public caller observation](../../../reports/professor-stage5-ingress/public-caller-references.json) and [activity observation](../../../reports/professor-stage5-ingress/maintenance-activity-observation.json).

Names-only exports were requested through the user input channel; no credential values were requested. Available tools cannot list the needed live credential inventories. This remains an external evidence blocker, independent of WAN.

## Required retirement proof

- outside-LAN trusted Professor HTTPS.
- Vercel Preview and Production authenticated E2E.
- profile/saved-case ownership and persistence.
- ML/GIS/Market/Valuation accepted behavior.
- all required credential dependencies adopted.
- reboot and renewal acceptance.
- no unique remote state/caller remains.
- explicit retirement approval.

Pre-ingress host/credential reviews and later retirement gates are distinct. Keeping an optional legacy maintenance definition temporarily external does not make it a dependency of the current accepted Professor local profile. Its replacement/admission or explicit retirement must be settled before cloud shutdown. Nothing in this matrix enables public maintenance, paid providers, market_ops or ingress.
