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

Set public `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, and
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` in Vercel for each deployed environment.
The latter two must identify the same production Supabase Auth project whose
user JWTs the FastAPI VNext verifier accepts. Supply these public values before
the Next.js production build; changes require a frontend redeploy. The Auth URL
must be that project's HTTPS `.supabase.co` origin, and the browser key must
begin with `sb_publishable_`. No actual project value belongs in git.
`NEXT_PUBLIC_APP_ENV` remains optional for the existing app environment setup.
Production requires an HTTPS absolute API origin and
rejects localhost, credentials, query strings, fragments, and unsafe schemes.
Local development alone may use the documented localhost fallback. Preview
may use a matching backend or an explicitly approved shared staging backend.

`NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY` is optional and intentionally public. Set
it only to a dedicated Maps Embed API key restricted both to the Maps Embed API
and to the approved website/referrer origins. Never copy or reuse the backend
`GOOGLE_MAPS_API_KEY`; missing browser configuration leaves the existing
Location Insight and Leaflet experiences available with a bounded unavailable
Google-preview state.

No backend token, privileged provider key, database URL, or session secret may use a
`NEXT_PUBLIC_` name or enter the browser bundle.

The VNext identity review accepts email/password sign-in for an existing,
valid Supabase Auth user. Public self-registration is deferred; this slice
enables authenticated access for valid Supabase users. The backend still checks
the signed JWT, workspace membership, property access, and feature flag.

## CORS and cookies

Use exact origins only. Localhost is a development fallback, not a production
allowlist. Session cookies are HttpOnly, Secure in production-like modes,
SameSite Strict, and scoped to their protected path. Cross-origin state changes
retain same-origin and CSRF checks.
Those cookies belong to the existing pilot flow. VNext Supabase Auth stores its
browser session through the official Supabase client and sends its short-lived
access token only to the configured FastAPI `/v1` origin for identity requests.

## Maintenance and outage behavior

Set `MAINTENANCE_MODE` in the backend provider configuration rather than
editing code. Public read-only pages may remain available while mutating
requests return a bounded maintenance state. Readiness still reflects critical
dependencies. Backend, database, source, and compatibility failures must show
recoverable unavailable states without mock substitution or infinite retries.
