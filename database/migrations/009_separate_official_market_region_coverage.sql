-- Separate the release-based official coverage metadata from the legacy
-- direct-query coverage table without rewriting or dropping existing data.

do $$
begin
    if to_regclass('public.official_market_region_coverage') is null
       and to_regclass('public.market_region_coverage') is not null
       and exists (
           select 1
           from information_schema.columns
           where table_schema = 'public'
             and table_name = 'market_region_coverage'
             and column_name = 'release_id'
       )
       and not exists (
           select 1
           from information_schema.columns
           where table_schema = 'public'
             and table_name = 'market_region_coverage'
             and column_name = 'valid_market_candidate_count'
       ) then
        alter table public.market_region_coverage rename to official_market_region_coverage;
    end if;
end
$$;

create table if not exists official_market_region_coverage (
    release_id text not null references official_market_releases(release_id) on delete restrict,
    county text not null,
    district text not null,
    coverage_status text not null,
    latest_period varchar(7),
    record_count integer not null default 0,
    source_updated_at date,
    primary key (release_id, county, district)
);

create index if not exists idx_official_market_region_coverage_region_period
    on official_market_region_coverage (county, district, latest_period desc);
