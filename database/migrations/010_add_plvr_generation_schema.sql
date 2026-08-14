-- Phase 2F Approval A: additive production schema for authoritative PLVR
-- generations. This migration creates no generation, transaction, aggregate,
-- coverage, checkpoint, or active-pointer rows.

create table public.plvr_dataset_generations (
    dataset_key text not null,
    generation_id text not null,
    generation_role text not null,
    state text not null,
    source_manifest_sha256 text not null,
    dataset_sha256 text not null,
    expected_transaction_count bigint not null,
    expected_aggregate_count bigint not null,
    expected_period_min varchar(7) not null,
    expected_period_max varchar(7) not null,
    expected_city_count integer not null,
    expected_geographic_unit_count integer not null,
    canonical_invalid_count bigint not null default 0,
    future_publishable_count bigint not null default 0,
    lineage_missing_count bigint not null default 0,
    unresolved_source_conflict_count bigint not null default 0,
    manifest_frozen boolean not null default false,
    validated_at timestamptz,
    failure_reason_code text not null default '',
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    constraint pk_plvr_dataset_generations primary key (dataset_key, generation_id),
    constraint uq_plvr_dataset_generations_generation_id unique (generation_id),
    constraint ck_plvr_dataset_generations_role
        check (generation_role in ('legacy', 'candidate')),
    constraint ck_plvr_dataset_generations_state
        check (state in (
            'registered', 'loading', 'loaded', 'aggregating',
            'validated', 'active', 'inactive', 'failed'
        )),
    constraint ck_plvr_dataset_generations_expected_counts check (
        expected_transaction_count >= 0
        and expected_aggregate_count >= 0
        and expected_city_count >= 0
        and expected_geographic_unit_count >= 0
        and canonical_invalid_count >= 0
        and future_publishable_count >= 0
        and lineage_missing_count >= 0
        and unresolved_source_conflict_count >= 0
    ),
    constraint ck_plvr_dataset_generations_period_min
        check (expected_period_min ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    constraint ck_plvr_dataset_generations_period_max
        check (expected_period_max ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    constraint ck_plvr_dataset_generations_period_order
        check (expected_period_min <= expected_period_max),
    constraint ck_plvr_dataset_generations_hashes
        check (source_manifest_sha256 <> '' and dataset_sha256 <> '')
);

create index idx_plvr_dataset_generations_state
    on public.plvr_dataset_generations (dataset_key, state, updated_at desc);

create table public.plvr_generation_transactions (
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
    canonical_status text not null,
    publishable boolean not null default true,
    loaded_at timestamptz not null default clock_timestamp(),
    constraint pk_plvr_generation_transactions
        primary key (generation_id, source_row_hash),
    constraint uq_plvr_generation_transactions_identity
        unique (generation_id, source_identity),
    constraint fk_plvr_generation_transactions_generation
        foreign key (dataset_key, generation_id)
        references public.plvr_dataset_generations (dataset_key, generation_id)
        on delete restrict,
    constraint ck_plvr_generation_transactions_period
        check (transaction_period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    constraint ck_plvr_generation_transactions_lineage check (
        source_row_hash <> ''
        and source_identity <> ''
        and source_manifest_sha256 <> ''
        and source_artifact_sha256 <> ''
        and business_dedupe_key <> ''
    ),
    constraint ck_plvr_generation_transactions_metrics
        check (area_ping >= 0 and unit_price_per_ping >= 0 and total_price >= 0),
    constraint ck_plvr_generation_transactions_canonical_status
        check (canonical_status in ('canonical_valid', 'legacy_unverified'))
);

create index idx_plvr_generation_transactions_region_period
    on public.plvr_generation_transactions
    (generation_id, city, district, transaction_period desc);

create index idx_plvr_generation_transactions_business_key
    on public.plvr_generation_transactions (generation_id, business_dedupe_key);

create table public.plvr_generation_market_aggregates (
    dataset_key text not null,
    generation_id text not null,
    county text not null,
    district text not null,
    geographic_unit_kind text not null,
    period varchar(7) not null,
    average_unit_price numeric(18, 2),
    transaction_count bigint not null,
    record_count bigint not null,
    source_name text not null,
    coverage_status text not null,
    data_status text not null,
    aggregation_method text not null,
    built_at timestamptz not null default clock_timestamp(),
    constraint pk_plvr_generation_market_aggregates
        primary key (generation_id, county, district, period),
    constraint fk_plvr_generation_market_aggregates_generation
        foreign key (dataset_key, generation_id)
        references public.plvr_dataset_generations (dataset_key, generation_id)
        on delete restrict,
    constraint ck_plvr_generation_market_aggregates_period
        check (period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    constraint ck_plvr_generation_market_aggregates_counts
        check (transaction_count >= 0 and record_count >= 0)
);

create index idx_plvr_generation_market_aggregates_region_period
    on public.plvr_generation_market_aggregates
    (generation_id, county, district, period desc);

create table public.plvr_generation_region_coverage (
    dataset_key text not null,
    generation_id text not null,
    county text not null,
    district text not null,
    geographic_unit_kind text not null,
    period varchar(7) not null,
    coverage_status text not null,
    reason_code text not null default '',
    built_at timestamptz not null default clock_timestamp(),
    constraint pk_plvr_generation_region_coverage
        primary key (generation_id, county, district, period),
    constraint fk_plvr_generation_region_coverage_generation
        foreign key (dataset_key, generation_id)
        references public.plvr_dataset_generations (dataset_key, generation_id)
        on delete restrict,
    constraint ck_plvr_generation_region_coverage_period
        check (period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    constraint ck_plvr_generation_region_coverage_status check (
        coverage_status in ('COMPLETE', 'PARTIAL', 'MISSING', 'NOT_YET_EXPECTED')
    )
);

create index idx_plvr_generation_region_coverage_region_period
    on public.plvr_generation_region_coverage
    (generation_id, county, district, period desc);

create table public.plvr_active_dataset (
    dataset_key text not null,
    active_generation_id text not null,
    previous_generation_id text,
    switch_sequence bigint not null default 0,
    switched_at timestamptz not null default clock_timestamp(),
    constraint pk_plvr_active_dataset primary key (dataset_key),
    constraint fk_plvr_active_dataset_active_generation
        foreign key (dataset_key, active_generation_id)
        references public.plvr_dataset_generations (dataset_key, generation_id)
        on delete restrict,
    constraint fk_plvr_active_dataset_previous_generation
        foreign key (dataset_key, previous_generation_id)
        references public.plvr_dataset_generations (dataset_key, generation_id)
        on delete restrict,
    constraint ck_plvr_active_dataset_switch_sequence check (switch_sequence >= 0)
);

create table public.plvr_generation_load_checkpoints (
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
    constraint pk_plvr_generation_load_checkpoints
        primary key (dataset_key, generation_id),
    constraint fk_plvr_generation_load_checkpoints_generation
        foreign key (dataset_key, generation_id)
        references public.plvr_dataset_generations (dataset_key, generation_id)
        on delete restrict,
    constraint ck_plvr_generation_load_checkpoints_counts check (
        attempted_rows >= 0
        and inserted_rows >= 0
        and duplicate_rows >= 0
        and completed_batches >= 0
        and inserted_rows + duplicate_rows <= attempted_rows
    )
);

create index idx_plvr_generation_load_checkpoints_updated_at
    on public.plvr_generation_load_checkpoints (updated_at desc);

alter table public.plvr_dataset_generations enable row level security;
alter table public.plvr_generation_transactions enable row level security;
alter table public.plvr_generation_market_aggregates enable row level security;
alter table public.plvr_generation_region_coverage enable row level security;
alter table public.plvr_active_dataset enable row level security;
alter table public.plvr_generation_load_checkpoints enable row level security;

create function public.plvr_guard_frozen_generation_manifest()
returns trigger
language plpgsql
security invoker
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

create trigger trg_plvr_frozen_generation_manifest
before update on public.plvr_dataset_generations
for each row execute function public.plvr_guard_frozen_generation_manifest();

create function public.plvr_guard_generation_transaction()
returns trigger
language plpgsql
security invoker
as $$
declare
    generation public.plvr_dataset_generations%rowtype;
begin
    select * into generation
    from public.plvr_dataset_generations
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

create trigger trg_plvr_generation_transaction
before insert or update on public.plvr_generation_transactions
for each row execute function public.plvr_guard_generation_transaction();

create function public.plvr_guard_generation_derived_row()
returns trigger
language plpgsql
security invoker
as $$
declare
    generation_state text;
begin
    select state into generation_state
    from public.plvr_dataset_generations
    where dataset_key = new.dataset_key and generation_id = new.generation_id;
    if generation_state <> 'aggregating' then
        raise exception 'generation_not_aggregating';
    end if;
    return new;
end;
$$;

create trigger trg_plvr_generation_aggregate
before insert or update on public.plvr_generation_market_aggregates
for each row execute function public.plvr_guard_generation_derived_row();

create trigger trg_plvr_generation_coverage
before insert or update on public.plvr_generation_region_coverage
for each row execute function public.plvr_guard_generation_derived_row();

create function public.plvr_guard_active_generation()
returns trigger
language plpgsql
security invoker
as $$
declare
    generation_state text;
begin
    select state into generation_state
    from public.plvr_dataset_generations
    where dataset_key = new.dataset_key and generation_id = new.active_generation_id;
    if generation_state not in ('validated', 'active') then
        raise exception 'active_generation_must_be_validated';
    end if;
    return new;
end;
$$;

create trigger trg_plvr_active_generation
before insert or update on public.plvr_active_dataset
for each row execute function public.plvr_guard_active_generation();

create view public.plvr_active_transactions
with (security_invoker = true)
as
select transaction.*
from public.plvr_generation_transactions transaction
join public.plvr_active_dataset active
  on active.dataset_key = transaction.dataset_key
 and active.active_generation_id = transaction.generation_id
where transaction.publishable;

create view public.plvr_active_market_aggregates
with (security_invoker = true)
as
select aggregate.*
from public.plvr_generation_market_aggregates aggregate
join public.plvr_active_dataset active
  on active.dataset_key = aggregate.dataset_key
 and active.active_generation_id = aggregate.generation_id;

create view public.plvr_active_region_coverage
with (security_invoker = true)
as
select coverage.*
from public.plvr_generation_region_coverage coverage
join public.plvr_active_dataset active
  on active.dataset_key = coverage.dataset_key
 and active.active_generation_id = coverage.generation_id;

comment on table public.plvr_dataset_generations is
    'Authoritative PLVR dataset generation metadata; Approval A creates schema only.';
comment on table public.plvr_generation_transactions is
    'Generation-scoped PLVR transactions; populated only under a separate Approval B.';
comment on table public.plvr_generation_market_aggregates is
    'Generation-scoped market aggregates; populated only under a separate Approval C.';
comment on table public.plvr_generation_region_coverage is
    'Generation-scoped coverage; populated only under a separate Approval C.';
comment on table public.plvr_active_dataset is
    'Metadata-backed active generation pointer; changed only under a separate Approval D.';
comment on table public.plvr_generation_load_checkpoints is
    'Restartable generation-load checkpoints; populated only under a separate Approval B.';
