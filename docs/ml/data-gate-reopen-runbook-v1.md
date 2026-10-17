# Data Gate Reopen v1 operator handoff

Target A remains **BLOCKED**. Target B remains **BLOCKED for training/evaluation**.
The real baseline is 2,267 research candidates, zero PIT-valid observations,
zero chronological observations and zero approved cohort. **ML-B MAY NOT BEGIN.**
This command is offline and does not train, evaluate a model, change production,
create an ML UI, deploy or push. Synthetic contract tests establish software
behavior only. No new official evidence was acquired in this slice.

## Pipeline and ownership

| Stage | Existing owner reused by the operator command |
| --- | --- |
| Official sources/captured evidence | `external-official-sources-v1.json`, `external-acquisition-map-v1.json`, retained private originals; no network in the reopen command |
| Receipt schema/authority/scope/hash | `external_evidence.validate_receipt`, `retained_file`, `in_scope`; `reopen_data_gate.validate_receipts` classifies incomplete versus invalid evidence |
| Source registry and raw/schema/detail validation | `reopen_data_gate.load_bundle`, `audit_foundation._archive_status`, `audit_target_reframing.stage_manifest`, `audit_source_recovery._load_members`, `plvr_raw_parser` |
| Full lineage before target selection | `external_evidence.ingest`, `historical.select_as_of`, `lineage.select_as_of`; reopen admission additionally requires closed visible history at every freeze |
| Target B population | `observed_transaction.classify`; `historical.data_gate` rebuilds the full population from staged originals |
| PIT membership | `historical.select_pit_v3`, publication and dependency validation |
| Chronology | `chronology.design_splits`, full-ledger reselection at each of the four freezes; family/version disjointness and existing maturity/subgroup rules |
| Admission | unchanged `external_evidence.admission` and `ml-b-admission-v2.json`; reopen additionally requires release continuity and closed history |
| Approved cohort | `reopen_data_gate.rebuild` verifies two fresh builds before approval; `artifacts` exports private frozen membership only on PASS |
| ML-2 guard | `check_training_authorization.authorized` rebuilds twice and compares every frozen artifact against fresh results |

| Evidence | Software classification | Current external state |
| --- | --- | --- |
| E1 historical publication | IMPLEMENTED VALIDATION: `validate_receipt`, `historical.historical_proof`, `temporal.resolve_availability` | MISSING REAL EVIDENCE: exact original bytes/version hashes bound to historical publication bounds before intended freezes |
| E2 namespace authority | IMPLEMENTED VALIDATION: namespace receipt schema, authority/scope checks, `lineage.identify` | MISSING REAL EVIDENCE: uniqueness/reuse/correction/cancellation/replacement semantics across releases/counties |
| E3 revision/cancellation/replacement | IMPLEMENTED VALIDATION: receipt event binding, complete visible ledger certificates, as-of selector, reopen closure checks | MISSING REAL EVIDENCE: all original/version/tombstone/duplicate/changed-ID edges and completeness at each freeze. MISSING SOFTWARE for accepting cross-namespace replacement families: the existing selector deliberately quarantines these even with an explicit edge; this slice does not guess a resolver or authorize their exclusion to get PASS |
| E4 release continuity | Previously MISSING SOFTWARE for a distinct release manifest attestation. IMPLEMENTED VALIDATION in `ReleaseContinuityReceipt` and `continuity_valid` now binds the exact declared archive inventory, explicit predecessor order, no gaps, both counties, covered dates and attested cutoff | MISSING REAL EVIDENCE: complete provider manifest including overlapping originals, refreshes, withdrawals and replacements; quarter/date labels alone never prove continuity |
| E5 rights/unit linkage | IMPLEMENTED VALIDATION: `RightsUnitMappingReceipt`, `rights_dwelling.classify`, payload/object/role/fraction binding | NOT REQUIRED FOR TARGET B; still MISSING REAL EVIDENCE and required for Target A. Complete dwelling rights and registered unit counts remain unverified |

`IMPLEMENTED_VALIDATION` describes code, never government authentication. In a
machine decision's `evidence` map it means the supplied evidence passed that
stage's implemented checks; it is not an independent claim about the institution.
A human data steward must inspect the retained original, its agency authority,
historical claims, exact correspondence, lawful reuse and scope before recording
the existing REVIEWED_AUTHORITY receipt metadata. Hashes and Booleans cannot do
that review. Missing evidence cannot become an assumed no-correction/no-cancellation.

## Private bundle contract

Use `docs/ml/contracts/data-gate-bundle-v1.schema.json` for `bundle.json`.
It has closed fields: `version`, `cutoff`, `observation_at`, `sources`, `receipts`,
and optional `execution_observed_at`. Each source declares its bounded release
ID/version, relative retained path, SHA-256, byte size, official URL and recorded
retrieval time. Sources may include newly received official versions outside the
old 17-release recovery inventory; they still require the same reviewed embedded
schemas, county/main/detail bindings, ZIP limits, CRC and exact byte checks. An
unreviewed schema version is invalid evidence, requiring a separate schema review.
Maximums are 128 source versions, 1,024 receipts and 100,000 main occurrences;
there is no truncation to obtain a passing result.

Receipt objects use the existing four schemas plus
`release-continuity-v1.schema.json`. Retained receipt paths resolve under the
private bundle and are individually rehashed. The continuity receipt is an
explicit, reviewed ordered provider manifest. Each entry contains release ID,
archive SHA-256 and authoritative predecessor release ID (null for its first
entry). It must cover the exact supplied inventory, both counties, every
included effective date, and history through the cutoff, with no declared gaps.
A branching/unresolved replacement manifest stays BLOCKED pending an explicit
contract/resolver review. Do not linearize it by hash, filename or date order.

Each lineage receipt's `visible_ledger_sha256` binds the *enriched research
ledger*, not a provider-issued research ID. The steward must establish the
correspondence from official events to archive/member/physical occurrences and
version hashes, then certify the complete visible ledger at the final cutoff
and each exact fold selection cutoff. Keep all of that correspondence private.
The hash covers intake clocks and receipt references too: freeze the operator
observation and reviewed receipt IDs/proof hashes before final certification.
No missing predecessor, changed-ID edge, cancellation or unknown dependency may
be dropped to certify the remaining rows. Explicit cross-namespace replacements
remain blocked until a separately reviewed authoritative resolver exists.

`execution_observed_at`, when provided, is the operator's explicit observation
of this new intake, used for the new ledger's ingestion/transformation clocks.
It must follow all source **and receipt** retrievals and not exceed
`observation_at`. It never becomes historical publication availability. Leave it
absent for an old logical snapshot whose execution time is unknown: execution
clocks remain null and cannot authorize training. The program never samples a
wall clock, file mtime or download time to manufacture publication evidence.
Date-only official publication proof uses the existing conservative next-Taipei-
midnight upper bound, with the original precision retained privately.

## Exact PowerShell procedure

Run from this repository root. Choose private locations outside **every** Git
checkout; ignored directories inside a checkout are also rejected for new intake
and output. Evidence and output directories must be separate siblings. Existing
outputs are accepted only when their exact file set and bytes are identical;
otherwise choose a fresh output directory.

1. Store originals privately. Keep applicant names, contacts, case applications,
   addresses and official transaction tokens out of Git. Where a retained proof
   contains personal material, use the separately retained authority-prepared
   non-personal proof required by the receipt contract; do not claim a personal
   original is NON_PERSONAL.

   ```powershell
   $private = 'C:\Projects\proptech-private-evidence\ml-datagate-reopen-v1'
   $evidence = Join-Path $private 'received'
   New-Item -ItemType Directory -Force -Path $evidence | Out-Null
   # Save official response attachments and exact original ZIPs here.
   ```

2. Hash the retained originals. Keep this listing private; do not paste document
   contents, full paths or transaction IDs into a committed report.

   ```powershell
   Get-ChildItem -LiteralPath $evidence -File | Get-FileHash -Algorithm SHA256 |
     Export-Csv -LiteralPath (Join-Path $private 'original-hashes.csv') -NoTypeInformation -Encoding utf8
   ```

3. Create the private `bundle.json` and reviewed receipts against the contracts
   above. Use original recorded retrieval times and actual agency evidence.
   Record `execution_observed_at` and `observation_at` explicitly for the intake
   observation. Do not backdate them or change them between the double runs.
   Requested receipts/lineage certificates are not supplied by this repository.

   ```powershell
   $env:PYTHONUTF8 = '1'
   $env:PYTHONIOENCODING = 'utf-8'
   python -m pip install -r requirements-dev.txt
   python -m json.tool (Join-Path $evidence 'bundle.json') > (Join-Path $private 'bundle-readable.private.json')
   ```

4. Run evidence validation. The same command performs steps 5 and 6 in order,
   twice independently, without a caller-provided determinism approval flag.

   ```powershell
   $review = Join-Path $private 'received-dry-run'
   python -m scripts.ml.reopen_data_gate --bundle $evidence --output $review --dry-run
   $gateExit = $LASTEXITCODE
   Get-Content -LiteralPath (Join-Path $review 'summary.md')
   ```

5. The command rebuilds Target B candidates and PIT membership from the original
   archives, full unfiltered history and publication/dependency evidence. No
   earlier candidate/membership file can substitute for this rebuild.

6. The command rebuilds chronological eligibility and evaluates the frozen
   admission policy. After reviewing the dry run, use a new output directory to
   request the actual gate decision and, only on PASS, freeze the private cohort.

   ```powershell
   $frozen = Join-Path $private 'received-frozen'
   python scripts/ml/reopen_data_gate.py --bundle $evidence --output $frozen
   $gateExit = $LASTEXITCODE
   $decision = Get-Content -Raw -LiteralPath (Join-Path $frozen 'decision.json') | ConvertFrom-Json
   $decision.status
   ```

7. If BLOCKED, do not train. Obtain the missing E1-E4 proofs/coverage; E5 remains
   a Target A blocker. INVALID_EVIDENCE means malformed/corrupt/unbound input;
   correct the private bundle using originals and rerun in a fresh directory.
   Exit codes: PASS=0, BLOCKED=1, INVALID_EVIDENCE=2. Dry-run always withholds
   authorization and approved membership, even for complete inputs.

8. If PASS, retain the immutable complete private output and only then authorize
   a **separate ML-2 branch**. The guard must pass immediately before ML-2 starts:

   ```powershell
   python scripts/ml/check_training_authorization.py --bundle $evidence --frozen $frozen
   if ($LASTEXITCODE -ne 0) { throw 'ML-2 is not authorized; do not train.' }
   ```

No ML-2 branch, estimator, training job or deployment is executed by these steps.
Any future ML-2 runner must call this guard and refuse a nonzero result.

## Reproduction and public boundary

Run the same command into a second new sibling output directory without editing
sources, receipts, observation timestamps, contracts, code or Python environment:

```powershell
$second = Join-Path $private 'received-frozen-second'
python -m scripts.ml.reopen_data_gate --bundle $evidence --output $second
$hashA = Get-Content -Raw -LiteralPath (Join-Path $frozen 'output-hashes.json')
$hashB = Get-Content -Raw -LiteralPath (Join-Path $second 'output-hashes.json')
if ($hashA -cne $hashB) { throw 'Outputs differ; do not authorize ML-2.' }
```

Every invocation itself rehashes/reparses/revalidates twice and compares its
aggregate report, full enriched ledger digest and every proposed private frozen
artifact. The comparison happens before setting independent determinism true.
The machine decision records Python, target/receipt versions, contract/code,
source manifest, full bundle, receipt manifest, chronology and output hashes.
`output-hashes.json` hashes the decision/summary and any frozen private artifacts;
it intentionally does not hash itself. The guard checks exact artifact sets,
fresh source/receipt/contract/code/Python identity and bytes, and rejects tampering,
missing files, extra files, symlinks or a hand-edited PASS record.

Only `decision.json`, `summary.md`, and the **hashes** in `output-hashes.json`
are eligible for publication after review. `public_bytes` enforces a closed
recursive shape and value vocabulary, plus existing privacy checks; receipt
filenames, URLs, free text, error messages and raw rows never flow into reports.
All outputs are initially private. The CLI has no public/raw export flag.
Do not copy any frozen row-level file into Git, including derived IDs or features.
The optional PASS handoff contains these exact private artifacts:

| Artifact | Meaning |
| --- | --- |
| `approved-cohort.json` | Frozen family/version/physical membership |
| `train.json`, `validation.json`, `calibration.json`, `test.json` | Disjoint ordered membership, exact freezes and source-ledger binding |
| `features.json`, `feature-contract.json` | Frozen allowlisted features; no prices/IDs as model features |
| `labels.json`, `label-contract.json` | Frozen recorded-transfer labels, separate from features |
| `source-manifest.json` | Exact source hashes and reviewed parser/schema/detail bindings |
| `chronology.json` | Freeze selection, provenance and chronology conditions |
| `decision.json`, `summary.md`, `output-hashes.json` | PASS admission record, operator summary and artifact integrity |

There is no approved real handoff today. Current E1-E4 evidence remains missing;
E5 remains unresolved for Target A. No model was trained.
