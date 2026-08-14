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
`schema_migration_ledger` and would attempt every unrecorded migration. Approval
A expressly excludes ledger DML and unrelated pending migration execution.
Therefore production execution is blocked until a separate authorization
defines the bounded ledger operation or another reviewed, ledger-consistent
application procedure. Migration 010 must not be applied ad hoc around that
control.

## Local validation

The targeted validation applies migration 010 inside a transaction against the
guarded local `plvr_cutover_dryrun` database. It verifies tables, views,
constraints, foreign keys, indexes, RLS, security-invoker view behavior, empty
generation tables, an empty candidate metadata record, no active pointer, and
coexistence with a legacy table. The transaction is always rolled back.

## Remaining approvals

- Approval A production execution remains pending the ledger authorization.
- Approval B candidate transaction loading is not authorized.
- Approval C aggregate and coverage building is not authorized.
- Approval D active-pointer and reader switching is not authorized.
- Approval E legacy retirement or deletion is prohibited.
