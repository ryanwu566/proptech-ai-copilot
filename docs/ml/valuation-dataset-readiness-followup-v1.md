# ML-A foundation follow-up v1

Date: **2026-10-07, Asia/Taipei**. Starting SHA: `9435233ca38843dbeabbe8327148acd199f405ee`. Branch: `research/ml-valuation-dataset-foundation-v1`.

**Verdict: BLOCKED. ML-B may not begin.**

This is a narrow re-evaluation of the canonical [ML-A findings](valuation-dataset-readiness-v1.md). The historical audit/evidence have not been overwritten. See the [foundation report](valuation-dataset-foundation-v1.md), [release ledger](valuation-source-release-ledger-v1.json) and [aggregate evidence](valuation-dataset-foundation-evidence-v1.json).

| Canonical blocker | Repair achieved | Actual acceptance evidence | Follow-up status |
| --- | --- | --- | --- |
| B1: raw residential/target/area/parking semantics | Strict parsers, conservative rules, source/staging contracts and synthetic tests | No raw archives; no real rights/detail/parking/area attestation; target-valid cohort unknown | BLOCKED |
| B2: historical availability/version lineage | Versioned offline release ledger; occurrence/family/version IDs; explicit-chain as-of selection and cancellation tests | 17 historical publication/availability timestamps unknown; no complete real occurrence ledger | BLOCKED |
| B3: geography/identity ambiguity | Reconciled failure classification; source-member county checks; no guessed remaps or destructive dedupe | 115,113 cross-county registry mismatches remain source-unresolved; 457 fact groups / 1,026 rows unresolved | BLOCKED |
| B4: reproducible source storage | Checksum/member/schema/build/manifest contracts and bounded recovery/storage workflow | 17 locally missing archives; 0 exact archive recoveries; no approved PLVR immutable-store restore or two real dataset builds | BLOCKED |
| B5: actual cohort volume/chronology | Deterministic bounded funnel with count conservation and explicit unknown stages | 451,672 inherited official rows and 351,286 type-only proxy; actual residential/parking/target/PIT counts unknown | BLOCKED |
| B6: raw date/floor/classification transforms | Offline exact mixed transaction target, strict calendar/floor/units/parking/revision tests; no wall-clock age | Synthetic transforms pass; matching real-release parser/detail/schema integration still absent | PARTIALLY REPAIRED; not sufficient to pass |

Source recovery: **17 MISSING locally**, **remote exact-byte recovery UNKNOWN**, **253,796,255 historical declared bytes**. Historical retrieval claims are August 2026; they do not establish earlier public availability. No source download was performed.

Geography diagnostics reconcile: **325,585 registry-plausible + 115,113 mismatched + 10,974 city-level-only = 451,672**. `台` variants affect an overlapping 211,170 rows and do not resolve county lineage. All mismatched districts appear under some other current county, which supports contamination diagnosis but does not authorize row remapping.

Parking: all **451,672 legacy rows UNKNOWN** from the absent parking columns. Target-valid/final candidate counts are **null/unknown**. Official staging rows audited in this task: **0**. No evidence supports a smaller actual trustworthy cohort yet.

Executed validation: focused offline fixtures, input bounds/privacy, formal JSON Schemas using the already installed validator, manifest count/cutoff checks, aggregate reconciliation and deterministic reruns. Independent review findings were reproduced and fixed; final verification details appear below. These checks certify foundation behavior, not source truth or ML readiness.

## Final verification record

- `python -m pytest tests/test_ml_dataset_foundation.py -q --basetemp=.pytest-temp-ml-foundation`: **89 passed**. Temporary test inputs remain in the ignored workspace directory.
- All three Draft 2020-12 schemas validate; the actual release ledger and synthetic manifest/staging fixtures pass formal validation. Runtime contract checks reject missing availability, changed feature/source contracts and unreconciled counts.
- Canonical city/type/month/district counts, residential-type proxy, duplicate arithmetic and geography partition reconcile.
- Two fresh CLI processes produce identical full output bytes; their parsed output matches the checked-in evidence. Fresh ledger reconstruction also matches the checked-in ledger. This is report determinism, not two real dataset builds.
- Generated aggregate evidence is approximately 6 KiB; release ledger approximately 31 KiB; no row dataset or source ZIP is staged.
- Independent review's Important issues, including the missing-ID conflict bypass, were reproduced with failing tests and fixed. The final reviewer confirmed **no unresolved Important/Critical findings** and independently passed 81 read-only tests (six temporary-file tests excluded); the root run passed all 89, including two subsequent Git line-ending reproducibility checks.
- Local documentation links, Python compilation, JSON parsing, scoped file inventory and Git whitespace checks pass. Production paths and canonical audit files are unchanged.

## Exact remaining prerequisites

1. Restore a bounded real source release set by exact archive/member/schema checksums; establish declared county/time coverage and preserve details.
2. Implement/onboard matching archive/CSV parsing and reviewed full-rights, one-dwelling, area and no-parking proof. Obtain a nonempty actual cohort with row locators and target reconciliation.
3. Establish evidenced historical public availability or conservative authenticated bounds and complete ordered identity/revision/cancellation history. If only prospective evidence exists, collect prospectively rather than fabricate historical timestamps.
4. Resolve source county/official ID namespace conflicts from source evidence; quarantine unresolved collisions and city-level-only labels.
5. Provision or verify an approved private immutable PLVR artifact store/retention/restore contract; build two complete real datasets with identical full output/exclusion/manifest hashes.
6. Measure actual conservative eligible counts, subgroup coverage, contiguous mature months and availability-safe train/validation/calibration/test boundaries.

Road and age remain excluded/deferred. No model training, production changes, infrastructure change, upload, push, merge or deployment is authorized by this result. Completion of the foundation repair commit does not mean ML-A passed.
