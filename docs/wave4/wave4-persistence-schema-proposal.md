# Wave 4 persistence schema proposal

Status: **proposal only; no migration is created or registered in this branch**.
The API and frontend use a transactional seam; production uses
`UnavailableCaseRepository`, which returns 503 `maintenance` with reason
`persistence_pending`. There is no production memory store or successful-save
simulation. The only memory adapter is a rollback-capable test fixture.

## Migration sequencing and activation

This checkout ends at migration 021. Wave 1C may own **022**. After Wave 1C merges,
rebase on then-current main, inspect every migration and the registry, and allocate
the next unused sequence. **Suggested: 023 only if 022 is then the highest merged
sequence**; otherwise use `max(merged sequence) + 1`. Do not reserve 022 or register
this document as a migration. Preserve all existing registry checksums.

Activation requires a real SQL adapter, migration with grants/RLS/constraints,
disposable PostgreSQL conformance tests and production configuration review. It
must not be enabled merely by an environment flag or by interpreting missing
tables as empty accounts. Worker and notification activation are separate gates.

## Identity and authorization

Personal case identity is the existing verified `AuthenticatedPrincipal.user_id`
UUID, matching Supabase Auth. Account must be active on **every request**. Email,
browser IDs, JWT user metadata, localStorage roles, and workspace roles never
grant personal ownership. There is no implicit mapping from workspace
owner/admin/manager/member/viewer to personal owner/editor/viewer. Existing
`/v1/cases` workspace/property contracts remain unchanged.

| Personal case role | Read snapshot/activity | Edit title/notes | Manage members | Monitoring preferences |
| --- | --- | --- | --- | --- |
| owner | yes | yes | yes | yes |
| editor | yes | yes | no | no |
| viewer | yes | no | no | no |
| unrelated / revoked user | no | no | no | no |

Ownership is immutable in v1. Owner cannot be demoted, removed or duplicated in
memberships. There are no public links, bearer share tokens, anonymous reads,
email invitations, workspace inheritance, or owner transfer endpoints. Membership
requires an explicit Auth UUID. SQL must enforce that it references an existing
Auth identity; unknown targets return a bounded validation error without an
account discovery endpoint. Suspension is checked on each recipient's own request,
so no cross-account consumer status lookup is needed to grant membership.
Only owner sees the member roster; members see their
own effective role and `members_only` sharing state. Revocation is effective on
the next request; delivery/worker consumers must recheck it too.

## Proposed tables

Use the existing unexposed `vnext_private` schema and restricted `vnext_api` role
from current main; recheck these contracts after rebase. Table names below live
in that schema and are deliberately distinct from workspace case tables.
All UUID references must use the canonical existing Auth/account key after rebase.

| Table | Proposed columns / constraints |
| --- | --- |
| `personal_case_owners` | `case_id uuid PK`, `owner_id uuid NOT NULL FK auth.users(id)`, `created_at timestamptz NOT NULL`; UNIQUE `(case_id, owner_id)` for import consistency FK; owner immutable; minimal ACL root independent of cases |
| `personal_saved_cases` | `id uuid PK`, `owner_id uuid NOT NULL`, composite FK `(id, owner_id)` to `personal_case_owners(case_id, owner_id)`, `revision bigint NOT NULL CHECK >= 1`, `title text NOT NULL CHECK length BETWEEN 1 AND 500`, `notes text NOT NULL DEFAULT '' CHECK length <= 8000`, `created_at`, `updated_at` server timestamptz; immutable owner projection readable by authorized members |
| `personal_case_imports` | `case_id uuid PK FK cases(id)`, `owner_id uuid NOT NULL`, `import_key text CHECK length BETWEEN 1 AND 160`, `import_digest char(64)`, `snapshot jsonb NOT NULL`, `user_authored jsonb NOT NULL`, `imported_at timestamptz`; unique `(owner_id, import_key)`; immutable snapshot and authored originals; combined payload <= 262144 UTF-8 bytes under application validation, SQL conservative size guard |
| `personal_case_members` | `case_id uuid FK cases(id)`, `member_id uuid FK auth.users(id)`, `role text CHECK IN ('editor','viewer')`, `created_at`, `updated_at`; PK `(case_id, member_id)`; prohibit owner membership; at most 50 per case atomically |
| `personal_case_monitoring` | `case_id uuid PK FK cases(id)`, `cadence text CHECK IN ('off','daily','weekly') DEFAULT 'off'`, `refresh_policy text CHECK = 'manual_only'`, `updated_at`; row shares case revision; execution/delivery availability derived from server configuration, never asserted by caller |
| `personal_case_activity` | `case_id uuid FK cases(id)`, `revision bigint CHECK >= 1`, `actor_id uuid`, `kind text CHECK IN ('case_imported','metadata_updated','membership_updated','monitoring_updated')`, `occurred_at timestamptz`; PK `(case_id, revision)`; append-only; no note/evidence/token/email payload |
| `personal_case_commands` | `actor_id uuid FK auth.users(id)`, `http_method text CHECK IN ('POST','PATCH','PUT')`, `canonical_route text CHECK length <= 300`, `key_hash char(64)`, `request_fingerprint char(64)`, `case_id uuid FK cases(id)`, `revision bigint CHECK >= 1`, `created_at`, `expires_at >= created_at + interval '24 hours'`; PK `(actor_id,http_method,canonical_route,key_hash)`; committed reference only, no raw key/request/response body |

Use FK cascades for internal case children when a separately authorized account
deletion workflow is implemented; no case deletion API is added here. Choose
account-deletion retention/redaction rules before activation, including how actor
UUIDs in another owner's activity are handled. No raw JWT, credential, destination,
email address, provider response log or session document belongs in these tables.

`personal_case_owners` avoids recursive RLS: membership policies consult the small
owner ACL root rather than selecting `personal_saved_cases`, whose own read policy
consults memberships. Owner rows can be inserted first and all children inserted
within the same transaction. A deferred constraint trigger must require each owner
ACL root to have exactly one matching saved case at commit, preventing orphan ACLs.
The import `(case_id, owner_id)` composite FK must reference the matching owner
ACL root. Cases also carry an immutable, composite-FK-checked `owner_id`: a member
can read that authorized case projection even though the owner-only ACL root is
hidden by RLS. The adapter must not inner-join the hidden ACL root to open a shared
case. Use a lock-protected invoker trigger for cross-row membership constraints
(target is not owner; <=50 members); PostgreSQL CHECK constraints cannot contain
cross-table subqueries. The transaction adapter enforces these same rules before
the trigger, so all violations return safe application errors.

## RLS and grants

Enable **and force RLS on every table**. Revoke all from PUBLIC, anon and generic
Data API roles. Grant only the existing restricted backend request role, bound
through `DatabasePrincipalContext.transaction(principal)` and the established
server-validated UUID claim. Never connect using a bypass-RLS service key for
request operations. RLS predicates below use `uid` as shorthand for the existing
`(select auth.uid())`, bound by the transaction-local `request.jwt.claim.sub` /
`request.jwt.claims` settings. Do not invent a second principal variable.

Every policy must additionally require an active canonical consumer account.
Account suspension takes precedence over case roles, including platform admins.

| Table | SELECT USING | Write policy and column boundary |
| --- | --- | --- |
| owners | `owner_id = uid` | INSERT WITH CHECK `owner_id = uid`; no UPDATE/DELETE grants |
| members | `member_id = uid OR EXISTS owner ACL for (case_id, uid)` | owner-only INSERT/UPDATE/DELETE; USING and WITH CHECK owner ACL; CHECK target != owner; UPDATE grant on role only |
| cases | `owner_id = uid` OR own membership | INSERT WITH CHECK own ACL and owner_id = uid; UPDATE USING and WITH CHECK owner/editor access; column grants title, notes, revision, updated_at only; immutable id/owner enforced below grants and composite FK |
| imports | same readable-case predicate | INSERT only with own ACL and matching import owner; no UPDATE/DELETE; immutable digest/snapshot/user_authored |
| monitoring | same readable-case predicate | owner-only INSERT/UPDATE, both USING/WITH CHECK; cadence/updated_at only; no caller execution state |
| activity | same readable-case predicate | INSERT CHECK actor_id = uid AND owner/editor access, with transaction trigger checking matching revision/kind; no UPDATE/DELETE |
| commands | `actor_id = uid` (hashed receipt metadata only) | INSERT CHECK actor_id = uid AND current command-specific write permission; immutable committed references; expiry-only bounded DELETE under actor scope, never evict live receipts |

Policies alone cannot enforce a compare-and-swap or tie an activity INSERT to an
authorized mutation. The SQL adapter must use a transaction with guarded writes;
use invoker functions or narrowly scoped trigger validation where needed. Do not
expose unrestricted SQL writes through the Data API. Any necessary definer trigger
must live in the private schema, fix `search_path`, qualify objects, revoke public
EXECUTE, and validate the canonical principal; require a separate security review.
No broad `SECURITY DEFINER` ACL helper is needed for the acyclic owner/member design.
Receipt SELECT/count and expired-only DELETE are actor-scoped even after a case
membership is revoked, so actor admission still counts all live receipts and
performs bounded expiry cleanup. This exposes only the actor's own prior hashed
command metadata/references. It never authorizes case reads or replay: recheck
current case write permission before projecting the referenced resource.

RLS decisions follow [Supabase's current RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security): grants control operations; row policies
must restrict ownership and both USING/WITH CHECK must protect updates.

## Indexes and bounded access

- Owners: `(owner_id, case_id)` supports stable owned list pagination and ACL lookup.
- Members: PK `(case_id, member_id)` plus `(member_id, case_id)` for own ACL/shared list.
- Cases: PK id and `(owner_id, id)` for owned lists; optional `(updated_at DESC, id)` for a future cursor order. v1 seam
  specifies stable UUID ordering; SQL adapter must match, using bounded offset.
- Imports: unique `(owner_id, import_key)`, PK case_id; no JSON GIN index needed.
- Activity: PK `(case_id, revision)` supports reverse revision pages.
- Commands: scoped PK plus `(actor_id, expires_at)` for live count/expiry cleanup
  and `(case_id)` for the FK. No index on canonical body JSON: none is retained.
- Monitoring: PK case_id; future partial `(next_due_at, case_id)` WHERE enabled
  only when job scheduling is actually introduced.

List and activity API defaults are 20, max 100, offset max 10000. Frontend uses 20
and explicit pagination; list responses omit the historical evidence snapshot.
CaseTransaction has separate append and paged activity methods; a SQL adapter
must apply offset/limit in the query rather than loading full history.
No unbounded browser polling, subscriptions
or automatic provider reads are permitted for status rendering.

## Atomic adapter requirements

Implement `CaseRepository.transaction(principal)` / `CaseTransaction` from
`services/vnext/durable_cases.py`. No SQL adapter is shipped before the schema exists.

1. Every mutation, including membership revocation, must acquire the common
   `personal_saved_cases` row lock through its guarded compare-and-swap UPDATE
   before writing child rows. Recheck the live ACL/account policy in that UPDATE;
   all ACL changes advance the same case revision. Read-only `get` must use an
   ordinary authorized SELECT so viewers can open cases. Never lock the immutable
   owner ACL root: members cannot see it and request roles have no UPDATE grant.
   If an adapter uses an explicit case-row `FOR UPDATE`, do so only on an already
   authorized write path, never on viewer/read paths. Use case-row, children,
   activity order consistently; no child write may precede the guarded case write.
2. Creation reserves the unique `(owner, import_key)` under a transactional advisory
   lock or insert-conflict/read pattern. Same digest returns the existing case;
   different digest returns 409 `idempotency_conflict`. Digest covers original
   snapshot and authored attachments, not mutable metadata. Retries after a lost
   response must not create duplicates, even when metadata was edited meanwhile.
3. `replace(record, expected_revision)` must execute `UPDATE ... WHERE id = ? AND
   revision = expected_revision`, require exactly one row, and insert membership,
   preference and activity changes in **that same transaction**. Any failure rolls
   back everything. Store activity as separate append-only rows, not an overwritten
   JSON array. No lost update or last-write-wins fallback.
4. Snapshot and user_authored are immutable after creation. Metadata patch only
   changes title/notes. Server-created timestamps belong outside original JSON.
5. Acknowledge only after transaction commit. Errors are bounded safe envelopes,
   never raw SQL/provider payloads. Reopen/list/activity never import providers.
6. Adapter conformance must test two real DB connections racing writes and revocation,
   commit failure rollback, duplicate imports, permission denied and suspended users.
   Run direct SQL tests as anon, request A/B, member and bypass-free app role to
   establish RLS enforcement. Current in-memory tests prove service contracts,
   **not database isolation, SQL grants, or RLS execution**.
7. All four personal mutations require the platform's bounded `Idempotency-Key`
   header, in addition to import deduplication/CAS. Implement `find_command` and
   `append_command` in the same transaction. Acquire the actor admission lock
   before case locks to serialize scoped duplicate lookup and the 2048-live-receipt
   cap. After authorization, replay matching committed references without another
   write/activity; changed canonical body is 409 idempotency conflict. New keys
   never bypass revision CAS. Store hashes/references only, retain at least 24h,
   prune at most 100 expired rows per admission and fail closed at capacity.
   No receipt may survive a failed mutation or commit. Recheck current write role
   on replay; return the current authorized case projection like existing VNext
   parcel-set commands, never an old private roster. Include duplicate races,
   revocation, changed-body reuse, expiry, capacity and receipt-failure rollback
   in future two-connection conformance tests. No SQL adapter/table is created here.

## Browser-to-account workflow and sync semantics

`/cases` retains the original browser repository and adds a separate Cloud panel.
Mounting, logging in, restoring a session, returning online or rendering sync status
never uploads or calls an analysis provider. User selects a local case, previews,
and explicitly confirms. The reader uses original storage JSON, bypassing evidence
normalizers. It includes the case's separate Decision Room document without
rewriting notes/history, and rejects duplicates, invalid JSON, excessive size or
credential-shaped fields/values as a whole. It never silently strips fields.

Before POST, reread and compare the content digest to the confirmed preview; if
the local case/notes changed, require a new preview. An import key is a SHA-256
digest of this immutable payload; server uniqueness is scoped to the verified
owner. Upload success, timeout, auth failure, conflict and 503 all leave the
original local bytes untouched. No cloud copies, import markers, session tokens,
pending upload queues or cloud drafts are written to browser storage. Existing
Auth SDK session handling remains in its existing storage boundary.

Successful save means a server acknowledgment, not continuing live synchronization.
The UI states local changes do not auto-sync, shows Cloud revision/last-read time,
and requires explicit refresh. Conflict leaves the draft intact, disables blind
retry and requires reading the latest revision. The UI displays remote metadata
alongside the retained draft before another explicit save. Offline disables writes
and does not retry on reconnect. Account change clears displayed Cloud data; client
checks the session generation after both fetch and JSON decoding to discard late
responses. A new account must never see a prior account's Cloud state.

## Monitoring, change detection and notification contracts

`case_monitoring.py` defines pure source observations and a bounded cached-check
planner. Source change means a different normalized source **content digest** for
the same source with known available observations. New baselines, failed/unknown
states, fetched timestamps, source publication timestamps alone and UI rerenders
never emit a source-change claim. Unknown remains unknown; old evidence stays intact.

Preferences are off/daily/weekly, provider refresh is always manual-only. Execution
and delivery remain `not_configured` regardless of saved cadence. No worker,
cron job, provider refresh endpoint, browser interval or outbound notification is
configured by this branch. Pure planning is disabled without explicit worker
configuration, deduplicates case IDs and caps a batch at 20 and remaining quota.

Future worker schema (separate activation/migration):

- `personal_case_monitor_jobs`: case_id, due_at, scheduled_window, lease_until,
  attempt_count <= 3, status; UNIQUE `(case_id, scheduled_window)`; partial due index.
- `personal_case_source_observations`: case_id, source_id, content_digest,
  provider state, source_updated_at, checked_at; append-only separate observations.
- `personal_case_notification_outbox`: event_id, case_id, activity_revision,
  recipient_id, kind, deduplication_key UNIQUE, status, attempt_count, next_attempt_at.
  No destination/token/secret in event payload; recipient resolved server-side.

Worker claims use SKIP LOCKED and leases, daily >=24h / weekly >=7d with bounded
jitter, at most 20 claims per batch, bounded backlog, retries with exponential
backoff and no catch-up burst. Recheck active owner/account/membership, preference
revision, quota and provider policies before work. Reuse Wave 1C's then-current
quota contract; cached jobs cannot spend provider quota or invoke refresh. A future
expensive manual refresh requires an independent explicit action and atomic quota
reservation; never bypass current provider admission or auto-refresh on reopen.
The worker activation migration must extend the activity kind allowlist for
trusted `source_changed` observations and define the atomic observation/activity/
outbox transaction. There is deliberately no client endpoint to assert that a
provider source changed or to manufacture monitoring success.

`NotificationDelivery` is an interface only. The event contains case UUID,
recipient UUID, revision and kind with a stable deduplication key. No existing
delivery integration was adopted. Before enabling delivery, configure a real
provider, obtain channel consent, validate destinations server-side, recheck case
access at send time, and test idempotency/failure semantics. Do not report email
or SMS as sent until a real provider acknowledges it.

## Endpoint contract

All `/v1/saved-cases` routes require existing bearer verification and active account,
reject forged identity headers/query fields, and return no-store responses.
All four mutation routes require `Idempotency-Key` with the existing platform
16–128 character allowlist. Create's import key and update CAS remain additional
protections; they do not exempt these commands from the header/replay contract.

| Method/path | Body / semantics |
| --- | --- |
| POST root | snapshot, user_authored, import_key, strict explicit_consent=true; 201 only after commit |
| GET root | scope=owned/shared, offset, limit; no evidence payload |
| GET /{UUID} | immutable snapshot + bounded metadata, effective role, prefs and sharing state |
| PATCH /{UUID}/metadata | expected_revision, title and/or notes only |
| PUT /{UUID}/membership | expected_revision, member_id UUID, editor/viewer or null to revoke; owner only |
| PUT /{UUID}/monitoring | expected_revision, off/daily/weekly, manual_only; owner only |
| GET /{UUID}/activity | reverse revision page; no note/evidence payload |

401 invalid session; 403 insufficient role/suspension; 404 absent or unrelated
resource; 409 revision/import conflict; 422 invalid/credential/forged fields;
503 persistence pending or safe unavailable. Future SQL adapter must preserve these
contracts and the unchanged Auth/Saved Case regressions before activation.
