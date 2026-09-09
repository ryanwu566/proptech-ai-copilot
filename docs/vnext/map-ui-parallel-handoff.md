# Parallel Map UI Track handoff

Status: frontend component preparation only. This is not the integrated Map Workspace release.

## Scope and components

This track adds a reusable, provider-neutral presentation layer under
`frontend_next/components/vnext-map/`:

- `MapWorkspace` owns presentation-only selection, layer visibility, viewport zoom, and the
  deterministic loading demonstration.
- `CaseContextHeader` keeps Workspace, Case, optional PropertyEntity, review stage, and purpose
  visible above the map.
- `ParcelReviewList` shows current parcel candidates separately from reviewed working geometry.
- `InvestigationMap` is a synthetic SVG investigation surface with selectable parcel features,
  non-provider overlays, viewport metadata, and keyboard controls.
- `LayerControls` changes local visibility without changing evidence or identity state.
- `MapLegend` exposes title, observation status, synthetic authority, and attribution for every
  visible layer.
- `EvidencePanel` keeps source, coverage, timestamp, attribution, evidence reference, limitations,
  and unknown-safe state semantics beside the map.
- `ObservationStatusBadge` provides consistent present, unknown, unavailable, partial-coverage,
  stale, and no-match presentation.

Local styling is contained in `map-workspace.module.css`. No shared stylesheet, locale file,
homepage, global navigation, backend, migration, or production-readiness file was changed.

## Frontend presentation contract

`frontend_next/lib/vnext-map-preview/contract.ts` defines a presentation/view-model boundary. It
mirrors the committed `MapWorkspaceContract` concepts without claiming to be a network DTO:

| Spatial contract concept | Frontend view-model |
| --- | --- |
| Workspace and Case | `CaseContextViewModel` |
| optional PropertyEntity | `selectedPropertyEntity` |
| candidate parcel geometry IDs | `candidateParcels[].geometryId` |
| confirmed parcel geometry IDs | `confirmedParcels[].geometryId` |
| selected layers | local `Set<string>` seeded by `selectedByDefault` |
| legend | `MapLegendItemViewModel`, projected from visible layers |
| observations / Evidence | `observationIds` and per-layer `evidenceId` |
| attribution | per-layer `attribution` and `sourceLabel` |
| limitations | layer limitation plus workspace-level `limitations` |
| viewport | bounded EPSG:4326 `MapViewportViewModel` |
| feature selection | local `MapFeatureSelectionViewModel` |

The view-model is intentionally stricter than ad hoc component props, but it is not a production
API or persistence contract. A selected feature must remain attached to a visible layer; hiding
that layer clears only the local inspection focus.

## Synthetic fixture boundary

`frontend_next/lib/vnext-map-preview/fixtures.ts` is the sole data source. Its IDs, labels,
coordinates, dates, parcel shapes, authorities, observations, and coverage states are deterministic
demo values. The preview makes no request and uses no external tile, address, customer record,
credential, production session, geocoder, Supabase client, or provider adapter.

The screen labels the fixture `Synthetic / Demo data` and `Development-only preview`. Fixture
authority is always `synthetic`; it is never presented as verified or production-authoritative.

## Preview route and production exclusion

The local component preview is:

```text
http://127.0.0.1:3102/dev/spatial-map-preview
```

Run it from `frontend_next`:

```powershell
npm.cmd ci
npm.cmd run dev -- --hostname 127.0.0.1 --port 3102
```

The page calls `notFound()` whenever `NODE_ENV` is not `development`, is marked `noindex`, and is
not linked from the homepage or normal navigation. The production browser gate starts the built
application on owned port 3103 and asserts an HTTP 404 for the preview route.

## Candidate versus reviewed behavior

Candidate parcel shapes use dashed violet boundaries and explicit `Candidate · inspect only`
language. Reviewed working geometry uses a solid green boundary and remains in a separate group.
Selection changes only `MapFeatureSelectionViewModel` in React memory. It cannot confirm parcel
identity, create a PropertyEntity, create a CasePropertyLink, prove ownership or a legal boundary,
or establish safety. The evidence rail repeats this boundary after every selection.

## Unknown-safe observation behavior

The preview keeps these states visibly distinct:

- `unknown`: truth cannot be determined;
- `unavailable`: the synthetic provider cannot currently answer;
- `partial_coverage`: a result exists with a material uncovered edge;
- `stale`: a historical result exists outside freshness policy;
- `no_match`: matching failed but absence was not proven;
- `present`: an observation exists only within its stated fixture coverage.

Evidence remains in the rail when a map layer is hidden. The empty-layer warning states that no
visible feature never means safe, no risk, or proven absence.

## Responsive and accessibility behavior

- Native buttons and checkboxes have visible focus treatment and mobile touch targets.
- SVG parcel polygons expose button semantics, descriptive labels, pressed state, and Enter/Space
  selection.
- Layer controls retain native Space-key behavior.
- Selection, visibility, loading, and completion changes are announced through a polite live region.
- Evidence disclosures expose `aria-expanded` and `aria-controls`.
- Map busy state uses `aria-busy`; its loading panel uses a live status.
- Desktop uses a Case header, control rail, map work surface, and sticky evidence rail. Tablet moves
  evidence below the work surface. The 390 px layout uses a single-column flow without horizontal
  overflow.
- Motion is reduced when `prefers-reduced-motion` is active.

## Tests

Focused browser coverage is in `frontend_next/e2e/spatial-map-preview.spec.ts`. The owned runner
records and terminates only the frontend process tree that it starts, so it does not reuse or stop
another track's service.

Development component/browser checks:

```powershell
cd frontend_next
node scripts/run-spatial-map-preview-e2e.cjs
```

Production exclusion after `npm.cmd run build`:

```powershell
$env:SPATIAL_PREVIEW_E2E_TARGET = "production"
node scripts/run-spatial-map-preview-e2e.cjs
Remove-Item Env:SPATIAL_PREVIEW_E2E_TARGET
```

The browser suite covers synthetic labeling and Case context, parcel selection, candidate/reviewed
distinction, layer toggles and retained evidence, unknown/unavailable/partial/stale/no-match states,
loading, keyboard interaction, selection clearing, 390 px behavior, homepage/navigation absence,
and production HTTP 404 exclusion.

Additional gates:

```powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
git diff --check
```

## Backend adapter still required

An integrated release still needs an approved, authenticated adapter that:

1. returns a tenant- and purpose-authorized projection of the provider-neutral spatial contracts;
2. validates Workspace, Case, optional PropertyEntity, parcel reference, Evidence, and feature-layer
   relationships server-side;
3. maps every provider result into the existing bounded observation and coverage states without
   collapsing unknown, unavailable, no-match, partial, stale, or error outcomes;
4. preserves Evidence IDs, source/environment/authority, timestamps, license/attribution,
   transformations, coverage gaps, and limitations;
5. keeps credentials, raw provider payloads, private storage paths, and internal errors out of the
   browser;
6. exposes explicit identity-review commands separately from map inspection; and
7. defines reviewed persistence for Case map preferences or Activities before any client save action
   is enabled.

No endpoint shape, database object, or persistence behavior is invented in this track.

## Stage 2A Slice boundaries

The ongoing Slice 1 backend work remains independent and authoritative for its approved server-side
scope. This frontend must wait for that work's reviewed authorization, DTO, Evidence projection,
and failure semantics before replacing the synthetic fixture with an adapter.

Any later Slice 2 integration must separately approve authenticated route wiring, Case continuity,
workspace authorization, persistence/audit behavior, error and retry policy, contract tests, and the
handoff into explicit human identity review. This preview does not start or pre-approve that work.

## NLSC Stage 2B boundary

NLSC integration remains entirely outside this track. Stage 2B must first approve the exact dataset
and endpoint, authorization, license and attribution, CRS/version, coverage, refresh cadence, quota,
and failure acceptance. Until then, no NLSC adapter, credential, request, tile, emulation, scraped
response, or verification claim belongs in these components or fixtures.

## Production impact

NONE. The preview is development-only, unlinked, provider-free, non-persistent, and HTTP 404 in a
production build.
