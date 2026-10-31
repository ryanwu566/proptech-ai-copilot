# Professor Server local integration handoff — 2026-10-29

**Stage 1 Server Data/DB Integration is COMPLETE for the supported local runtime
and explicitly accepted archive-only datasets.** The successful guarded apply
receipt and its SQL, configuration, image, database/security and artifact evidence
were inspected from the readable copy. All remaining Stage 1 host/database gates
pass. Twelve ordinary live API contracts and listener/frontend checks also pass.
Ordinary runtime no longer requires X9. The server is ready to begin Stage 2 local
frontend acceptance; frontend and production acceptance are separate work.

This closure used no sudo or Docker socket access, reran no privileged apply,
changed no implementation and reran no full test suite. The earlier PARTIAL
acceptance in commit `0a4843796d3429169389380db7ee1c447c96aa40` is superseded.

Authoritative operator evidence:
`/var/backups/proptech-selfhost/final-data-integration/apply-20261029T013804Z-MREVbS6x`.
Readable evidence: `/tmp/professor-apply-success-evidence`; successful completion
at `2026-10-29T01:59:43.423007+00:00`. Application/migration hashes, SQL candidate
membership, backup hash and safe evidence hashes were verified without exposing
protected configuration values or copying private artifacts into git.
Sanitized current acceptance is in
[`acceptance.json`](../../reports/professor-final-integration/acceptance.json).

**DO NOT TOUCH `/dev/sda`.** It may contain the professor's existing data.
The reviewed apply checks backing-device metadata and contains no device-write
operations. This acceptance performed no disk/device operation. It does not
constitute an independent disk forensic audit.

## Architecture and server paths

FastAPI is reached through the existing reverse proxy at `127.0.0.1:8080`.
App and valuation are separate databases/roles in the existing `postgres_app`
container; usage uses `postgres_usage`. Both containers use internal Docker
networks with no published PostgreSQL ports. The receipt verifies the new API
image and healthy API/proxy after recreation/restart. The retained PostgreSQL
containers passed post-apply TLS, identity and private-network checks; usage
runtime health passed. This is verified apply evidence, supplemented by current
HTTP checks, rather than a duplicate direct Docker census.
Existing listeners on 80 and 3322 were left untouched. Their presence does not
constitute approved public ingress. Port 8080 is loopback-only; no host 5432
listener was found during final acceptance.

| Purpose | Path / identity |
|---|---|
| Repository / local branch | `/home/andy/proptech-ai-copilot` / `server/final-data-integration-20261028` |
| Compose project | `proptech-selfhost`, `docker-compose.selfhost.yml` |
| Host overrides | `/etc/proptech-selfhost/{datasets,valuation,local-frontend}.override.yml` |
| Protected configuration | `/etc/proptech-selfhost/{compose,runtime}.env` — never print values |
| Credentials / TLS CA | `/run/proptech-selfhost/secrets`, `/run/proptech-selfhost/tls` |
| Runtime data root selected by apply | `/srv/proptech-data/DB` |
| Original source | `/run/media/andy/Crucial X9/DB` — preserve without modification |
| Backups and operator evidence | `/var/backups/proptech-selfhost/final-data-integration/` |
| App database / role | `proptech_app` / `app_runtime` |
| Usage database / role | `proptech_api_usage` / `proptech_usage_runtime_v1` |
| Valuation database / role | `proptech_valuation` / `valuation_runtime` |
| Verified compose services | `postgres_app`, `postgres_usage`, `api`, `reverse_proxy` |
| Applied API image | `proptech-professor-api:apply-20261029t013804z-mrevbs6x` |

Post-apply probes verify TLS 1.3 with certificate verification, SELECT-only RIS
access and SELECT-only valuation access to nine serving/forensic objects.
`valuation_runtime` has no INSERT, UPDATE, DELETE, TRUNCATE, TRIGGER, public-schema
CREATE, superuser, BYPASSRLS, CREATEDB, CREATEROLE or replication privilege.
Usage TLS/least-privilege and runtime health also pass. Database URLs and
credentials must not be copied to this repository.

The new API container is
`ec5f86ee56c661940c5edeecb17fde9fa5610ce3ba494dfb21f7e9c57854ade7`, image ID
`sha256:9d563647cf1ea2788f86be46b54a8420b2fe0bd0c0bbb5c7a2ba0b4d474f353e`.

## Runtime and archive data

The previously completed full copy verification covered 11,511 files /
14,061,730,283 bytes with zero missing, extra, size or SHA256 mismatches.
The final acceptance intentionally does not repeat this multi-GB comparison.
The inventory and per-artifact hashes remain under
`reports/professor-final-integration/`.

| Dataset | State and version / limitation |
|---|---|
| NLSC | Runtime-active from the verified read-only `/srv` bind. SHA256 `1b1db799708e61ee337d1ac6ae0fa359eafd8c28b8cf297d80b0c83cb5a2b03d`, 7,691 features, source vintage ROC-1150817. Live village resolution passes. |
| RIS | Runtime-active. Village `65000050016`, 11507: population 6,134, households 3,834. Freshness remains explicitly stale. Supplied table baseline 100,863 rows. |
| WRA | Runtime-active from the verified read-only processed `/srv` bind. All ten immutable `v1` scenarios pass manifest/hash/feature/spatial checks with zero R2 calls. The live `24h-350mm` SHA256 is `13b0bf6e0029259ead7e6fd4688ac030f5a2f500a171418f59377c50033cf631`. Publication vintage remains unknown. |
| PLVR raw | Preserved forensic/source archive. 8,702 files / 4,156,676,110 bytes in the prior reference inventory. No transaction/source deletion. |
| PLVR database | Committed raw population remains 451,744: 451,672 official and 72 sample rows, zero future official rows. Row 38652 is retained. Exactly 117,986 deterministic serving exclusions are applied; raw/status totals intentionally include them. |
| GSMMA sensitivity | Archive only: 70 raw packages, no established production-schema immutable processed artifact. Explicit-version local transport exists; no versioned artifact is activated. |
| ARDSWC | Archive only: five recorded official ZIP hashes. No reviewed equivalence between copied 115-year layers and the existing `113-public-mvt` semantic/version contract. |
| Liquefaction | Archive/reference only: 35/36 snapshot hashes match; only 18/36 files have entirely valid polygons. No adapter or repair invented. GeologyCloud remains the supported remote contract, guarded. |
| CWA | Archive only: 56 files; both current JSON snapshot hashes validated. No supported production consumer or earthquake-risk conclusion added. |
| Supabase backup | Archive only: 18 files / 155,727,177 bytes inventoried; contents were not printed or restored. |

**DO NOT fill, infer, invent, download or repair the accepted CWA 1897–1989
early instrumental earthquake gap. It is not a blocker.**

WRA scenarios: `6h-150mm`, `6h-250mm`, `6h-350mm`, `12h-200mm`, `12h-300mm`,
`12h-400mm`, `24h-200mm`, `24h-350mm`, `24h-500mm`, `24h-650mm`.

## Local artifact boundary

`WRA_FLOOD_LOCAL_ROOT` explicitly selects local mode. The reviewed apply mounts
only the processed WRA directory and the NLSC artifact read-only from `/srv`.
Missing, corrupt or malformed local artifacts fail closed without R2 fallback.
The verified object-store implementation rejects symlinks and arbitrary paths,
bounds compressed reads and reuses manifest, SHA256, decode and spatial checks.
Live matched and no-match Terrain requests return `storage_backend=local` and
the pinned scenario hash; no-match remains `unknown`, never safe/low.

Both dataset mount sources start with `/srv/proptech-data/DB/`, use
`read_only=true` and prohibit automatic source-path creation. The evidence chain
validates planned overrides against effective Compose before recreation, then
checks the running image and read-only/no-X9 mounts before emitting PASS. It
therefore proves ordinary-runtime X9 independence without another privileged
inspection. X9 was not unmounted or modified by this closure.

GSMMA local mode additionally requires an explicit immutable dataset version;
`latest` is rejected. Do not configure it until production-schema artifacts and
provenance exist. Existing R2 behavior is retained when local mode is absent.
No paid provider E2E was run or provider credentials logged.

## PLVR serving quality and reconciliation

The original related-party transaction remains forensic evidence. Its official
serial `RPWNMLNKNHLGFBF78EA` uniquely reconciles to serving row **38652**, using
all ten normalized facts: geography, period, address, road, building type, area,
total/unit price and reliable floor. Historical `dedupe_key` is not authoritative.
The full offline reference scan covered 880 files / 3,507,266 raw rows:

| Classification | Evidence groups |
|---|---:|
| UNIQUE_MATCH | 117,986 |
| MULTIPLE_MATCH | 59,721 |
| NO_MATCH | 958,681 |

The known serial occurs once, with one fact version, one official identity and
one serving match; no conflicting revision or removed-note evidence exists.
Every unique candidate was checked against the supplied snapshot, independently
recomputed from its raw serving facts. Every non-unique proposed serving ID is
null. Ambiguous revisions, competing IDs, unreliable floors and missing IDs
remain ineligible for automatic exclusion.

Migration 023 adds `market_serving_exclusions` and invoker/barrier views
`market_serving_transactions` and `market_serving_district_periods`. The reason
is `special_note_requires_review`, evidence class `UNIQUE_MATCH`. No raw address
is exposed through exclusion metadata. Original `real_price_transactions`
remain available for forensic/status use.

With `PLVR_SERVING_EXCLUSIONS_ENABLED=true`, Market, segmentation, Valuation,
Trend and Finder use filtered serving relations, without raw fallback if a
required view/grant is missing. The reviewed apply compares every current raw
row with its snapshot under a lock, preserves row 38652, writes additive
exclusions and deterministically reconciles aggregates/coverage/metadata in one
transaction. It does not invoke the protected operator refresh.

Fresh API acceptance no longer reproduces the bad May 2026 result:
新北市/新莊區/2026-05 returns explicit `no_data`, no price/count and
`market_summary_missing`. Other district periods remain covered. 中正路 returns
370 transactions, average 44.71. The now-verified committed SQL receipt proves
raw-row retention and serving exclusion. Complete comparison of its applied
candidate section with classifications proves that only the 117,986 unique
identities were applied; ambiguous/unmatched groups remain unmodified. The
transaction's persisted coverage equality guard passed, with 7,500 active
aggregate groups and 368 canonical coverage entries. Historical inactive
aggregate rows may remain; no serving table was truncated. National coverage
remains partial and source freshness remains aging.

## Startup, shutdown and checks

Use the existing host overrides; the apply updates them and pins the new local
image. Do not reintroduce the old X9 binding or use an older image that ignores
exclusions. Operator commands from the repository:

```bash
sudo docker compose --env-file /etc/proptech-selfhost/compose.env \
  -p proptech-selfhost -f docker-compose.selfhost.yml \
  -f /etc/proptech-selfhost/datasets.override.yml \
  -f /etc/proptech-selfhost/valuation.override.yml \
  -f /etc/proptech-selfhost/local-frontend.override.yml up -d --no-build --pull never
```

Shutdown uses the same prefix with `stop reverse_proxy api`, preserving all
PostgreSQL containers and volumes. Never use `down -v`, remove existing volumes,
DROP databases, TRUNCATE serving tables or delete source transactions. Do not
rerun the privileged apply merely to inspect acceptance.

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/readiness
python3 scripts/ops/professor_local_api_acceptance.py
ss -lntp
```

Keep `market_ops` and paid operations disabled. Verified installed overrides and
the successful effective-Compose/recreation guards prove
`ANTI_ABUSE_MARKET_OPS_DISABLED=true`, Earth Engine disabled and disabled
geocoding/places/routes/satellite/location/parcel/ARDSWC/liquefaction/NLSC-gateway/
TGOS operations. Local village artifact resolution is independent of the disabled
NLSC gateway. The final acceptance invoked no operator route or paid provider.

## Backup and rollback

The successful operator apply contains a private `valuation-before.dump`,
its SHA256/TOC verification, `etc-before/`, `compose-command.json`, image IDs,
configuration hashes, security evidence, reconciliation and `ROLLBACK.md`.
The 34,822,110-byte backup matches its verified SHA256
`ea91d564b345e9efdc75c2b9060a8fe435a1b3d29078d504e35080ef01460dfe`;
the TOC verification receipt passes. All 49 supplied evidence files were
inventoried; protected configuration values were not decoded. Never commit
backups, raw serving exports, SQL containing private records or secrets.
Use the existing `scripts/ops/selfhost-backup.sh` workflow for ongoing backups;
rehearse restoration into separate disposable targets before any real restore.

Keep the additive exclusion evidence and raw data. If a commit is successful or
uncertain, do not restore an old unfiltered image. Keep the API/proxy stopped
while performing a separately reviewed repair. The archive is not an automatic
overwrite instruction. All configuration recovery must preserve permissions,
private networks and TLS. Exact run-specific recovery instructions are in the
operator evidence directory's `ROLLBACK.md`.

## Final verification and next phase

The updated `acceptance.json` records the successful apply receipt, safe evidence
hashes, 17 verified application/migration hashes, complete SQL/classification
membership checks, TLS/privilege proof, applied mounts/flags, and twelve fresh
ordinary loopback contracts. The SQL hash is
`af9e67ff48c52d1e1516274b245a8352d150a303d10e69d926ced0994f04cd49`.
No private evidence files were copied into git. Earlier supporting evidence is
retained with its original observation time:

- `api-acceptance.json`: 11 loopback observations, including NLSC → RIS.
- `final-live-api-acceptance.json`: nine strict business/WRA/health contracts pass.
- `final-local-security-checks.json`: listener boundaries, frontend preservation
  and no device-write operations during acceptance.
- `failed-apply-diagnosis.json`: full conservative offline reconciliation,
  independently verified candidate hashes and prior repair test evidence.

The earlier full suite passed 4,260 tests / 149 skipped; the repair-focused run
passed 131 tests. These are historical validation, not tests rerun during final
acceptance. The privileged apply and full test suite were not rerun. The
pre-existing `frontend_next/next-env.d.ts` change remains untouched and excluded
from the final commit (SHA256
`0f70629890b72a0a82e91972cc032c04b658b26c265373cb711cf576bfbf8fcc`).

There are no remaining Stage 1 host/database gates. The earlier evidence-access
block is closed; entries describing that block in historical probe files are
superseded by this receipt review. Ordinary runtime no longer needs X9 connected;
no source modification, unmount or disconnect was performed. Stage 2 local
frontend acceptance can begin, including the intentionally limited/unknown
provider and freshness states. Browser/user-flow acceptance remains unperformed.

GSMMA, ARDSWC and liquefaction local-provider activation remains blocked by the
documented artifact, semantic/version and integrity limitations. Their archive
preservation and explicit unavailable runtime states satisfy the accepted Stage 1
scope; optional activation belongs to later work and must not produce fabricated
risk conclusions. CWA is archive-only by
contract, with its accepted historical gap intact. Public ingress, authentication
and abuse boundaries, backup/restore rehearsal and frontend acceptance require
separate next-phase review before public hosting. DNS, Vercel, Cloud Run, Render
and GitHub remote were not changed; no push, tunnel or production deployment
occurred. This handoff makes no production-readiness claim.
