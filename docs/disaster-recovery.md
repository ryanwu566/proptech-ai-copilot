# Disaster Recovery Runbook

## Outage classes

- **DB unavailable:** keep liveness separate from readiness, stop write
  operations, inspect provider status, and do not enable SQLite fallback.
- **Bad deploy:** return to the last known-good application release and rerun
  readiness and smoke checks.
- **Migration issue:** stop the rollout, preserve the migration transaction
  evidence, and use the reviewed rollback guidance. Do not drop tables as an
  ad-hoc repair.
- **Token or secret exposure:** revoke and rotate the affected credential,
  invalidate scoped sessions where applicable, and inspect access logs without
  copying the secret into an incident record.
- **Admin access disabled:** keep deny-by-default behavior, repair the
  configured token through the hosting platform, and rerun protected route
  checks.
- **Evidence export recovery:** restore from a provider snapshot, verify
  participant isolation, publication status, and deletion boundaries before
  re-enabling exports.

## Recovery sequence

1. Declare the incident and record a correlation reference.
2. Classify liveness, readiness, database, and release-version status.
3. Protect the active database and stop destructive actions.
4. Restore or roll back using the provider-approved procedure.
5. Apply only reviewed migrations.
6. Run migration validation, security tests, smoke tests, and browser checks.
7. Reopen traffic only after `/readiness` is ready.

Hosted recovery is not claimed by local tests. Local SQLite restore is only a
schema and operator-drill check.
