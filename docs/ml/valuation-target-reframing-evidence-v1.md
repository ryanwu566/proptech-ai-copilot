# ML Wave 1: target reframing and authoritative evidence v1

**Target A: BLOCKED. Target B: BLOCKED for training/evaluation.** Target B has
**2,267 target-valid research candidates**, not approved dwelling sales or ML
training rows. Point-in-time-valid, chronologically evaluable and approved
training counts are all **0**. ML-B may not begin. Production valuation is unchanged.

Repository `ryanwu566/proptech-ai-copilot`; branch
`research/ml-target-reframing-evidence-v1`; starting SHA
`95018f6fc2a366656cb798414dc54860d009e536`. The required clean worktree, branch,
expected SHA and HEAD equality to local `origin/main` were verified before edits.
No fetch changed that baseline. All dates discussed here use Asia/Taipei.

## What the two targets measure

| Dimension | A: strict property valuation | B: observed residential transaction price |
| --- | --- | --- |
| Estimand | Price per verified complete single dwelling's transferred registered area | Recorded gross transaction consideration per reported transferred registered building ping, in the bounded no-parking subset |
| Observation | Proved complete dwelling interest and registered unit | One official reported transaction occurrence; identity still provisional |
| Source fields | Main/use/area/price plus exact authoritative building/land/object rights mapping | Exact main transaction type, use, reported object counts, price/area/unit price, floor/type/district, complete building/land/parking joins |
| Rights | Complete dwelling rights required; gates unchanged | Unverified complete dwelling rights retained explicitly; reported fractional portions can be part of the observed transfer |
| One dwelling | Registered single dwelling proof required | Reported building count exactly one is an inclusion condition, never unit proof; multiple detail portions explicitly retain unresolved roles |
| Parking | Confirmed absence under v1 | Same confirmed absence; all mixed-parking transactions exclude; no guessed parking deduction |
| Area | Verified registered dwelling transferred area including supported ancillary/common portions | Reported registered transferred area, reconciled to detail sum; never interior/usable area or asserted complete rights |
| Corrections | Full identity/version/cancellation lineage required | Candidates retain revision ambiguity; same full-ledger proof required before PIT/evaluation |
| Responsible eventual output | Only after A approval, a scoped dwelling valuation claim | Only after B approval, conditional observed transaction-price research; no current ML output authorized |
| Leakage | Future price, revised labels, publication, aggregates and present GIS | Same temporal controls; gross/official unit price only construct/reconcile labels, never features |

The changed research question justifies retaining incomplete dwelling-right
knowledge for B: the outcome is a reported transfer, not a verified whole-unit
sale. It does **not** justify missing source verification, parking ambiguity,
historical availability or revision proof. Target A contracts and numerical,
rights, dwelling and parking gates remain intact.

The [MOI FAQ](https://lvr.land.moi.gov.tw/R11/jsp/qa.jsp) distinguishes registered
area from actual usage, describes parking-dependent unit-price calculations,
and cautions that reported building counts and disclosed transactions have
limited interpretation. These explanations support the conservative B estimand;
they do not attest any particular row's registered units or rights.

## Actual evidence and provenance

The prior readiness, foundation, source-recovery, semantic/temporal closure and
closure-follow-up reports, code, contracts and manifests were reused. Existing
archives in `C:/Projects/proptech-ml-semantic-temporal-closure/artifacts/ml/plvr-source-recovery/`
were read and copied, with preflight/download metadata, into this worktree's
ignored artifact root. Nothing in that prior worktree was modified. There were
**zero archive downloads in this wave**, zero commercial listing requests and
zero database operations. Local copies passed the existing expected-hash,
ZIP/package/CRC/limit checks before raw parsing.

| Exact archive | Bytes | SHA-256 | Prior verified HTTPS upper bound (Taipei) |
| --- | --- | --- | --- |
| 112S3 | 14,876,099 | `4d9fa7be16bc9aba99e79c0f86ca27b32f46755de04e98e1dd2c8d8297b466c1` | 2026-10-08T14:23:17.233018+08:00 |
| 115S2 | 14,705,972 | `6b4c148bad106a235dddf214001d605ff9ffa45ac50561f7125c6d7fa795d4da` | 2026-10-08T14:23:31.096999+08:00 |

Archive bytes total **29,582,071**. The nationwide ZIP packages were parsed only
for Taipei `a_lvr_land_a.csv` and New Taipei `f_lvr_land_a.csv`, with each complete
build/land/park detail member. Embedded manifest county/schema bindings and
reviewed schema hashes passed. Other counties/releases were not newly audited.
The other fifteen releases in the inherited recovery ledger were not restored.

Current official pages inspected: [dataset 25119](https://data.gov.tw/dataset/25119),
[seasonal download page](https://plvr.land.moi.gov.tw/DownloadOpenData),
[MOI FAQ](https://lvr.land.moi.gov.tw/R11/jsp/qa.jsp), and
[official supply-system landing page](https://plvr.land.moi.gov.tw/Index).
The catalog identifies the dataset/schema families. The supply page distinguishes
static Open Data from the dynamic query service. Neither binds an exact archive
hash to first historical publication or supplies a complete row-level correction
chain in the recovered evidence. A search-index lead for a change-data service
was not corroborated by the live page and was not promoted to evidence.

Evidence classes are separate: (1) inherited audit history; (2) exact recovered
official bytes and fresh scoped aggregates; (3) current explanatory web content;
(4) synthetic executed contract tests; (5) future approval conditions. Current
web content and synthetic evidence cannot fill missing historical row evidence.

## Implementation and conserving classifications

The versioned [B contract](contracts/observed-transaction-target-v1.json) defines
population, observation unit, types, parking, area, Decimal normalization,
geography, source lineage, exclusions, revision ambiguity, availability,
features, leakage, baselines and eligibility. [Observed transaction logic](../../scripts/ml/observed_transaction.py)
and the [offline builder](../../scripts/ml/audit_target_reframing.py) reuse existing
source verification, CSV parsing, detail indexing, semantic diagnostics and
as-of selection. Chronology receives an explicit B cohort selector; A remains
its default. No completed production or strict pipeline was replaced.

| Class | Actual count | Meaning |
| --- | ---: | --- |
| Raw main observations | 37,669 | Every main CSV transaction occurrence in scope |
| Raw detail observations | 159,995 | 83,942 building; 55,387 land; 20,666 parking |
| All main plus detail records audited | 197,664 | Detail rows never inflate main occurrence count |
| Structurally valid main observations | 37,668 | Parsed day, source locator and county/district valid; one invalid day excludes |
| Target-valid B research candidates | 2,267 | Confirmed no-parking, reported residential one-building transfer subset |
| Point-in-time-valid B observations | 0 | All candidates lack qualified identity/revision history |
| Chronologically evaluable B observations | 0 | No approved historical population or valid folds |
| Approved training cohort | 0 | Approval deliberately separate from candidates |
| Strict A approved cohort | 0 | Original gates preserved and rerun |

Candidate exclusions total **35,402**, so `37,669 = 2,267 + 35,402`. Every main
row has a private eligibility ledger entry containing all semantic reasons and
independent PIT disposition. Sequential first-reason counts are mutually
exclusive; parallel diagnostic counts are never subtracted as if disjoint.

The funnel reaches 16,689 exact type rows after day validation, 13,573 residential
rows, then applies supported types, reported counts, complete detail joins,
restricted detail use, detail-area reconciliation, parking, numerical target,
floor and note rules. Exact stage counts and reason histograms are in the
[bounded machine evidence](valuation-target-reframing-evidence-v1.json).

First exclusions include 20,979 unsupported transaction types, 3,116
non-residential uses, 545 unsupported types, 162 reported multi-building cases,
3,020 unresolved/mixed detail uses, 254 detail-area mismatches, 5 duplicate detail
payloads, 16 parking ambiguities, 64 area-scope exclusions, 1,821 floor
ambiguities, 5,419 reported notes requiring review and one invalid day.

Numerical B labels require positive finite NTD price and m² area, 5–150 ping,
10,000–5,000,000 NTD/ping, explicit area field/unit evidence, and mandatory
official NTD/m² agreement within `max(1, 0.001 * total/area)`. With Decimal
precision 28, `ping = m² * 0.3025` and `NTD/ping = total_NTD / ping`; the log is
derived only after admission. Price support is **outcome truncation of the
research estimand**, not a deployable way to screen predictions by unknown price.
No invalid price is repaired, imputed or silently discarded.

## Parking, rights and registered-object findings

Across all raw rows: 13,433 confirmed no-parking, 16,662 parking present, 7,311
parking ambiguous and 263 unknown. The B candidates all require numeric zero
parking area/price, blank type, reported parking count zero, a complete unique
join with no parking detail, and the existing building-use/note parking guard.
Blank parking numerics never become zero. Unknown or mixed detail uses exclude.

The exact building schema has transferred area, use, floor and transfer label,
but no registered unit count, object-role basis or numeric building-right
fraction. Land fractions alone cannot establish complete dwelling interests.
No real full-rights or registered single-dwelling proof was recovered.

Of B candidates, **827** have one building-detail portion; **1,440** have several.
Both retain unverified registered-unit counts and complete dwelling rights. The
4,328 candidate building portions contain 2,240 reported whole and 2,088
reported fractional transfer labels. These are detail-level descriptions,
never proof that the main transaction conveys a complete dwelling.
Only exact `住家用`, `共有部分`, `共有部份` detail uses are allowed in B v1,
with at least one residential detail and a reconciled area sum. This conservative
string policy excludes other plausible common-use descriptions until reviewed.

Blank notes mean **no reported note**, not proven ordinary/arm's-length sale.
Official disclosure filtering and this restriction still leave selection bias.

## Geography, time and dataset viability

Raw geography: Taipei **11,998** rows across 12 districts; New Taipei **25,671**
across 29. Raw effective months range **2013-06 through 2026-06**; this is sparse
registration-quarter coverage, not a complete continuous historical panel.

Candidate geography: Taipei **707** across all 12 districts; New Taipei **1,560**
across 24 districts. Types: **1,018 公寓**, **792 住宅大樓**, **457 華廈**.
112S3 contributes **1,434** candidates and 115S2 **833**. Candidate effective
months range **2022-07 through 2026-05**, in only **24 observed months**, with
large gaps. The largest month, 2023-06, has **423** candidates (**18.66%**).
The 2023-05–07 concentration alone supplies 1,220 candidates (53.82%). Several
district totals are below the per-block subgroup minimum, even before time
partitioning. Full marginal coverage is recorded without transaction rows.

There are **37,669 provisional families**, **0 repeated provisional identifiers**
in this bounded scope and **0 attested correction edges**. Absence of repeats
does not prove cross-release uniqueness, changed-ID linkage or no corrections.
Selection bias includes official disclosure screening; transaction-only sampling;
no-parking, blank-note, floor, exact-use and target-support filters; fractional
and common-area transfers; two isolated registration quarters. Neither time nor
nationwide population generalization is defensible.

Chronological status is **BLOCKED**. No train/validation/calibration/test dates
were selected. The existing maturity contract requires at least 21 **contiguous,
complete, mature** months, adequate monthly and district/type block volume,
historically frozen full-ledger membership and a completed test observation
period. Twenty-four sparse candidate months do not satisfy those conditions.

## Publication, revisions and leakage controls

Embedded `build_time.xml` describes registration/contract windows: 112S3 sales
registered 2023-06-11–2023-09-10; 115S2 sales registered
2026-03-11–2026-06-10. Neither is a publication timestamp. All release-published
timestamps remain null; historical first publication is proved for **0 releases**.
The October 8 exact HTTPS observations are conservative present upper bounds
only. All 2,267 candidates are public by the explicit October 9 audit cutoff,
but none is thereby proved public at its historical fold freeze.

The full occurrence ledger is resolved before eligibility. Unknown namespace,
cancellation state or revision chain excludes; there is no latest-download,
hash-order or rounded-fact correction inference. Future available versions cannot
overwrite earlier labels; an ineligible current correction cannot resurrect an
old qualifying row. Identical/repeated families cannot cross fitting/evaluation
blocks. Changed-ID links remain a blocker. Date-only publication advances to
the next Taipei midnight; system first-seen alone gives no public timestamp.
Logical observation clocks leave ingestion/transformation instants null rather
than manufacturing historic execution times.

Only district, supported type, reported transferred area, validated floor and
explicit prediction calendar are feature columns. Transaction calendar is a
retrospective conditional research scenario; prospective inputs must be known
independently at the planned scoring date. Current GIS/POI/Routes/Places/MRT,
hazards, present market summaries, LLM outputs, future correction fields, IDs,
addresses and behavior are excluded. Age is deferred; any future age feature
must use completion and transaction-time evidence, never current age. Roads
remain experimental. Label construction never adds price to features.

## Baseline preparation and reproducibility

Global median, district/type median and comparable estimator contracts use only
approved frozen TRAIN family/version membership, with public availability
strictly before the earlier prediction/fitting boundary, effective transaction
before scoring, and subject-family exclusion. B's executable historical selector
uses B rather than accidentally falling back to A. Unknown changed-ID links
still prevent actual evaluation. Comparable/tuning decisions may use TRAIN and
VALIDATION only; calibration and test cannot fit or select. Synthetic tests
verify nonempty B folds and baseline input support; no estimator/model was fitted.
All three actual baseline-readiness decisions remain **false**.

Two clean final builds, `artifacts/ml/plvr-source-recovery/target-final-a` and
`target-final-b`, used identical exact sources, code, contracts, registry,
Python version and October 9 00:00 Taipei cutoff/logical observation time.
**All 14 files match byte for byte**, including source manifest, occurrences,
membership, targets, features, exclusion/eligibility/revision ledgers,
chronological outputs, approved membership, dataset manifest and evidence.
Each candidate membership/target/feature file has 2,267 rows; exclusions have
35,402; the eligibility ledger has 37,669. Every occurrence's availability
reference matches the persisted source-manifest canonical hash
`017706a2da5b5dbe2fa2bbac265b3dd8077af6577d7a2ac3066bbfc36a48ab2e`.
Exact output hashes are in the machine evidence. A prior diagnostic build was
retained but is not one of these final builds. Matching nonempty candidate files
prove candidate extraction only; empty PIT/training outputs never authorize ML-B.

## Exact missing evidence and recommendation

For **A**, obtain authoritative exact-row private/common building objects,
registered-unit count, numeric transferred/required building interests and the
complete required land/common interests. One main row, one detail, a whole
transfer label or a blank note cannot substitute.

For **B**, complete dwelling-right proof is not the immediate gate. Obtain:

1. An official namespace/reuse specification for `編號`/transfer identifiers,
   plus exact version-level old→new and cancellation mappings, including
   changed-ID corrections and coverage/completeness attestations. The static
   archives and dynamic-query relationship alone do not supply this.
2. Authenticated release records or trustworthy historic captures binding
   **each exact ZIP hash/version** to a publication/observation bound before its
   intended freeze. October 2026 captures cannot serve 2023 historical fitting.
3. Only then, restore a declared contiguous registration/release panel with
   authenticated coverage and revisions; verify mature monthly and subgroup
   volumes with B's actual exclusions. Re-run per-freeze membership and two
   nonempty PIT/evaluation builds. Do not choose dates to force four blocks.

Until this evidence exists, retain the 2,267 candidates for source/semantics
research. No ML-B handoff or training authorization is issued. This is a concrete
transaction-level path with remaining identity/time blockers, not a relabeling
of incomplete dwelling transactions as valuations.

## Execution register

Tests: **53 focused target tests passed**, **244 complete ML tests passed**,
and **3,385 full Python tests passed, 0 failed, 32 skipped**, in 399.55 seconds.
The 32 skips are explicitly gated database/integration cases; one existing
Starlette/httpx deprecation warning remains. The full command was
`python -m pytest -q -ra`; PowerShell expanded `tests/test_ml_*.py` for the ML run.
Source modules and builder had RED→GREEN tests before implementation. Independent
review found an intermediate provenance hash and an inconsistent type
normalization; both were reproduced and corrected with focused regressions.
The reviewer independently reran 53 tests and reviewed code, aggregate privacy
and report claims: **0 unresolved Critical/Important/Minor findings**. The reviewer
did not independently reparse the ZIPs or verify live web content; the implementing
agent performed final two-build/source-binding and full-suite checks.

The initial full run had 40 failures, 3,343 passes and 32 skips during dependency
setup/concurrent data builds. Missing locked TypeScript caused frontend failures;
worker/spatial timing cases also failed. After `npm ci --ignore-scripts --no-audit
--no-fund`, a targeted rerun passed 39 and failed one existing worker timing case
under build load. The final complete run, with builds finished, passed all 3,385.
Neither production code nor timing limits were changed to pass these checks.
No ML dependencies were added; package/lock files are unchanged.

| Requested item | Final disposition |
| --- | --- |
| 1 Starting state | Required clean branch/SHA and local origin/main equality verified |
| 2 A verdict | BLOCKED; 0 approved; gates unchanged |
| 3 B verdict | BLOCKED; transaction-level target definition supported, training/evaluation unapproved |
| 4 Recovered evidence | Two exact local ZIPs, 29,582,071 bytes, complete scoped main/detail members; no new archive downloads |
| 5 Rows audited | 37,669 main + 159,995 detail = 197,664 |
| 6 Structural rows | 37,668 |
| 7 B target candidates | 2,267 |
| 8 PIT rows | 0 |
| 9 Approved rows | 0 |
| 10 Coverage | Taipei/New Taipei; candidates 2022-07–2026-05, 24 sparse months, 23 missing months, longest observed run 9 months |
| 11 Parking/rights | Confirmed no-parking only; complete dwelling rights/unit count remain unverified |
| 12 Revision/publication | 0 attested chains/cancellations/historical publications; current October 8 upper bounds only |
| 13 Leakage | Full-ledger selection, strict freezes, duplicate protection, source identity, feature allowlist, frozen baseline versions |
| 14 Baselines | Three contracts and executable B history prepared; all actual baselines unready |
| 15 Reproducibility | 14/14 final files identical; nonempty candidates, no nonempty approved proof |
| 16 Files | Eight bounded ML files listed below and in JSON |
| 17 Tests | 53 focused / 244 ML / 3,385 full passed; 0 final failures; 32 integration skips; 1 warning |
| 18 Independent review | Code + reports reviewed; limitations above |
| 19 Findings | Both reproduced review defects fixed; 0 unresolved |
| 20 Blockers | Exact rights/unit proof for A; identity/cancellation/revision proof, historical byte-bound availability and mature contiguous population for B |
| 21 ML-B | May not begin; no handoff issued |
| 22 Commit | Exactly one requested local commit; SHA recorded in final response |
| 23 Git status | Final postcommit result in final response |
| 24 Diff check | Precommit passed; final postcommit result in final response |
| 25 Safe for PR? | Yes for bounded research review after a user-controlled push; no training/product approval; no push/PR performed |

Changed files: `scripts/ml/observed_transaction.py`,
`scripts/ml/audit_target_reframing.py`, `scripts/ml/chronology.py`,
`tests/test_ml_target_reframing.py`,
`docs/ml/contracts/observed-transaction-target-v1.json`,
`docs/ml/valuation-target-reframing-plan-v1.md`, this report and its JSON evidence.

Privacy verification scanned changed files against **37,669 real official IDs**
and **35,976 full address strings** and found none. Raw ZIPs, main/detail rows,
addresses, official IDs and all JSONL outputs remain ignored. Only ML code,
synthetic tests, contracts, this plan/report and bounded aggregates are committed.
No model training, production valuation/service/UI/database change, push, merge
or deployment is part of this wave. Commit message:
`research: implement ml target reframing and evidence recovery`.
