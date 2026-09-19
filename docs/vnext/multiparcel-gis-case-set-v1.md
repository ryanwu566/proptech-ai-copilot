# Multi-Parcel GIS Case Set v1

Status: Stage 2 design contract only; no migration, runtime code, provider integration or UI implementation
Date: 2026-09-20

## 1. Objective

Design the smallest durable Stage 2 slice that lets one Case review multiple parcel
candidates and selected parcels without becoming an unbounded GIS editor.

Target workflow:

```text
Case
  -> PropertyEntity
  -> parcel set
  -> selected parcels
  -> evidence/provenance
  -> map visualization
```

This slice does not solve cadastral provider integration, planning/zoning, title, CRM,
arbitrary drawing, freehand editing, or legal parcel-boundary authority.

## 2. Current Audit

### PropertyEntity graph

The current VNext graph is structurally close to the target:

- `property_entities` are workspace-scoped application aggregates, not government IDs.
- `property_identity_references` already support `reference_type='parcel'`.
- `property_graph_nodes` already map `property`, `address`, `geo_reference`, `parcel`,
  `building`, `listing`, and `case` node types.
- `property_relations` already supports `property_parcel` and `parcel_building`.
- Relations are typed, temporal, evidence-bearing, statused, and append-only.

This is sufficient for saying "this Property has these parcel observations/relations." It
is not sufficient for saying "this Case is reviewing this ordered parcel set and these
members are currently selected."

### Parcel identity references

Manual parcel references exist as normalized parcel hypotheses:

- `POST /v1/properties/{property_entity_id}/parcel-hypotheses`
- source `user-upload`
- `property_identity_references.reference_type='parcel'`
- `property_relations.relation_type='property_parcel'`
- relation status `proposed`
- no identity confirmation

The current command deliberately creates unverified manual references. It also has a
workspace-wide duplicate guard by normalized parcel key. That is conservative for Stage 1,
but Stage 2 needs to support the same parcel being reviewed in more than one Property/Case
over time without making duplicate reference rows. Reuse should become a controlled relation
or parcel-set membership operation, not another identical identity reference.

### Parcel hypotheses and evidence

Parcel evidence already has a provider-independent envelope:

- fact type `parcel.hypothesis_observation.v1`
- status/coverage/quality/license/lineage fields
- evidence links to parcel graph nodes
- source classes limited to request-appendable `user-upload` or `vnext-deterministic`
- review states such as `unreviewed`, `manual_review_required`, `reviewed`, and `rejected`

This is sufficient for provenance about a parcel candidate. It is not sufficient for
recording case-local parcel selection, review order, active focus, or a user decision that a
candidate belongs in the case parcel set.

### Case attachment

Cases exist and can be attached to a confirmed Property through append-only
`case_property_links`. The Case attachment history is versioned and concurrency-checked.

The current model supports one current Case-to-Property attachment. It does not create a
case graph node automatically, nor does it have a case-scoped relation from Case to parcel
members. A Stage 2 parcel set must therefore be anchored by `case_id` and
`property_entity_id`, not inferred from all `property_parcel` graph edges.

### Map geometry models

Current GIS behavior is request-scoped:

- `/parcel-geometry/status` reports `uploaded_geometry_persisted: false`.
- `/parcel-geometry/upload` accepts bounded GeoJSON, KML, and Shapefile ZIP, normalizes to
  EPSG:4326, validates topology, computes geometric area, and clearly labels upload results
  as user-provided, non-legal geometry.
- NLSC official vector is disabled unless endpoint and authorization are proven.
- spatial intersection is done application-side with Shapely/pyproj.

The existing geometry path is useful for preview and evidence capture, but it does not own a
durable legal parcel boundary and does not yet use PostGIS.

### Frontend map components

The frontend currently has:

- `GeoMap` for location/POI visualization, center marker, radius, base layers, and nearby
  markers.
- `TerrainEvidenceLeafletMap` for a cadastral raster overlay, point marker, optional parcel
  GeoJSON overlay, and hazard radius.
- `TerrainRiskAnalysis` upload controls for one request-scoped parcel geometry, including
  replace/remove, validation, consistency and spatial-analysis display.
- `property-identity-review` and `vnext-property-identity-workflow` for graph/candidate
  review, including proposed parcel hypotheses.

The map UI can render one uploaded/user parcel overlay today. Stage 2 needs a parcel list
and multiple overlay styles, but not drawing tools.

### PostGIS availability

PostGIS is not applied in current migrations. The architecture says it must be introduced in
a dedicated additive migration only after managed-provider/extension-schema approval. Stage
2 design may require PostGIS for durable geometry, but this document does not create it.

### Evidence model

The evidence model is strong enough for Stage 2:

- evidence is immutable/versioned;
- evidence links point to graph nodes;
- lineage can link derivations and supersession;
- unknown/unavailable/limited/conflicting states are preserved;
- mock/demo/test evidence cannot satisfy production confirmation.

Stage 2 should reuse this model and add only the missing case parcel-set decision record.

## 3. Design Decision

Add a first-class, bounded `case_parcel_sets` aggregate plus append-only
`case_parcel_set_events`.

Do not add a general GIS project/editor. Do not make geometries mutable drawings. Do not
duplicate the property graph. The graph remains the identity/evidence backbone; the parcel
set is the case-local review state over that graph.

Recommended conceptual tables:

```text
case_parcel_sets
  case_parcel_set_id
  workspace_id
  case_id
  property_entity_id
  status                    draft|under_review|confirmed|superseded|archived
  active_member_reference_id nullable parcel identity reference
  version
  created_by_user_id
  created_at
  updated_at
  supersedes_case_parcel_set_id nullable

case_parcel_set_members
  case_parcel_set_member_id
  workspace_id
  case_parcel_set_id
  property_entity_id
  parcel_identity_reference_id
  property_parcel_relation_id
  member_order
  selection_state            candidate|selected|confirmed|rejected|removed
  selection_reason
  selected_by_user_id nullable
  selected_at nullable
  evidence_id nullable
  geometry_evidence_id nullable
  version
  created_by_user_id
  created_at
  valid_from
  valid_to nullable
  supersedes_member_id nullable

case_parcel_set_events
  case_parcel_set_event_id
  workspace_id
  case_parcel_set_id
  event_type                 created|member_added|member_selected|member_confirmed|
                             member_rejected|member_removed|active_changed|
                             reordered|geometry_attached|superseded
  actor_user_id
  case_version_observed
  parcel_set_version_before
  parcel_set_version_after
  request_id
  idempotency_record_id
  metadata
  created_at
```

The first implementation can collapse members and events into one append-only member history
table if that is simpler, but it must still expose a current projection with ordering,
selection, active state and version.

## 4. Why Current Graph Alone Is Not Enough

`property_relations` can answer "which parcel references are related to this Property?" It
cannot safely answer these case-local questions:

- which subset is currently in scope for this Case;
- which candidates are selected for review versus rejected or removed;
- which parcel is active in the map/detail panel;
- what order the user expects in tables, reports, and review workflow;
- which case version and parcel-set version the user observed before changing the set;
- whether a parcel belongs to another Case's review without copying identity references.

Adding ad hoc metadata to `property_relations` would make global graph edges carry UI state.
That would blur Property identity with Case workflow and make append-only history harder to
reason about. A small parcel-set aggregate keeps the graph clean.

## 5. Persistence Requirements

### Identity and relations

Every member must reference:

- the same `workspace_id` as the Case and Property;
- the current attached `property_entity_id`;
- a `property_identity_references` row with `reference_type='parcel'`;
- a `property_relations` row with `relation_type='property_parcel'` connecting the Property
  node to the parcel node.

The relation may be `proposed`, `confirmed`, or `disputed`. `rejected`, `superseded`, and
closed relations can remain visible in history, but cannot be newly selected.

### Ordering

Ordering is case-local and explicit. Use `member_order` as a dense positive integer in the
current projection. Reorder operations append a new version/event; they do not mutate older
events. The API returns ordered members by `member_order`, then `created_at`.

### Selected and active state

`selection_state` is persisted per member:

- `candidate`: visible hypothesis, not selected;
- `selected`: included in the working parcel set;
- `confirmed`: human-confirmed as part of the parcel set, still not legal title;
- `rejected`: reviewed and excluded;
- `removed`: previously in the set, no longer current.

`active_member_reference_id` is a UI/workflow convenience for the current map/detail focus.
It must point to a non-removed current member. Changing active state is idempotent and
versioned, but it is not evidence and not a property graph relation.

### Proposed versus confirmed

Stage 2 has two independent confirmation dimensions:

1. Graph identity confirmation: existing `identity_decisions` and confirmed
   `property_parcel` relation semantics.
2. Case parcel-set confirmation: a human says "these parcel members are the set this Case is
   reviewing."

Case parcel-set confirmation does not create legal title, owner identity, planning status, or
official boundary authority. UI copy must use "confirmed in case" or "case-confirmed parcel
set", not "official parcel ownership."

### Geometry ownership

Geometry is evidence, not the parcel-set owner.

Recommended future geometry evidence fact types:

```text
parcel.geometry.user_upload.v1
parcel.geometry.official_boundary.v1
parcel.geometry.point_reference.v1
parcel.geometry.preview_union.v1
```

The parcel member references the chosen `geometry_evidence_id` when a geometry preview is
available. Official boundary evidence may be used only after NLSC or another parcel vector
source is accepted. User upload remains `user_provided|unverified` and cannot upgrade a
parcel identity to official.

If PostGIS is approved, add a dedicated VNext spatial table keyed by evidence/member, for
example:

```text
parcel_geometry_versions
  parcel_geometry_version_id
  workspace_id
  parcel_identity_reference_id
  evidence_id
  geometry_kind              point|polygon|multipolygon
  source_authority           user|official|deterministic
  geom_4326                  geometry
  bbox_4326                  geometry or generated envelope
  area_m2_computed
  legal_boundary             boolean
  crs_original
  created_at
```

That table should be append-only and evidence-backed. It should never store arbitrary editor
drawings without a source/evidence envelope.

### Provenance

Every add/select/confirm/remove/reorder action must record:

- authenticated actor;
- request ID;
- idempotency record;
- observed Case version;
- observed parcel-set version;
- source/evidence IDs cited by the decision;
- bounded reason or selection note where applicable.

Map preview geometry must carry source, CRS, coverage, quality, license and lineage through
Evidence. Raw uploads require private artifact/storage policy before persistence.

### Versioning and concurrency

Mutations use optimistic concurrency:

- caller supplies `case_version` and `parcel_set_version`;
- server rejects stale writes with `version_conflict`;
- successful writes increment parcel-set version;
- writes that affect Case identity/workflow should also check Case version;
- idempotency keys replay without repeating events.

Use advisory locks or row-level serialization around one `case_parcel_set_id` to prevent two
simultaneous selections from creating conflicting current projections.

## 6. API Surface

Suggested smallest `/v1` routes:

```text
GET  /v1/cases/{case_id}/parcel-set
POST /v1/cases/{case_id}/parcel-set
POST /v1/cases/{case_id}/parcel-set/members
POST /v1/cases/{case_id}/parcel-set/members/{member_id}/select
POST /v1/cases/{case_id}/parcel-set/members/{member_id}/reject
POST /v1/cases/{case_id}/parcel-set/members/{member_id}/remove
POST /v1/cases/{case_id}/parcel-set/active-member
POST /v1/cases/{case_id}/parcel-set/reorder
POST /v1/cases/{case_id}/parcel-set/confirm
```

All mutations require `Idempotency-Key`. All mutations require active workspace membership;
confirmation requires owner/admin or the same role policy used for identity confirmation.

`POST /members` accepts an existing parcel identity reference/relation, or a bounded inline
manual parcel hypothesis payload that delegates to the existing parcel-hypothesis command and
then adds the resulting relation as a set member. It must not create duplicate parcel
references for the same normalized key when an existing reference is available in the same
workspace.

Suggested response shape:

```json
{
  "case_id": "uuid",
  "property_entity_id": "uuid",
  "parcel_set_id": "uuid",
  "status": "under_review",
  "version": 4,
  "active_member_id": "uuid",
  "members": [
    {
      "member_id": "uuid",
      "order": 1,
      "selection_state": "selected",
      "parcel_identity_reference_id": "uuid",
      "property_parcel_relation_id": "uuid",
      "relation_status": "proposed",
      "display_value": "...",
      "source": {"source_id": "user-upload", "source_type": "user"},
      "evidence_ids": ["uuid"],
      "geometry": {
        "geometry_evidence_id": "uuid",
        "status": "user_provided",
        "legal_boundary": false,
        "bbox": [0, 0, 0, 0],
        "centroid": {"lat": 0, "lng": 0}
      }
    }
  ]
}
```

Do not expose raw geometry bodies by default once persisted geometry can become large or
licensed. Return bounded map-ready summaries and a separate authorized geometry read only
when policy allows.

## 7. UI Behavior

The Stage 2 UI should be a review workbench, not a GIS editor:

- Case header shows attached Property, parcel-set status, version and evidence freshness.
- Left/table rail lists parcel members in persisted order with status chips:
  `candidate`, `selected`, `case-confirmed`, `rejected`, `removed`.
- Map canvas renders multiple parcel overlays:
  selected = solid accent;
  candidate = dashed;
  rejected/removed = hidden by default but available in history;
  user upload = dashed with non-legal label;
  official boundary = solid only when accepted evidence exists.
- Clicking a row sets active member and centers/fits the map.
- Map click may create only a point reference/hypothesis, not a polygon boundary.
- Upload can attach geometry evidence to one parcel candidate or to a preview union, but
  cannot freehand edit or replace an official boundary.
- Confirmation button states exactly what is being confirmed: the case parcel set, not title,
  ownership, zoning or legal area.
- Evidence rail shows per-member provenance, geometry limitation, source coverage, quality,
  license and conflicts.

No freehand drawing, vertex editing, split/merge tool, bulk cadastral fetcher, title action,
zoning panel, owner/contact flow, or CRM workflow belongs in this slice.

## 8. Migration Likelihood

Migration is likely, but not in this docs-only stage.

Minimum additive schema later:

- `018_vnext_case_parcel_sets.sql` or next safe sequence from the registry;
- private `vnext_core` tables with FORCE RLS;
- grants only to `vnext_api`;
- RLS policies matching case/property membership;
- append-only guards for events/history;
- idempotency/audit integration;
- no PostGIS dependency for the first non-geometry parcel set slice.

PostGIS is a second additive migration only if durable geometry storage/querying is included.
The smallest Stage 2 slice can launch without PostGIS by persisting parcel-set membership and
showing existing evidence/point/upload summaries. Durable polygon storage and spatial
intersection acceleration need PostGIS acceptance first.

## 9. Dependencies

Required before implementation:

- Stage 1 identity and case attachment remain passing.
- `identity_v1` and future `parcel_workspace` feature gates stay server-enforced.
- Data-source registry owner action for exact NLSC parcel dataset if official vectors are in
  scope.
- Private upload/artifact policy if raw uploaded geometry is persisted.
- PostGIS provider/extension approval only if durable polygon storage or spatial indexing is
  part of the implementation slice.
- UI must reuse the existing Leaflet rendering foundation and property identity review copy
  rather than introduce a new editor shell.

## 10. Acceptance Tests

### Contract and service tests

- A Case attached to one Property can create one parcel set.
- A parcel set cannot be created for a Case without a same-workspace attached Property.
- Adding a member requires a valid same-workspace `property_parcel` relation.
- Adding the same parcel relation twice is idempotent or returns a duplicate conflict; it does
  not create a second current member.
- The same parcel identity reference can be a member of different Case parcel sets in the same
  workspace when each Case/Property relation is valid.
- Ordering is stable and reorder requires the current parcel-set version.
- Active member must be a current non-removed member.
- `selected`, `confirmed`, `rejected`, and `removed` transitions are append-only and audited.
- Case parcel-set confirmation does not create title/ownership/planning claims.
- Stale `case_version` or `parcel_set_version` returns `version_conflict`.
- Idempotency replay returns the prior resource without duplicating events.

### Database and security tests

- Cross-workspace Case/Property/parcel relation links fail.
- RLS denies anonymous access and denies active viewers from mutations.
- Owner/admin confirmation passes; unauthorized role confirmation fails.
- Append-only guards prevent event/history updates/deletes by the application role.
- Audit rows are created for successful and denied consequential mutations.
- No table is exposed through Data API/base grants beyond reviewed role grants.

### Evidence and provenance tests

- Every selected or confirmed member cites evidence or explicitly records why evidence is
  unavailable/unknown.
- User-upload geometry remains `user_provided|unverified` and `legal_boundary=false`.
- Demo/test evidence cannot satisfy production parcel-set confirmation.
- Conflicting parcel evidence blocks case parcel-set confirmation unless an authorized
  reviewer records a bounded conflict-resolution decision.
- Geometry evidence preserves CRS, source, retrieval/effective time, quality, license and
  lineage.

### UI and E2E tests

- The parcel set renders as a synchronized table and map overlay.
- Selecting a row changes the active parcel and map focus.
- Candidate/selected/confirmed/rejected visual states are distinguishable without implying
  legal authority.
- Upload/preview limitations are visible before confirmation.
- Mobile layout keeps the ordered member list, active parcel details and map usable without
  overlap.
- The confirmation dialog names the selected parcel count, source limitations and explicit
  non-title/non-zoning boundary.

## 11. Stage 2 Slice Recommendation

Build Stage 2 in two sub-slices:

1. Durable case parcel set without PostGIS:
   case-scoped set/member/event tables, API, read projection, frontend table/map overlay
   using existing parcel references and existing geometry/evidence summaries.
2. Durable geometry evidence after source/storage/PostGIS acceptance:
   geometry evidence fact types, optional `parcel_geometry_versions`, GiST indexes, map-ready
   geometry read policy, and spatial query acceptance.

The first sub-slice is the smallest useful product step. It lets a Case review multiple
parcel candidates and selected parcels durably, while keeping provider integration and true
GIS infrastructure out of scope until their evidence gates are met.

## 12. Final Assessment

Existing model sufficient: partially. The graph/evidence foundation is sufficient for parcel
identity references, property-parcel relations and provenance. It is not sufficient for
case-local parcel-set ordering, active state, selected state, and review confirmation.

New schema required: yes, for `case_parcel_sets` and `case_parcel_set_members/events`.
PostGIS schema is not required for the smallest durable parcel-set slice, but is likely for
durable polygon storage and spatial indexing.

Migration likely: yes. The future migration should be additive, private, RLS-protected and
registered as the next safe sequence. No migration is created by this document.

Acceptance gate: GO only for a bounded parcel-set review slice. NO-GO for official cadastral
boundary claims, arbitrary GIS editing, title/ownership, planning/zoning, or persisted raw
uploads until their source/storage/PostGIS gates are approved.
