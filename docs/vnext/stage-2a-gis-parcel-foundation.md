# Stage 2A GIS / Parcel Foundation

Status: Slice 1 durable spatial persistence; development migration only, with no production
provider, live migration, API route, feature enablement, or map UI

## 1. Purpose

Stage 2A establishes the spatial language needed to ask what a parcel or map layer says about
a property without turning proximity, geometry, or provider output into legal identity or a
safety claim. It supports parcel investigation, map context, evidence review, and durable Case
continuity for the Taiwan Property Decision Intelligence Workspace.

The Slice 0 implementation is deliberately pure:

- immutable Python domain contracts in `services/vnext/spatial.py`;
- explicit CRS transformation through the already-installed `pyproj` library;
- bounded geometry predicates through the already-installed `Shapely` library;
- provider-neutral protocols and result normalization;
- direct adaptation into Stage 1 `EvidenceDraft` and `PropertyRelationDraft` contracts;
- deterministic, conspicuously synthetic fixtures and unit tests.

Slice 1 adds a development-only PostgreSQL persistence boundary and migration 018. It makes no
network/provider call and has not been applied to a hosted or production database.

## 2. Relationship to Stage 1

Stage 1 remains the source of truth for tenant scope, confirmable property identity, graph
nodes, evidence, human decisions, Cases, and Case/property links. Stage 2A does not introduce
a second parcel identity or provenance system.

| Stage 1 concept | Stage 2A use |
| --- | --- |
| `PropertyEntity` | The application property aggregate selected in Map Workspace; geometry does not replace it |
| `IdentityReferenceType.PARCEL` | The parcel identity node referenced by `ParcelGeometry.parcel_identity_reference_id` |
| `IdentityReferenceType.GEO_REFERENCE` | A point/location observation; never silently promoted to a parcel boundary |
| `PropertyRelationDraft` | Spatially supported property/parcel or parcel/building edges remain proposals |
| `IdentityDecisionRecord` | Existing explicit human confirmation remains the only identity confirmation path |
| `EvidenceDraft` | Spatial observations adapt into the existing immutable evidence framework |
| `CaseRecord` | Map Workspace is Case-scoped and may exist before a property or parcel is confirmed |
| `CasePropertyLinkRecord` | Unchanged; spatial resolution never attaches a Case automatically |

Confidence, exact overlap, containment, distance, nearest-neighbor rank, and provider authority
may support review. None of them confirms a property/parcel relationship or merges graph
nodes. `proposed_property_parcel_relation()` always returns `status=proposed`, including when
confidence is `1.0`.

### Slice 1 persisted model

Migration `018_add_vnext_spatial_foundation` adds three narrowly scoped objects without
altering the Stage 1 tables:

- `vnext_core.parcel_geometry_versions` is tenant-owned, immutable geometry history linked by
  a composite workspace foreign key to the existing parcel identity reference, Stage 1
  Evidence, and Stage 1 idempotency record.
- `vnext_core.spatial_layers` is global system metadata. A layer is versioned rather than
  edited, carries no credential, and is SELECT-only for `vnext_api`; registration is a reviewed
  migration/operator action, not a normal tenant command.
- `vnext_core.spatial_observations` is tenant-owned, immutable evidence linked to a typed
  PropertyEntity, identity-reference, parcel, building, address, geo-reference, or Case
  subject, and optionally to a parcel geometry version.

Tenant tables use the existing `auth.users.id` principal, active workspace membership checks,
RLS plus FORCE RLS, and INSERT/SELECT-only application grants. The global layer registry has
no workspace duplication and no application mutation grant. None of these records changes
identity status, creates a PropertyEntity/relation, or attaches a Case.

## 3. Competitive-workflow rationale

The useful workflow lesson from the prior competitor audit is that property work is spatial,
iterative, and must retain context: users need to move among address, parcel, building, map
layers, evidence, and their Case without losing the object under investigation. Stage 2A
adopts that workflow principle while keeping this product's stronger trust boundaries:

- canonical-but-confirmable identity rather than an opaque automatic match;
- evidence and source limitations beside each spatial assertion;
- unknown-safe semantics rather than an empty overlay presented as safety;
- durable Case context rather than a disconnected GIS tool catalog.

No competitor endpoint, payload, credential, dataset, visual design, or implementation is
copied, scraped, reverse engineered, or required.

## 4. Parcel / geometry model

`ParcelGeometry` is an immutable version of geometry associated with an existing Stage 1
parcel identity reference. Its contract contains:

- opaque `geometry_id` and `parcel_identity_reference_id`;
- `Polygon` or `MultiPolygon` geometry type;
- original `source_geometry` and its declared `source_crs`;
- normalized `geometry` and `normalized_crs` for interchange;
- precision, tolerance, units, and method;
- bounded geometry-source key;
- retrieval, effective, and validity timestamps;
- structured geographic, temporal, subject, and field coverage;
- source/provider/environment/authority provenance and processing lineage;
- an existing Stage 1 `evidence_id`;
- monotonic version and optional `supersedes_geometry_id`.

The source geometry is never overwritten by normalization. Version 1 cannot supersede an
older record; later versions must identify the version they supersede. Invalid topology,
empty geometry, unsupported geometry types, non-finite coordinates, excessive coordinate
counts, and invalid EPSG:4326 bounds fail closed with bounded codes. Slice 0 does not repair
malformed geometry because repair is a material derivation that needs its own evidence and
review policy.

Canonical geometry is not stored inside `PropertyEntity`. Slice 1 stores immutable,
workspace-scoped versions adjacent to the existing parcel graph node. The latest version is a
read projection over the append-only history, not a mutable `current` flag. Raw/source
artifacts remain Evidence or private Artifact material as license permits. A current geometry
version is a working representation, not an assertion of legal boundary or ownership unless
its evidence and source contract expressly support that claim.

Source geometry is encoded as two-dimensional WKB with a separate, mandatory source CRS and
coordinate-order field. This avoids pretending arbitrary projected coordinates are GeoJSON.
The SHA-256 of those bytes detects corruption. A separate normalized JSONB geometry is always
EPSG:4326 longitude/latitude for safe application/API interchange. The repository round-trips
WKB through Shapely, while database constraints keep source and normalized representations
unambiguous and bound their size. Transformation steps remain immutable JSON lineage.

## 5. CRS policy

1. API and map interchange use `EPSG:4326` with explicit longitude/latitude (`x/y`) order.
2. Every source declares a parseable CRS and coordinate order. Missing or ambiguous CRS is an
   error, not permission to guess.
3. `source_geometry` and `source_crs` are preserved after transformation.
4. Transformations use `pyproj.Transformer(..., always_xy=True)` and append library/version,
   source CRS, target CRS, and coordinate-order lineage.
5. Distance, tolerance, and future area operations use an explicitly selected projected CRS
   whose linear unit is metres. They cannot run in degrees under a metre label.
6. TWD97 / TM2 `EPSG:3825` and `EPSG:3826` are supported examples through the generic CRS
   contract. Neither is a universal Taiwan default; selection depends on jurisdiction,
   geometry extent, source definition, and operation accuracy requirements.
7. No custom projection mathematics is implemented.

The API CRS and processing CRS have different jobs. EPSG:4326 is portable interchange.
Projected distance/area work chooses a suitable local CRS explicitly and records it in the
operation result. Unknown CRS, failed transformation, suspicious axis order, and unit mismatch
fail safely.

## 6. Layer registry

`SpatialLayer` and `SpatialLayerRegistry` provide stable, provider-neutral, versioned metadata. Each
layer declares:

- opaque ID, stable key, title, category, provider, source, and authority class;
- geometry types, source CRS choices, and supported output CRS choices;
- structured coverage and gaps;
- snapshot, effective-interval, live-observation, or unknown temporal semantics;
- event, periodic, manual, immutable-release, or unknown refresh semantics;
- license status/identifier, attribution, commercial-use and redistribution decisions;
- mandatory evidence and provenance requirements;
- availability, uncertainty, and limitations.

Layer key/version pairs and IDs are unique. The durable registry is global system metadata to
avoid copying identical definitions into every workspace. `vnext_api` can read but cannot
insert, update, or delete it, and all versions are append-only. Registration describes a
contract, not production acceptance.
A synthetic layer cannot declare itself fully authoritative/available, and a future official
layer still needs the data-source readiness evidence pack before enablement.

## 7. Spatial operation contracts

Slice 0 defines and implements bounded contracts for:

| Operation | Inputs | Output | Unit rule |
| --- | --- | --- | --- |
| point-in-polygon | Point + Polygon/MultiPolygon | `matches` | boolean; tolerance only in explicit projected metres |
| intersects | Two geometries | `matches` | boolean; tolerance only in explicit projected metres |
| contains | Container + target | `matches` | boolean; tolerance only in explicit projected metres |
| distance | Two geometries | distance + within-tolerance | explicit projected metre CRS only |
| nearest | Query + bounded candidates | stable feature ID + distance | explicit projected metre CRS; deterministic tie-break by feature ID |
| bounding-box query | Query geometry + bounded candidates | matching feature IDs + four bounds | processing-CRS units, zero tolerance |

Every request declares each input CRS, processing CRS, output units, tolerance, and tolerance
unit. Every result repeats those declarations and records input feature IDs, Shapely version,
and all CRS transformations. Operations return geometric observations only. `nearest` never
means same parcel; `intersects` never means a confirmed identity edge; `distance=0` never
means legal equivalence.

## 8. Provider abstraction

The contracts expose separate `ParcelProvider`, `GeometryProvider`, and
`SpatialLayerProvider` protocols over a shared request/result envelope:

```text
provider response
  -> typed SpatialProviderResult
  -> source/environment/coverage/license validation
  -> SpatialObservation normalization
  -> Stage 1 EvidenceDraft
  -> optional proposed graph relation
  -> explicit human review when identity-affecting
```

The provider result can be present, absent, no-match, limited, unavailable, unknown,
provider-error, stale, or not-assessed. Data is forbidden on failure states. Present/limited/
stale require data. An absent result is accepted only with complete, gap-free coverage.
Provider-error exposes bounded codes and retryability, never raw exception or response bodies.

Provider ID, source ID, and authority must match the selected layer during normalization.
`demo`/`test` sources cannot run as production sources, and `synthetic` authority cannot be
constructed in the production environment. No implementation in this slice contacts TGOS,
Google, NLSC, PLVR, a competitor, or any other external system.

## 9. Evidence integration

`SpatialProvenance` is a spatial specialization of facts already required by Stage 1, not a
new evidence store. It carries source/provider/version, authority, environment, retrieval and
effective timestamps, source record/reference, Evidence ID, and transformation lineage.

`observation_evidence_draft()` maps a normalized observation directly to Stage 1
`EvidenceDraft`:

- coverage maps to existing `known|partial|unknown|unavailable` semantics;
- observation state maps to existing evidence status;
- license and attribution remain structured;
- source record, provider, retrieval/effective time, limitations, and lineage survive;
- failures have no usable fact value;
- a proven negative observation is an explicit scoped value, never a generic risk/safety fact.

`parcel_geometry_evidence_draft()` similarly links a geometry to the same Stage 1 store using
an opaque `parcel-geometry:<uuid>` reference rather than duplicating large geometry in an
Evidence value. License metadata remains canonical on Evidence. Database triggers verify
workspace, fact type, source, provider, environment, retrieval time, and expected evidence
status before accepting a spatial row.

Raw provider payloads, private storage paths, permanent signed URLs, and credentials are not
fields in these contracts. The repository and database verify workspace equality among the
subject, Evidence, parcel identity reference, geometry, and Case where applicable.

## 10. Unknown / failure semantics

| Spatial status | Meaning | Downstream behavior |
| --- | --- | --- |
| `present` | A covered layer returned a validated observation | Usable only within stated coverage/freshness; not automatically authoritative |
| `absent` | The queried feature is absent from proven complete, gap-free coverage | Scoped negative observation only; never automatically “safe” |
| `no_match` | Query returned no match but absence semantics are not proven | Preserve no-match and request more evidence |
| `unavailable` | Source/coverage cannot currently supply an answer | Show unavailable; do not infer absence |
| `unknown` | Truth cannot be determined | Preserve unknown; block safety/consequential claims |
| `partial_coverage` | Some result exists but material gaps remain | Show result and gaps; do not fill uncovered dimensions |
| `provider_error` | Provider execution failed | Map to unavailable Evidence while retaining the distinct attempt state |
| `stale` | Historical value exists outside freshness policy | Show history as stale; refresh before consequential use |
| `not_assessed` | No assessment has been performed | Do not display a result or imply zero risk |

`unknown`, `unavailable`, `no_match`, `not_assessed`, and `provider_error` are deliberately
different states. None means no parcel, no hazard, no planning constraint, zero risk, or safe.
Even `absent` supports only the exact layer/query/coverage/effective-time negative statement.

When providers disagree, every observation and its lineage survives. The system creates a
conflict for review; source priority may order evidence but cannot erase it, confirm identity,
or select a geometry automatically.

## 11. Map Workspace contract

`MapWorkspaceContract` places the map inside a durable professional investigation context.
It requires:

- workspace and Case IDs;
- optional selected `PropertyEntity`;
- separate candidate and confirmed parcel-geometry IDs;
- selected stable layer keys;
- legend entries with title, authority, observation status, and attribution;
- observation IDs for the Evidence rail;
- bounded EPSG:4326 viewport and optional bounds;
- typed feature selection linked to layer and Evidence;
- visible limitations.

A selected feature must belong to an active layer, and every active layer must have legend
metadata. The map can therefore support future parcel/building selection, layer toggles,
planning/hazard overlays, comparisons, and spatial inspection without becoming the homepage
or an isolated tool list. Slice 0 defines state only; it adds no frontend component or route.

Map state is attached to `Case` as investigation context, not as property identity. Slice 1
deliberately defers MapWorkspace persistence because viewport, selection, and layer toggles
are presentation state rather than durable evidence. A later slice may persist reviewed Case
map preferences or append map-inspection Activities. It must
not populate `Case.property_entity_id` or create `CasePropertyLink` without the existing
explicit command.

## 12. Security / privacy considerations

- Privileged GIS access is server-side only; browsers never receive provider credentials.
- Supabase `service_role`, database URLs, and future NLSC credentials are forbidden in client
  bundles, provider results, logs, geometry metadata, and Evidence DTOs.
- Exact address, point, and parcel geometry can be private tenant data. APIs must return only
  purpose- and role-authorized projections with non-enumerating cross-workspace behavior.
- User-supplied geometry is labelled `user_supplied` and remains unverified until independently
  supported; upload provenance cannot become official authority.
- Raw artifacts are private and retained only when license and tenant policy permit.
- Provider errors are bounded codes; no raw body, URL credential, SQL, or stack trace crosses
  the adapter boundary.
- Spatial persistence remains in private-by-default VNext schemas with workspace authorization
  and RLS defense in depth. Migration 018 adds no role, Auth change, public table, or Data API
  exposure.

## 13. NLSC Stage 2B boundary

NLSC source approval, exact cadastral dataset/endpoint, authorization, license, attribution,
CRS/version, coverage, update cadence, quota, and failure acceptance remain pending. The
existing metadata-only registry entry and disabled placeholder do not prove integration.

Stage 2B may implement an NLSC production adapter only after that evidence pack is approved.
This slice does not invent credentials, emulate undocumented endpoints, scrape services, make
live calls, claim official coverage, or label synthetic fixtures NLSC data.

## 14. Test strategy

Focused Slice 0 and Slice 1 tests cover:

- valid, malformed, empty, overly ambiguous, and transformed geometry contracts;
- explicit EPSG:4326 coordinate order and projected metre processing;
- source geometry/CRS and transformation-lineage preservation;
- point inside/outside parcel, overlap, contains, distance, nearest, and bounding box;
- no-match, partial, unknown, unavailable, provider-error, stale, and not-assessed fixtures;
- complete-coverage requirement for an absence observation;
- provider/source/environment/authority separation;
- Evidence field preservation;
- full-confidence property/parcel relations remaining proposed;
- Case-scoped Map Workspace metadata;
- unmistakably synthetic fixture labels.
- immutable first/new geometry versions, complete history, WKB/CRS round-trip, Evidence links,
  invalid/self/cross-parcel supersession, duplicate version/source records, and concurrent
  supersession races;
- observation idempotent replay and distinct unknown/no-match/error/absence behavior;
- global layer mutation denial, tenant RLS/FORCE RLS, ownership, grants, and cross-workspace
  isolation on a disposable local PostgreSQL database.

The relevant Stage 1 graph/evidence/identity tests are regression gates because the new module
imports their contracts. No credentialed provider, hosted-database, or PostGIS test is
appropriate until a later slice explicitly introduces those boundaries.

## 15. Slice roadmap

- **Slice 0:** pure domain/CRS/layer/provider/operation/map contracts, synthetic
  fixtures, tests, and architecture decisions.
- **Slice 1 (this gate):** additive migration 018, spatial repositories, append-only versioning,
  Stage 1 Evidence/idempotency linkage, workspace/RLS gates, and disposable PostgreSQL proof.
- **Later Stage 2A slices:** bounded map read workflow and approved non-production integration
  rehearsals.
- **Stage 2B:** production NLSC adapter only after source approval and real-provider acceptance.
- **Stage 3:** building, planning, and redevelopment observations reuse the same layer,
  temporal, CRS, Evidence, conflict, relation-proposal, and Map Workspace contracts.

PostGIS remains a later architecture option, not a Slice 0 dependency. Its adoption requires a
separate additive migration, managed-provider extension approval, RLS/grant design, index/query
plan evidence, disposable-database validation, backup/restore readiness, and rollout gate.

## 16. Explicit non-goals

Slice 1 does not:

- apply migration 018 to production, add PostGIS, add a role, or expose an API route;
- enable `parcel_workspace`, `identity_v1`, or any other feature flag;
- implement a production NLSC or other GIS provider;
- scrape, reverse engineer, or call a competitor or official system;
- create or confirm `PropertyEntity`, parcel identity, or graph relations;
- merge/split property or parcel records;
- auto-attach a Case or modify SavedCase behavior;
- build the map UI or alter the homepage;
- expose browser-direct privileged GIS access;
- modify Stage 1 production readiness or authorize production rollout;
- implement Stage 3 building/planning features.

## 17. Architecture decisions

### 1. Where should canonical parcel geometry live?

In a future immutable, workspace-scoped parcel-geometry record owned by the Spatial bounded
context and linked to the existing Stage 1 parcel identity-reference graph node and Evidence.
It does not live inside `PropertyEntity`, an address string, or only in an opaque raw artifact.
“Current” is a reviewed projection over versions, not an in-place overwrite.

### 2. Is geometry an identity attribute, an evidence artifact, or both?

Both, with distinct roles. Source geometry/raw material is evidence. A normalized, versioned
geometry can be an attribute of a parcel identity candidate/current working representation.
Geometry alone never establishes legal or canonical identity.

### 3. When can two parcel geometries be considered the same parcel?

Never from coordinate equality, overlap, centroid, distance, or tolerance alone. They may be
proposed as the same parcel when identifier, jurisdiction, temporal applicability, geometry
comparison, coverage, source, and conflicts are all reviewed. Identity-affecting equivalence
requires the existing explicit human confirmation path.

### 4. How are geometry versions represented?

Each immutable record has `geometry_id`, version, effective/validity times, Evidence and
provenance, plus `supersedes_geometry_id` after version 1. Corrections append; they do not
mutate source coordinates or delete history.

### 5. How should parcel split/merge history be represented later?

As explicit temporal graph events and successor/predecessor relations backed by evidence and
human review. Prior parcel nodes and geometry versions remain addressable, old open intervals
close at the effective time, and no destructive row merge occurs.

### 6. Which CRS is used at API boundaries?

EPSG:4326 with explicit longitude/latitude order. Original provider CRS and coordinates remain
available through authorized provenance/source representations rather than being discarded.

### 7. Which CRS should spatial distance/area operations use?

An explicitly selected, suitable local projected CRS with metre units, chosen from the
jurisdiction and geometry extent and recorded in the result. EPSG:3825/3826 are extensible
Taiwan examples, not universal defaults. Geodesic methods may be added later under a separate
named contract when their error policy is defined.

### 8. What happens when provider coverage is unknown?

The result is `unknown` or `unavailable`, value is absent, limitations are visible, and no
negative/safe/zero-risk conclusion is allowed. A provider no-match remains `no_match` unless
complete coverage and negative-query semantics are independently proven.

### 9. What happens when providers disagree?

Preserve all observations and lineage, create a conflict, show source/coverage/time differences,
and block automatic identity or consequential conclusions. A later authorized human decision
may cite the evidence without deleting the losing observation.

### 10. What requires human confirmation?

Property/parcel or parcel/building identity, replacement of a current canonical geometry,
same-as/merge/split decisions, resolution of material provider conflicts, and any Case
attachment that changes canonical property context. Viewing a geometric predicate does not.

### 11. Which operations should eventually move into PostGIS?

Large tenant datasets, indexed point-in-polygon/intersection queries, bounding-window scans,
nearest-neighbor search, spatial joins, topology validation at write boundaries, and repeated
area/distance aggregation should move after query-plan and extension approval.

### 12. Which operations should remain application-layer?

Provider normalization, license/coverage/authority gates, CRS policy selection, small bounded
candidate comparisons, Evidence creation, conflict semantics, human-confirmation decisions,
Map Workspace orchestration, and safe error projection remain application responsibilities.

### 13. How does Map Workspace attach to Case?

The contract requires `workspace_id` and `case_id`; selected property, candidate/confirmed
parcel geometries, layers, observations, viewport, and feature selection are investigation
context. Persisted preferences/Activities may be added later, but map interaction cannot create
`CasePropertyLink` or populate canonical property identity automatically.

### 14. How does this design enable future Building/Planning Stage 3?

Building geometries and planning overlays can reuse CRS definitions, layer registry metadata,
provider envelopes, observation/failure states, Evidence adaptation, temporal validity,
spatial operations, proposed typed graph relations, and the same Case-scoped map shell. Stage
3 can add domain-specific facts without weakening identity or creating another provenance
framework.
