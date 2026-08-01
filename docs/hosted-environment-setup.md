# Hosted Environment Setup

The backend and frontend are separate deployments. Configure names and scopes
from `config/hosted-environment-manifest.json`; this file contains metadata
only and no values.

## Backend

Required in preview and production: `APP_ENV`, `DATABASE_URL`,
`CORS_ALLOWED_ORIGINS`, `PUBLIC_APP_BASE_URL`, `BACKEND_PUBLIC_URL`, and
`PILOT_SESSION_SIGNING_KEY`. Optional provider variables remain server-only.
`API_CONTRACT_VERSION` and `SCHEMA_VERSION` identify compatibility.

`DATABASE_URL` must use a provider PostgreSQL URL. `postgres` and `postgresql`
schemes are accepted; SQLite is rejected in production-like modes. Use the
provider's certificate-verifying SSL policy, normally `verify-full` where the
provider documents it, through `POSTGRES_SSLMODE`. Do not disable certificate
verification globally. Connections use a bounded timeout.

## Frontend

Set only public `NEXT_PUBLIC_API_BASE_URL` and, when needed, public
`NEXT_PUBLIC_APP_ENV` values. Production requires an HTTPS absolute origin and
rejects localhost, credentials, query strings, fragments, and unsafe schemes.
Local development alone may use the documented localhost fallback. Preview
may use a matching backend or an explicitly approved shared staging backend.

No backend token, provider key, database URL, or session secret may use a
`NEXT_PUBLIC_` name or enter the browser bundle.

## CORS and cookies

Use exact origins only. Localhost is a development fallback, not a production
allowlist. Session cookies are HttpOnly, Secure in production-like modes,
SameSite Strict, and scoped to their protected path. Cross-origin state changes
retain same-origin and CSRF checks.

## Maintenance and outage behavior

Set `MAINTENANCE_MODE` in the backend provider configuration rather than
editing code. Public read-only pages may remain available while mutating
requests return a bounded maintenance state. Readiness still reflects critical
dependencies. Backend, database, source, and compatibility failures must show
recoverable unavailable states without mock substitution or infinite retries.
