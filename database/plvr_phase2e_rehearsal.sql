-- Phase 2E rehearsal schema. ISOLATED DATABASE ONLY - DO NOT EXECUTE IN PRODUCTION.

create table if not exists plvr_dataset_generations (
    dataset_key text not null,
    generation_id text not null,
    generation_role text not null check (generation_role in ('legacy', 'candidate', 'failure_fixture')),
    state text not null check (
        state in ('registered', 'loading', 'loaded', 'aggregating', 'validated', 'active', 'inactive', 'failed')
    ),
    source_manifest_sha256 text not null,
    dataset_sha256 text not null,
    expected_transaction_count bigint not null check (expected_transaction_count >= 0),
    expected_aggregate_count bigint not null check (expected_aggregate_count >= 0),
    expected_period_min varchar(7) not null,
    expected_period_max varchar(7) not null,
    expected_city_count integer not null check (expected_city_count >= 0),
    expected_geographic_unit_count integer not null check (expected_geographic_unit_count >= 0),
    canonical_invalid_count bigint not null default 0 check (canonical_invalid_count >= 0),
    future_publishable_count bigint not null default 0 check (future_publishable_count >= 0),
    lineage_missing_count bigint not null default 0 check (lineage_missing_count >= 0),
    unresolved_source_conflict_count bigint not null default 0 check (unresolved_source_conflict_count >= 0),
    manifest_frozen boolean not null default false,
    validated_at timestamptz,
    failure_reason_code text not null default '',
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    primary key (dataset_key, generation_id),
    unique (generation_id),
    check (expected_period_min ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    check (expected_period_max ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    check (expected_period_min <= expected_period_max)
);

create table if not exists plvr_generation_transactions (
    dataset_key text not null,
    generation_id text not null,
    source_row_hash text not null,
    source_identity text not null,
    source_manifest_sha256 text not null,
    source_artifact_sha256 text not null,
    official_transaction_id text not null default '',
    official_transfer_id text not null default '',
    business_dedupe_key text not null,
    production_fact_hash text not null,
    transaction_period varchar(7) not null,
    city text not null,
    district text not null,
    geographic_unit_kind text not null,
    road text not null default '',
    address_text text not null default '',
    building_type text not null default '',
    area_ping double precision not null,
    building_age_years double precision not null default 0,
    floor integer not null default 0,
    total_floor integer,
    unit_price_per_ping double precision not null,
    total_price double precision not null,
    source text not null,
    canonical_status text not null check (canonical_status in ('canonical_valid', 'legacy_unverified')),
    publishable boolean not null default true,
    loaded_at timestamptz not null default clock_timestamp(),
    primary key (generation_id, source_row_hash),
    unique (generation_id, source_identity),
    foreign key (dataset_key, generation_id)
        references plvr_dataset_generations(dataset_key, generation_id) on delete restrict,
    check (transaction_period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    check (source_row_hash <> '' and source_identity <> '' and source_artifact_sha256 <> ''),
    check (business_dedupe_key <> ''),
    check (area_ping >= 0 and unit_price_per_ping >= 0 and total_price >= 0)
);

create index if not exists idx_plvr_generation_transactions_region_period
    on plvr_generation_transactions(generation_id, city, district, transaction_period);
create index if not exists idx_plvr_generation_transactions_business_key
    on plvr_generation_transactions(generation_id, business_dedupe_key);

create table if not exists plvr_generation_market_aggregates (
    dataset_key text not null,
    generation_id text not null,
    county text not null,
    district text not null,
    geographic_unit_kind text not null,
    period varchar(7) not null,
    average_unit_price numeric(18, 2),
    transaction_count bigint not null check (transaction_count >= 0),
    record_count bigint not null check (record_count >= 0),
    source_name text not null,
    coverage_status text not null,
    data_status text not null,
    aggregation_method text not null,
    built_at timestamptz not null default clock_timestamp(),
    primary key (generation_id, county, district, period),
    foreign key (dataset_key, generation_id)
        references plvr_dataset_generations(dataset_key, generation_id) on delete restrict,
    check (period ~ '^\d{4}-(0[1-9]|1[0-2])$')
);

create table if not exists plvr_generation_region_coverage (
    dataset_key text not null,
    generation_id text not null,
    county text not null,
    district text not null,
    geographic_unit_kind text not null,
    period varchar(7) not null,
    coverage_status text not null check (
        coverage_status in ('COMPLETE', 'PARTIAL', 'MISSING', 'NOT_YET_EXPECTED')
    ),
    reason_code text not null default '',
    built_at timestamptz not null default clock_timestamp(),
    primary key (generation_id, county, district, period),
    foreign key (dataset_key, generation_id)
        references plvr_dataset_generations(dataset_key, generation_id) on delete restrict,
    check (period ~ '^\d{4}-(0[1-9]|1[0-2])$')
);

create table if not exists plvr_active_dataset (
    dataset_key text primary key,
    active_generation_id text not null,
    previous_generation_id text,
    switch_sequence bigint not null default 0,
    switched_at timestamptz not null default clock_timestamp(),
    foreign key (dataset_key, active_generation_id)
        references plvr_dataset_generations(dataset_key, generation_id) on delete restrict,
    foreign key (dataset_key, previous_generation_id)
        references plvr_dataset_generations(dataset_key, generation_id) on delete restrict
);

create table if not exists plvr_generation_load_checkpoints (
    dataset_key text not null,
    generation_id text not null,
    source_kind text not null,
    last_source_key text not null default '',
    attempted_rows bigint not null default 0,
    inserted_rows bigint not null default 0,
    duplicate_rows bigint not null default 0,
    completed_batches integer not null default 0,
    complete boolean not null default false,
    updated_at timestamptz not null default clock_timestamp(),
    primary key (dataset_key, generation_id),
    foreign key (dataset_key, generation_id)
        references plvr_dataset_generations(dataset_key, generation_id) on delete restrict
);

create table if not exists plvr_rehearsal_events (
    event_id bigint generated always as identity primary key,
    dataset_key text not null,
    generation_id text,
    event_type text not null,
    safe_detail jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default clock_timestamp()
);

create or replace function plvr_guard_frozen_generation_manifest()
returns trigger
language plpgsql
as $$
begin
    if old.manifest_frozen and (
        new.source_manifest_sha256 is distinct from old.source_manifest_sha256
        or new.dataset_sha256 is distinct from old.dataset_sha256
        or new.expected_transaction_count is distinct from old.expected_transaction_count
        or new.expected_aggregate_count is distinct from old.expected_aggregate_count
        or new.expected_period_min is distinct from old.expected_period_min
        or new.expected_period_max is distinct from old.expected_period_max
        or new.expected_city_count is distinct from old.expected_city_count
        or new.expected_geographic_unit_count is distinct from old.expected_geographic_unit_count
        or new.canonical_invalid_count is distinct from old.canonical_invalid_count
        or new.future_publishable_count is distinct from old.future_publishable_count
        or new.lineage_missing_count is distinct from old.lineage_missing_count
        or new.unresolved_source_conflict_count is distinct from old.unresolved_source_conflict_count
    ) then
        raise exception 'frozen_generation_manifest_is_immutable';
    end if;
    new.updated_at := clock_timestamp();
    return new;
end;
$$;

drop trigger if exists trg_plvr_frozen_generation_manifest on plvr_dataset_generations;
create trigger trg_plvr_frozen_generation_manifest
before update on plvr_dataset_generations
for each row execute function plvr_guard_frozen_generation_manifest();

create or replace function plvr_guard_generation_transaction()
returns trigger
language plpgsql
as $$
declare
    generation plvr_dataset_generations%rowtype;
begin
    select * into generation
    from plvr_dataset_generations
    where dataset_key = new.dataset_key and generation_id = new.generation_id;
    if not found or generation.state <> 'loading' then
        raise exception 'generation_not_loading';
    end if;
    if generation.generation_role = 'candidate' and (
        new.canonical_status <> 'canonical_valid'
        or not new.publishable
        or new.transaction_period < generation.expected_period_min
        or new.transaction_period > generation.expected_period_max
    ) then
        raise exception 'candidate_publishability_guard_failed';
    end if;
    return new;
end;
$$;

drop trigger if exists trg_plvr_generation_transaction on plvr_generation_transactions;
create trigger trg_plvr_generation_transaction
before insert or update on plvr_generation_transactions
for each row execute function plvr_guard_generation_transaction();

create or replace function plvr_guard_generation_derived_row()
returns trigger
language plpgsql
as $$
declare
    generation_state text;
begin
    select state into generation_state
    from plvr_dataset_generations
    where dataset_key = new.dataset_key and generation_id = new.generation_id;
    if generation_state <> 'aggregating' then
        raise exception 'generation_not_aggregating';
    end if;
    return new;
end;
$$;

drop trigger if exists trg_plvr_generation_aggregate on plvr_generation_market_aggregates;
create trigger trg_plvr_generation_aggregate
before insert or update on plvr_generation_market_aggregates
for each row execute function plvr_guard_generation_derived_row();

drop trigger if exists trg_plvr_generation_coverage on plvr_generation_region_coverage;
create trigger trg_plvr_generation_coverage
before insert or update on plvr_generation_region_coverage
for each row execute function plvr_guard_generation_derived_row();

create or replace function plvr_guard_active_generation()
returns trigger
language plpgsql
as $$
declare
    generation_state text;
begin
    select state into generation_state
    from plvr_dataset_generations
    where dataset_key = new.dataset_key and generation_id = new.active_generation_id;
    if generation_state not in ('validated', 'active') then
        raise exception 'active_generation_must_be_validated';
    end if;
    return new;
end;
$$;

drop trigger if exists trg_plvr_active_generation on plvr_active_dataset;
create trigger trg_plvr_active_generation
before insert or update on plvr_active_dataset
for each row execute function plvr_guard_active_generation();

create or replace view plvr_active_transactions as
select transaction.*
from plvr_generation_transactions transaction
join plvr_active_dataset active
  on active.dataset_key = transaction.dataset_key
 and active.active_generation_id = transaction.generation_id
where transaction.publishable;

create or replace view plvr_active_market_aggregates as
select aggregate.*
from plvr_generation_market_aggregates aggregate
join plvr_active_dataset active
  on active.dataset_key = aggregate.dataset_key
 and active.active_generation_id = aggregate.generation_id;

create or replace view plvr_active_region_coverage as
select coverage.*
from plvr_generation_region_coverage coverage
join plvr_active_dataset active
  on active.dataset_key = coverage.dataset_key
 and active.active_generation_id = coverage.generation_id;
