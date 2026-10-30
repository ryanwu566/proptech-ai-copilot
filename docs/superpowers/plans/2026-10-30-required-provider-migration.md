# Required provider credential storage migration

> **For agentic workers:** Execute inline, with focused tests and independent security review. Do not execute the operator migration against the host.

**Goal:** Require every listed backend provider credential in Professor protected storage while keeping activation disabled.

**Architecture:** Extend the one operator entry point with --migrate-all. Reuse Stage2 secure reads/imports/writes and streaming image scanner. Store nine secrets in the existing /etc secret store and four public settings in companion root-private configuration; stage individual provider groups under /run. Preserve the six current runtime credentials, database admin material and existing consumers. Use immutable local image, fixed entrypoint, no-network ephemeral probes only.

**Spec:** Latest user credential-policy change; migration is required even while provider disabled.

## Constraints / review focus

- No agent credential reads, sudo, actual installation, cloud/runtime/network/frontend changes or push.
- Metadata access denial is UNKNOWN filesystem state, never confirmed missing or permission to replace keys.
- Existing validated STORE/staged values win; conflicting or unsafe files fail closed, never overwrite.
- Browser public keys stay frontend-only. No server-only key enters ENV, Git, image layers or logs.
- All collected inputs validate before writes. Core material is preserved, never generated.
- Stream full image/history/config, Git context and project logs with actual known values only inside operator process. Include ADC private-key scalar; never export values or their hashes.
- Provider-specific staged mounts; no additions to live API mount/env/flags. Fixed immutable-image probes, nonroot/read-only/no-network/no-log/no-capabilities/resource/time limits.
- Store/stage/readability/leak-scan acceptance is distinct from provider-functional acceptance, which is NOT_RUN.

## Tasks

- [x] Write failing tests for required targets, secure adoption/collection/staging, private metadata and isolated verification command.
- [x] Implement required-provider storage policy and --migrate-all without service activation.
- [x] Add operator procedure, provider-by-provider future activation tests, sanitized preparation state and truthful unknown filesystem scope.
- [x] Run focused tests/static validation, independent review, update evidence and one local commit.

Final verification:170focused tests plus28subtests PASS (198JUnit cases). Synthetic filesystem/operator-flow boundaries only; no actual sudo, credential read, migration, host Docker probe or provider request executed. Static policy/AST/scans and independent review PASS after containment/concurrent-write fixes. Nine secret files +four companion public settings required; six isolated groups. Current filesystem UNKNOWN preserved separately from missing migration acceptance. Operator --migrate-all is the current required policy; older optional/empty-plan artifacts are historical. Local commit only; no push.
