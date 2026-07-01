-- Coverage metadata for protected Market Insight rollout operations.
-- Apply only through the protected operator workflow or a reviewed database change.

create table if not exists market_region_coverage (
    county text not null,
    district text not null,
    coverage_status text not null,
    valid_market_candidate_count integer not null default 0,
    source_updated_at date,
    reconciled_at timestamptz not null,
    primary key (county, district)
);

create index if not exists idx_market_region_coverage_county
    on market_region_coverage (county);

create index if not exists idx_market_region_coverage_status
    on market_region_coverage (coverage_status);
