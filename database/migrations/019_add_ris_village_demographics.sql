-- Phase 3A: canonical monthly RIS ODRP014 village demographics observations.
-- district_code is unique only within a statistic month; it is not a
-- permanent village entity identifier.

create table public.ris_village_demographics (
    id bigint generated always as identity primary key,
    statistic_yyymm text not null,
    statistic_month date not null,
    district_code text not null,
    site_id text not null,
    village text not null,
    household_count integer not null check (household_count >= 0),
    total_population integer not null check (total_population >= 0),
    male_population integer not null check (male_population >= 0),
    female_population integer not null check (female_population >= 0),
    age_0_14 integer not null check (age_0_14 >= 0),
    age_15_64 integer not null check (age_15_64 >= 0),
    age_65_plus integer not null check (age_65_plus >= 0),
    child_ratio double precision
        check (child_ratio is null or (child_ratio >= 0 and child_ratio <= 1)),
    working_age_ratio double precision
        check (working_age_ratio is null or (working_age_ratio >= 0 and working_age_ratio <= 1)),
    elderly_ratio double precision
        check (elderly_ratio is null or (elderly_ratio >= 0 and elderly_ratio <= 1)),
    average_household_size double precision
        check (average_household_size is null or average_household_size >= 0),
    audit_reasons jsonb not null default '[]'::jsonb,
    source_provider text not null default 'RIS',
    source_dataset text not null default 'ODRP014',
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    unique (statistic_yyymm, district_code)
);

create index idx_ris_village_demographics_district_month
    on public.ris_village_demographics (district_code, statistic_month desc);

create index idx_ris_village_demographics_site_month
    on public.ris_village_demographics (site_id, statistic_month desc);

create index idx_ris_village_demographics_month
    on public.ris_village_demographics (statistic_month);

alter table public.ris_village_demographics enable row level security;

revoke all on table public.ris_village_demographics from public;
revoke all on sequence public.ris_village_demographics_id_seq from public;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'anon') then
        execute 'revoke all on table public.ris_village_demographics from anon';
        execute 'revoke all on sequence public.ris_village_demographics_id_seq from anon';
        if has_table_privilege('anon', 'public.ris_village_demographics',
                               'select, insert, update, delete, truncate, references, trigger') then
            raise exception 'anon retains a privilege on public.ris_village_demographics';
        end if;
    end if;

    if exists (select 1 from pg_roles where rolname = 'authenticated') then
        execute 'revoke all on table public.ris_village_demographics from authenticated';
        execute 'revoke all on sequence public.ris_village_demographics_id_seq from authenticated';
        if has_table_privilege('authenticated', 'public.ris_village_demographics',
                               'select, insert, update, delete, truncate, references, trigger') then
            raise exception 'authenticated retains a privilege on public.ris_village_demographics';
        end if;
    end if;
end
$$;
