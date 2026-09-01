-- 017_vnext_legacy_saved_case_import.sql
--
-- Stage 1 Slice 7: explicit SavedCase v1 COPY import metadata. Incoming
-- browser payloads and raw client identifiers are deliberately not retained.

create table vnext_private.legacy_case_imports (
    legacy_case_import_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    case_id uuid not null,
    actor_user_id uuid not null,
    legacy_format text not null,
    legacy_client_id_hash text not null,
    schema_version integer not null,
    import_mode text not null,
    imported_at timestamptz not null default clock_timestamp(),
    client_created_at timestamptz,
    client_updated_at timestamptz,
    accepted_field_classes text[] not null default '{}'::text[],
    dropped_field_classes text[] not null default '{}'::text[],
    warnings text[] not null default '{}'::text[],
    idempotency_record_id uuid not null,
    request_id text not null,
    constraint fk_vnext_legacy_import_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_legacy_import_case
        foreign key (workspace_id, case_id)
        references vnext_core.cases(workspace_id, case_id) on delete restrict,
    constraint fk_vnext_legacy_import_actor
        foreign key (actor_user_id) references auth.users(id) on delete restrict,
    constraint fk_vnext_legacy_import_idempotency
        foreign key (workspace_id, idempotency_record_id)
        references vnext_private.idempotency_records(
            workspace_id, idempotency_record_id
        ) on delete restrict,
    constraint uq_vnext_legacy_import_case
        unique (workspace_id, case_id),
    constraint uq_vnext_legacy_import_idempotency
        unique (workspace_id, actor_user_id, idempotency_record_id),
    constraint uq_vnext_legacy_import_scoped_client
        unique (workspace_id, actor_user_id, legacy_format, legacy_client_id_hash),
    constraint ck_vnext_legacy_import_format
        check (legacy_format = 'saved_case_v1'),
    constraint ck_vnext_legacy_import_client_hash
        check (legacy_client_id_hash ~ '^[0-9a-f]{64}$'),
    constraint ck_vnext_legacy_import_schema_version
        check (schema_version = 1),
    constraint ck_vnext_legacy_import_mode
        check (import_mode = 'copy'),
    constraint ck_vnext_legacy_import_request
        check (char_length(request_id) between 1 and 128),
    constraint ck_vnext_legacy_import_accepted
        check (
            cardinality(accepted_field_classes) between 1 and 18
            and array_position(accepted_field_classes, null) is null
            and accepted_field_classes <@ array[
                'title', 'legacy_timestamps', 'workflow_snapshot', 'address_input',
                'property_inputs', 'property_search_summary', 'valuation_evidence_summary',
                'valuation_summary', 'trend_snapshot', 'market_snapshot', 'loan_artifact',
                'holding_cost_artifact', 'location_summary', 'terrain_reference',
                'risk_presentation', 'tax_artifact', 'report_activity', 'journey_context'
            ]::text[]
        ),
    constraint ck_vnext_legacy_import_dropped
        check (
            cardinality(dropped_field_classes) between 0 and 9
            and array_position(dropped_field_classes, null) is null
            and dropped_field_classes <@ array[
                'legacy_client_payload_id', 'unsupported_fields', 'raw_provider_payload',
                'exact_coordinates', 'raw_comparable_rows', 'private_storage_paths',
                'corrupt_optional_section', 'oversized_fields', 'provider_internals'
            ]::text[]
        ),
    constraint ck_vnext_legacy_import_warnings
        check (
            cardinality(warnings) between 0 and 15
            and array_position(warnings, null) is null
            and warnings <@ array[
                'address_requires_resolution', 'missing_address', 'missing_valuation',
                'unsupported_fields_dropped', 'raw_provider_fields_dropped',
                'exact_coordinates_dropped', 'raw_comparable_rows_dropped',
                'private_storage_paths_dropped', 'corrupt_optional_section_dropped',
                'oversized_fields_dropped', 'legacy_timestamps_inconsistent',
                'legacy_snapshot_requires_revalidation', 'terrain_reference_only',
                'terrain_safe_conclusion_blocked', 'risk_presentation_not_authoritative'
            ]::text[]
        )
);

create index idx_vnext_legacy_case_imports_actor
on vnext_private.legacy_case_imports (actor_user_id);

create function vnext_private.guard_legacy_case_import()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if not exists (
        select 1
        from vnext_core.cases imported_case
        where imported_case.workspace_id = new.workspace_id
          and imported_case.case_id = new.case_id
          and imported_case.created_by_user_id = new.actor_user_id
          and imported_case.identity_status = 'legacy_unverified'
          and imported_case.version = 1
    ) then
        raise exception using errcode = '23514', message = 'vnext_legacy_import_case_invalid';
    end if;
    if not exists (
        select 1
        from vnext_private.idempotency_records idempotency
        where idempotency.workspace_id = new.workspace_id
          and idempotency.actor_user_id = new.actor_user_id
          and idempotency.idempotency_record_id = new.idempotency_record_id
          and idempotency.http_method = 'POST'
          and idempotency.canonical_route = '/v1/cases/import-legacy'
          and idempotency.operation_status = 'pending'
    ) then
        raise exception using errcode = '23514', message = 'vnext_legacy_import_idempotency_invalid';
    end if;
    if exists (
        select 1
        from vnext_core.case_property_links link
        where link.workspace_id = new.workspace_id
          and link.case_id = new.case_id
    ) then
        raise exception using errcode = '23514', message = 'vnext_legacy_import_case_attachment_forbidden';
    end if;
    return new;
end
$$;

revoke all on function vnext_private.guard_legacy_case_import() from public;

create trigger trg_vnext_legacy_case_import_guard
before insert on vnext_private.legacy_case_imports
for each row execute function vnext_private.guard_legacy_case_import();

create trigger trg_vnext_legacy_case_import_append_only
before update or delete on vnext_private.legacy_case_imports
for each row execute function vnext_private.guard_slice6_append_only();

alter table vnext_private.legacy_case_imports enable row level security;
alter table vnext_private.legacy_case_imports force row level security;

revoke all on table vnext_private.legacy_case_imports from public;
grant select, insert on vnext_private.legacy_case_imports to vnext_api;

create policy legacy_case_imports_actor_select
on vnext_private.legacy_case_imports
for select
to vnext_api
using (
    actor_user_id = (select auth.uid())
    and exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = legacy_case_imports.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy legacy_case_imports_actor_insert
on vnext_private.legacy_case_imports
for insert
to vnext_api
with check (
    actor_user_id = (select auth.uid())
    and exists (
        select 1
        from vnext_core.workspace_members member
        where member.workspace_id = legacy_case_imports.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

comment on table vnext_private.legacy_case_imports is
    'Append-only bounded SavedCase v1 COPY import records. Raw payloads and raw browser IDs are excluded.';
