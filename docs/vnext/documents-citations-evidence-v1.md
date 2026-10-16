# Documents, Citations & Evidence Graph v1

Status: Wave 5 schema-independent implementation; no migration or storage enabled.

Current-main integration and final acceptance are recorded in
[the Wave 5 acceptance record](wave5-current-main-acceptance.md). The verification
section below describes the original pre-integration run.

## Scope and design

Make decisions traceable to their exact evidence version. Reuse the Evidence ledger,
property graph, case projections, and title-document trust ladder. Keep source,
document/version, observation, claim, citation, verification and lifecycle separate.
An uploaded registry extract is user supplied, not authenticated official evidence.

The intake boundary consumes bounded byte chunks and strict metadata. It rejects
unsafe names, unsupported signatures, active PDF content and malformed data exports.
It returns an immutable quarantine receipt, never retained bytes, extracted text,
an ownership conclusion or a storage URL. PDF/image acceptance is not a malware scan.
No route exposes this boundary before durable authorization, scanning and storage exist.

The frontend projects saved case fields into observation → claim → decision edges.
These are browser snapshot references, explicitly not canonical Evidence ledger IDs.
Citation identity includes case, immutable snapshot version and observation ID; labels,
translations, array order and current wall time do not participate. Report rendering
and the provider-free Copilot resolver share this contract. Document metadata has a
strict, case/workspace-scoped read adapter for a future authorized server projection.
No document metadata is added to generic browser case storage.

Freshness and supersession are projections. Missing freshness policy means unknown;
failed and superseded evidence cannot support current claims. Historical citations
remain resolvable and carry limitations. New versions never rewrite old records.

Browser snapshots have no durable archive in the existing repository. Frozen reports
retain their values and provenance, with report-local citation anchors. A citation
opened against a different browser snapshot shows unavailable instead of silently
rebinding. Durable historical document reads require the future private persistence
adapter to supply all immutable versions; this release does not claim a document vault.

The Copilot contract is `proptech-citation-v1`. Supply only a citation ID to
`resolveCopilotCitation(graph, caseId, citationId, workspaceId)` using a graph obtained
through an authorized read. Document graphs require an exact workspace as well as case;
browser graphs use null workspace and are never promoted to server authority. Resolver
output includes source, immutable version, observation, dates, verification, state,
claim/decision IDs, internal reference and `supportsCurrentClaim`. Unresolved IDs return
null; the consumer must mark the statement unsupported. A resolved historical citation
does not support a current claim. A reviewed, clean, temporally applicable document
observation can support a bounded claim; contradictions block current support. This is
not identity confirmation or a legal determination. The local snapshot fingerprint
reuses the existing change detector and is not an authentication token or durable ID.
Browser editions are anchored by case ID and the repository's `savedAt`, not localized
values or freshness projections. Persistence must replace this timestamp-based local
edition identity with an immutable server revision; out-of-band edits that reuse a
saved timestamp are outside the browser repository's version guarantee.

Affected-decision navigation opens the existing Decision Room saved-evidence section,
with a second link to the relevant market/location/risk/finance analysis. These are
domain-level review dependencies; no manual note or task is falsely claimed to have
cited evidence. The room links back to the claim/source graph. Persisted per-decision
citations will require explicit immutable decision revisions and claim links.

Report references use the same citation shape through `reportEvidenceReferences` and
`ReportCitationReferences`; future authorized document reports can render document
citations through the same component. Intake receipts are deliberately not browser DTOs:
a server adapter must minimize/map snake_case receipt fields to `DocumentMetadata` and
must never mark a pending scan clean or extraction successful. Extraction, scan and human
verification are independent gates. No provider, OCR, storage or SQL is invoked here.

## Future persistence proposal (no SQL registration)

After Wave 1C releases the migration sequence, propose private case-scoped Document,
DocumentVersion, DocumentArtifact, ExtractionAttempt, Observation, Claim, Citation,
ClaimEvidenceLink and append-only lifecycle/verification event records. Reuse existing
evidence_items, evidence_lineage, evidence_links and property graph subjects through
workspace-consistent composite foreign keys. Document is the business aggregate;
DocumentVersion and all source facts are immutable. `supersedes_id` must target the
same workspace/case/document and cannot form cycles or fork silently.

Document classes: land/property registry extracts, cadastral/map evidence, permits,
zoning evidence, valuation/report attachments and official PDF/data exports. V1 intake
formats: PDF, PNG, JPEG, UTF-8 JSON; maximum 10 MiB. Other formats fail closed.
Store server-generated IDs, SHA-256, detected media type, byte length, declared class,
source classification, observed/effective/expiry dates, scan/extraction/verification
states and bounded failure codes. Store filenames privately only if required; never
use them as paths, log fields or citation IDs. No arbitrary remote URL ingestion.
Persist the authenticated actor, server receipt time and request correlation privately;
the caller-declared observed date must never replace the server ingestion timestamp.

Authorization must combine current membership/role, case assignment, purpose and
sensitivity before every metadata, graph, citation, report or download read. Existing
workspace-wide Evidence RLS is insufficient for title PII. Narrow audited writers
bridge human-reviewed observations into the ledger without relaxing generic inserts.
Browser DTOs exclude party data, extracted text, storage paths, secrets and signed URLs.
Canonical public URLs are optional reviewed source metadata, never synthesized.

Enable retained intake only with private immutable artifact storage, bounded streaming,
malware/content scanning (including encoded PDF actions), audit, retention/license
policy, deletion/tombstones and principal-bound transactions. Extraction attempts are
append-only, with pending/failed/unknown distinct from success; OCR is not implemented.
No automatic identity, title, ownership, legal-right or safety promotion.

## Implementation and verification plan

- [x] Strict quarantine intake and adversarial tests, without providers or persistence.
- [x] Stable scoped citation/read model, lifecycle projection, document metadata adapter;
      test locale independence, historical resolution and isolation.
- [x] Accessible case evidence page, provenance, bidirectional decision links, shared
      citation component, report rendering and Copilot resolver seams in four locales.
- [x] Run model/security tests, graph regressions, keyboard/mobile browser checks,
      typecheck, lint and build; review diff and create one local commit.

Review focus: forged cross-case links, encoded unsafe filenames, expired evidence at
the exact boundary, unknown dates, snapshot changes with old report citations, and
provider calls caused by navigation. No migration, push, deploy or migration execution.

## Verification — 2026-10-16

- Focused backend/property graph/parcel/report regressions: 114 passed; final intake
  security run: 38 passed.
- Citation, case/report model and Decision Room regressions: 42 passed.
- Production browser build (`npm run build:e2e`, Turbopack): passed, including TypeScript.
- Standalone typecheck: passed. Full lint: zero errors, 23 pre-existing warnings.
  Changed-file lint also had zero errors; the two E2E files are excluded by the
  repository's existing lint configuration and were verified by Playwright.
- Chromium browser suite: 5 passed across zh-TW, en, ja and ko; 390px keyboard/mobile
  provenance, reload stability, cross-case rejection, Decision Room round trip, report
  print references, 1280px navigation and malformed-storage blocking. The four locale
  flows asserted zero provider calls and no evidence-page writes to saved case storage.
- No migration SQL or migration registration was added. Persistence and durable
  document history remain the future work described above.
