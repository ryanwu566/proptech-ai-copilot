-- Additive BLUE serving quarantine. Apply only after reviewed reconciliation.
-- Does not delete, update or hide forensic access to original transactions.
create table if not exists public.market_serving_exclusions (
    serving_transaction_id bigint primary key
        references public.real_price_transactions(id),
    reason_code text not null check (reason_code = 'special_note_requires_review'),
    source_evidence_class text not null check (source_evidence_class = 'UNIQUE_MATCH'),
    source_official_id text not null check (source_official_id <> ''),
    evidence_version text not null check (evidence_version <> ''),
    fact_sha256 text not null check (fact_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default now()
);
revoke all on public.market_serving_exclusions from public;

-- PostgreSQL >=15: honor invoker privileges and any underlying RLS policies.
create or replace view public.market_serving_transactions
with (security_barrier=true, security_invoker=true) as
-- BEGIN PORTABLE VIEW SELECT
select serving_row.*
from public.real_price_transactions serving_row
where not exists (
    select 1 from public.market_serving_exclusions exclusion
    where exclusion.serving_transaction_id = serving_row.id
)
-- END PORTABLE VIEW SELECT
;
revoke all on public.market_serving_transactions from public;
-- Operator grants SELECT on these two objects to the inspected runtime role.
-- Enable PLVR_SERVING_EXCLUSIONS_ENABLED only after verification; no raw fallback.

-- Passive Market catalog/status reads also derive from filtered transactions;
-- a stale persisted aggregate must not restore an excluded-only group.
create or replace view public.market_serving_district_periods
with (security_barrier=true, security_invoker=true) as
select replace(trim(city),'臺','台') as county,
       trim(district) as district,transaction_period as period,
       round(avg(unit_price_per_ping)::numeric,2) as average_unit_price,
       count(*)::integer as transaction_count,count(*)::integer as record_count,
       'Official PLVR OpenData aggregate'::text as source_name,
       max(imported_at)::date as source_updated_at,
       'partial'::text as coverage_status,'available'::text as data_status,
       'avg_unit_price_per_ping_by_city_district_period'::text as aggregation_method
from public.market_serving_transactions
where source='official_plvr_opendata'
  and nullif(trim(city),'') is not null and nullif(trim(district),'') is not null
  and transaction_period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'
  and unit_price_per_ping>0 and unit_price_per_ping<=500
  and total_price>0 and area_ping>0
group by replace(trim(city),'臺','台'),trim(district),transaction_period;
revoke all on public.market_serving_district_periods from public;
-- Runtime also requires SELECT on this live derived view.
