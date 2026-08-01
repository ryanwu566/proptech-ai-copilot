# Security Operations

## Secrets and sessions

Production requires a strong `PILOT_SESSION_SIGNING_KEY`. Admin and reviewer
tokens are optional capabilities but are required to use their protected
routes. Tokens are compared in constant time, scoped by role, short-lived when
used as sessions, and revocable.

Rotate a credential by creating the replacement in the hosting platform,
deploying it through the normal release process, invalidating affected scoped
sessions, and removing the old value only after verification. Do not put any
of these values in Vercel public variables, browser code, URLs, screenshots,
or documentation examples.

## Access boundaries

Participant, reviewer, and administrator routes remain separate and deny by
default. Public evidence exposes only approved aggregate fields. Missing
configuration disables protected operations; it never opens anonymous access.

## Incident diagnostics

Logs and responses may contain route, method, status class, bounded error code,
release version, and correlation ID. They must not contain request payloads,
database URLs, SQL, tokens, provider raw errors, or participant evidence.
