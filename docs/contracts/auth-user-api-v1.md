# Auth and User API v1 — Stage 4A contract

Status: backend active on the private Professor API; frontend integration ready.
Live authenticated user-flow acceptance remains pending frontend integration.
Frontend owner: Claude. Backend owner: this branch. No frontend files changed.

## Accepted public identity authority

Authority audit PASS for the existing Vercel deployment reporting commit
`9cc40d645757af4513d9afdf0c008939cc489a77`:

- Project: `flyhsjcynreuofbcdxod` (`proptech-valuation-db`).
- Browser project URL: `https://flyhsjcynreuofbcdxod.supabase.co`.
- FastAPI issuer: `https://flyhsjcynreuofbcdxod.supabase.co/auth/v1`.
- Audience: `authenticated`; canonical user ID: verified `sub` UUID unchanged.
- Public authority SHA256: `ffd784ac6e456727b17ad7daf4db013351e76b43599c27ec4f4aa830958b588e`.

This is proven from the deployed public auth bundle and provider aggregate
metadata, independently of key values. One existing confirmed, authenticated,
non-anonymous user belongs to that project. No password/identity migration is
needed. See `reports/professor-stage4a-auth-userdb/auth-authority.json` for exact
release/asset proof and scope. Unknown deployment bytes require another public
metadata review, not a secret-key comparison. No active conflicting issuer was
observed; test projects and the inactive valuation-green archive are not identity
authorities for this captured frontend.

The authority review is approved and the local database approval flag is now
true. The operator activated backend source commit
`1d4f4db7a991b4f7bb2baead7c3201dc21b50514` successfully. Supabase users and
credentials were preserved. Professor PostgreSQL is the application-data authority.
The private API remains at `http://127.0.0.1:8080`; public Vercel-to-server
ingress is a later task. Do not rerun provisioning or activation for integration.

## Identity and transport

HYBRID: retain existing Supabase Auth project and UUIDs. Use existing supabase-js
singleton and public publishable key; never service-role/signing secrets. Register
and login remain `auth.signUp({email,password})` and
`auth.signInWithPassword({email,password})`. Invalid login is generic; duplicate
signup is neutral request acceptance, not proof of new account/delivery. Recovery
completion remains provider-operated, not a new FastAPI password endpoint.

Every endpoint below requires `Authorization: Bearer <Supabase access JWT>`;
credentials omitted, HTTPS in eventual ingress, no-store, redirects rejected.
Stage 4A requires RS256/ES256, kid, issuer, audience, UUID sub, role authenticated,
non-anonymous identity, session_id UUID, integer iat and exp. Backend only trusts
verified subject; no user_id/role override in bodies, headers or query fields.
Missing/expired/malformed/revoked token =>401. Never put tokens in URLs/logs.
No new cookies; bearer mutation calls do not rely on ambient cookie authority.
Existing Origin policy still applies. Public CORS/ingress remains a later gate.

### Logout sequence

POST `/v1/session/logout` with bearer, no body: 200 `{ "status":"revoked" }`.
For an active account this durably revokes this session UUID on Professor Server, including future
refreshes with the same ID. Then call existing SDK local signOut and clear private
UI state even if provider logout fails. Do not claim provider/global logout on
network failure. A repeat with the revoked bearer receives401; treat as already
unauthenticated. Supabase-only logout does not instantly invalidate JWTs on this
server; remote deletion/revocation remains bounded by access-token expiration.

## Existing compatible endpoints

GET `/v1/account`: `{user_id,status:"active"|"suspended",platform_role:
"consumer"|"platform_admin",created_at,updated_at}`. Own suspended status remains
readable. No role/status updates from browser. GET `/v1/session` returns
`{status:"authenticated",user_id,session_id,expires_at}` (suspended account403).
Unauthenticated session status401, never fabricated anonymous account.
A suspended account receives403 on consumer operations including logout; clear
its browser SDK state, retain server-owned data, and do not claim local backend
revocation succeeded when the backend refused it.

## Profile and preferences

GET `/v1/profile`: `{user_id,revision,display_name,locale,created_at,updated_at}`.
Defaults revision1, display_name empty, locale zh-TW. PATCH same path:
`{expected_revision:1,display_name:"Name",locale:"zh-TW"}`; fields optional but at
least one required. locale zh-TW/en/ja/ko; name max80, no credentials.

GET `/v1/preferences`: `{user_id,revision,data,created_at,updated_at}`; defaults
revision1,data{}. PUT same path `{expected_revision:1,data:{...}}`, JSON max24KiB.
Use explicit versioned keys in data for existing buyer preference/compare state.
Server stores authored JSON, does not evaluate or assert risk semantics. CAS409
requires reloading and asking user to resolve; do not silently overwrite.

## Saved Cases (preserves established concepts)

All successes remain the existing CaseView/CaseSummary shapes. POST
`/v1/saved-cases` requires Idempotency-Key (16–128 chars A-Z/a-z/0-9/._:-) and:
`{snapshot:<existing SavedCase v1>,user_authored:{},import_key:"local-id",
explicit_consent:true}`. Snapshot requires version1, workflowMode buying_wizard,
id/title/createdAt/updatedAt/inputSummary/data.inputs; maximum256KiB total.
Snapshot evidence is retained as supplied, including unknown/error/source dates;
never refreshed or promoted. Ownership is server-derived, private by default.
201 returns `{id,owner_id,role:"owner",revision,title,notes,created_at,updated_at,
snapshot,user_authored,members:{},monitoring,sharing:"private"}`.

GET `/v1/saved-cases?scope=owned&offset=0&limit=20`: CaseSummary[]
`{id,role,revision,title,updated_at,sharing}`; limit1–100,offset0–10000.
GET `/v1/saved-cases/{id}` reopens full case, no provider calls.
PATCH `/{id}/metadata`: `{expected_revision,title?,notes?}`, Idempotency-Key.
PUT `/{id}/monitoring`: `{expected_revision,cadence:"off"|"daily"|"weekly",
refresh_policy:"manual_only"}`, Idempotency-Key. This records preferences only;
execution/delivery remain not_configured. GET `/{id}/activity` returns bounded
revision/actor_id/kind/occurred_at events, not notes/provider payloads.
DELETE `/{id}?expected_revision=N`: 204; owner-only CAS soft deletion, subsequent
read404, import/command replay never restores it. Repeated delete404.

Stage 4A personal persistence is OWNER-ONLY: scope=shared returns []; membership
PUT returns422 unsupported_input after ownership check. No automatic migration of
legacy workspace sharing. Hidden/other-user resources return404 for read/write.

## Reports

POST `/v1/reports`: `{case_id,title,payload:{...}}`, max128KiB payload, title1–200.
201 `{id,case_id,title,payload,provenance:"user_supplied_unverified",created_at}`.
GET `/v1/reports?offset=0&limit=20` lists own reports (bounded full records).
GET `/v1/reports/{id}` reopens; DELETE same path204. Report ownership must match
case ownership. A deleted case makes reports inaccessible; no public share URL,
PDF generation or provider validation is claimed. POST is not idempotent: reload
list after uncertain response, do not blindly retry. Reports cannot change owner.

## Errors and browser-local data

Structured errors `{error:{code,message,request_id,retryable,details?}}` follow
the existing VNext envelope. 401 authentication_required;403 account_suspended or
permission_denied;404 not_found;409 version_conflict/idempotency_conflict;
422 validation_failed/unsupported_input;429 rate_limited;503 account_unavailable
or maintenance. Do not render raw provider/SQL exceptions. No secret echoes.

Signing in never uploads localStorage. Anonymous/local drafts remain explicitly
this-browser-only. Prompt before explicit import per case/account; preserve local
bytes until successful commit and deliberate deletion. On account switch clear
in-memory private state and cancel/discard stale requests. Cross-device persistence
applies only to successfully committed cloud resources. No fake fallback to
localStorage on503. Frontend integration must call backend logout before SDK
signout; existing SDK-only logout does not yet implement this stronger guarantee.

## Current acceptance and frontend handoff

The activated image is
`sha256:dce27b6bd9b1d336e8b15c93559642722b5e98f4c21012df4718f220ab4c0cde`.
Endpoint and payload contracts above are unchanged. Sixteen protected operations
match the schema generated offline from that source. `/openapi.json` returns404
through the existing ingress policy; frontend integration uses this document.

Live private-role TLS, reviewed authority, exact schema/grants/RLS, secret mounts,
health/readiness, Stage1–3 regressions and unauthenticated/malformed denial pass.
The fresh focused backend pack passes 65 tests on private disposable PostgreSQL,
including signed sessions, profile persistence, Saved Cases across connections
and logout/new session, and foreign read/update/delete denial. These are backend
proofs; no real Supabase access token or live signed-in mutation was exercised by
the agent. See `reports/professor-stage4a-auth-userdb/final-live-acceptance.json`.

Frontend integration must collect sanitized outcomes for an existing authorized
user's session/account, profile update/readback, explicit case save/reopen,
backend logout followed by SDK signout, and a new login retaining the saved data.
Then check refresh and another authorized device. Use a second already authorized
account for live foreign-resource denial if one exists; this task does not
authorize creating or modifying Supabase users. Never send passwords, keys or
tokens to an agent or put them in evidence. Record statuses and persistence
outcomes only. Until those flows run, authenticated live acceptance stays pending;
no browser-local draft or disposable test is evidence of a real user's live save.
