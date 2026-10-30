# Professor Server privileged apply — operator runbook

This is the dry-run description of the **real apply path**, not a preflight stub.
The agent has **not executed** the script, any embedded apply program, or sudo.
Validation is Bash syntax, Python AST inspection, static safety checks and an
independent static review. Successful static validation is not a live acceptance
claim. The script performs its live gates and writes a PASS/FAILED receipt when
an operator runs it.

## Operator command

From this exact prepared checkout:

```bash
sudo bash /home/andy/proptech-ai-copilot/scripts/ops/professor_server_privileged_apply.sh
```

The script requires root, takes an exclusive lock and forces Docker to the local
`unix:///var/run/docker.sock`; it does not use a remote Docker context. No
password is requested or echoed by the script. Do not add `bash -x`, redirect
secret files to the terminal, edit the checkout/configuration during the run, or
run PLVR import jobs concurrently. Preparation can take tens of minutes on this
server: raw releases are reconciled on disk, not treated as 1.1M serving rows.
SQLite spill files use a private mode-0700 `sqlite-temp/` directory in the new
evidence directory via explicit `SQLITE_TMPDIR`/`TMPDIR`; the container root stays
read-only. This is disk-backed scratch, not a larger RAM allowance. Classification
uses explicit indexed summary tables to avoid an identities-by-facts Cartesian
plan at nationwide cardinality. Match and ambiguity requirements are unchanged.
The API/proxy maintenance window starts only after backups, artifact validation,
image preparation, reconciliation and a merged Compose preview have passed.

## Live prerequisites and fail-closed gates

- Existing project `proptech-selfhost`, one running `api` and `reverse_proxy`, API
  UID/GID `10001:10001`, expected repository working directory and reviewed Compose
  files: `docker-compose.selfhost.yml`, `datasets.override.yml`,
  `valuation.override.yml`, and optionally `local-frontend.override.yml`.
- Existing databases `proptech_app`, `proptech_api_usage`, `proptech_valuation`
  must each resolve to exactly one discovered local PostgreSQL container. Runtime
  TLS server addresses must match those containers before any database backup or
  change. Administrative connections use each container's local Unix socket.
- PostgreSQL 15+ for invoker-security views. No database container may publish
  ports, use host networking, or attach to a noninternal Docker network. No host
  PostgreSQL 5432 listener; port 8080 must be bound only to loopback.
- Read-only mount metadata guards run before lock/evidence writes. They also
  check Docker storage, containerd storage when present, and PostgreSQL writable
  mount sources before Docker image/database mutations. Any `/dev/sda` backing
  path causes refusal; the script never opens, mounts or modifies that device.
- At least 5 GiB free space; existing role identities/least privilege and
  verify-full TLS checks must pass. The baseline serving population must remain
  451,744 total / 451,672 official / 72 nonofficial, zero future official rows,
  with official source row 38652 still present.
- `/srv/proptech-data/DB` supplies every dataset read. NLSC must match
  `1b1db799708e61ee337d1ac6ae0fa359eafd8c28b8cf297d80b0c83cb5a2b03d` and
  decode to 7,691 features. All ten WRA scenarios must pass the existing runtime
  manifest/schema/hash/count validators and match the prior reference hashes.
  A matched point and a distinct no-match point are checked with an R2 factory
  that raises if called. Runtime UID access is checked before maintenance.
- The prepared modules, migration, administrative-area registry and reference
  evidence must exist in this checkout. The image contains the exact audited
  patch bytes over the existing local API image. Staged application directories
  are explicitly 0755 and code files 0644 while evidence/context parents remain
  private. A network-disabled, read-only, UID0/cap-drop-ALL `--help` probe must
  succeed before reconciliation; no capability is added. No dependency install or image
  pull occurs. Existing baseline build identity is not presented as a new Git
  release; the report records image IDs and per-file SHA256 instead.
- All 880 raw sale CSVs and every current serving row are reconciled by the tested
  helper. Repeated releases collapse into identity/fact groups. Multiple serving
  matches, multiple IDs sharing facts, revisions, removed notes, rejected source
  revisions, missing IDs and unsupported/lossy floor tokens cannot authorize an
  automatic exclusion. The known serial must uniquely map to 38652. Raw file
  hashes are rechecked after the scan; current database rows are checked again
  under a transaction lock. Any mismatch stops application.

These are real preconditions, not an unconditional blocker. When they pass, the
script proceeds to apply. If the server differs from the reviewed baseline, it
refuses rather than inventing credentials, schemas, provenance or successful data.

## Exactly what the script changes

1. **Private evidence and backups:** creates a unique root-private directory under
   `/var/backups/proptech-selfhost/final-data-integration/apply-<UTC>-<random>/`.
   It retains original `/etc/proptech-selfhost` Compose/env/override files before
   modifying any of them, a full valuation custom-format dump with SHA256 and
   verified TOC, a private complete serving snapshot, hashes, classification
   ledger/index, prepared SQL, image context, receipts and rollback instructions.
   Backups can contain secrets/private records and must remain out of Git.
2. **Local image tags:** retains a tag for the existing API image and builds a
   uniquely tagged local API image with the prepared local-artifact and PLVR
   serving changes. It copies only an explicit allowlist of application files;
   no dataset archive, `.env`, secret, frontend build or multi-GB source copy is
   added. A small generated startup wrapper loads the existing valuation secret
   and forces verify-full TLS using the existing mounted CA, without printing it.
3. **Additive valuation database changes, one transaction:** applies migration
   `023_add_market_serving_exclusions.sql`, creates the exclusion table and two
   invoker-security serving views, and inserts only deterministic `UNIQUE_MATCH`
   exclusions with reason `special_note_requires_review` and evidence provenance.
   Pre-existing exclusions with conflicting facts/IDs or without an identical current `UNIQUE_MATCH` candidate cause rollback; identical reruns are permitted. Only SELECT is granted on
   the new objects to `valuation_runtime`. Row 38652 remains byte-for-byte in the
   original table and is absent from the serving view; full snapshot equality
   checks run both before and after the database changes.
4. **Deterministic Market metadata:** recomputes eligible district-period groups
   from the filtered view and canonical registry up to the explicit run month.
   It upserts aggregates, marks obsolete groups unavailable with null prices and
   zero counts, updates existing coverage counts/source dates, and upserts `v1`
   read-model metadata. Zero coverage becomes `coverage_unknown`; coverage stays
   partial. A final comparison proves persisted coverage matches filtered source
   counts. It never invokes the protected refresh endpoint or enables market_ops.
5. **Persistent existing `/etc` overrides:** merges the API additions into
   `datasets.override.yml` and, when different, the last active operator override.
   Unrelated declarations, environment keys, secrets, CA mounts, networks and CORS
   are preserved. NLSC's old target is rebound from the verified server copy and
   only the processed WRA directory is added, both read-only with
   `create_host_path: false`. The new image, startup wrapper, explicit exclusion
   selection and WRA local root are persisted in the normal Compose file list.
6. **Provider switches:** enables local Terrain and the existing database-backed
   Valuation/Trend/Finder/Market operations. It keeps market_ops, Google/paid
   providers, satellite, ARDSWC, liquefaction and remote NLSC operations disabled.
   GSMMA is explicitly selected into local-only unavailable behavior because its
   processed artifact is absent; this is not a fabricated dataset/version or an
   R2 fallback. The CWA archive and accepted 1897–1989 gap are untouched.
7. **Runtime:** stops only the existing API and reverse proxy for the transition,
   recreates **only `api`** with `--no-deps --no-build --pull never`, then restarts
   the same reverse proxy so nginx resolves the replacement API. It verifies
   identities/TLS/mounts before restoring proxy traffic. No database container is
   recreated; no volume is removed; no image is pushed.

Existing database credentials, role passwords, original transaction rows, X9
source files, frontend files (including `frontend_next/next-env.d.ts`), Git state,
DNS, Vercel, Cloud Run and public ingress configuration are not modified.

## Post-apply acceptance and failure behavior

The script verifies API/proxy health, usage-store read-only health, app RIS SELECT
and no write privileges, valuation SELECT-only privileges, nonsuperuser/no bypass
RLS/no role/database creation, actual verify-full TLS connections and private
container/server identity. It checks NLSC→RIS at 榮和里 (`65000050016`, population
6,134 / households 3,834), raw versus serving counts, Valuation, Trend, Finder,
Market road behavior, the exact filtered database aggregate for 2026-05 and real
Terrain WRA matched/no-match provenance. An unavailable provider/query failure
cannot pass as successful filtering. A specifically justified valuation
insufficient-comparables response may remain explicit without inventing a price.
It also rechecks loopback-only 8080, internal PostgreSQL, read-only mounts and zero
active API binds referencing X9. Data freshness remains whatever the source
supports; the script does not label aging data fresh or no-match safe.

`apply-report.json` is checkpointed through the run. The safe child JSON is also
saved as `reconciliation-result.json` before checking its exit status, including
allowlisted invariant/SQLite codes on failure. No exception text, SQL payload,
credentials or raw transaction values are copied into that diagnostic. Final `acceptance.json`,
`api-acceptance.json`, security evidence and `ROLLBACK.md` are private artifacts
in the unique backup directory; its path is printed. The script returns zero
only after all required live gates pass, otherwise nonzero with a FAILED report.
No production-readiness claim is made.

On failure after maintenance begins, the script rediscovers the current
project/service API and proxy containers, stops them, and verifies they are
stopped. It does not falsely claim cleanup succeeded if Docker fails. An API
whose database commit is successful or uncertain remains behind a stopped proxy;
an older image that ignores exclusions is never silently restored.

Rollback guidance is written before maintenance, with exact original Compose
arguments/image identity and original configuration backups. If no database
apply was attempted, the operator can restore original files and start the old
API/proxy. After a successful/uncertain commit, keep maintenance in place and
repair/reapply the exclusion-aware image; do not serve the old unfiltered code.
The full database archive is for a separately reviewed restoration rehearsal,
not an automatic destructive overwrite. Additive exclusion evidence is retained.

## Static validation performed

- `bash -n scripts/ops/professor_server_privileged_apply.sh`.
- Python AST parsing of the outer embedded orchestrator and all three embedded
  programs (startup wrapper, TLS/privilege probe, local-artifact verifier).
- Static checks for forbidden destructive commands/source writes, local Docker
  targeting, read-only dataset binds, guarded API-only recreation, disabled
  market_ops/paid operations, current-row comparison, known-row retention,
  rollback/report paths and pre-mutation Compose/configuration validation.
- Independent static review; no privileged apply, embedded program, Docker action,
  database action or sudo command was executed to validate this script.


## Failed-run diagnosis and repaired launch invariant

The seven supplied artifacts in `/tmp/professor-apply-failure-evidence` were read.
The original run `apply-20261029T004605Z-vAY9viAw` records `command_failed_2`,
not a matching-gate rejection: database apply/commit, maintenance stop,
configuration write and runtime replacement are all false. Its population was
451,744 total / 451,672 official / 72 samples, with zero future official rows.
The backup receipt verified its archive and TOC; runtime TLS/privilege probes
passed. No rollback or database mutation was needed for that failed attempt.

The launch invariant was inconsistent: `umask 077` created staged directories
0700, `COPY --chown=10001:10001` assigned them to the runtime owner, but the offline
job launched as UID0 with **all** capabilities dropped. UID0 cannot traverse
another UID's 0700 directories without DAC override. Python therefore cannot
open the reconciler, producing exit 2 before its exception handler/matching code.
A disposable permission fixture reproduces that startup failure. Historical
stderr was discarded, so the literal original errno message was not recovered;
the launch defect is reconstructed from the deterministic code/ownership policy
and the observed exit. Parser arguments are unchanged and valid.

The repaired staging component makes only nonsecret application directories
0755 and code files 0644; the private evidence and image-context parents stay
0700. An identical-UID/capability launch preflight now catches any future problem
before scanning. Filesystem read-only policy and dropped capabilities remain.

SQLite missing-temp-space errors follow the reconciler's caught exception path
(exit **1**); its old quadratic plan would stall/time out, not explain the
recorded launcher exit **2**. Both were independently reproduced and fixed as
additional defects: explicit private disk scratch and indexed summary joins.
They must not be presented as the proven immediate cause of this failed run.

The supplied serving snapshot SHA256 is
`8d673a1f0eec2f2055880df8ac1ebb52dfb659717c9dc603a9e3ebde4952dafe`.
The ten strong facts of official serial `RPWNMLNKNHLGFBF78EA` and row 38652 are
identical; both hash to
`4b3787fe56703bd6a2d1d422b4ac3ae86d7568840a4b053fefd557925e7a9c4d`.
Only row 38652 in all 451,672 official serving rows has this fingerprint. The raw
serial occurs once across all 880 source-reference files, with the related-party
note and reliable second-floor value. Historical dedupe keys were not used.
Full read-only reclassification against this snapshot completed with exit 0 over
all 880 reference files / 3,507,266 rows: 117,986 UNIQUE_MATCH groups, 59,721
MULTIPLE_MATCH groups and 958,681 NO_MATCH groups. The known serial has exactly
one occurrence, one fact version, one official identity and one serving match,
with no removed-note or blocked-revision evidence. Every non-unique group has
a null proposed serving identity; none is an exclusion candidate. Every unique
candidate was also checked against the private serving index. Matching rules
were not loosened.

The offline scan read the previously verified original reference source without
modifying it. Operator retry uses `/srv/proptech-data/DB` and must still verify
fresh server-copy artifacts and a new serving snapshot against every original
gate and locked equality check. Sanitized findings and evidence hashes are in
[failed-apply-diagnosis.json](../../reports/professor-final-integration/failed-apply-diagnosis.json).
The live exclusion itself remains pending operator execution.
