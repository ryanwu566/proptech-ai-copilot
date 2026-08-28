# Evidence Architecture v1

Status: Stage 0 conceptual contract; no evidence table or provider is enabled

## 1. Definition and invariants

Evidence is an attributable statement supplied by an official/partner source, provider,
user, document or deterministic calculation. It is not a UI badge and not an AI conclusion.

Every evidence item must answer:

```text
who/what supplied it?
when was it retrieved and effective?
what subject and fact does it describe?
what geographic/semantic coverage applies?
what is its status and quality?
how was it derived and what does it supersede?
where is the raw artifact, if retention is permitted?
```

Unknown, unavailable, no-match and unverified remain distinct. They may not be rendered or
stored as `safe`, `0`, `none`, `official`, `complete` or `available`.

## 2. Evidence DTO

Conceptual JSON DTO:

```json
{
  "id": "uuid",
  "workspace_id": "uuid",
  "subject_type": "property",
  "subject_id": "uuid",
  "fact_type": "address.normalized",
  "value": {},
  "value_ref": null,
  "value_schema": "address-fact-v1",
  "source_id": "tgos-address",
  "source_type": "official",
  "provider": "tgos",
  "retrieved_at": "RFC3339 timestamp",
  "effective_at": "RFC3339 timestamp or null",
  "expires_at": "RFC3339 timestamp or null",
  "coverage": {},
  "quality": {},
  "status": "available",
  "license": {},
  "lineage": {},
  "raw_artifact_ref": null,
  "created_by": "authenticated principal or system job",
  "created_at": "RFC3339 timestamp",
  "supersedes_id": null
}
```

Field rules:

| Field | Contract |
| --- | --- |
| `id` | Opaque stable identifier; never derived from the fact value |
| `workspace_id` | Mandatory tenant boundary for private evidence |
| `subject_type/id` | Typed subject reference; must resolve in the same workspace |
| `fact_type` | Versioned registry key, not arbitrary UI text |
| `value` | Small, validated JSON value; null when status has no usable fact |
| `value_ref` | Reference to a large/private typed artifact; mutually exclusive with inline value unless the schema expressly allows a summary |
| `source_id/type` | Registry source and `official|partner|user|deterministic|document|demo|test` classification |
| `provider` | Adapter/version that retrieved or calculated the item; nullable for direct user input |
| `retrieved_at` | When the system obtained it; never substituted for source effective date |
| `effective_at` | When the fact applies; unknown remains null with a limitation |
| `expires_at` | Explicit source/contract expiry; absence does not imply perpetual freshness |
| `coverage` | Geographic, temporal, subject and field coverage plus known gaps |
| `quality` | Method/version, confidence, validation checks and limitations |
| `status` | Controlled lifecycle/evidence status below |
| `license` | License/terms version, attribution, commercial/redistribution decision and evidence of review |
| `lineage` | Parent evidence, transformations, code/rule/model versions and source record fingerprint |
| `raw_artifact_ref` | Private artifact pointer; never a public storage URL |
| `created_by` | Authenticated principal, provider job or deterministic service identity |
| `supersedes_id` | Prior evidence corrected/replaced by this immutable version |

Values, source, retrieval time and lineage are immutable. A correction appends a new item and
sets `supersedes_id`; it does not edit history. Controlled status changes are separate
append-only lifecycle events or a narrowly mutable projection backed by audit.

## 3. Status model

| Status | Meaning | Value rule | Downstream rule |
| --- | --- | --- | --- |
| `available` | Fact is present and passes its declared contract | validated value/value_ref required | usable within stated coverage and freshness only |
| `limited` | Some fact is usable but coverage/quality is materially limited | value allowed with explicit limitation | may inform review; cannot fill uncovered dimensions |
| `unavailable` | Provider/source could not supply the fact | value null | show failure/unavailability; never infer absence |
| `unknown` | The truth/status cannot be determined | value null | preserve unknown; request more evidence |
| `stale` | Previously usable item is outside its freshness policy | historical value retained but flagged | do not represent as current; fresh retrieval required for consequential action |
| `conflicting` | Materially incompatible items exist | conflicting item references required | block automatic confirmation/consequential action |
| `user_provided` | User supplied a value/artifact | validated value/ref required | label user source; no official promotion without independent evidence |
| `unverified` | Format may be accepted but authenticity/meaning is not verified | value/ref may exist | not authoritative; cannot confirm identity/title/safety alone |

Provider transport states such as `error`, `not_configured`, `not_checked` and `no_match` are
recorded in provider attempts. Their evidence mapping is conservative:

- `error|not_configured|not_checked` -> `unavailable|unknown`;
- `no_match` -> a scoped negative-observation fact only if coverage and query semantics are
  proven, otherwise `unknown`;
- `demo|test` -> non-production evidence namespace and never `available` in production.

## 4. Coverage and quality

`coverage` is structured rather than a free-text claim:

```json
{
  "geography": {"kind": "point|district|dataset", "value": "...", "status": "known|partial|unknown"},
  "time": {"from": null, "to": null, "status": "known|partial|unknown"},
  "subject_scope": "address|parcel|building|listing|district|other",
  "fields": ["..."],
  "gaps": ["bounded reason code"]
}
```

`quality` contains named, versioned dimensions rather than one unexplained score:

```text
confidence: decimal or null
confidence_method: versioned method or null
validation_status: passed|limited|failed|not_checked
source_record_status: official|partner|user|derived|unknown
precision: source-specific structured value
limitations[]
```

Confidence does not override status, source class, coverage or human confirmation.

## 5. Freshness

Freshness is a projection over evidence timestamps and source policy; it does not rewrite the
source fact.

1. Use explicit `expires_at` when contractually supplied.
2. Otherwise use the reviewed source registry cadence and fact-type policy.
3. If no policy/effective date is known, freshness is `unknown`, not current.
4. At/after expiry, project `stale`; retain original `status` and value for history.
5. Consequential operations declare their maximum acceptable freshness. Title purchase,
   identity confirmation, valuation publication and hazard conclusions do not share one TTL.
6. Cache age is not source freshness. `retrieved_at` is not automatically `effective_at`.

## 6. Lineage

Minimum lineage structure:

```json
{
  "source_record_id_hash": "optional non-reversible reference",
  "source_artifact_id": "uuid-or-null",
  "parent_evidence_ids": [],
  "transformation": "normalization|aggregation|calculation|manual_review|none",
  "transformation_version": "version-or-null",
  "rule_version": "version-or-null",
  "input_hash": "canonical-input-hash-or-null",
  "output_hash": "canonical-output-hash-or-null"
}
```

Deterministic calculations store input evidence IDs, rule/code version and output evidence.
Aggregates link a release/artifact and aggregation method. AI output is an Artifact or AI
Synthesis record referencing evidence; it is not written back as authoritative evidence.

## 7. Provider contract

All providers implement a conceptual asynchronous contract:

```text
Provider.resolve(request, context) -> ProviderResult<T>

ProviderResult:
  provider_id
  provider_version
  status                 # available|limited|unavailable|no_match|error
  data                   # null unless status permits it
  source_metadata
  retrieved_at
  effective_at
  coverage
  quality
  license_metadata
  errors[]               # bounded codes, retryability, no secrets/raw body
  raw_artifact_ref       # optional private reference
  environment            # production|demo|test
```

Provider request context includes request ID, workspace, purpose, deadline and allowed source
policy. It never passes user-controlled provider URLs or frontend credentials. Adapters use
bounded timeouts/retries and preserve partial failure. `data` and success status must agree.

Production rules:

- Provider failure cannot return a fake successful result.
- A result missing required source, retrieval, coverage, status or license metadata cannot
  become `available` evidence.
- Mock/fixture adapters set `environment=demo|test`; database constraints/service checks
  prevent them from becoming production evidence.
- A fixture contract test proves DTO behavior only. Credentialed/snapshot acceptance proves
  reachability, source and coverage separately.

## 8. Conflict handling

Evidence is conflicting when two applicable, sufficiently identified items cannot both be
true for the same subject/fact/effective interval, or when sources disagree on identity-critical
dimensions. The system:

1. preserves every item and lineage;
2. creates an explicit conflict set with reason and scope;
3. marks the resolution/case dimension as conflicting;
4. prevents automatic identity confirmation, merge or consequential downstream action;
5. permits an authorized human to record a resolution decision that cites evidence;
6. never deletes the losing evidence.

Source priority may guide review but is not an automatic truth overwrite.

## 9. Artifact and privacy boundary

Raw provider payloads, documents, exact contact/title data and uploaded files are stored only
as private Artifacts when retention and license permit. Public/browser DTOs receive allowlisted
evidence summaries, never storage paths, credentials, SQL, stack traces, raw provider bodies
or permanent signed URLs. Exact address/coordinates remain private unless the explicit product
flow requires and authorizes them.

When raw retention is prohibited, store a source fingerprint, retrieval evidence and bounded
metadata sufficient for audit without retaining the payload.

## 10. Deterministic facts and AI boundary

```text
Provider/User/Document facts
          -> Evidence
          -> versioned deterministic calculations
          -> calculation Evidence
          -> AI Synthesis (read/reference only)
          -> draft Artifact
          -> human approval where consequential
```

AI may:

- summarize, compare and explain evidence;
- detect conflicts and missing evidence;
- draft a report;
- suggest the next investigation step.

AI may not:

- create/confirm canonical property identity or merge/split entities;
- rewrite authoritative evidence or provider lineage;
- replace valuation, TaxOracle, loan or holding-cost calculations;
- declare legal rights, clean title, no hazard or safety;
- contact owners, purchase title, publish or export without explicit authorized action.

AI output records model/provider/version, prompt-template version, cited evidence IDs, actor,
request ID and approval state. Unsupported statements are removed or marked unsupported; they
are never backfilled into evidence.

## 11. Evidence acceptance tests

- Every usable fact has source, retrieval time, coverage, status, quality and lineage.
- Missing/unknown/unavailable never becomes zero/safe/none.
- Stale status is deterministic and time-testable.
- Conflicts block identity confirmation and other declared operations.
- Mock/test evidence cannot cross the production boundary.
- Provider errors contain bounded codes and no raw response/secrets.
- Cross-workspace evidence/subject/artifact links fail at both service and database layers.
- AI cannot mutate evidence or authoritative tables and every synthesis cites evidence IDs.
