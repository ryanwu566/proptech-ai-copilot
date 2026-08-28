# VNext Architecture Overview v1

Status: Stage 0 architecture contract; no runtime implementation
Date: 2026-08-28
Decision authority: `docs/vnext/stage-0-architecture-signoff.md`

## 1. Scope and source hierarchy

VNext adds an architecture foundation for confirmable property identity, durable cases,
traceable evidence, tenant workspaces, and later professional capabilities. Stage 0 adds
documentation only. It does not add a resolver, database migration, API route, feature,
provider call, or UI.

The review used active documentation and current code. When they conflict, current code
wins. In particular:

- `SavedCase` is a browser-only version-1 object stored at
  `proptech.savedCases.v1`; it is not a durable server Case.
- The production boundary is Next.js -> FastAPI -> managed PostgreSQL. The frontend has
  no database credentials.
- The repository does not currently use Supabase Auth or the Supabase Data API. Pilot
  authorization uses application-defined participant/reviewer/administrator sessions. This
  describes current code; the VNext architecture decision is Supabase Auth with
  `auth.users.id` as the canonical user identifier.
- The reviewed production migration runner registers migrations `004` through `010`.
  Earlier valuation/market migrations and the `011` compact-green schema have separate
  operational paths.
- `docs/itaiwan-proptech-deep-workflow-audit-v1.md`, named as a mandatory design input,
  is absent. No archive document was substituted for it. This is a signoff blocker.

## 2. Current architecture

```text
Browser / Next.js
  - consumer journey and tools
  - runtime/session context
  - SavedCase v1 in localStorage
             |
             v
FastAPI
  - request validation and safe errors
  - deterministic tax/loan/holding-cost services
  - valuation, market, location, terrain, commute and pilot routes
  - server-only provider credentials
             |
             v
Managed PostgreSQL in production-like environments
  - pilot evidence and TaxOracle history
  - PLVR/market generations and aggregates
  - no general VNext tenant/property/case model yet
```

The present case model is a decision snapshot assembled from frontend module outputs.
It can be saved, compared, loaded and printed, but has no canonical property identity,
workspace ownership, durable evidence lineage, server-side activities, or artifact model.

## 3. Target domain principles

1. `PropertyEntity` is an application aggregate representing the asset currently believed
   to be under study. It is not claimed to be a nationwide government property ID.
2. `Case` records why a workspace is studying a property. Property and Case are different
   lifecycles; one property may have many cases.
3. `Evidence` is an attributable, time-aware statement. Unknown is never rewritten as
   zero, none, safe, available or verified.
4. Address, parcel, building and listing relations are many-to-many, temporal and
   confidence-bearing.
5. A property becomes confirmed only after candidate review and an attributable human
   confirmation. Similar strings never authorize a destructive merge.
6. Tenant authorization is enforced at the data boundary and server boundary, never by
   navigation visibility alone.
7. AI synthesizes evidence; it does not own identity, deterministic calculations or
   authoritative facts.

### Authentication and application boundary

- Supabase Auth is the VNext authentication source.
- `auth.users.id` UUID is the canonical user identifier.
- FastAPI remains the application API/BFF for both Consumer and Professional modes. It
  validates the authenticated principal and enforces domain/workspace authorization; VNext
  does not create a second professional backend.
- `workspace_members.user_id` references `auth.users.id`. Authorization requires the resource
  `workspace_id`, an active membership, and an allowed `owner|admin|manager|member|viewer`
  role.
- Every future tenant-owned table exposed through a browser-reachable Supabase surface has
  RLS. `TO authenticated` alone is insufficient; policies also evaluate `(select auth.uid())`
  and active workspace membership.
- Documents, contacts, ownership/title data and private CRM notes are server/private-storage
  surfaces by default, not directly browser-readable base tables.

## 4. Bounded contexts

| Context | Owns | May depend on | Must not own |
| --- | --- | --- | --- |
| Providers | External adapters, access errors, source metadata | Provider configuration | Domain truth or UI claims |
| Evidence | Evidence items, status, coverage, freshness, lineage | Providers, Artifacts | Property merge decisions |
| Identity | Resolution requests, candidates, confirmations | Evidence, Workspace | Case purpose or AI prose |
| Property Graph | Entities, graph nodes, temporal relations | Identity, Evidence, Workspace | Provider execution |
| Spatial | Coordinates, CRS, geometries, spatial predicates | Evidence, Providers | Legal parcel identity |
| Market | PLVR releases, aggregates, comparable facts | Providers, Evidence | Valuation truth or purchase advice |
| Case | Purpose, assignment, workflow state, attached property | Property Graph, Evidence, Workspace | Canonical identity |
| Workspace | Tenant, membership, role, status | Authentication boundary | Property facts |
| Documents | Private document metadata and processing state | Workspace, Artifacts, Evidence | Public title/contact access |
| Artifacts | Files, reports, exports and immutable references | Case, Evidence, Workspace | Authoritative facts |
| Activities | User-visible operational timeline | Case, Workspace | Immutable security audit |
| CRM | Contacts, tasks and communications | Case, Workspace, Activities | Automatic owner identity from ambiguity |
| Deterministic Intelligence | Valuation/tax/finance/risk calculations | Evidence, Market, Spatial | Provider or AI fallback truth |
| AI Synthesis | Summaries, comparisons and drafts | Evidence, Case, deterministic outputs | Fact mutation, identity confirmation |

## 5. Dependency direction

```text
Provider adapters
      |
      v
Evidence + raw artifact references
      |
      v
Identity resolution + Property Graph
      |
      v
Deterministic Intelligence
      |
      v
Case Workflow
      |
      v
AI Synthesis
      |
      v
Artifacts / Consumer UX / Professional UX
```

Workspace authorization surrounds every server-side layer. Activities record user-visible
workflow events; append-only audit records security-significant mutations independently.
A downstream layer may quote an upstream fact only with its evidence reference and status.
A provider or AI failure cannot be replaced by demo success.

## 6. Conceptual core model

All durable tenant rows carry `workspace_id`. Identifiers are opaque, server-generated UUIDs
(application-generated UUIDv7 is preferred when the selected runtime supports it). Business
keys such as an address or lot number are searchable attributes, never primary keys.

### `workspaces`

- Responsibility: personal or team tenant and its lifecycle.
- Stable identifier: `workspace_id`; immutable. `workspace_type` is `personal|team`.
- Mutable: display name and controlled status transitions.
- Sensitive: billing/organization metadata, if added, is private.
- Temporal: `created_at`, `updated_at`, `archived_at`.
- FKs/indexes: unique personal-workspace owner rule; status index.
- Tenant/retention: root tenant record; archive before deletion. Legal/contract retention is
  an owner decision.

### `workspace_members`

- Responsibility: user-to-workspace authorization.
- Stable identifier: `workspace_member_id`; unique `(workspace_id, user_id)` while active.
- Mutable: role and membership status, only through audited commands.
- Sensitive: user ID, invitation and membership metadata.
- Temporal: `invited_at`, `joined_at`, `left_at`, `revoked_at`, `updated_at`.
- FKs/indexes: restrictive FK to workspace and `auth.users.id`; indexes on
  `(user_id,status)` and `(workspace_id,status,role)`.
- Tenant/retention: workspace-scoped; retain tombstone and audit reference after departure.

### `property_entities`

- Responsibility: application-level property aggregate, not a government identifier.
- Stable identifier: `property_entity_id`; immutable.
- Mutable: lifecycle state and preferred display label. Confirmed facts live as relations or
  evidence, not overwritten label strings.
- Sensitive: inferred occupancy/ownership must not be stored here.
- Temporal: `created_at`, `updated_at`, `superseded_at`; no hard delete during merge/split.
- FKs/indexes: workspace FK; indexes on workspace/state and optional normalized search keys.
- Tenant/retention: workspace-scoped; retain while referenced, then archive/tombstone.

### `addresses`

- Responsibility: normalized address observations and their source form.
- Stable identifier: `address_id`; address text is mutable/temporal, not identity.
- Mutable: normalization version and display formatting; original observation is preserved.
- Sensitive: full unit/door address is private tenant data.
- Temporal: `observed_at`, `valid_from`, `valid_to`, `superseded_at`.
- FKs/indexes: workspace FK; equality/search index on a hashed/normalized key, not global
  uniqueness. Trigram search is optional and cannot merge entities.
- Tenant/retention: workspace-scoped; redact/export under workspace policy.

### `geo_references`

- Responsibility: point or geometry reference plus CRS and provenance.
- Stable identifier: `geo_reference_id`; geometry revisions create new evidence-backed rows.
- Sensitive: exact coordinates can identify a private address.
- Temporal: `effective_at`, `retrieved_at`, `valid_to`.
- FKs/indexes: workspace FK, evidence FK where available; GiST index only after PostGIS is
  introduced. Coordinate equality is not identity.
- Tenant/retention: workspace-scoped; raw upload retention follows artifact policy.

### `property_relations`

- Responsibility: temporal, evidence-backed edges among graph nodes.
- Stable identifier: `property_relation_id`; revisions supersede rather than overwrite.
- Mutable: proposed edges may transition status; confirmed edge history is immutable.
- Sensitive: owner/contact/title relations are held in private contexts, not public edges.
- Temporal: `valid_from`, `valid_to`, `confirmed_at`, `superseded_at`.
- FKs/indexes: workspace, from/to graph node, evidence and confirmer FKs; indexes on both
  edge directions, type/status, and open temporal range.
- Tenant/retention: both endpoints must share a workspace; retain relationship history.

### `cases`

- Responsibility: purpose-specific investigation workspace such as
  `buy_due_diligence`, `development`, `brokerage`, `valuation_review` or
  `investment_review`.
- Stable identifier: `case_id`; optional property attachment can change only through an
  audited command.
- Mutable: title, purpose, workflow status, assignment and notes.
- Sensitive: notes, financial inputs, contacts and assignments.
- Temporal: `opened_at`, `updated_at`, `closed_at`, `archived_at`.
- FKs/indexes: workspace FK, optional confirmed property FK, assignee member FK; indexes on
  workspace/status/updated time and property/purpose.
- Tenant/retention: workspace-scoped; soft archive. Child evidence/artifacts use restrictive
  deletion and a reviewed retention job.

### `evidence_items`

- Responsibility: immutable, attributable fact versions.
- Stable identifier: `evidence_id`; corrections create a new row with `supersedes_id`.
- Mutable: only controlled lifecycle status metadata; fact value and lineage are immutable.
- Sensitive: value or raw artifact may be private; public projections are allowlisted.
- Temporal: `retrieved_at`, `effective_at`, `expires_at`, `created_at`.
- FKs/indexes: workspace, subject graph/case, source, raw artifact and superseded evidence;
  indexes on subject/fact/effective time and status/expiry.
- Tenant/retention: retain lineage at least as long as any dependent decision/artifact.

### `artifacts`

- Responsibility: metadata for uploads, reports, exports and provider raw objects.
- Stable identifier: `artifact_id`; object versions are immutable.
- Sensitive: storage path, title documents, contact exports and provider raw data.
- Temporal: `created_at`, `retention_until`, `deleted_at`.
- FKs/indexes: workspace/case/evidence FKs; unique storage object version; retention index.
- Tenant/retention: private bucket only; delete bytes through a reviewed lifecycle while
  preserving a non-sensitive tombstone/audit reference where required.

### `activities`

- Responsibility: user-facing Case timeline such as assignment, note or task completion.
- Stable identifier: `activity_id`; corrections append compensating activity.
- Sensitive: actor, notes and CRM context.
- Temporal: append-only `occurred_at`, optional `effective_at`.
- FKs/indexes: workspace, case, actor member and optional artifact/evidence; indexes on
  `(case_id,occurred_at desc)` and actor/time.
- Tenant/retention: workspace-scoped; case retention applies.

### `audit_events`

- Responsibility: append-only security and accountability ledger.
- Stable identifier: `audit_event_id`; request ID and idempotency reference are separately
  indexed, not globally treated as event identity.
- Immutable/sensitive: actor, operation, subject and before/after references are immutable;
  no raw secrets or document bodies.
- Temporal: `occurred_at`, ingestion time and optional retention/legal-hold time.
- FKs/indexes: workspace and actor references may be retained as stable IDs even after user
  departure; indexes on workspace/time, subject/time, request ID and operation/time.
- Tenant/retention: server-only, no end-user update/delete policy. Partitioning may be added
  when volume justifies it; retention requires security/legal approval.

An internal `property_graph_nodes` support table may map typed records to graph node IDs so
both endpoints of `property_relations` retain real FKs. It is not a new product concept.
Parcel, Building and Listing remain future typed node records; no one-to-one cardinality is
assumed.

## 7. Consumer and Professional modes

There is one backend and one domain model. Both modes use Identity, Property Graph,
Evidence, Case, Valuation, Market, Risk, Finance, Tax, AI and Artifact services.

| Concern | Consumer | Professional |
| --- | --- | --- |
| Primary job | Decide whether a home deserves further investigation | Research a land/building/site/case and produce accountable work |
| Entry | Existing guided property journey | A selected workspace, property and case |
| Navigation | Progressive decision steps | Permission-gated modules |
| Density | Summary first | Evidence-dense, multi-panel |
| Case purpose | Usually `buy_due_diligence` | Any supported professional purpose |
| Permissions | Personal-workspace defaults | Team role and assignment aware |

Professional navigation may later expose Property, Parcel, Building, GIS, Planning,
Redevelopment, Market, Listings, Title, Risk, Valuation, Finance, Tax, CRM, Team and AI.
This changes visibility and density, not domain truth. The consumer homepage remains a
decision journey rather than a tool catalog.

The future Professional Workspace contains a Context Header, Map Canvas, Evidence Rail,
Task Panel, Module Detail, Copilot and Activity Timeline. Every module must show the active
Workspace, Property, Case, evidence freshness and next investigation step. It is a coherent
property/case-centered workflow shell, not an unrelated list of tools.

## 8. Feature gates

Feature gates are evaluated server-side for protected capabilities and mirrored client-side
only for presentation. Unknown flags are off. Demo/test providers require a separate
non-production runtime mode and can never satisfy a production gate.

| Flag | Stage owner | Default | Minimum enablement evidence |
| --- | --- | --- | --- |
| `identity_v1` | Stage 1 | off | state/contract/tenant/security tests and human confirmation UX |
| `professional_workspace` | Stage 8 | off | roles, tenant E2E, accessibility and workflow acceptance |
| `parcel_workspace` | Stage 2 | off | authorized source, CRS/coverage and geometry acceptance |
| `building_intelligence` | Stage 3 | off | building source license/identity contract |
| `planning_intelligence` | Stage 3 | off | jurisdiction, effective-date and source coverage |
| `listing_intelligence` | Stage 4 | off | partner authorization and relist semantics |
| `document_intelligence` | Stage 5/7 | off | private storage, malware/privacy review and human approval |
| `crm` | Stage 6 | off | role model, contact consent and audit acceptance |
| `ai_synthesis` | Stage 7 | off | evidence-only grounding and approval/audit controls |

## 9. Database and migration strategy

### Namespace

- Keep existing `public` and `compact_green` semantics unchanged.
- Put VNext tenant/domain tables in `vnext_core`, private facts/documents in
  `vnext_private`, and extensions in an `extensions` schema where supported.
- Do not expose those schemas through the Supabase Data API during Stage 1.
- If direct Data API access is later approved, create a narrowly exposed `api_v1` schema
  with reviewed security-invoker projections/RPCs. Do not expose base tables by default.

### Ordering and compatibility

1. Freeze and document the exact current migration registry/checksums.
2. Resolve the duplicate `002` naming and the separate `011` operational path before
   assigning the first VNext migration number. Do not rename already-applied files.
3. Allocate a non-colliding monotonic number and create it through the selected migration
   tool; Stage 0 creates no migration.
4. Deploy schema and RLS in a transaction to a disposable/preview database first.
5. Grant the application role only the statements it needs; no frontend grants.
6. Add nullable compatibility references before any backfill. Backfills are separate,
   restartable, observable jobs, never migration-time rewrites of legacy rows.
7. Leave PLVR, valuation history, market, pilot evidence and TaxOracle history untouched.

Migrations are forward-only and additive. Recovery uses a verified provider checkpoint and
application rollback; a guessed destructive down migration is not the primary recovery path.
Every production apply requires backup identity, checksum-ledger review, RLS/tenant tests,
index review, readiness verification and a restore rehearsal appropriate to the change.

### PostGIS

PostGIS is introduced in a dedicated additive migration only after the managed provider and
extension schema are approved. Add new `geometry/geography` columns or VNext spatial tables;
do not reinterpret existing latitude/longitude or compact PLVR columns. Normalize external
CRS at ingestion, preserve original CRS in evidence, use EPSG:4326 for interchange, use an
appropriate projected CRS for area/distance, and add GiST indexes after representative query
plans are reviewed.

## 10. Testing architecture

| Layer | Required coverage |
| --- | --- |
| Unit | normalization, state transitions, relation rules, status/freshness and unknown preservation |
| Contract | provider request/result, DTO/OpenAPI compatibility, error and idempotency behavior |
| Database | clean and upgrade migration, FKs/checks/indexes, RLS, cross-tenant isolation, PostGIS plans |
| Security | BOLA/IDOR, role escalation, membership revocation, signed URL scope, service-role leakage |
| Integration | provider -> evidence -> candidate without fake success; audit and activity append |
| E2E | input -> candidates -> explicit confirmation -> case -> evidence, under personal and team tenants |
| Provider | fixture contract tests separated from credentialed real-provider acceptance |

Fixture success proves adapter shape only. Production enablement requires a separately recorded
real-provider acceptance with coverage, license, freshness and failure-path evidence.

## 11. Current conflicts and minimum-change decisions

| Current architecture | Problem | Options | Recommended decision | Migration impact |
| --- | --- | --- | --- | --- |
| Browser `SavedCase` combines property facts and a decision snapshot | It is not durable identity or evidence | Replace it, mutate it, or adapt it | Keep v1 unchanged; optional import adapter creates an unverified durable Case | No current data rewrite |
| Current custom pilot sessions; no Supabase Auth in runtime | VNext needs one canonical workspace principal without replacing the existing FastAPI BFF | Supabase Auth, another IdP, or custom application principals | **Selected:** Supabase Auth; `workspace_members.user_id -> auth.users.id`; FastAPI validates the principal and remains the shared Consumer/Professional BFF | Additive Auth/membership integration later; no Stage 0 runtime change |
| Existing server tables mostly in `public`; RLS is inconsistent | Accidental Data API exposure could bypass application assumptions | Retrofit all now or isolate VNext | Keep current server-only; put VNext in private schemas and deny grants | No Stage 0 migration |
| Current terrain overall level can reach downstream summaries | Unknown-to-safe behavior is not proven impossible | Ignore, rewrite terrain now, or gate signoff | Record as critical pre-existing trust blocker; repair in its approved stage | No Stage 0 behavior change |
| Migration numbering includes duplicate `002`; runner covers `004`-`010`, while `011` has a separate runbook | A naive glob/order policy is unsafe | Rename history or freeze and allocate | Never rename applied files; publish one authoritative registry before VNext DDL | Documentation/owner action first |
| Some older docs describe valuation demo fallback while current trust contract fails closed | Documentation can overstate current behavior | Follow old docs or current code/trust contract | Current code and active fail-closed contract govern; stale setup guidance needs separate cleanup | No semantic change |

## 12. Stage boundaries

- Stage 1: identity resolution contracts and a gated, confirmable implementation.
- Stage 2: parcel/GIS and authorized geometry.
- Stage 3: building/planning/redevelopment.
- Stage 4: market/listing relations; no scraping without authorization.
- Stage 5: title partner and private document controls.
- Stage 6: CRM/team workflows and contact consent.
- Stage 7: evidence-grounded AI synthesis.
- Stage 8: Professional Workspace UI.

No work beyond this Stage 0 contract is authorized by this document.
