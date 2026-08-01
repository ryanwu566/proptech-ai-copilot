# Hosted Production Launch Candidate

This is the authoritative launch handoff for the current architecture. It is
an implementation and verification contract, not proof that a provider is
already configured or live.

## Current architecture

- Frontend: Vercel, Next.js root `frontend_next`.
- Backend: Render-compatible FastAPI service using `backend.api_main:app`.
- Database expectation: managed PostgreSQL in preview and production. SQLite is
  local development only and is never a production fallback.
- Current hosted URLs: owner-configured; no URL is hardcoded in this repository.
- Start command: `uvicorn backend.api_main:app --host 0.0.0.0 --port $PORT`.
- Health paths: `/liveness`, `/health`, `/readiness`, `/release-version`,
  `/compatibility`, and `/source-status`.

## Verification state

Local and disposable checks may be run from the repository. Hosted database,
TLS, domains, migration completion, backup, monitoring, and source reachability
remain `owner_action` until an operator runs the documented commands against
the intended environment. No hosted success is inferred from a successful
frontend deployment.

## Required owner actions

1. Create isolated preview and production managed PostgreSQL databases.
2. Configure the variables listed in `config/hosted-environment-manifest.json`
   in the provider secret store, with distinct preview and production values.
3. Set the exact frontend origin in `CORS_ALLOWED_ORIGINS`; never use a
   credentialed wildcard or an arbitrary Vercel deployment suffix.
4. Record the provider backup checkpoint before the first production migration.
5. Run `python scripts/apply_production_migrations.py --database-url <managed-postgres-url> --release-version <release-id>`
   from an approved operator environment. The command emits only categories.
6. Run `python scripts/production_smoke.py --frontend-url <frontend-origin> --backend-url <backend-origin> --expected-environment production`.
7. Run `HOSTED_FRONTEND_URL=<frontend-origin> npm --prefix frontend_next run test:e2e:hosted`.
8. Preserve the generated release evidence and rollback checkpoint.

Follow the complete numbered [owner launch checklist](hosted-owner-launch-checklist.md)
and generate the non-secret pack with `scripts/generate_release_evidence.py`.

The placeholders above are command-shape placeholders only. Do not put their
values in source, logs, tickets, screenshots, or chat.

## Truth boundaries

Source status remains categorical. Missing or unavailable official sources are
not replaced by mock success, zero risk, or current official-data claims. The
offline competition example is deterministic and explicitly labelled; it is
not customer data and is not an official-source result. Tax, terrain, market,
valuation, loan, case, comparison, privacy, and terms boundaries remain intact.

## Operational status

Use `COMPLETE_REQUIRES_OWNER_ACTION` until preview and production are reached,
PostgreSQL schema and backup/restore are verified, and the read-only hosted
smoke and browser matrix pass. Use `COMPLETE` only after those facts are
recorded. Use `BLOCK` for a failed security boundary, migration, restore,
regression suite, or release-preservation check.
