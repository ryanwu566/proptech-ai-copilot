# Hosted Owner Launch Checklist

Run each step in the named environment. A `pending` or `configuration_required`
result is not a successful release. Never place secret values in commands,
files, screenshots, or logs; provider secret injection is required.

1. Create isolated preview and production managed PostgreSQL instances. Expected: both exist; failure: provider setup required; safe to proceed: no.
2. Record provider backup/snapshot capability and retention. Expected: checkpoint recorded privately; failure: no recovery evidence; safe to proceed: no.
3. Configure backend preview variables from the environment manifest. Expected: preview values are distinct; failure: separation missing; safe to proceed: no.
4. Configure backend production variables from the environment manifest. Expected: required categories are present; failure: startup must remain fail-closed; safe to proceed: no.
5. Configure frontend preview `NEXT_PUBLIC_API_BASE_URL`. Expected: matching or approved staging backend; failure: preview origin invalid; safe to proceed: no.
6. Configure frontend production `NEXT_PUBLIC_API_BASE_URL`. Expected: HTTPS absolute origin; failure: localhost or malformed origin; safe to proceed: no.
7. Configure secrets only in provider/GitHub secret stores. Expected: no secret appears in source or logs; failure: rotate and stop; safe to proceed: no.
8. Verify exact production and preview CORS origins. Expected: preflight allows only intended origin; failure: reject and correct; safe to proceed: no.
9. Run preview dry-run and migration command. Expected: bounded migration summary and ledger; failure: rollback transaction and investigate; safe to proceed: no.
10. Run preview `scripts/production_smoke.py`. Expected: liveness/readiness/release/source/public pages pass; failure: preview is not ready; safe to proceed: no.
11. Run hosted preview Playwright with `HOSTED_FRONTEND_URL`. Expected: locale/device smoke passes; failure: preserve evidence and fix; safe to proceed: no.
12. Generate non-secret preview evidence with `scripts/generate_release_evidence.py`. Expected: preview status is explicit; failure: mark pending; safe to proceed: no.
13. Review preview release identity, privacy, terms, source state, and offline disclosure. Expected: no misleading live/official claim; failure: stop; safe to proceed: no.
14. Record the production backup checkpoint immediately before migration. Expected: private provider checkpoint exists; failure: do not migrate; safe to proceed: no.
15. Run the production migration command through provider secret injection. Expected: ledger, tables, indexes, and foreign keys verify; failure: use rollback runbook; safe to proceed: no.
16. Deploy the backend with the documented ASGI start command. Expected: liveness is up and readiness reflects PostgreSQL; failure: keep traffic off; safe to proceed: no.
17. Deploy the frontend with the production public API origin. Expected: no localhost requests; failure: roll back frontend; safe to proceed: no.
18. Run production read-only smoke. Expected: all required checks pass; failure: classify outage/configuration; safe to proceed: no.
19. Run hosted production Playwright with non-destructive flows. Expected: all selected locales/devices pass; failure: do not call release complete; safe to proceed: no.
20. Confirm readiness, release identity, compatibility, and source status. Expected: categories match the intended release; failure: investigate; safe to proceed: no.
21. Confirm Privacy and Terms pages in the hosted frontend. Expected: current limitations are visible; failure: stop public launch; safe to proceed: no.
22. Confirm the explicitly labelled offline competition example. Expected: it remains deterministic and not official live data; failure: disable the claim, not the boundary; safe to proceed: no.
23. Confirm rollback checkpoint and escalation contacts, then record sign-off. Expected: evidence pack marks each environment accurately; failure: status remains `COMPLETE_REQUIRES_OWNER_ACTION`; safe to proceed: no.

The application is `COMPLETE` only after the hosted facts above are verified.
Until then use `COMPLETE_REQUIRES_OWNER_ACTION`.
