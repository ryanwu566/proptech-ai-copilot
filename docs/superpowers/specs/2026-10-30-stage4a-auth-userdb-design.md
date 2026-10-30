# Professor Server Stage 4A design

User-authorized backend-only implementation, based on accepted Stage 3 HEAD
85a489d2cbd07c9df80bfa12206cc6a6242cf159, isolated branch
server/stage4a-auth-userdb-20261030. Frontend and historical worktrees are outside ownership.

## Audit and strategy

Browser `frontend_next/lib/vnext-auth-session.ts` uses supabase-js password
signup/login, persisted SDK sessions and refresh, local-scope signout, and reset
request only. FastAPI `services/vnext/auth.py` verifies RS256/ES256 public JWKS,
issuer/audience/expiry and UUID subject. No NextAuth/Auth.js or local password
store is used. Browser SDK storage is not HttpOnly. Backend bearer calls omit
cookies; existing write-Origin and pilot-cookie CSRF protections remain.

Read-only aggregate inspection of primary connected project proptech-valuation-db
on 2026-10-30 found one auth.users row and one user with prior sign-in. No user
identifiers, password hashes, tokens or email addresses were fetched. Deployment
identity/configuration still needs operator confirmation. No existing identity is
modified. Existing account authority expects Supabase auth.users FK in migration
020 and dedicated vnext_api. Personal CaseService deliberately uses an unavailable
repository. Legacy workspace cases are a separate contract. Browser Saved Cases,
decision rooms, preference profiles, comparison selections and exports are local;
logging in does not imply upload. Profiles here mean account display preferences,
not inferred property/buyer risk conclusions.

## Alternatives

KEEP hosted application persistence would not satisfy the local-data goal.
SELF-HOST authentication would introduce password, recovery and identity migration
risk for an existing user. Selected HYBRID retains Supabase identity and maps its
verified issuer/UUID to Professor application data. Selection is the implementer's
judgment under the user's express evidence-based architecture delegation.

## Boundaries

Use additive, independently versioned database/userdb migration, outside the
frozen valuation/legacy migration runner. Schema professor_user in proptech_app;
no local fake auth.users table or password migration. Direct least-privilege
professor_user_runtime login; forced RLS, transaction-local verified subject,
explicit owner predicates, immutable ownership and server account status/role.
Lazy user registration follows a verified token; fixed issuer binding prevents
cross-project UUID confusion. Local account state is independent of old hosted
account authority: activating requires an explicit reconciliation of existing
hosted suspensions/admin roles; absent that evidence activation stays blocked.

Reuse existing /v1/account and /v1/saved-cases shapes when explicitly configured.
Default legacy behavior remains. Personal cases owner-only, membership writes
unsupported, shared list empty. Transactional CAS, receipts, retained tombstones,
activity and source snapshot remain; never silently refresh provider evidence.
Profiles/preferences use CAS; reports are explicitly unverified saved user
snapshots, never newly generated provider conclusions. Anonymous drafts remain
browser-local until explicit consent. No automatic cross-user upload/migration.

JWT signature/expiry remain mandatory. Stage 4A additionally requires a verified
session_id UUID and integer iat/exp. Store session UUID revocation, never tokens;
logout revokes that local session across refreshes immediately. Browser must also
invoke Supabase local signout to revoke its refresh token. Remote signout/deletion
is not instantly observable offline: access JWTs may remain valid until expiry.
No promise of complete provider revocation detection. No local password endpoints.

## Acceptance and activation

Tests run against synthetic JWTs and a fresh Unix-socket-only disposable PostgreSQL
cluster; no real credentials. Supply operator-only additive provisioning command,
backup/rollback guidance, explicit disabled-by-default API profile. No live host
apply, image build, database migration or Docker recreation in this session.
Stage 4A remains PARTIAL until operator issuer/account-authority reconciliation,
provisioning and controlled image activation plus authenticated cross-device E2E.
No /dev/sda, X9, cloud deployment, paid provider, market_ops or port changes.
