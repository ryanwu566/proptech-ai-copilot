# ML semantic and temporal evidence closure v1

Final gate: **BLOCKED**. Approved candidate count: **0**. Approved scope: **none**.
ML-B may not begin. No approved dataset or ML-B handoff is issued.

The implementation closes executable validation gaps, including historical
membership selection, but the recovered official bytes do not prove complete
dwelling rights, one registered dwelling, historical availability or complete
revision history. Matching empty target/features/split files cannot satisfy the
user's nonempty cohort standard.

Machine evidence: [valuation-semantic-temporal-closure-evidence-v1.json](valuation-semantic-temporal-closure-evidence-v1.json).
New gate: [readiness follow-up](valuation-dataset-readiness-semantic-temporal-closure-followup-v1.md).
Existing foundation/recovery contracts and prior audit history remain intact.

## Source and semantic evidence

The starting branch was `research/ml-valuation-semantic-temporal-closure-v1`,
HEAD and origin/main both `d06ed4f062a212fed4ce0adf092c2fdc515a3f62`, with a
clean worktree. Only this isolated worktree was used for task files.

Prior gate: BLOCKED, zero approved rows. Its unresolved requirements were whole
rights, a single dwelling, compatible area/target, publication and revision
evidence, nonempty deterministic reconstruction and proper chronological folds.

Only 112S3 and 115S2 were restored once each from the existing release ledger:

| Release | ZIP bytes | Archive SHA-256 | Verified current upper bound (UTC) |
|---|---:|---|---|
| 112S3 | 14,876,099 | `4d9fa7be16bc9aba99e79c0f86ca27b32f46755de04e98e1dd2c8d8297b466c1` | 2026-10-08T06:23:17.233018+00:00 |
| 115S2 | 14,705,972 | `6b4c148bad106a235dddf214001d605ff9ffa45ac50561f7125c6d7fa795d4da` | 2026-10-08T06:23:31.096999+00:00 |

Both HTTP downloads returned 200 and matched the previous exact hashes; package
CRC and embedded schema checks passed. All physical Taipei/New Taipei sale main,
build, land and park records were parsed: 37,669 main and 197,664 total records,
including 83,942 build, 55,387 land and 20,666 park details. Main members are
`a_lvr_land_a.csv` and `f_lvr_land_a.csv`; other counties, rent and presales are
outside the cohort attempt. The ZIPs contain additional national members but
these were not admitted to this attempt. Complete detail member joins had no
orphan keys or ambiguous main keys. Repeated details remain physical records and
do not become distinct units by deduplication.

The prior 17-release preflight observations were reused faithfully, rather than
claimed as new probes. Two existing archives were restored; there were no new
seasonal archives, retries, recursive crawl, commercial sources or moving latest
downloads. Official catalog and explanatory material were consulted through
bounded read-only browsing.

Building detail fields are 編號, 屋齡, 建物移轉面積平方公尺, 主要用途,
主要建材, 建築完成日期, 總層數, 建物分層 and 移轉情形. They omit a
registered building identifier, numeric transferred building rights fraction,
private/common object role and registered dwelling-unit count. The detail 編號
joins a transaction; it is not an independently proved building identifier.
Land detail supplies 權利人持分分子/分母 and 移轉情形. Those are parcel
ownership interests: a fractional parcel interest can be the complete land
interest associated with a condominium. It cannot automatically imply either a
partial dwelling or complete rights. Neither 全筆移轉 alone, blank notes,
declared one building, one main row nor an address proves all required interests.

`rights_dwelling.classify` uses strict complete/unique joins, cardinality, area,
status/fraction agreement and object mappings. FULL_RIGHTS_CONFIRMED requires
every private dwelling's 1/1 transfer plus the complete required linked common
and land interests; a proven shortfall is PARTIAL_RIGHTS. Missing numeric/object
basis stays unknown or ambiguous. SINGLE_DWELLING_CONFIRMED requires one mapped
private residential registered unit, one compatible declared building, an
agreeing single transferred floor and exact main/detail area sum. Common
objects must link to that unit and agree with native common-use semantics.
Unresolved multiplicity stays ambiguous; an explicit multiple count is excluded.

Reviewed supplemental evidence must bind exact archive, member, physical main
record, schema and main/build/land payloads. Input consistency checks do not
authenticate the legal authority of a supplied supplement. No authoritative
supplement was recovered or used by the real builder; synthetic positive tests
are implementation tests only.

| Classification | Real main occurrences |
|---|---:|
| FULL_RIGHTS_CONFIRMED | 0 |
| PARTIAL_RIGHTS (proven against the complete dwelling basis) | 0 |
| RIGHTS_AMBIGUOUS | 32,602 |
| RIGHTS_UNKNOWN | 5,067 |
| SINGLE_DWELLING_CONFIRMED | 0 |
| MULTI_DWELLING | 245 |
| DWELLING_AMBIGUOUS | 26,330 |
| DWELLING_UNKNOWN | 11,094 |

The existing complete park-detail/main-fields/use/notes contract yields 13,433
NO_PARKING_CONFIRMED, 16,662 PARKING_PRESENT, 7,311 PARKING_SEMANTICS_AMBIGUOUS
and 263 UNKNOWN. Only confirmed absence can qualify. No price or area parking
subtraction is introduced to manufacture eligibility.

Area remains `registered-transferred-building-including-aux-common-no-parking-v1`:
建物移轉總面積平方公尺 is m², and ping = m² × 0.3025. It is registered
transferred area, which can include common and ancillary portions; no claim of
interior, usable or net area is made. Official guidance supports that distinction.
[MOI PLVR FAQ](https://lvr.land.moi.gov.tw/R11/jsp/qa.jsp).
Declared counts cannot establish a registered single unit.
[Official PLVR explanation](https://lvr.land.moi.gov.tw/jsp/index.jsp).

The target stays `residential-unit-ntd-ping-log-v1`: total NTD / registered ping,
then natural log. Decimal positivity/scope/reconciliation checks follow the
merged foundation. Target construction runs only after full rights, one dwelling,
no parking, compatible area, source, revision and availability are proved; all
other occurrences have no training target. The official NTD/m² field is a
diagnostic, never a replacement target. Tolerance is
max(1 NTD/m², 0.001 × total NTD / registered m²).

Raw reconciliation gives 21,244 within tolerance, 10,411 mismatches, 4,242 not
computable, 664 outside v1 scope and 1,108 absent official prices. These counts
include land-only, parking, mixed rights and multi-object transactions and do
not validate a dwelling target. The supported residential target/use/type plus
confirmed-no-parking diagnostic intersection has 10,842 rows: 10,758 within
tolerance, 84 outside scope and zero mismatches. None is a qualified target.

## Temporal, revision and cohort behavior

The official [dataset catalog](https://data.gov.tw/dataset/25119) and
[seasonal download page](https://plvr.land.moi.gov.tw/DownloadOpenData) identify
the data/schema families and release channel. Scheduled refreshes, seasonal
names, transaction dates, `build_time.xml` registration/contract windows and
current HTTP metadata do not authenticate publication of these exact bytes at
past cutoffs. No usable historical publication record was recovered.

Recovered release classes: EXACT_PUBLICATION_TIME 0, DATE_ONLY_PUBLICATION 0,
CONSERVATIVE_UPPER_BOUND 2, SYSTEM_FIRST_SEEN 0, UNKNOWN 0. All 37,669 occurrences
inherit their current conservative bound; authenticated historical releases and
occurrences are both 0. The other 15 releases in the prior ledger have no usable
recovered byte-bound availability evidence. They supply no cohort occurrences.

Exact evidence must bind release and archive/version bytes. Date-only evidence
becomes eligible at the following midnight in Asia/Taipei, never a guessed
intraday instant. A current verified HTTPS retrieval permits eligibility only
from its actual observed upper bound, never retroactively. SYSTEM_FIRST_SEEN
alone and unknown availability exclude under public-information framing.
The fixed logical snapshot/cutoff is 2026-10-08T06:30:00+00:00 (14:30 Taipei),
after both retrieval bounds. Actual row ingestion/transformation clocks remain
null; the logical clock is explicitly separate and cannot assert replay history.

Identity preserves transaction family, raw/cancel-state content version and
archive/member/physical occurrence independently. All 37,669 provisional families
remain REVISION_UNVERIFIED: stable cross-release ID namespace and complete
correction/cancellation semantics are unproved. Attested republications,
corrections, supersessions, cancellations, collision links and confirmed distinct
transactions are each 0; predecessor edges 0. Absent observed repeats do not
prove absence of revisions. Changed IDs are never linked by guessing.

The full non-destructive ledger is selected as of each cutoff before semantic
admission. A later correction cannot replace an earlier version before it was
available; a later cancellation cannot remove it before that cancellation bound.
Ambiguous lineage or conflicting immutable/semantic/detail evidence quarantines
the family; no latest-state dedupe or silent row dropping is used. Every physical
occurrence has a stable first exclusion and all applicable exclusion reasons.

All 37,669 main geographies agree with county/member and current registry.
Raw scope is Taipei 11,998 rows across 12 districts, New Taipei 25,671 across
29 districts. No district-only county repair, historical name guessing or
national scope claim is made.

| Stage | Input | Retained | First excluded | Reason |
|---|---:|---:|---:|---|
| schema | 37,669 | 37,668 | 1 | INVALID_DATE: 1 |
| source_identity | 37,668 | 37,668 | 0 | None |
| geography | 37,668 | 37,668 | 0 | None |
| transaction_target | 37,668 | 16,689 | 20,979 | UNSUPPORTED_TARGET: 20,979 |
| residential_use | 16,689 | 13,573 | 3,116 | NON_RESIDENTIAL_USE: 3,116 |
| building_type | 13,573 | 13,028 | 545 | UNSUPPORTED_BUILDING_TYPE: 545 |
| rights | 13,028 | 0 | 13,028 | RIGHTS_AMBIGUOUS: 13,007; RIGHTS_UNKNOWN: 21 |
| dwelling | 0 | 0 | 0 | None |
| parking | 0 | 0 | 0 | None |
| price_area | 0 | 0 | 0 | None |
| physical | 0 | 0 | 0 | None |
| revision | 0 | 0 | 0 | None |
| availability | 0 | 0 | 0 | None |

The source-identity stage validates physical/schema identity, not the separately
unproven cross-release namespace. Downstream zero-input stages do not prove their
contracts passed. Conservation is 37,669 raw = 37,669 excluded + 0 admitted,
with unique physical ledger entries and no duplicate admitted family.

Raw building types: 18,649 住宅大樓, 7,122 公寓, 5,465 華廈 and 6,433
unsupported. Raw dates run sparsely from 2013-06 to 2026-06, concentrated around
the two release windows; 37,668 are valid day precision and one invalid. The
full aggregate raw district/month/type/release counts are in machine evidence.
They are not mature continuous population coverage. Approved county, district,
building type, release and month coverage are all empty; every approved monthly
count is zero. No approved temporal range or four split periods exists.

Split proposals require at least 21 contiguous mature months: at least 12 train,
then 3 validation, 3 calibration and 3 test; at least 20 rows per month and 20
county/district/type rows per block, explicit complete coverage, day precision,
unique families and version/occurrence provenance. These are declared research
minimums, not sufficient statistical representativeness or empirically estimated
lag. Labels must be available strictly before the next block freeze, with test
labels observed by a separate cutoff after the full last test month. No arbitrary
universal lag or random fallback is invented.

The entire supplied ledger is also selected independently at each block freeze;
versions and full historical membership must match the proposal. A correction or
cancellation learned later cannot silently rewrite training membership: a
global-cutoff proposal that differs returns HISTORICAL_MEMBERSHIP_DIFFERS and no
assignments. Assignment provenance binds ledger digest and selection cutoff.
Coverage remains unproved and cohort empty here, so split viability is false.
Calibration is excluded from fitting/model selection.

Baseline 0 global median, Baseline 1 district/type median and Baseline 2 historical
comparables are all unready. `baseline_history` validates their future input
population by full-ledger as-of selection at min(prediction time, fit cutoff),
strictly earlier transaction day, subject-family exclusion and mandatory frozen
fit-family membership. Unknown evidence abstains. No estimator or model is fit.
Model A columns remain county_district, building_type, area_ping, floor,
prediction_year and prediction_month. Age is optional and excluded from Model A;
road text, address/ID, price-derived inputs and any unreviewed extras are excluded.

## Reproducibility, privacy and validation

Two create-only independent process builds used the same exact bytes and logical
configuration, with hash seeds 11/29 and TZ UTC/Asia/Taipei. Delivery A/B have
identical bytes for all 13 files; all 10 bound JSONL hashes and current code,
closure/source contracts, registry and dataset/source manifest bindings verify.
The build manifest is a diagnostic manifest with readiness_approval false;
it is not an approved training dataset. Earlier intermediate artifacts remain
ignored and are not the delivered code-bound pair.

| Delivery file | Bytes | Matching actual-file SHA-256 |
|---|---:|---|
| cohort-membership.jsonl | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| dataset-manifest.json | 5,275 | `8b261a456f56677b765f384d6b0f1cbb9b6d11c1a00d665d07fe57a7affc8b3a` |
| evidence.json | 19,357 | `c083a411eaf53f190abc006aefae36a04f6fb3f2f72f6289799c3e6f1e8e3e01` |
| exclusions.jsonl | 30,091,522 | `87d50bbaa6bd2522e4425076c9794749d1ed0ba76fe174f54958d64199de3481` |
| features.jsonl | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| occurrences.jsonl | 147,320,386 | `a1baaffb596d546505d3562fdea5d7d01ddf44a88bcb30526b645caf47eb9b2a` |
| revision-edges.jsonl | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| revision-lineage.jsonl | 28,515,433 | `d2a905ec0f790761fd109888c5245c7af37510285546f0cd6d82c1aebbf1dade` |
| semantic-classifications.jsonl | 34,302,812 | `1d335f294356ac959fbc6687787059cf37d3e58611560c357d495b98dc32563c` |
| source-manifest.json | 33,332 | `9be9c424caee52362e88598ea0fd89bb2020e2c8493751eee4c6a8e6c41fb1a6` |
| source-records.jsonl | 208,163,422 | `449c16c4c8a987b4a0523e5cd91307365d6a8695ce28f0afe871a5610144a681` |
| splits.jsonl | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| targets.jsonl | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Membership, target, features and split files are empty. Their common SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
is not nonempty reproducibility evidence. Nonempty diagnostic hashes attest
preservation/exclusion determinism only. No nonempty admitted-output hashes exist.
Canonical semantic hashes used by existing manifest contracts and byte hashes
including each JSON file's terminal newline are both reported separately.

Real ZIPs, CSV/member contents, addresses, transaction IDs, rows, targets and
exclusions remain under ignored `artifacts/ml/plvr-source-recovery`. Changed
Git-intended files were checked against every real main-row address and official
ID, with zero substring matches; aggregate district/month/type counts are allowed.
No new raw storage, credentials, databases, Parquet or row dumps are staged.
Supplement identity tests use SYNTHETIC labels and are not real records.

ML validation: 122 existing foundation/recovery/parser tests plus 69 new
semantic/temporal tests, **191 passed**. New tests cover rights and required
interests, object roles/counts, invalid denominators, joins/area/floor conflicts,
availability classes/current retrieval, revisions/cancellations, conservation,
held-out membership, maturity/freezes and subprocess determinism. Full Python
regression: **3035 passed, 31 skipped, 1 warning in 262.31s (0:04:22)**.

An initial full run required restoring existing locked frontend dependencies;
`npm ci --ignore-scripts --no-audit --no-fund` restored TypeScript without changing
tracked package/lock files or installing ML packages. A later run under concurrent
real builds hit `test_two_active_two_queued_and_fifth_fails_closed` worker-start
timing; it passed in an isolated rerun after builds ended. That intermittent
failure and interim tests during fixture edits are preserved in ignored logs.
The final full regression ran after builds finished and Python code froze.

Independent review found and prompted fixes for native-right/status disagreement,
misclassified common objects, missing-proof exclusions, conflicting semantic
versions, supplement scope binding, frozen fit membership, label/clock provenance,
floor agreement, last-month completeness and hindsight revision membership.
All Critical/Important findings were resolved. Independent final code, delivery
artifact and authored report review report no remaining Critical, Important or
Minor findings; final review is recorded in machine validation before commit.

## Exact remaining evidence gap

The smallest semantic gap is an authoritative mapping for a candidate transaction
that identifies its one private registered dwelling, all common/ancillary objects,
the transferred building fraction and the complete required land/common
interests, tied to the exact recovered row and detail bytes. Current building
schemas have no building-right fraction denominator, registered unit count or
object identity/role capable of establishing that mapping. A reviewed official
registry/document extract or official immutable supplemental schema/records
providing these fields would unblock semantic classification for that bounded
subset. Ordinary parcel fractions and declared counts cannot substitute.

For PIT readiness the same candidate/version additionally needs immutable
official publication logs or independently trustworthy historical observations
bound to its exact bytes at/before fold cutoffs, and authenticated namespace plus
complete revision/cancellation coverage (or justified snapshot semantics).
Current retrieval establishes only October 2026 bounds. Expanding archive volume
without these fields does not close either gap. Sufficient complete mature
releases and two matching nonempty builds would then be required for evaluation.

## Requested final-report register

| Item | Result |
|---|---|
| 1 Starting SHA | d06ed4f062a212fed4ce0adf092c2fdc515a3f62 |
| 2 Branch | research/ml-valuation-semantic-temporal-closure-v1 |
| 3 Prior blockers | Rights, dwelling, area/target, historical availability, revision, nonempty build and chronology; prior 0 rows |
| 4 Sources | Two exact 112S3/115S2 ZIPs; Taipei/New Taipei sale main + complete build/land/park details |
| 5 Rights fields | Native land ownership fractions available; building numeric rights/object basis absent |
| 6 Rights classifier | Strict full/partial/ambiguous/unknown, with required-interest and exact supplement binding |
| 7 Full rights | 0 |
| 8 Dwelling fields | Declared building count/detail rows available; registered one-unit basis absent |
| 9 Dwelling classifier | Registered mapped one-unit, consistent floor/area/roles; ambiguous multiplicity excluded |
| 10 Single dwelling | 0 |
| 11 Parking | 13,433 absence confirmed; other classes excluded |
| 12 Area | Registered m² × 0.3025; common/ancillary may be included; no interior claim |
| 13 Target | Total NTD / registered ping, ln; 0 qualified labels |
| 14 Reconciliation | Raw 21,244 within/10,411 mismatch; residential no-parking intersection 10,758 within/84 outside scope; diagnostic only |
| 15 Availability sources | Official catalog/download/FAQ; exact current HTTPS observations; no authenticated past publication |
| 16 Classes | Two current upper bounds, 37,669 occurrences; other recovered classes 0; 15 unrecovered prior releases unknown |
| 17 Historical availability | 0 releases, 0 occurrences |
| 18 Policy | Never earlier than evidenced exact/version bound; next midnight for date-only; first-seen alone excluded |
| 19 Revision identity | 37,669 provisional families, all REVISION_UNVERIFIED |
| 20 Supersession/cancellation | 0 attested edges/events; no changed-ID inferred links |
| 21 As-of | Full ledger before eligibility and per-block historical membership check; no later rewrite |
| 22 Geography | All 37,669 source/registry-consistent; no district-only repair |
| 23 Funnel | 37,669 → 37,668 → 16,689 → 13,573 → 13,028 → 0 at rights; full table above |
| 24 Candidates | 0 |
| 25 Approved geography | None (raw Taipei/New Taipei only) |
| 26 Approved types | None (attempt supports 公寓, 華廈, 住宅大樓) |
| 27 Approved time | None |
| 28 Monthly coverage | All approved counts zero; raw counts in JSON, not complete mature coverage |
| 29 Split viability | False; no assignments |
| 30 Train period | None |
| 31 Validation period | None |
| 32 Calibration period | None |
| 33 Test period | None |
| 34 Maturity | Byte-bound release availability before each freeze; full last test month completed; no guessed lag |
| 35 Baselines | All 3 unready; frozen as-of input support implemented |
| 36 Two builds | 13/13 files byte-identical with frozen code/contract; both admitted outputs empty |
| 37 Nonempty hashes | No admitted-output hashes; nonempty diagnostic hashes above do not satisfy gate |
| 38 Privacy | Real addresses/official IDs absent from changed tracked content; raw artifacts ignored |
| 39 Files | 12 bounded ML code/test/contract/plan/report files; no production changes |
| 40 Modules | Added rights_dwelling, temporal, strict_cohort, chronology, audit_semantic_temporal_closure; extended lineage |
| 41 Added tests | 69 semantic/temporal parametrized cases in test_ml_semantic_temporal_closure.py |
| 42 Existing ML | 122 passed |
| 43 New tests | 69 passed; total ML 191 |
| 44 Full Python | 3035 passed, 31 skipped, 1 warning in 262.31s (0:04:22) |
| 45 Independent review | Final code/artifact/report review clear; independently scanned all 12 files |
| 46 Critical/Important | 0 unresolved |
| 47 Gate | BLOCKED |
| 48 Approved scope | None |
| 49 ML-B | May not begin |
| 50 Handoff | None issued |
| 51 Remaining blocker | Exact one-dwelling complete-interest mapping + historical byte-bound availability/complete revisions, then mature nonempty folds |
| 52 Commit SHA | Reported in final response; sole local commit has the exact requested message (self-referential hash is not embedded) |
| 53 git status --short | Final response records verification after the sole commit |
| 54 git diff --check | Precommit check passed; final response records the postcommit check |

No training, ML library installation, production valuation/API/schema/UI changes,
push, merge or deployment occurred. Branch/worktree and ignored audit artifacts
are retained. Commit message: `research: close ml semantic and temporal evidence gaps`.
