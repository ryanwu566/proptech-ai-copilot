# Professional GIS Workspace V1 Design

## Purpose

Turn the Professional Workspace Parcel/GIS area into a truthful, read-only investigation surface backed by the authorized Case Parcel Set GET contract and the currently loaded PropertyEntity graph page. The surface must expose review state without implying approved geometry, Case-to-Property attachment, canonical Property Identity, or legal parcel boundaries.

## Existing Boundaries

- The route supplies only a Case UUID reference. Case details are not loaded.
- The existing shell separately authorizes a Workspace and loads a PropertyEntity, graph page, and Evidence page.
- No approved read proves that the route Case is attached to the loaded PropertyEntity.
- `GET /v1/cases/{case_id}/parcel-set` is feature-gated and authorized by the backend. Its 404 response intentionally does not distinguish feature unavailability, resource absence, and other fail-closed cases.
- Parcel Set mutations exist in the backend but are outside this frontend slice.
- No approved professional parcel geometry or TILE_001 integration is available.

## Read Sequence and Failure Model

The shell retains its current sequence:

1. Validate route and query UUIDs without a backend request when invalid.
2. Read the authorized Workspace.
3. Read the PropertyEntity and require its `workspace_id` to equal the authorized Workspace.
4. Only after those reads and that binding succeed, issue bounded graph, Evidence, and Case Parcel Set GET reads in parallel.
5. Require graph and Evidence workspace bindings exactly as today.
6. Require the Parcel Set `workspace_id` to equal the authorized Workspace and its `case_id` to equal the route Case reference.

Graph or Evidence failure continues to fail the approved context load. Parcel Set failures are represented inside the loaded context so an unavailable parcel resource does not erase valid Identity and Evidence context:

- 404: `not_available`, with deliberately ambiguous copy.
- 403 or permission-denied envelope: `denied`.
- missing/expired session: `session_error`.
- missing frontend configuration: `configuration_error`.
- invalid JSON, malformed DTO, Case mismatch, or Workspace mismatch: `invalid_response`.
- transport or infrastructure failure: `error`.
- valid DTO, including zero members: `ready`.

No failure state is converted to an empty Parcel Set.

## Contract

Create a focused Case Parcel Set contract module. It accepts only the documented root and member fields and returns a typed DTO with no arbitrary JSON. It validates:

- UUID fields and ISO timestamps;
- `draft | case_reviewed` set status;
- `candidate | case_selected | case_rejected` member review status;
- version at least 1;
- positions from 1 through 100;
- at most 100 members;
- unique member IDs, parcel reference IDs, and positions;
- members already strictly ordered by increasing position;
- non-null `active_member_id` names a returned member;
- exact Case and Workspace response bindings.

The parser does not sort or otherwise repair malformed member ordering. Because positions are unique, the backend's member-ID tie-break never needs to select between equal positions on the frontend.

## Client Surface

Add one `caseParcelSet(caseId, workspaceId)` method to the existing authenticated VNext client. It performs only `GET /v1/cases/{caseId}/parcel-set`, uses the existing bearer-session flow, validates both expected IDs through the contract parser, and exposes no Parcel Set command or mutation method.

## Graph Cross-reference

For every Parcel Set member, inspect only the loaded graph page and match only nodes where:

```text
node.node_type === "parcel"
AND
node.record_id === member.parcel_identity_reference_id
```

Outcomes are:

- zero matches: `missing`, displayed as “Reference not present in the loaded PropertyEntity graph page.”
- one match: `matched`, displayed as “Also present in the currently loaded PropertyEntity graph page.” with only display label, reference status, source ID, and source environment;
- more than one match: `ambiguous`, with no node chosen and no metadata disclosed.

Display label, status, source, relation order, and member order never participate in selection. A graph cursor produces the visible disclosure “Additional graph records are available; parcel cross-reference may be incomplete.” Missing and ambiguous matches remain non-authoritative.

## Readiness and Presentation

Parcel/GIS is `NOT_AVAILABLE` until a valid, authorized Parcel Set is loaded. Once loaded it is always `PARTIAL`, including with zero members, because professional parcel geometry remains unavailable.

The Map Canvas becomes a neutral investigation canvas with no Leaflet component, tiles, marker, coordinates, SVG geometry, or inferred location. It presents:

- set status and version;
- active member as a separate review-focus attribute;
- ordered member list and Case-local review status;
- graph cross-reference outcome and bounded matched metadata;
- graph pagination warning;
- geometry `NOT_AVAILABLE` state;
- the canonical/legal disclaimer;
- the Case-to-Property binding limitation.

The existing Evidence Rail remains unchanged because the current typed Evidence page does not prove an exact Parcel Set linkage.

## Truth Boundaries

The visible surface must state:

> Case parcel review state does not confirm canonical Property Identity or legal parcel boundaries.

When Parcel Set data is shown it must also state:

> Case-to-Property binding is not available from an approved read in this workspace slice.

`case_selected` is a Case-local review status only. `active_member_id` is review focus only and is independent of every member review status. Neither status proves a canonical identity, Case-to-Property attachment, current legal parcel, or legal boundary.

## Accessibility and Responsive Behavior

Use semantic headings, description lists, and ordered lists. Readiness, review, active, match, and geometry states are visible text rather than color-only signals. Existing module buttons retain keyboard focus and pressed state. Layouts wrap identifiers and collapse to one column without horizontal overflow at the existing 390px mobile viewport.

## Verification

Add pure contract/view-model tests and Professional Workspace browser tests for success, failure, binding, ambiguity, pagination, truth boundaries, request methods/hosts, secrets, keyboard navigation, and mobile overflow. Run existing Workspace, VNext identity/auth, Case Parcel Set, hardening, Python regression, typecheck, lint, production build, and retry-disabled browser coverage. No migrations, dependencies, providers, pushes, or merges are permitted.
