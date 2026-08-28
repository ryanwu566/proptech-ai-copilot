# VNext API Contract v1

Status: Stage 0 interface/OpenAPI skeleton; no `/v1` route is implemented

## 1. Conventions

- Base path: `/v1`.
- JSON request/response uses `snake_case`, UTF-8 and RFC 3339 UTC timestamps.
- Resource IDs are opaque server-issued UUIDs. Clients must not infer tenancy or type from IDs.
- Supabase Auth is the VNext authentication source. The caller supplies a bearer access token;
  FastAPI remains the primary application API/BFF and resolves the canonical principal from
  `auth.users.id` UUID after token validation.
- Every tenant request resolves `workspace_id` from a path/body/context value and verifies
  `workspace_id + active workspace_members.user_id = auth.users.id + allowed role`. A header
  alone and `TO authenticated` alone never grant tenant access.
- Consumer and Professional modes use these same endpoints/domain services. Mode changes
  presentation, density and allowed modules; it does not create another backend.
- Documents, contacts, ownership/title data and private CRM notes require purpose-specific
  FastAPI operations. Their base tables/objects are not directly exposed to the browser.
- `X-Correlation-ID` may be supplied; the server returns a normalized safe request ID.
- Mutations require `Idempotency-Key` where specified and support optimistic concurrency with
  a version/ETag for state transitions.
- Responses never contain database URLs, storage paths, credentials, SQL, stack traces, raw
  provider bodies or unrestricted document/contact/title data.
- Status/coverage/limitations are data, not optional presentation hints.

## 2. Resource summaries

```text
PropertyResolution
  resolution_id, workspace_id, state, input, normalized_input
  candidates[], conflicts[], provider_attempts[]
  selected_candidate_id, confirmed_property_entity_id
  version, created_by, created_at, updated_at

Property
  property_entity_id, workspace_id, lifecycle_state, display_label
  confirmation_summary, version, created_at, updated_at

PropertyGraph
  property, nodes[], relations[], as_of, next_cursor

Case
  case_id, workspace_id, purpose, status, title
  property_entity_id?, identity_status
  assigned_member_id?, version, opened_at, updated_at, closed_at?
```

All evidence uses the DTO in `evidence-architecture-v1.md`. Provider attempts expose bounded
metadata/status/errors, not raw payloads.

## 3. Endpoint contract

### `POST /v1/property-resolutions`

Creates a resolution request. Requires workspace create permission and `Idempotency-Key`.

```json
{
  "workspace_id": "uuid",
  "input": {"kind": "address", "value": {"text": "..."}},
  "case_id": null
}
```

Returns `202 Accepted` with a `PropertyResolution` in `received|normalizing`, or `201 Created`
only if synchronous deterministic work has already produced a persisted non-confirmed state.
It never returns `confirmed` without the confirm command.

### `GET /v1/property-resolutions/{id}`

Returns `200` for an authorized workspace member. Candidates, conflicts, evidence summaries
and provider attempt statuses are included according to role/sensitivity. Cross-tenant IDs
return the product's non-enumerating permission/not-found policy.

### `POST /v1/property-resolutions/{id}/confirm`

Requires `Idempotency-Key`, current `version`, authorized role and explicit candidate.

```json
{
  "candidate_id": "uuid",
  "version": 3,
  "confirmation_reason": "user_verified_against_displayed_evidence"
}
```

Returns `200` with the confirmed resolution and property reference. The transaction creates
or links the PropertyEntity, approved graph relations and audit event atomically. Ambiguity,
stale/conflicting evidence, role failure or version conflict fails closed.

### `POST /v1/property-resolutions/{id}/reject`

Requires idempotency and version. Rejects one candidate or closes the resolution with a
bounded reason. Rejected candidates/evidence remain immutable.

```json
{"candidate_id": "uuid-or-null", "version": 3, "reason_code": "not_same_property"}
```

### `GET /v1/properties/{id}`

Returns the authorized property aggregate, confirmation summary and current lifecycle state.
It does not flatten all address/parcel/building/listing facts into one alleged authoritative
record.

### `GET /v1/properties/{id}/graph`

Supports `as_of`, `relation_type`, `status`, `cursor` and bounded `limit`. Returns typed nodes
and temporal relations with evidence references. Default view is current open confirmed and
disputed edges; history requires an explicit query and permission.

### `GET /v1/properties/{id}/evidence`

Supports `fact_type`, `status`, `effective_at`, `cursor` and bounded `limit`. Returns allowlisted
Evidence DTOs ordered by fact/effective/retrieval time. Raw artifacts require a separate
authorized document operation.

### `POST /v1/cases`

Requires workspace create permission and `Idempotency-Key`.

```json
{
  "workspace_id": "uuid",
  "purpose": "buy_due_diligence",
  "title": "...",
  "property_entity_id": null,
  "legacy_import": null
}
```

Returns `201`. `property_entity_id`, when supplied, must be a confirmed property in the same
workspace. A Case may be created without it.

### `POST /v1/cases/{id}/attach-resolution`

Requires idempotency, case `version`, assignment/role permission and a confirmed resolution
from the same workspace.

```json
{"resolution_id": "uuid", "case_version": 2}
```

Returns `200` with updated Case. It appends attachment history and audit; it does not rewrite
legacy browser data or delete the prior property/relationship history.

## 4. Error contract

```json
{
  "error": {
    "code": "ambiguous_identity",
    "message": "Identity requires confirmation.",
    "request_id": "safe-correlation-id",
    "retryable": false,
    "details": {"resolution_id": "uuid", "conflict_codes": ["provider_disagreement"]}
  }
}
```

`message` is safe and localizable. `details` is an allowlisted schema per code; it never
contains raw input/provider/SQL/exception data.

| Code | HTTP | Meaning |
| --- | --- | --- |
| `provider_unavailable` | 503 | Required provider attempt failed/not configured and no supportable result exists |
| `coverage_unavailable` | 422 or 503 | Source does not cover the input (`422`) or coverage service cannot be determined (`503`) |
| `ambiguous_identity` | 409 | Confirmation/consequential action blocked by candidate ambiguity |
| `permission_denied` | 403 | Authenticated principal lacks tenant/resource operation permission |
| `authentication_required` | 401 | Supabase token is missing, invalid, expired or cannot resolve `auth.users.id` |
| `stale_evidence` | 409 | Operation requires fresher evidence |
| `conflicting_evidence` | 409 | Material conflict blocks the requested operation |
| `unsupported_input` | 422 | Input kind/shape/provider policy is unsupported |
| `validation_failed` | 422 | Bounded field validation failure |
| `not_found` | 404 | Resource absent or hidden under non-enumeration policy |
| `version_conflict` | 409 | ETag/version no longer current |
| `idempotency_conflict` | 409 | Same key reused with a different canonical request |
| `rate_limited` | 429 | Bounded server/provider limit reached; optional safe retry metadata |
| `maintenance` | 503 | Mutation disabled under maintenance mode |

Provider failure is never `200 OK` with a fake result. When at least one provider supplies a
real limited result, the resolution resource may persist as `partially_resolved` with each
failed attempt visible; status and coverage must prevent false completeness.

## 5. Idempotency contract

Required for:

- resolution create/confirm/reject;
- Case create and resolution attachment;
- document upload initialization/completion;
- title procurement;
- CRM activity creation;
- exports;
- AI run and approval;
- merge/split proposals and approvals.

Rules:

1. Key is an opaque client-generated value of bounded length/charset, sent only in the
   `Idempotency-Key` header. It must not contain user/property/contact data.
2. Server scope is `(workspace_id, actor_id, method, canonical_route, key_hash)`.
3. Server stores canonical request hash, operation status, response reference, creation and
   expiry. It does not store secrets/raw documents in the idempotency record.
4. Same key + same canonical request returns the original status/resource/response semantics
   and does not repeat side effects.
5. Same key + different request returns `409 idempotency_conflict`.
6. An in-progress duplicate returns the original operation reference and retry guidance.
7. Minimum replay window is 24 hours for ordinary mutations; procurement/export/AI job windows
   are set by business/financial risk and may be longer. Audit retention is independent.
8. Provider retry is internal to the original operation and never changes the user's
   idempotency identity.

Database uniqueness enforces the scope. Confirm/attach also lock or compare the current
resource version so two different keys cannot approve competing transitions.

## 6. Audit and activity coupling

Every successful or denied consequential mutation has one request ID. The domain transaction
stores the durable state and its required audit event atomically where possible. The event
records actor, workspace, operation, subject, timestamp, source, outcome, idempotency hash and
before/after references. It does not store raw before/after documents. User-visible Activities
are separate records and can be appended through an outbox/worker after commit without
weakening the security audit.

Audit-required operations include identity confirmation, merge/split, membership/role change,
document upload/access/share, title purchase, CRM edit, assignment, export and AI approval.

## 7. Pagination, concurrency and caching

- List/graph/evidence endpoints use opaque cursor pagination and bounded limits; no offsets for
  unbounded tenant datasets.
- Resource responses include `version` and/or ETag. Mutations supply expected version.
- Tenant/private/provider-dependent responses are `private, no-store` unless a separately
  approved cache contract exists.
- Public aggregates remain under existing market/valuation cache and semantics; VNext does not
  change them.

## 8. OpenAPI skeleton

This is an interface sketch, not mounted in the running application:

```yaml
openapi: 3.1.0
info:
  title: PropTech AI Copilot VNext API
  version: 1.0.0-stage0
paths:
  /v1/property-resolutions:
    post:
      operationId: createPropertyResolution
      parameters: [{ $ref: '#/components/parameters/IdempotencyKey' }]
      responses: {'201': {description: Persisted}, '202': {description: Accepted}, '422': {description: Unsupported input}, '503': {description: Provider unavailable}}
  /v1/property-resolutions/{id}:
    get: {operationId: getPropertyResolution, responses: {'200': {description: Resolution}, '404': {description: Not found}}}
  /v1/property-resolutions/{id}/confirm:
    post:
      operationId: confirmPropertyResolution
      parameters: [{ $ref: '#/components/parameters/IdempotencyKey' }]
      responses: {'200': {description: Confirmed}, '409': {description: Ambiguous, stale, conflicting, or version conflict}, '403': {description: Permission denied}}
  /v1/property-resolutions/{id}/reject:
    post:
      operationId: rejectPropertyResolution
      parameters: [{ $ref: '#/components/parameters/IdempotencyKey' }]
      responses: {'200': {description: Rejected or unresolved}, '409': {description: Conflict}}
  /v1/properties/{id}:
    get: {operationId: getProperty, responses: {'200': {description: Property}, '404': {description: Not found}}}
  /v1/properties/{id}/graph:
    get: {operationId: getPropertyGraph, responses: {'200': {description: Graph}}}
  /v1/properties/{id}/evidence:
    get: {operationId: getPropertyEvidence, responses: {'200': {description: Evidence page}}}
  /v1/cases:
    post:
      operationId: createCase
      parameters: [{ $ref: '#/components/parameters/IdempotencyKey' }]
      responses: {'201': {description: Case created}, '409': {description: Idempotency conflict}}
  /v1/cases/{id}/attach-resolution:
    post:
      operationId: attachCaseResolution
      parameters: [{ $ref: '#/components/parameters/IdempotencyKey' }]
      responses: {'200': {description: Attached}, '409': {description: Resolution/state conflict}, '403': {description: Permission denied}}
components:
  securitySchemes:
    SupabaseBearer:
      type: http
      scheme: bearer
      bearerFormat: JWT
  parameters:
    IdempotencyKey:
      name: Idempotency-Key
      in: header
      required: true
      schema: {type: string, minLength: 16, maxLength: 128}
security:
  - SupabaseBearer: []
```

Stage 1 must expand this into executable schemas/examples and contract tests before mounting
routes. It must not implement beyond the approved feature gate.
