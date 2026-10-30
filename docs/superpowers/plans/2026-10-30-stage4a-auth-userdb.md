# Stage 4A implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, then one fresh security review.

**Goal:** Preserve existing Supabase users while adding isolated Professor user persistence.
**Architecture:** Hybrid identity; dedicated forced-RLS application schema and direct runtime role.
**Tech Stack:** FastAPI, existing PyJWT, psycopg, PostgreSQL; no new dependencies.
**Spec:** docs/superpowers/specs/2026-10-30-stage4a-auth-userdb-design.md

## Global constraints

No frontend edits, main/history worktree writes, sudo, live migrations, cloud changes,
provider activation or push. Preserve Stage 1–3 and existing users. No secret reads.

## Review focus

- Cross-issuer identity reuse must deny, including a matching UUID.
- A refreshed token with revoked session_id must deny.
- CAS/idempotency across concurrent processes must commit once or conflict.
- Tombstones must not resurrect through an import retry.
- Suspended users and unsafe request roles must fail at the SQL boundary.

## Tasks

- [x] Audit auth and existing users, isolate worktree, run baseline focused tests (93 passed).
- [x] Write failing PostgreSQL/API tests for ownership, CAS, logout and lifecycle.
- [x] Add database/userdb/001_professor_users.sql, repository/context and optional wiring.
- [x] Add session/profile/preferences/report/delete routes and explicit API contract.
- [x] Test against isolated Unix-socket PostgreSQL; run focused existing regressions.
- [x] Prepare operator-only provisioning/profile/runbook with backup and fail-closed gates.
- [x] Independent security review, focused repair, static checks and truthful acceptance.
- [x] Commit intentional backend/docs/tests files locally only.

Ruling: no design-confirmation pause: user explicitly delegates architecture choice
based on audit and requests implementation. No privileged activation is authorized
for agent execution. Live authority/identity reconciliation is an operator gate.

Final evidence: reports/professor-stage4a-auth-userdb/acceptance.json.
Operator provisioning/authority/activation and live frontend E2E remain pending;
PARTIAL is deliberate. No host apply is part of this completed implementation plan.
