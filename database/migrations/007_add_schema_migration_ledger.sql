-- Operational schema ledger. It contains migration metadata only, never secrets
-- or business records. Apply with the reviewed migration runner before traffic.

create table if not exists schema_migration_ledger (
  migration_id text primary key,
  schema_version text not null,
  applied_at timestamptz not null default now(),
  release_version text,
  checksum text
);

create index if not exists idx_schema_migration_ledger_applied_at
  on schema_migration_ledger(applied_at desc);
