# Hosted Migration Runbook

## Before migration

1. Confirm the target is the isolated preview or production managed
   PostgreSQL instance, not a local SQLite file.
2. Record provider backup/snapshot identifier and retention limitation.
3. Confirm the release identity and expected `SCHEMA_VERSION`.
4. Run the verification-only command:
   `python scripts/apply_production_migrations.py --dry-run`.

## Apply

Use the provider's secret injection mechanism to supply the database URL to the
explicit `--database-url` argument; never paste it into a file or log:

`python scripts/apply_production_migrations.py --database-url <managed-postgres-url> --release-version <release-id>`

The command applies the reviewed files in one transaction, records migration
identity/checksum in `schema_migration_ledger`, and verifies required tables,
indexes, and foreign keys before committing. A failed transaction is rolled
back and reports only a category.

## Verify and recover

Run `python scripts/production_smoke.py` against the intended frontend and
backend origins, then check `/readiness`, `/release-version`, and
`/compatibility`. If verification fails, stop traffic and use the recorded
provider restore checkpoint. Migrations are not assumed reversible; restore
guidance is the recovery path for destructive or incompatible schema changes.
