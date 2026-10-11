# Independent ML-0 review

One independent, read-only reviewer examined the implementation, contracts,
tests, official-source/request documents and local capture artifacts against
Part N of the supplied specification. The reviewer reported **0 Critical,
3 Important and 0 Minor** findings. All three Important findings were corrected
before the final commit; the author verified the fixes with regression tests.
The corrected patch was not independently re-reviewed. Final suite and rebuild
results are recorded in [validation](external-evidence-validation-v1.json).

| Finding | Correction | Regression evidence |
| --- | --- | --- |
| Matching reports could assert their own admission conditions without reading original inputs | Byte-only comparison always withholds approval. Positive verification requires freshly staged, rehashed sources and recomputed receipt/gate results, compared with the reports. CLI exposes `verify --revalidate`. | A forged all-true report cannot approve a cohort; report/source mismatch raises an error. |
| Ingestion discarded previously declared external dependencies | Preserve declarations and reject unreviewed staged dependencies as a whole; only reviewed receipt-backed availability enters the adapter. | A later availability dependency survives ingestion and cannot enter an earlier PIT freeze. |
| Duplicate releases were treated as correction/self-supersession events | Require `duplicate_of_occurrence_id`, bind the original occurrence/version/parent/status/time and reuse its semantic lineage. Duplicate cancellations/replacements remain conservatively rejected. | An explicit repeated original version collapses to one synthetic PIT observation; an unbound reference fails closed. |

Regression failures were observed before the corrections, followed by **50
focused tests passing**. A subsequent real CLI integration check found that the
fresh gate comparison omitted the recovery-manifest hash carried by CLI reports.
The adapter now supplies the freshly verified manifest digest to the comparison;
a matching digest passes and a different digest fails. The additional regression
was observed failing before its fix, followed by **51 focused tests passing**.
This additional fix was author-verified and is not described as independently
reviewed. All positive authority scenarios use fictional material
inside temporary test directories. They do not add real receipts, historical
proofs or approved observations.

The reviewer independently rehashed all five retained metadata responses against
the public capture manifest and confirmed the real receipt bundle is empty.
The review covered current-only files, filenames/mtime as time authority, derived
IDs, correction/cancellation/replacement leakage, late rights supplements,
licensing, personal-data exposure, thresholds and synthetic evidence promotion.

The reviewer distinguished these upstream responsibilities from code correctness:

- Hashes and review flags do not authenticate an institution. A responsible data
  steward must examine original official material, scope and lawful reuse.
- The inherited privacy check detects prohibited row fields and machine paths;
  it is not a universal personal-information detector. Captured raw metadata
  remains private because public pages can contain incidental contact details.
- Admission minima are feasibility safeguards; neither sample power nor model
  accuracy is claimed. The frozen criteria cannot be relaxed to force PASS.
- The <=17-release staging boundary and known schema support remain explicit;
  larger scope/new schemas require separate reviewed onboarding.
- Metadata elapsed bounds are checked between transport operations; a blocking
  operation can add the configured five-second timeout.
- External-source currency was not independently repeated by the reviewer;
  the research record separates official page observations, indexed leads and
  retained bytes, without calling any of them historical proof.

No agency was contacted and no personal record was acquired for this review.
The remaining E1–E5 blockers require external authoritative evidence.
