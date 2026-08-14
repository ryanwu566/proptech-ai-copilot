# PLVR Production Schema Approval A Phase 2F

## Authorization boundary

Phase 2F Approval A is limited to additive production schema definition for the
authoritative PLVR generation architecture. It does not authorize candidate
transaction loading, aggregate or coverage building, active-pointer changes,
reader changes, legacy mutation, or legacy deletion.

Migration `010_add_plvr_generation_schema.sql` is derived from the successful
Phase 2E rehearsal. It defines generation metadata, generation-scoped
transactions, aggregates, coverage, restartable load checkpoints, and the
metadata-backed active pointer. It also defines lifecycle guards and
security-invoker active views. The migration inserts no rows and creates no
active generation or pointer.

All new public tables have row-level security enabled. No public API grants or
policies are introduced by this migration.

## Production preflight

The sanitized read-only preflight confirmed:

- the production runtime uses remote PostgreSQL;
- the legacy `real_price_transactions` table is present;
- no Phase 2F target table or active view already exists;
- no active generation pointer exists;
- the current legacy reader path remains in place;
- the custom `schema_migration_ledger` table is not present.

The repository's normal migration runner creates and writes
`schema_migration_ledger` and would attempt every unrecorded migration. The
Phase 2F-A1 audit therefore established an explicit metadata baseline instead
of invoking that runner. Migrations 004-006 and 008-009 were proven absent and
were neither executed nor recorded as applied.

## Production Approval A execution

Phase 2F-A2 completed the bounded production operation in one transaction:

- created `schema_migration_ledger` from migration 007;
- recorded the independently proven 001, both 002, 003, and 007 baselines;
- applied only migration 010;
- recorded migration 010 with its reviewed checksum;
- committed exactly six migration metadata rows.

Post-commit read-only validation confirmed all six generation tables, three
security-invoker active views, six explicit indexes, lifecycle constraints,
foreign keys, RLS, guard functions, and triggers. Every generation table and
active view remained empty, and no active dataset pointer was created.

The legacy official PLVR count remained `451672`, the total
`real_price_transactions` count remained `451744`, and the maximum publishable
period remained `2026-05`. No business-data DML, destructive operation, reader
switch, or user-visible data-path change occurred.

Validation results:

- targeted Phase 2F tests: 15 passed;
- relevant PLVR/Market/PostgreSQL tests: 465 passed, 3 skipped, 1 warning;
- full Python suite: 1206 passed, 3 skipped, 1 warning.

## Local validation

The targeted validation applies migration 010 inside a transaction against the
guarded local `plvr_cutover_dryrun` database. It verifies tables, views,
constraints, foreign keys, indexes, RLS, security-invoker view behavior, empty
generation tables, an empty candidate metadata record, no active pointer, and
coexistence with a legacy table. The transaction is always rolled back.

## Remaining approvals

- Approval A additive production schema execution is complete.
- Approval B candidate transaction loading is not authorized.
- Approval C aggregate and coverage building is not authorized.
- Approval D active-pointer and reader switching is not authorized.
- Approval E legacy retirement or deletion is prohibited.
