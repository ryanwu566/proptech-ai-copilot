# Journey Property Identity Anchor Design

## Purpose

Expose a bounded property identity anchor in the current browser journey so Location, Market, Valuation, Terrain, Finance, Decision, and saved-case evidence can be understood as referring to the same selected property context. This anchor is not a cadastral identifier, government property ID, legal parcel identity, or durable VNext `PropertyEntity`.

## Existing architecture

The repository already has two distinct identity surfaces:

- The current production journey in `frontend_next/app/page.tsx` carries a `JourneyPropertyContext`, location evidence, downstream analyses, and browser-saved cases. `updateJourneyProperty` already clears location, terrain, market, valuation, and affordability evidence when the address changes.
- VNext has durable authenticated property entities, candidate resolutions, evidence, manual decisions, case attachments, parcel hypotheses, building claims, parcel-building relations, and case-local parcel review. Its production resolution engine deliberately has no approved providers, its feature flags default off, and manual parcel/building records remain unverified proposals.

Location Insight is the production-safe bridge for the browser journey. It already carries accepted normalized address evidence, coordinates, geocoding provenance, and canonical NLSC village name/code. It must be reused rather than invoking independent geocoding or village logic.

## Boundary and naming

The new contract is named `JourneyPropertyIdentityAnchorV1` and always contains:

- `scope: "journey_browser_anchor"`
- `version: 1`
- a locally generated `journey_anchor_id` prefixed `journey-browser-`
- copy and limitations that state it is a workflow correlation aid only

The ID is opaque and persists only with the journey or browser-saved case. It is never sent to, substituted for, or described as a durable VNext entity ID.

## Contract

The anchor stores only bounded normalized fields:

- input and normalized address
- latitude and longitude when accepted Location Insight resolved them
- city, district, village, and village code
- address/location status
- independently bounded parcel and building projections
- domain-specific confidence category and basis
- bounded provenance sources and checked time
- limitations
- revalidation state and explicit conflict reasons

Status vocabulary is explicit. Address/location may be `candidate`, `unresolved`, `unavailable`, `unsupported`, `error`, or `stale`. Parcel/building may be `candidate`, `manual_confirmed`, `unresolved`, `unavailable`, `restricted`, `unsupported`, or `error`. A manually confirmed candidate records method, time, and source candidate, but never acquires government or cadastral authority wording.

Parcel and building default to `unavailable` with limitations explaining that no approved resolver supplied evidence. Address-level analysis remains fully usable in that state.

## Confidence

Anchor confidence is one of `high`, `medium`, `low`, or `unknown` and applies only to correlation of address-level spatial evidence:

- `high`: normalized address, coordinates, city/district, resolved NLSC village code, and trusted geocoding provenance are mutually available.
- `medium`: normalized address and accepted coordinates are available, but village identity or trusted provider provenance is incomplete.
- `low`: only normalized user/property-selection address and administrative context are available.
- `unknown`: no usable address identity exists or stored and fresh evidence conflict.

Every confidence value carries a limitation stating that it does not confirm parcel, building, ownership, title, or legal boundary identity. Parcel and building status never inherit anchor confidence.

## Projection and provenance

`buildJourneyPropertyIdentityAnchor` projects only from `JourneyPropertyContext` and the normalized surface of `LocationInsightResult`. It does not retain raw provider payloads, POIs, demographics, internal scoring, credentials, or configuration.

Allowed source records contain a bounded source ID, evidence kind, and checked time. Geocoding source comes from the accepted geocoding contract. Village provenance comes from `nlsc_village_boundary` only when village resolution is `resolved`.

## Saved-case reconciliation

Browser-saved cases persist the anchor separately from compacted Location Insight. Reopening restores the stored anchor and its provenance exactly after contract normalization.

When fresh Location Insight is later resolved, `reconcileJourneyPropertyIdentityAnchor` compares:

- normalized address after Unicode/whitespace normalization when both sides provide it;
- coordinates using a 100-metre conflict threshold, allowing harmless provider precision differences;
- resolved village code when both sides provide it.

If any comparison conflicts, the stored anchor and stored provenance remain visible, `revalidation.status` becomes `needs_revalidation`, address/location status becomes `stale`, confidence becomes `unknown`, and the conflict fields are recorded. Fresh values do not silently replace stored values. If comparable evidence agrees, the same journey anchor ID is preserved and bounded fields/provenance may be refreshed.

## Journey state and stale evidence

Selecting a different address creates a new browser-scoped anchor and clears the prior anchor plus Location, Market, Terrain, Valuation, Loan, Holding Cost, and Tax evidence. Property-search output is also cleared when it no longer identifies the active selection. Address-level anchor creation does not wait for parcel or building evidence.

## UI

A small reusable identity card appears in the Location stage and Decision stage. It shows:

- “Journey property identity” and the non-authoritative scope notice
- address and administrative location
- village or its explicit unavailable state
- parcel and building status independently
- address-level confidence and its limitation
- bounded sources
- stale/revalidation warning when applicable

It uses existing card styling and does not redesign the workflow.

## Tests and rollout boundary

Tests cover contract projection, confidence, conservative parcel/building defaults, bounded persistence, reopen reconciliation, stale conflicts, property-switch clearing, UI copy, and address-level workflow continuity. Existing VNext backend, parcel/building relation, Property Case, TypeScript, build, and relevant Playwright suites are regression-tested.

No feature flag, provider, authentication, durable identity table, production configuration, deployment setting, or live service is changed.
