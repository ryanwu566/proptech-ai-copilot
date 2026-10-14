-- Wave 1A: private, minimal server-controlled account authority.
-- Matches this repository's numbered migration registry; no hosted execution.
create table vnext_private.consumer_accounts (
    user_id uuid primary key references auth.users(id) on delete restrict,
    status text not null default 'active' check (status in ('active', 'suspended')),
    platform_role text not null default 'consumer' check (platform_role in ('consumer', 'platform_admin')),
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp()
);

-- Existing identities start as consumers. No metadata or workspace-role authority.
insert into vnext_private.consumer_accounts (user_id) select id from auth.users;

alter table vnext_private.consumer_accounts enable row level security;
alter table vnext_private.consumer_accounts force row level security;
revoke all on vnext_private.consumer_accounts from public;
grant select on vnext_private.consumer_accounts to vnext_api;
grant insert (user_id) on vnext_private.consumer_accounts to vnext_api;

create policy consumer_accounts_self_select on vnext_private.consumer_accounts
for select to vnext_api using (user_id = (select auth.uid()));
create policy consumer_accounts_default_insert on vnext_private.consumer_accounts
for insert to vnext_api with check (
    user_id = (select auth.uid()) and status = 'active' and platform_role = 'consumer'
);

-- A restrictive policy composes with all existing membership-dependent policies.
-- Missing accounts and suspension both deny tenant data access at the DB boundary.
create policy workspace_members_active_account on vnext_core.workspace_members
as restrictive for select to vnext_api using (
    exists (select 1 from vnext_private.consumer_accounts account
            where account.user_id = (select auth.uid()) and account.status = 'active')
);

comment on table vnext_private.consumer_accounts is
    'Auth identity remains auth.users. Status/role updates require a separately authorized operator; never grant request roles UPDATE. Operator updates also set updated_at. No Data API exposure.';
