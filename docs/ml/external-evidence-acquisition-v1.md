# ML-0 external authoritative evidence acquisition

**Target A BLOCKED; Target B BLOCKED; ML-B MAY NOT BEGIN.**

Baseline `c9ab5f61a45f7f704326af66cb0bea02740b9927`, branch
`research/ml-external-evidence-acquisition-v1`, research date 2026-10-11,
Asia/Taipei. This lane researches/acquires external authority and prepares
ingestion. It does not train, estimate intervals, alter production valuation,
introduce UI or replace the existing Data Gate.

## Acquisition findings and routes

The [complete machine-readable E1–E5 map](external-acquisition-map-v1.json)
records every requested acquisition dimension: authority/unit, product, exact
evidence, public URL, history mechanism, request/API/download/form route,
login/application, reuse, expected formats/fields/times and personal-data scope.
The [19-source registry](external-official-sources-v1.json) and
[capture manifest](external-metadata-capture-manifest-v1.json) distinguish retained
bytes, failed transports and browser/index observations.

| Blocker | Responsible authority and product | Established observation | Evidence still required |
| --- | --- | --- | --- |
| E1 publication/bytes | MOI 地政司, PLVR public sale batches | Static publication differs from dynamic queries; current metadata is available | Original release/hash/time/immutable version binding for 112S3, 115S2 and every required historical release |
| E2 official identity | MOI 地政司; local land authorities | Main/detail join keys exist; field presence does not define cross-release identity | Official 編號/移轉編號 uniqueness/reuse/stability and changed-key semantics |
| E3 lineage | MOI and transaction's jurisdictional land office | Official correction procedure exists | Complete original/revision/cancellation/replacement/duplicate events, explicit edges/tombstones and cutoff coverage |
| E4 continuity | MOI provider; data.gov.tw for discovery/routing | Public catalog/history landing inspected | Complete original/revised/withdrawn releases, historical bytes and gap/retention declarations |
| E5 rights/unit | Taipei/New Taipei land offices; building authorities for supplements; NLSC for spatial context/referral | Registration/permit/map application routes identified | Non-personal registered-unit/object-role/required-interest/actual-transfer mapping tied to exact PLVR records and historical versions |

The [PLVR Open Data page](https://plvr.land.moi.gov.tw/DownloadOpenData)
describes static 1/11/21 releases and distinguishes the dynamic service.
The [sale catalog](https://data.gov.tw/dataset/25119) and
[combined catalog](https://data.gov.tw/dataset/77051) identify the publisher,
schema/manifest products and Government Open Data License v1. Their listing or
metadata-modification dates do not establish the historical bytes of a ZIP.
These observations supply acquisition context only.

The [NLSC viewer description](https://www.nlsc.gov.tw/cp.aspx?n=16732) describes
public geographic viewing; [map-store documentation](https://www.nlsc.gov.tw/cp.aspx?n=16739)
describes certificate/application and purchase routes. The
[service application page](https://maps.nlsc.gov.tw/S09SOA/homePage.action?Language=ZH)
distinguishes service applications/subscriptions. No inspected map product
establishes PLVR-to-registered-unit or transferred-right identity. NLSC is not
assumed to be the custodian of registration ownership/transfer evidence.

The [Taipei transcript directory](https://land.gov.taipei/Content_List.aspx?n=D37BA350BBD48584)
and [address suppression page](https://land.gov.taipei/cp.aspx?n=D590300A57853E80)
show why a transcript class must not be called non-personal merely because it
partly suppresses personal fields. The request asks for authority-redacted
property/object extracts, with entitlement and reuse clarified first.

The [New Taipei correction description](https://www.tamsui.land.ntpc.gov.tw/cp.aspx?n=14312)
routes corrections through the relevant land office and specifies party/agent
requirements. It does not expose a complete public version feed. The
[exclusive/common drawings notice](https://www.land.ntpc.gov.tw/News_Content.aspx?n=2&s=40576)
is an indexed official lead concerning separately numbered common portions;
its direct browser open failed. No mapping was acquired from it. The
[local catalog](https://data.ntpc.gov.tw/datasets/ACCE802D-58CC-4DFF-9E7A-9ECC517F78BE)
is a field-discovery lead, with no recovered identity stability specification.

[Taipei building FAQs](https://cmo.gov.taipei/News_toggle.aspx?PageSize=20&n=961284F845E9477B&page=5&sms=87415A8B9CE81B16)
describe permit-copy/query context. [New Taipei's permit issuance page](https://service.ntpc.gov.tw/eservice/CaseData.action?itemId=106036)
identifies 工務局施工科使照股 for issuance. Issuance is not a historical-copy
request endpoint; R7 asks that unit to route the request. A permit does not prove
registered dwelling count or transaction-specific transferred rights.

## Bounded acquisition and missing evidence

Nineteen explicitly selected public metadata URLs were attempted, once each,
with HTTPS/official-host redirect checks, <=3 redirects, <=1 MiB per response,
15-second elapsed checks and three workers. Five responses were retained;
fourteen raised TLS errors in the coding environment. TLS verification was
not bypassed. The nominal elapsed bound is checked between transport reads;
a blocked connect/read can add up to the configured five-second timeout.
Browser/index observations are separate, and no response hash is fabricated
for unavailable bytes. This is bounded research, not a universal assertion that
government historical evidence does not exist.

Every retained object has official URL, actual UTC retrieval time, byte size,
SHA-256, local relative retention path, purpose and license note in the capture
manifest. Raw pages/PDFs remain ignored and private; public catalogs can include
incidental staff contact data, so no raw page body is committed. The SHA binds
the captured current response, not an earlier version of the described dataset.
No transaction dataset, paid portal, personal transcript or map bulk product was
downloaded. No login, form submission, email or agency contact was performed.

The two inherited ZIPs were copied read-only from the prior ML-A3 worktree into
this worktree's ignored recovery directory. Rebuilding uses the original
preflight/download metadata and rehashes the actual bytes:

| ZIP | Bytes | SHA-256 | Evidence class |
| --- | ---: | --- | --- |
| 112S3 | 14,876,099 | `4d9fa7be16bc9aba99e79c0f86ca27b32f46755de04e98e1dd2c8d8297b466c1` | CURRENT_ONLY without a qualified historical receipt |
| 115S2 | 14,705,972 | `6b4c148bad106a235dddf214001d605ff9ffa45ac50561f7125c6d7fa795d4da` | CURRENT_ONLY without a qualified historical receipt |

The original 2026-10-08 capture bounds remain late availability bounds; the copy
does not create a new historical date. Original archive hashes and terms are
also included in refresh output. Other inherited ledger entries are not called
recovered bytes. No original publication manifest, authenticated prior hash,
normative stable identity guarantee, complete cancellation stream, replacement
map or registered-rights linkage was recovered. Authenticated historical proofs:
**0**. Revision/cancellation/replacement authority and rights mappings: **0**.

Observed main keys remain 37,669 unique derived research families; prior alternate
移轉編號 analysis has 4,356 ambiguous groups, including 19 candidate groups. These
counts cannot certify stability. IDs remain **DERIVED_RESEARCH_TRANSACTION_ID**.
Missing later rows are not cancellations; value similarity is not lineage. All
1,440 multi-building-portion candidates still lack authoritative unit/rights
mapping; the 827 single-portion candidates are not automatically single dwellings.

## Requests prepared for the owner

[Seven Chinese formal drafts](external-official-request-packages-v1.md) provide
subjects, complete request bodies, exact fields, periods, rationale, non-personal
scope, machine-readable preferences, checksums/versions, reuse questions and
fallback attestations. R1 covers E1/E4; R2 E2/E3; R3/R4 local land linkage;
R5 NLSC history/referral; R6/R7 local permit supplements. No invented department
contact is used. An official FAQ index identifies 地政資訊作業科, but the inspected
live FAQ did not locate that exact entry; it remains a routing lead, not a verified
current office assignment. R1/R2 address 地政司 through formal intake.

The [MOI application template](https://ws.moi.gov.tw/Download.ashx?n=55Sz6KuL6KGoLnBkZg%3D%3D&u=LzAwMS9VcGxvYWQvT2xkRmlsZS9zaXRlX25vZGVfZmlsZS81OTEyL%2BeUs%2Biri%2BihqC5wZGY%3D)
is an indexed official fallback; its indexed terms restrict purpose and
third-party/commercial reuse. Current acceptance and applicable authorization
must be confirmed by the agency. Requested products are not automatically
covered by the public-batch [Open Data license](https://data.gov.tw/licenses).
No commercial reuse rights are claimed for any requested proof or registration
extract. Applicant personal details belong only in the owner's external official
application, never in evidence fixtures or this repository.

Chronology request scope: transactions 2022-07 through 2026-06; original release
history from first publication through an explicitly attested 2026-10-11 cutoff.
Request every quarter 111S3–115S2 plus overlapping original 1/11/21 releases,
full refreshes, corrections, withdrawals and replacements. Extra dates may be
needed to mature later labels; they must be declared prospectively. A quarter
label does not define the included transaction or publication interval.

## Receipt boundary and dry-run

[The machine-readable schema](contracts/external-evidence-v1.schema.json) defines
`HistoricalPublicationReceipt`, `TransactionNamespaceAuthority`,
`TransactionLineageReceipt`, and `RightsUnitMappingReceipt`. All require source
authority/official route, retained proof path/hash/size, retrieval/publication/
effective time, dataset/county/release scope, version, limitations, reuse,
non-personal status and recorded authority review. Shapes have closed field
sets and bounded arrays. Validation uses the research-only `jsonschema`
dependency in requirements-dev.txt; production dependencies are unchanged.

The validator rehashes retained proof bytes and rejects escaped/absolute paths,
wrong authority/host pairs, missing times, unknown license, ambiguous identity,
incomplete lineage, unbound event versions, orphan event locators and conflicting
receipts. Neither a 64-character hash nor REVIEWED_AUTHORITY authenticates a
government claim. The owner/data steward must inspect original official proof,
the institution, the event/object/byte binding and lawful reuse, then explicitly
record the reviewer role and basis. A signed/current attestation must clearly
bind historical facts; its date does not backdate source bytes.

Exact-time or conservative-upper-bound publication proofs are supported. For
date-only provider proof, the reviewer must encode a conservative **next Taipei
midnight** upper bound and preserve the original date/precision in retained
material; inventing an exact midnight publication time is prohibited. Original
filenames and immutable version IDs are required but never supply time authority.

Ingestion clears staged authority claims and computes native rights uncertainty
before applying receipts. Full source history is preserved before semantic
filtering. All visible occurrences need explicit cancellation-state and namespace
evidence. A history receipt binds the **enriched visible research ledger SHA**
at the exact cutoff; this is a reviewer-audited correspondence to official
material, not a claim that agencies issue our derived identifiers or hashes.
Each chronological freeze needs its own complete-history receipt. Raw rows and
official tokens stay private. A rights receipt binds archive/member/physical row,
schema and exact main/build/land payloads; existing role/fraction checks still
decide Target A. Late rights supplements are availability dependencies and cannot
leak backward. Accessory roles outside the existing proven role contract remain
blocked, requiring a separate authoritative contract revision, not a heuristic.
Existing external dependency declarations are preserved and cause a fail-closed
rejection until receipt-backed review supplies their availability; ingestion
cannot erase them to admit an earlier freeze. Duplicate releases must identify
the original occurrence and retain its version and actual predecessor. They
never create a self-supersession edge. Duplicate cancellations/replacements are
currently rejected conservatively rather than inferred from disappearance.

Synthetic proof material exists only inside temporary test fixtures. The real
CLI offers no synthetic override. Tests exercise valid receipts, missing time,
invalid/wrong hash, current-only files, unknown/ambiguous namespaces and lineage,
cancellation, changed-key replacement quarantine, rights ambiguity, unknown reuse,
malformed payloads, escaped paths and real-mode fixture rejection. The real receipt
bundle [contains no receipts](external-evidence-receipts-v1.json).

## Refresh and frozen ML-B admission

Run from the repository root, after installing research dependencies:

```powershell
python -m scripts.ml.refresh_external_evidence refresh --cutoff 2026-06-30T23:59:59+08:00 --observation-at 2026-10-11T00:00:00+08:00 --output artifacts/ml/external-evidence/build-a/refresh.json
python -m scripts.ml.refresh_external_evidence refresh --cutoff 2026-06-30T23:59:59+08:00 --observation-at 2026-10-11T00:00:00+08:00 --output artifacts/ml/external-evidence/build-b/refresh.json
python -m scripts.ml.refresh_external_evidence verify --first artifacts/ml/external-evidence/build-a/refresh.json --second artifacts/ml/external-evidence/build-b/refresh.json --revalidate
```

Equal-input refresh is idempotent; it accepts an existing byte-identical output,
and refuses to overwrite different bytes. Use a new output path when receipts
change. Put reviewed real receipts in a private JSON bundle via `--receipts` and
their retained material under `--evidence-root`; only publish sanitized summaries.
Broader future acquisition can use `--preflight`, `--downloads`, and explicit
`--releases` from the existing bounded <=17-release inventory. All requested
archives must be restored and hash/schema/detail verified before staging; a
missing release fails, without silently shrinking the requested inventory.
Default older audit behavior still requires exactly 112S3/115S2. New schema or
larger release scope requires a separate reviewed onboarding change. Receipt
ingestion is bounded to 100,000 full-ledger occurrences, 1,024 receipts and
2 MiB of retained material per receipt. An expanded period exceeding these
bounds fails; do not trim the full ledger to make it fit. Review the bounds and
resource budget in a separate onboarding change before ingesting that scope.

The refresh reruns historical publication, namespace, full lineage, PIT,
chronology and admission. Individual refresh output withholds approval while
independent byte equality is pending. Verification compares independently built
aggregate files, audits privacy and binds the contract/policy hashes. Positive
admission additionally requires `verify --revalidate`, which stages and rehashes
the sources, checks the recovery manifest and rebuilds receipt and gate results.
Byte comparison alone always withholds approval; matching reports cannot certify
their own conditions. This validates reproducibility and source correspondence;
institutional authentication still requires accountable review of original proof.

[ML-B policy v2](contracts/ml-b-admission-v2.json) is frozen before any real
receipt: >=840 PIT rows, >=21 usable and contiguous months, >=20 rows per city
per month (>=40 overall), both Taipei and New Taipei throughout, >=12 TRAIN
months and separate 3-month VALIDATION/CALIBRATION/TEST blocks, and the inherited
>=20 district/type rows per block. More training months are allowed; the final
nine months stay separate. Publication/dependencies and complete lineage must
cover 100% of admitted versions and each cutoff's visible history. Full-ledger
reselection, release-lag maturity, disjoint families, frozen Target A/B versions,
privacy and independent determinism remain mandatory.

These minima retain the existing 21-month four-block gate. Twelve train months
cover one annual cycle; three months per later block provide a quarterly span.
Twenty rows per city/month exposes sparse city cells and implies 840 rows across
21 months. It is a feasibility floor, not a precision, accuracy or power claim.
A later prospective power analysis may require more data; thresholds cannot be
relaxed to force PASS. Current candidate chronology has 24 sparse observed months,
longest continuous run nine months; **PIT usable months remain zero**.

## Delivery evidence

The [validation record](external-evidence-validation-v1.json) and
[final evidence report](external-evidence-final-report-v1.md) record real rebuilt
counts, deterministic hashes, focused/all-ML/full Python results, privacy,
independent review and repository hygiene. The independent review specifically
checks current-only/filename/mtime confusion, derived-key labeling, cancellation/
revision leakage, later supplements, license assumptions, privacy, numerical
thresholds and synthetic promotion. Synthetic pass counts never appear as
historical evidence or approved real observations.

Next owner action: send R1/R2, with the shared non-personal/time/hash annex,
through MOI 地政司's verified formal intake after filling applicant details outside
the repository; request a case number and written evidence/terms. In parallel,
submit R3/R4 for lawful agency-redacted linkage, with R5–R7 only for documented
referral/supplements. Preserve returned originals privately, record actual
receipt time and hash, review authority/scope/reuse, then refresh. Until those
external proofs pass all gates, **ML-B MAY NOT BEGIN**.
