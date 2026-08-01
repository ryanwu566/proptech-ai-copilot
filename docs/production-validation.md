# Production Validation

## Local and CI checks

Run the following without loading environment files or contacting production:

```text
python scripts/validate_postgres_migration.py
python scripts/validate_pilot_evidence_migration.py
python scripts/production_smoke.py
python -m pytest -q
npm.cmd --prefix frontend_next run build
python scripts/security_performance_release_gate.py --json
```

`validate_postgres_migration.py` performs a static check without a URL. CI may
pass an explicitly provisioned disposable Postgres service URL; the migration
is applied inside a transaction and rolled back after checking tables, indexes,
and foreign keys. No hosted production migration is implied.

## Browser matrix

The existing Playwright harness covers Chromium and Chrome, the four supported
locales (`zh-TW`, `en`, `ja`, `ko`), and mobile widths 360, 390, and 430. It
checks page errors, console diagnostics, key navigation, and horizontal
overflow. Run it after a local production frontend build; provider responses
remain mocked by the test fixtures.

## Hosted handoff

After deployment, an operator must verify the configured backend host, database
readiness, release version, protected route behavior, and the browser smoke
matrix. This repository does not claim that Render, Vercel, or a production
database was contacted by local validation.
