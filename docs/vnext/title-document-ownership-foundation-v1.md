# Title, Document, and Ownership Foundation v1

Status: Stage 5 architecture contract; documentation only

This document defines a foundation for Taiwan real-estate title and due-diligence
document workflows. It does not add a migration, Storage bucket, provider, OCR job,
API route, or production policy. It does not determine legal ownership, the validity or
priority of a right, whether an entry has been discharged, or whether title is clear.

The target document families are:

- land transcript (`land_transcript`);
- building transcript (`building_transcript`);
- the ownership section of either transcript;
- the other-rights/encumbrance section of either transcript; and
- other user-uploaded due-diligence documents (`due_diligence_other`).

The words “confirmed” and “observation” have deliberately narrow meanings below. A
human-confirmed observation means that an authorized reviewer confirmed what a cited
document version displays. It is not an independent legal determination.

## 1. Decisions

1. `Document` is the stable, case-scoped business record. `DocumentVersion` is an
   immutable received or procured edition. `DocumentArtifact` is metadata for immutable
   bytes or a derived rendition in private object storage.
2. Original bytes, extracted text, structured claims, human-confirmed observations, and
   legal interpretation are separate records with one-way promotion gates.
3. `ExtractedClaim` is always a suggestion or transcription candidate. It is never an
   ownership fact, a graph relation, or proof that a right exists or does not exist.
4. `OwnershipObservation` and `EncumbranceObservation` record what an authorized human
   found in an exact document version and citation. They are append-only and temporal.
5. Owner, debtor, right-holder, address, identifier, and debt data remain in
   `vnext_private`. They do not become general property-graph nodes or generic case JSON.
6. The existing Evidence ledger remains the provenance and subject-link layer. It receives
   only a minimized pointer/summary after human confirmation; sensitive content remains
   behind a purpose-specific document operation.
7. All file storage is private. A public bucket, permanent object URL, client-held service
   key, and direct bucket listing are forbidden.
8. Every read or download is authorized against current workspace membership, role, case
   assignment, purpose, sensitivity, and resource scope. Object-key knowledge is not
   authorization.
9. AI/OCR may extract, normalize, cite, compare, and suggest. It may not confirm an
   observation, create a confirmed graph relation, identify the legal owner, determine the
   legal effect or priority of an entry, or declare title clean.
10. The first implementation slice is a private, auditable document vault. OCR, AI,
    ownership observations, title procurement, external sharing, and production rollout are
    later gates.

## 2. Current repository audit

### 2.1 What exists

| Area | Current foundation | Reuse decision |
| --- | --- | --- |
| Workspace and Case | Migration `013` provides `workspaces`, `workspace_members`, workspace-scoped `cases`, role-aware RLS, idempotency, and append-only `audit_events`. Migration `016` adds append-only `case_property_links`. | Every Document belongs to one workspace and one owning Case. Use current membership and Case authorization; do not invent a user-owned file silo. |
| PropertyEntity | `property_entities` is an application aggregate, explicitly not a government identifier. Inferred ownership is prohibited on it. | Do not add owner fields to PropertyEntity. A document may cite a parcel/building subject without changing the PropertyEntity. |
| Parcel/building graph | `property_identity_references` supports address, geo, parcel, and building references. `property_graph_nodes` and `property_relations` provide typed, temporal, evidence-backed edges. Current parcel/building inputs are manual or limited and do not prove ownership. | Link reviewed document evidence to an existing parcel/building node. Document extraction may propose a subject candidate but may not confirm or merge it. |
| Evidence | Migration `014` provides immutable/versioned `evidence_items`, `evidence_lineage`, and `evidence_links`, including `source_type=document`, coverage, quality, license, time, supersession, and a private artifact reference string. | Reuse provenance, lineage, conflict, and subject links. Do not use Evidence as a file, OCR job, document version, person record, or legal conclusion. |
| Artifacts | `artifacts` is described conceptually in the VNext architecture, and Evidence has `raw_artifact_ref`, but there is no durable artifact table or object lifecycle. | Implement an explicit DocumentArtifact record before any retained title upload. Replace unverified strings with workspace-consistent FKs/bridges prospectively; preserve legacy compatibility. |
| Storage/security | The security contract already requires private buckets, server-generated keys, validation before availability, 60–300 second downloads, purpose/role checks, audit, and independent retention of bytes, tombstones, and audit. | Adopt and narrow this contract for restricted title content. Do not expose Storage or document base tables directly to the browser/Data API. |
| Audit | `vnext_private.audit_events` is append-only, insert-only for the application path, workspace-scoped, and limits metadata size. Current docs prohibit raw payloads and document bodies. | Reuse it with a Stage 5 event allowlist. Never put filenames, extracted text, claims, party data, storage keys, signed URLs, or document content in audit metadata. |

Relevant current contracts are [Architecture Overview](architecture-overview-v1.md),
[Evidence Architecture](evidence-architecture-v1.md),
[Property Identity Architecture](property-identity-architecture-v1.md),
[Workspace and Security Architecture](workspace-security-architecture-v1.md), and the
[VNext API Contract](api-contract-v1.md).

### 2.2 Gaps

The current repository has no runtime title/document vault, `Document`, document version,
stored artifact lifecycle, ownership observation, encumbrance observation, signed document
delivery, or retention/deletion workflow. The parcel upload endpoint is request-scoped and is
not a document system. The source registry marks the title source `partner_required`; no
title partner, procurement contract, legal basis, consent flow, cost workflow, or production
authorization is approved.

The existing `evidence_items` read policy is workspace-member-wide. It is not sufficient for
owner names, identifiers, contact addresses, secured amounts, or other restricted title
content. Stage 5 must keep that content private and add case/sensitivity-aware evidence access
before any sensitive document-derived Evidence value can be returned.

The current Evidence insert policy also permits user/deterministic/demo/test sources on the
normal request path, but not `source_type=document`. Stage 5 must not loosen that generic
policy. A later migration needs a narrow, audited document-Evidence writer that accepts only
human-confirmed private observation references and the safe projection contract in this
document.

The current audit row accepts bounded JSON metadata but the database does not understand
document-content sensitivity. The Stage 5 service must use a fixed metadata schema, and tests
must prove that user input and provider/OCR output cannot flow into logs or audit metadata.

## 3. Considered approaches

### A. Extend Evidence to hold documents and parsed data

This is superficially small but conflates an attributable fact with file upload state,
malware scanning, byte retention, versions, OCR text, and review decisions. It also risks
exposing title PII through current workspace-wide Evidence reads. Rejected.

### B. Add owner and right-holder nodes to the general property graph

This makes graph traversal convenient but creates a broadly visible person/relationship
graph, encourages name-based identity inference, and confuses document observations with
legal rights. Rejected.

### C. Case-scoped private document aggregate with an evidence bridge

This keeps bytes, PII, parsing, and review in a restricted context while preserving the
existing Evidence ledger and parcel/building graph as the provenance and subject layers.
This is the selected approach.

## 4. Trust ladder and promotion gates

```text
private original bytes
  -> derived extracted-text artifact
  -> ExtractedClaim (machine/manual suggestion with citation)
  -> authorized human review
  -> OwnershipObservation or EncumbranceObservation
  -> minimized document Evidence + evidence_links
  -> optional future professional/legal interpretation (separate model)
```

| Layer | Record | Meaning | May be changed into the next layer automatically? |
| --- | --- | --- | --- |
| Raw file | `DocumentArtifact(role=original_file)` | Exact received/procured bytes, hash, media metadata, and scan state | No. It must pass validation and be bound to a sealed DocumentVersion. |
| Extracted text | `DocumentArtifact(role=extracted_text)` | Derived text for a specific source artifact and extractor version; still untrusted and PII-bearing | No. It may feed claim generation only. |
| Structured claim | `ExtractedClaim` | A field-level suggestion with document section and page/region citation | No. An authorized human must accept or reject it. |
| Human-confirmed fact | `OwnershipObservation` or `EncumbranceObservation` | The reviewer confirmed that the cited version displays the recorded content | No. It is not a legal conclusion or proof of current state. |
| Legal interpretation | A separate future professional-review record | A qualified person’s scoped interpretation with author, scope, date, and cited evidence | Never produced by OCR/AI or inferred from observation status. |

Promotion is append-only. Rejecting or superseding a claim does not alter the source bytes.
Correcting an observation creates a new observation that supersedes the old one; it never
rewrites the cited document.

Source claims and confirmed observations are immutable. Document, DocumentVersion, and
DocumentArtifact lifecycle state may use a narrowly mutable, optimistic-concurrency
projection for operational reads, but every transition appends a typed lifecycle event and
immutable object/version content never changes. Claim review and observation dispute or
supersession are separate append-only decision records, not status updates on their source
rows.

## 5. Aggregate and relationships

```text
Workspace
  -> Case
      -> Document
          -> DocumentVersion 1..n
              -> DocumentArtifact 1..n
              -> ExtractedClaim 0..n
              -> OwnershipObservation 0..n
              -> EncumbranceObservation 0..n

Observation
  -> exact DocumentVersion + source artifact + page/section citation
  -> Case-property-link snapshot + confirmed property-to-subject relation snapshot
  -> zero or more source ExtractedClaims
  -> one minimized Evidence item when eligible
  -> EvidenceLink -> Case/Parcel/Building graph node
```

Every relationship uses `(workspace_id, id)` composite foreign keys where the current schema
supports them. Cross-workspace Case, Document, Artifact, claim, observation, evidence, and
graph links fail in the database as well as the service. Foreign-key columns and common
workspace/case/status/time access paths are indexed.

A Document has one owning Case. Cross-Case reuse is deferred and prohibited in the first
slice. A later copy operation must create a new Document/version in the destination Case,
preserve provenance to the source Document, repeat authorization/retention decisions, and
audit the copy; it cannot forward an object URL or create a shared mutable Document.
Cross-workspace document reuse is prohibited.

An observation also snapshots the Case’s then-current `case_property_link` and the eligible
confirmed `property_parcel` or `property_building` relation used to reach its subject node.
A private `document_subject_links` bridge holds those FKs. “Same workspace” alone is not
enough: promotion fails unless the subject is reachable from the owning Case’s current
PropertyEntity through that confirmed relation. Later Case reattachment or graph
supersession does not rewrite the historical observation.

## 6. Domain model

### 6.1 `Document`

Responsibility: stable logical envelope for one case document across replacements, refreshed
transcripts, and derived renditions.

Conceptual fields:

```text
document_id                   uuid
workspace_id                  uuid
case_id                       uuid
document_family               land_transcript|building_transcript|due_diligence_other
origin                        user_upload|partner_delivery|official_delivery
sensitivity_class             confidential|restricted_title
provenance_status             user_asserted|channel_verified|unknown
display_name                  private user-facing metadata
source_id                     registry key or user-upload
license_status / license_ref
case_purpose_snapshot
processing_policy_id
uploader_representation_code  bounded reviewed-policy assertion
notice_terms_version
processing_authorized_by_user_id / processing_authorized_at
retention_policy_id
document_status               active|superseded|deletion_pending|deleted
record_version                optimistic-concurrency version
created_by_user_id
created_at
superseded_at / deleted_at
```

Invariants:

- `workspace_id` and `case_id` are immutable and must match.
- A family label does not authenticate the document. A user-uploaded transcript remains
  `provenance_status=user_asserted` unless an approved channel proves otherwise.
- `display_name` may contain PII and is never used as a storage key, authorization input, or
  log field.
- Land and building transcripts have a non-downgradeable minimum sensitivity of
  `restricted_title`. A `due_diligence_other` upload starts quarantined/unclassified and
  cannot become available until an approved policy assigns its sensitivity. Derived
  artifacts inherit source sensitivity; only a separately validated redacted derivative may
  receive a narrower presentation policy.
- Availability requires an approved processing-policy reference, owning Case purpose,
  uploader representation/authority code, notice/terms version, actor, timestamp, and
  retention policy. These fields record the reviewed workflow decision; they do not state a
  legal basis or entitlement.
- “Current version” is a projection over non-deleted versions and explicit supersession. It
  is not a mutable pointer that can silently rewrite history.
- A Document is not Evidence and does not assert anything about a parcel, building, owner,
  right, or document authenticity.

### 6.2 `DocumentArtifact`

Responsibility: immutable metadata for one private stored object or derived rendition.

Conceptual fields:

```text
document_artifact_id          uuid
workspace_id / case_id / document_id / document_version_id
artifact_role                 original_file|normalized_file|extracted_text|page_image|redacted_preview|export
derived_from_artifact_id      nullable uuid
transformation_run_id         nullable uuid
transformation_method         nullable bounded registry key
transformation_tool / transformation_version nullable
transformation_config_digest  nullable hash
storage_backend               bounded registry key
bucket_id                     private bucket identifier
object_key                    server-generated private key
object_version                backend generation/version
declared_media_type
detected_media_type
byte_size
sha256
malware_scan_status           pending|passed|failed|error
content_validation_status     pending|passed|failed|error
availability_status           pending_upload|quarantined|available|rejected|deletion_pending|deleted
record_version                optimistic-concurrency version
created_by_user_id / created_by_service
created_at / available_at / deleted_at
retention_until
```

Invariants:

- No public URL is stored. `object_key`, `bucket_id`, and provider generation are server-only.
- Objects are immutable and never upserted. A replacement creates a new artifact and usually
  a new DocumentVersion.
- `sha256` detects byte equality and supports integrity checks; it does not establish
  authenticity, authorship, or legal validity. Cross-workspace hash lookup is forbidden.
- Only `available` artifacts may be downloaded or processed. Scan or validation error fails
  closed and keeps the object quarantined.
- Declared media type and filename are untrusted. Limits use detected type, actual size,
  archive expansion, page count, and parser budgets.
- Derived artifacts carry their parent artifact and transformation/tool version. Extracted
  text is as sensitive as the original file.

### 6.3 `DocumentVersion`

Responsibility: immutable snapshot of one received/procured edition and its source context.

Conceptual fields:

```text
document_version_id           uuid
workspace_id / case_id / document_id
version_number                positive integer within Document
supersedes_document_version_id nullable uuid
original_artifact_id          uuid after sealing
source_document_reference     encrypted or minimized private value
transcript_access_class       first|second|third|not_applicable|unknown
requested_print_scope         all|owner_specific|description_only|description_and_ownership|description_and_other_rights|other|unknown
source_issued_at              nullable timestamp copied from source
obtained_at                   timestamp
source_as_of                  nullable timestamp explicitly stated by source
page_count                    nullable positive integer
package_completeness          complete|possibly_incomplete|not_checked
sealing_status                pending|sealed|rejected
content_hash                  hash of accepted original artifact
record_version                optimistic-concurrency version
created_by_user_id / created_by_service
created_at
```

Invariants:

- Sealing binds exactly one accepted original artifact, version number, source metadata, and
  content hash. Those values are immutable after sealing.
- `source_issued_at`, `source_as_of`, and `obtained_at` are distinct. Missing source time stays
  null; obtained time is never substituted for it.
- A later transcript supersedes an earlier version for workflow presentation but does not
  erase it or automatically invalidate its historical observations.
- Package completeness describes the received file package, not the completeness of the
  registry, rights, or legal situation.
- This version does not model a negative section-review observation. “No entries observed,”
  “no other rights,” and equivalent absence output are prohibited until a separately
  designed `SectionReviewObservation` can bind the exact version/artifact, requested print
  scope, section presence, completeness, redaction/unreadable state, reviewer, citations,
  and mandatory limitations.

### 6.4 `ExtractedClaim`

Responsibility: private, field-level extraction suggestion from an exact DocumentVersion.

Conceptual fields:

```text
extracted_claim_id            uuid
workspace_id / case_id / document_id / document_version_id
source_artifact_id            original or extracted-text artifact
claim_type                    versioned registry key
section_type                  header|description|ownership|other_rights|footer|other
subject_candidate_type        case|parcel|building|unknown
subject_candidate_key         private normalized candidate, nullable
field_key                     versioned field registry key
raw_value                     encrypted/private typed value
normalized_value              encrypted/private typed value, nullable
value_schema
page_number                   one-based page, nullable only for non-paginated input
region_or_text_offsets        bounded citation coordinates/offsets
citation_hash                 hash of cited region/text
extraction_method             manual_entry|ocr|model|deterministic_parser
extractor_name / extractor_version / prompt_template_version
confidence                    nullable 0..1 with named method
created_by_user_id / created_by_service
created_at
```

Invariants:

- Every claim cites a source artifact, version, section, and page/region. A claim without a
  resolvable citation cannot be promoted.
- Confidence ranks review effort only. It cannot change source class, prove authenticity,
  confirm identity, or bypass review.
- Claims are not returned by generic Evidence endpoints and are not indexed into an external
  AI/vector service without a separately approved PII-processing contract.
- Claims are immutable suggestions. Accept/reject/supersede appends a private
  `claim_review_decision` with actor, time, reason, source claim, and created observation when
  accepted. Current review state is derived; accepting a claim never mutates it into a fact.
- Unknown, illegible, redacted, missing, and conflicting are explicit claim outcomes; they
  are never normalized to empty, zero, “none,” or “clean.”

### 6.5 `OwnershipObservation`

Responsibility: append-only record that an authorized reviewer confirmed a cited ownership
section displays particular registered-holder information for a subject at the document’s
stated time.

Conceptual fields:

```text
ownership_observation_id      uuid
workspace_id / case_id / document_id / document_version_id
subject_node_id               parcel or building graph node
case_property_link_id_snapshot
subject_property_relation_id  confirmed property_parcel|property_building edge
source_artifact_id            same-version artifact
registration_sequence_as_printed
registration_date_source_text nullable private source text
registration_date_normalized  nullable date
registration_cause_as_printed nullable private text/code
cause_date_source_text        nullable private source text
cause_date_normalized         nullable date
registered_holder_name_ciphertext
registered_holder_identifier_ciphertext nullable
registered_holder_address_ciphertext nullable
party_match_token             nullable workspace-keyed HMAC for review only
right_scope_numerator / right_scope_denominator nullable positive integers
right_scope_as_printed        exact private source text
certificate_reference_ciphertext nullable
related_other_right_sequences private structured child rows
other_registered_items        cited private child claims, not an unbounded JSON note
source_page / source_region / source_page_geometry
citation_scheme / citation_version / citation_hash
confirmed_by_user_id / confirmed_at / confirmation_reason_code
supersedes_ownership_observation_id nullable
created_at
```

Invariants and semantics:

- `human_confirmed` means “matches the cited document,” not “is the legal owner now.”
- The target must be an existing same-workspace parcel or building node reached through the
  owning Case’s current `case_property_link` and an eligible confirmed
  `property_parcel|property_building` relation. Both links are snapshotted and validated in
  the promotion transaction. If identity is unresolved or the subject belongs to another
  property in the same workspace, the claim remains case/document scoped; extraction cannot
  create a confirmed target.
- Each registration sequence is preserved separately. Co-ownership shares are exact
  numerator/denominator values when unambiguous, with original text retained. The system does
  not force shares to total one or infer missing holders.
- Names, masked identifiers, addresses, and similarity scores cannot merge people, create a
  global person identity, or add an `owns` edge to the general property graph.
- First/second/third transcript class and redaction affect what was visible. Hidden data stays
  unknown and is not reconstructed.
- Each normalized date preserves its source text and calendar. Normalization occurs only
  when unambiguous; otherwise the normalized value stays null.
- Observations are immutable human-confirmed records. A dispute or supersession appends an
  `observation_disposition`; a corrected observation may point to its predecessor. The older
  source and review record remain intact subject to retention policy.

### 6.6 `EncumbranceObservation`

Responsibility: append-only record that an authorized reviewer confirmed a cited
other-rights entry, restriction notation, or cross-reference appears in an exact document
version. “Encumbrance” is a product grouping, not a conclusion about legal effect.

Conceptual fields:

```text
encumbrance_observation_id    uuid
workspace_id / case_id / document_id / document_version_id
subject_node_id               parcel or building graph node
case_property_link_id_snapshot
subject_property_relation_id  confirmed property_parcel|property_building edge
source_artifact_id            same-version artifact
observation_kind              other_right_entry|restriction_notation|cross_reference
registration_sequence_as_printed
right_kind_as_printed         private source text/code
registration_date_source_text nullable private source text
registration_date_normalized  nullable date
registration_cause_as_printed nullable private text/code
party_roles                   typed private child rows: right_holder|debtor|setting_obligor
subject_registration_sequence_as_printed nullable
right_scope_numerator / right_scope_denominator nullable positive integers
right_scope_as_printed        nullable private source text
right_value_as_printed        nullable private source text
secured_amount_as_printed     nullable private source text with qualifiers
secured_amount_normalized     nullable exact decimal
currency_code                 nullable normalized bounded code
maximum_amount_as_printed     nullable private source text
secured_scope_as_printed      nullable private source text
interest_or_rent_as_printed   nullable private source text
late_interest_as_printed      nullable private source text
penalty_as_printed            nullable private source text
duration_as_printed           nullable private source text
repayment_date_source_text    nullable private source text
repayment_date_normalized     nullable date
common_collateral_refs        private structured child rows
other_registered_items        cited private child claims
source_page / source_region / source_page_geometry
citation_scheme / citation_version / citation_hash
confirmed_by_user_id / confirmed_at / confirmation_reason_code
supersedes_encumbrance_observation_id nullable
created_at
```

Invariants and semantics:

- Values and qualifiers are recorded “as printed.” A repayment date, duration, or
  restriction date does not let the system infer that a right is extinguished, enforceable,
  senior, satisfied, or current. An actual cancellation/discharge registration, if displayed,
  is a separately cited entry/observation and is never inferred from a repayment field.
- Right holder, debtor, and setting obligor are distinct typed child roles with separately
  encrypted displayed names/identifiers. They are never collapsed into one party field.
- Normalized dates and amounts always retain source text, calendar, currency, unit, and
  qualifier. Ambiguous values remain null in normalized columns.
- Registration order may be displayed as document data but is not converted into an
  automated priority conclusion.
- Common collateral and subject references are explicit child records so each can cite a
  page/line and be linked to an identity candidate. They are not comma-separated text or an
  uncited JSON blob.
- No row is created merely because no other-rights entry was extracted. Negative
  section-review observations are deferred and prohibited by this version.
- The same identity, redaction, conflict, PII, and supersession rules as
  OwnershipObservation apply.

## 7. Taiwan document profile

Official local-government guidance describes land and building registration transcripts as
having description (`標示部`), ownership (`所有權部`), and other-rights (`他項權利部`)
sections, with different print scopes and personal-data visibility. The architecture uses
those labels only as document structure; it does not encode legal conclusions. See the
[New Taipei City Land Administration transcript guide](https://www.land.ntpc.gov.tw/cp.aspx?Create=1&n=12855)
and the [Kaohsiung transcript-class guide](https://landp-ws.kcg.gov.tw/Download.ashx?n=5qqU5qGI5LiL6LyJLnBkZg%3D%3D&u=L0ZTMDEvRmlsZVBhdGgvMS9yZWxmaWxlLzAvNjU2Mi9jN2U4NjcxZC01NmMyLTQyNzYtODM0Ni1kMGJjZjMwZjI4NzkucGRm).

The profile records, when visible and understood:

- whether the subject is land or building;
- jurisdiction/land-office/section and land-number or building-number candidate;
- requested transcript class and print scope;
- issue/print time and page/package completeness signals;
- description, ownership, and other-rights section presence;
- registration sequence and exact source wording; and
- redaction/visibility limitations.

Field catalogs are versioned profiles, not universal columns forced onto every
due-diligence document. Unknown or unrecognized fields remain cited claims for review.
Parser/profile versions are recorded so a later profile can reprocess the same immutable
source without erasing the earlier run.

## 8. Evidence and graph linkage

### 8.1 Link rules

1. A Document is always linked to its owning Case.
2. A DocumentVersion may contain a parcel/building identity candidate without being linked
   to a graph node.
3. An authorized human may link a reviewed observation only through the owning Case's
   snapshotted current `case_property_link` and an eligible confirmed
   `property_parcel|property_building` relation to the subject node. Same-workspace
   reachability alone is insufficient. Mismatch or ambiguity blocks promotion and creates a
   bounded review reason.
4. Each promoted observation receives at most one Evidence projection through a unique,
   append-only observation/Evidence bridge. The observation is
   the private value; the stored Evidence row uses `value=null` and `value_ref` for a private
   observation reference, plus provenance, temporal scope, status, quality, coverage, and
   source artifact/version lineage.
5. `evidence_links` connects the Evidence item to the parcel/building node and, where useful,
   a Case node. It uses `describes`, `supports`, `contradicts`, or `limits`; it never uses a
   legal `owns` or `free_of_encumbrance` relation.
6. Claim-to-observation links and observation-to-Evidence links use explicit private bridge
   tables/FKs. The lineage is queryable without putting raw claim content into Evidence JSON.
7. Corrections append a new observation, Evidence item, lineage edge, and conflict or
   supersession link. The losing evidence is not silently deleted while retention permits it.

The narrow document-Evidence writer performs one transaction that inserts the Evidence item,
unique observation/Evidence bridge, applicable `evidence_links` and `evidence_lineage`, and
success audit event. It never updates the immutable observation. A partially written
projection is rolled back and retried idempotently.

### 8.2 Safe Evidence projection

The generic Evidence row must not contain party names, identifiers, addresses, document text,
debt details, certificate numbers, or unrestricted amounts. The stored row uses the existing
mutually exclusive value contract exactly as follows:

```text
fact_type         = title.ownership_observation
value             = null
value_ref         = ownership-observation:<uuid>
value_schema      = ownership-observation-ref-v1
source_type       = document
source_record_id  = <ownership_observation_id>
evidence_status   = limited
raw_artifact_ref  = artifact:<uuid>  # compatibility pointer until the FK bridge exists
```

Non-sensitive version/section/citation limitations live in the existing bounded
coverage/quality/lineage metadata. The generic Evidence DTO returns `value_ref` but never
dereferences it. A separate purpose-specific document endpoint may return an authorized,
field-minimized observation DTO after a fresh access check. The existing `raw_artifact_ref`
string is not a storage URL. A future migration adds workspace-consistent
artifact/observation/Evidence bridges rather than relaxing the `value`/`value_ref`
exclusivity or changing legacy references in place.

Before document-derived Evidence is exposed, Evidence rows need an access scope such as
`workspace_standard|case_restricted`, a `case_id` where restricted, and RLS/service checks
that preserve current behavior for existing standard evidence while restricting document
evidence. Without that change, sensitive title details remain solely in `vnext_private`.

## 9. Ownership and other-rights semantics

- Property identity, registered-holder observation, beneficial ownership, authority to sell,
  occupancy, contactability, and legal ownership are different concepts. Stage 5 models only
  cited document observations.
- A transcript is a source snapshot. Its issue/as-of time, class, scope, sections, redactions,
  and package completeness travel with every observation. It is never “current” merely
  because it is the newest file in this workspace.
- `PropertyEntity` remains an application aggregate. No owner name, owner ID, contact address,
  or ownership percentage is added to it.
- A party string is not a person identity. Matching uses a workspace-keyed, purpose-limited
  review token at most; it cannot create an automatic party merge or cross-workspace index.
- Human confirmation verifies transcription against the cited page. It does not verify source
  authenticity unless an approved delivery channel separately supplies that provenance.
- Missing section, unreadable text, redaction, partial print scope, stale source time,
  unresolved subject, and conflicting versions stay explicit and block any “no rights,”
  “sole owner,” “clean,” or equivalent output.
- This version cannot output “no entries observed” or “no encumbrance.” If a future
  `SectionReviewObservation` is designed and implemented, its UI and API must display the
  supplied-section, print-scope, completeness, redaction, and unreadable limitations beside
  every negative observation.
- A professional may later record a legal interpretation in a separate, access-controlled
  model. It must identify the author, role, scope, time, jurisdiction, cited observations,
  assumptions, and review status. Stage 5 does not define or automate that conclusion.

## 10. Private storage architecture

### 10.1 Bucket and object rules

- Use a private bucket dedicated to restricted case documents, or a private sensitivity-class
  bucket whose policies are equivalent. `public=true` is prohibited.
- The server generates keys such as
  `<workspace>/<case>/<document>/<version>/<artifact>`. Original filenames are private
  metadata, never a path segment or authorization rule.
- Bucket-level limits restrict accepted media types and object size; the completion service
  rechecks detected type, actual bytes, archive expansion, pages, and checksum.
- Direct upload, if selected, uses a short-lived operation bound to one pending Artifact,
  exact object key, maximum bytes, and expected media class. Completion is idempotent.
- Upload completion moves metadata through `pending_upload -> quarantined -> available` only
  after validation and malware scanning. Failure remains quarantined/rejected and auditable.
- No overwrite/upsert is used. A new upload creates a new immutable object/version.
- Storage paths, provider credentials, secret/service keys, and object listings never enter a
  browser DTO. Supabase Storage object `owner_id` alone is not case authorization.

Supabase private buckets apply access control to object operations, while public buckets
bypass read access controls. Current platform guidance also notes that signed URLs remain
valid until expiry and are not revoked by Auth-key rotation. The design therefore uses short
expiry and a server stream for the highest sensitivity. See [Storage access control](https://supabase.com/docs/guides/storage/security/access-control),
[private-bucket downloads](https://supabase.com/docs/guides/storage/serving/downloads), and
[Storage ownership semantics](https://supabase.com/docs/guides/storage/security/ownership).

### 10.2 Bounded download

1. The client requests a download for an Artifact ID, not an object key.
2. FastAPI authenticates the user and checks current membership, allowed role, owning Case,
   assignment/purpose, sensitivity, artifact availability, retention state, and requested
   rendition.
3. The service appends an allowlisted audit event for success or denial.
4. For ordinary approved documents, the server issues a signed URL with a 60-second default
   and a hard maximum of 300 seconds. It is returned in a `Cache-Control: private, no-store`
   response and is never persisted, placed in analytics, or logged.
5. For `restricted_title` originals, exports containing party data, or any case requiring
   immediate revocation/completed-access audit, the server returns a server-mediated stream
   instead of exposing a reusable signed URL. Each stream request is freshly authorized; its
   response itself contains no reusable capability. If product policy later requires a
   single-consumption grant, it uses a nonce-backed grant atomically consumed before bytes
   are sent.
6. Content-Disposition uses a sanitized download name; the stored original filename is not
   reflected without authorization. Browser responses use `Referrer-Policy: no-referrer`.

A signed URL is a time-bounded bearer capability, not proof of the viewer’s identity after
issuance. Audit distinguishes URL issuance from a server-streamed completed access. Removing
membership blocks new issuance immediately; previously issued URLs remain bounded by the
short TTL, which is why higher-risk content uses the server stream.

## 11. Authorization

All checks require an authenticated Supabase `auth.users.id`, active workspace membership,
same-workspace resource chain, and a purpose-specific FastAPI operation. JWT
`user_metadata`, a caller-provided workspace header, a storage prefix, and `TO authenticated`
alone are not authorization.

The maximum conceptual permissions are:

| Operation | owner/admin | manager | member | viewer |
| --- | --- | --- | --- | --- |
| Upload ordinary `due_diligence_other` document | yes | yes | explicit Case upload policy | no |
| Upload/procure title transcript | explicit purpose | assigned Case + explicit purpose | no by default | no |
| Read redacted metadata | yes | assigned Case | case policy | no by default |
| View original restricted title file | explicit purpose | assigned Case + explicit purpose | no by default | no |
| Review claims | reviewer capability | assigned reviewer capability | no by default | no |
| Human-confirm an observation | reviewer capability | assigned reviewer capability | no by default | no |
| Export/share restricted content | explicit policy and recipient scope | no by default | no | no |
| Set/release retention hold or approve deletion | owner/admin command | no by default | no | no |

These are ceilings, not grants. Land/building transcripts are always `restricted_title`, so
the ordinary-document member rule can never authorize them. Document sensitivity, Case purpose/state, assignment,
retention hold, source/license, and feature gates may narrow them. There is no generic member
SELECT on document/claim/observation base tables. The browser receives allowlisted DTOs from
the BFF; private tables remain outside exposed schemas and the Data API.

The normal request role does not own tables, bypass RLS, or hold a Storage service key. If a
server-side storage broker requires elevated object operations, it is isolated, narrowly
scoped, never invoked directly by the browser, and repeats domain authorization before each
operation.

## 12. PII and logging

Title documents can contain names, identifiers, dates of birth, addresses, registration
references, financial obligations, and relationship data. Treat original files, extracted
text, claims, observations, page images, previews, and exports as restricted PII.

- Sensitive scalar values live in `vnext_private`; encrypt high-risk fields with keys outside
  the database where the deployment threat model requires it.
- Search/matching uses the minimum workspace-keyed derived token. No global owner directory,
  plaintext full-text owner index, or cross-workspace person lookup is created.
- Browser list DTOs use masked/minimized labels. Full content requires an additional
  authorization operation and is excluded from client persistence, URL/query/hash, error
  monitoring, and analytics.
- External OCR/AI, support tickets, screenshots, and test fixtures receive no production
  document unless an explicit processing basis, processor contract, region, retention,
  incident, and no-training policy is approved.
- Test fixtures are synthetic and carry `source_environment=test`; they cannot become
  production observations or available production Evidence.

Application logs and audit metadata may contain only bounded IDs, event type, state
transition, safe reason code, byte/page counts, media class, request ID, actor ID, and outcome.
There is no document content in logs. Logs and audit metadata must not contain:

- original filename or display name;
- document bytes, extracted text, snippets, or claim values;
- names, identifiers, addresses, registration/certificate numbers, amounts, or contact data;
- object keys, signed URLs/tokens, authorization headers, cookies, or provider bodies; or
- raw exceptions whose message may contain parser/document content.

Errors use fixed codes and a request ID. Parser/provider details are sanitized before they
cross the service boundary.

## 13. Retention, deletion, and restore

No universal legal retention duration is asserted here. Every available Document must have
an approved `retention_policy_id` selected by document family, source/license, Case purpose,
and workspace policy. A document without an applicable policy cannot leave quarantine in
production.

Lifecycle:

1. A delete request immediately disables new download/processing grants and creates an
   audited `deletion_pending` state.
2. The retention service evaluates active retention hold, source/license obligations,
   dependent approved exports/decisions, and the selected policy. A hold blocks byte erasure
   but does not broaden access.
3. Eligible original and derived objects are deleted by explicit Artifact ID/object version.
   The worker verifies object absence before setting `deleted_at`.
4. Extracted text and page images are deleted with or before the original unless the approved
   policy explicitly requires otherwise. Derived data never receives a longer accidental
   lifetime.
5. Claims and observations are deleted, minimized, or retained only as the applicable policy
   permits. Retained audit contains no content. A non-sensitive tombstone preserves IDs,
   deletion time, actor/service, policy, outcome, and safe reason.
6. Deletion failure remains retryable and visible to operators without restoring user access.
7. Backup retention is documented separately. A restore procedure replays deletion
   tombstones before restored objects can become available, preventing deleted content from
   silently returning to the application.

Workspace archive is not bulk document deletion. User departure revokes access immediately
while authored observations and audit attribution follow their independent policies. Export
and subject-access workflows return only data the current actor is authorized to receive and
are themselves audited.

Retention hold is orthogonal to document lifecycle. It is represented by append-only
`document_retention_holds` rows with scope, safe reason code, setter, set time, and policy
authority reference. Releasing a hold appends a separate `document_retention_hold_releases`
record referencing the immutable hold, with release actor, time, and safe reason. Current
hold state is derived from that chain; it is not a `document_status`, and release never
updates or deletes hold history.

Taiwan’s official Personal Data Protection Act source is the policy/legal review starting
point, not a conclusion supplied by this architecture: [Personal Data Protection Act](https://law.pdpc.gov.tw/LawContent.aspx?id=FL010627).

## 14. Audit contract

Required event families:

```text
document.created
document.upload_initialized
document.upload_completed
document.validation_passed|failed
document.version_sealed
document.metadata_viewed
document.download_issued|streamed|denied
document.claims_generated
document.claim_reviewed
document.observation_confirmed|disputed|superseded
document.evidence_linked
document.share_created|revoked|accessed
document.retention_hold_set|released
document.deletion_requested|completed|failed
document.ai_run_started|completed|failed|approved
```

Each event records actor/service, workspace, operation, resource type/ID, request ID,
idempotency hash where relevant, outcome, safe reason code, and allowlisted references. It
does not record before/after document content. Consequential state and its success audit are
committed atomically where possible. Denials are audited without revealing whether a
cross-workspace resource exists.

User-facing Case activity is separate from security audit. An activity may say that a
document was added or reviewed, but must use minimized labels and must not duplicate private
content.

The current `audit_events.actor_user_id` is mandatory and its insert policy supports only the
authenticated user actor. It cannot honestly represent scanners, extraction jobs, retention
workers, or deletion workers. Before the first worker is enabled, an additive audit migration
must introduce `actor_type=user|service`, a nullable user actor, a bounded registered service
principal, an exactly-one-actor constraint, and narrowly granted append-only worker/audit
writer paths. The existing user policy remains intact; a service actor never impersonates an
`auth.users` row or gains audit read/update/delete access.

## 15. Eventual OCR and AI boundary

No OCR or AI implementation is authorized by this document.

An eventual extraction pipeline must be asynchronous and permission-scoped:

```text
available Artifact
  -> approved processing job with Case purpose
  -> isolated malware-safe parser/OCR environment
  -> extracted-text Artifact + tool/model/version lineage
  -> ExtractedClaims with exact citations and explicit unknowns
  -> authorized human review
  -> append-only Observation
  -> minimized Evidence projection
```

AI/OCR may:

- classify a document family/section as a suggestion;
- extract text and field candidates;
- normalize dates, registration sequences, fractions, and amounts while preserving source
  text;
- propose parcel/building identity candidates;
- identify contradictions, missing pages/sections, unreadable areas, and questions for a
  reviewer;
- draft a citation-grounded, clearly labeled summary of confirmed observations; and
- suggest redactions and the next due-diligence step.

AI/OCR may not:

- authenticate a document or promote a user upload to official provenance;
- confirm parcel/building identity, merge entities, or create confirmed graph relations;
- accept its own claim or create a human-confirmed observation;
- identify a legal owner or infer a person match from a name/masked ID;
- decide that a right is valid, invalid, released, senior, enforceable, or extinguished;
- infer absence from a missing, redacted, unreadable, partial, or stale section;
- declare ownership, title clean, no encumbrance, transaction safety, or legal compliance;
- expose document content to a model without approved processing and minimization; or
- write directly to authoritative Evidence/observation tables, export, share, procure, or
  contact a person.

Every run records provider/model/tool version, processing region/class, prompt/template
version where applicable, source Artifact IDs and hashes, output Artifact/claim IDs, actor or
service, request ID, timestamps, status, and approval state. Logs contain identifiers and
bounded status only, never prompts or document content. Unsupported output is discarded or
marked unsupported; it is never backfilled as evidence.

## 16. Conceptual service operations

These routes are an eventual contract shape, not implementation authorization:

```text
POST /v1/cases/{case_id}/documents/upload-init
POST /v1/documents/{document_id}/versions/{version_id}/upload-complete
GET  /v1/cases/{case_id}/documents
GET  /v1/documents/{document_id}
POST /v1/document-artifacts/{artifact_id}/download
POST /v1/document-versions/{version_id}/claims:extract
POST /v1/extracted-claims/{claim_id}:accept
POST /v1/extracted-claims/{claim_id}:reject
POST /v1/ownership-observations
POST /v1/encumbrance-observations
POST /v1/documents/{document_id}:request-deletion
```

Mutations require an `Idempotency-Key` and optimistic version where state can race. Responses
return IDs, safe status, timestamps, citations, and limitations. They never return storage
paths, raw provider bodies, private-table rows, or permanent URLs. A denied cross-workspace
request uses a non-enumerating not-found/forbidden contract.

Claim accept/reject operations append `claim_review_decision` rows. Observation dispute and
supersession operations append `observation_disposition` rows and, for corrections, a new
observation. None of these operations updates the source claim or observation.

## 17. Likely migrations

No migration is created in this stage. The current registry ends at `017`; sequence `018` is
only the current likely next slot and must be revalidated at implementation time.

1. **Document vault foundation** — private `documents`, `document_versions`, and
   `document_artifacts`; composite workspace/Case FKs; immutability/lifecycle guards;
   processing-policy/uploader-representation records; indexes; grants/FORCE RLS; idempotent
   upload completion; and audit actor evolution for registered user/service principals. The
   private bucket and Storage policies are a separately reviewed deployment change, not
   assumed by SQL table creation.
2. **Document access and retention** — purpose/capability policy records if needed, bounded
   download grants, append-only retention hold intervals, lifecycle events/projections,
   deletion tombstones, retryable deletion outbox, and restore reconciliation.
3. **Extraction foundation** — `extracted_claims`, extraction runs, claim citations, derived
   artifact lineage, and append-only `claim_review_decisions`. It still includes no OCR
   provider by default.
4. **Ownership/other-rights observations** — private observation tables, structured child
   party/collateral references, `document_subject_links` that snapshot Case-property and
   confirmed subject relations, claim links, append-only observation dispositions,
   supersession/conflict constraints, and human-review commands.
5. **Evidence access bridge** — workspace-consistent observation/artifact/Evidence bridges,
   `case_restricted` evidence scope, safe projections, and revised RLS that preserves existing
   standard-evidence access, plus a narrow audited writer for `source_type=document` rather
   than broadening the normal Evidence insert policy.

Migration acceptance includes clean/upgrade/repeat rehearsal, registry checksum validation,
FK/index review, table ownership and grants, forced RLS, cross-tenant and role-negative tests,
append-only tests, no-delete application grants, and rollback by feature gate. Applied
migration files are never renamed.

## 18. First implementation slice

Deliver only the private document-vault boundary:

- one authenticated workspace Case;
- manual selection of `land_transcript`, `building_transcript`, or
  `due_diligence_other` without content interpretation;
- approved processing-policy and retention-policy references, Case-purpose snapshot,
  uploader representation/authority code, notice/terms version, actor, and timestamp before
  availability;
- enforced `restricted_title` minimum for land/building transcripts and quarantine until an
  approved classification for other uploads;
- one immutable original PDF/image artifact per DocumentVersion;
- private bucket, server-generated object key, strict upload bounds, quarantine, media
  validation, malware scan adapter, checksum, and sealed version;
- role/purpose/assignment-authorized metadata list and download;
- 60-second signed download for allowed ordinary renditions and freshly authorized
  server-mediated streaming, with no reusable response capability, for restricted originals;
- append-only upload, validation, download, denial, retention, and deletion audit;
- retention-policy assignment, deletion request, verified byte deletion, and tombstone; and
- feature flag default-off plus synthetic security/tenant tests.

Explicitly exclude partner procurement, cost/points, OCR, AI, extracted text, claim parsing,
ownership or encumbrance observations, person matching, sharing, exports, public links,
mobile offline copies, and legal conclusions.

Exit criteria:

- no public bucket or permanent object URL exists;
- cross-workspace, inactive-member, unassigned-manager, viewer, wrong-Case, deleted,
  quarantined, and expired-grant access all fail without resource enumeration;
- members cannot access land/building transcripts or `restricted_title` artifacts; ordinary
  document member upload/read succeeds only when the explicit Case policy grants that exact
  operation;
- member removal blocks new access immediately and prior signed access expires within the
  bounded policy;
- original and derived object keys cannot be selected/listed from the browser;
- upload replacement cannot overwrite an existing object/version;
- validation and malware failure never become available;
- logs, audit, analytics, errors, and frontend state contain no document content, filename,
  object key, signed URL, token, or title PII;
- deletion removes exact bytes, leaves only the approved tombstone/audit, and remains deleted
  after restore rehearsal;
- production rollout remains disabled until deployment region, processor/storage terms,
  incident response, backup deletion, retention policies, and live JWT/RLS/Storage isolation
  receive owner/security/privacy approval.

## 19. Acceptance gates for later observations

Before OwnershipObservation or EncumbranceObservation is enabled:

- the owning Case's current `case_property_link` and an eligible confirmed
  `property_parcel|property_building` relation to the subject are snapshotted and validated;
  limited evidence coverage may remain visible, but limited or unresolved identity cannot be
  promoted;
- the exact source version, page/section citation, transcript class/scope, as-of time,
  provenance, completeness, and redaction limits are available to the reviewer;
- private PII encryption/masking and restricted retrieval pass tests;
- two-version corrections, co-ownership fractions, partial sections, unreadable fields,
  conflicts, common collateral, missing time, and deleted source behavior are tested;
- Evidence receives only a minimized pointer and restricted access scope;
- generic graph/Evidence endpoints cannot enumerate party or debt data;
- the UI says “observed in the cited document” and never “legal owner,” “clean title,” or “no
  encumbrance”; and
- AI/system roles cannot set the human reviewer fields or observation status.

## 20. Architecture result

| Decision area | Result |
| --- | --- |
| Domain model | `Document -> DocumentVersion -> DocumentArtifact/ExtractedClaim -> human-reviewed Observation`, with legal interpretation separate |
| Storage | Private immutable objects, quarantine/scan, no overwrite/public URL, 60–300 second bounded delivery, server stream for highest sensitivity |
| Authorization | Workspace + Case + active membership + role + assignment + purpose + sensitivity, checked at each operation |
| Evidence linkage | Minimized restricted Evidence pointer plus existing lineage/subject links; private content never enters the general graph |
| Ownership semantics | Document-bound, temporal registered-holder observation only; no owner identity merge or legal/current-title inference |
| AI boundary | Extract and suggest with citations; never authenticate, confirm ownership/right status, or declare title clean |
| Migration posture | Five prospective additive slices; no migration or Storage change in this stage |
| First implementation | Private, auditable upload/version/download/deletion vault with no OCR or observation parsing |

**Architecture decision: GO** for planning and implementing the bounded private-vault first
slice after its named owner/security/privacy prerequisites are approved.

**Production decision: NO-GO** for title procurement, OCR/AI processing, ownership or
encumbrance conclusions, public sharing, or production rollout based on the current
repository state.
