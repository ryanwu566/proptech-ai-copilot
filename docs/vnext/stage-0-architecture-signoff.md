# Stage 0 Architecture Signoff

Date: 2026-08-28
Scope: VNext architecture blocker closure only
Production behavior change: **NONE**

## Current result

```text
Stage 0 Architecture Result: NO-GO
Stage 1 Authorization: BLOCKED
```

Authentication and workspace-principal architecture is decided. Terrain safety is a named
external pre-Stage-1 gate rather than an undecided architecture question. The remaining
architecture blocker is the required primary input
`docs/itaiwan-proptech-deep-workflow-audit-v1.md`: it is not present in the supplied attachment,
working tree, Git history or local refs, so reconciliation cannot truthfully be signed off.

No archive document was substituted, no missing audit was reconstructed from the Stage 0
prompt, and no Stage 1 implementation was started.

## Architecture blockers

1. The complete iTaiwan PropTech deep workflow audit must be supplied at
   `docs/itaiwan-proptech-deep-workflow-audit-v1.md` and reconciled against `docs/vnext/*`.

This section becomes `NONE` only after that primary input is present and reviewed.

## External pre-Stage-1 gates

1. Supabase Security Hotfix on `security/supabase-rls-hotfix` must be `GO`.
2. Terrain Unknown Safety Gate on `safety/terrain-unknown-gate` must be `GO`.

These gates block Stage 1 authorization, but neither is an unresolved Stage 0 architecture
decision.

## Authentication and workspace-principal decision

- VNext uses **Supabase Auth** as the authentication source.
- Canonical user identifier is `auth.users.id` UUID.
- `workspace_members.user_id` references `auth.users.id`.
- FastAPI remains the shared application API/BFF for Consumer and Professional modes; there
  is one domain backend.
- Workspace-owned resources require `workspace_id + active membership + role` authorization.
- Conceptual roles are `owner`, `admin`, `manager`, `member` and `viewer`.
- Every future browser-exposed tenant table must enable RLS. `TO authenticated` is not enough;
  policies must verify `auth.uid()` and an active workspace membership, with role/resource
  checks for mutations and sensitive reads.
- Documents, contacts, ownership/title data and private CRM notes are private/server-mediated
  by default.
- `service_role` is restricted to operator jobs, migrations, trusted background jobs,
  privileged administrative tasks and necessary private Storage operations. It is forbidden
  in browsers, `NEXT_PUBLIC_*`, general user-facing requests and authorization bypasses.
- Documents, title and report artifacts use private buckets and short-lived signed URLs or a
  more restrictive server stream; public buckets are forbidden.

This is an architecture decision only. No Auth integration, live Supabase schema, RLS policy,
security migration or Storage configuration is changed on this branch.

## Terrain safety transfer

```text
Terrain unknown/unavailable can currently coexist with an overall green decision signal.
```

Remediation and acceptance evidence belong to `safety/terrain-unknown-gate` and are a:

```text
REQUIRED PRE-STAGE-1 SAFETY GATE
```

This branch does not modify `frontend_next/lib/risk-summary.ts`,
`frontend_next/lib/terrain-reference-evidence.ts`, terrain scoring, production behavior or
provider semantics.

## Architecture decisions

1. `PropertyEntity` is a workspace-scoped application aggregate, not a Case or claimed
   government identifier.
2. A Case has its own identity and lifecycle, may remain unverified and may optionally attach
   to a confirmed PropertyEntity.
3. Resolution is normalized input -> provider Evidence -> candidates/conflicts -> explicit
   attributable human confirmation.
4. Address, parcel, building, listing and coordinate observations use typed many-to-many
   temporal relations with source, confidence and validity intervals.
5. Merge/split is proposed, evidence-reviewed, human-confirmed and non-destructive; history
   and Evidence remain durable.
6. Evidence is immutable/versioned and includes source, retrieval/effective time, coverage,
   status, quality, license and lineage. Unknown is never safe/zero/none.
7. Provider failure stays unavailable/partial; demo/test results cannot become production
   Evidence.
8. Personal and team workspaces share one tenant model and the Supabase Auth principal
   contract above.
9. FastAPI is the shared Consumer/Professional BFF; mode changes presentation, density,
   permission and case purpose, not domain truth.
10. Professional Workspace is a property/case-centered workflow shell with Context Header,
    Map Canvas, Evidence Rail, Task Panel, Module Detail, Copilot and Activity Timeline. It is
    not an unrelated tool list.
11. Future exposed tenant tables are deny-by-default with Auth/RLS/GRANT acceptance; sensitive
    base data stays private.
12. Private documents/title/contact data use private Storage, short authorized delivery and
    append-only access audit.
13. AI can read/cite Evidence and deterministic results to draft synthesis. It cannot modify
    identity, authoritative facts, calculations or execute consequential actions.
14. Listing and title capabilities stay disabled until an exact authorized/licensed source or
    partner, permitted uses, retention and real-provider acceptance are approved.
15. SavedCase v1 and `proptech.savedCases.v1` remain untouched. Optional future import creates
    a `legacy_unverified` Case without asserting a confirmed Property.
16. VNext migrations are additive, private-schema-first and forward-only; existing PLVR,
    valuation, market, pilot and TaxOracle semantics remain unchanged.

## Architecture review

| # | Review question | Current answer | Evidence / gate |
| --- | --- | --- | --- |
| 1 | Are PropertyEntity and Case separated? | Yes | Separate responsibilities, IDs, lifecycles and optional attachment. |
| 2 | Do Address/Parcel/Building avoid one-to-one assumptions? | Yes | Typed many-to-many temporal relations. |
| 3 | Does resolution require candidates and confirmation? | Yes | Confirmation requires an immutable candidate and human actor. |
| 4 | Is automatic destructive merge forbidden? | Yes | Similarity, provider, AI and legacy input cannot trigger it. |
| 5 | Is Evidence durable and attributable? | Yes | Required source/time/coverage/status/quality/license/lineage and immutable history. |
| 6 | Can unknown become safe? | No under the VNext contract; runtime gate open | Existing terrain behavior is explicitly transferred to the external safety branch. |
| 7 | Can AI modify authoritative facts? | No | Read/cite/draft only. |
| 8 | Is workspace tenancy/principal clear? | Yes | Supabase Auth `auth.users.id`, membership, role, FastAPI and RLS boundaries are fixed. |
| 9 | Can browser code arbitrarily read sensitive data? | No | Server-mediated private tables/buckets and short authorized delivery. |
| 10 | Does legacy SavedCase continue to work? | Yes | No code/storage change; optional future copy-only import. |
| 11 | Is Consumer behavior unchanged? | Yes | Documentation-only closure. |
| 12 | Are PLVR/valuation/tax/terrain semantics unchanged? | Yes | No service/schema/data/UI changes. |
| 13 | Is the supplied audit reconciled? | **No - Critical** | The required audit file was not supplied. |
| 14 | May Stage 1 start? | **No** | Audit reconciliation and both external gates must be complete. |

## Current architecture conflicts resolved by contract

| Current architecture | Problem | Selected decision | Migration impact |
| --- | --- | --- | --- |
| SavedCase is a browser decision snapshot | It cannot be canonical durable identity | Preserve v1; optional `legacy_unverified` import | none now; additive future rows |
| Runtime has custom pilot sessions and no Supabase Auth | VNext requires one stable workspace principal | Supabase Auth; `workspace_members.user_id -> auth.users.id`; shared FastAPI BFF | additive future Auth/membership work |
| Legacy `public` RLS/grants are inconsistent | Data API exposure would violate tenant assumptions | no new exposure; deny-by-default VNext schemas and reviewed projections | owned by the security hotfix/future migrations |
| Terrain level reaches risk summary | Unknown can coexist with a green signal | external safety gate on `safety/terrain-unknown-gate` | no change on this branch |
| Migration numbering/registration differs across paths | Naive glob/checksum ordering is unsafe | do not rename applied files; freeze a registry before VNext DDL | documentation/owner action before DDL |

## Validation

Closure validation is recorded after all documentation inputs are present. Until the missing
audit is supplied, the final closure rerun is:

| Check | Result | Classification |
| --- | --- | --- |
| Frontend typecheck | NOT RUN | Final closure rerun pending |
| Frontend lint | NOT RUN | Final closure rerun pending |
| Frontend production build | NOT RUN | Final closure rerun pending |
| Backend tests | NOT RUN | Final closure rerun pending |

An earlier Stage 0 run reported `1 failed, 1417 passed, 5 skipped` because
`psycopg_pool` could not be imported. The isolated test now passes and the package is currently
installed, so the earlier result is **UNVERIFIED PRE-EXISTING**, not `PASS` and not yet a
reproducible baseline classification. No dependency file was changed by this documentation
work.

## Changed documentation

- `docs/vnext/architecture-overview-v1.md`
- `docs/vnext/property-identity-architecture-v1.md`
- `docs/vnext/workspace-security-architecture-v1.md`
- `docs/vnext/api-contract-v1.md`
- `docs/vnext/stage-0-architecture-signoff.md`

No frontend, backend, service, provider, migration, environment, feature-flag or production
configuration file is changed by this closure work.

## Deferred implementation

| Stage | Explicitly deferred work |
| --- | --- |
| Stage 1 Property Identity | gated resolver, candidates UI/API, confirmation persistence, graph schema |
| Stage 2 Parcel / GIS | authorized parcel source, PostGIS, cadastral workspace, coverage acceptance |
| Stage 3 Building / Planning | building source/identity and temporal planning intelligence |
| Stage 4 Market / Listings | licensed listing partner and relist relations |
| Stage 5 Title | partner/procurement and private legal document controls |
| Stage 6 CRM | contacts, activities, assignment, consent and audit |
| Stage 7 AI | Evidence-grounded synthesis and approval controls |
| Stage 8 Professional Workspace | workflow shell UI |

## Stage 1 authorization

> **Do not enter Stage 1.**

Stage 1 remains blocked until the audit is supplied/reconciled and both named external
security/safety gates are `GO`. At that point this signoff must be updated, validation rerun,
committed and pushed before Stage 1 can be authorized.
