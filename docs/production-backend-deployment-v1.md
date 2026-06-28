# Production Backend Deployment Configuration v1

This project deploys as two surfaces:

- FastAPI backend on Render, from the repository root.
- Next.js frontend on Vercel, from `frontend_next`.

Do not put provider keys, refresh tokens, database URLs, or other secrets in frontend variables or committed files.

## Render FastAPI Web Service

Use the repository root and the checked-in `render.yaml` blueprint.

- Service type: Web Service
- Runtime: Python
- Build command: `pip install -r backend/requirements.txt`
- Start command: `uvicorn backend.api_main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`
- Branch: `main`

The backend entry point is `backend.api_main:app`. Render should not use the root Dockerfile for this service.

## Render Environment Variables

Backend boot and CORS:

- `CORS_ALLOWED_ORIGINS`

Optional backend feature configuration:

- `VALUATION_DATABASE_URL`
- `GOOGLE_MAPS_API_KEY`
- `TGOS_APP_ID`
- `TGOS_API_KEY`
- `TDX_CLIENT_ID`
- `TDX_CLIENT_SECRET`
- `COMMUTE_REFRESH_TOKEN`

`COMMUTE_REFRESH_TOKEN` belongs only on the Render backend. Do not set it on Vercel and do not expose it with a `NEXT_PUBLIC_` prefix.

If optional provider variables are absent, affected features should return their existing unavailable or fallback states. `/health` must still boot.

## CORS

Set `CORS_ALLOWED_ORIGINS` to the Vercel frontend origin allowlist. Use comma-separated origins when needed.

Rules:

- Include only origins, not paths.
- Do not use `*` with credentials.
- Localhost origins are only the development fallback when no allowlist is configured.
- Production should explicitly configure the Vercel origin in Render.

## Vercel Frontend

Use the existing Vercel project for `proptech-ai-copilot`.

- Root Directory: `frontend_next`
- Variable name: `NEXT_PUBLIC_API_BASE_URL`
- Value: the deployed Render backend base URL
- Apply to Production and Preview as appropriate.

Do not set backend secrets, provider keys, or refresh tokens in Vercel. The frontend only needs the public backend base URL.

If `NEXT_PUBLIC_API_BASE_URL` is missing in production, the frontend fails closed instead of falling back to localhost. If it is explicitly set to localhost during a production build, API requests are also treated as unconfigured.

## Post-Deployment Smoke Checks

After Render and Vercel are configured:

1. Open `GET /health` on the backend and confirm it returns an OK status.
2. Confirm the frontend can load without exposing backend errors or secrets.
3. Run a simple property flow that calls the backend through the configured API base URL.
4. Confirm address resolve either resolves or returns a safe unavailable message.
5. Confirm Terrain Risk unavailable states remain conservative and are not shown as low risk.
6. Confirm commute refresh is triggered only by an authorized backend call, then nearest-station features use the backend result.
7. Confirm saved cases, comparison, print / save as PDF, and HTML export still work.

Never paste provider raw payloads, tokens, coordinates, or secret values into deployment logs, tickets, or documentation.
