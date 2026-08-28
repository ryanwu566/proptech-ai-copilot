# Stage 0 Architecture Signoff

Date: 2026-08-28
Scope: VNext architecture blocker closure only
Production behavior change: **NONE**

## Current result

```text
Stage 0 Architecture Result: GO
Supabase Security Gate: GO / CLOSED
Terrain Unknown Safety Gate: PENDING
Stage 1 Authorization: BLOCKED
```

The complete `docs/itaiwan-proptech-deep-workflow-audit-v1.md` was supplied, copied byte-for-byte
and reconciled against every Stage 0 VNext contract. It introduces no architecture
contradiction. Authentication/workspace-principal architecture is decided. Supabase production
security is closed. Terrain safety is the sole remaining external pre-Stage-1 gate rather than
an unresolved architecture question.

No archive document or shortened substitute was used, and no Stage 1 implementation was
started.

## Architecture blockers

```text
NONE
```

## External pre-Stage-1 gate status

| Gate | Status | Stage 1 effect |
| --- | --- | --- |
| Supabase Security Hotfix | **GO / CLOSED** | Completed by the secured-main remediation and operator live verification; no longer blocks Stage 1. |
| Terrain Unknown Safety Gate on `safety/terrain-unknown-gate` | **PENDING** | `REQUIRED PRE-STAGE-1 SAFETY GATE`; the only remaining authorization blocker. |

The pending terrain gate blocks Stage 1 authorization, but it is not an unresolved Stage 0
architecture decision.

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

This is an architecture decision only. This reconciliation introduces no Auth integration,
live Supabase schema operation, new RLS policy or Storage configuration. The secured-main
security migration is integrated unchanged and is not applied to a live Supabase project here.

## Security architecture reconciliation

```text
Security architecture reconciliation: PASS
```

Migration `012_security_rls_deny_by_default.sql` establishes the current interim posture for
legacy `public` tables: RLS enabled, no permissive Data API policy, and direct
`anon`/`authenticated` table privileges revoked while the trusted backend-owner path remains
available. That deny-default baseline is intentionally not the final VNext authorization
model.

The final VNext contract remains Supabase Auth `auth.users.id`, active workspace membership,
role and resource checks, membership-aware RLS for every exposed tenant table, a non-owner
normal application role, private sensitive data and Storage, and a tightly bounded
`service_role`. The secured-main remediation explicitly defers those ownership policies to the
VNext workspace architecture, so the two documents are consistent rather than competing
security models.

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

## Competitive workflow audit reconciliation

Source: `docs/itaiwan-proptech-deep-workflow-audit-v1.md`

Source/copy SHA-256: `E3AA1F8C0C0DF06114372A4B8A3E2763F0BB7F898BFDDA760FAE8C9F78E29409`

| Audit direction | Reconciliation result | Contract evidence |
| --- | --- | --- |
| `PropertyEntity != Case` | Aligned | Separate IDs, lifecycles, purposes and optional confirmed attachment. |
| Candidate-based resolution | Aligned | Normalization -> provider Evidence -> candidates/conflicts -> confirmation. |
| Human confirmation for ambiguity | Aligned | `ambiguous` blocks title/CRM/merge; confirmation requires selected candidate and actor. |
| Address/parcel/building/listing cardinality | Aligned | Typed many-to-many graph; no generic one-to-one constraint. |
| Typed temporal relations | Aligned | Relation type/source/confidence/evidence plus `valid_from`/`valid_to` and supersession. |
| Durable Evidence/provenance | Aligned | Immutable versions with source, time, coverage, status, quality, license and lineage. |
| Consumer + Professional backend | Aligned | Shared FastAPI BFF, domain services and tenant model; presentation and permissions differ. |
| Task-oriented Professional Workspace | Aligned | Context Header, Map Canvas, Evidence Rail, Task Panel, Module Detail, Copilot and Timeline; not a tool list. |
| AI authority boundary | Aligned | AI reads/cites/drafts only and cannot mutate identity, Evidence or authoritative facts. |
| Deterministic intelligence | Aligned | Valuation, finance, tax and risk calculations remain authoritative/versioned inputs to synthesis. |
| Listing acquisition | Aligned | Partner/allowlist/license gate; no unlicensed scraping or cross-brand aggregation. |
| Direct title procurement | Aligned | Partner/legal/privacy/consent/cost/audit gate; private artifacts only. |
| Unknown/unavailable | Aligned | Explicit Evidence states; never rewritten as safe, zero, none, complete or available. |

No genuine inconsistency required rewriting the existing identity, Evidence, security, API or
legacy migration contracts. Only stale references to the previously missing audit and this
signoff/index were corrected.

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
| 13 | Is the supplied audit reconciled? | Yes | Full audit copied with matching hash; all thirteen named architecture directions align. |
| 14 | May Stage 1 start? | **No** | The terrain safety gate must reach `GO`; the Supabase gate is closed and architecture itself is ready. |

## Current architecture conflicts resolved by contract

| Current architecture | Problem | Selected decision | Migration impact |
| --- | --- | --- | --- |
| SavedCase is a browser decision snapshot | It cannot be canonical durable identity | Preserve v1; optional `legacy_unverified` import | none now; additive future rows |
| Runtime has custom pilot sessions and no Supabase Auth | VNext requires one stable workspace principal | Supabase Auth; `workspace_members.user_id -> auth.users.id`; shared FastAPI BFF | additive future Auth/membership work |
| Legacy `public` RLS/grants were inconsistent | Data API exposure would violate tenant assumptions | secured-main deny-default baseline now; future exposed VNext resources still require membership-aware RLS | hotfix closed; additive VNext authorization work remains deferred |
| Terrain level reaches risk summary | Unknown can coexist with a green signal | external safety gate on `safety/terrain-unknown-gate` | no change on this branch |
| Migration numbering/registration differs across paths | Naive glob/checksum ordering is unsafe | do not rename applied files; freeze a registry before VNext DDL | documentation/owner action before DDL |

## Validation

Final combined validation was run after the complete audit reconciliation and the normal
merge of secured `main` into `vnext-stage-0`:

| Check | Result | Classification |
| --- | --- | --- |
| Frontend typecheck | **PASS** | `tsc --noEmit`; no errors |
| Frontend lint | **PASS with 27 warnings** | 0 errors; existing unused-symbol/argument warnings in frontend source |
| Frontend production build | **PASS** | Next.js 16.2.12 optimized build, TypeScript, page data and static generation completed |
| Backend tests | **PASS: 1417 passed, 5 skipped, 1 warning** | Hermetic run with external database/provider targets cleared; 5 isolated Postgres checks skipped because targets were not configured; existing FastAPI/Starlette `httpx` deprecation warning |
| Migration static validation | **PASS** | `static_contract_pass`; database application intentionally not run |
| Migration dry-run | **PASS / READY** | 8 registered migrations; no database connection or live mutation |
| Migration 012 registration | **PASS** | File exists exactly once and is registered exactly once as migration 8 of 8 |
| Protected scope | **PASS** | Migration 012 and both terrain files have the same blobs as secured `main` |

An earlier Stage 0 run reported `1 failed, 1417 passed, 5 skipped` because
`psycopg_pool` could not be imported. The isolated test now passes and the package is currently
installed, so that historical result remains **UNVERIFIED PRE-EXISTING** and is not
retroactively claimed as proven. The current full run is the result reported above.

The dedicated worktree initially lacked `node_modules`: the first typecheck could not start and
17 Node-backed Python tests could not import TypeScript. `npm ci` installed 217 packages from
the committed lockfile with 0 reported vulnerabilities; it changed no dependency manifest or
lockfile. A subsequent backend attempt inherited `PLVR_DRY_RUN_DATABASE_URL` for an unavailable
local target at `127.0.0.1:55432`, causing 2 connection timeouts. The recorded final run cleared
that external target so those tests followed their declared skip contract. These setup attempts
are not hidden or counted as final application failures.

On the combined rerun, the first typecheck attempt was unable to write
`frontend_next/tsconfig.tsbuildinfo` because the dedicated worktree was outside the restricted
command sandbox (`EPERM`). It was rerun with worktree write permission and passed; this was a
runner setup failure, not a TypeScript failure. Final failed checks: **none**. Live Supabase
application and disposable-database transactional application were **not run** by design; only
the requested static validator and migration dry-run were executed.

No dependency file was changed by this documentation work.

## Changed documentation

- `docs/itaiwan-proptech-deep-workflow-audit-v1.md`
- `docs/README.md`
- `docs/vnext/api-contract-v1.md`
- `docs/vnext/architecture-overview-v1.md`
- `docs/vnext/data-source-registry-v1.md`
- `docs/vnext/evidence-architecture-v1.md`
- `docs/vnext/legacy-case-migration-v1.md`
- `docs/vnext/property-identity-architecture-v1.md`
- `docs/vnext/stage-0-architecture-signoff.md`
- `docs/vnext/workspace-security-architecture-v1.md`

The reconciliation commit changes documentation only. The synchronized branch also contains
the secured-main security files unchanged; this closure does not modify frontend, backend,
service, provider, migration, environment, feature-flag or production configuration behavior.

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

Stage 0 architecture is ready and the Supabase Security Gate is `GO / CLOSED`. Stage 1 remains
blocked only until the Terrain Unknown Safety Gate is `GO` and its acceptance is recorded.
