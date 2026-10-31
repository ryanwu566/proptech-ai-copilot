# Professor Server Stage 2 controlled activation — completed record

**Stage 2 is COMPLETE for the current local profile. Do not rerun activation or
secret installation.** The operator completed run `20261029T114148Z-b7ae118d6efa`
with exit 0. This document retains the reviewed historical plan, prepared against
commit `d8a93492eb900550ce490990fade7726766b18da`. The agent did not execute the
runner or access credential values. No new credential is needed for this profile.

Historical operator command that completed successfully (do not rerun):

```bash
sudo python3 -B /home/andy/proptech-ai-copilot/scripts/ops/professor_stage2_activation.py --apply
```

The runner first validates the actual merged model and prints `change-plan.json`,
including the four current container IDs, existing database volume identities,
target image name, exact secret lists, and rollback path. It then requires typing
`ACTIVATE` in that terminal. No image pull/build or container action precedes that
confirmation. No password or credential is an argument. Default `--plan` stops
before that confirmation/build/apply; it creates only private sanitized evidence
and a root-owned coordination lock, not service/configuration changes.

## Exact changes after confirmation

1. Take SELECT-only TLS/security/data/coverage snapshots and twelve focused API
   checks. Back up the five existing `/etc` configuration files (three overrides
   plus `compose.env`/`runtime.env`; the source compose is hashed separately).
   Actual saved files are listed in `etc-before/`; no credential files are copied.
2. Freeze installed package **names/versions**, not URLs/environment, from the
   working API. Pull official `python:3.12-slim` using an empty Docker client
   config, pin its repository digest, download the exact binary wheels from
   public PyPI in a separate transient container, and hash them. No application
   provider or private registry credential is supplied. Failure stops here.
3. Construct a fresh context exclusively from committed public runtime files in
   `d8a93492…`. No working-tree `.env`, credentials, `.git`, frontend application,
   tests or host dataset is copied. Install the frozen wheels offline, build a
   clean backend, and apply the committed `infra/selfhost/Dockerfile`. The old
   application image is **not** a base layer. Images have unique local run tags.
4. Stream every candidate image layer, including historical/deleted file contents,
   through a credential scanner. Scan full image config/history, generated public
   context, compose models, build output and relevant logs. Raw output/exports
   are never saved or echoed. Scans cover known installed values/password and
   encoding variants plus credential/private-key signatures; arbitrary unknown
   encodings are not a claimed guarantee.
5. In isolated, read-only, non-root containers with `--network none`, validate the
   five actual staged credential files without returning them; compare package
   versions, run `pip check`, import the app, and verify NLSC and all ten WRA
   artifacts, hashes and hit/no-match contracts. Recheck staged identities,
   persistent equality, original config hashes, source/frontend hash and all
   current container IDs before maintenance.
6. Stop the existing proxy and API. Exclusively add one root-owned nonsecret file:
   `/etc/proptech-selfhost/stage2-secrets.override.yml`. It pins the new local API
   image and public build identity; it is appended **last** to the original four
   compose files. Existing `/etc` configs are unchanged.
7. Recreate exactly `postgres_app`, then `postgres_usage`, then `api`, each with:
   `up -d --no-deps --no-build --pull never --force-recreate SERVICE`.
   Each PG service must already have a populated named volume and pass health.
   Exact physical volume name/source/mount identity is checked before and after.
   PostgreSQL retains its immutable image, TLS config, data, roles, private network
   and commands. It receives only its existing `*_admin_password` file; initializer
   role-password files remain protected on the host. API receives exactly its five
   runtime files; no admin/provider/browser secret or legacy alias is permitted.
8. With the proxy still stopped, verify live inodes/ownership/0440 modes, read-only
   mounts, credentials/config guards, TLS and privileges, row 38652 retained and
   excluded, unchanged population/UNIQUE exclusions, and deterministic persisted
   coverage. Run direct API acceptance. Restart the **same proxy container**,
   then run the twelve checks through `127.0.0.1:8080`. Verify no host5432 listener,
   only loopback8080, healthy services, market_ops/paid providers still disabled.
9. Leave the three rebuilt service containers plus the original proxy running only
   after all gates pass. Remove only labelled probe/download containers and the
   generated public build context. Keep both old images, all database volumes,
   staged/persistent credentials, TLS, datasets and rollback records.

## Rollback and evidence

Private evidence:
`/var/backups/proptech-selfhost/stage2-activation/<timestamp-id>/` (root0700).
Before maintenance, `rollback.json`, `ROLLBACK.md`, `compose-before.json`,
configuration hashes and `etc-before/` record the recovery inputs. A failure or
interrupt during maintenance triggers a bounded rollback: stop proxy/API, remove
only this run's unchanged additive override, recreate the original three services
from the original four-file model and verified old image identities against the
same volumes, verify database/filter/API contracts, then start the proxy last.
If rollback fails, leave API/proxy stopped and report FAILED; never invent success
or restore/overwrite databases. A pre-maintenance failure leaves services alone.

Only sanitized allowlisted receipts are published to an exclusive root-owned
`/tmp/professor-stage2-activation-<random>/` path for final acceptance. The runner
prints that path. No raw dotenv/secret/config environment dump should be pasted
into chat. Optional provider credentials stay stored and inactive.

Never touch `/dev/sda`, the X9 source, database source rows or volumes. No public
ports, cloud/remote/DNS changes, push, new feature activation, credential rotation,
Stage 1 reapply or full test suite is part of this procedure. Preserve
`frontend_next/next-env.d.ts` byte-for-byte. The controlled PostgreSQL restarts
cause a short local maintenance window; data loss is not an authorized operation.

## Completed operator activation

This plan was executed successfully by the operator in run
`20261029T114148Z-b7ae118d6efa` with exit0. Stage2final acceptance is PASS for
the current local profile. Do not rerun the activation or installation scripts.
The active profile is the fifth `/etc/proptech-selfhost/stage2-secrets.override.yml`
file; ordinary operations must use the five-file prefix in the current secrets
runbook. The operator script is retained as the reviewed one-time activation
record; its source/host preconditions deliberately refuse an already-applied host.

Current status and sanitized evidence are in
`reports/professor-stage2-secrets/acceptance.json` and
`reports/professor-stage2-secrets/final-activation-evidence.json`.
Earlier refused attempts and repairs remain historical reports. No rollback,
provider activation, secret reinstallation or image rebuild is required now.
