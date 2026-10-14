# Wave 1A implementation plan

Goal: consumer login, signup and account pages using the existing Supabase/VNext identity stack.

Authorized specification: the user's Wave 1A Consumer Auth & Account Foundation v1 request.
Base: `0185c81416a56b14c1dada38d959d90aeac2ecf4` (fetched origin/main; clean worktree; fast-forward only).
Execution: inline implementation; one independent review after implementation. Exactly one final local feature commit; no push, merge or deployment.

- [x] Add failing tests for account authority, direct API suspension, default consumer privileges, missing/error denial and migration grants.
- [x] Implement a minimal private account table with forced RLS, own-record reads/default-only creation, no request-role updates; register migration 020 without changing historical checksums.
- [x] Add account status API and a shared active-account dependency to all VNext protected operations. Add restrictive membership RLS for suspension.
- [x] Add failing deterministic client tests for signup states, validation, reset request, provider error sanitization and reuse of existing login/logout/restore handling.
- [x] Implement localized consumer forms and account display using the existing browser client, safe bearer API calls, session generation checks and bounded loading/error states.
- [x] Add a small localized account entry to the commercial header; preserve anonymous workflows and browser Saved Cases.
- [x] Exercise all four locales and widths 390/430/1024/1440, login/signup/logout/restore/expiry/suspension, keyboard focus and no secret leakage through mocked providers.
- [x] Run Python regressions, frontend deterministic suites, typecheck, lint, production build, unchanged route/global performance gates and release/security contracts. Three existing worker failures reproduce at BASE_SHA; acceptance records them.
- [x] Review independently, address findings, record evidence and external/hosted gaps in acceptance documentation; check hygiene. Commit is the final step.

Review focus: duplicate-email privacy, stale account responses after logout, missing database/configuration, suspension via direct API, and unintended changes to local Saved Cases. No billing, quotas, OAuth, admin UI, collaboration or case migration.
