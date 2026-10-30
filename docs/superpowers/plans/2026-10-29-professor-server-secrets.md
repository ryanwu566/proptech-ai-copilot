# Professor Server Stage 2 credential preparation

**Goal:** Prepare server-owned credential storage, least-privilege mounts and an
operator-only installation procedure without reading real credentials or changing
the running server. User scope and safety requirements authorize preparation and
synthetic verification; privileged installation and activation remain operator work.

**Design:** Extend the existing individual Compose secret-file mounts. Environment
interpolation and a whole-directory secret mount were rejected because they expose
values through rendered configuration or grant unrelated credentials. Keep the
five Stage 1 API credentials; preserve their values rather than rotating them.
Store future provider credentials without mounting/enabling their consumers.

Persistent files: `/etc/proptech-selfhost/secrets`, root:root 0700 directory,
root:root 0600 files. Volatile staging: `/run/proptech-selfhost/secrets`, root:root
0700 parent, root:10001 0440 API files, root:70 0440 PostgreSQL initialization
files. Individual bind mounts preserve host file permissions; Compose permission
metadata is not relied on. Containers never mount the persistent directory.

**Implementation:** Standard-library Python secret IO and policy; a tracked API
entrypoint preserving valuation TLS/PLVR settings; operator CLI; an additive,
unapplied Compose override; sanitized JSON inventory and runbook. No dependency
installation, database migration, frontend migration or cloud change is needed.

## Constraints and review focus

- Never open actual dotenv/credential files or read real environment values in
  this agent. Audit source identifiers, protected-path metadata and prior sanitized
  Stage 1 evidence only. Test with explicitly synthetic values.
- No privileged execution, secret arguments/output, push, /dev/sda access or X9
  writes. Preserve `frontend_next/next-env.d.ts`.
- Preserve core DB URLs, HMAC and session keys by default. Optional credentials
  do not enable providers. market_ops stays disabled; DB/8080 boundaries unchanged.
- Refuse symlinks, hardlinks, permissive/incorrect ownership, missing/oversized
  values, inherited credentials/libpq authority, unknown mounts and unready features.
- Error/log handling must suppress secret values, including exception chains and
  URL-encoded passwords, without breaking Uvicorn access-log argument structure.
- Installer writes must be exclusive/atomic, prevent traversal and preserve old
  files unless explicit replacement is requested. Reboot staging and inode-bound
  Docker mounts must be documented; no automatic recreation occurs.

## Tasks

- [x] Audit source names and classify every credential/public setting/ops alias.
- [x] Add synthetic failing tests for secure file IO, local startup, logging,
  installer atomicity, sanitized CLI failures and Compose isolation.
- [x] Implement shared policy/IO and the new entrypoint; keep legacy ops unchanged.
- [x] Implement operator installation/adoption/staging/validation with hidden TTY
  input, safe file import and generated local signing material; no service apply.
- [x] Add the core-only override, image copies and Git/build-context exclusions.
- [x] Document inventory, manual supply, deferred retirement, reboot/activation,
  rollback and Stage 2 acceptance. Do not claim installed/live acceptance.
- [x] Run focused tests, AST/shell/config checks and independent security review.
  User explicitly restricts verification to focused tests, not the full suite.

The independent review is limited to source/new files, never actual credentials.
No commit or push is required by this preparation task.
