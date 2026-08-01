-- Durable TaxOracle history for the production Postgres adapter.
-- Apply in a reviewed migration transaction. Rollback: drop the index, then
-- the table only after retention and export verification.

create table if not exists tax_analysis_history (
  id bigserial primary key,
  case_id text not null,
  client_name text not null,
  eligibility_status text not null,
  risk_score integer not null,
  signal_color text not null,
  payload_json jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_tax_analysis_history_created_at
  on tax_analysis_history(created_at desc);
create index if not exists idx_tax_analysis_history_case_id
  on tax_analysis_history(case_id, created_at desc);
