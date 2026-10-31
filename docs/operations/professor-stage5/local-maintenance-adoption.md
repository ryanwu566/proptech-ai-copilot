# Local maintenance adoption — no jobs activated

All three legacy workflows remain unchanged externally for now (C). Their
self-hosted target is a local controlled implementation (A) if the capability is
retained. None is assumed unused or silently retired. The proposed service names
below reserve design identities only; no unit, role, directory or timer exists
because of this task. Existing manual dispatch cadence is preserved.

## Commute snapshot

Source: `services/commute_service.py`, `services/tdx_mrt_client.py` and
`.github/workflows/refresh-commute-snapshot.yml`.

`refresh_commute_snapshot()` assigns an API-process global `_snapshot`. Running
that function in a separate one-shot process updates that process's memory and
does **not** refresh the API worker. Copying the HTTP job into cron would not
produce a faithful local replacement.

Proposed `proptech-commute-snapshot.service` therefore needs a separately reviewed
bounded TDX producer plus immutable/versioned snapshot storage and an API
loader/reload contract. Proposed derived root:`/srv/proptech-runtime/commute`, not
the verified `/srv/proptech-data/DB` archive or X9. Before creation verify its
backing storage and refuse/dev/sda. Preserve source timestamps, schema/provenance,
checksums, bounded counts and explicit stale/unavailable states. A saved file or
successful fetch must not imply fresh/covered data. The adapter and persistence
acceptance are not implemented or claimed by this planning change.

TDX_CLIENT_ID and TDX_CLIENT_SECRET belong to an admitted producer identity,
using Stage2 protected storage and separate minimal read-only worker mounts.
Do not mount them into the six-file API profile. No new paid Routes/Places call,
provider admission or periodic timer follows from the TDX mapping. The API
capabilities to preserve are `/commute/status` and `/commute/nearest`; other
optional commute/route capabilities retain their own disabled/admission policy.

## Market read model

Source: `services/plvr_market_aggregate_service.py`,
`backend/api/routes_market.py` and
`.github/workflows/refresh-market-read-model.yml`.

The legacy refresh deletes/replaces derived aggregate and metadata rows and may
initialize schema. It is not an approved unattended Professor job. The existing
valuation_runtime credential is SELECT-only and must remain so. Never add writes
to a serving role, mount administrator credentials into API/job consumers or run
the protected refresh blindly.

Proposed `proptech-market-reconcile.service` requires a reviewed bounded local
operation with a distinct minimal operations principal and a new explicit
file-only credential contract. That role/file contract is not provisioned; no
unsupported environment name is invented for the Stage2 installer. Allow only
necessary reads of reviewed serving views and narrowly scoped writes to derived
Market tables. Do not grant raw transaction deletion, TRUNCATE, DROP, ownership,
superuser or bypass-RLS privileges. Keep API market_ops disabled.

Use deterministic reconciliation and transaction/advisory-lock boundaries,
conservative CPU/memory/time limits, sanitized result counters and a protected
backup/rollback. Preserve raw row38652, its serving exclusion, duplicate/revision
ambiguity protection, demo/future-official distinctions and actual partial
coverage. Future import/update authorization is a separate operation; this job
does not download or insert a new historical archive into serving.

## Coverage reconciliation and audit

Source: `.github/workflows/reconcile-market-coverage.yml` and existing coverage
repository/SQL contracts. Target:`proptech-coverage-audit.service`, manual only.
Read-only audit can use the existing read capability; any reconciliation writes
require the separately reviewed operations principal above. Results must compare
eligible serving counts, timestamps and persisted coverage after quality
exclusions. Zero/unknown coverage stays explicit, never nationwide-complete.

The Professor schema/coverage population is already provisioned. The legacy
bootstrap substep is **B: not carried forward locally**, rather than replayed
against accepted tables. The remote workflow remains unchanged until its own
retirement gate. No provisioning, bootstrap, refresh or reconciliation is run.

## Installation boundary

There is no missing required current-profile secret confirmed today. Therefore
no new privileged installation script is released speculatively. Optional
producer/data/role adapters first need retention/admission decisions, bounded
implementation tests, exact schema/privilege review and protected recovery
material. Only then prepare one concrete reviewed operator installer.

Current external definitions are not a runtime dependency of the accepted local
Professor profile. They are remaining migration/retirement work while old
deployments/callers remain. Public nginx continues to deny all refresh/bootstrap/
reconcile/audit maintenance paths. A future CI URL substitution is not an
authorized migration. No new scheduler/cron, workflow dispatch, credentials or
provider activation occurred.
