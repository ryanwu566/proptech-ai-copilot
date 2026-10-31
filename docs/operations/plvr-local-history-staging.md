# PLVR historical staging for the Stage 3 session

**Dataset preparation: PASS.** The independent full verifier passed for
**1,321,059 clean transactions** from 3,507,266 sale-main occurrences. The retained
release labels are 105S4–115S3 (2016 Q4–2026 Q3); observed clean transaction dates
are 2011-01-08 through 2026-09-03. Older sparse late-filed observations and the
thin 2026-09 tail do not establish complete historical coverage. The descriptive
≥100 rows/month span 2013-03–2026-08 must not be called authoritative coverage.

Artifact fingerprint:
`bccf2ec1bc19110b9f55e35c3eaec284c2ad57a97318acea7381c5be5002ccee`.
Compressed JSONL is 594,216,027 bytes; the full artifact including the lineage
ledger is 8,343,623,179 bytes. The build used one low-priority worker and peaked at
168,591,360 bytes of RSS. No privileged setup is required for this user to consume it.

There are 3,507,231 candidate families, 2,186,172 primary family exclusions,
3 unidentified occurrences, 1 repeated appearance and 31 additional reported versions
across 31 conflicting families. All 31 conflicting families are quarantined; 9 have
primary revision reasons and 22 have note-priority reasons. The known related-party
serial matches the accepted strong-fact baseline for serving row 38652 and has
one raw occurrence, zero clean occurrences. No serving database was accessed.

The artifact contains 21 cities/counties, 330 reported geography pairs (including
two explicit city-level groups), and 12 building types. City spellings follow
production storage; normalize them with the existing registry for an approved
model encoder. City-level records have an empty district: do not infer a district,
coordinates or extra coverage. Training authorization remains false.

This task builds data only, in the isolated worktree
`/home/andy/.codex/worktrees/cb5c/proptech-ai-copilot`, branch
`data/plvr-history-ml-20261029`, based on Stage 2 commit
`ff3b1df23ccc91d628911491b8ee2f5133c0e7cf`. It does not change the main checkout,
Stage 1/2 commits, frontend, serving tables, containers or providers. No model
has been trained and nothing is pushed.

The completed artifact path and exact counts are recorded in
`reports/plvr-local-history/acceptance.json`. Only a fingerprint directory with
`COMPLETE.json` and a successful independent `verify` result is consumable.
Ignore `.building-*` scratch directories.

## Source and coverage

The intended server source is `/srv/proptech-data/DB/實價登錄 PLVR`. The root-owned
parent prevents this user from traversing it. This build instead reads the
original, previously byte-verified X9 mirror at
`/run/media/andy/Crucial X9/DB/實價登錄 PLVR`, mounted on `/dev/sdb2`. That actual
root is recorded in provenance. Source files are opened read-only with no-follow
and no-atime flags; no extraction, renaming, removal, formatting or raw-data
transformation occurs. No data is downloaded. `/dev/sda` is not used.

Forty consecutive release labels run from `105S4` through `115S3`. Every ZIP is
hashed against `00_manifest/plvr_10y_40q_manifest.csv`. Every retained member is
CRC/decode checked, hashed and compared with its extracted copy. Presale, rent,
detail and schema bytes are inventoried, not counted as additional sale-main
transactions. All 880 sale-main A files are parsed with strict schemas, actual
English descriptor labels and exact logical/physical row locators.

The complete raw valid-calendar range, clean effective-date range, monthly
counts and longest contiguous block with at least 100 clean rows per month are
reported separately. The density rule is an explicit descriptive recommendation;
it does not establish complete historical coverage or publication availability.
Release labels, transaction dates and filesystem mtimes are not publication times.

## Canonical identity and exclusions

An official serial in the `moi-plvr-sale-a` namespace defines a candidate family.
The canonical ID is SHA-256 of `moi-plvr-sale-a|<serial>`. Full source-row hashes
and normalized semantic hashes retain every appearance/version. The raw-row
hash covers canonical JSON of unmodified parsed CSV fields, not the physical CSV
line encoding; exact file hashes and physical line locators preserve byte provenance. Independent
unrounded city/district/date/address/building/floor/area/price facts guard linkage.
Known single-floor representations and width/whitespace variants are normalized;
unknown floors remain explicit. No historical dedupe_key is used as identity.

Repeated versions create provenance occurrences, not new transactions. Conflicting
versions are quarantined; a later quarter does not prove a revision should win.
Missing/demo/invalid serials are excluded. All nonblank notes taint the serial and
its matching fact family, including unidentified noted rows and note removal in
another release. Different IDs sharing the same strong facts remain ambiguous.
The known related-party serial `RPWNMLNKNHLGFBF78EA` is always excluded; the
production serving row 38652 is never read, updated or removed by this pipeline.

Existing production geography, building, month and price normalization is the
minimum gate. Staging additionally checks valid exact days through the pinned
as-of date, finite positive arithmetic and the source contract. Invalid/future
rows remain in the forensic ledger with reason codes. Features omit legacy
current-year building ages; age is computed at transaction time, and future or
unknown completion evidence produces null.

No full raw addresses or note text are copied into staging. Authorized source
inspection is possible through release/member/hash/record/physical-line locators.

## Artifact files

- `transactions.jsonl.gz`: deterministic gzip, UTF-8 canonical JSON, one clean
  family per row, sorted by canonical ID. Stream it; do not load the whole file
  into this server's RAM.
- `lineage.sqlite`: dedicated read-only ML ledger, never a serving database.
  `occurrences` preserves all sale rows; `versions` preserves distinct reported
  semantics; `dispositions` explains every candidate-family decision;
  `clean_transactions` exposes selected features and representative lineage.
  `source_files`, `identity_stats` and `fact_stats` retain verification support.
- `schema.json`: complete record JSON Schema, units, nullable fields and semantic
  limitations. Decimal amounts/areas are strings to preserve precision.
- `provenance-manifest.json`: all release/member hashes, actual source root and
  exact transform/dependency-source hashes.
- `coverage.json`: clean geography, building-type and monthly counts.
- `summary.json`: counts, date windows, exclusions, checksums, resource usage and
  fingerprint. Physical occurrences, distinct versions and unique identities are
  separate accounting units. `revision_versions_quarantined` counts additional
  distinct versions beyond one per family; all conflicting families are excluded,
  including their first version.
- `COMPLETE.json`: summary hash and dataset fingerprint. Published paths are new
  fingerprint directories; files are 0440 and directories 0550.

The dataset hash covers canonical rows, source releases, as-of day and pinned
transform-source hashes. The logical JSONL and gzip hashes are separately
recorded. Source/output roots do not change the data hash. Different root paths
may change provenance-file and summary bytes without changing the dataset.

## Stage 3 consumption

Use the exact completed artifact directory from the acceptance report. Verify it
first from this isolated worktree; no checkout/merge in the other session is needed:

```bash
python3 -B /home/andy/.codex/worktrees/cb5c/proptech-ai-copilot/scripts/ml/prepare_historical_transactions.py verify --artifact /home/andy/proptech-ml-data/plvr-history/bccf2ec1bc19110b9f55e35c3eaec284c2ad57a97318acea7381c5be5002ccee
```

For streaming input, open `transactions.jsonl.gz` with Python `gzip.open(path,
'rt',encoding='utf-8')`, decode one JSON object per line and batch at most 10,000
rows. For SQL, open `lineage.sqlite` with `mode=ro&immutable=1`, and set
`PRAGMA query_only=ON`. Query `clean_transactions`; `features_json` holds the
same feature fields as the compressed artifact. Join the representative occurrence
to `occurrences` and `source_files` when source/version evidence is needed.
Pin the dataset fingerprint, schema and source-code hashes in any subsequent
Stage 3 experiment configuration.

This is clean canonical staging of historical transaction records, not an
approved point-in-time cohort. Every row retains `training_authorized=false`,
`historical_publication_proven=false` and a null `source_release_available_at`.
The existing strict ML temporal, revision-history, target and training gates are
unchanged. Publication/cancellation/replacement history must be independently
established before claiming leakage-safe historical evaluation.

`gross_unit_price_ntd_ping` is reported gross consideration divided by registered
transferred building area. Parking and dwelling rights are unverified; it must
not be relabeled as a verified no-parking whole-dwelling target. Stage 3 must
select/admit its target/cohort under its existing contracts. No train/validation/
test splits or model are manufactured here.

## Rebuild and optional protected-copy comparison

A normal rebuild uses an unused output parent on the internal disk, the pinned
as-of day and this exact source checkout. The CLI defaults to the protected
server copy; an operator can first provide ordinary read access if desired.
This build used the explicit read-only X9 fallback:

```bash
ionice -c3 python3 -B /home/andy/.codex/worktrees/cb5c/proptech-ai-copilot/scripts/ml/prepare_historical_transactions.py build --source-root '/run/media/andy/Crucial X9/DB/實價登錄 PLVR' --output-parent /home/andy/proptech-ml-data/plvr-history-rebuild --as-of 2026-10-29
```

The worker uses nice 15, one process, a 32 MiB SQLite cache, file-backed temporary
storage inside its new staging directory and disk-reserve checks. The output
must use the reviewed internal ML path and the same backing filesystem as
`/home/andy`; the whole X9 mount, serving-data root, main checkout and device
paths are forbidden output targets.

No privileged setup is needed to read the completed artifact. One optional
operator-only command can independently compare every staged source hash with
the protected `/srv` copy without rebuilding, writing source data, changing
permissions or touching databases:

```bash
sudo python3 -B /home/andy/.codex/worktrees/cb5c/proptech-ai-copilot/scripts/ml/prepare_historical_transactions.py verify-source --artifact /home/andy/proptech-ml-data/plvr-history/bccf2ec1bc19110b9f55e35c3eaec284c2ad57a97318acea7381c5be5002ccee --source-root '/srv/proptech-data/DB/實價登錄 PLVR'
```

That optional command is not executed by this session. The artifact itself has
no X9 dependency after completion. Neither consumption nor verification needs a
production DB URL, provider credential, container recreation or public ingress.
