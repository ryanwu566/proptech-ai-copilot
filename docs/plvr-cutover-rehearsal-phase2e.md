# PLVR Cutover Rehearsal Phase 2E

## Scope and safety boundary

This rehearsal ran only against the disposable local PostgreSQL database
`plvr_cutover_dryrun`, reached through `PLVR_DRY_RUN_DATABASE_URL`. The target
guard accepted only loopback hosts and did not fall back to any production
runtime variable. Production connection attempts, DDL, DML, writes, and
pointer switches were all zero.

The BLUE generation came from the retained read-only production snapshot. The
GREEN generation came from the checksum-verified Phase 2C.5 clean shadow and
its 17 retained official source packages. No data was downloaded or recovered
from production during this rehearsal.

## Rehearsed schema

The isolated schema in `database/plvr_phase2e_rehearsal.sql` provides:

- generation registration and lifecycle state;
- generation-scoped transactions, aggregates, and coverage;
- durable load checkpoints;
- one active pointer for the `official_plvr` dataset;
- active-generation transaction, aggregate, and coverage views;
- manifest immutability and generation-state guards;
- pointer validation and atomic pointer updates;
- bounded rehearsal event evidence.

The SQL is intentionally outside `database/migrations`. It is rehearsal input,
not an approved production migration.

## Result

| Check | Result |
| --- | --- |
| GREEN transactions | 517,195 |
| GREEN aggregates | 9,606 |
| Publishable period | 2023-09 through 2026-07 |
| Official coverage | 94.29% |
| Missing expected coverage scopes | 0 |
| Hard gates | 15 / 15 passed |
| Golden regions | 7 / 7 passed |
| Dual read | PASS |
| BLUE to GREEN switch | PASS, atomic |
| Post-switch acceptance | PASS |
| GREEN to BLUE rollback | PASS, pointer-only |
| Rollback target | Under 5 minutes |
| BLUE to GREEN switch-forward | PASS |
| Failure injection | PASS |
| Resume | PASS |
| Idempotency | PASS |

The BLUE snapshot retained one future forensic row while keeping it
unpublishable. Raw BLUE evidence therefore remained intact, while publishable
reader and aggregate checks continued to end at `2026-07`.

GREEN loading was interrupted after three batches and resumed from its durable
checkpoint. A repeated first batch inserted zero additional rows. Rebuilding
aggregates and coverage produced stable counts and fingerprints.

## Failure rehearsal

The rehearsal confirmed that registered, partially loaded, loaded-only, and
failed generations cannot become active. It also confirmed rollback of an
interrupted aggregate transaction and an interrupted pointer-switch
transaction. The active pointer stayed valid throughout every injected
failure, and no partial generation became visible through active views.

## Evidence

- `artifacts/plvr_cutover_rehearsal_summary.json`
- `artifacts/plvr_cutover_rehearsal_gates.json`
- `artifacts/plvr_cutover_rehearsal_switch.json`
- `artifacts/plvr_cutover_rehearsal_rollback.json`
- `artifacts/plvr_cutover_rehearsal_failure_injection.json`

These artifacts contain bounded counts, states, durations, and gate evidence.
They do not contain connection strings, credentials, raw transaction rows, or
production payloads.

## Future production Approval A work

Approval A would require a separately reviewed additive production migration
derived from the rehearsal schema. That review must confirm existing-object
compatibility, table and index names, foreign keys, lifecycle constraints,
guard functions, active views, and rollback behavior against the then-current
production schema. It must also define a forward-only migration ledger entry
and a no-op/idempotency contract before any production execution.

This rehearsal does not authorize that migration. It also does not authorize:

- Approval A: production additive schema DDL;
- Approval B: production authoritative candidate load;
- Approval C: production aggregate build;
- Approval D: production reader or pointer switch;
- Approval E: legacy generation retirement or deletion.

All five approvals remain unexecuted. Approval E remains prohibited until a
later phase.
