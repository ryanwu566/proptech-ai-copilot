-- Safe idempotent import-run audit fields.
alter table valuation_import_runs
    add column if not exists city_scope text default '',
    add column if not exists district_scope text default '',
    add column if not exists road_scope text default '',
    add column if not exists input_file_count integer not null default 0,
    add column if not exists read_rows integer not null default 0,
    add column if not exists accepted_rows integer not null default 0,
    add column if not exists inserted_rows integer not null default 0,
    add column if not exists updated_rows integer not null default 0,
    add column if not exists skipped_duplicate_rows integer not null default 0,
    add column if not exists excluded_rows integer not null default 0;
