# Provider credential migration and operator workflow

> **For agentic workers:** Use superpowers:executing-plans inline and independent security review. User has already authorized autonomous preparation; do not execute privileged installation.

**Goal:** Map all accepted names to the requested migration classes and prepare one stored-only operator workflow for the reviewed missing-required set, currently empty.

**Architecture:** Reuse the names-only matrix, accepted Stage2/4 receipt and Stage2 hidden-input/protected-import/atomic-write primitives. A fixed reviewed names-only plan gates the operator wrapper. Unknown remote metadata and optional providers never become missing. No runtime/hardening changes.

**Tech stack:** Python standard library, existing Stage2 installer, focused pytest, JSON/CSV/Markdown.

**Spec:** Latest Stage5 credential-migration-only instruction.

## Constraints and review focus

- No credential values, private envfiles, privileged execution, activation, cloud/network/frontend/runtime/database changes or push.
- No missing-required credential is confirmed for the current local profile.
- Browser-public names remain frontend-only; protected server values never enter the browser/image/Compose/log/Git.
- Core recovery must use protected existing material, never generate or change DB/password/signing identity.
- Reject arbitrary names, unsafe source paths, optional/unapproved entries, overwritten/symlinked targets and reflected parser errors.
- Unsupported Stage4 user-secret recovery requires separate review, not Stage2 provisioning or role substitution.

## Tasks

- [x] Write failing tests for migration classification and empty/unsafe/nonempty installer behavior.
- [x] Implement pure classification and one wrapper reusing Stage2 primitives; no service operations.
- [x] Publish names-only migration matrix, fixed empty install plan and operator procedure.
- [x] Run focused tests/AST/static scans and independent review; update acceptance and one local commit.

Final verification:47focused tests PASS, including synthetic private file writes/recovery only; AST/classification-rebuild/static literal checks PASS; independent review PASS after receipt-proof gate regression. The current install set is empty, no root/host install was executed and no operator action is needed. All cloud retirement gates remain pending. Local commit only.
