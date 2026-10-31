# Stage 3 bounded evidence and claim closure

The user-defined v1 completion criteria allow a rigorously restricted capability
instead of requiring every future property/PIT feature. This closure retains the
existing fitted gross-transfer model and its original target. It does not turn
unknown evidence into positive eligibility for a whole dwelling or a historical
public-information backtest.

## Publication, revision and cancellation: BOUNDED

The audit rehashed every retained artifact, including the 7.3 GiB SQLite ledger,
and bound those bytes to the previous complete independent row/lineage verifier.
It streamed all 1,321,059 canonical rows and replayed existing cohort/split rules.
Every admitted identity hash, split count and exclusion count matched the original
716,413-row admission. The ledger was opened `mode=ro&immutable=1`, with
`query_only=ON` and a 16 MiB cache. No source mount, network download, serving DB,
training or historical build was used.

The manifest inventories 40 consecutive releases 105S4–115S3, 880 sale-main files
and 8,660 total members. Sale-main headers have two distinct recorded hashes: 110
files through 106S4 and 770 from 107S1 onward. These are schema-byte observations,
not evidence of stable ownership/parking semantics. Release labels, `build_time.xml`
inventory, archive build times, transaction dates and file mtimes are not
authenticated public-availability times. All rows explicitly retain publication
proof false and null release-availability timestamps. There is no retained
cancellation event table or cancellation-named inventory member. Filename absence
alone does not prove an event ledger could never exist elsewhere.

The existing canonical selector uses official serial identity, full raw-semantic
version hashes and independent strong-fact families. It quarantines all 31
observed conflicting identity groups; zero enter clean data. It propagates any
nonblank note across the identity and matching fact family, including a later note
on an older apparently ordinary observation. Ambiguous multi-ID fact groups are
also excluded. No later release wins automatically, and no older eligible version
is resurrected after a disqualifying observation. The known related-party serial
for legacy 38652 remains one raw occurrence and zero clean/admitted occurrences.

This reconstructs **observed conflicts and note-taint**, not a complete legal
cancellation/supersession history. A cancellation never reported in the retained
archives, or a replacement under a different serial and changed strong facts, may
remain undetected. Its prevalence cannot be quantified from this artifact. A row
missing from a subsequent quarterly delivery is not interpreted as canceled;
quarterly archive absence is not an authoritative tombstone. A date-only subset
cannot manufacture the missing completeness proof.

Therefore v1 estimates the statistical relation among **frozen reported gross
transfer observations**, without asserting any retained transaction is currently
legally active. Evaluation is retrospective archive-snapshot generalization with
the existing source-quarter membership restrictions, not a historical PIT
backtest. Unknown cancellation risk remains explicitly disclosed in API scope.
This bounded estimand needs neither a fabricated publication time nor a claim that
the archive is a cancellation-complete current register. Stronger PIT contracts
remain unchanged and unauthorized.

## Parking: EXCLUDED FROM V1

Staging retains `parking_count_reported` and `parking_basis`. Canonical counts are
713,618 reported zero and 607,441 reported positive; none are null. Every retained
parking basis is `UNVERIFIED`. The audit records these distributions separately
for every release and the admitted cohort. Those observations show presence and
count missingness only: they do not establish how source parking consideration or
area reconciles with gross building consideration/registered area.

Raw PLVR parser contracts recognize `交易筆棟數`, parking type, parking price,
parking area and parking detail rows. The canonical artifact does not preserve
parking price/area or joined detail semantics, so their consistency across all 40
releases is not established here. Earlier two-release detail audits are evidence
for those two releases only. They are not generalized to the full archive.

The model consumes no parking feature or adjustment. The target remains gross
consideration divided by reported registered transferred area; no parking-exclusive
price, no-parking cohort or zero-count absence proof is claimed. The API rejects
parking fields and parking-exclusive requests. Parking effects remain unseparated
noise/mix in the gross target. No unsupported imputation occurs.

## Whole-dwelling rights: RESTRICTED

All 1,321,059 canonical rows have `rights_status=UNVERIFIED`. Main transaction
sign/count, residential use, building type, address and floor do not prove a
complete dwelling. Blank notes and one reported building cannot supply that proof.
The canonical artifact omits the joined object-level rights evidence needed to
establish a dwelling's complete required private/common/land interests.

Existing reviewed raw-parser evidence for 112S3/115S2 distinguishes build-detail
`移轉情形` and land-detail `權利人持分分子/分母`. Land fractions describe parcel
ownership interests, not a numeric transferred fraction of a dwelling. A partial
land share can be the complete required condominium land interest. Neither a
fraction nor `全筆移轉` alone proves partial or complete whole-dwelling rights;
private/common object roles and required-interest mappings are missing. No
whole-dwelling eligibility is inferred for the 40-release cohort from that limited
two-release evidence.

Known partial-right/nonstandard transactions disclosed by notes are excluded by
the existing any-note rule. Synthetic regressions prove partial/cancellation/
supersession notes invalidate the entire identity, including an earlier blank-note
version. Undisclosed partial interests may still occur among unknown-rights rows;
zero known partial-status rows does not mean zero latent partial transactions.

V1 therefore supports only the **reported registered transfer basis**, not a
whole-dwelling or share-specific valuation. It never divides by a share or scales
a reported partial transfer to a hypothetical full property. Explicit partial-right
or whole-property requests reject before model loading; unknown rights are not
relabeled complete. These restrictions make the original observed-transfer target
defensible without an invented ownership certificate.

## Enforced API and model impact

The API-only `requested_value_basis` accepts exactly `reported_transfer`, defaulted
for existing callers. `whole_dwelling`, `whole_property`, `partial_rights` and
`parking_exclusive` reject with 422. Unsupported share/parking fields also reject.
The response includes `scope` from `plvr-bounded-transfer-evidence-v1`, identifying
snapshot-only publication evidence, residual cancellation risk, no parking feature,
unverified transfer rights, and no whole-property scaling.

This envelope restriction is independent of the immutable fitting contract
`plvr-gross-transfer-features-v1`. `Subject`, all nine features, preprocessing,
fitting source files, cohort, splits, weights and existing artifact bytes remain
unchanged. Feature-parity regressions compare the restricted API DTO directly with
the original model `Subject`. Native inference and provenance tests retain the
same model version and hashes. The existing holdout metrics are retained; no new
holdout experiment or performance claim is created.

Audit result: **no dataset, feature or model artifact change; no retraining or
re-evaluation of model performance required**. Focused tests and a real-artifact
API acceptance probe validate only the new boundary. The prior model version,
manifest pin and reproducibility/resume evidence remain authoritative.

Focused validation (255 tests), real-artifact live acceptance and independent
review passed; the bounded current-profile v1 is COMPLETE under the revised
acceptance criteria. Future full-property/PIT,
parking or share-valuation products require new evidence and contracts; they are
excluded future scope rather than unfinished v1 features.

The audit verifier explicitly binds the current summary digest and all five file
hashes to the previously committed admission evidence before reading rows. A
regression proves changing bytes and rewriting summary/COMPLETE declarations
cannot impersonate the prior full verification. API scope states that a separate
cancellation-event ledger is unavailable; it promises only observed conflict and
note-taint exclusion. All completed evidence remains tied to the unchanged model.
