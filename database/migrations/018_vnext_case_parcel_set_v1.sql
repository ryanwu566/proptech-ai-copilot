-- 018_vnext_case_parcel_set_v1.sql
--
-- Durable Case-local parcel membership and review state.  Property Identity
-- references remain the truth layer: Case selection is not official or
-- canonical parcel confirmation and does not change Property Identity.

-- Migration 015 already provides uq_vnext_cases_workspace_case.  Reuse that
-- frozen composite key rather than adding a duplicate index.

create table vnext_core.case_parcel_sets (
    parcel_set_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    case_id uuid not null,
    status text not null default 'draft',
    version bigint not null default 1,
    active_member_id uuid,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    reviewed_at timestamptz,
    constraint fk_vnext_case_parcel_sets_case
        foreign key (workspace_id, case_id)
        references vnext_core.cases(workspace_id, case_id)
        on delete restrict,
    constraint fk_vnext_case_parcel_sets_created_by
        foreign key (created_by_user_id)
        references auth.users(id)
        on delete restrict,
    constraint uq_vnext_case_parcel_sets_workspace_set
        unique (workspace_id, parcel_set_id),
    constraint uq_vnext_case_parcel_sets_case
        unique (workspace_id, case_id),
    constraint ck_vnext_case_parcel_sets_status
        check (status in ('draft', 'case_reviewed')),
    constraint ck_vnext_case_parcel_sets_version
        check (version >= 1),
    constraint ck_vnext_case_parcel_sets_review_time
        check (
            (status = 'case_reviewed' and reviewed_at is not null)
            or (status = 'draft' and reviewed_at is null)
        )
);

create table vnext_core.case_parcel_set_members (
    parcel_set_member_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    parcel_set_id uuid not null,
    parcel_identity_reference_id uuid not null,
    position smallint not null,
    review_status text not null default 'candidate',
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_case_parcel_set_members_set
        foreign key (workspace_id, parcel_set_id)
        references vnext_core.case_parcel_sets(workspace_id, parcel_set_id)
        on delete restrict,
    constraint fk_vnext_case_parcel_set_members_reference
        foreign key (workspace_id, parcel_identity_reference_id)
        references vnext_core.property_identity_references(
            workspace_id, identity_reference_id
        )
        on delete restrict,
    constraint fk_vnext_case_parcel_set_members_created_by
        foreign key (created_by_user_id)
        references auth.users(id)
        on delete restrict,
    constraint uq_vnext_case_parcel_set_members_workspace_member
        unique (workspace_id, parcel_set_id, parcel_set_member_id),
    constraint uq_vnext_case_parcel_set_members_reference
        unique (workspace_id, parcel_set_id, parcel_identity_reference_id),
    constraint uq_vnext_case_parcel_set_members_position
        unique (workspace_id, parcel_set_id, position)
        deferrable initially deferred,
    constraint ck_vnext_case_parcel_set_members_position
        check (position between 1 and 100),
    constraint ck_vnext_case_parcel_set_members_review_status
        check (review_status in ('candidate', 'case_selected', 'case_rejected'))
);

alter table vnext_core.case_parcel_sets
    add constraint fk_vnext_case_parcel_sets_active_member
    foreign key (workspace_id, parcel_set_id, active_member_id)
    references vnext_core.case_parcel_set_members(
        workspace_id, parcel_set_id, parcel_set_member_id
    )
    on delete restrict;

create index idx_vnext_case_parcel_sets_active_member
    on vnext_core.case_parcel_sets (workspace_id, active_member_id)
    where active_member_id is not null;

create index idx_vnext_case_parcel_set_members_order
    on vnext_core.case_parcel_set_members (
        workspace_id, parcel_set_id, position, parcel_set_member_id
    );

create index idx_vnext_case_parcel_set_members_reference
    on vnext_core.case_parcel_set_members (
        workspace_id, parcel_identity_reference_id
    );

create function vnext_private.guard_case_parcel_set_update()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public, auth, vnext_core, vnext_private
as $$
begin
    if new.parcel_set_id is distinct from old.parcel_set_id
       or new.workspace_id is distinct from old.workspace_id
       or new.case_id is distinct from old.case_id
       or new.created_by_user_id is distinct from old.created_by_user_id
       or new.created_at is distinct from old.created_at then
        raise exception using
            errcode = '42501',
            message = 'vnext_case_parcel_set_identity_is_immutable';
    end if;

    if new.version <> old.version + 1 then
        raise exception using
            errcode = '40001',
            message = 'vnext_case_parcel_set_version_increment_required';
    end if;

    if new.updated_at <= old.updated_at then
        raise exception using
            errcode = '23514',
            message = 'vnext_case_parcel_set_update_time_must_advance';
    end if;

    if (new.status = 'case_reviewed' and new.reviewed_at is null)
       or (new.status = 'draft' and new.reviewed_at is not null) then
        raise exception using
            errcode = '23514',
            message = 'vnext_case_parcel_set_review_time_invalid';
    end if;

    return new;
end;
$$;

revoke all on function vnext_private.guard_case_parcel_set_update() from public;

create trigger trg_vnext_case_parcel_sets_guard_update
before update on vnext_core.case_parcel_sets
for each row execute function vnext_private.guard_case_parcel_set_update();

create function vnext_private.guard_case_parcel_set_member()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog, public, auth, vnext_core, vnext_private
as $$
declare
    selected_reference_type text;
begin
    if tg_op = 'UPDATE' and (
        new.parcel_set_member_id is distinct from old.parcel_set_member_id
        or new.workspace_id is distinct from old.workspace_id
        or new.parcel_set_id is distinct from old.parcel_set_id
        or new.parcel_identity_reference_id is distinct from old.parcel_identity_reference_id
        or new.created_by_user_id is distinct from old.created_by_user_id
        or new.created_at is distinct from old.created_at
    ) then
        raise exception using
            errcode = '42501',
            message = 'vnext_case_parcel_set_member_identity_is_immutable';
    end if;

    if tg_op = 'UPDATE' and new.updated_at <= old.updated_at then
        raise exception using
            errcode = '23514',
            message = 'vnext_case_parcel_set_member_update_time_must_advance';
    end if;

    select reference.reference_type
    into selected_reference_type
    from vnext_core.property_identity_references reference
    where reference.workspace_id = new.workspace_id
      and reference.identity_reference_id = new.parcel_identity_reference_id;

    if not found then
        raise exception using
            errcode = '23503',
            message = 'vnext_case_parcel_member_reference_not_found';
    end if;

    if selected_reference_type <> 'parcel' then
        raise exception using
            errcode = '23514',
            message = 'vnext_case_parcel_member_reference_must_be_parcel';
    end if;

    return new;
end;
$$;

revoke all on function vnext_private.guard_case_parcel_set_member() from public;

create trigger trg_vnext_case_parcel_set_members_guard
before insert or update on vnext_core.case_parcel_set_members
for each row execute function vnext_private.guard_case_parcel_set_member();

alter table vnext_core.case_parcel_sets enable row level security;
alter table vnext_core.case_parcel_sets force row level security;
alter table vnext_core.case_parcel_set_members enable row level security;
alter table vnext_core.case_parcel_set_members force row level security;

revoke all on table vnext_core.case_parcel_sets from public;
revoke all on table vnext_core.case_parcel_set_members from public;

grant select, insert, update on vnext_core.case_parcel_sets to vnext_api;
grant select, insert, update on vnext_core.case_parcel_set_members to vnext_api;

create policy case_parcel_sets_active_member_select
on vnext_core.case_parcel_sets
for select
to vnext_api
using (
    exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = case_parcel_sets.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member', 'viewer')
    )
);

create policy case_parcel_sets_active_writer_insert
on vnext_core.case_parcel_sets
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = case_parcel_sets.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy case_parcel_sets_active_writer_update
on vnext_core.case_parcel_sets
for update
to vnext_api
using (
    exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = case_parcel_sets.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
)
with check (
    exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = case_parcel_sets.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy case_parcel_set_members_active_member_select
on vnext_core.case_parcel_set_members
for select
to vnext_api
using (
    exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = case_parcel_set_members.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member', 'viewer')
    )
);

create policy case_parcel_set_members_active_writer_insert
on vnext_core.case_parcel_set_members
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = case_parcel_set_members.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy case_parcel_set_members_active_writer_update
on vnext_core.case_parcel_set_members
for update
to vnext_api
using (
    exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = case_parcel_set_members.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
)
with check (
    exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = case_parcel_set_members.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

comment on table vnext_core.case_parcel_sets is
    'One durable parcel-review set per Case. Case review is not official or canonical parcel confirmation and does not change Property Identity.';

comment on table vnext_core.case_parcel_set_members is
    'Ordered Case-local parcel membership and disposition; membership never confirms canonical Property Identity.';
