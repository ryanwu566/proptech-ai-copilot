# Earth Engine keyless ADC implementation plan

**Goal:** Replace the Professor installer’s service-account private-key requirement with keyless ADC impersonation, without installing credentials or activating a provider.

**Architecture:** Keep the existing `google.auth.default()` → `ee.Initialize(credentials=..., project=...)` adapter. Admit only bounded `impersonated_service_account` ADC with an authorized-user refresh source and the exact existing Earth Engine service account. Persist the protected ADC refresh material, never access tokens or service-account private keys. WIF remains the preferred future alternative if user-session policy prevents unattended refresh; no renewable external identity is currently evidenced.

**Constraints:** Preserve `iam.disableServiceAccountKeyCreation`; no IAM/cloud/runtime changes, real credential reads, paid calls, sudo, network configuration, frontend edits or push. Supplied refresh tokens remain secrets. Runtime provider flags stay disabled. Org reauthentication and real reboot acceptance stay pending.

## Tasks

- [x] Add failing tests for impersonated ADC acceptance, fixed target/endpoints, unknown fields/types, private-key rejection, scalar leak scanning and library loading/refresh using synthetic transports only.
- [x] Implement one strict offline ADC validator shared by Stage2/Stage5. Update the installer scanner to include nested refresh token/client secret independently of JSON formatting.
- [x] Verify actual installed google-auth and Earth Engine compatibility using synthetic ADC; retain existing single-attempt refresh and sanitized failure behavior.
- [x] Document one protected ADC preparation/import workflow, least-privilege IAM prerequisites, session-policy constraints and reboot restoration boundaries. Update names-only policy/evidence.
- [x] Run focused tests/static checks, independent security review, then create a local commit. Do not run credential migration or provider activation.

## Decisions and verification ledger

- User selected keyless ADC/service-account impersonation; no further design approval is required by the task.
- Existing adapter already discovers ADC and refreshes credentials; no replacement auth stack or GCP SDK in the runtime image is needed.
- Persisted authorized-user refresh credentials permit refresh after process/reboot without an interactive shell while valid. They cannot defeat revocation or organizational reauthentication. Unattended production acceptance is explicitly pending those checks; never weaken policy to pass.
- Current development test environment: `/tmp/proptech-integration-venv` has google-auth2.62.0, Earth Engine1.7.50 and pytest9.2.0. Actual active image was not rebuilt or changed.

- RED→GREEN: original keyless tests failed31 cases against the private-key-only installer, then passed; reboot-hook tests failed4 before implementation; actual image ADC probe tests failed2 before implementation. Empty optional account regression failed before the compatibility fix.
- Final focused validation: 250 passed; one pre-existing Starlette/httpx deprecation warning. AST/embedded Python/JSON/literal scanner/diff checks pass. Independent review PASS after the optional-account fix, with106 tests independently rerun.
- Operator auth command remains NONE until approved source ADC, CLI availability and source IAM are established. The conditional commands and required role are documented; no real credentials or privileged action were used.
