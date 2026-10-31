# Vercel cutover checklist — preparation only

Vercel remains frontend-only. No production setting/build/deployment changed.
Stage4B binding is operator-accepted COMPLETE; Stage5 public authenticated E2E is
new evidence to collect, not a request to redo frontend implementation.

Future browser-safe setting NAME: `NEXT_PUBLIC_API_BASE_URL`.
Its eventual value is the **exact selected trusted Professor HTTPS origin**,
without path, credentials or trailing slash. No value is provided yet because
there is no approved hostname/IP identity. Do not use127.0.0.1, Cloud Run, Render
or an external tunnel as the replacement public backend.

1. Select owned TLS identity and finish direct external HTTPS acceptance.
2. Establish exact intended Vercel Preview deployment URL(s), excluding wildcard
   *.vercel.app. Record current preview config/deployment for rollback.
3. Review Professor API_ALLOWED_HOSTS as current exact hosts plus API identity;
   CORS_ALLOWED_ORIGINS includes production
   `https://proptech-ai-copilot.vercel.app` and only those approved preview URLs.
   Keep preview credentials/session mechanism identical to Stage4 contract.
4. Operator-approved Preview-only change: set NEXT_PUBLIC_API_BASE_URL to the
   selected origin and rebuild that deployment. Browser-facing CSP/connect-src
   must admit the same API origin; frontend owner handles any frontend change.
   Keep Supabase public project/publishable configuration unchanged.
5. Run Preview browser E2E for auth/profile/cases, ownership denial, ML/GIS/Market/
   Valuation/Trend/Finder and missing-provider limitations; inspect sanitized
   network outcomes. No server-only key belongs in Vercel/browser build variables.
6. After explicit production approval, record old production API origin and
   deployment, apply that same public Professor origin to Production, rebuild,
   test real Production E2E, and retain a rollback deployment/config receipt.
7. Verify requests actually reach Professor Server and no unique old-cloud
   runtime/provider dependency remains. Keep legacy services until retirement gate.

All public/browser config names are listed in the credential matrix. An origin
is public metadata, not a credential; server provider keys, DB URLs, ADC and
service-role keys remain in protected Professor storage only. No production
mutation or automatic cloud shutdown is part of this checklist.
