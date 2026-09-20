# Taipei Planning Read V1 Source Audit

**Audit date:** 2026-09-20
**Gate:** Gate 0 source suitability
**Decision:** approved for a manual-reference normalization seam only

## Authority and accepted geography

The competent local planning publisher is the Taipei City Department of Urban Development.
V1 accepts only the exact jurisdiction `Taipei City` and the exact
scope `urban_plan_non_national_park`. The Taipei zoning lookup instructions
state that Yangmingshan National Park is outside this lookup's coverage; V1
therefore rejects national-park scope and does not infer another authority.

Official human-facing sources inspected for this gate were:

- zoning-certificate portal:
  <https://zone.udd.gov.taipei/new_index1.aspx>
- urban-plan announcement index:
  <https://udd.gov.taipei/announcement/biwfsm8>
- zoning lookup instructions:
  <https://zone.udd.gov.taipei/new_nav6_04.aspx>
- zoning lookup FAQ and Yangmingshan National Park boundary statement:
  <https://zone.udd.gov.taipei/new_nav6_05.aspx>
- Taipei open-data land-use survey dataset:
  <https://data.taipei/dataset/detail?id=a132a433-db7c-4387-8085-83e6a093b17f>

## Source characteristics

| Source | Access/format | Manual lookup keys | V1 legal meaning |
| --- | --- | --- | --- |
| Issued zoning certificate | Human-facing HTML portal and issued document | Reported certificate reference and optional reported zoning metadata | `USER_PROVIDED`, limited, and unverified; no authenticity, currency, validity-period, property applicability, or entire-case coverage claim |
| Official urban-plan announcement | Human-facing HTML announcement index and linked documents | Reported announcement reference, optional plan identifier, and optional reported effective date | `USER_PROVIDED`, limited, and unverified; current legal effect still requires later-amendment, supersession, revocation, and competent-authority confirmation |
| `LUI_002` land-use survey | Taipei open-data distribution; specified-year/reference dataset | Dataset-defined survey fields | Separate `REFERENCE_ONLY` survey evidence, not statutory zoning and not emitted by this seam |

The portal mapping and issuing-authority label are server-owned constants. No
caller can provide a URL, host, filesystem path, authority, provider, or
credential. Reported identifiers are treated as bounded data only.

## Update, availability, and verification semantics

Announcement publication is not proof that a referenced document remains the
current legal position: the official index includes later amendments and
revocation-related records. A caller-supplied effective date is preserved only
as reported metadata and never upgrades authority or verification.

The human-facing portals offer no runtime availability guarantee for this
application. V1 intentionally has no runtime transport, no scraping, and no
provider fallback. `TAIPEI_PLANNING_SOURCE_MODE=manual_evidence` records that
decision. Missing or unsupported source-mode configuration fails closed with a
bounded 503; the default-off rollout flag fails closed with 404.

Every successful normalization is fixed to:

- `status=LIMITED`
- `authority_class=USER_PROVIDED`
- `coverage_status=LIMITED`
- `verification_required=true`
- `verification_status=unverified`

The seam produces no FAR, BCR, buildability, permitted-use, ownership,
entitlement, development-approval, property/parcel binding, or case-level
conclusion. `normalized_at` records server normalization time only.

## Licensing and attribution

The Taipei open-data material is published under the Open Government Data License, version 1.0:
<https://data.taipei/rule>. Any future use or redistribution
of the open dataset must retain the required source attribution and comply with
that license. This V1 endpoint neither downloads nor redistributes that dataset;
it only documents the boundary so `LUI_002` cannot be promoted from
`REFERENCE_ONLY` to statutory or authoritative evidence.

## Gate 0 conclusion

The reviewed sources support human verification of official Taipei planning
documents, but they do not establish a stable, exact, machine-readable contract
that satisfies V1's jurisdiction, legal-effect, and evidence-authority rules.
Gate 0 therefore authorizes bounded `manual_evidence` normalization and no
runtime transport. A future retrieval architecture requires a new source audit,
contract tests, and an explicit architecture review.
