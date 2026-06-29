# Commute Snapshot Operations v1

This document describes the manual operations workflow for refreshing the in-memory MRT commute snapshot on the production backend.

The workflow is intended for demo preparation or operational refreshes. It is not a permanent snapshot storage mechanism and does not prevent memory loss after backend sleep, restart, or redeploy.

## GitHub Secrets Setup

In the GitHub repository, open:

```text
Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

Create these repository secrets:

```text
RENDER_API_BASE_URL
COMMUTE_REFRESH_TOKEN
```

Do not put real URLs, tokens, host names, credentials, or secret examples in this document. Do not put `COMMUTE_REFRESH_TOKEN` in Vercel, browser code, URLs, frontend environment variables, or client-side documentation examples.

## Manual Refresh Flow

In the GitHub repository, open:

```text
Actions
→ Refresh Commute Snapshot
→ Run workflow
→ Run workflow
```

The workflow calls the production backend once:

```text
POST /commute/refresh
```

The frontend must not call `/commute/refresh`.

## Success Criteria

Check only these safe log lines:

```text
REFRESH_RESULT=success
REFRESH_HTTP_STATUS=200
```

Do not log or paste response bodies, station names, coordinates, addresses, tokens, provider payloads, provider errors, request headers, or backend URLs.

## Important Limits

- The snapshot currently exists only in Render backend memory.
- Render free services may sleep, restart, or redeploy, and the in-memory snapshot may disappear.
- The manual GitHub Actions refresh is suitable before a demo or when an operator needs to refresh commute data.
- This is not a durable snapshot persistence mechanism.
- The frontend cannot call `/commute/refresh`.
- `COMMUTE_REFRESH_TOKEN` must not be placed in Vercel, browser code, URLs, frontend code, or documentation examples.
- TDX credentials stay in the Render backend runtime. The workflow only sends the protected refresh token to the backend.
