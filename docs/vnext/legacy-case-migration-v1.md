# Legacy SavedCase Migration v1

Status: Stage 0 compatibility contract; no browser or server migration is implemented

## 1. Current code is authoritative

The current frontend `SavedCase` contract is version 1 and is stored only in browser
`localStorage` under:

```text
proptech.savedCases.v1
```

The storage module caps the list at 10, compacts provider details, removes raw comparable and
location details, converts terrain results into a bounded reference object, and uses
`sessionStorage`/browser events when loading a Case. Save, load, compare, delete, clear and
browser print/export behavior are existing production behavior and remain unchanged.

Some active documentation names a different historical key. The current code above governs
VNext compatibility.

## 2. Decision

```text
SavedCase v1 in browser
        |
        | explicit, optional user import
        v
Legacy Import Adapter
        |
        v
Durable Case with identity_status=legacy_unverified
        |
        | optional resolution -> candidates -> human confirmation
        v
Confirmed Property attachment
```

The adapter does not replace, rewrite, delete or mark the local object imported. Import is a
copy initiated by the user. The original can continue to load, compare and print through the
current UI.

## 3. Compatibility invariants

- Do not change `SAVED_CASES_STORAGE_KEY`, `SavedCase.version`, `workflowMode`, event names,
  maximum count or compacting behavior in Stage 0/1.
- Do not auto-upload localStorage contents, enumerate them server-side or send them for
  identity resolution without explicit selection and consent.
- Do not add server identifiers or import status to the v1 object.
- Do not treat its address, title, generated case ID, coordinates, terrain summary or valuation
  as canonical property identity.
- Existing compare/report/print continues to read v1 objects exactly as today.
- Missing values remain missing. `0` is not used to stand for unknown data.
- Import failure cannot corrupt or remove the local object.
- VNext API and database changes are additive and feature-gated off by default.

## 4. Legacy import DTO

Future conceptual request:

```json
{
  "workspace_id": "uuid",
  "legacy_format": "saved_case_v1",
  "legacy_client_id": "opaque-browser-case-id",
  "payload": {},
  "import_mode": "copy",
  "consent": true
}
```

The endpoint is separate from generic Case creation or uses the `legacy_import` field in that
endpoint. It requires authentication, membership, `Idempotency-Key`, size limits and an exact
versioned schema. Extra/raw provider fields are dropped by an allowlist before persistence.

Conceptual response:

```json
{
  "case_id": "uuid",
  "import_status": "imported_unverified",
  "identity_status": "legacy_unverified",
  "property_entity_id": null,
  "resolution_id": null,
  "warnings": ["address_requires_resolution"]
}
```

`legacy_client_id` is an idempotency/dedup reference scoped to user/workspace/format. It is not
a Property ID and should be hashed or minimized when retained.

## 5. Field mapping

| SavedCase v1 source | Durable destination | Evidence/status |
| --- | --- | --- |
| `title` | `cases.title` | user-provided; not identity |
| `createdAt`, `updatedAt` | import metadata and optional legacy timestamps | preserve as client-declared timestamps; server import time remains authoritative |
| `activeWizardStep`, `progress` | optional legacy workflow snapshot/activity | user-provided snapshot; do not force new Case workflow state |
| `inputSummary.city/district/road` and `data.inputs` address parts | Case investigation input + user-provided address evidence | `legacy_unverified` / `unverified`; no PropertyEntity attachment |
| budget/property price/area inputs | Case financial/property notes in approved typed fields | user-provided, not valuation evidence |
| `propertySearch` | optional bounded legacy summary | reference only; matched rows are already compacted and cannot confirm identity |
| `valuationEvidence` and eligible compacted `valuation` | evidence summary linked to Case if schema/status is still valid | preserve source/status/time where present; revalidation required for consequential current use |
| `trend`, `marketInsight` | optional bounded snapshot artifact | stale/unknown freshness unless timestamps/source prove otherwise |
| `loan`, `holdingCost`, `taxOracle` | deterministic/user-input legacy calculation artifact | record rule/input version if present; never recalculate during import |
| `locationInsight` | bounded location summary | resolved coordinates/provider details remain excluded; cannot confirm property |
| `terrainReference` or migrated legacy `terrainRisk` | reference-only evidence summary | unknown/limited/no-match remain conservative; never safe |
| `riskSummary` | legacy presentation artifact only | not authoritative evidence or identity input |
| `reportCompleted` | optional legacy activity | does not mark durable Case complete |
| journey context/notes | Case notes/context after allowlist and size limits | private user-provided data |

Unsupported/extra fields are ignored with a bounded warning; they are not placed into a raw
JSON dump. Raw provider payloads, credentials, errors and exact coordinates remain excluded.

## 6. Import flow

1. User opens the existing saved-case surface. Nothing is uploaded automatically.
2. When the VNext import feature is approved and enabled, user selects one Case and target
   workspace, sees the exact data classes to be copied and confirms.
3. Client creates an allowlisted v1 transfer DTO without mutating localStorage.
4. Server validates schema/version, membership, tenant quota and idempotency.
5. Server presents or records a dry-run summary: fields accepted, dropped, limited and missing.
6. User confirms import; server creates the durable Case and user-provided evidence in one
   transaction, with `identity_status=legacy_unverified` and `property_entity_id=null`.
7. Audit records actor, workspace, new Case, legacy format and request ID without raw payload.
8. Identity resolution is optional and separate. It produces candidates; only explicit human
   confirmation attaches a PropertyEntity.
9. Local v1 Case remains operational and may be deleted only through the existing explicit
   browser action.

## 7. Duplicate and retry behavior

- Import requires `Idempotency-Key` and a canonical payload hash.
- Same key/payload returns the original durable `case_id`.
- Same key/different payload returns `idempotency_conflict`.
- A second import with a different key but same scoped `legacy_client_id` returns a duplicate
  preview and requires explicit “create another Case” confirmation.
- Deduplication never merges PropertyEntities and never deletes either Case.

## 8. Identity upgrade

An imported Case stays `legacy_unverified` even when it has an address. The upgrade path is:

```text
legacy_unverified
  -> create property resolution from explicitly selected inputs
  -> candidates_found / ambiguous / partial / unresolved
  -> user confirms one candidate
  -> attach confirmed resolution to Case
  -> identity_status=confirmed with attachment history
```

If resolution is unresolved/ambiguous, the Case continues to function as an unverified Case.
Title procurement, owner linking, CRM binding, merge and other consequential actions remain
blocked.

## 9. Privacy and tenancy

Import is available only to an authenticated member of the target workspace. Full address,
financial inputs, notes and reports are private tenant data. Team import warns that selected
members may gain access under team policy. Sensitive documents are not part of SavedCase v1;
future uploads use the private Artifact/Storage contract.

The server never requests all localStorage keys or browser history. Telemetry records only
bounded operation status, not payload/address/price/notes. Exports and deletion follow Case
and workspace retention policy after import; deleting a browser copy does not delete the
durable copy and vice versa.

## 10. Rollout and rollback

1. Ship DTO/adapter tests with feature flag off.
2. Validate representative sanitized v1 fixtures including corrupt/partial/terrain legacy
   shapes; fixtures do not contain real customer data.
3. Enable only in an isolated test/personal workspace after Auth/RLS passes.
4. Compare imported Case display against the original without changing comparison/report.
5. Roll back by disabling the import flag/API. Durable imports already created remain ordinary
   Cases and are not deleted automatically; local v1 data is unaffected.

## 11. Acceptance criteria

- Existing SavedCase save/load/compare/delete/print tests pass unchanged.
- No localStorage schema/key mutation and no automatic upload occurs.
- Address-only imports have `legacy_unverified` and no PropertyEntity.
- Unknown/unavailable/partial legacy states remain conservative.
- Raw coordinates/provider rows/errors/secrets are not imported.
- Retry/dedup creates no duplicate side effect and performs no property merge.
- Cross-workspace import/read/update is denied.
- Import disable/rollback leaves existing Consumer behavior intact.
