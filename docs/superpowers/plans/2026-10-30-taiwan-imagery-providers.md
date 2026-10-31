# Taiwan imagery provider implementation plan

**Goal:** Use on-demand NLSC PHOTO2 by default on Professor Server, support explicitly noncommercial CSRSR annual imagery, retain Earth Engine disabled unless explicitly selected and enabled.

**Base/worktree:** accepted Stage3/4A plus provider preparation `fae25daa6b1c8f1af5c32c64c32ae3570c1d37cb`; `/home/andy/.codex/worktrees/fce0/proptech-ai-copilot`; branch `server/taiwan-imagery-provider-20261030`. No hardening worktree, main checkout, existing frontend next-env, runtime or cloud mutation.

**Architecture:** Preserve POST latitude/longitude request. Provider-neutral metadata extends the response; existing EE metadata stays truthful. `SATELLITE_REFERENCE_PROVIDER` defaults to `nlsc_photo2`, with `csrsr_spot` and explicit `earth_engine` alternatives. Existing satellite anti-abuse admission remains required; no flag is enabled or host configuration applied. CSRSR additionally requires `CSRSR_SPOT_NONCOMMERCIAL_USE=true`; controlled `CSRSR_SPOT_YEAR` defaults2025 and must be advertised by capabilities. Taiwan requests use bounded single-flight only, without completed image caching. EE alone keeps its existing cache and process isolation.

**Shared contract:** New optional/nullable-compatible response metadata: provider (`nlsc_photo2|csrsr_spot|earth_engine|unknown`), source_type (`orthophoto|satellite|null`), dataset_or_layer, observation_date nullable, vintage nullable (annual string), date_precision (`unknown|year|range|day`), processing_method, center nullable, bbox nullable (four3857 numbers), bbox_crs nullable, usage_restriction nullable. Existing dataset/source/attribution/limitations/disclaimer/status/reason/image remain. window_start/end and cloud_filter_percent become nullable for non-EE. Existing aoi_radius_m500 and 512JPEG transport remain. No raw imagery persistence in cases/browser storage.

## Tasks

- [x] Backend transport/adapters and synthetic security tests: strict HTTPS hosts/no redirects, fixed PHOTO2 WMS3857 request, CSRSR safe capabilities/year/zoom and bounded tile composition, Pillow decode/NoData/byte/pixel/deadline/parallel ceilings. Normal CA validation only; no TLS flag relaxation. Models: `services/imagery_reference.py`; providers: `services/imagery_providers.py`; HTTP: `services/imagery_http.py`.
- [x] Integrate provider selector/service/response metadata; skip all EE manager resolution/start in Taiwan mode; preserve existing guards and EE explicit-mode regressions. Accurate provider usage/config/observability, no image persistence or Taiwan completed-result cache.
- [x] Frontend metadata/type/presentation helpers and meaningful focused unit tests: neutral initial/error state, orthophoto vs satellite/year wording, only show real EE cloud metadata, manual trigger/race protection, no Saved Case image storage. Only related component/API/types/i18n/helpers/tests change.
- [x] Document local-only smoke/profile/transport checks and limitations; add sanitized acceptance evidence. Run focused backend/frontend tests, typecheck, affected lint, diff/secret checks, independent review; create ONE local commit after all required checks pass.

## Security and verification rulings

- Docker socket is not accessible to this agent. Never use sudo/inherit operator tickets. Current source backend Dockerfile uses Python3.12; actual active image/Python/TLS must be verified through an operator read-only command if access remains unavailable.
- Host Python3.14 audit hit a NLSC certificate `Missing Subject Key Identifier`; normal curl succeeded. Use normal validating Python HTTP transport and fail closed on TLS error; do not introduce insecure fallback, HTTP downgrade, verify=False or changes to SSL verify flags merely to pass.
- User authorizes live on-demand service integration. No bulk/offline/persistent imagery mirror; CSRSR competition restriction must be explicit. No new credentials, no EE ADC import/activation, no effect on risk scoring.
- Unit tests use synthetic images and injected HTTP only; zero real-provider requests during test suites. Separate optional low-volume TLS/read-only probes must be reported distinctly.
- Only this plan's final combined work is committed; subagents must not commit or change main/hardening trees. User's ONE local commit requirement overrides per-task commit conventions.
