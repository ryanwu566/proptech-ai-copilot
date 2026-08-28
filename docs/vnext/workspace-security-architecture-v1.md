# Workspace and Security Architecture v1

Status: Stage 0 decision contract; no tenant, Auth, RLS, Storage or PostGIS change applied

## 1. Current boundary

The current production-like architecture uses a server-only PostgreSQL URL and FastAPI owns
database/provider access. The browser receives only a public API origin. Pilot flows use
application-defined participant tokens and short-lived reviewer/administrator cookies; the
repository does not currently use Supabase Auth, Supabase client libraries or the Data API.

Existing tables are not a uniform multi-tenant schema. Several legacy/public tables have no
RLS, while PLVR generation tables enable RLS and security-invoker views. This is safe only
under the present server-only/no-Data-API assumption and least-privilege database grants. It
must not be interpreted as approval to expose `public` through Supabase REST/GraphQL.

## 2. Workspace model

Both personal and team workspaces use the same domain and tenant key.

```text
workspace
  workspace_id
  workspace_type       personal|team
  display_name
  status               active|suspended|archived
  created_at/updated_at/archived_at

workspace_member
  workspace_member_id
  workspace_id
  user_id
  role                 owner|admin|manager|member|viewer
  status               invited|active|suspended|left|removed
  invited_at/joined_at/left_at/revoked_at
```

A personal workspace has one active owner and can use the same member/RLS logic. Team
functionality remains gated off until invitation, role, removal and isolation E2E tests pass.

## 3. Role contract

Roles are workspace-local. A user can hold different roles in different workspaces.

| Operation | owner | admin | manager | member | viewer |
| --- | --- | --- | --- | --- | --- |
| Read permitted workspace properties/cases/evidence | yes | yes | yes | yes | yes |
| Create/update ordinary cases and activities | yes | yes | yes | yes | no |
| Confirm identity / attach confirmed resolution | yes | yes | yes, if assigned/policy allows | policy-controlled | no |
| Upload ordinary case documents | yes | yes | yes | policy-controlled | no |
| Read sensitive title/contact documents | policy-controlled | policy-controlled | assignment + purpose | no by default | no |
| Assign cases/manage workflow | yes | yes | yes | no | no |
| Invite/remove members or change non-owner roles | yes | yes | no | no | no |
| Transfer ownership/archive workspace | yes | no | no | no | no |
| Run exports/AI approvals | yes | yes | policy-controlled | policy-controlled | no |

The table states maximum conceptual permission. Resource assignment, sensitivity class,
feature gate, case state and evidence status may further restrict it. `owner` is not a database
superuser.

## 4. Authenticated principal decision

Decision: VNext uses **Supabase Auth** as its authentication source. The canonical user
identifier is the UUID at `auth.users.id`.

```text
Supabase Auth access token
        -> FastAPI authentication boundary
        -> canonical principal = auth.users.id
        -> workspace_members.user_id
        -> workspace_id + active membership + role authorization
        -> shared Consumer / Professional domain services
```

FastAPI remains the primary application API/BFF. Consumer and Professional modes do not fork
into separate domain backends. FastAPI validates the Supabase-authenticated principal, resolves
the workspace resource and applies domain authorization before normal request-path database or
Storage access. This decision does not add Auth code or change current pilot sessions in
Stage 0.

`workspace_members.user_id` references `auth.users.id`. Auth-user deletion must not cascade
away durable evidence, activities or audits; the deletion/deactivation workflow first revokes
sessions and memberships and then applies the approved retention/anonymization policy.

Pilot participant/reviewer/administrator roles remain a separate existing boundary and are not
implicitly promoted into workspace membership. JWT `user_metadata`/`raw_user_meta_data` is
never used for authorization because it is user-editable. Membership rows are the source of
truth for workspace roles; token claims do not replace a current active-membership check for
sensitive operations.

## 5. Schema exposure decision

| Schema/surface | Stage 0 decision | Access |
| --- | --- | --- |
| existing `public` application tables | Treat as server-only until every grant/table/policy/view is inventoried | least-privilege backend/ops roles; no new Data API exposure |
| `compact_green` | Server-only PLVR query schema | valuation backend/loader only |
| future `vnext_core` | Private-by-default tenant/domain base tables | VNext backend role; RLS defense in depth |
| future `vnext_private` | Sensitive document/contact/title metadata and audit internals | narrowly privileged server roles only |
| future `api_v1` | Optional future Data API projections/RPCs | not exposed until Auth/RLS/GRANT acceptance passes |
| Storage private buckets | Private objects only | policy-controlled object access or short signed operation |

Data API schema exposure and SQL grants are separate from RLS. A table must first be granted
to a Data API role and then pass its RLS policy; neither control substitutes for the other.
Every table in an exposed schema has RLS enabled before any `anon`/`authenticated` grant.
Private schemas also use RLS where practical as defense in depth.

## 6. RLS strategy

Base rule: no anonymous tenant rows. Every tenant policy verifies an active membership for
the row's `workspace_id`; `TO authenticated` alone is not authorization.

The normal application role never owns tenant tables or has `BYPASSRLS`. VNext migrations
also evaluate `FORCE ROW LEVEL SECURITY` for tenant tables so owner-context maintenance cannot
silently become an application access path; exceptional operator jobs use explicit, audited
roles and never share credentials with request handling.

Conceptual read predicate:

```sql
exists (
  select 1
  from vnext_core.workspace_members member
  where member.workspace_id = row.workspace_id
    and member.user_id = (select auth.uid())
    and member.status = 'active'
)
```

Conceptual mutation rules add allowed roles and resource-specific checks. `UPDATE` policies
must have both `USING` (current row authorization) and `WITH CHECK` (new row ownership/role
authorization), plus a matching `SELECT` policy. Inserts never accept a caller-supplied
workspace unless membership and role are verified. Deletes are generally replaced by
audited archive/status commands.

Policy design:

- `workspaces`: active members may read; owners control ownership/archive operations through
  an audited server command.
- `workspace_members`: active members may read a bounded roster; only owner/admin commands
  invite/change/remove, and the last owner cannot be removed.
- property/case/relation/evidence/activity/artifact rows: membership plus role/sensitivity;
  both referenced records must share `workspace_id`.
- `audit_events`: authorized server role inserts; tenant viewers receive only approved audit
  projections if the product later exposes them; no update/delete policy.
- sensitive document/contact/title rows: no generic member select; use an assignment/purpose
  checked server command and audit each access.

Views use `security_invoker = true` on supported PostgreSQL versions and inherit caller RLS.
On unsupported versions, keep them unexposed/revoke Data API roles. `SECURITY DEFINER` is not
used as a permission-error workaround. If an exceptional internal definer function is later
required, it lives in a non-exposed schema, sets a safe `search_path`, checks the principal
and workspace in its body, receives explicit grants only, and is security-reviewed.

## 7. Database roles and `service_role`

Use distinct roles/credentials:

- `vnext_api`: normal FastAPI request path; no schema ownership, no bypass RLS, no DDL;
- `vnext_ingest`: reviewed provider imports/evidence append within bounded schemas;
- `vnext_worker`: background jobs with purpose-specific grants;
- `vnext_migrator`: operator-only DDL during reviewed migrations;
- `vnext_audit_writer`: optional append-only audit insert path;
- read-only operations/analytics roles with approved projections only.

Supabase `service_role`/secret key is allowed only in trusted server/operator environments for
operator jobs, migrations, trusted background jobs, privileged administrative tasks and
necessary private Storage operations. Each path remains purpose-scoped and audited. It is not
the normal authorization mechanism and must be wrapped by application authorization.

It is forbidden in:

- `NEXT_PUBLIC_*`, browser bundles, localStorage/sessionStorage/cookies;
- public API responses, logs, analytics, screenshots, tickets or docs;
- user-supplied headers and client-to-database calls;
- provider adapters that do not need Supabase administration;
- general user-facing request handling or any path that uses it to bypass normal
  workspace/membership/resource authorization.

## 8. Personal/team lifecycle and departure

- Personal workspace creation is idempotent per user and cannot silently become a team.
- Invitations expire and do not grant access until accepted by the intended principal.
- Suspension immediately denies new access. Because JWT claims/session state can be stale,
  sensitive operations check current membership server-side; session revocation/short token
  lifetime is part of the chosen Auth design.
- On `left|removed`, the member loses read/write and signed-URL issuance immediately. Assigned
  cases/tasks require an audited reassignment or remain unassigned.
- Authored evidence, activities and audit events remain attributed to a stable principal ID;
  they are not deleted or reassigned. User-facing profile fields may be minimized/anonymized
  under a reviewed privacy process.
- The last active owner must transfer ownership before leaving/archiving.
- Links and signed URLs already issued use short TTLs; high-sensitivity access can use
  server-proxied downloads or session checks for stricter revocation.

## 9. Private documents, contacts and title data

No public title/contact table is created.

Future Storage contract:

1. private bucket per sensitivity class or one private bucket with policy-enforced object
   prefixes; documents, title and report artifacts never use a public bucket;
2. object key generated by server, for example
   `<workspace-id>/<case-id>/<artifact-id>/<version>`; filenames are metadata, not path auth;
3. artifact row created in `pending_upload`; upload is size/type bounded and malware/content
   validation runs before `available`;
4. Storage policies and server checks verify active membership, role, assignment and artifact
   workspace; Storage upsert, if allowed, requires insert/select/update rights and creates a
   new object version rather than overwriting evidence;
5. downloads use a one-use server stream for highest sensitivity or a signed URL normally
   expiring in 60-300 seconds; exact TTL is risk-class policy;
6. signed URLs are issued only after authorization, never persisted in evidence/activities,
   never logged, and each issue/access/share is audited;
7. sharing uses explicit recipient/scope/expiry/revocation records, not forwarded permanent
   links;
8. retention/legal hold applies independently to object bytes, metadata tombstone and audit.

Contact data should be field-encrypted with keys outside the database where warranted. Search
uses minimal derived indexes; plaintext contacts and owner identity never appear in public
projections. Title purchase requires partner contract, explicit user confirmation, idempotency,
cost disclosure and audit before any implementation.

## 10. Audit architecture

`audit_events` is append-only and server-only:

```text
audit_event_id
workspace_id
actor_type / actor_id
operation
subject_type / subject_id
occurred_at
request_id
idempotency_key_hash
source
before_ref / after_ref
outcome
reason_code
metadata                 # bounded, allowlisted; no raw payload/secrets
```

Audit identity confirmation, merge/split, membership/role change, document upload/access/share,
title purchase, CRM edit, case assignment, export, AI run/approval and sensitive signed-URL
issuance. Database privileges deny update/delete to application roles. Integrity controls may
add a hash chain or external immutable sink later, but must not block the transactional write
without a defined failure policy. Activities and audits are different: activities are
user-facing workflow; audits are security/accountability evidence.

## 11. PostGIS adoption

Current spatial behavior is application-side and existing data semantics remain unchanged.
Future adoption is additive:

1. owner confirms managed PostgreSQL/PostGIS support and extension schema;
2. create extension in an approved `extensions` schema using the selected migration tool;
3. add new VNext `geography(Point,4326)`/`geometry` columns or tables, preserving raw input and
   original CRS evidence;
4. validate Taiwan bounds and coordinate order; do not treat point geometry as legal parcel;
5. use EPSG:4326 for interchange and an appropriate TWD97 projected CRS for area/distance;
6. add GiST/SP-GiST indexes and inspect representative `EXPLAIN (ANALYZE, BUFFERS)` on synthetic
   or approved non-sensitive data;
7. deploy read path behind a disabled feature gate, backfill separately, compare, then enable;
8. rollback by disabling the gate/application read path; preserve additive columns until a
   later reviewed retention decision.

## 12. Security acceptance gate

Before Stage 1 persistence or any Data API exposure:

- Supabase Auth token validation and `auth.users.id` principal mapping are contract-tested;
- clean and upgrade migrations pass in a disposable managed-Postgres equivalent;
- every exposed table has explicit grants, RLS enabled and positive/negative policies;
- cross-tenant read/write/link tests pass for all roles;
- `UPDATE` policies prove both `USING` and `WITH CHECK` behavior;
- anonymous access and `TO authenticated`-only BOLA are denied;
- views/functions, Storage objects and signed URLs pass privilege tests;
- service-role/secret leakage scans pass frontend bundle and logs;
- member removal blocks new access immediately and expires old links within policy;
- audit rows cannot be updated/deleted by application roles;
- backup/restore and RLS deployment ordering are rehearsed.

Current architecture result: the authentication/workspace-principal decision is complete.
Production Supabase policy/schema remediation remains implementation work owned by
`security/supabase-rls-hotfix` and is a required external pre-Stage-1 security gate. This
document does not modify its live schema or migrations.
