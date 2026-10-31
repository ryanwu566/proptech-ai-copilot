# Independent provider credential migration

**Goal:** Install and validate Google, TGOS, TDX, R2 and OpenAI separately while Earth Engine remains PENDING_IAM.

**Architecture:** Add fixed `--provider`/`--stage-provider` selections to the existing operator entrypoint. Bound input, writes, metadata acceptance and isolated probes to that provider. Keep full Git/image/history/environment/log scans and include all other already-present provider credentials in the known-secret scanner without requiring missing providers. Preserve global runtime/Supabase/core guards, shared lock, protected ownership, exact complete selected groups, no overwrites and no activation. Legacy `--migrate-all` remains explicitly all-or-nothing; it is no longer needed for individual providers.

**Constraints:** No actual keys read or installed by the agent; no sudo/cloud/provider calls, paid activation, IAM changes, public/network/runtime changes, frontend modifications or push. Shared Google server key only. Earth Engine private keys stay forbidden. Operator attests Google key restriction to140.119.55.43 and Geocoding/Places(New)/Routes; offline storage validation does not independently prove console restrictions or provider API access.

- [x] Write failing scoped storage/CLI/orchestration tests; include missing Earth Engine, selected-pair atomic validation, unselected preservation, global known-secret scanning and concurrent changes.
- [x] Parameterize storage/runner/probe selection and retain full-mode compatibility. Add explicit selected-provider reboot restore, with existing full restore unchanged.
- [x] Update provider runbook, key restriction metadata and truthful Stage5 preparation evidence; do not claim installation or IAM approval.
- [x] Run focused suites/static validation and independent security review; commit locally only.

**Review focus:** cross-provider imports; unselected credentials leaked in retained image layers; incomplete credential pairs; state changes during scans; reboot restore silently demanding Earth Engine. No provider functional acceptance occurs here.

## Verification ledger

- Initial selected-provider tests:21 expected failures and1 pre-existing sanitization pass before implementation.
- Scoped storage, CLI, full-mode compatibility and operator-flow tests passed after refactor. Added global unselected leak/change/insertion coverage;37 independent-provider tests pass.
- Final focused credential/keyless ADC/satellite/worker regressions:287 passed, one pre-existing Starlette/httpx deprecation warning. No full repository suite rerun.
- Independent security review:PASS,105 tests independently rerun; no critical/important findings. Static Python/embedded Python/JSON/literal-secret/diff checks pass.
- No actual credentials read, installation executed, runtime/cloud/network modified or provider activated. Google console restrictions remain operator-attested; Earth Engine PENDING_IAM.
