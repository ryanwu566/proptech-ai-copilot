-- 013_vnext_workspace_case_foundation.sql
--
-- Stage 1 Slice 2: durable Workspace/Case tenancy foundation.
-- This migration is additive, creates no PropertyEntity or Evidence records,
-- exposes no schema through the Data API, and provisions no database secret.

-- The request identity is a direct-login database role whose password is
-- provisioned by deployment tooling outside migration history.  Creating a
-- LOGIN role without a password keeps current_user verification possible while
-- making the role unable to authenticate until an operator provisions it.
do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'vnext_api') then
        create role vnext_api
            login
            nosuperuser
            nocreatedb
            nocreaterole
            noinherit
            noreplication
            nobypassrls;
    end if;
end
$$;

alter role vnext_api
    login
    nosuperuser
    nocreatedb
    nocreaterole
    noinherit
    noreplication
    nobypassrls;

comment on role vnext_api is
    'Normal VNext FastAPI request role. Credential provisioned outside migrations; never owns tenant tables or bypasses RLS.';

do $$
begin
    if to_regclass('auth.users') is null then
        raise exception 'vnext_auth_users_prerequisite_missing';
    end if;
    if to_regprocedure('auth.uid()') is null then
        raise exception 'vnext_auth_uid_prerequisite_missing';
    end if;
end
$$;

create schema if not exists vnext_core;
create schema if not exists vnext_private;

revoke all on schema vnext_core from public;
revoke all on schema vnext_private from public;
grant usage on schema auth, vnext_core, vnext_private to vnext_api;
grant execute on function auth.uid() to vnext_api;

create table vnext_core.workspaces (
    workspace_id uuid primary key default gen_random_uuid(),
    workspace_type text not null,
    display_name text not null,
    status text not null default 'active',
    version bigint not null default 1,
    created_by_user_id uuid not null,
    personal_owner_user_id uuid,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    archived_at timestamptz,
    constraint fk_vnext_workspaces_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint fk_vnext_workspaces_personal_owner
        foreign key (personal_owner_user_id) references auth.users(id) on delete restrict,
    constraint ck_vnext_workspaces_type
        check (workspace_type in ('personal', 'team')),
    constraint ck_vnext_workspaces_display_name
        check (char_length(btrim(display_name)) between 1 and 160),
    constraint ck_vnext_workspaces_status
        check (status in ('active', 'suspended', 'archived')),
    constraint ck_vnext_workspaces_version
        check (version >= 1),
    constraint ck_vnext_workspaces_personal_owner
        check (
            (workspace_type = 'personal' and personal_owner_user_id is not null)
            or (workspace_type = 'team' and personal_owner_user_id is null)
        ),
    constraint ck_vnext_workspaces_archive_time
        check (
            (status = 'archived' and archived_at is not null)
            or (status <> 'archived' and archived_at is null)
        )
);

create unique index uq_vnext_workspaces_personal_owner
    on vnext_core.workspaces (personal_owner_user_id)
    where workspace_type = 'personal' and status <> 'archived';

create index idx_vnext_workspaces_status
    on vnext_core.workspaces (status, updated_at desc);

create table vnext_core.workspace_members (
    workspace_member_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    user_id uuid not null,
    role text not null,
    status text not null default 'invited',
    invited_at timestamptz not null default clock_timestamp(),
    joined_at timestamptz,
    left_at timestamptz,
    revoked_at timestamptz,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_workspace_members_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_workspace_members_user
        foreign key (user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_workspace_members_workspace_user
        unique (workspace_id, user_id),
    constraint uq_vnext_workspace_members_workspace_member
        unique (workspace_id, workspace_member_id),
    constraint ck_vnext_workspace_members_role
        check (role in ('owner', 'admin', 'manager', 'member', 'viewer')),
    constraint ck_vnext_workspace_members_status
        check (status in ('invited', 'active', 'suspended', 'left', 'removed')),
    constraint ck_vnext_workspace_members_lifecycle
        check (
            (status = 'invited' and joined_at is null and left_at is null and revoked_at is null)
            or (status in ('active', 'suspended') and joined_at is not null and left_at is null and revoked_at is null)
            or (status = 'left' and joined_at is not null and left_at is not null and revoked_at is null)
            or (status = 'removed' and revoked_at is not null)
        )
);

create index idx_vnext_workspace_members_user_status
    on vnext_core.workspace_members (user_id, status);

create index idx_vnext_workspace_members_workspace_status_role
    on vnext_core.workspace_members (workspace_id, status, role);

create table vnext_core.cases (
    case_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    purpose text not null,
    status text not null default 'open',
    title text not null,
    identity_status text not null default 'unverified',
    assigned_member_id uuid,
    created_by_user_id uuid not null,
    version bigint not null default 1,
    opened_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    closed_at timestamptz,
    archived_at timestamptz,
    constraint fk_vnext_cases_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_cases_assigned_member
        foreign key (workspace_id, assigned_member_id)
        references vnext_core.workspace_members(workspace_id, workspace_member_id)
        on delete restrict,
    constraint fk_vnext_cases_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint ck_vnext_cases_purpose
        check (purpose in (
            'buy_due_diligence', 'development', 'brokerage',
            'valuation_review', 'investment_review'
        )),
    constraint ck_vnext_cases_status
        check (status in ('open', 'in_progress', 'on_hold', 'closed', 'archived')),
    constraint ck_vnext_cases_title
        check (char_length(btrim(title)) between 1 and 240),
    constraint ck_vnext_cases_identity_status
        check (identity_status in (
            'unverified', 'legacy_unverified', 'resolving', 'confirmed'
        )),
    constraint ck_vnext_cases_version
        check (version >= 1),
    constraint ck_vnext_cases_close_time
        check (
            status <> 'closed' or closed_at is not null
        ),
    constraint ck_vnext_cases_archive_time
        check (
            (status = 'archived' and archived_at is not null)
            or (status <> 'archived' and archived_at is null)
        )
);

create index idx_vnext_cases_workspace_status_updated
    on vnext_core.cases (workspace_id, status, updated_at desc);

create index idx_vnext_cases_assignee
    on vnext_core.cases (workspace_id, assigned_member_id)
    where assigned_member_id is not null;

create index idx_vnext_cases_purpose
    on vnext_core.cases (workspace_id, purpose);

create table vnext_private.idempotency_records (
    idempotency_record_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    actor_user_id uuid not null,
    http_method text not null,
    canonical_route text not null,
    idempotency_key_hash text not null,
    request_fingerprint text not null,
    operation_status text not null default 'pending',
    response_status_code integer,
    response_reference_type text,
    response_reference_id uuid,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    expires_at timestamptz not null,
    constraint fk_vnext_idempotency_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_idempotency_actor
        foreign key (actor_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_idempotency_scope
        unique (
            workspace_id, actor_user_id, http_method,
            canonical_route, idempotency_key_hash
        ),
    constraint ck_vnext_idempotency_method
        check (http_method in ('POST', 'PUT', 'PATCH', 'DELETE')),
    constraint ck_vnext_idempotency_route
        check (char_length(canonical_route) between 1 and 300),
    constraint ck_vnext_idempotency_key_hash
        check (idempotency_key_hash ~ '^[0-9a-f]{64}$'),
    constraint ck_vnext_idempotency_request_fingerprint
        check (request_fingerprint ~ '^[0-9a-f]{64}$'),
    constraint ck_vnext_idempotency_operation_status
        check (operation_status in ('pending', 'succeeded', 'failed')),
    constraint ck_vnext_idempotency_response_status
        check (response_status_code is null or response_status_code between 100 and 599),
    constraint ck_vnext_idempotency_reference_type
        check (
            response_reference_type is null
            or char_length(response_reference_type) between 1 and 80
        ),
    constraint ck_vnext_idempotency_expiry
        check (expires_at > created_at)
);

create index idx_vnext_idempotency_expiry
    on vnext_private.idempotency_records (expires_at);

create index idx_vnext_idempotency_workspace_actor_created
    on vnext_private.idempotency_records (workspace_id, actor_user_id, created_at desc);

create table vnext_private.audit_events (
    audit_event_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    actor_user_id uuid not null,
    event_type text not null,
    resource_type text not null,
    resource_id uuid,
    request_id text not null,
    idempotency_key_hash text,
    source text not null default 'vnext_api',
    outcome text not null,
    reason_code text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_audit_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_audit_actor
        foreign key (actor_user_id) references auth.users(id) on delete restrict,
    constraint ck_vnext_audit_event_type
        check (char_length(event_type) between 1 and 120),
    constraint ck_vnext_audit_resource_type
        check (char_length(resource_type) between 1 and 80),
    constraint ck_vnext_audit_request_id
        check (char_length(request_id) between 1 and 128),
    constraint ck_vnext_audit_key_hash
        check (
            idempotency_key_hash is null
            or idempotency_key_hash ~ '^[0-9a-f]{64}$'
        ),
    constraint ck_vnext_audit_source
        check (char_length(source) between 1 and 80),
    constraint ck_vnext_audit_outcome
        check (outcome in ('succeeded', 'denied', 'failed')),
    constraint ck_vnext_audit_reason_code
        check (reason_code is null or char_length(reason_code) between 1 and 80),
    constraint ck_vnext_audit_metadata
        check (
            jsonb_typeof(metadata) = 'object'
            and octet_length(metadata::text) <= 16384
        )
);

create index idx_vnext_audit_workspace_created
    on vnext_private.audit_events (workspace_id, created_at desc);

create index idx_vnext_audit_resource_created
    on vnext_private.audit_events (workspace_id, resource_type, resource_id, created_at desc)
    where resource_id is not null;

create index idx_vnext_audit_request
    on vnext_private.audit_events (request_id);

create index idx_vnext_audit_event_type_created
    on vnext_private.audit_events (event_type, created_at desc);

create function vnext_private.guard_case_update()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if new.case_id is distinct from old.case_id
       or new.workspace_id is distinct from old.workspace_id
       or new.created_by_user_id is distinct from old.created_by_user_id
       or new.opened_at is distinct from old.opened_at then
        raise exception using errcode = '42501', message = 'vnext_case_identity_is_immutable';
    end if;
    if new.identity_status is distinct from old.identity_status then
        raise exception using errcode = '42501', message = 'vnext_case_identity_command_required';
    end if;
    if new.assigned_member_id is distinct from old.assigned_member_id then
        raise exception using errcode = '42501', message = 'vnext_case_assignment_command_required';
    end if;
    if new.version <> old.version + 1 then
        raise exception using errcode = '40001', message = 'vnext_case_version_increment_required';
    end if;
    if old.status = 'archived' and new.status <> 'archived' then
        raise exception using errcode = '42501', message = 'vnext_case_archive_is_terminal';
    end if;
    return new;
end
$$;

revoke all on function vnext_private.guard_case_update() from public;

create trigger trg_vnext_cases_guard_update
before update on vnext_core.cases
for each row execute function vnext_private.guard_case_update();

create function vnext_private.guard_idempotency_update()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if new.idempotency_record_id is distinct from old.idempotency_record_id
       or new.workspace_id is distinct from old.workspace_id
       or new.actor_user_id is distinct from old.actor_user_id
       or new.http_method is distinct from old.http_method
       or new.canonical_route is distinct from old.canonical_route
       or new.idempotency_key_hash is distinct from old.idempotency_key_hash
       or new.request_fingerprint is distinct from old.request_fingerprint
       or new.created_at is distinct from old.created_at
       or new.expires_at is distinct from old.expires_at then
        raise exception using errcode = '42501', message = 'vnext_idempotency_scope_is_immutable';
    end if;
    if old.operation_status <> 'pending'
       and new.operation_status is distinct from old.operation_status then
        raise exception using errcode = '42501', message = 'vnext_idempotency_operation_is_final';
    end if;
    return new;
end
$$;

revoke all on function vnext_private.guard_idempotency_update() from public;

create trigger trg_vnext_idempotency_guard_update
before update on vnext_private.idempotency_records
for each row execute function vnext_private.guard_idempotency_update();

create function vnext_private.guard_audit_append_only()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    raise exception using errcode = '42501', message = 'vnext_audit_event_is_append_only';
end
$$;

revoke all on function vnext_private.guard_audit_append_only() from public;

create trigger trg_vnext_audit_append_only
before update or delete on vnext_private.audit_events
for each row execute function vnext_private.guard_audit_append_only();

alter table vnext_core.workspaces enable row level security;
alter table vnext_core.workspaces force row level security;
alter table vnext_core.workspace_members enable row level security;
alter table vnext_core.workspace_members force row level security;
alter table vnext_core.cases enable row level security;
alter table vnext_core.cases force row level security;
alter table vnext_private.idempotency_records enable row level security;
alter table vnext_private.idempotency_records force row level security;
alter table vnext_private.audit_events enable row level security;
alter table vnext_private.audit_events force row level security;

revoke all on all tables in schema vnext_core from public;
revoke all on all tables in schema vnext_private from public;
revoke all on all functions in schema vnext_private from public;

grant select on vnext_core.workspaces to vnext_api;
grant select on vnext_core.workspace_members to vnext_api;
grant select, insert, update on vnext_core.cases to vnext_api;
grant select, insert, update on vnext_private.idempotency_records to vnext_api;
grant insert on vnext_private.audit_events to vnext_api;

create policy workspace_members_self_select
on vnext_core.workspace_members
for select
to vnext_api
using (
    user_id = (select auth.uid())
);

create policy workspaces_active_member_select
on vnext_core.workspaces
for select
to vnext_api
using (
    exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = workspaces.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy cases_active_member_select
on vnext_core.cases
for select
to vnext_api
using (
    exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = cases.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member', 'viewer')
    )
);

create policy cases_active_writer_insert
on vnext_core.cases
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and assigned_member_id is null
    and identity_status in ('unverified', 'legacy_unverified')
    and exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = cases.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy cases_active_writer_update
on vnext_core.cases
for update
to vnext_api
using (
    exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = cases.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
)
with check (
    exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = cases.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy idempotency_actor_select
on vnext_private.idempotency_records
for select
to vnext_api
using (
    actor_user_id = (select auth.uid())
    and exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = idempotency_records.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy idempotency_actor_insert
on vnext_private.idempotency_records
for insert
to vnext_api
with check (
    actor_user_id = (select auth.uid())
    and exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = idempotency_records.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy idempotency_actor_update
on vnext_private.idempotency_records
for update
to vnext_api
using (
    actor_user_id = (select auth.uid())
    and exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = idempotency_records.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
)
with check (
    actor_user_id = (select auth.uid())
    and exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = idempotency_records.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy audit_actor_insert
on vnext_private.audit_events
for insert
to vnext_api
with check (
    actor_user_id = (select auth.uid())
    and exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = audit_events.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member', 'viewer')
    )
);

alter default privileges in schema vnext_core revoke all on tables from public;
alter default privileges in schema vnext_private revoke all on tables from public;
alter default privileges in schema vnext_private revoke all on functions from public;

comment on schema vnext_core is
    'Private VNext tenant/domain base tables. Not exposed through the Supabase Data API.';
comment on schema vnext_private is
    'Private VNext operational/security records. Server roles only; not a browser surface.';
comment on table vnext_private.audit_events is
    'Append-only VNext security/accountability events. Application role has INSERT only.';
