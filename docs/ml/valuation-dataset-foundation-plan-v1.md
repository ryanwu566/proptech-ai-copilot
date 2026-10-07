# ML valuation dataset foundation implementation plan

**Goal:** Make the minimum offline semantics, lineage and cohort checks executable, preserve the canonical ML-A findings, and record an evidence-based follow-up gate.

**Architecture:** Standard-library Python modules in `scripts/ml/` operate on bounded local inputs. Source bytes, append-only release metadata and private staging remain outside Git. The audit emits aggregate JSON only and never connects to a serving database or downloads sources.

**Spec:** The supplied 40-section foundation repair request and `valuation-dataset-readiness-v1.md`, especially B1–B6 and the exact initial cohort/target contracts.

**Constraints:** Only this workspace and expected branch; exactly one final commit; no production changes, migrations, provider loops, datasets in Git, training, uploads, push, merge, rebase or deploy. Existing dependencies only. Unknown dates/counts remain null. The task authorizes implementation and the final commit; execute inline, with one independent reviewer at the end.

**Review focus:** Unknown availability must quarantine an identity; selected invalid/canceled revisions must not resurrect older rows; zero parking price alone must not pass; source county conflicts must not be guessed from districts; missing rights/area/schema proof must block eligibility.

## Task 1: Strict offline semantics

Files: `scripts/ml/semantics.py`, `tests/test_ml_dataset_foundation.py`.

- [x] Write and run failing fixtures for geography, raw ROC date precision, single floor, parking contradictions, residential/use/rights, price/area/unit reconciliation and transaction-time age.
- [x] Implement `normalize_geography`, `parse_roc_date`, `parse_floor`, `classify_parking`, `construct_target`, `evaluate_row`. Preserve source values and explicit first/all exclusion reasons. Decimal conversion is exactly 0.3025 ping/m²; no rounding before target construction.
- [x] Run focused tests; expected invalid cases fail closed.

## Task 2: Identity, revision and contracts

Files: `scripts/ml/lineage.py`, `scripts/ml/contracts.py`, `docs/ml/contracts/*.schema.json`, `docs/ml/valuation-source-release-ledger-v1.json`.

- [x] Write and run failing tests for duplicate/republication/correction/ambiguous identities, cancellation, future correction and unknown availability.
- [x] Implement county-namespaced family/version/occurrence IDs and as-of selection over all versions before cohort filtering. Keep every occurrence; emit aggregate selection reasons, never destructive updates.
- [x] Define strict release ledger and dataset manifest schemas, with count/checksum/cutoff relationships and explicit unknown metadata.
- [x] Inventory exactly the 17 canonical releases; distinguish absent local bytes from unknown remote recovery. Validate schemas and inventory statuses with fixtures.

## Task 3: Bounded aggregate audit

Files: `scripts/ml/audit_foundation.py`, `docs/ml/valuation-dataset-foundation-evidence-v1.json`.

- [x] Write and run failing tests for funnel conservation, bounds, aggregate reconciliation, malformed input, deterministic ordering and input immutability.
- [x] Implement canonical-evidence inventory mode and optional private staging JSONL audit mode. Enforce file/row limits; fail on truncation rather than claim complete counts.
- [x] Produce source counts, geography reasons, parking/target/lineage/time/identity aggregates and blockers. Distinguish inherited legacy observations, local recovery evidence and synthetic fixtures.
- [x] Run twice with unchanged inputs; compare complete output hashes.

## Task 4: Evidence and final gate

Files: `docs/ml/valuation-dataset-foundation-v1.md`, `docs/ml/valuation-dataset-readiness-followup-v1.md`.

- [x] Document actual source/recovery results, eligibility derivability, area/parking/target semantics, identity/time contracts, recovery/build/storage workflow and actual versus unavailable funnel counts.
- [x] Narrowly re-evaluate B1–B6; never approve ML-B without a demonstrated defensible cohort.
- [x] Obtain independent review and fix Important/Critical findings, run focused tests, determinism/count/schema/JSON checks, inspect sizes/scope and `git diff --check`.
- [x] Prepare the one authorized commit: `research: establish ml valuation dataset foundation`; report SHA and clean status in final delivery.

## Execution decisions and progress

- Starting state verified: clean; `research/ml-valuation-dataset-foundation-v1`; `9435233ca38843dbeabbe8327148acd199f405ee`.
- No AGENTS.md found in the workspace. Use the existing isolated workspace without creating another worktree outside the permitted path.
- Canonical audit read before implementation. Local historical manifest exists; raw archives/SQLite/Parquet do not. No historical download is required to document this boundary; no mass recovery is attempted.
- Geography reports identify import county contamination; current-registry plausibility alone cannot repair source identity.
- User's one-commit and workspace boundaries override skill defaults for intermediate commits and alternate worktrees. Execution progress will be recorded here.
- Task 1 complete: strict semantics implemented; synthetic eligibility, target, parking, geography, date/floor and month-age fixtures pass.
- Task 2 complete: release/staging/manifest JSON contracts and relational validation implemented; non-destructive identity/version/occurrence and as-of revision selection tested. All 17 local archives are MISSING; publication/ML import counts remain unknown.
- Task 3 complete: bounded aggregate-only CLI implemented; canonical totals reconcile; repeated full CLI outputs match; read-only/input-privacy/bounds tests pass. No real raw staging inputs exist.
- Task 4 complete: reports and narrow follow-up verdict are BLOCKED. Independent reviewer found source admission, physical locator, immutable release/member and manifest-validation gaps; failing regressions demonstrated each and fixes pass. Final suite: 89 passed. Final reviewer confirmed no unresolved Important/Critical findings and passed 81 read-only tests (six temporary-file tests excluded). Two subsequent Git line-ending regressions also pass. One bounded commit is prepared after validation; its SHA is reported in delivery.
- Ruling: no full application/browser suite is needed for this isolated offline addition; the requested focused suite exercises all new tooling, and production paths are unchanged.
- Ruling: private staging is an evidence-linked input contract, not authenticated raw-source proof; no complete archive parser, source attestation, full dataset builder, real chronological split or storage provisioning is claimed.
