# Stage 0 Architecture Signoff

Date: 2026-08-28  
Scope: VNext architecture preparation only  
Production behavior change: **NONE**

## Stage 0 Result

```text
Stage 0 Result: NO-GO
Stage 1 Readiness: NOT READY
```

The required architecture package is defined, but the gate cannot pass because a mandatory
primary input (`docs/itaiwan-proptech-deep-workflow-audit-v1.md`) is absent and therefore was
not reconciled. In addition, the active terrain audit records a critical unresolved false-safety
boundary: terrain overall level reaches downstream risk-summary behavior and the repository
does not yet prove unknown can never be interpreted as safe. Authentication/principal mapping
for durable workspace RLS is also an owner decision required before Stage 1 persistence.

No archive document was substituted, no critical question was marked passed without evidence,
and no Stage 1 implementation was started.

## Created

- `docs/vnext/architecture-overview-v1.md`
- `docs/vnext/property-identity-architecture-v1.md`
- `docs/vnext/evidence-architecture-v1.md`
- `docs/vnext/workspace-security-architecture-v1.md`
- `docs/vnext/data-source-registry-v1.md`
- `docs/vnext/api-contract-v1.md`
- `docs/vnext/legacy-case-migration-v1.md`
- `docs/vnext/stage-0-architecture-signoff.md`

## Changed

- `docs/README.md` — adds the VNext Stage 0 package to the active index.

No frontend, backend, service, provider, migration, environment, feature-flag or production
configuration file was changed by Stage 0.

## Production Behavior Changes

```text
NONE
```

The package consists only of documentation contracts. It does not add `/v1` routes, schema,
RLS, Auth, Storage, PostGIS, external calls, resolver behavior, UI or feature enablement.

## Architecture decisions (15)

1. PropertyEntity is a workspace-scoped application aggregate, not a claimed government ID.
2. PropertyEntity and Case have separate identities/lifecycles; a Case may exist unverified and
   a Property may serve many cases.
3. Identity always follows normalized input -> provider evidence -> candidates/conflicts ->
   explicit human confirmation; no automatic destructive merge.
4. Address, parcel, building, listing and coordinates are many-to-many temporal graph nodes,
   never generic one-to-one identifiers.
5. Merge/split preserves both entities, evidence and temporal edges; approved link migration is
   a separate audited step.
6. Evidence is immutable/versioned and always carries source, time, coverage, status, quality
   and lineage. Unknown is never safe/zero/none.
7. Provider failure remains unavailable/partial with safe errors; demo/test providers cannot
   become production evidence.
8. Personal and team workspaces share one tenant model with role/status membership; all
   durable domain rows are workspace-scoped.
9. VNext base/private schemas are server-only and deny-by-default. Any future Data API surface
   is a separate reviewed `api_v1` projection after Auth/RLS/GRANT acceptance.
10. `service_role`/secret keys stay in trusted server/operator paths and never replace resource
    authorization or enter the browser.
11. Private documents/title/contact data use private Storage, short authorized delivery and
    append-only access audit; no public title/contact tables.
12. AI reads/cites Evidence and deterministic results to draft synthesis; it cannot mutate
    identity, facts, calculations or perform consequential actions.
13. Consumer and Professional modes share backend/domain truth and differ only in navigation,
    visibility, density, permission and case purpose.
14. SavedCase v1 and `proptech.savedCases.v1` remain untouched. Optional import creates a
    durable `legacy_unverified` Case without a confirmed Property.
15. VNext migrations are additive, private-schema-first and forward-only with backup/restore;
    existing PLVR, valuation, market, pilot and TaxOracle semantics/rows remain untouched.

## Architecture review questions

| # | Review question | Answer | Evidence / gate |
| --- | --- | --- | --- |
| 1 | Are PropertyEntity and Case clearly separated? | Yes, contractually | Separate responsibilities, IDs, lifecycles and optional attachment are defined. No implementation exists yet. |
| 2 | Do Address/Parcel/Building avoid one-to-one assumptions? | Yes | Typed graph nodes and many-to-many temporal relations; no generic uniqueness/cardinality constraint. |
| 3 | Does resolution require candidates and confirmation? | Yes | No direct confirmed transition from input; confirm command requires selected immutable candidate and human actor. |
| 4 | Is there any automatic destructive merge? | No in the VNext contract | Similarity/provider/AI/legacy input are expressly forbidden triggers. Current product has no canonical merge feature. |
| 5 | Does Evidence include source/time/coverage/status? | Yes | DTO also requires quality, license and lineage. |
| 6 | Can unknown still become safe? | **Not proven — Critical NO** | VNext contract forbids it, but the active terrain audit says the existing overall level reaches `risk-summary` and false-safety closure is incomplete. Stage 0 intentionally did not change behavior. |
| 7 | Can AI modify authoritative facts? | No under the VNext contract | AI has read/cite/draft permissions only; no authoritative write path is defined. |
| 8 | Is the Workspace tenant boundary clear? | Yes in architecture; not implemented | `workspace_id`, membership roles/status, server checks and RLS are defined. Auth principal choice remains open. |
| 9 | Can frontend read sensitive documents/contacts arbitrarily? | No under the VNext contract | Private schema/bucket, assignment/purpose checks, short delivery and access audit; no public tables. Not implemented. |
| 10 | Does legacy SavedCase continue to work? | Yes | No code/storage change. Optional adapter is copy-only and future-gated. |
| 11 | Is Consumer journey behavior unchanged? | Yes | Documentation-only Stage 0; no homepage/navigation/UI edits. |
| 12 | Are PLVR/valuation/tax/terrain semantics unchanged? | Yes | No service/schema/data/UI changes. The pre-existing terrain trust gap is recorded, not silently redefined. |
| 13 | Can Stage 1 safely start now? | **No** | Missing mandatory audit, unresolved false-safety evidence and Auth/workspace principal decision block the gate. |

Because questions 6 and 13 are critical and not compliant, the required result is `NO-GO`.

## Current architecture conflicts resolved by contract

| Current architecture | Problem | Options | Recommended decision | Migration impact |
| --- | --- | --- | --- | --- |
| SavedCase is browser decision snapshot | Cannot be canonical durable identity | replace, mutate, or adapt | preserve v1; optional explicit import as `legacy_unverified` | none now; additive future Case/evidence rows |
| No Supabase Auth/Data API; custom pilot sessions | No generic workspace principal for RLS | Supabase Auth, other IdP mapping, server-only principal | owner selects one stable principal; membership table is source of truth | additive Auth mapping/RLS after decision |
| Legacy `public` RLS/grants are inconsistent | Data API exposure would violate assumptions | retrofit all legacy or isolate VNext | no new exposure; private `vnext_core/vnext_private` plus optional future `api_v1` | additive schemas only |
| Terrain level reaches risk summary | False-safety boundary not proven closed | ignore, repair now, or gate | gate Stage 1 and repair through approved trust-boundary work | no Stage 0 semantic change |
| Migration numbering/registration differs across paths | Glob ordering/checksum mistakes are possible | rename history or freeze registry | do not rename applied files; approve one registry and new range | documentation/owner action before VNext DDL |

## Validation

Validation commands were run after the documentation package was created. The first raw
backend invocation inherited external database target variables and an inaccessible Windows
temp root; its failures were discarded as non-hermetic. The recorded backend result is the
retry with those targets cleared and a unique workspace-local `--basetemp`.

| Check | Command | Result | Classification |
| --- | --- | --- | --- |
| Frontend typecheck | `npm.cmd --prefix frontend_next run typecheck` | PASS | No TypeScript errors |
| Frontend lint | `npm.cmd --prefix frontend_next run lint` | PASS with 27 warnings | Pre-existing unused-symbol warnings in existing frontend files; 0 errors; documentation is outside lint graph |
| Frontend production build | `npm.cmd --prefix frontend_next run build` | PASS | Next.js optimized build and static generation completed |
| Backend tests | database/provider target variables cleared; `python -m pytest --basetemp=<workspace-local-unique-dir>` | **FAIL: 1 failed, 1417 passed, 5 skipped** | Pre-existing environment/dependency gap: `psycopg_pool` is not installed, so `test_concurrent_init_one_pool` cannot monkeypatch/import it; `backend/requirements.txt` declares `psycopg[binary,pool]` |

Stage 0 documentation changes do not enter the frontend/backend compilation graph. No
dependency was installed and the missing-pool failure is not claimed as passed. The repository
also had unrelated frontend edits and generated browser artifacts before this work; none was
modified intentionally by Stage 0.

## Deferred

| Stage | Explicitly deferred work |
| --- | --- |
| Stage 1 Property Identity | gated resolver, normalization implementation, candidates UI/API, confirmation persistence, graph schema |
| Stage 2 Parcel / GIS | authorized NLSC/other parcel source, PostGIS, cadastral map/workspace, coverage acceptance |
| Stage 3 Building / Planning | building source/identity, planning and renewal effective-date intelligence |
| Stage 4 Market / Listings | listing partner, relist relations, licensed cross-source listing intelligence; existing PLVR semantics unchanged |
| Stage 5 Title | partner/procurement, private title storage/delivery and legal/consent controls |
| Stage 6 CRM | contacts, activities, team assignment, consent and CRM audit |
| Stage 7 AI | evidence-grounded synthesis, report drafts, approval controls; no production LLM now |
| Stage 8 Professional Workspace | Context Header, Map Canvas, Evidence Rail, Task Panel, Module Detail, Copilot and Timeline UI |

## Blocking owner actions

1. Supply `docs/itaiwan-proptech-deep-workflow-audit-v1.md`; review it fully and reconcile
   conflicts into these contracts.
2. Approve remediation/acceptance evidence proving terrain unknown/unavailable/no-match cannot
   become a positive/safe downstream conclusion.
3. Decide authentication and authenticated principal mapping (Supabase Auth, another IdP, or
   server-only equivalent) for workspace membership/RLS.
4. Decide managed Supabase/Postgres topology, exposed schemas/Data API posture, backups and
   PostGIS availability.
5. Freeze one authoritative production migration registry/next number, including the separate
   `011` compact-green operational path and duplicate historical `002` names.
6. Complete TGOS terms/configuration/quota and real-provider acceptance if used in Stage 1.
7. Complete NLSC dataset/endpoint/authorization/license decision before parcel/GIS work.
8. Record PLVR license/attribution approval for any new VNext evidence purpose.
9. Select listing and title partners before those capabilities are designed as live features.
10. Approve private Storage, document/contact retention, signed access and audit policy.

## Stage 1 readiness

> **Do not enter Stage 1 yet.**

After owner actions 1-5 are closed, update this signoff, re-answer all 13 questions, rerun the
validation matrix and require every Critical answer to comply. A revised `GO` or
`CONDITIONAL GO` is required before any identity resolver, VNext migration, `/v1` behavior or
UI is implemented.
