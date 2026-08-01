# Environment Matrix

Values are configured in the hosting platform or a local process environment.
This document intentionally contains names only and no example secrets.

| Name | Development | Test | Preview | Production |
| --- | --- | --- | --- | --- |
| `APP_ENV` | optional | `test` | `preview` | `production` |
| `APP_RUNTIME` | optional | optional | required | required |
| `DATABASE_URL` | optional | optional | required | required |
| `PILOT_EVIDENCE_DATABASE_URL` | compatibility alias | optional | alias only | alias only |
| `PILOT_SESSION_SIGNING_KEY` | optional | test fixture only | required | required |
| `PILOT_ADMIN_TOKEN` | optional | fixture only | protected operator setting | protected operator setting |
| `PILOT_REVIEW_TOKEN` | optional | fixture only | protected operator setting | protected operator setting |
| `CORS_ALLOWED_ORIGINS` | local defaults allowed | local defaults allowed | required | required |
| `PUBLIC_APP_BASE_URL` | optional | optional | required | required |
| `RELEASE_VERSION` | optional | optional | recommended | recommended |

Production-like readiness rejects missing or malformed database, session,
CORS, or public base URL configuration. Admin and reviewer capabilities remain
disabled when their tokens are absent; absence does not enable anonymous access.
Client bundles must use only public frontend configuration. Server-only names,
database URLs, tokens, and keys must never be imported by client modules.
