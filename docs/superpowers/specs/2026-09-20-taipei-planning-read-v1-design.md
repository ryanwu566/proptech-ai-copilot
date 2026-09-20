# Taipei Planning Read V1 Design

**Date:** 2026-09-20
**Repository:** `proptech-taipei-planning-runtime`
**Branch:** `feature/taipei-planning-read-v1`
**Decision:** Implement a manual official-document-reference seam only.

## Purpose

Establish the smallest truthful runtime foundation for investigating Taipei
City statutory planning evidence without presenting manually entered metadata
as verified statutory truth. The slice introduces a strict evidence vocabulary,
a fail-closed feature boundary, and one read-only normalization endpoint.

The runtime will accept a bounded reference to one of two kinds of official
Taipei City planning documents. It will normalize the reported metadata as
`USER_PROVIDED`, `LIMITED`, and `unverified`. It will not fetch, scrape, upload,
store, verify, or bind the document to a PropertyEntity or Case.

## Non-goals

This slice does not provide:

- live zoning lookup by parcel, lot number, address, coordinate, or map point;
- current statutory zoning or legal-effect confirmation;
- parcel identity or parcel-to-document confirmation;
- FAR, BCR, permitted-use, buildability, entitlement, ownership, development
  approval, investment advice, or legal advice;
- artifact upload, document parsing, document storage, persistence, audit writes,
  database reads, background work, browser requests, provider requests, or NLSC
  calls;
- Yangmingshan National Park or any jurisdiction outside Taipei City;
- frontend changes or integration with the concurrent Professional GIS work.

## Gate 0 Source Audit

### Competent authority

The competent local source owner for this slice is the Taipei City Department
of Urban Development (`Taipei UDD`). The runtime must use this full authority
name and must not accept a caller-supplied authority.

### Reviewed official sources

| Source | Geography | Inputs | Format and access | Legal meaning | Version/update semantics | Terms and constraints |
| --- | --- | --- | --- | --- | --- | --- |
| Taipei City Land Use Zoning open dataset | Taipei City parcel-indexed land-use zoning; it does not close the Yangmingshan National Park path | Dataset API supports bounded `q`, `limit`, and `offset`; records contain district/section and mother/sub-lot components | Official CSV download and JSON API over HTTPS | Official open data but expressly reference-only; the publisher directs users to the current query service and says implementation-grade use depends on field/building-line or cadastral demarcation | Six-month cadence; metadata and resource updated 2026-07-01; no controlling plan identifier or legal-effective date per record | Free and public under Open Government Data License v1 with attribution; may change between releases |
| Land Use Zoning Online Query and Certificate System | Taipei City land except Yangmingshan National Park | District, section/subsection, mother/sub-lot; certificate application also involves applicant and payment data | Public manual query; paid application and electronic certificate workflow | An issued certificate is an official authority artifact for its stated subject, purpose, and date, but a caller's reference to one is not independently verified evidence | Current-service workflow; published authority material says certificates have a bounded validity period, which must be read from the artifact in a future verification workflow | No reviewed bulk API; personal/payment workflow; this slice must not automate or scrape it |
| Taipei UDD Urban Plan Announcements | Case-specific Taipei City main plans, detailed plans, and plan-specific controls | Manual case search by title, district, parcel text, announcement date, or case context | Official HTML pages with announcement and plan document downloads | The announcement and its attached promulgated plan artifacts may be authoritative within their scope, but list metadata alone does not prove present legal effect | Event-driven publication; later amendment, supersession, revocation, and even retroactive revocation are possible | No complete reviewed machine-readable applicability/supersession API; this slice must not automate or scrape it |
| Urban Planning Integrated Query System | Taipei City urban-plan area | Manual cadastral/location selection, timeline, and plan case | Public manual Web GIS | Reference and discovery context; not a reusable statutory feature API | Operational and event-driven; no public stable schema/version contract was proven | Public manual access only for this slice; no scraping or undocumented endpoint use |

### Exact runtime decision

The open zoning dataset is machine-readable, but the repository has no safe,
exact, production-accepted parcel input that supplies every component needed
for a precise join. The full-component parcel contract is explicitly an
unverified hypothesis, while the confirmed lot-number resolution contract does
not carry a required district component. The open dataset also lacks a
per-record controlling plan and legal-effective date and disclaims legal use.

Therefore V1 must not call that API. It will expose a manual document-reference
seam only. Provider timeout, non-2xx, malformed-response, and oversized-response
tests are inapplicable because no provider transport exists.

## Evidence and Authority Model

The schema defines these closed authority classes for forward compatibility:

- `AUTHORITATIVE_LOCAL`
- `REFERENCE_ONLY`
- `USER_PROVIDED`
- `NOT_AVAILABLE`

Every successful V1 manual observation sets `authority_class` to
`USER_PROVIDED`. There is no branch, flag, role, document kind, field
combination, or reported date that upgrades it to `AUTHORITATIVE_LOCAL` or
`REFERENCE_ONLY`.

The document can name an official Taipei UDD artifact while the observation
remains user-provided. `issuing_authority` identifies the declared issuer; it
does not describe runtime verification.

`LUI_002` remains a separate `REFERENCE_ONLY` historical or specified-year
land-use survey observation. This Taipei seam neither accepts nor emits
`LUI_002`. Neither source class can become `AUTHORITATIVE_LOCAL` in V1.

## Runtime Configuration

Two independent environment gates are required:

```text
TAIPEI_PLANNING_READ_V1=true
TAIPEI_PLANNING_SOURCE_MODE=manual_evidence
```

`TAIPEI_PLANNING_READ_V1` uses the repository's existing exact truthy-value
parsing and defaults to false. A disabled flag makes the route fail closed as
`404 not_found`, consistent with existing VNext feature routes.

The source mode must equal `manual_evidence` after trimming and lowercasing.
Missing, blank, or any other value makes the route fail closed as bounded
`503 coverage_unavailable`. Safe configuration reporting may expose only
`configured`, `not_configured`, or `malformed`; it must not echo values.

These configuration gates enable the seam but never change evidence authority.

## API Contract

### Route

```text
POST /v1/planning/taipei/observe
```

The route is authenticated by the existing `/v1` router boundary. It requires
no workspace, user identifier, PropertyEntity, Case, idempotency key, or
repository. It is semantically read-only despite using POST for a bounded body.

### Request

```json
{
  "jurisdiction": "Taipei City",
  "scope": "urban_plan_non_national_park",
  "document_kind": "issued_zoning_certificate",
  "reported_document_reference": "reported certificate or announcement identifier",
  "reported_plan_identifier": null,
  "reported_zone_code": null,
  "reported_zone_label": null,
  "reported_effective_date": null
}
```

Rules:

- Models use `extra="forbid"`.
- `jurisdiction` must be the exact literal `Taipei City`.
- `scope` must be the exact literal `urban_plan_non_national_park`.
- `document_kind` is either `issued_zoning_certificate` or
  `official_urban_plan_announcement`.
- `reported_document_reference` is required and bounded to 200 Unicode
  characters after trimming.
- `reported_plan_identifier` and `reported_zone_label` are optional and bounded
  to 200 characters; `reported_zone_code` is optional and bounded to 80.
- Optional blank strings normalize to `null`; the required reference cannot be
  blank.
- Every text value rejects ASCII control characters, NUL, HTML delimiters, URI
  schemes such as `://`, obvious `http://`, `https://`, and `www.` web-address
  prefixes, absolute filesystem paths, and traversal sequences when they form a
  path. Ordinary bounded Unicode identifier text and legitimate certificate or
  announcement punctuation, including non-path slash and backslash characters,
  remain valid data. Values are never interpreted as executable HTML, URLs, or
  filesystem paths.
- `reported_effective_date` is an ISO calendar date or `null`.
- No free-form object, bytes, file, URL, address, coordinate, lot/parcel input,
  credential, token, or user identifier is accepted.

Unsupported jurisdiction, ambiguous jurisdiction, national-park scope, and
unsupported document kinds are rejected as bounded `422` responses. The
endpoint never infers jurisdiction or scope.

### Response

The success DTO is `PlanningObservationV1`:

```json
{
  "status": "LIMITED",
  "jurisdiction": "Taipei City",
  "scope": "urban_plan_non_national_park",
  "authority_class": "USER_PROVIDED",
  "document_kind": "issued_zoning_certificate",
  "issuing_authority": "Taipei City Department of Urban Development",
  "source_portal": "https://zone.udd.gov.taipei/new_index1.aspx",
  "reported_document_reference": "...",
  "reported_plan_identifier": null,
  "reported_zone_code": null,
  "reported_zone_label": null,
  "reported_effective_date": null,
  "coverage_status": "LIMITED",
  "verification_required": true,
  "verification_status": "unverified",
  "limitations": [],
  "normalized_at": "2026-09-20T00:00:00Z",
  "disclaimer": "Planning evidence must be confirmed against the competent local authority and current legally effective plan/certificate."
}
```

The implementation emits only `LIMITED` success observations with
`authority_class=USER_PROVIDED`, `coverage_status=LIMITED`,
`verification_required=true`, and `verification_status=unverified`. The
response schema must not contain FAR, BCR, buildability, ownership,
entitlement, development-approval, parcel-confirmation, PropertyEntity, Case,
or current-statutory-truth fields. V1 never emits a successful `200`
`NOT_AVAILABLE` observation; `NOT_AVAILABLE` remains future schema vocabulary.

`normalized_at` is a server-generated, timezone-aware UTC timestamp describing
normalization time only. It is not a retrieval, observation, document, or
legal-effective timestamp.

### Fixed official source mapping

The server owns this immutable mapping:

| Document kind | Issuing authority | Source portal |
| --- | --- | --- |
| `issued_zoning_certificate` | Taipei City Department of Urban Development | `https://zone.udd.gov.taipei/new_index1.aspx` |
| `official_urban_plan_announcement` | Taipei City Department of Urban Development | `https://udd.gov.taipei/announcement/biwfsm8` |

No request field can select a host, path, authority, or provider.

## Limitations and Legal-effect Semantics

Every success response includes stable, bounded limitations covering:

- manual metadata is unverified and user-provided;
- the reference is not bound to any current PropertyEntity, parcel, or Case;
- no FAR, BCR, buildability, entitlement, ownership, development approval, or
  permitted-use conclusion is produced;
- `LUI_002` is separate reference-only land-use survey evidence and is not
  statutory zoning;
- the fixed disclaimer requires competent-authority confirmation.

Certificate observations additionally state that the runtime has not confirmed
the certificate's authenticity, currency, validity period, applicability to a
loaded property, or coverage of an entire case.

Announcement observations additionally state:

> Current legal effect requires confirmation against later amendments,
> supersession, revocation, and the competent authority.

Supplying `reported_effective_date` only preserves the reported value. It never
changes authority, verification, coverage, status, or limitations.

## Components

### Domain module

A focused `services/vnext/taipei_planning.py` module owns:

- closed enums and immutable source mapping;
- the strict domain request value;
- `PlanningObservationV1` construction;
- bounded text normalization and URL/path/HTML rejection;
- feature/source-mode eligibility checks that are independent of FastAPI;
- the UTC clock injection used by deterministic tests.

It imports no HTTP, browser, NLSC, database, repository, persistence, or job
module.

### API module

`backend/api/v1/taipei_planning.py` owns strict Pydantic request and response
models, dependency wiring, error mapping through the existing VNext error
envelope, and the one POST handler. The VNext router includes this router.

### Feature and production configuration

`services/vnext/feature_flags.py` gains `taipei_planning_read_v1` and reports it
in the bounded `/v1` context. `services/production_config.py` validates only the
source-mode category and adds a value-free safe-report key. `.env.example` and
`render.yaml` document/configure both optional environment variables with the
feature disabled by default.

### Source audit documentation

`docs/vnext/taipei-planning-read-v1-source-audit.md` records the Gate 0 table,
official references, runtime decision, inapplicable transport cases, and
external blockers. It does not claim an official API integration.

## Error Handling

All errors use the existing bounded VNext error envelope and correlation ID.

- Feature disabled: `404 not_found`.
- Source mode missing, blank, or unknown: `503 coverage_unavailable`.
- Unsupported jurisdiction, scope, document kind, extra field, URL/path/HTML
  input, missing reference, invalid date, or oversized text: `422` with no raw
  input echoed.
- Unexpected failures: existing bounded `500 internal_error` handling.

No error includes environment values, submitted text, credentials, exception
text, paths, provider bodies, or stack traces.

## Security and Side-effect Boundary

The implementation must have zero runtime capability for external transport or
persistence. Tests invoke the real endpoint while installing fail-fast sentinels
on the repository's common HTTP clients, browser-facing integration points,
NLSC adapters, database connection entry points, and job enqueue entry points.
Any such call fails the test.

The endpoint accepts no URL or provider selector, so it has no SSRF surface.
The source mapping is immutable and server-controlled. No raw body is logged or
included in error details.

## Test Strategy

Development follows red-green-refactor. Each behavior test must fail for the
intended missing behavior before implementation is added.

Focused tests cover:

- feature flag off and default-off parsing;
- missing, blank, and wrong source mode;
- unsupported and ambiguous jurisdiction;
- Yangmingshan and national-park scope exclusion;
- both accepted document kinds and rejection of every other kind;
- extra URL fields and URL/path/HTML values rejected;
- required and optional text bounds;
- manual certificate and announcement normalization;
- `USER_PROVIDED`, `LIMITED`, `verification_required=true`, and `unverified`
  invariants;
- absence of any verified upgrade path;
- reported effective date preservation without current-effect promotion;
- `normalized_at` is normalization time and no retrieval/observation timestamp
  is exposed;
- success/error semantics are frozen: success is `LIMITED`, invalid input is
  `422`, feature-off is `404`, and unavailable source mode is bounded `503`;
- certificate and announcement-specific limitations;
- response-schema absence of FAR, BCR, buildability, ownership, entitlement,
  approval, parcel confirmation, PropertyEntity, and Case claims;
- explicit `LUI_002` separation;
- zero HTTP, requests, browser fetch, scraping, NLSC, database, persistence,
  audit-write, and background-job calls;
- bounded error payloads with no submitted text or configuration value;
- production safe-report and deployment configuration behavior;
- route method/path and read-only behavior;
- relevant identity/location, source-contract, security, and production-config
  regressions;
- the complete Python suite.

Transport failure-response tests are documented as inapplicable rather than
simulated because the architecture contains no provider transport.

## Delivery Constraints

- Zero migrations and database schema changes.
- Zero new product dependencies.
- Zero frontend files changed.
- At most one commit, ultimately named
  `feat(planning): add Taipei planning read seam`.
- Do not push or merge.
- Independent review must inspect authority promotion, legal-effect overclaim,
  property/case binding, caller-controlled URLs, hidden transport/scraping,
  inference of prohibited planning conclusions, LUI_002 promotion,
  jurisdiction leakage, persistence, and credential exposure.
- Critical and Important review findings are fixed test-first before delivery.

## Acceptance Decision

The slice is a `GO` only if every successful result is visibly user-provided,
limited, and unverified; every unsupported configuration/input fails closed;
the complete test suite passes; independent review has no unresolved Critical
or Important finding; and the final diff contains no migration, frontend,
transport, persistence, or dependency change.
