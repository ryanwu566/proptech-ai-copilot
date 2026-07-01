-- Optional performance indexes for bounded Market Insight direct queries.
-- Apply manually in the production database after review.

create index if not exists idx_market_direct_query_county_period
    on real_price_transactions (city, transaction_period desc)
    where source = 'official_plvr_opendata'
      and unit_price_per_ping > 0
      and area_ping > 0;

create index if not exists idx_market_direct_query_county_district_period
    on real_price_transactions (city, district, transaction_period desc)
    where source = 'official_plvr_opendata'
      and unit_price_per_ping > 0
      and area_ping > 0;
