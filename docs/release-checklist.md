# Release Checklist

## Build and configuration

- [ ] Review the intended commit and changed files.
- [ ] Configure the environment names in `docs/environment-matrix.md`.
- [ ] Confirm no secret is present in source, client bundle, logs, or URL.
- [ ] Run targeted migration, security, backup/restore, and smoke tests.
- [ ] Run the complete Python test suite and frontend production build.
- [ ] Run `scripts/security_performance_release_gate.py --json`.
- [ ] Run `git diff --check`.

## Deploy and migrate

- [ ] Apply Postgres migrations in order with a reviewed operator account.
- [ ] Keep the previous release available for rollback.
- [ ] Verify `/liveness`, `/health`, `/readiness`, `/release-version`, and
      `/source-status` without recording response bodies.
- [ ] Run the browser matrix for supported locales and mobile widths.
- [ ] Confirm the frontend points to the intended backend host.

## Rollback

- [ ] Stop a migration if schema verification fails.
- [ ] Roll back application code first when compatible.
- [ ] Treat destructive schema rollback as a reviewed data operation.
- [ ] Record only categorical status and a correlation reference in incident
      notes.
