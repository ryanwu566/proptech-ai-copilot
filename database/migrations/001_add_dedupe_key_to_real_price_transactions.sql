-- Safe idempotent dedupe support for official PLVR imports.
alter table real_price_transactions
    add column if not exists dedupe_key text;

create unique index if not exists uq_real_price_source_dedupe_key
    on real_price_transactions (source, dedupe_key)
    where dedupe_key is not null;
