# PLVR Authoritative Lineage Recovery and Collision Resolution v1

## Safety boundary

This is the Phase 2B-1.5 evidence report. Production access was **SELECT only**.
No transaction, aggregate, import run, schema object, runtime setting, or
credential was changed. This report does not authorize Phase 2B-2.

Snapshot: `2026-08-11T15:33:34+08:00`

Final SELECT-only recount: `2026-08-11T15:41:34+08:00`; official rows,
canonical invalid rows, future rows, and aggregate rows were unchanged.

Baseline commit: `8511576e2de1e4a17433056f5323793e22b5767d`

## Result

Gate: `NOT_READY_FOR_ANY_PHASE_2B2`

The audit found no invalid transaction that can be deterministically joined to
an immutable official artifact, an immutable row-linked import run, or a
verified official transaction identity. The correct scoped repair cohort is
therefore empty. An empty cohort is a safety result, not a failed attempt to
invent a target.

| Repair-ready cohort | Rows |
| --- | ---: |
| `AUTHORITATIVE_UPDATE_READY` | 0 |
| `PROVABLE_DUPLICATE_READY` | 0 |
| `AUTHORITATIVE_REIMPORT_READY` | 0 |
| Total scoped ready | 0 |

## Lineage inventory

| Evidence | Production coverage | Row join | Immutable | Authority |
| --- | ---: | --- | --- | --- |
| `real_price_transactions.id` | 451,672 (100%) | Direct row locator | Stable DB identity | Not source identity |
| `source` | 451,672 (100%) | Direct | No artifact identity | Supporting only |
| `imported_at` | 451,672 (100%) | 154 exact run timestamps; 0 invalid rows | No | Supporting only |
| `dedupe_key` | 451,672 (100%) | Direct | Algorithm/version unknown | Supporting identity only |
| `raw_note` | 0 non-blank | Direct | No | None |
| `valuation_import_runs` | 57 runs | No transaction FK | Run summaries only | Partial |
| Run note file summaries | 56 runs, 5,113 entries | No row-to-file join | No artifact hash | Partial |
| Artifact/release/hash columns | Absent | None | No | None |
| Official pipeline tables | Absent in production | None | N/A | None |

Every stored key is a distinct 64-character hash, but no key-version or source
transaction identifier is stored. All 56 parseable run notes describe multiple
files. They preserve filename, encoding, row count, and city hint, but no
artifact checksum, release ID, raw-row identity, or transaction FK.

The repository and local project data contain samples, mocks, registries, and
derived catalogs, but no historical official PLVR ZIP, formal import manifest,
or hash-bound production artifact. Status:
`AUTHORITATIVE_ARTIFACT_UNAVAILABLE`.

### Invalid-row lineage

| Status | Rows | Meaning |
| --- | ---: | --- |
| `COMPLETE` | 0 | No deterministic row to artifact/city chain |
| `PARTIAL` | 126,087 | Source/date/key metadata exists without authoritative join |
| `MISSING` | 0 | All rows retain at least partial operational metadata |
| `CONFLICTING` | 0 | There are no competing authoritative sources to compare |

Partial lineage cannot promote a row. District uniqueness, address county,
period, price, area, building type, counterpart facts, and import date remain
Level D supporting evidence.

## Collision resolution

### Exact-fact collisions

All 57,350 exact-fact collisions are `DUPLICATE_IDENTITY_C`: normalized facts
match, but official transaction ID, immutable artifact, and raw-row identity
are missing.

| Disposition | Rows |
| --- | ---: |
| `PROVABLE_DUPLICATE_READY` | 0 |
| `PROBABLE_DUPLICATE_ONLY` | 57,350 |
| Conflicting lineage | 0 |
| Unresolved fact comparison | 0 |

Fact equality is not proof that two rows represent one official transaction.
No deletion or quarantine write is authorized.

### Three natural-key collisions

The prior Phase 2B-1 artifact committed aggregate counts only, so it does not
contain safe row references, current/target geography, or counterpart hashes
for these three rows. A fresh SELECT-only natural-fact check confirmed the
collision population but did not recover official identity. The only bounded
difference category is one or more exact-identity fields beyond the natural
key: building age, floor, or total floor.

| Case | Lineage | Differing category | Safest disposition |
| --- | --- | --- | --- |
| `phase2b1-natural-collision-01` | `PARTIAL` | building-age or floor identity | `UNRESOLVED_COLLISION` |
| `phase2b1-natural-collision-02` | `PARTIAL` | building-age or floor identity | `UNRESOLVED_COLLISION` |
| `phase2b1-natural-collision-03` | `PARTIAL` | building-age or floor identity | `UNRESOLVED_COLLISION` |

The unavailable row-level Phase 2B-1 manifest is not reconstructed from row
order or offsets. These cases must be rematerialized at operator runtime with
opaque row references and both before hashes before any future decision.

### Dedupe/ambiguous collisions

The 194-row bucket reconciles as follows:

| Identity shape | Rows | Safety disposition |
| --- | ---: | --- |
| Same official identity | 0 | None ready |
| Natural/exact facts agree without official identity | 191 | Ambiguous probable duplicate |
| Key-only collision | 3 | Unresolved |
| Proven conflicting official transaction | 0 | None established |

The 191/3 split reconciles the prior collision totals against a SELECT-only
natural-fact counterpart count of 57,544. It does not promote any row because
official identity remains absent.

## No-collision cohort

The 51,689 no-collision candidates remain supporting-only. They are the best
future update candidates, but none has complete authoritative lineage and none
has an authoritative or proven-derivable dedupe rebuild. Ready count: 0.

## Dedupe forensics

Git history contains both a legacy official-ID-or-fact hash and the current
geography-sensitive v2 algorithm. Production does not record which algorithm
created a key. It also does not retain the official transaction serial needed
to reconstruct serial-based keys. A SELECT-only reconstruction using persisted
fields and current v2 with an empty serial matched 0 stored keys.

No foreign key references `real_price_transactions` or `dedupe_key`. Import and
repair code use the key for duplicate checks and manifests, so changing it is
still an identity operation. For all 126,087 invalid rows:

* `DEDUPE_REBUILD_AUTHORITATIVE`: 0
* `DEDUPE_REBUILD_DERIVABLE`: 0
* `DEDUPE_LEGACY_UNKNOWN`: 126,087

The stable future apply locator is the primary key `id`, but `id` alone is not
an apply precondition. A future batch must compare `id`, source, current city,
current district, current dedupe key, and a hash of all relevant facts.
Duplicate disposition must additionally revalidate the counterpart ID and
before hash. Any mismatch invalidates the row and fails the batch.

## Batch evidence

The 2026-06-07 population contains 115,113 invalid rows across supporting,
ambiguous, and unresolved outcomes. The 2026-06-08 population contains 10,974
unresolved rows. The leading bad mappings all occur on 2026-06-07, which is a
strong corruption signature, but not proof of one run or artifact: zero
invalid rows exactly join to a run timestamp, and the available run summaries
are multi-file.

Classifications:

* 2026-06-07: `MIXED_BAD_BATCH`
* 2026-06-08: `PARTIAL_LINEAGE_BATCH`
* `AUTHORITATIVE_BAD_IMPORT_BATCH`: none

## Future row

The Taipei City / Nangang District row for `2026-10` has an opaque dedupe key,
but no exact import-run timestamp match, raw note, transaction ID, raw date,
source filename, or artifact. It remains `UNRESOLVED`.

Recommended action: keep it excluded from publishable data and preserve it for
source recovery. Do not delete it. If an immutable artifact later proves the
raw period is also `2026-10`, classify it as
`VALID_SOURCE_FUTURE_SEMANTIC_ANOMALY`; if the raw period differs, classify it
as `PARSE_OR_IMPORT_ERROR`.

## Future repair options

### Option A - update rows in place

Lowest operational complexity, but currently unsafe because artifact lineage
and dedupe reconstruction are missing. It also carries the greatest risk of
turning a plausible geography inference into an irreversible source claim.

### Option B - quarantine bad batch and authoritative re-import

Best lineage and rollback properties if the exact historical artifacts and
hashes are recovered. It preserves bad rows for review and gives new rows an
explicit release/import identity. Currently blocked by artifact absence.

### Option C - remove proven duplicates and update no-collision rows

Potentially smallest data change, but it requires Level A/B duplicate identity
and authoritative dedupe reconstruction. Current provable duplicate count is
zero.

### Option D - rebuild affected scopes from authoritative artifacts

Preferred when a complete historical artifact set is recovered. It avoids
mass guessing and allows scope checksums, but must remain scoped and requires a
reviewed quarantine/lineage schema before production use.

Option B or D is preferable after artifact recovery. Option A is not justified
by the present evidence.

## Scoped manifest and simulation

The committed manifest contains no raw addresses or row IDs. It is bound to:

* snapshot `2026-08-11T15:33:34+08:00`;
* official rows `451,672`;
* invalid rows `126,087`;
* main commit `8511576e2de1e4a17433056f5323793e22b5767d`.

Baseline hash:
`49165c39a934cfce1aed2b3c384905eb91c355cf39d09196402b712f3e9e7086`

Empty manifest SHA-256:
`a13b8740c19215f2590ad44761341910a17d3e34047971fc5f78f1f4345c0a0c`

| Measure | Scoped simulation |
| --- | ---: |
| Baseline transactions | 451,672 |
| Updates | 0 |
| Duplicate removals | 0 |
| Reimports | 0 |
| Projected transactions | 451,672 |
| Projected invalid rows | 126,087 |
| Remaining collisions | 57,547 |
| Future rows remaining | 1 |
| Affected aggregate scopes | 0 |

Any change to the baseline counts, commit, snapshot contract, source row, or
counterpart invalidates a future non-empty manifest. No nationwide aggregate
rebuild is proposed.

## Production gate

`NOT_READY_FOR_ANY_PHASE_2B2`

There is no non-zero cohort with complete authoritative evidence, resolved
collision disposition, stable source identity, and known dedupe handling.
