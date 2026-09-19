# Active Listing Observation Pilot v1

Status: proposed Stage 4 contract; docs only; no provider access or runtime capability is
authorized by this document

## 1. Decision

The first Stage 4 current-listing slice is a private, workspace-scoped observation ledger. An
authenticated user may save a listing URL as a reference and manually record a small set of
listing facts. The service does not request, render, unfurl, proxy, crawl or scrape the URL.
A licensed partner feed may later call the same domain commands only after its source has passed
the existing source-readiness gate.

The canonical model separates:

```text
Source -> Listing -> ListingObservation -> PriceObservation
                    |
                    +-> immutable Evidence

Listing --proposed/unverified relation--> PropertyEntity
```

`Listing` is a publication record, not a property. `ListingObservation` is a point-in-time claim
about that publication. `PriceObservation` is an asking-price fact within an observation.
`PropertyEntity` remains the workspace's reviewed property aggregate. `Source` describes the
publisher/brand and the permitted acquisition method; it does not confer authority on a
user-entered fact.

This design closes the current-inventory visibility gap without claiming broad market coverage,
without treating asking price as transaction value and without aggregating 15 platforms.

## 2. Pilot scope

### In scope

- one user-created observation at a time from a user-provided HTTPS listing URL and/or
  user-entered facts;
- source/brand, listing status, observation time, current asking price and an optional previous
  asking-price claim;
- immutable observation and price-change history;
- a private link from a Case to a Listing for workflow use;
- an optional `proposed`, unverified Listing-to-PropertyEntity relation;
- explicit correction, rejection, staleness and source-removal behavior;
- a stable internal seam for one future licensed partner feed; and
- a read-only sold-versus-asking presentation that keeps PLVR transaction facts and listing
  asking facts in separate series.

### Explicitly out of scope

- fetching any user URL, including `HEAD`, metadata preview, oEmbed, screenshot or browser proxy;
- crawling, scraping, change polling or backfilling any listing website;
- multi-brand aggregation, inventory completeness or market-share claims;
- images, descriptions, floor plans, broker/seller contact data or other copied page content;
- automatic address extraction, geocoding, property resolution or identity confirmation;
- automatic same-property or same-listing assertions, including across brands;
- public raw listing export, alerts, automated outreach, CRM or AI recommendations;
- partner-feed activation before contract, field, retention, takedown and real-feed acceptance;
  and
- writing asking prices into PLVR, comparable-sale, valuation or official transaction tables.

## 3. Non-negotiable invariants

1. Saving a URL records only a user-supplied reference. It never authorizes access to the URL or
   reuse of the publisher's content.
2. A Listing and a PropertyEntity are different objects with different identifiers and
   lifecycles. There is no `property_entity_id` column on `Listing` that implies identity.
3. A URL match, external listing ID, price, brand, address-like text or user selection cannot
   automatically confirm that two Listings describe the same property.
4. The pilot creates only `proposed` Listing-to-PropertyEntity relations backed by
   user-provided, unverified evidence. It exposes no relation-confirmation endpoint.
5. Asking price is neither transacted price nor valuation evidence. PLVR and listing projections
   remain separately labelled, queried and calculated.
6. Observation facts and corrections are append-only. A correction supersedes evidence; it
   never silently rewrites history.
7. `observed_at`, `recorded_at` and source effective time are distinct. The service never invents
   one from another.
8. Stale, unknown, withdrawn, unavailable and no observation are distinct states. None is
   rendered as current, active or zero.
9. Every tenant record, relation, evidence link and Case reference is workspace-scoped and
   protected by the existing authorization/RLS boundary.
10. Source configuration is fail-closed. A catalogued brand is not a licensed feed, and
    credentials or a recognizable host are not production acceptance.

## 4. Canonical domain model

The names below are domain names. Suggested persistence names use `vnext_core` and remain
additive to migrations `013`-`017`.

### 4.1 `Source`

`Source` answers two questions: which publisher/brand is the Listing associated with, and which
acquisition methods are permitted? It does not answer who asserted a particular observation;
that is recorded in observation Evidence.

Suggested `vnext_core.listing_sources` fields:

| Field | Contract |
| --- | --- |
| `source_id` | Opaque UUID; never derived from a hostname |
| `workspace_id` | Mandatory tenant boundary, including a workspace instance of a curated Source |
| `brand_name` | Display label; user-declared labels remain explicitly unverified |
| `source_kind` | `publisher`, `brokerage`, `partner_feed` or `unknown` |
| `canonical_hosts` | Reviewed host set; used for attribution suggestions, never for fetching |
| `verification_status` | `user_declared`, `catalogued` or `contracted` |
| `provider_access_policy` | `none` or `licensed_feed`; only the latter may enable an adapter |
| `manual_observation_policy` | `disabled` or `manual_facts`; never grants provider access |
| `source_registry_key` | Required key into the evidence/provider source registry |
| `freshness_policy_key` | Required before facts can be projected as fresh |
| `terms_ref`, `retention_policy_key`, `takedown_policy_key` | Reviewed policy references, never contract bodies or secrets |
| `created_at`, `disabled_at` | Lifecycle timestamps |

The existing `evidence_items.source_id` is a bounded registry key. This pilot reserves
`user-listing-manual` for manual listing facts; a future partner receives a separate contracted
key. It is deliberately not the `Source` UUID. For example, a user observation may reference a
catalogued brokerage `Source` while its Evidence still says `source_type=user`,
`source_id=user-listing-manual`.

The reviewed system source catalog remains configuration. Selecting a catalog entry creates or
reuses its workspace-scoped Source instance and preserves the catalog's registry key; there is
no cross-tenant Source row.

An unknown host or manually typed brand creates or selects a workspace-only Source with
`verification_status=user_declared`, `provider_access_policy=none`,
`manual_observation_policy=manual_facts`, `source_registry_key=user-listing-manual` and
`freshness_policy_key=manual-listing-7d-v1`. It cannot enable a provider adapter. An exact host
match may suggest a catalogued Source, but the UI must show the selection and allow correction.

This pilot clarifies the earlier source-registry rule that limited Listing URLs to
allowlisted/licensed partners: that restriction still governs provider access, resolution,
fetching and ingestion. A generic HTTPS URL may be stored only as a private, no-fetch,
user-provided reference under this contract. The source registry must add that manual-reference
use before the feature flag is enabled; it must not mark the referenced publisher as approved.

`listing_observation_manual_v1` is an independent, default-off manual feature flag. It requires
the authenticated VNext workspace/Case foundation, the `user-listing-manual` registry entry,
the approved `manual-listing-7d-v1` policy and this contract's tests; it does not satisfy or
enable `listing_intelligence`. The existing `listing_intelligence` flag remains the partner-feed
gate and still requires partner authorization. The source registry and architecture feature-gate
table must record this split before either runtime flag is enabled; until then this proposal
authorizes no runtime change.

### 4.2 `Listing`

`Listing` groups observations believed to belong to one publication lifecycle at one Source.
It is not a building, unit, parcel, offer contract or claim of exclusive inventory.

Suggested `vnext_core.listings` fields:

| Field | Contract |
| --- | --- |
| `listing_id`, `workspace_id` | Opaque UUID and mandatory tenant boundary |
| `source_id` | FK to `listing_sources`; one Listing cannot change Source in place |
| `external_listing_id` | Nullable partner identifier; accepted only under a contracted mapping |
| `publication_lifecycle_key` | Nullable partner-defined lifecycle key; not inferred across relists |
| `record_state` | `open`, `archived` or `superseded`; not the marketplace status |
| `version`, actor, `created_at`, `archived_at` | Exactly one of user/service actor; concurrency, attribution and lifecycle |

Marketplace status and current asking price are projections from observations, never mutable
truth columns on `Listing`.

Raw URLs do not live in `listings` or immutable Evidence. A required private support table,
`vnext_private.listing_url_references`, contains:

```text
listing_url_reference_id, workspace_id, listing_id
protected_normalized_url, keyed_url_fingerprint
supersedes_url_reference_id, created_by_user_id or created_by_service, created_at
redacted_at, redaction_reason
```

It is server-only and uses the approved private-storage/encryption control for the deployment.
Exactly one user/service actor is required; partner URL storage remains disabled until the
service-actor constraint and private storage have passed partner acceptance.
Ordinary URL correction appends a new reference and supersession link. The current reference is
the latest non-redacted member of the chain. Privacy erasure or contractual takedown is the sole
privileged exception: it removes or crypto-erases URL plaintext and the dedup fingerprint from
every active/private copy, sets a non-sensitive tombstone and emits an audit event containing no
URL. Cache entries and unexpired idempotency material associated with the reference are also
purged when policy requires identifier erasure.

`listing.reference_url.v1` Evidence stores `reference_present=true`, the Listing/Source IDs and
an opaque `value_ref` to this private record. It never stores the raw URL, host/path/query, URL
fingerprint or an unkeyed hash of them in `value`, lineage, `content_hash`, audit or logs. After
erasure the immutable Evidence still resolves to a tombstone, not the URL. The private URL is
also excluded from public exports.

### 4.3 `ListingObservation`

`ListingObservation` is an immutable snapshot claim about one Listing.

Suggested `vnext_core.listing_observations` fields:

| Field | Contract |
| --- | --- |
| `listing_observation_id`, `workspace_id`, `listing_id` | Opaque ID and workspace-consistent FK |
| `observation_method` | `user_entered` or, later, `licensed_feed` |
| `listing_status` | `active`, `under_offer`, `reserved`, `withdrawn`, `expired`, `sold_claimed`, `source_removed` or `unknown` |
| `observed_at` | When the user/provider says the status and price were observed |
| `recorded_at` | Server time at durable acceptance |
| `source_effective_at` | Nullable provider effective time; never synthesized for manual entry |
| `expires_at` | Deterministic from the reviewed source/fact policy |
| `source_event_id` | Nullable partner event ID; unavailable to the manual path |
| `evidence_id` | Status/context Evidence item |
| `supersedes_observation_id` | Nullable correction predecessor |
| `created_by_user_id` / `created_by_service` | Exactly one actor class |
| `created_at` | Server creation time |

`sold_claimed` means only that the user or Source reported the listing as sold. It is not PLVR
transaction evidence. `source_removed` is an operational/takedown state, not proof that a sale
occurred.

### 4.4 `PriceObservation`

`PriceObservation` is an immutable price fact attached to one `ListingObservation`. It keeps
price history independent from publication identity and status.

Suggested `vnext_core.price_observations` fields:

| Field | Contract |
| --- | --- |
| `price_observation_id`, `workspace_id` | Opaque ID and tenant boundary |
| `listing_id`, `listing_observation_id` | Workspace-consistent FKs; both must name the same Listing |
| `price_type` | Pilot accepts only `asking_total` |
| `observation_role` | `observed_asking` or `reported_previous_asking` |
| `amount` | Positive base-10 integer string at the API; `numeric(18,0)` in storage |
| `currency` | Pilot accepts only `TWD` |
| `effective_at` | Equals the parent `observed_at` for `observed_asking`; nullable for a source-reported previous claim |
| `evidence_id` | Asking-price Evidence item |
| `supersedes_price_observation_id` | Nullable correction predecessor |
| `created_at` | Server creation time |

No floating-point price enters the contract. Unit price, negotiable range, rent, fees and price
per ping require later versioned price types rather than overloading `asking_total`.
`amount` must match `^[1-9][0-9]{0,17}$`, so the API rejects values above the
`numeric(18,0)` ceiling with `price_contract_invalid` before persistence.

### 4.5 `PropertyEntity` and relations

`PropertyEntity` is unchanged. A Listing is registered as a `listing` graph node by extending
the existing `property_graph_nodes` target guard to accept a real Listing FK.

The pilot may append this edge:

```text
PropertyEntity --property_listing--> Listing
relation_status = proposed
source_type = user
evidence_status = user_provided
verification = unverified       # DTO label derived from the proposed user relation
confidence = null
```

The command means “the user proposes that this listing may describe this PropertyEntity.” It
does not mean “same property,” “verified address” or “confirmed unit.” The UI cannot accept a
confidence percentage because no reviewed method exists. Rejection or correction appends a
new relation decision referencing the earlier relation; it does not delete the proposal.

The pilot has no route that sets this relation to `confirmed`. A later identity slice may add
that route only with candidate review, evidence, explicit human intent and the confirmation
rules in `property-identity-architecture-v1.md`.

### 4.6 Case reference

A Case-to-Listing reference is required workflow metadata when `case_id` is supplied; it is not
identity. `vnext_core.case_listing_links` is an append-only decision chain with:

```text
case_listing_link_id, workspace_id, case_id, listing_id
decision                         # attached|removed
supersedes_case_listing_link_id
created_by_user_id, created_at
```

Case and Listing use composite workspace FKs. The current projection is the latest decision in
one chain; a unique/idempotent command prevents two open chains for the same `(workspace, case,
listing)` tuple. Create-with-Case validates `case_version` and atomically creates the Listing,
first observation, `attached` decision, incremented Case version and audit event. Later
attach/remove commands validate the current Case version, append a decision, increment that
version and audit in the same transaction. Creating or removing this link must not populate
`cases.property_entity_id` or create a PropertyEntity relation.

### 4.7 Listing-to-Listing duplicate candidate

`possible_same_publication` is a review hint between two Listing graph nodes, not a property
identity assertion. It reuses `property_relations` with both endpoints of type `listing`,
`relation_status=proposed`, `source_type=user`, confidence null and Evidence fact type
`listing.possible_same_publication.v1`. It is created when the user deliberately keeps an exact
candidate separate, or when a Source correction produces a replacement Listing.

The pilot permits only `proposed`, `rejected`, `superseded` or `disputed` states for this edge.
It has no `confirmed`/`same_publication` state and never merges history. Rejection appends a new
relation decision that names the prior decision. Cross-source Listings always remain separate,
even while this review hint exists.

The hint is semantically symmetric but stored with deterministic direction: the Listing ordered
first by `(created_at, listing_id)` is `from`, and the later one is `to`. Read DTOs return
`incoming|outgoing` relative to the requested Listing. Create-separate, URL-correction and
move-publication responses include the new relation ID so the rejection route is discoverable.

## 5. Current, previous and price-change semantics

The API computes projections; it does not persist mutable `current_price` or `previous_price`
columns.

### Current asking price

`current_asking_price` exists only when all of the following are true:

1. the latest non-superseded ListingObservation has `active`, `under_offer` or `reserved` status;
2. that same observation has a non-superseded `observed_asking` PriceObservation;
3. both status and price Evidence are usable and not expired; and
4. no material correction/conflict blocks the projection.

Otherwise `current_asking_price` is null. The response may still expose
`last_observed_asking_price` with its time and `stale|historical|conflicting` label. The service
does not carry a price forward from an earlier snapshot merely because a later status-only
record exists. Licensed feeds may define explicit carry-forward semantics only in a later,
reviewed source mapping.

### Previous asking price

For chronological observations, `previous_asking_price` is the nearest earlier,
non-superseded `observed_asking` for the same Listing with a different amount and currency,
excluding members removed from active chronology by a resolved conflict decision.
Repeated observations at the same price remain in history but do not create price-change
events.

The manual form also supports a source-reported previous price:

- If the user personally observed the earlier price and supplies its earlier `observed_at`, the
  service creates an earlier `listing_status=unknown` ListingObservation plus `observed_asking`
  PriceObservation. It does not invent the earlier status.
- If the page or another source merely reports “previous price,” the service creates
  `reported_previous_asking` on the current observation. It may show a labelled delta, but it
  is not inserted into the chronological observation series and no change time is inferred.

### Price-change history

Price-change events are deterministic read-model rows derived from adjacent distinct
chronological prices:

```text
from_price, to_price, absolute_delta, percentage_delta,
from_observed_at, to_observed_at, evidence_ids[]
```

They are recalculated after out-of-order entry, correction or conflict decision using only the
active chronological set. Percentage delta is null if a valid positive prior amount is
unavailable. A reported-previous claim produces a separately labelled `reported_delta` with
`changed_at=null`; it never masquerades as observed history.
For two positive TWD amounts, `percentage_delta = ((to - from) / from) * 100`, calculated with
decimal arithmetic and rounded half-up to four decimal places. `absolute_delta` is a signed
integer amount.

Ordering is deterministic by `observed_at`, then `recorded_at`, then opaque ID. API responses
label user-entered times and do not imply provider timestamps.

### Conflict handling

Ordering is not conflict resolution. The service opens a Listing conflict when non-superseded
facts cannot both be true for the same Listing and effective instant/interval, including:

- different asking amounts/currencies with the same `observation_role` and `effective_at`;
- incompatible statuses with the same `observed_at`;
- two corrections that supersede the same predecessor but disagree; or
- a future partner fact that overlaps a manual/partner fact under that Source's reviewed
  effective-interval semantics.

Different prices at different observation times are ordinary history, not a conflict.

`vnext_core.listing_conflicts` records immutable `listing_conflict_id`, Listing, conflict kind,
fact/effective scope and detection time. `listing_conflict_members` has checked nullable FKs for
the involved ListingObservation, PriceObservation and required Evidence ID. An append-only
`listing_conflict_decisions` chain stores `opened|resolved_by_correction|reopened`, its
predecessor decision ID, actor/service, reason and time. Detection creates the conflict,
members and initial `opened` decision atomically. All rows carry `workspace_id` and composite
workspace FKs. An open conflict touching the latest required status or price sets
`current_asking_price=null` and returns the involved Evidence IDs and bounded conflict code.
Older conflicts remain visible in history but do not suppress a later, non-conflicting current
observation.

Resolution never deletes a member or silently chooses the last write. An authorized user calls
`POST /v1/listing-conflicts/{conflict_id}/resolve` with the current Listing version, current
conflict-decision ID, a bounded reason and a complete replacement observation. The transaction
appends the correcting observation/Evidence and a `resolved_by_correction` decision, increments
the Listing version and writes the audit event. A newly conflicting concurrent command fails
with `409 version_conflict|conflicting_evidence` and the conflict stays open.

The latest `resolved_by_correction` decision excludes every member of that conflict from the
active chronological price/status projection; the appended replacement participates normally.
No singular supersession FK is stretched across several members. Excluded members remain in
history with `conflict_state=resolved_excluded`, their Evidence and decision ID. Reopening the
same fact scope creates a `reopened` decision and a new explicit member set; it never silently
reactivates an old member.

## 6. API contract

All endpoints inherit `/v1` conventions, Supabase bearer authentication, workspace role
authorization, safe errors and private/no-store responses from `api-contract-v1.md`.
`owner|admin|manager|member` may write; `viewer` is read-only. Every mutating `POST` requires a
new `Idempotency-Key` for each materially different canonical request. `GET` never requires an
idempotency key.

Concurrency is route-specific:

| Route | Expected version/decision | Atomic result and audit |
| --- | --- | --- |
| Create Listing | `case_version` when a Case is supplied | Listing v1, first facts, required Case-link decision and Case-version increment when applicable, and one audit event |
| Append/correct observation | current `listing_version`; correction target must be the current member of its supersession chain | append facts, increment Listing version and audit |
| Correct URL reference | current `listing_version` and `expected_url_reference_id` (nullable only when absent) | append private URL reference/Evidence, optionally append duplicate proposal, increment Listing version and audit |
| Move Source/publication | current source Listing version; supplied Case/link versions | create replacement Listing/facts/review edge, update requested Case links, increment affected versions and audit |
| Propose/reject Property relation | current `listing_version`; rejection also names `expected_relation_decision_id` | append relation decision, increment Listing version and audit |
| Attach/remove Case link | current `case_version` and latest link-decision ID when one exists | append link decision, increment Case version and audit |
| Reject publication candidate | current `listing_version` and `expected_relation_decision_id` | append relation decision, increment Listing version and audit |
| Resolve conflict | current `listing_version` and `expected_conflict_decision_id` | append correction + resolution, increment Listing version and audit |

Version comparison, new rows, projection-affecting version increment and audit event occur in
one transaction. A competing command returns `409 version_conflict`; it does not create a
second latest branch. Denied consequential mutations emit the safe audit outcome required by
the base API contract.

### `POST /v1/listings`

Creates a Listing and its first observation atomically. `case_id` is optional. Either
`listing_url` or a source selection/declaration is required; an active-like status requires an
asking price.

```json
{
  "workspace_id": "uuid",
  "case_id": "uuid-or-null",
  "case_version": "integer-or-null",
  "source": {
    "source_id": "uuid-or-null",
    "declared_brand_name": "Example Realty"
  },
  "listing_url": "https://listings.example/item/123",
  "observation": {
    "observed_at": "2026-09-20T02:30:00Z",
    "status": "active",
    "asking_price": {
      "amount": "25800000",
      "currency": "TWD",
      "price_type": "asking_total"
    },
    "previous_asking_price": {
      "amount": "26800000",
      "currency": "TWD",
      "basis": "source_reported",
      "observed_at": null
    }
  },
  "attestation": {
    "kind": "manual_facts_only",
    "version": "listing-manual-entry-v1",
    "accepted": true
  },
  "duplicate_disposition": null,
  "duplicate_candidate_id": null,
  "duplicate_candidate_version": null,
  "duplicate_token": null
}
```

`source_id` selects an accessible Source. `declared_brand_name` creates/selects a
workspace-scoped, user-declared Source. A request normally supplies exactly one; if both are
present, the declaration must exactly match the selected Source and does not rename it.
`case_version` is required exactly when `case_id` is non-null.

For `previous_asking_price.basis=user_observed`, `observed_at` is required and must precede the
current observation. For `source_reported`, it is nullable and no historical time is inferred.
An observation more than five minutes in the future is rejected; the tolerance handles clock
skew and is not an effective-time inference.

The command performs only local parsing, validation and persistence. Generic URL normalization
lowercases scheme/host, removes a default port and fragment, rejects credentials, and otherwise
preserves path/query semantics. Only reviewed partner-specific canonicalizers may remove
provider parameters. No DNS or network request occurs.

An exact open URL fingerprint or contracted partner lifecycle-key match returns
`409 possible_existing_listing` with a same-workspace `candidate_id`, `candidate_version` and a
single-use, ten-minute signed `duplicate_token`. The token binds actor, workspace, canonical
request fingerprint and candidate version; it contains no raw URL. The client either appends to
that Listing through its observation endpoint or resubmits Create with the three candidate
fields and `duplicate_disposition=create_separate_relist|create_separate_uncertain`. The changed
request requires a new `Idempotency-Key`. The server revalidates the token, workspace, candidate
version and exact candidate condition, then creates a separate Listing plus a
`possible_same_publication` proposal. It never merges them automatically. Replaying the original
key/request returns the original 409; reusing that key with a disposition returns
`409 idempotency_conflict`.

Returns `201 Created` with a `ListingDTO`.

### `POST /v1/listings/{listing_id}/observations`

Appends a manual observation to an existing Listing. It accepts the `observation` and
`attestation` objects above plus `listing_version`. It cannot change Source or external listing
identity. It increments the Listing version and returns `201 Created` with the immutable
observation and refreshed projections.

### `GET /v1/listings/{listing_id}`

Returns source, `reference_url_available`, observed status, current/last/previous price
projections, freshness, limitations, Case references and relation summaries. It never returns
the raw URL. Each fact includes its Evidence reference and source label.

Conceptual projection:

```json
{
  "listing_id": "uuid",
  "workspace_id": "uuid",
  "record_state": "open",
  "source": {
    "source_id": "uuid",
    "brand_name": "Example Realty",
    "verification_status": "user_declared",
    "provider_access_policy": "none",
    "manual_observation_policy": "manual_facts"
  },
  "reference_url_available": true,
  "observed_status": {
    "value": "active",
    "observed_at": "2026-09-20T02:30:00Z",
    "freshness": "fresh",
    "evidence_id": "uuid"
  },
  "current_asking_price": {
    "amount": "25800000",
    "currency": "TWD",
    "observed_at": "2026-09-20T02:30:00Z",
    "freshness": "fresh",
    "evidence_id": "uuid"
  },
  "previous_asking_price": {
    "amount": "26800000",
    "currency": "TWD",
    "basis": "source_reported",
    "observed_at": null,
    "evidence_id": "uuid"
  },
  "property_relations": [
    {"property_entity_id": "uuid", "status": "proposed", "verification": "unverified"}
  ],
  "publication_relations": [
    {"relation_id": "uuid", "other_listing_id": "uuid", "direction": "outgoing", "status": "proposed"}
  ],
  "limitations": ["user_entered", "not_transaction_price", "inventory_incomplete"],
  "version": 1
}
```

If stale, `current_asking_price` is null and the same fact appears under
`last_observed_asking_price` with `freshness=stale`.

### `GET /v1/listings/{listing_id}/reference-url`

Returns the current raw URL only to an active same-workspace `owner|admin|manager|member` with
access to the Listing/Case purpose. It returns `403` to `viewer`, support/operator principals and
unscoped callers; collections, exports and ordinary Listing DTOs remain redacted. The response
is `private, no-store`, is never prefetched, and appends a safe URL-access audit event containing
only Listing and URL-reference IDs. If redacted, it returns `410 url_reference_redacted` without
a historical URL. The explicit user click then opens it with `noopener,noreferrer`.

### `GET /v1/listings/{listing_id}/history`

Returns cursor-paginated observations and derived price changes. Default ordering is newest
first; `order=oldest_first` is supported for a chart. Superseded records are hidden from the
default projection but available with `include_superseded=true` to authorized members.

### `POST /v1/listing-observations/{observation_id}/corrections`

Requires a complete replacement snapshot; omission is never interpreted as “keep the old
value.” Nullable fields use explicit JSON null.

```json
{
  "listing_version": 3,
  "reason_code": "incorrect_price",
  "replacement": {
    "observed_at": "2026-09-20T02:30:00Z",
    "status": "active",
    "asking_price": {"amount": "25800000", "currency": "TWD", "price_type": "asking_total"},
    "previous_asking_price": null
  }
}
```

The target must be the current member of its supersession chain unless this request is part of
the explicit conflict-resolution command. The transaction appends replacement
ListingObservation, PriceObservation and Evidence rows with supersession links, increments the
Listing version and audits. It never updates or deletes the original facts.

### `POST /v1/listings/{listing_id}/url-references`

Corrects or adds the private URL without changing Source or copying page content.

```json
{
  "listing_version": 3,
  "expected_url_reference_id": "uuid-or-null",
  "listing_url": "https://listings.example/item/456",
  "reason_code": "incorrect_url",
  "duplicate_disposition": null,
  "duplicate_candidate_id": null,
  "duplicate_candidate_version": null,
  "duplicate_token": null
}
```

It locally normalizes the URL, appends a private URL-reference version plus opaque Evidence,
increments the Listing version and audits. An exact candidate returns the same bounded 409/token
contract as Create. The user may instead move to/append the existing Listing, or resubmit with a
new idempotency key and `duplicate_disposition=keep_current_separate`; that explicit choice also
appends a `possible_same_publication` proposal and returns its relation ID. No URL is fetched.

### `POST /v1/listings/{listing_id}/move-publication`

Changing Source or external listing identity is not a fact correction. This command creates a
replacement Listing with an explicitly re-entered complete observation; it never silently copies
old facts.

```json
{
  "listing_version": 3,
  "reason_code": "wrong_source",
  "replacement": {
    "source": {"source_id": "uuid", "declared_brand_name": null},
    "listing_url": "https://other.example/listing/789",
    "observation": {
      "observed_at": "2026-09-20T03:00:00Z",
      "status": "active",
      "asking_price": {"amount": "25800000", "currency": "TWD", "price_type": "asking_total"},
      "previous_asking_price": null
    },
    "attestation": {"kind": "manual_facts_only", "version": "listing-manual-entry-v1", "accepted": true}
  },
  "case_link": {
    "case_id": "uuid",
    "case_version": 4,
    "expected_link_decision_id": "uuid",
    "action": "move"
  },
  "duplicate_disposition": null,
  "duplicate_candidate_id": null,
  "duplicate_candidate_version": null,
  "duplicate_token": null
}
```

`case_link` is optional. `move` appends `removed` for the old Case/Listing chain and `attached`
for the replacement; `keep_both` appends only the replacement attachment. Other Case links to
the old Listing are unchanged. The transaction creates the replacement Listing/facts, appends a
`possible_same_publication` proposal, returns its relation ID, increments the old Listing and
affected Case versions, and audits. If the replacement has an exact candidate, the normal
duplicate token/new-idempotency-key contract applies; the client may choose the existing Listing
through the separate append and Case-link commands instead. The command never archives the old
Listing merely because other Cases may still reference it.

### `POST /v1/listings/{listing_id}/property-relations`

```json
{
  "property_entity_id": "uuid",
  "relation_type": "property_listing",
  "intent": "propose_unverified",
  "listing_version": 1
}
```

The response is always a `proposed`, `unverified` relation. A same-workspace, non-archived
PropertyEntity is required. The endpoint never invokes property resolution or confirmation.

### `POST /v1/listing-property-relations/{relation_id}/reject`

Requires `listing_version`, `expected_relation_decision_id` and a bounded reason such as
`wrong_property`, `wrong_unit`, `insufficient_evidence` or `duplicate_proposal`. It appends a
rejection decision and increments the Listing version. The proposal remains in history. No
confirm operation exists in the pilot.

### Case and duplicate-relation mutations

- `POST /v1/cases/{case_id}/listing-links` requires `case_version`, `listing_id` and
  `decision=attached|removed`; removal also supplies `expected_link_decision_id`.
- `POST /v1/listing-publication-relations/{relation_id}/reject` requires `listing_version`,
  `expected_relation_decision_id` and `reason_code`. No confirm/merge route exists.
- `POST /v1/listing-conflicts/{conflict_id}/resolve` uses the complete correction contract and
  concurrency behavior defined in the conflict section.

### Read collections

- `GET /v1/cases/{case_id}/listings` returns Listings explicitly referenced by that Case.
- `GET /v1/properties/{property_entity_id}/listing-relations` returns proposed, rejected and
  disputed relations separately. It must not label proposed rows “this property's listings.”
- `GET /v1/listings/{listing_id}/publication-relations` returns a cursor-paginated page of
  proposed/rejected/disputed duplicate candidates with relation ID, other Listing ID, direction,
  Evidence ID and latest decision ID.

### Errors added by this contract

| Code | HTTP | Meaning |
| --- | --- | --- |
| `possible_existing_listing` | 409 | Exact bounded candidate exists; caller must choose append or separate |
| `listing_relation_unverified` | 409 | An operation incorrectly requires a confirmed relation |
| `source_not_enabled` | 422/503 | Manual facts are disabled for this Source (`422`) or a required partner Source is unavailable/disabled (`503`) |
| `url_reference_invalid` | 422 | URL is not acceptable as a private HTTPS reference |
| `url_reference_redacted` | 410 | The private URL was erased/redacted and no historical value is returned |
| `observation_time_invalid` | 422 | Time is absent, implausibly future or inconsistent with prior-input semantics |
| `price_contract_invalid` | 422 | Amount, TWD currency, role or ordering violates the pilot contract |
| `listing_stale` | 409 | Consequential action requested a current observation but only stale history exists |

Errors and audit events contain IDs and bounded codes, never full URLs or amounts unless the
purpose-specific audit policy expressly permits the latter.

## 7. Evidence and provenance

Every observation creates or links immutable Evidence under
`evidence-architecture-v1.md`.

| Fact | Evidence fact type | Manual path | Future partner path |
| --- | --- | --- | --- |
| URL reference | `listing.reference_url.v1` | `source_type=user`, `status=user_provided` | `source_type=partner`, status per accepted mapping |
| Listing status | `listing.status_observation.v1` | user-provided, validation not checked | available/limited only after field acceptance |
| Observed asking | `listing.asking_price.v1` | user-provided, TWD/shape validated | available/limited only after field acceptance |
| Reported previous asking | `listing.reported_previous_asking_price.v1` | user-provided; effective time may be unknown | partner mapping must state semantics |
| Property relation proposal | `listing.property_relation_proposal.v1` | user-provided evidence; proposed/unverified relation | partner data may suggest but never confirm identity |
| Publication duplicate candidate | `listing.possible_same_publication.v1` | user-provided/deterministic candidate; never property identity | partner rule must be reviewed |
| Conflict decision | `listing.conflict_resolution.v1` | user correction citing every conflict member | partner automation cannot select a winner |

Manual evidence is displayed as **User-provided · unverified**. Internally it uses
`evidence_status=user_provided`, `source_type=user`, `quality_status=not_checked|limited` and an
explicit `unverified` limitation. Format validation does not promote it to official or partner
evidence.

For manual facts, Evidence `retrieved_at` is the server `recorded_at`, `effective_from` is the
declared `observed_at`, and domain expiry is `observed_at + 7 days`. An old observation may
therefore already be expired when recorded. The implementation migration must replace the
current `ck_vnext_evidence_expiry` rule that assumes expiry is later than retrieval; the revised
rule must permit already-expired historical evidence while still requiring expiry to be later
than the fact's known effective/observed start. It must not change old rows or invent a newer
effective time.

Minimum lineage is:

```text
actor or service
observation method and contract version
Source UUID plus evidence source-registry key
observed_at, recorded_at and source_effective_at
canonical fact-input hash using the opaque URL-reference ID, never raw URL material
normalizer or partner-mapper version
provider event/external record references when licensed
parent/superseded evidence IDs
```

The URL itself is not proof of page contents. Its only raw copy is the redactable private URL
reference described above; immutable Evidence holds an opaque reference/tombstone. The service
stores no fetched artifact for the manual path. Partner raw payload retention is off by default;
if a contract later permits it, the payload uses a private Artifact, bounded retention and no
browser storage URL.

Evidence created from the manual-entry product flow may use `license_status=not_applicable`
only after product terms and the manual-facts attestation are approved. This describes the
user's factual assertion; it does not license provider access, caching or redistribution.
Partner evidence requires `license_status=approved` and a reviewed `license_ref`.

## 8. Deduplication and relist policy

Deduplication is conservative and operates at three distinct levels:

1. **Request replay:** the existing idempotency contract automatically returns the same result.
   This is not entity matching.
2. **Possible same publication:** an exact normalized URL fingerprint, or a contracted exact
   `(Source, external_listing_id, publication_lifecycle_key)`, creates a candidate. A user or
   partner-specific reviewed rule chooses append versus separate. The records are not merged.
3. **Possible same property:** separate Listings may each have their own proposed relation to a
   PropertyEntity. The system does not infer a relation between the Listings from that fact.

Never-auto-merge signals include:

- same or similar URL outside a reviewed canonicalizer;
- shared brand, price, text, address, coordinates, image or contact;
- time proximity or an external similarity score;
- a PropertyEntity candidate, AI output or another user's relation; and
- disappearance followed by reappearance.

A relist is a new Listing by default. It may reuse the old Listing only when the partner
contract documents identifier stability across that exact lifecycle and acceptance tests cover
relist behavior. The pilot may retain a `possible_same_publication` proposal, but exposes no
accept/confirm/merge operation. Both IDs and histories remain separate. Cross-source records are
always distinct Listings in this pilot.

## 9. User correction and deletion

The correction UI offers four explicit actions:

- **Correct observation:** append replacement status/time/price evidence with a reason.
- **Add newer observation:** append history without alleging the earlier fact was wrong.
- **Reject property relation:** append a rejected relation decision.
- **Move to another Source/publication:** create a new Listing and preserve a review link.

Price or status correction recomputes read projections and derived deltas. Reports that used an
older Evidence ID remain reproducible and show that the evidence was later superseded.

Ordinary correction never deletes history. Privacy erasure, contract takedown and workspace
deletion are separate audited operations. They may remove or irreversibly redact a URL or raw
artifact while retaining a minimal non-sensitive tombstone when law and contract permit. A
tombstone cannot be projected as a current Listing.

## 10. Freshness, expiry and removal

Freshness is computed from Evidence timestamps and Source policy; it is not a mutable claim.

- The manual pilot policy is seven calendar days from `observed_at`. A historical observation
  older than seven days is stale immediately. Opening the record does not refresh it.
- A user refresh requires an explicit new observation. No job revisits the URL.
- A future partner Source must have a reviewed cadence and maximum acceptable age. Until that
  policy exists, partner freshness is `unknown` and the source cannot be enabled. The service
  does not silently fall back to the manual seven-day rule.
- At `now >= expires_at`, a fact is stale. History remains readable, but current asking price is
  null and the record is excluded from current-inventory counts.
- A terminal user-entered status also expires as a statement about the present. It remains
  “last reported withdrawn/expired/sold,” not permanent truth.
- Feed silence is not a takedown or no-longer-active fact unless the partner contract explicitly
  defines complete snapshots or deletion events.
- A contractual takedown/disable event immediately hides the URL and disallowed fields, stops
  ingestion for that Source and applies the reviewed purge/tombstone policy. It does not infer
  sale, deletion of the property or absence from other Sources.

Freshness projections are `fresh|stale|unknown`; source status remains separately visible.

## 11. Privacy and legal boundary

This design is a technical boundary, not a legal opinion. Product/legal owners must approve
the exact terms, notices and retention behavior before feature enablement.

### Permitted manual behavior

- accept a user-entered URL as a private reference;
- accept the user's own minimal factual transcription of brand, status, time and asking price;
- validate locally and store it inside the authenticated workspace; and
- let the user explicitly open the original link in a new tab with `noopener,noreferrer` and a
  notice that the external site's terms apply.

### Prohibited behavior

- any server or client background request to the URL;
- previews, screenshots, HTML, structured-data extraction or browser automation;
- copying/storing listing text, photos, floor plans, contact details or seller/owner data;
- turning a user URL into an allowlist for crawling;
- using manual observations to claim provider endorsement, complete supply or official status;
- public redistribution or bulk export of raw listing records; and
- enabling a partner adapter because credentials exist or a Source is merely catalogued.

The manual DTO is field-allowlisted. Free-form description/contact fields do not exist. URLs
are private because paths/query strings may contain identifiers. They are excluded from
telemetry and redacted in support/admin views by default. Input rejects non-HTTPS schemes,
embedded credentials and excessive length. Since no request occurs, the URL cannot become an
SSRF input; future code must preserve that no-fetch invariant.

The approved erasure path inventories the private URL row, dedup fingerprint, application/cache
copies and unexpired idempotency material, then deletes or crypto-erases each policy-covered
identifier. Immutable Evidence and audit retain only opaque record IDs and the redaction reason.
There is no raw URL in those ledgers to conflict with erasure.

The partner contract must decide authorized fields, commercial use, display, caching,
redistribution, attribution, geographic/temporal coverage, rate limits, raw-payload retention,
user deletion, takedown SLA, termination purge and audit evidence. Fields outside the approved
mapping fail closed.

## 12. UI workflow

1. In a Case's Market area, the user chooses **Add listing observation**.
2. The form explains: “We save this as your private reference. We do not open or scrape the
   page.” Pasting a URL performs local parsing only; no preview or loading state implies access.
3. The user selects or declares a brand/Source, then enters observation time, status, current
   asking price and optional previous-price basis. The UI labels all manual facts
   **User-provided · unverified**.
4. If an exact candidate exists, the UI shows **Add an observation to the existing publication**
   and **Keep separate as a possible relist/uncertain record**. Neither option claims the same
   property.
5. The optional identity step defaults to **Not linked to a property**. Selecting an existing
   PropertyEntity says **Propose a possible relation** and displays that confirmation is not
   part of this pilot.
6. Review shows the exact stored fields, observed time, seven-day expiry, Source status and
   manual-facts attestation before save.
7. The Listing detail displays source/brand, a role-gated **Open source URL** action, observed
   status, freshness, current or last observed asking price, previous-price basis and the
   observation timeline. Price cuts use observed evidence IDs and never imply a completed
   transaction.
8. Sold-versus-asking view uses separate visual rows/series: **Official recorded transactions
   (PLVR)** and **User/partner asking observations**. No blended average or valuation input is
   produced. PLVR rows are an explicitly described geographic/market comparable cohort, not
   asserted sales of the Listing's property. The UI prohibits a per-property sold/asking delta
   until a later contract permits a confirmed Listing-to-PropertyEntity relation.
9. **Correct** opens the four correction choices above. The UI keeps superseded history
   accessible and never edits a timeline row in place.

Stale records receive a prominent **Last observed; refresh manually** state. Unknown and stale
states are not represented only by color.

## 13. Licensed partner-feed seam

The application service accepts a source-neutral internal command after authentication and
source-policy checks:

```text
IngestListingObservationCommand
  mandatory workspace scope
  listing Source UUID and source-registry key
  external_listing_id and external_event_id
  publication_lifecycle_key, if contractually defined
  reference_url, if display/storage is permitted
  observed_at and source_effective_at
  mapped listing status
  allowlisted asking-price facts
  mapper/version, license and coverage metadata
  raw_artifact_ref only when retention is permitted
```

The manual API and future adapter both call the same validation, persistence, evidence and
projection services. Only provenance, actor, idempotency identity and source policy differ.

A partner adapter remains backend-only and maps provider enums to the canonical model. Unknown
provider values become `unknown` or a rejected event; they are never coerced to `active`.
Provider event idempotency is scoped by Source. An external listing ID can group events only
under reviewed lifecycle semantics. The adapter cannot create a confirmed PropertyEntity
relation.

There is no public partner-ingest endpoint in the manual pilot. Enabling one Source requires:

1. `production_accepted` source evidence under `data-source-registry-v1.md`;
2. signed contract and field-level license/redistribution/retention decisions;
3. documented listing ID, relist, deletion and full-snapshot/delta semantics;
4. fixture contract tests plus separately recorded real-feed acceptance;
5. freshness, outage, late/out-of-order event and takedown tests;
6. per-Source feature flag/kill switch and operations runbook; and
7. proof that raw feed data, credentials and restricted fields cannot reach browser DTOs; and
8. explicit service-actor support for Listing and graph-node creation. A feed job must not
   impersonate a user to satisfy the current user-only graph-node column.

The first partner implementation may enable exactly one contracted Source. Multi-partner and
cross-brand aggregation remain out of scope.

No feed-specific field may be added to the canonical tables without a versioned mapping or a
private provider extension.

## 14. Suggested implementation slice

Implement behind a default-off `listing_observation_manual_v1` flag in this order:

1. Add the `user-listing-manual` registry entry and `manual-listing-7d-v1` policy, and amend the
   architecture feature-gate table to distinguish the manual flag from partner-only
   `listing_intelligence`. Runtime remains off until those governing docs/configuration agree.
2. Add `listing_sources`, `listings`, `listing_observations`, `price_observations`,
   `case_listing_links`, private URL references, and listing conflict/member/decision tables
   with workspace FKs, RLS, append-only/supersession checks and indexes. Adjust the Evidence
   expiry constraint for honestly ingested, already-stale historical facts without rewriting
   existing Evidence.
3. Extend graph-node and relation guards for a real `listing` target and proposed-only
   `property_listing` and `possible_same_publication` edges. Do not add confirmation.
4. Add pure URL normalization, price-history, conflict-detection and freshness projections with
   no HTTP client dependency.
5. Add create/append/read/history/role-gated-URL/correct/propose/reject/conflict services and
   FastAPI routes using the existing auth, idempotency, audit and evidence infrastructure.
6. Add the manual intake, detail/timeline and separate sold-versus-asking UI inside the
   authenticated Case workflow.
7. Define the internal partner command/protocol and contract fixtures only. Do not implement or
   enable an external feed in this slice.

Likely modules are a new additive migration, `services/vnext/listing_*`, a bounded
`backend/api/v1/listings.py` router, listing client/types/components in `frontend_next`, and
contract/security/E2E tests. Existing PLVR and valuation services are read-only dependencies
for separate presentation; they are not modified to ingest asking prices.

### Acceptance gate

- Network-deny tests prove every manual create/read/correct flow succeeds with no outbound URL
  request and no HTTP client call.
- Idempotent replay creates one result; exact URL candidates never auto-merge; explicit relists
  remain separate. Duplicate resubmission tests cover token expiry, wrong workspace/actor,
  changed candidate version, a required new idempotency key and one proposed publication edge.
- Current, previous-distinct, repeated, reported-previous, out-of-order, maximum-price,
  percentage-rounding, correction and stale price cases have deterministic tests.
- Same-instant price/status conflicts and concurrent correction branches create explicit
  conflict members, suppress the affected current projection and resolve only by appended
  correction/decision. Resolved members remain historical but are excluded from current and
  previous-price chronology.
- The expiry boundary at seven days is clock-controlled and excludes stale rows from current
  inventory while preserving history.
- Every manual Evidence row preserves user source and an unverified limitation, with actor,
  observation time, recorded time, expiry, lineage and no authority promotion.
- Every Listing-to-PropertyEntity relation is proposed/unverified; no request path can confirm
  it or infer cross-listing identity. Publication-candidate relations also have no confirm or
  merge route.
- Case create/attach/remove/reopen tests prove the required append-only Case-link projection,
  version conflicts, idempotency and atomic audit behavior.
- URL correction and Source/publication movement tests cover expected reference/listing/Case
  versions, explicit Case-link actions, duplicate tokens, returned publication-relation IDs and
  no silent fact copying.
- RLS and service tests prove cross-workspace Listing, URL, Case, Evidence and relation IDs are
  non-enumerable and inaccessible; composite workspace FKs reject mixed-tenant writes.
- Raw URL reads allow only same-workspace writer roles, deny viewers/revoked memberships/support
  principals, audit safely and remain absent from collections/exports.
- URL values and partner identifiers do not appear in logs, errors, Evidence, ordinary
  idempotency records or audit metadata; any keyed request material follows its purge policy.
- Takedown/redaction removes every policy-covered URL/fingerprint/cache copy and leaves only the
  policy-approved opaque tombstone.
- Asking prices remain absent from PLVR transaction, comparable-sale and valuation inputs.
- Sold-versus-asking tests label the PLVR cohort as market comparables and prohibit a
  same-property delta from a proposed/unverified relation.
- UI accessibility tests distinguish fresh/stale/unknown and user/partner/official semantics
  with text, not color alone.

## 15. Go / no-go boundary

**GO** for an authenticated, private, manual-observation implementation after product/legal
approval of the manual-entry notice, attestation, seven-day freshness policy, retention and
erasure behavior, and after the source registry/architecture gate updates above are approved.
This slice materially closes the Stage 4 current-asking gap without provider access.

**NO-GO** for URL retrieval, scraping, cross-brand aggregation, automated property matching,
public redistribution or partner ingestion. A licensed feed remains no-go until its individual
source-readiness and acceptance gates pass.
