-- 016_vnext_identity_confirmation_case_links.sql
--
-- Stage 1 Slice 6: explicit human identity decisions, confirmed graph edges,
-- and append-only Case-to-Property attachment history. Immutable resolution
-- and candidate snapshots remain unchanged. Confirmation is owner/admin only
-- and remains separate from Case attachment.

alter table vnext_private.idempotency_records
    add constraint uq_vnext_idempotency_workspace_record
    unique (workspace_id, idempotency_record_id);

alter table vnext_private.idempotency_records
    add column response_error_code text;

alter table vnext_private.idempotency_records
    add constraint ck_vnext_idempotency_response_error_code
    check (
        response_error_code is null
        or (
            operation_status = 'failed'
            and response_error_code ~ '^[a-z][a-z0-9._-]{2,79}$'
        )
    );

create table vnext_core.identity_decisions (
    identity_decision_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    identity_resolution_id uuid not null,
    identity_candidate_id uuid,
    property_entity_id uuid,
    materialized_identity_reference_id uuid,
    primary_evidence_id uuid,
    decision_type text not null,
    decision_reason text,
    reason_code text,
    resolution_version_observed bigint not null,
    decision_version bigint not null,
    candidate_type_snapshot text,
    candidate_status_snapshot text,
    confidence_snapshot numeric(5, 4),
    confidence_method_snapshot text,
    coverage_status_snapshot text not null,
    coverage_snapshot jsonb not null,
    supporting_evidence_ids_snapshot uuid[] not null default '{}'::uuid[],
    supporting_reference_ids_snapshot uuid[] not null default '{}'::uuid[],
    source_id_snapshot text,
    source_type_snapshot text,
    source_environment_snapshot text,
    source_record_id_snapshot text,
    created_new_property boolean,
    created_new_reference boolean,
    actor_user_id uuid not null,
    request_id text not null,
    idempotency_record_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_identity_decisions_resolution
        foreign key (workspace_id, identity_resolution_id)
        references vnext_core.identity_resolutions(workspace_id, identity_resolution_id)
        on delete restrict,
    constraint fk_vnext_identity_decisions_candidate
        foreign key (workspace_id, identity_resolution_id, identity_candidate_id)
        references vnext_core.identity_candidates(
            workspace_id, identity_resolution_id, identity_candidate_id
        ) on delete restrict,
    constraint fk_vnext_identity_decisions_property
        foreign key (workspace_id, property_entity_id)
        references vnext_core.property_entities(workspace_id, property_entity_id)
        on delete restrict,
    constraint fk_vnext_identity_decisions_reference
        foreign key (workspace_id, materialized_identity_reference_id)
        references vnext_core.property_identity_references(
            workspace_id, identity_reference_id
        ) on delete restrict,
    constraint fk_vnext_identity_decisions_evidence
        foreign key (workspace_id, primary_evidence_id)
        references vnext_core.evidence_items(workspace_id, evidence_id)
        on delete restrict,
    constraint fk_vnext_identity_decisions_actor
        foreign key (actor_user_id) references auth.users(id) on delete restrict,
    constraint fk_vnext_identity_decisions_idempotency
        foreign key (workspace_id, idempotency_record_id)
        references vnext_private.idempotency_records(
            workspace_id, idempotency_record_id
        ) on delete restrict,
    constraint uq_vnext_identity_decisions_workspace_decision
        unique (workspace_id, identity_decision_id),
    constraint uq_vnext_identity_decisions_resolution_version
        unique (workspace_id, identity_resolution_id, decision_version),
    constraint uq_vnext_identity_decisions_idempotency
        unique (idempotency_record_id),
    constraint ck_vnext_identity_decisions_type
        check (decision_type in ('confirmed', 'candidate_rejected', 'resolution_rejected')),
    constraint ck_vnext_identity_decisions_reason
        check (
            (
                decision_type = 'confirmed'
                and decision_reason is not null
                and char_length(btrim(decision_reason)) between 8 and 1000
                and reason_code is null
            )
            or (
                decision_type in ('candidate_rejected', 'resolution_rejected')
                and decision_reason is null
                and reason_code is not null
                and reason_code ~ '^[a-z][a-z0-9._-]{2,79}$'
            )
        ),
    constraint ck_vnext_identity_decisions_versions
        check (
            resolution_version_observed >= 1
            and decision_version = resolution_version_observed + 1
        ),
    constraint ck_vnext_identity_decisions_candidate_type
        check (
            candidate_type_snapshot is null
            or candidate_type_snapshot in (
                'address', 'geo_reference', 'parcel', 'building', 'composite_property'
            )
        ),
    constraint ck_vnext_identity_decisions_candidate_status
        check (
            candidate_status_snapshot is null
            or candidate_status_snapshot in (
                'proposed', 'plausible', 'conflicting',
                'insufficient', 'rejected', 'superseded'
            )
        ),
    constraint ck_vnext_identity_decisions_confidence
        check (
            confidence_snapshot is null
            or (
                confidence_snapshot between 0 and 1
                and confidence_method_snapshot is not null
            )
        ),
    constraint ck_vnext_identity_decisions_confidence_method
        check (
            confidence_method_snapshot is null
            or char_length(confidence_method_snapshot) between 1 and 120
        ),
    constraint ck_vnext_identity_decisions_coverage_status
        check (coverage_status_snapshot in ('known', 'partial', 'unknown', 'unavailable')),
    constraint ck_vnext_identity_decisions_coverage
        check (
            jsonb_typeof(coverage_snapshot) = 'object'
            and octet_length(coverage_snapshot::text) <= 16384
        ),
    constraint ck_vnext_identity_decisions_evidence_count
        check (cardinality(supporting_evidence_ids_snapshot) between 0 and 32),
    constraint ck_vnext_identity_decisions_reference_count
        check (cardinality(supporting_reference_ids_snapshot) between 0 and 32),
    constraint ck_vnext_identity_decisions_source_id
        check (
            source_id_snapshot is null
            or source_id_snapshot ~ '^[a-z0-9][a-z0-9._-]{1,79}$'
        ),
    constraint ck_vnext_identity_decisions_source_type
        check (
            source_type_snapshot is null
            or source_type_snapshot in (
                'official', 'partner', 'user', 'deterministic', 'document', 'demo', 'test'
            )
        ),
    constraint ck_vnext_identity_decisions_source_environment
        check (
            source_environment_snapshot is null
            or source_environment_snapshot in ('production', 'demo', 'test')
        ),
    constraint ck_vnext_identity_decisions_source_record
        check (
            source_record_id_snapshot is null
            or char_length(source_record_id_snapshot) between 1 and 240
        ),
    constraint ck_vnext_identity_decisions_request_id
        check (char_length(request_id) between 1 and 128),
    constraint ck_vnext_identity_decisions_shape
        check (
            (
                decision_type = 'confirmed'
                and identity_candidate_id is not null
                and property_entity_id is not null
                and materialized_identity_reference_id is not null
                and primary_evidence_id is not null
                and candidate_type_snapshot is not null
                and candidate_status_snapshot is not null
                and confidence_snapshot is not null
                and confidence_method_snapshot is not null
                and source_id_snapshot is not null
                and source_type_snapshot is not null
                and source_environment_snapshot is not null
                and created_new_property is not null
                and created_new_reference is not null
            )
            or (
                decision_type = 'candidate_rejected'
                and identity_candidate_id is not null
                and property_entity_id is null
                and materialized_identity_reference_id is null
                and primary_evidence_id is null
                and candidate_type_snapshot is not null
                and candidate_status_snapshot is not null
                and confidence_snapshot is not null
                and confidence_method_snapshot is not null
                and source_id_snapshot is not null
                and source_type_snapshot is not null
                and source_environment_snapshot is not null
                and created_new_property is null
                and created_new_reference is null
            )
            or (
                decision_type = 'resolution_rejected'
                and identity_candidate_id is null
                and property_entity_id is null
                and materialized_identity_reference_id is null
                and primary_evidence_id is null
                and candidate_type_snapshot is null
                and candidate_status_snapshot is null
                and confidence_snapshot is null
                and confidence_method_snapshot is null
                and source_id_snapshot is null
                and source_type_snapshot is null
                and source_environment_snapshot is null
                and source_record_id_snapshot is null
                and created_new_property is null
                and created_new_reference is null
                and cardinality(supporting_evidence_ids_snapshot) = 0
                and cardinality(supporting_reference_ids_snapshot) = 0
            )
        )
);

create unique index uq_vnext_identity_decisions_confirmed_resolution
    on vnext_core.identity_decisions (workspace_id, identity_resolution_id)
    where decision_type = 'confirmed';

create unique index uq_vnext_identity_decisions_rejected_resolution
    on vnext_core.identity_decisions (workspace_id, identity_resolution_id)
    where decision_type = 'resolution_rejected';

create unique index uq_vnext_identity_decisions_rejected_candidate
    on vnext_core.identity_decisions (
        workspace_id, identity_resolution_id, identity_candidate_id
    ) where decision_type = 'candidate_rejected';

create index idx_vnext_identity_decisions_resolution_created
    on vnext_core.identity_decisions (
        workspace_id, identity_resolution_id, decision_version, created_at
    );

create index idx_vnext_identity_decisions_property_confirmed
    on vnext_core.identity_decisions (workspace_id, property_entity_id, created_at desc)
    where decision_type = 'confirmed';

create function vnext_private.guard_identity_decision()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
    selected_resolution vnext_core.identity_resolutions%rowtype;
    selected_candidate vnext_core.identity_candidates%rowtype;
    selected_property vnext_core.property_entities%rowtype;
    selected_reference vnext_core.property_identity_references%rowtype;
    current_version bigint;
    invalid_count integer;
begin
    select * into selected_resolution
    from vnext_core.identity_resolutions resolution
    where resolution.workspace_id = new.workspace_id
      and resolution.identity_resolution_id = new.identity_resolution_id;
    if not found then
        raise exception using errcode = '23503', message = 'vnext_identity_decision_resolution_invalid';
    end if;

    select selected_resolution.version + count(*) into current_version
    from vnext_core.identity_decisions decision
    where decision.workspace_id = new.workspace_id
      and decision.identity_resolution_id = new.identity_resolution_id;
    if new.resolution_version_observed <> current_version
       or new.decision_version <> current_version + 1 then
        raise exception using errcode = '40001', message = 'vnext_identity_decision_version_conflict';
    end if;

    if exists (
        select 1 from vnext_core.identity_decisions decision
        where decision.workspace_id = new.workspace_id
          and decision.identity_resolution_id = new.identity_resolution_id
          and decision.decision_type in ('confirmed', 'resolution_rejected')
    ) then
        raise exception using errcode = '40001', message = 'vnext_identity_decision_is_terminal';
    end if;

    if not exists (
        select 1 from vnext_private.idempotency_records idempotency
        where idempotency.workspace_id = new.workspace_id
          and idempotency.idempotency_record_id = new.idempotency_record_id
          and idempotency.actor_user_id = new.actor_user_id
          and idempotency.http_method = 'POST'
          and idempotency.operation_status = 'pending'
    ) then
        raise exception using errcode = '23514', message = 'vnext_identity_decision_idempotency_invalid';
    end if;

    if new.decision_type = 'resolution_rejected' then
        if new.coverage_status_snapshot <> selected_resolution.coverage_status
           or new.coverage_snapshot <> selected_resolution.coverage then
            raise exception using errcode = '23514', message = 'vnext_identity_decision_snapshot_invalid';
        end if;
        return new;
    end if;

    select * into selected_candidate
    from vnext_core.identity_candidates candidate
    where candidate.workspace_id = new.workspace_id
      and candidate.identity_resolution_id = new.identity_resolution_id
      and candidate.identity_candidate_id = new.identity_candidate_id;
    if not found then
        raise exception using errcode = '23503', message = 'vnext_identity_decision_candidate_invalid';
    end if;

    if new.candidate_type_snapshot <> selected_candidate.candidate_type
       or new.candidate_status_snapshot <> selected_candidate.candidate_status
       or new.confidence_snapshot <> selected_candidate.confidence
       or new.confidence_method_snapshot <> selected_candidate.confidence_method
       or new.coverage_status_snapshot <> selected_candidate.coverage_status
       or new.coverage_snapshot <> selected_candidate.coverage
       or new.supporting_evidence_ids_snapshot <> selected_candidate.supporting_evidence_ids
       or new.supporting_reference_ids_snapshot <> selected_candidate.supporting_reference_ids
       or new.source_id_snapshot <> selected_candidate.source_id
       or new.source_type_snapshot <> selected_candidate.source_type
       or new.source_environment_snapshot <> selected_candidate.source_environment
       or new.source_record_id_snapshot is distinct from selected_candidate.source_record_id then
        raise exception using errcode = '23514', message = 'vnext_identity_decision_snapshot_invalid';
    end if;

    if exists (
        select 1 from vnext_core.identity_decisions decision
        where decision.workspace_id = new.workspace_id
          and decision.identity_resolution_id = new.identity_resolution_id
          and decision.identity_candidate_id = new.identity_candidate_id
          and decision.decision_type = 'candidate_rejected'
    ) then
        raise exception using errcode = '40001', message = 'vnext_identity_candidate_already_rejected';
    end if;

    if new.decision_type = 'candidate_rejected' then
        return new;
    end if;

    if selected_resolution.resolution_status not in (
        'candidates_found', 'ambiguous', 'partially_resolved'
    ) or not selected_resolution.needs_human_confirmation
       or selected_candidate.candidate_status in ('insufficient', 'rejected', 'superseded')
       or not selected_candidate.needs_human_confirmation
       or selected_candidate.candidate_type = 'composite_property' then
        raise exception using errcode = '23514', message = 'vnext_identity_candidate_not_confirmable';
    end if;

    if selected_candidate.coverage_status <> 'known'
       or cardinality(selected_candidate.supporting_evidence_ids) = 0
       or selected_candidate.source_type in ('demo', 'test')
       or selected_candidate.source_environment <> 'production' then
        raise exception using errcode = '23514', message = 'vnext_identity_candidate_evidence_incomplete';
    end if;

    select count(*) into invalid_count
    from vnext_core.evidence_items evidence
    where evidence.workspace_id = new.workspace_id
      and evidence.evidence_id = any(selected_candidate.supporting_evidence_ids)
      and (
          evidence.coverage_status <> 'known'
          or evidence.evidence_status not in ('available', 'user_provided')
          or evidence.quality_status <> 'passed'
          or evidence.license_status not in ('approved', 'not_applicable')
          or (evidence.expires_at is not null and evidence.expires_at <= new.created_at)
      );
    if invalid_count <> 0 then
        raise exception using errcode = '23514', message = 'vnext_identity_candidate_evidence_invalid';
    end if;

    select count(*) into invalid_count
    from vnext_core.evidence_items evidence
    where evidence.workspace_id = new.workspace_id
      and evidence.evidence_id = any(selected_candidate.supporting_evidence_ids);
    if invalid_count <> cardinality(selected_candidate.supporting_evidence_ids)
       or not new.primary_evidence_id = any(selected_candidate.supporting_evidence_ids) then
        raise exception using errcode = '23503', message = 'vnext_identity_candidate_evidence_scope_invalid';
    end if;

    if exists (
        select 1 from vnext_core.identity_conflicts conflict
        where conflict.workspace_id = new.workspace_id
          and conflict.identity_resolution_id = new.identity_resolution_id
          and conflict.severity = 'blocking'
          and conflict.resolution_state in ('open', 'requires_review')
          and (
              conflict.left_candidate_id = new.identity_candidate_id
              or conflict.right_candidate_id = new.identity_candidate_id
          )
    ) then
        raise exception using errcode = '23514', message = 'vnext_identity_candidate_blocking_conflict';
    end if;

    select * into selected_property
    from vnext_core.property_entities property
    where property.workspace_id = new.workspace_id
      and property.property_entity_id = new.property_entity_id;
    if not found then
        raise exception using errcode = '23503', message = 'vnext_identity_decision_property_invalid';
    end if;
    if selected_candidate.possible_existing_property_entity_id is not null then
        if new.created_new_property
           or new.property_entity_id <> selected_candidate.possible_existing_property_entity_id then
            raise exception using errcode = '23514', message = 'vnext_identity_existing_property_mismatch';
        end if;
    elsif not new.created_new_property
       or selected_property.created_by_user_id <> new.actor_user_id
       or selected_property.created_at < transaction_timestamp() then
        raise exception using errcode = '23514', message = 'vnext_identity_new_property_required';
    end if;

    select * into selected_reference
    from vnext_core.property_identity_references reference
    where reference.workspace_id = new.workspace_id
      and reference.identity_reference_id = new.materialized_identity_reference_id;
    if not found
       or selected_reference.reference_type <> selected_candidate.candidate_type
       or selected_reference.normalized_key <> selected_candidate.normalized_key
       or selected_reference.display_value <> selected_candidate.display_identity
       or selected_reference.source_id <> selected_candidate.source_id
       or selected_reference.source_type <> selected_candidate.source_type
       or selected_reference.source_environment <> selected_candidate.source_environment
       or selected_reference.source_record_id is distinct from selected_candidate.source_record_id
       or selected_reference.confidence is distinct from selected_candidate.confidence
       or selected_reference.confidence_method is distinct from selected_candidate.confidence_method
       or selected_reference.reference_status not in ('observed', 'unverified')
       or selected_reference.valid_from is not null
          and selected_reference.valid_from > new.created_at
       or selected_reference.valid_to is not null and selected_reference.valid_to <= new.created_at then
        raise exception using errcode = '23514', message = 'vnext_identity_reference_mismatch';
    end if;
    if new.created_new_reference then
        if selected_reference.created_by_user_id <> new.actor_user_id
           or selected_reference.created_at < transaction_timestamp() then
            raise exception using errcode = '23514', message = 'vnext_identity_reference_creation_invalid';
        end if;
    elsif not new.materialized_identity_reference_id = any(
        selected_candidate.supporting_reference_ids
    ) then
        raise exception using errcode = '23514', message = 'vnext_identity_reference_reuse_invalid';
    end if;

    return new;
end
$$;

revoke all on function vnext_private.guard_identity_decision() from public;

create trigger trg_vnext_identity_decisions_guard
before insert on vnext_core.identity_decisions
for each row execute function vnext_private.guard_identity_decision();

create function vnext_private.guard_slice6_append_only()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    raise exception using errcode = '42501', message = 'vnext_slice6_record_is_immutable';
end
$$;

revoke all on function vnext_private.guard_slice6_append_only() from public;

create trigger trg_vnext_identity_decisions_append_only
before update or delete on vnext_core.identity_decisions
for each row execute function vnext_private.guard_slice6_append_only();

alter table vnext_core.property_relations
    add column identity_confirmation_id uuid;

alter table vnext_core.property_relations
    add constraint fk_vnext_property_relations_confirmation
    foreign key (workspace_id, identity_confirmation_id)
    references vnext_core.identity_decisions(workspace_id, identity_decision_id)
    on delete restrict;

alter table vnext_core.property_relations
    add constraint ck_vnext_property_relations_confirmation_reference
    check (
        (relation_status = 'confirmed' and identity_confirmation_id is not null)
        or (relation_status <> 'confirmed' and identity_confirmation_id is null)
    );

create index idx_vnext_property_relations_confirmation
    on vnext_core.property_relations (workspace_id, identity_confirmation_id)
    where identity_confirmation_id is not null;

create function vnext_private.guard_confirmed_property_relation()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
    confirmation vnext_core.identity_decisions%rowtype;
    from_record uuid;
    to_record uuid;
    expected_relation_type text;
begin
    if new.relation_status <> 'confirmed' then
        return new;
    end if;

    select * into confirmation
    from vnext_core.identity_decisions decision
    where decision.workspace_id = new.workspace_id
      and decision.identity_decision_id = new.identity_confirmation_id
      and decision.decision_type = 'confirmed';
    if not found then
        raise exception using errcode = '23514', message = 'vnext_property_relation_confirmation_invalid';
    end if;

    select node.record_id into from_record
    from vnext_core.property_graph_nodes node
    where node.workspace_id = new.workspace_id
      and node.property_graph_node_id = new.from_node_id
      and node.node_type = 'property';
    select node.record_id into to_record
    from vnext_core.property_graph_nodes node
    where node.workspace_id = new.workspace_id
      and node.property_graph_node_id = new.to_node_id
      and node.node_type = confirmation.candidate_type_snapshot;

    expected_relation_type := 'property_' || confirmation.candidate_type_snapshot;
    if from_record is distinct from confirmation.property_entity_id
       or to_record is distinct from confirmation.materialized_identity_reference_id
       or new.relation_type <> expected_relation_type
       or new.direction <> 'directed'
       or new.confirmed_by_user_id <> confirmation.actor_user_id
       or new.created_by_user_id <> confirmation.actor_user_id
       or new.confirmed_at <> confirmation.created_at
       or new.source_id <> confirmation.source_id_snapshot
       or new.source_type <> confirmation.source_type_snapshot
       or new.source_environment <> confirmation.source_environment_snapshot
       or new.source_type in ('demo', 'test')
       or new.source_environment <> 'production'
       or new.confidence is distinct from confirmation.confidence_snapshot
       or new.confidence_method is distinct from confirmation.confidence_method_snapshot
       or new.evidence_id is distinct from confirmation.primary_evidence_id then
        raise exception using errcode = '23514', message = 'vnext_property_relation_confirmation_mismatch';
    end if;
    return new;
end
$$;

revoke all on function vnext_private.guard_confirmed_property_relation() from public;

create trigger trg_vnext_property_relations_confirmation
before insert on vnext_core.property_relations
for each row execute function vnext_private.guard_confirmed_property_relation();

create table vnext_core.case_property_links (
    case_property_link_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    case_id uuid not null,
    property_entity_id uuid not null,
    identity_resolution_id uuid not null,
    identity_confirmation_id uuid not null,
    actor_user_id uuid not null,
    case_version_before bigint not null,
    case_version_after bigint not null,
    supersedes_case_property_link_id uuid,
    request_id text not null,
    idempotency_record_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_case_property_links_case
        foreign key (workspace_id, case_id)
        references vnext_core.cases(workspace_id, case_id) on delete restrict,
    constraint fk_vnext_case_property_links_property
        foreign key (workspace_id, property_entity_id)
        references vnext_core.property_entities(workspace_id, property_entity_id)
        on delete restrict,
    constraint fk_vnext_case_property_links_resolution
        foreign key (workspace_id, identity_resolution_id)
        references vnext_core.identity_resolutions(workspace_id, identity_resolution_id)
        on delete restrict,
    constraint fk_vnext_case_property_links_confirmation
        foreign key (workspace_id, identity_confirmation_id)
        references vnext_core.identity_decisions(workspace_id, identity_decision_id)
        on delete restrict,
    constraint fk_vnext_case_property_links_actor
        foreign key (actor_user_id) references auth.users(id) on delete restrict,
    constraint fk_vnext_case_property_links_idempotency
        foreign key (workspace_id, idempotency_record_id)
        references vnext_private.idempotency_records(
            workspace_id, idempotency_record_id
        ) on delete restrict,
    constraint uq_vnext_case_property_links_workspace_link
        unique (workspace_id, case_property_link_id),
    constraint uq_vnext_case_property_links_case_link
        unique (workspace_id, case_id, case_property_link_id),
    constraint fk_vnext_case_property_links_supersedes
        foreign key (workspace_id, case_id, supersedes_case_property_link_id)
        references vnext_core.case_property_links(
            workspace_id, case_id, case_property_link_id
        ) on delete restrict,
    constraint uq_vnext_case_property_links_case_version
        unique (workspace_id, case_id, case_version_after),
    constraint uq_vnext_case_property_links_confirmation
        unique (workspace_id, case_id, identity_confirmation_id),
    constraint uq_vnext_case_property_links_idempotency
        unique (idempotency_record_id),
    constraint ck_vnext_case_property_links_versions
        check (
            case_version_before >= 1
            and case_version_after = case_version_before + 1
        ),
    constraint ck_vnext_case_property_links_supersession
        check (
            supersedes_case_property_link_id is null
            or supersedes_case_property_link_id <> case_property_link_id
        ),
    constraint ck_vnext_case_property_links_request_id
        check (char_length(request_id) between 1 and 128)
);

create index idx_vnext_case_property_links_case_history
    on vnext_core.case_property_links (
        workspace_id, case_id, case_version_after desc, created_at desc
    );

create index idx_vnext_case_property_links_property
    on vnext_core.case_property_links (workspace_id, property_entity_id, created_at desc);

create index idx_vnext_case_property_links_resolution
    on vnext_core.case_property_links (workspace_id, identity_resolution_id);

create index idx_vnext_case_property_links_supersedes
    on vnext_core.case_property_links (
        workspace_id, case_id, supersedes_case_property_link_id
    ) where supersedes_case_property_link_id is not null;

create function vnext_private.guard_case_property_link()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
    selected_case vnext_core.cases%rowtype;
    confirmation vnext_core.identity_decisions%rowtype;
    current_link_id uuid;
begin
    select * into selected_case
    from vnext_core.cases case_record
    where case_record.workspace_id = new.workspace_id
      and case_record.case_id = new.case_id;
    if not found or selected_case.version <> new.case_version_before then
        raise exception using errcode = '40001', message = 'vnext_case_property_link_version_conflict';
    end if;

    select * into confirmation
    from vnext_core.identity_decisions decision
    where decision.workspace_id = new.workspace_id
      and decision.identity_decision_id = new.identity_confirmation_id
      and decision.identity_resolution_id = new.identity_resolution_id
      and decision.property_entity_id = new.property_entity_id
      and decision.decision_type = 'confirmed';
    if not found then
        raise exception using errcode = '23514', message = 'vnext_case_property_link_confirmation_invalid';
    end if;

    if not exists (
        select 1 from vnext_private.idempotency_records idempotency
        where idempotency.workspace_id = new.workspace_id
          and idempotency.idempotency_record_id = new.idempotency_record_id
          and idempotency.actor_user_id = new.actor_user_id
          and idempotency.http_method = 'POST'
          and idempotency.operation_status = 'pending'
    ) then
        raise exception using errcode = '23514', message = 'vnext_case_property_link_idempotency_invalid';
    end if;

    select link.case_property_link_id into current_link_id
    from vnext_core.case_property_links link
    where link.workspace_id = new.workspace_id
      and link.case_id = new.case_id
      and not exists (
          select 1 from vnext_core.case_property_links later
          where later.workspace_id = link.workspace_id
            and later.case_id = link.case_id
            and later.supersedes_case_property_link_id = link.case_property_link_id
      )
    order by link.case_version_after desc
    limit 1;

    if current_link_id is distinct from new.supersedes_case_property_link_id then
        raise exception using errcode = '40001', message = 'vnext_case_property_link_supersession_conflict';
    end if;
    return new;
end
$$;

revoke all on function vnext_private.guard_case_property_link() from public;

create trigger trg_vnext_case_property_links_guard
before insert on vnext_core.case_property_links
for each row execute function vnext_private.guard_case_property_link();

create trigger trg_vnext_case_property_links_append_only
before update or delete on vnext_core.case_property_links
for each row execute function vnext_private.guard_slice6_append_only();

create function vnext_private.guard_case_property_link_commit()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if not exists (
        select 1 from vnext_core.cases case_record
        where case_record.workspace_id = new.workspace_id
          and case_record.case_id = new.case_id
          and case_record.version = new.case_version_after
          and case_record.identity_status = 'confirmed'
    ) then
        raise exception using errcode = '40001', message = 'vnext_case_property_link_case_update_required';
    end if;
    return null;
end
$$;

revoke all on function vnext_private.guard_case_property_link_commit() from public;

create constraint trigger trg_vnext_case_property_links_commit
after insert on vnext_core.case_property_links
deferrable initially deferred
for each row execute function vnext_private.guard_case_property_link_commit();

create or replace function vnext_private.guard_case_update()
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
    if new.identity_status is distinct from old.identity_status
       and (
           new.identity_status <> 'confirmed'
           or old.identity_status not in ('unverified', 'legacy_unverified', 'resolving')
           or not exists (
               select 1 from vnext_core.case_property_links link
               where link.workspace_id = new.workspace_id
                 and link.case_id = new.case_id
                 and link.actor_user_id = (select auth.uid())
                 and link.case_version_before = old.version
                 and link.case_version_after = new.version
           )
       ) then
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

alter table vnext_core.identity_decisions enable row level security;
alter table vnext_core.identity_decisions force row level security;
alter table vnext_core.case_property_links enable row level security;
alter table vnext_core.case_property_links force row level security;

revoke all on table vnext_core.identity_decisions from public;
revoke all on table vnext_core.case_property_links from public;

grant select, insert on vnext_core.identity_decisions to vnext_api;
grant select, insert on vnext_core.case_property_links to vnext_api;

create policy identity_decisions_active_member_select
on vnext_core.identity_decisions
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = identity_decisions.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy identity_decisions_owner_admin_insert
on vnext_core.identity_decisions
for insert
to vnext_api
with check (
    actor_user_id = (select auth.uid())
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = identity_decisions.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin')
    )
);

create policy property_relations_human_confirmation_insert
on vnext_core.property_relations
for insert
to vnext_api
with check (
    relation_status = 'confirmed'
    and identity_confirmation_id is not null
    and confirmed_by_user_id = (select auth.uid())
    and created_by_user_id = (select auth.uid())
    and source_type not in ('demo', 'test')
    and source_environment = 'production'
    and exists (
        select 1 from vnext_core.identity_decisions decision
        where decision.workspace_id = property_relations.workspace_id
          and decision.identity_decision_id = property_relations.identity_confirmation_id
          and decision.decision_type = 'confirmed'
          and decision.actor_user_id = (select auth.uid())
    )
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = property_relations.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin')
    )
);

create policy case_property_links_active_member_select
on vnext_core.case_property_links
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = case_property_links.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy case_property_links_owner_admin_insert
on vnext_core.case_property_links
for insert
to vnext_api
with check (
    actor_user_id = (select auth.uid())
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = case_property_links.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin')
    )
);

comment on table vnext_core.identity_decisions is
    'Immutable explicit human identity decisions. Confidence and rank are snapshots, never autonomous confirmation.';
comment on table vnext_core.case_property_links is
    'Append-only Case-to-Property attachment history tied to a valid human confirmation.';
