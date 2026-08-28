# Property Identity Architecture v1

Status: Stage 0 contract only; resolver and UI are not implemented

## 1. Decision

`PropertyEntity` is a workspace-scoped application aggregate. It represents the real asset
or asset set a user currently believes they are studying, without claiming a nationwide
government ID. A `Case` represents a purpose for studying it. They have separate identifiers,
lifecycles and permissions.

Address, parcel, building, listing and coordinate observations are evidence-backed graph
nodes. None is globally unique and none is assumed one-to-one with another node. Resolution
always produces reviewable candidates before confirmation.

## 2. Supported future inputs

| Input kind | Minimum value | Normalization output | Special boundary |
| --- | --- | --- | --- |
| `address` | user-entered address text | original text, normalized components/version | String similarity is candidate evidence only |
| `lot_number` | jurisdiction + section/subsection + number | structured cadastral reference | Requires authorized/covered provider confirmation |
| `building_number` | issuing authority + identifier | structured building reference | No nationwide uniqueness claim |
| `coordinates` | lat/lon + declared CRS | EPSG:4326 point and original CRS | A point is not a parcel boundary |
| `map_click` | viewport point + map source/version | coordinate input with interaction metadata | Map click is user-provided/unverified |
| `listing_url` | normalized HTTPS URL on allowlisted/partner host | partner listing reference | No scraping or identity claim from URL alone |

All inputs retain the original observation and normalization version. Normalization may clean
formatting but may not invent absent building, parcel, address or jurisdiction components.

## 3. Resolution contract

```text
Input
  -> normalization
  -> provider resolution attempts
  -> evidence-backed candidates
  -> conflict detection
  -> explicit human confirmation or rejection
  -> property graph edges
```

Conceptual request:

```json
{
  "workspace_id": "uuid",
  "input": {
    "kind": "address",
    "value": {"text": "..."},
    "declared_crs": null
  },
  "case_id": null,
  "normalization_version": "identity-normalizer-v1"
}
```

Conceptual resolution record:

```json
{
  "resolution_id": "uuid",
  "workspace_id": "uuid",
  "state": "candidates_found",
  "input_ref": "artifact-or-inline-reference",
  "normalized_input": {},
  "candidates": [],
  "conflicts": [],
  "provider_attempts": [],
  "selected_candidate_id": null,
  "confirmed_property_entity_id": null,
  "created_by": "authenticated-principal-id",
  "created_at": "RFC3339 timestamp",
  "updated_at": "RFC3339 timestamp",
  "version": 1
}
```

Candidate contract:

```text
candidate_id
candidate_kind
display_label
proposed_nodes[]
proposed_relations[]
supporting_evidence_ids[]
provider_sources[]
confidence                 # bounded score plus named method/version
coverage
conflicts[]
requires_human_confirmation = true
```

Confidence orders candidates for review. It is never an automatic merge/confirmation
threshold.

## 4. Resolution state machine

Allowed transition outline:

```text
received -> normalizing -> candidates_found -> confirmed
                         |                  -> ambiguous
                         |                  -> partially_resolved
                         |                  -> unresolved
ambiguous -> confirmed | partially_resolved | unresolved
partially_resolved -> candidates_found | confirmed | unresolved
confirmed -> superseded
unresolved -> normalizing
any non-terminal record -> superseded
```

Transitions are commands checked against the stored version. Every transition records actor,
request ID, reason and audit event. `confirmed` and `superseded` are terminal versions; new
information starts a new resolution or explicit superseding version.

| State | Meaning | Allowed operations | Forbidden operations | UI semantics | Persistence semantics |
| --- | --- | --- | --- | --- | --- |
| `received` | Valid request accepted but not normalized | inspect, cancel/supersede, begin normalization | candidates, confirmation, property attachment | “Received; not assessed” | Persist original input, actor, tenant, idempotency/request IDs |
| `normalizing` | Deterministic normalization/provider planning in progress | update bounded progress, fail to unresolved, add provider attempts | show a confirmed property, merge, downstream procurement | Loading with no success claim | Persist normalization version and append attempt metadata; never raw secrets |
| `candidates_found` | One or more evidence-backed candidates exist and no unresolved blocking conflict prevents presentation | inspect evidence/map, select, reject, request more evidence, confirm one candidate | silent confirmation, multi-candidate merge, owner/CRM/title action | Candidate comparison; explicit confirm control | Persist immutable candidate snapshots and conflict evaluation |
| `ambiguous` | Multiple plausible interpretations or a material conflict remains | display candidates, map confirmation, human selection/rejection, add evidence | title purchase, owner link, CRM bind, property merge, authoritative downstream action | Prominent ambiguity and missing-evidence message | Persist all candidates/conflicts; no confirmed property FK |
| `confirmed` | An authorized human confirmed one candidate for this workspace | read graph, attach to Case, propose later correction/merge/split | edit history in place, auto-reconfirm another candidate | Confirmed with actor/time/source and change path | Persist selected candidate, confirmer, time, evidence set and created edges |
| `partially_resolved` | Some nodes/relations are supportable but identity is not fully confirmable | inspect partial graph, add evidence, re-resolve, use explicitly limited reference data | legal/title/owner conclusions, destructive merge, represent as confirmed | Partial badge; name resolved and unresolved dimensions | Persist supported proposals as `proposed`/`limited`; confirmed property is null unless an earlier property attachment remains explicit |
| `unresolved` | No supportable candidate, unsupported input, unavailable coverage or exhausted provider attempt | edit/retry input through a new attempt, inspect errors, supersede | fake candidate, safe/no-risk conclusion, confirmed attachment | Explain no result vs provider unavailable | Persist safe error/coverage statuses and attempt lineage; no synthetic data |
| `superseded` | A newer resolution, correction, merge or split replaced this record | read history and follow successor link | mutate, confirm, attach as current | Read-only history with successor reason | Immutable; retain `superseded_by`, actor, time and reason |

## 5. Normalization and conflict detection

Normalization is deterministic, versioned and unit-tested. It may:

- Unicode-normalize and safely standardize Taiwan administrative/address tokens;
- parse structured lot/building identifiers while retaining raw text;
- normalize coordinate order/CRS and reject implausible values;
- canonicalize an allowlisted partner listing URL without fetching it;
- emit warnings and missing fields rather than guessing.

Conflict detection runs before confirmation and records, at minimum:

- provider disagreement on normalized address, coordinates or jurisdiction;
- parcel/building/address cardinality disagreement;
- temporal conflict such as renumbering, parcel split/merge or listing relist;
- low/unknown source coverage or stale/unverified evidence;
- an existing workspace entity with competing confirmed relations.

A conflict is data. It is not removed by taking the highest provider score.

## 6. Property graph

Required node kinds:

```text
property | address | geo_reference | parcel | building | listing | case
```

Parcel, building and listing tables are Stage 2-4 work. Stage 1 may register placeholder node
kinds and relation enums, but must not create false provider-backed records.

Required logical edges:

```text
property -> address
property -> parcel
property -> building
property -> listing
parcel <-> building
listing -> building
listing -> parcel
property -> case
```

The implementation should use `property_graph_nodes` so `property_relations.from_node_id` and
`to_node_id` have real FKs. A graph node maps `(workspace_id,node_type,record_id)` to one opaque
node ID. Application and database checks require both endpoints and referenced evidence to
belong to the same workspace.

Conceptual `property_relations` columns:

```text
property_relation_id
workspace_id
from_node_id
to_node_id
relation_type
direction
confidence
confidence_method
source_id
evidence_id
status                    # proposed|confirmed|rejected|superseded|disputed
valid_from
valid_to
confirmed_by
confirmed_at
supersedes_relation_id
created_at
```

Indexes:

- `(workspace_id, from_node_id, relation_type, status, valid_to)`;
- `(workspace_id, to_node_id, relation_type, status, valid_to)`;
- partial index for open confirmed edges (`valid_to is null`);
- evidence and supersession references;
- optional exclusion/uniqueness constraints only for relation types whose real-world
  cardinality has been explicitly proven. No generic one-to-one constraint.

## 7. Confirmation

Confirmation requires:

1. authenticated workspace member with an authorized role;
2. resolution currently in `candidates_found`, `ambiguous` or `partially_resolved`;
3. selected candidate from the immutable candidate set;
4. explicit confirmation reason/intent and current record version;
5. evidence/status/coverage shown at the decision point;
6. idempotency key and append-only audit event.

Confirmation creates or links an application PropertyEntity and approved graph relations in
one transaction. Provider candidates not selected remain immutable evidence. A rejected
candidate is not deleted.

## 8. Merge ADR

Decision: merge is a reviewed graph operation, never row deletion or similarity-triggered
mutation.

```text
merge proposal
  -> compare identifiers, relations, temporal facts and conflicting evidence
  -> authorized human confirmation
  -> create `same_as` / `supersedes` relation
  -> migrate only explicitly approved open links
  -> close old temporal edges
  -> keep both entity records and audit history
```

The merge proposal records source and target, evidence set, affected links, conflicts and a
dry-run impact summary. Approval uses optimistic concurrency. Cases, artifacts, evidence and
activities are relinked only when individually eligible; immutable references may continue
to point at the historical entity. Undo is a compensating graph operation, not history
deletion.

Forbidden merge triggers include address-string similarity, coordinate proximity, shared
listing photos/text, a provider score alone, AI output or an unconfirmed legacy SavedCase.

## 9. Split ADR

Parcel division/consolidation, building subdivision, address renumbering and listing relist
are temporal events. A split:

1. proposes successor entities/relations and effective time;
2. compares authoritative and user evidence;
3. obtains authorized human confirmation;
4. creates successor entities/edges;
5. closes affected prior edges at `valid_to`;
6. preserves old entity IDs, cases, artifacts and evidence;
7. records audit and a visible activity when relevant.

Historical evidence remains attached to the subject it originally described unless a new,
explicit evidence item states successor applicability.

## 10. Case attachment

A Case may exist with no confirmed PropertyEntity. `legacy_unverified` and early investigation
cases hold their entered address/notes as user-provided evidence. `attach-resolution` accepts
only a confirmed resolution, or records an explicitly partial reference without populating
the canonical property FK. Reattachment is an audited command that preserves the previous
association interval.

## 11. Provider failure and mock boundary

- Every provider attempt records provider ID, source metadata, retrieval time, coverage,
  status and safe errors.
- All-provider failure produces `unresolved` plus `provider_unavailable`; it never produces
  a fake candidate or HTTP 200 success payload with invented facts.
- Partial provider success can return candidates only when each proposed fact has evidence
  and limitations.
- Fixture/mock candidates are marked `demo|test`, accepted only in non-production contract
  tests, and are never confirmable as production evidence.

## 12. Stage 1 exit criteria

Stage 1 cannot enable `identity_v1` until:

- the deep-workflow audit is present and reconciled;
- the Supabase Auth `auth.users.id` to `workspace_members.user_id` principal contract is
  covered by authorization tests;
- all state transitions, forbidden operations and idempotency behavior have contract tests;
- cross-tenant/RLS tests pass on a disposable database;
- candidate review requires visible human confirmation;
- no automatic destructive merge exists;
- real-provider acceptance is distinct from fixtures;
- existing Consumer/SavedCase behavior remains regression-tested and unchanged.
