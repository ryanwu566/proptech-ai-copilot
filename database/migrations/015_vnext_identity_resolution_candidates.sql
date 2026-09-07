-- 015_vnext_identity_resolution_candidates.sql
--
-- Stage 1 Slice 4: immutable identity-resolution runs, provider attempts,
-- ranked candidates and durable conflicts.  Candidate rows are hypotheses,
-- never PropertyEntity rows or confirmation decisions.  This migration adds
-- no public/Data API surface, provider scraping, Case attachment or canonical
-- selection behavior.

alter table vnext_core.cases
    add constraint uq_vnext_cases_workspace_case unique (workspace_id, case_id);

create table vnext_core.identity_resolutions (
    identity_resolution_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    case_id uuid,
    input_type text not null,
    raw_input jsonb not null,
    normalized_input jsonb not null,
    normalized_key text not null,
    normalization_version text not null,
    resolution_status text not null,
    coverage_status text not null,
    coverage jsonb not null,
    ambiguity_status text not null,
    needs_human_confirmation boolean not null default true,
    supersedes_resolution_id uuid,
    version bigint not null default 1,
    requested_by_user_id uuid not null,
    started_at timestamptz not null,
    completed_at timestamptz,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_identity_resolutions_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_identity_resolutions_case
        foreign key (workspace_id, case_id)
        references vnext_core.cases(workspace_id, case_id) on delete restrict,
    constraint fk_vnext_identity_resolutions_requested_by
        foreign key (requested_by_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_identity_resolutions_workspace_resolution
        unique (workspace_id, identity_resolution_id),
    constraint fk_vnext_identity_resolutions_supersedes
        foreign key (workspace_id, supersedes_resolution_id)
        references vnext_core.identity_resolutions(workspace_id, identity_resolution_id)
        on delete restrict,
    constraint ck_vnext_identity_resolutions_input_type
        check (input_type in (
            'address', 'lot_number', 'building_number', 'coordinates', 'map_click'
        )),
    constraint ck_vnext_identity_resolutions_raw_input
        check (jsonb_typeof(raw_input) = 'object' and octet_length(raw_input::text) <= 16384),
    constraint ck_vnext_identity_resolutions_normalized_input
        check (
            jsonb_typeof(normalized_input) = 'object'
            and octet_length(normalized_input::text) <= 16384
        ),
    constraint ck_vnext_identity_resolutions_normalized_key
        check (char_length(normalized_key) between 1 and 512),
    constraint ck_vnext_identity_resolutions_normalization_version
        check (normalization_version ~ '^[a-z0-9][a-z0-9._-]{1,79}$'),
    constraint ck_vnext_identity_resolutions_status
        check (resolution_status in (
            'received', 'normalizing', 'candidates_found', 'ambiguous',
            'partially_resolved', 'unresolved', 'failed', 'superseded'
        )),
    constraint ck_vnext_identity_resolutions_coverage_status
        check (coverage_status in ('known', 'partial', 'unknown', 'unavailable')),
    constraint ck_vnext_identity_resolutions_coverage
        check (jsonb_typeof(coverage) = 'object' and octet_length(coverage::text) <= 16384),
    constraint ck_vnext_identity_resolutions_ambiguity
        check (ambiguity_status in (
            'none', 'multiple_candidates', 'material_conflict',
            'insufficient_evidence', 'provider_limitation'
        )),
    constraint ck_vnext_identity_resolutions_human_gate
        check (needs_human_confirmation),
    constraint ck_vnext_identity_resolutions_version
        check (version = 1),
    constraint ck_vnext_identity_resolutions_lifecycle
        check (
            (
                resolution_status in ('received', 'normalizing')
                and completed_at is null
            )
            or (
                resolution_status in (
                    'candidates_found', 'ambiguous', 'partially_resolved',
                    'unresolved', 'failed', 'superseded'
                )
                and completed_at is not null
                and completed_at >= started_at
            )
        ),
    constraint ck_vnext_identity_resolutions_supersession
        check (
            supersedes_resolution_id is null
            or supersedes_resolution_id <> identity_resolution_id
        ),
    constraint ck_vnext_identity_resolutions_superseded_status
        check (
            resolution_status <> 'superseded'
            or supersedes_resolution_id is not null
        )
);

create index idx_vnext_identity_resolutions_workspace_status_started
    on vnext_core.identity_resolutions (workspace_id, resolution_status, started_at desc);

create index idx_vnext_identity_resolutions_case_started
    on vnext_core.identity_resolutions (workspace_id, case_id, started_at desc)
    where case_id is not null;

create index idx_vnext_identity_resolutions_requested
    on vnext_core.identity_resolutions (workspace_id, requested_by_user_id, started_at desc);

create index idx_vnext_identity_resolutions_supersedes
    on vnext_core.identity_resolutions (workspace_id, supersedes_resolution_id)
    where supersedes_resolution_id is not null;

create table vnext_core.resolution_attempts (
    resolution_attempt_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    identity_resolution_id uuid not null,
    attempt_order integer not null,
    strategy_id text not null,
    provider_id text not null,
    source_id text not null,
    source_type text not null,
    source_environment text not null,
    attempt_status text not null,
    coverage_status text not null,
    coverage jsonb not null,
    result_count integer not null,
    error_category text,
    error_code text,
    error_retryable boolean,
    started_at timestamptz not null,
    completed_at timestamptz not null,
    retrieved_at timestamptz,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_resolution_attempts_resolution
        foreign key (workspace_id, identity_resolution_id)
        references vnext_core.identity_resolutions(workspace_id, identity_resolution_id)
        on delete restrict,
    constraint fk_vnext_resolution_attempts_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_resolution_attempts_workspace_attempt
        unique (workspace_id, resolution_attempt_id),
    constraint uq_vnext_resolution_attempts_order
        unique (identity_resolution_id, attempt_order),
    constraint ck_vnext_resolution_attempts_order
        check (attempt_order between 1 and 64),
    constraint ck_vnext_resolution_attempts_strategy
        check (strategy_id ~ '^[a-z0-9][a-z0-9._-]{1,79}$'),
    constraint ck_vnext_resolution_attempts_provider
        check (provider_id ~ '^[a-z0-9][a-z0-9._-]{1,79}$'),
    constraint ck_vnext_resolution_attempts_source_id
        check (source_id ~ '^[a-z0-9][a-z0-9._-]{1,79}$'),
    constraint ck_vnext_resolution_attempts_source_type
        check (source_type in (
            'official', 'partner', 'user', 'deterministic', 'document', 'demo', 'test'
        )),
    constraint ck_vnext_resolution_attempts_environment
        check (source_environment in ('production', 'demo', 'test')),
    constraint ck_vnext_resolution_attempts_nonproduction_source
        check (
            source_type not in ('demo', 'test')
            or source_environment in ('demo', 'test')
        ),
    constraint ck_vnext_resolution_attempts_status
        check (attempt_status in (
            'available', 'limited', 'unavailable', 'timeout',
            'unsupported', 'no_match', 'error'
        )),
    constraint ck_vnext_resolution_attempts_coverage_status
        check (coverage_status in ('known', 'partial', 'unknown', 'unavailable')),
    constraint ck_vnext_resolution_attempts_coverage
        check (jsonb_typeof(coverage) = 'object' and octet_length(coverage::text) <= 16384),
    constraint ck_vnext_resolution_attempts_result_count
        check (
            result_count between 0 and 1000
            and (attempt_status not in ('available', 'limited') or result_count > 0)
            and (attempt_status in ('available', 'limited') or result_count = 0)
        ),
    constraint ck_vnext_resolution_attempts_error_category
        check (
            (
                attempt_status in ('unavailable', 'timeout', 'unsupported', 'error')
                and error_category in (
                    'provider_unavailable', 'timeout', 'unsupported_input',
                    'provider_rejected', 'invalid_response', 'transport_error',
                    'rate_limited', 'internal_error', 'not_configured'
                )
            )
            or (
                attempt_status in ('available', 'limited', 'no_match')
                and error_category is null
                and error_code is null
                and error_retryable is null
            )
        ),
    constraint ck_vnext_resolution_attempts_error_code
        check (
            error_code is null
            or error_code ~ '^[a-z0-9][a-z0-9._-]{0,79}$'
        ),
    constraint ck_vnext_resolution_attempts_time
        check (completed_at >= started_at),
    constraint ck_vnext_resolution_attempts_retrieval
        check (
            (
                attempt_status in ('available', 'limited', 'no_match')
                and retrieved_at is not null
                and retrieved_at >= started_at
                and retrieved_at <= completed_at
            )
            or (
                attempt_status in ('unavailable', 'timeout', 'unsupported', 'error')
                and retrieved_at is null
            )
        )
);

create index idx_vnext_resolution_attempts_resolution_order
    on vnext_core.resolution_attempts (workspace_id, identity_resolution_id, attempt_order);

create index idx_vnext_resolution_attempts_status_started
    on vnext_core.resolution_attempts (workspace_id, attempt_status, started_at desc);

create table vnext_core.identity_candidates (
    identity_candidate_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    identity_resolution_id uuid not null,
    candidate_type text not null,
    normalized_key text not null,
    normalized_identity jsonb not null,
    display_identity text not null,
    source_id text not null,
    source_type text not null,
    source_environment text not null,
    source_record_id text,
    retrieved_at timestamptz not null,
    confidence numeric(5, 4) not null,
    confidence_method text not null,
    ranking_factors jsonb not null,
    rank integer not null,
    candidate_status text not null,
    coverage_status text not null,
    coverage jsonb not null,
    supporting_evidence_ids uuid[] not null default '{}'::uuid[],
    supporting_reference_ids uuid[] not null default '{}'::uuid[],
    possible_existing_property_entity_id uuid,
    supersedes_candidate_id uuid,
    needs_human_confirmation boolean not null default true,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_identity_candidates_resolution
        foreign key (workspace_id, identity_resolution_id)
        references vnext_core.identity_resolutions(workspace_id, identity_resolution_id)
        on delete restrict,
    constraint fk_vnext_identity_candidates_existing_property
        foreign key (workspace_id, possible_existing_property_entity_id)
        references vnext_core.property_entities(workspace_id, property_entity_id)
        on delete restrict,
    constraint fk_vnext_identity_candidates_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_identity_candidates_workspace_candidate
        unique (workspace_id, identity_candidate_id),
    constraint uq_vnext_identity_candidates_resolution_candidate
        unique (workspace_id, identity_resolution_id, identity_candidate_id),
    constraint fk_vnext_identity_candidates_supersedes
        foreign key (workspace_id, supersedes_candidate_id)
        references vnext_core.identity_candidates(workspace_id, identity_candidate_id)
        on delete restrict,
    constraint uq_vnext_identity_candidates_rank
        unique (identity_resolution_id, rank),
    constraint ck_vnext_identity_candidates_type
        check (candidate_type in (
            'address', 'geo_reference', 'parcel', 'building', 'composite_property'
        )),
    constraint ck_vnext_identity_candidates_normalized_key
        check (char_length(normalized_key) between 1 and 512),
    constraint ck_vnext_identity_candidates_normalized_identity
        check (
            jsonb_typeof(normalized_identity) = 'object'
            and octet_length(normalized_identity::text) <= 16384
        ),
    constraint ck_vnext_identity_candidates_display
        check (char_length(btrim(display_identity)) between 1 and 512),
    constraint ck_vnext_identity_candidates_source_id
        check (source_id ~ '^[a-z0-9][a-z0-9._-]{1,79}$'),
    constraint ck_vnext_identity_candidates_source_type
        check (source_type in (
            'official', 'partner', 'user', 'deterministic', 'document', 'demo', 'test'
        )),
    constraint ck_vnext_identity_candidates_environment
        check (source_environment in ('production', 'demo', 'test')),
    constraint ck_vnext_identity_candidates_nonproduction_source
        check (
            source_type not in ('demo', 'test')
            or source_environment in ('demo', 'test')
        ),
    constraint ck_vnext_identity_candidates_source_record
        check (source_record_id is null or char_length(source_record_id) between 1 and 240),
    constraint ck_vnext_identity_candidates_confidence
        check (confidence between 0 and 1),
    constraint ck_vnext_identity_candidates_confidence_method
        check (char_length(confidence_method) between 1 and 120),
    constraint ck_vnext_identity_candidates_ranking_factors
        check (
            jsonb_typeof(ranking_factors) = 'object'
            and octet_length(ranking_factors::text) <= 16384
        ),
    constraint ck_vnext_identity_candidates_rank
        check (rank between 1 and 1000),
    constraint ck_vnext_identity_candidates_status
        check (candidate_status in (
            'proposed', 'plausible', 'conflicting',
            'insufficient', 'rejected', 'superseded'
        )),
    constraint ck_vnext_identity_candidates_coverage_status
        check (coverage_status in ('known', 'partial', 'unknown', 'unavailable')),
    constraint ck_vnext_identity_candidates_coverage
        check (jsonb_typeof(coverage) = 'object' and octet_length(coverage::text) <= 16384),
    constraint ck_vnext_identity_candidates_evidence_count
        check (cardinality(supporting_evidence_ids) between 0 and 32),
    constraint ck_vnext_identity_candidates_reference_count
        check (cardinality(supporting_reference_ids) between 0 and 32),
    constraint ck_vnext_identity_candidates_supersession
        check (
            supersedes_candidate_id is null
            or supersedes_candidate_id <> identity_candidate_id
        ),
    constraint ck_vnext_identity_candidates_superseded_status
        check (
            candidate_status <> 'superseded'
            or supersedes_candidate_id is not null
        ),
    constraint ck_vnext_identity_candidates_human_gate
        check (needs_human_confirmation)
);

create index idx_vnext_identity_candidates_resolution_rank
    on vnext_core.identity_candidates (workspace_id, identity_resolution_id, rank);

create index idx_vnext_identity_candidates_workspace_type_status
    on vnext_core.identity_candidates (workspace_id, candidate_type, candidate_status);

create index idx_vnext_identity_candidates_source_record
    on vnext_core.identity_candidates (workspace_id, source_id, source_record_id)
    where source_record_id is not null;

create index idx_vnext_identity_candidates_existing_property
    on vnext_core.identity_candidates (workspace_id, possible_existing_property_entity_id)
    where possible_existing_property_entity_id is not null;

create index idx_vnext_identity_candidates_evidence
    on vnext_core.identity_candidates using gin (supporting_evidence_ids);

create index idx_vnext_identity_candidates_references
    on vnext_core.identity_candidates using gin (supporting_reference_ids);

create table vnext_core.identity_conflicts (
    identity_conflict_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    identity_resolution_id uuid not null,
    left_candidate_id uuid not null,
    right_candidate_id uuid,
    related_identity_reference_id uuid,
    related_evidence_id uuid,
    related_property_entity_id uuid,
    conflict_type text not null,
    severity text not null,
    source_basis jsonb not null,
    conflict_basis jsonb not null,
    resolution_state text not null,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_identity_conflicts_resolution
        foreign key (workspace_id, identity_resolution_id)
        references vnext_core.identity_resolutions(workspace_id, identity_resolution_id)
        on delete restrict,
    constraint fk_vnext_identity_conflicts_left_candidate
        foreign key (workspace_id, identity_resolution_id, left_candidate_id)
        references vnext_core.identity_candidates(
            workspace_id, identity_resolution_id, identity_candidate_id
        ) on delete restrict,
    constraint fk_vnext_identity_conflicts_right_candidate
        foreign key (workspace_id, identity_resolution_id, right_candidate_id)
        references vnext_core.identity_candidates(
            workspace_id, identity_resolution_id, identity_candidate_id
        ) on delete restrict,
    constraint fk_vnext_identity_conflicts_reference
        foreign key (workspace_id, related_identity_reference_id)
        references vnext_core.property_identity_references(workspace_id, identity_reference_id)
        on delete restrict,
    constraint fk_vnext_identity_conflicts_evidence
        foreign key (workspace_id, related_evidence_id)
        references vnext_core.evidence_items(workspace_id, evidence_id)
        on delete restrict,
    constraint fk_vnext_identity_conflicts_property
        foreign key (workspace_id, related_property_entity_id)
        references vnext_core.property_entities(workspace_id, property_entity_id)
        on delete restrict,
    constraint fk_vnext_identity_conflicts_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_identity_conflicts_workspace_conflict
        unique (workspace_id, identity_conflict_id),
    constraint ck_vnext_identity_conflicts_distinct_candidates
        check (right_candidate_id is null or right_candidate_id <> left_candidate_id),
    constraint ck_vnext_identity_conflicts_resource_basis
        check (
            right_candidate_id is not null
            or related_identity_reference_id is not null
            or related_evidence_id is not null
            or related_property_entity_id is not null
        ),
    constraint ck_vnext_identity_conflicts_type
        check (conflict_type in (
            'normalized_identity_disagreement', 'identifier_disagreement',
            'address_parcel_mismatch', 'coordinate_parcel_mismatch',
            'provider_disagreement', 'cardinality_disagreement',
            'temporal_conflict', 'coverage_limitation', 'existing_property_conflict'
        )),
    constraint ck_vnext_identity_conflicts_severity
        check (severity in ('information', 'warning', 'blocking')),
    constraint ck_vnext_identity_conflicts_source_basis
        check (
            jsonb_typeof(source_basis) = 'object'
            and octet_length(source_basis::text) <= 16384
        ),
    constraint ck_vnext_identity_conflicts_basis
        check (
            jsonb_typeof(conflict_basis) = 'object'
            and octet_length(conflict_basis::text) <= 16384
        ),
    constraint ck_vnext_identity_conflicts_resolution_state
        check (resolution_state in ('open', 'requires_review', 'resolved', 'superseded'))
);

create index idx_vnext_identity_conflicts_resolution_state
    on vnext_core.identity_conflicts (workspace_id, identity_resolution_id, resolution_state);

create index idx_vnext_identity_conflicts_candidates
    on vnext_core.identity_conflicts (
        workspace_id, left_candidate_id, right_candidate_id
    );

create function vnext_private.guard_identity_candidate_support()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
    expected_count integer;
    actual_count integer;
begin
    select count(distinct item) into expected_count
    from unnest(new.supporting_evidence_ids) as item;
    if expected_count <> cardinality(new.supporting_evidence_ids) then
        raise exception using errcode = '23514', message = 'vnext_candidate_evidence_ids_must_be_unique';
    end if;

    select count(*) into actual_count
    from vnext_core.evidence_items evidence
    where evidence.workspace_id = new.workspace_id
      and evidence.evidence_id = any(new.supporting_evidence_ids);
    if actual_count <> cardinality(new.supporting_evidence_ids) then
        raise exception using errcode = '23503', message = 'vnext_candidate_evidence_scope_invalid';
    end if;

    select count(distinct item) into expected_count
    from unnest(new.supporting_reference_ids) as item;
    if expected_count <> cardinality(new.supporting_reference_ids) then
        raise exception using errcode = '23514', message = 'vnext_candidate_reference_ids_must_be_unique';
    end if;

    select count(*) into actual_count
    from vnext_core.property_identity_references reference
    where reference.workspace_id = new.workspace_id
      and reference.identity_reference_id = any(new.supporting_reference_ids);
    if actual_count <> cardinality(new.supporting_reference_ids) then
        raise exception using errcode = '23503', message = 'vnext_candidate_reference_scope_invalid';
    end if;

    return new;
end
$$;

revoke all on function vnext_private.guard_identity_candidate_support() from public;

create trigger trg_vnext_identity_candidates_support_scope
before insert on vnext_core.identity_candidates
for each row execute function vnext_private.guard_identity_candidate_support();

create function vnext_private.guard_identity_resolution_append_only()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    raise exception using errcode = '42501', message = 'vnext_identity_resolution_record_is_immutable';
end
$$;

revoke all on function vnext_private.guard_identity_resolution_append_only() from public;

create trigger trg_vnext_identity_resolutions_append_only
before update or delete on vnext_core.identity_resolutions
for each row execute function vnext_private.guard_identity_resolution_append_only();

create trigger trg_vnext_resolution_attempts_append_only
before update or delete on vnext_core.resolution_attempts
for each row execute function vnext_private.guard_identity_resolution_append_only();

create trigger trg_vnext_identity_candidates_append_only
before update or delete on vnext_core.identity_candidates
for each row execute function vnext_private.guard_identity_resolution_append_only();

create trigger trg_vnext_identity_conflicts_append_only
before update or delete on vnext_core.identity_conflicts
for each row execute function vnext_private.guard_identity_resolution_append_only();

alter table vnext_core.identity_resolutions enable row level security;
alter table vnext_core.identity_resolutions force row level security;
alter table vnext_core.resolution_attempts enable row level security;
alter table vnext_core.resolution_attempts force row level security;
alter table vnext_core.identity_candidates enable row level security;
alter table vnext_core.identity_candidates force row level security;
alter table vnext_core.identity_conflicts enable row level security;
alter table vnext_core.identity_conflicts force row level security;

revoke all on table vnext_core.identity_resolutions from public;
revoke all on table vnext_core.resolution_attempts from public;
revoke all on table vnext_core.identity_candidates from public;
revoke all on table vnext_core.identity_conflicts from public;

grant select, insert on vnext_core.identity_resolutions to vnext_api;
grant select, insert on vnext_core.resolution_attempts to vnext_api;
grant select, insert on vnext_core.identity_candidates to vnext_api;
grant select, insert on vnext_core.identity_conflicts to vnext_api;

create policy identity_resolutions_active_member_select
on vnext_core.identity_resolutions
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = identity_resolutions.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy identity_resolutions_active_writer_insert
on vnext_core.identity_resolutions
for insert
to vnext_api
with check (
    requested_by_user_id = (select auth.uid())
    and needs_human_confirmation
    and resolution_status <> 'superseded'
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = identity_resolutions.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy resolution_attempts_active_member_select
on vnext_core.resolution_attempts
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = resolution_attempts.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy resolution_attempts_active_writer_insert
on vnext_core.resolution_attempts
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and source_type in ('user', 'deterministic', 'demo', 'test')
    and exists (
        select 1 from vnext_core.identity_resolutions resolution
        where resolution.workspace_id = resolution_attempts.workspace_id
          and resolution.identity_resolution_id = resolution_attempts.identity_resolution_id
          and resolution.requested_by_user_id = (select auth.uid())
    )
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = resolution_attempts.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy identity_candidates_active_member_select
on vnext_core.identity_candidates
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = identity_candidates.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy identity_candidates_active_writer_insert
on vnext_core.identity_candidates
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and source_type in ('user', 'deterministic', 'demo', 'test')
    and needs_human_confirmation
    and exists (
        select 1 from vnext_core.identity_resolutions resolution
        where resolution.workspace_id = identity_candidates.workspace_id
          and resolution.identity_resolution_id = identity_candidates.identity_resolution_id
          and resolution.requested_by_user_id = (select auth.uid())
    )
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = identity_candidates.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy identity_conflicts_active_member_select
on vnext_core.identity_conflicts
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = identity_conflicts.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy identity_conflicts_active_writer_insert
on vnext_core.identity_conflicts
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and resolution_state in ('open', 'requires_review')
    and exists (
        select 1 from vnext_core.identity_resolutions resolution
        where resolution.workspace_id = identity_conflicts.workspace_id
          and resolution.identity_resolution_id = identity_conflicts.identity_resolution_id
          and resolution.requested_by_user_id = (select auth.uid())
    )
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = identity_conflicts.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

comment on table vnext_core.identity_resolutions is
    'Immutable snapshots of one identity-resolution run. Candidate generation success is not human confirmation.';
comment on table vnext_core.resolution_attempts is
    'Bounded provider/strategy outcomes, including safe failures and coverage, without raw provider bodies.';
comment on table vnext_core.identity_candidates is
    'Ranked identity hypotheses with provenance. A candidate is never a canonical PropertyEntity.';
comment on table vnext_core.identity_conflicts is
    'Durable competing-hypothesis conflicts; both candidates remain immutable and attributable.';
