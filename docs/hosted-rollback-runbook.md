# Hosted Rollback Runbook

## Detection

Use bounded liveness/readiness/release/compatibility checks and the hosted
smoke runner. Preserve only the release ID, categorical results, schema version,
and provider checkpoint. Do not capture private payloads or headers.

## Response

- Frontend-only failure: pause the frontend deployment and restore the prior
  frontend release; verify its API origin and backend compatibility.
- Backend-only failure: restore the prior backend release; keep the frontend on
  a compatible contract or roll it back together.
- Migration failure before traffic: keep the service unavailable, inspect the
  safe migration category, and restore the recorded checkpoint if needed.
- Migration incompatibility after traffic: enter maintenance mode, stop writes,
  preserve evidence, and restore PostgreSQL from the provider checkpoint. Do
  not invent a down-migration.
- Database/source outage: keep readiness or source status unavailable; do not
  show stale results as current and do not enable silent mock fallback.
- Compromised secret: rotate in the provider secret store, restart affected
  services, invalidate sessions where applicable, and rerun read-only smoke.

The managed PostgreSQL backup/restore boundary is provider-owned; never treat
a local SQLite copy as a production restore. After any rollback, verify release identity, schema compatibility, privacy and
terms pages, offline competition disclosure, and the no-localhost request
boundary. Escalate to the provider when backup or restore status is unknown.
