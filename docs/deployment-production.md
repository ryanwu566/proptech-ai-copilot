# Production Deployment

The Render service runs `backend.api_main:app`. Production and preview require
durable Postgres through `DATABASE_URL`; the API does not fall back to SQLite in
those modes. `PILOT_EVIDENCE_DATABASE_URL` remains a temporary compatibility
alias for an existing pilot deployment, but new deployments should use
`DATABASE_URL`.

## Before deploy

1. Configure the environment names in `docs/environment-matrix.md` in the
   hosting platform without placing them in the frontend.
   Include `API_ALLOWED_HOSTS` with exact approved backend/probe hosts and keep
   `ANTI_ABUSE_ENFORCEMENT_MODE=local_only`. The guardrails release fails
   startup without this allowlist; do not roll it out before owner configuration.
2. Apply migrations in order using the reviewed migration process.
3. Confirm `/liveness` is responsive and `/readiness` reports ready.
4. Run the release checklist and the production smoke command against the
   intended environment without printing response bodies.

The repository does not claim that a hosted migration or deployment has been
executed locally. Render and Vercel actions remain operator-controlled.
Production acceptance also requires the separately verified ingress/WAF,
cross-instance, quota/cost, monitoring and recovery evidence in the
[guardrails runbook](operations/production-guardrails-recovery-v1-runbook.md).
Repository gate PASS does not permit production GO.

## Failure behavior

Missing or malformed production configuration causes startup failure. A live
process reports liveness separately from persistence readiness; `/health` does
not imply that durable storage is ready. Diagnostic responses contain only
categories, release metadata, and a correlation reference.
