-- Market Insight read model schema.
-- This schema stores district-period aggregates only. It must not store raw
-- PLVR transaction rows, addresses, coordinates, credentials, or provider
-- payloads.

create table if not exists market_district_period_aggregates (
    county text not null,
    district text not null,
    period varchar(7) not null,
    average_unit_price numeric(14, 2),
    transaction_count integer not null default 0,
    record_count integer not null default 0,
    source_name text not null,
    source_updated_at date,
    coverage_status text not null default 'unknown',
    data_status text not null default 'unavailable',
    aggregation_method text not null,
    built_at timestamptz not null,
    primary key (county, district, period)
);

create index if not exists idx_market_read_model_county
    on market_district_period_aggregates (county);

create index if not exists idx_market_read_model_county_district
    on market_district_period_aggregates (county, district);

create index if not exists idx_market_read_model_county_district_period
    on market_district_period_aggregates (county, district, period desc);

create index if not exists idx_market_read_model_period
    on market_district_period_aggregates (period desc);

create table if not exists market_read_model_metadata (
    read_model_version text primary key,
    refresh_status text not null,
    coverage_status text not null default 'unknown',
    source_name text not null,
    source_updated_at date,
    earliest_period varchar(7),
    latest_period varchar(7),
    available_county_count integer not null default 0,
    available_district_count integer not null default 0,
    aggregate_region_count integer not null default 0,
    built_at timestamptz not null,
    caveat text not null
);
