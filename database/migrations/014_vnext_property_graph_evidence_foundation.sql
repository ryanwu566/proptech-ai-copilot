-- 014_vnext_property_graph_evidence_foundation.sql
--
-- Stage 1 Slice 3: workspace-scoped PropertyEntity, typed graph references
-- and relations, plus immutable/versioned Evidence and lineage.  This adds no
-- resolver, candidate ranking, provider integration, confirmation command,
-- Case attachment, listing/title capability, or browser/Data API exposure.

create table vnext_core.property_entities (
    property_entity_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    entity_status text not null default 'unverified',
    display_label text not null,
    version bigint not null default 1,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    archived_at timestamptz,
    constraint fk_vnext_property_entities_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_property_entities_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_property_entities_workspace_entity
        unique (workspace_id, property_entity_id),
    constraint ck_vnext_property_entities_status
        check (entity_status in ('unverified', 'active', 'disputed', 'archived')),
    constraint ck_vnext_property_entities_label
        check (char_length(btrim(display_label)) between 1 and 240),
    constraint ck_vnext_property_entities_version
        check (version >= 1),
    constraint ck_vnext_property_entities_archive_time
        check (
            (entity_status = 'archived' and archived_at is not null)
            or (entity_status <> 'archived' and archived_at is null)
        )
);

create index idx_vnext_property_entities_workspace_status_updated
    on vnext_core.property_entities (workspace_id, entity_status, updated_at desc);

create table vnext_core.property_identity_references (
    identity_reference_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    reference_type text not null,
    normalized_key text not null,
    display_value text not null,
    source_id text not null,
    source_type text not null,
    source_environment text not null,
    source_record_id text,
    confidence numeric(5, 4),
    confidence_method text,
    reference_status text not null default 'unverified',
    valid_from timestamptz,
    valid_to timestamptz,
    supersedes_reference_id uuid,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_identity_references_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_identity_references_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_identity_references_workspace_reference
        unique (workspace_id, identity_reference_id),
    constraint fk_vnext_identity_references_supersedes
        foreign key (workspace_id, supersedes_reference_id)
        references vnext_core.property_identity_references(workspace_id, identity_reference_id)
        on delete restrict,
    constraint ck_vnext_identity_references_type
        check (reference_type in ('address', 'geo_reference', 'parcel', 'building')),
    constraint ck_vnext_identity_references_normalized_key
        check (char_length(normalized_key) between 1 and 512),
    constraint ck_vnext_identity_references_display
        check (char_length(display_value) between 1 and 512),
    constraint ck_vnext_identity_references_source_id
        check (source_id ~ '^[a-z0-9][a-z0-9._-]{1,79}$'),
    constraint ck_vnext_identity_references_source_type
        check (source_type in (
            'official', 'partner', 'user', 'deterministic', 'document', 'demo', 'test'
        )),
    constraint ck_vnext_identity_references_environment
        check (source_environment in ('production', 'demo', 'test')),
    constraint ck_vnext_identity_references_nonproduction_source
        check (
            source_type not in ('demo', 'test')
            or source_environment in ('demo', 'test')
        ),
    constraint ck_vnext_identity_references_source_record
        check (source_record_id is null or char_length(source_record_id) between 1 and 240),
    constraint ck_vnext_identity_references_confidence
        check (
            confidence is null
            or (confidence between 0 and 1 and confidence_method is not null)
        ),
    constraint ck_vnext_identity_references_confidence_method
        check (
            confidence_method is null
            or char_length(confidence_method) between 1 and 120
        ),
    constraint ck_vnext_identity_references_status
        check (reference_status in (
            'observed', 'limited', 'unverified', 'disputed', 'superseded', 'rejected'
        )),
    constraint ck_vnext_identity_references_valid_time
        check (valid_from is null or valid_to is null or valid_from <= valid_to),
    constraint ck_vnext_identity_references_supersession
        check (
            supersedes_reference_id is null
            or supersedes_reference_id <> identity_reference_id
        ),
    constraint ck_vnext_identity_references_superseded_status
        check (reference_status <> 'superseded' or supersedes_reference_id is not null)
);

create index idx_vnext_identity_references_workspace_type_status
    on vnext_core.property_identity_references (
        workspace_id, reference_type, reference_status, valid_to
    );

create index idx_vnext_identity_references_source_record
    on vnext_core.property_identity_references (workspace_id, source_id, source_record_id)
    where source_record_id is not null;

create index idx_vnext_identity_references_supersedes
    on vnext_core.property_identity_references (workspace_id, supersedes_reference_id)
    where supersedes_reference_id is not null;

create table vnext_core.evidence_items (
    evidence_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    fact_type text not null,
    value jsonb,
    value_ref text,
    value_schema text,
    source_id text not null,
    source_type text not null,
    source_environment text not null,
    provider text,
    source_record_id text,
    retrieved_at timestamptz not null,
    effective_from timestamptz,
    effective_to timestamptz,
    expires_at timestamptz,
    coverage_status text not null,
    coverage jsonb not null,
    evidence_status text not null,
    quality_confidence numeric(5, 4),
    quality_method text,
    quality_status text not null,
    quality jsonb not null,
    license_status text not null,
    license_ref text,
    license jsonb not null,
    lineage jsonb not null default '{}'::jsonb,
    content_hash text not null,
    evidence_version bigint not null default 1,
    raw_artifact_ref text,
    supersedes_evidence_id uuid,
    created_by_user_id uuid,
    created_by_service text,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_evidence_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_evidence_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_evidence_workspace_evidence
        unique (workspace_id, evidence_id),
    constraint fk_vnext_evidence_supersedes
        foreign key (workspace_id, supersedes_evidence_id)
        references vnext_core.evidence_items(workspace_id, evidence_id)
        on delete restrict,
    constraint ck_vnext_evidence_fact_type
        check (fact_type ~ '^[a-z][a-z0-9_.-]{2,119}$'),
    constraint ck_vnext_evidence_value_shape
        check (
            (value is null or octet_length(value::text) <= 32768)
            and not (value is not null and value_ref is not null)
        ),
    constraint ck_vnext_evidence_value_ref
        check (value_ref is null or value_ref ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,239}$'),
    constraint ck_vnext_evidence_value_schema
        check (value_schema is null or value_schema ~ '^[a-z0-9][a-z0-9._-]{1,119}$'),
    constraint ck_vnext_evidence_source_id
        check (source_id ~ '^[a-z0-9][a-z0-9._-]{1,79}$'),
    constraint ck_vnext_evidence_source_type
        check (source_type in (
            'official', 'partner', 'user', 'deterministic', 'document', 'demo', 'test'
        )),
    constraint ck_vnext_evidence_environment
        check (source_environment in ('production', 'demo', 'test')),
    constraint ck_vnext_evidence_provider
        check (provider is null or char_length(provider) between 1 and 120),
    constraint ck_vnext_evidence_source_record
        check (source_record_id is null or char_length(source_record_id) between 1 and 240),
    constraint ck_vnext_evidence_effective_time
        check (
            effective_from is null or effective_to is null or effective_from <= effective_to
        ),
    constraint ck_vnext_evidence_expiry
        check (expires_at is null or expires_at > retrieved_at),
    constraint ck_vnext_evidence_coverage_status
        check (coverage_status in ('known', 'partial', 'unknown', 'unavailable')),
    constraint ck_vnext_evidence_coverage
        check (jsonb_typeof(coverage) = 'object' and octet_length(coverage::text) <= 16384),
    constraint ck_vnext_evidence_status
        check (evidence_status in (
            'available', 'limited', 'unavailable', 'unknown', 'stale',
            'conflicting', 'user_provided', 'unverified'
        )),
    constraint ck_vnext_evidence_status_value
        check (
            (
                evidence_status in ('available', 'limited', 'user_provided')
                and (value is not null or value_ref is not null)
            )
            or (
                evidence_status in ('unavailable', 'unknown')
                and value is null and value_ref is null
            )
            or evidence_status in ('stale', 'conflicting', 'unverified')
        ),
    constraint ck_vnext_evidence_user_status
        check (evidence_status <> 'user_provided' or source_type = 'user'),
    constraint ck_vnext_evidence_nonproduction_status
        check (
            source_type not in ('demo', 'test')
            or (
                source_environment in ('demo', 'test')
                and evidence_status <> 'available'
            )
        ),
    constraint ck_vnext_evidence_quality_confidence
        check (
            quality_confidence is null
            or (quality_confidence between 0 and 1 and quality_method is not null)
        ),
    constraint ck_vnext_evidence_quality_method
        check (quality_method is null or char_length(quality_method) between 1 and 120),
    constraint ck_vnext_evidence_quality_status
        check (quality_status in ('passed', 'limited', 'failed', 'not_checked')),
    constraint ck_vnext_evidence_quality
        check (jsonb_typeof(quality) = 'object' and octet_length(quality::text) <= 16384),
    constraint ck_vnext_evidence_license_status
        check (license_status in (
            'approved', 'owner_review_required', 'restricted',
            'prohibited', 'not_applicable', 'unknown'
        )),
    constraint ck_vnext_evidence_license_ref
        check (license_ref is null or char_length(license_ref) between 1 and 160),
    constraint ck_vnext_evidence_license
        check (jsonb_typeof(license) = 'object' and octet_length(license::text) <= 16384),
    constraint ck_vnext_evidence_lineage
        check (jsonb_typeof(lineage) = 'object' and octet_length(lineage::text) <= 16384),
    constraint ck_vnext_evidence_content_hash
        check (content_hash ~ '^[0-9a-f]{64}$'),
    constraint ck_vnext_evidence_version
        check (
            evidence_version >= 1
            and (supersedes_evidence_id is null or evidence_version > 1)
        ),
    constraint ck_vnext_evidence_raw_artifact
        check (
            raw_artifact_ref is null
            or raw_artifact_ref ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,239}$'
        ),
    constraint ck_vnext_evidence_creator
        check (
            (created_by_user_id is not null and created_by_service is null)
            or (created_by_user_id is null and created_by_service is not null)
        ),
    constraint ck_vnext_evidence_creator_service
        check (
            created_by_service is null
            or created_by_service ~ '^[a-z][a-z0-9._-]{1,79}$'
        ),
    constraint ck_vnext_evidence_supersession
        check (
            supersedes_evidence_id is null
            or supersedes_evidence_id <> evidence_id
        )
);

create index idx_vnext_evidence_workspace_fact_status_retrieved
    on vnext_core.evidence_items (
        workspace_id, fact_type, evidence_status, retrieved_at desc
    );

create index idx_vnext_evidence_workspace_source_record
    on vnext_core.evidence_items (workspace_id, source_id, source_record_id)
    where source_record_id is not null;

create index idx_vnext_evidence_supersedes
    on vnext_core.evidence_items (workspace_id, supersedes_evidence_id)
    where supersedes_evidence_id is not null;

create index idx_vnext_evidence_expires
    on vnext_core.evidence_items (workspace_id, expires_at)
    where expires_at is not null;

create table vnext_core.property_graph_nodes (
    property_graph_node_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    node_type text not null,
    record_id uuid not null,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_property_graph_nodes_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_property_graph_nodes_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_property_graph_nodes_workspace_node
        unique (workspace_id, property_graph_node_id),
    constraint uq_vnext_property_graph_nodes_record
        unique (workspace_id, node_type, record_id),
    constraint ck_vnext_property_graph_nodes_type
        check (node_type in (
            'property', 'address', 'geo_reference', 'parcel',
            'building', 'listing', 'case'
        ))
);

create index idx_vnext_property_graph_nodes_workspace_type_record
    on vnext_core.property_graph_nodes (workspace_id, node_type, record_id);

create function vnext_private.guard_property_graph_node_target()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if new.node_type = 'property' then
        if not exists (
            select 1 from vnext_core.property_entities record
            where record.workspace_id = new.workspace_id
              and record.property_entity_id = new.record_id
        ) then
            raise exception using errcode = '23514', message = 'vnext_graph_property_target_invalid';
        end if;
    elsif new.node_type in ('address', 'geo_reference', 'parcel', 'building') then
        if not exists (
            select 1 from vnext_core.property_identity_references record
            where record.workspace_id = new.workspace_id
              and record.identity_reference_id = new.record_id
              and record.reference_type = new.node_type
        ) then
            raise exception using errcode = '23514', message = 'vnext_graph_reference_target_invalid';
        end if;
    elsif new.node_type = 'case' then
        if not exists (
            select 1 from vnext_core.cases record
            where record.workspace_id = new.workspace_id
              and record.case_id = new.record_id
        ) then
            raise exception using errcode = '23514', message = 'vnext_graph_case_target_invalid';
        end if;
    else
        raise exception using errcode = '23514', message = 'vnext_graph_listing_target_unavailable';
    end if;
    return new;
end
$$;

revoke all on function vnext_private.guard_property_graph_node_target() from public;

create trigger trg_vnext_property_graph_nodes_target
before insert on vnext_core.property_graph_nodes
for each row execute function vnext_private.guard_property_graph_node_target();

create function vnext_private.append_property_graph_node()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if tg_table_name = 'property_entities' then
        insert into vnext_core.property_graph_nodes (
            workspace_id, node_type, record_id, created_by_user_id
        ) values (
            new.workspace_id, 'property', new.property_entity_id, new.created_by_user_id
        );
    elsif tg_table_name = 'property_identity_references' then
        insert into vnext_core.property_graph_nodes (
            workspace_id, node_type, record_id, created_by_user_id
        ) values (
            new.workspace_id, new.reference_type, new.identity_reference_id,
            new.created_by_user_id
        );
    else
        raise exception using errcode = '23514', message = 'vnext_graph_node_source_invalid';
    end if;
    return new;
end
$$;

revoke all on function vnext_private.append_property_graph_node() from public;

create trigger trg_vnext_property_entities_graph_node
after insert on vnext_core.property_entities
for each row execute function vnext_private.append_property_graph_node();

create trigger trg_vnext_identity_references_graph_node
after insert on vnext_core.property_identity_references
for each row execute function vnext_private.append_property_graph_node();

create table vnext_core.property_relations (
    property_relation_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    from_node_id uuid not null,
    to_node_id uuid not null,
    relation_type text not null,
    direction text not null,
    confidence numeric(5, 4),
    confidence_method text,
    source_id text not null,
    source_type text not null,
    source_environment text not null,
    evidence_id uuid,
    relation_status text not null default 'proposed',
    valid_from timestamptz,
    valid_to timestamptz,
    confirmed_by_user_id uuid,
    confirmed_at timestamptz,
    supersedes_relation_id uuid,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_property_relations_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_property_relations_from_node
        foreign key (workspace_id, from_node_id)
        references vnext_core.property_graph_nodes(workspace_id, property_graph_node_id)
        on delete restrict,
    constraint fk_vnext_property_relations_to_node
        foreign key (workspace_id, to_node_id)
        references vnext_core.property_graph_nodes(workspace_id, property_graph_node_id)
        on delete restrict,
    constraint fk_vnext_property_relations_evidence
        foreign key (workspace_id, evidence_id)
        references vnext_core.evidence_items(workspace_id, evidence_id)
        on delete restrict,
    constraint fk_vnext_property_relations_confirmed_by
        foreign key (confirmed_by_user_id) references auth.users(id) on delete restrict,
    constraint fk_vnext_property_relations_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_property_relations_workspace_relation
        unique (workspace_id, property_relation_id),
    constraint fk_vnext_property_relations_supersedes
        foreign key (workspace_id, supersedes_relation_id)
        references vnext_core.property_relations(workspace_id, property_relation_id)
        on delete restrict,
    constraint ck_vnext_property_relations_distinct_nodes
        check (from_node_id <> to_node_id),
    constraint ck_vnext_property_relations_type
        check (relation_type in (
            'property_address', 'property_geo_reference',
            'property_parcel', 'property_building', 'parcel_building'
        )),
    constraint ck_vnext_property_relations_direction
        check (direction in ('directed', 'bidirectional')),
    constraint ck_vnext_property_relations_confidence
        check (
            confidence is null
            or (confidence between 0 and 1 and confidence_method is not null)
        ),
    constraint ck_vnext_property_relations_confidence_method
        check (
            confidence_method is null
            or char_length(confidence_method) between 1 and 120
        ),
    constraint ck_vnext_property_relations_source_id
        check (source_id ~ '^[a-z0-9][a-z0-9._-]{1,79}$'),
    constraint ck_vnext_property_relations_source_type
        check (source_type in (
            'official', 'partner', 'user', 'deterministic', 'document', 'demo', 'test'
        )),
    constraint ck_vnext_property_relations_environment
        check (source_environment in ('production', 'demo', 'test')),
    constraint ck_vnext_property_relations_nonproduction_source
        check (
            source_type not in ('demo', 'test')
            or source_environment in ('demo', 'test')
        ),
    constraint ck_vnext_property_relations_status
        check (relation_status in (
            'proposed', 'confirmed', 'rejected', 'superseded', 'disputed'
        )),
    constraint ck_vnext_property_relations_confirmation
        check (
            (
                relation_status = 'confirmed'
                and confirmed_by_user_id is not null
                and confirmed_at is not null
            )
            or (
                relation_status <> 'confirmed'
                and confirmed_by_user_id is null
                and confirmed_at is null
            )
        ),
    constraint ck_vnext_property_relations_nonproduction_confirmation
        check (source_type not in ('demo', 'test') or relation_status <> 'confirmed'),
    constraint ck_vnext_property_relations_valid_time
        check (valid_from is null or valid_to is null or valid_from <= valid_to),
    constraint ck_vnext_property_relations_supersession
        check (
            supersedes_relation_id is null
            or supersedes_relation_id <> property_relation_id
        ),
    constraint ck_vnext_property_relations_superseded_status
        check (
            relation_status <> 'superseded'
            or (supersedes_relation_id is not null and valid_to is not null)
        )
);

create index idx_vnext_property_relations_from
    on vnext_core.property_relations (
        workspace_id, from_node_id, relation_type, relation_status, valid_to
    );

create index idx_vnext_property_relations_to
    on vnext_core.property_relations (
        workspace_id, to_node_id, relation_type, relation_status, valid_to
    );

create index idx_vnext_property_relations_open
    on vnext_core.property_relations (workspace_id, relation_type, from_node_id, to_node_id)
    where valid_to is null and relation_status in ('confirmed', 'disputed');

create index idx_vnext_property_relations_evidence
    on vnext_core.property_relations (workspace_id, evidence_id)
    where evidence_id is not null;

create index idx_vnext_property_relations_supersedes
    on vnext_core.property_relations (workspace_id, supersedes_relation_id)
    where supersedes_relation_id is not null;

create function vnext_private.guard_property_relation_endpoints()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
    selected_from_type text;
    selected_to_type text;
begin
    select node.node_type into selected_from_type
    from vnext_core.property_graph_nodes node
    where node.workspace_id = new.workspace_id
      and node.property_graph_node_id = new.from_node_id;

    select node.node_type into selected_to_type
    from vnext_core.property_graph_nodes node
    where node.workspace_id = new.workspace_id
      and node.property_graph_node_id = new.to_node_id;

    if selected_from_type is null or selected_to_type is null then
        raise exception using errcode = '23514', message = 'vnext_graph_relation_endpoint_invalid';
    end if;

    if (
        new.relation_type = 'property_address'
        and (selected_from_type <> 'property' or selected_to_type <> 'address')
    ) or (
        new.relation_type = 'property_geo_reference'
        and (selected_from_type <> 'property' or selected_to_type <> 'geo_reference')
    ) or (
        new.relation_type = 'property_parcel'
        and (selected_from_type <> 'property' or selected_to_type <> 'parcel')
    ) or (
        new.relation_type = 'property_building'
        and (selected_from_type <> 'property' or selected_to_type <> 'building')
    ) or (
        new.relation_type = 'parcel_building'
        and (
            selected_from_type <> 'parcel'
            or selected_to_type <> 'building'
            or new.direction <> 'bidirectional'
        )
    ) or (
        new.relation_type <> 'parcel_building'
        and new.direction <> 'directed'
    ) then
        raise exception using errcode = '23514', message = 'vnext_graph_relation_type_invalid';
    end if;
    return new;
end
$$;

revoke all on function vnext_private.guard_property_relation_endpoints() from public;

create trigger trg_vnext_property_relations_endpoints
before insert on vnext_core.property_relations
for each row execute function vnext_private.guard_property_relation_endpoints();

create table vnext_core.evidence_lineage (
    evidence_lineage_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    child_evidence_id uuid not null,
    parent_evidence_id uuid not null,
    lineage_type text not null,
    transformation text not null,
    transformation_version text,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_evidence_lineage_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_evidence_lineage_child
        foreign key (workspace_id, child_evidence_id)
        references vnext_core.evidence_items(workspace_id, evidence_id)
        on delete restrict,
    constraint fk_vnext_evidence_lineage_parent
        foreign key (workspace_id, parent_evidence_id)
        references vnext_core.evidence_items(workspace_id, evidence_id)
        on delete restrict,
    constraint fk_vnext_evidence_lineage_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_evidence_lineage_edge
        unique (workspace_id, child_evidence_id, parent_evidence_id, lineage_type),
    constraint ck_vnext_evidence_lineage_distinct
        check (child_evidence_id <> parent_evidence_id),
    constraint ck_vnext_evidence_lineage_type
        check (lineage_type in (
            'derived_from', 'normalized_from', 'aggregated_from',
            'calculated_from', 'manual_review_from', 'supersedes'
        )),
    constraint ck_vnext_evidence_lineage_transformation
        check (transformation in (
            'normalization', 'aggregation', 'calculation', 'manual_review', 'none'
        )),
    constraint ck_vnext_evidence_lineage_version
        check (
            transformation_version is null
            or char_length(transformation_version) between 1 and 120
        )
);

create index idx_vnext_evidence_lineage_parent
    on vnext_core.evidence_lineage (workspace_id, parent_evidence_id, child_evidence_id);

create index idx_vnext_evidence_lineage_child
    on vnext_core.evidence_lineage (workspace_id, child_evidence_id, parent_evidence_id);

create table vnext_core.evidence_links (
    evidence_link_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    evidence_id uuid not null,
    subject_node_id uuid not null,
    link_type text not null,
    fact_scope text not null,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_evidence_links_workspace
        foreign key (workspace_id) references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_evidence_links_evidence
        foreign key (workspace_id, evidence_id)
        references vnext_core.evidence_items(workspace_id, evidence_id)
        on delete restrict,
    constraint fk_vnext_evidence_links_subject
        foreign key (workspace_id, subject_node_id)
        references vnext_core.property_graph_nodes(workspace_id, property_graph_node_id)
        on delete restrict,
    constraint fk_vnext_evidence_links_created_by
        foreign key (created_by_user_id) references auth.users(id) on delete restrict,
    constraint uq_vnext_evidence_links_subject_fact
        unique (workspace_id, evidence_id, subject_node_id, link_type, fact_scope),
    constraint ck_vnext_evidence_links_type
        check (link_type in ('supports', 'contradicts', 'limits', 'describes')),
    constraint ck_vnext_evidence_links_fact_scope
        check (fact_scope ~ '^[a-z][a-z0-9_.-]{2,119}$')
);

create index idx_vnext_evidence_links_subject
    on vnext_core.evidence_links (workspace_id, subject_node_id, evidence_id);

create index idx_vnext_evidence_links_evidence
    on vnext_core.evidence_links (workspace_id, evidence_id, subject_node_id);

create function vnext_private.guard_graph_evidence_append_only()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    raise exception using errcode = '42501', message = 'vnext_graph_evidence_record_is_immutable';
end
$$;

revoke all on function vnext_private.guard_graph_evidence_append_only() from public;

create trigger trg_vnext_identity_references_append_only
before update or delete on vnext_core.property_identity_references
for each row execute function vnext_private.guard_graph_evidence_append_only();

create trigger trg_vnext_property_graph_nodes_append_only
before update or delete on vnext_core.property_graph_nodes
for each row execute function vnext_private.guard_graph_evidence_append_only();

create trigger trg_vnext_property_relations_append_only
before update or delete on vnext_core.property_relations
for each row execute function vnext_private.guard_graph_evidence_append_only();

create trigger trg_vnext_evidence_items_append_only
before update or delete on vnext_core.evidence_items
for each row execute function vnext_private.guard_graph_evidence_append_only();

create trigger trg_vnext_evidence_lineage_append_only
before update or delete on vnext_core.evidence_lineage
for each row execute function vnext_private.guard_graph_evidence_append_only();

create trigger trg_vnext_evidence_links_append_only
before update or delete on vnext_core.evidence_links
for each row execute function vnext_private.guard_graph_evidence_append_only();

alter table vnext_core.property_entities enable row level security;
alter table vnext_core.property_entities force row level security;
alter table vnext_core.property_identity_references enable row level security;
alter table vnext_core.property_identity_references force row level security;
alter table vnext_core.property_graph_nodes enable row level security;
alter table vnext_core.property_graph_nodes force row level security;
alter table vnext_core.property_relations enable row level security;
alter table vnext_core.property_relations force row level security;
alter table vnext_core.evidence_items enable row level security;
alter table vnext_core.evidence_items force row level security;
alter table vnext_core.evidence_lineage enable row level security;
alter table vnext_core.evidence_lineage force row level security;
alter table vnext_core.evidence_links enable row level security;
alter table vnext_core.evidence_links force row level security;

revoke all on table vnext_core.property_entities from public;
revoke all on table vnext_core.property_identity_references from public;
revoke all on table vnext_core.property_graph_nodes from public;
revoke all on table vnext_core.property_relations from public;
revoke all on table vnext_core.evidence_items from public;
revoke all on table vnext_core.evidence_lineage from public;
revoke all on table vnext_core.evidence_links from public;

grant select, insert on vnext_core.property_entities to vnext_api;
grant select, insert on vnext_core.property_identity_references to vnext_api;
grant select, insert on vnext_core.property_graph_nodes to vnext_api;
grant select, insert on vnext_core.property_relations to vnext_api;
grant select, insert on vnext_core.evidence_items to vnext_api;
grant select, insert on vnext_core.evidence_lineage to vnext_api;
grant select, insert on vnext_core.evidence_links to vnext_api;

create policy property_entities_active_member_select
on vnext_core.property_entities
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = property_entities.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy property_entities_active_writer_insert
on vnext_core.property_entities
for insert
to vnext_api
with check (
    entity_status = 'unverified'
    and created_by_user_id = (select auth.uid())
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = property_entities.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy identity_references_active_member_select
on vnext_core.property_identity_references
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = property_identity_references.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy identity_references_active_writer_insert
on vnext_core.property_identity_references
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and source_type in ('user', 'deterministic', 'demo', 'test')
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = property_identity_references.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy property_graph_nodes_active_member_select
on vnext_core.property_graph_nodes
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = property_graph_nodes.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy property_graph_nodes_active_writer_insert
on vnext_core.property_graph_nodes
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = property_graph_nodes.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy property_relations_active_member_select
on vnext_core.property_relations
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = property_relations.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy property_relations_active_writer_insert
on vnext_core.property_relations
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and source_type in ('user', 'deterministic', 'demo', 'test')
    and relation_status <> 'confirmed'
    and confirmed_by_user_id is null
    and confirmed_at is null
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = property_relations.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy evidence_items_active_member_select
on vnext_core.evidence_items
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = evidence_items.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy evidence_items_active_writer_insert
on vnext_core.evidence_items
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and created_by_service is null
    and source_type in ('user', 'deterministic', 'demo', 'test')
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = evidence_items.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy evidence_lineage_active_member_select
on vnext_core.evidence_lineage
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = evidence_lineage.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy evidence_lineage_active_writer_insert
on vnext_core.evidence_lineage
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and exists (
        select 1 from vnext_core.evidence_items child
        where child.workspace_id = evidence_lineage.workspace_id
          and child.evidence_id = evidence_lineage.child_evidence_id
          and child.created_by_user_id = (select auth.uid())
          and child.source_type in ('user', 'deterministic', 'demo', 'test')
    )
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = evidence_lineage.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy evidence_links_active_member_select
on vnext_core.evidence_links
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = evidence_links.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy evidence_links_active_writer_insert
on vnext_core.evidence_links
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and exists (
        select 1 from vnext_core.evidence_items evidence
        where evidence.workspace_id = evidence_links.workspace_id
          and evidence.evidence_id = evidence_links.evidence_id
          and evidence.created_by_user_id = (select auth.uid())
          and evidence.source_type in ('user', 'deterministic', 'demo', 'test')
    )
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = evidence_links.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

comment on table vnext_core.property_entities is
    'Workspace-scoped property anchors. Separate from Cases and from address/parcel/building observations.';
comment on table vnext_core.property_identity_references is
    'Immutable provenance-bearing address, geo, parcel and building reference observations.';
comment on table vnext_core.property_relations is
    'Immutable typed temporal graph edges. Conflicts and supersession append history rather than merging rows.';
comment on table vnext_core.evidence_items is
    'Immutable/versioned Evidence with source, time, coverage, quality, license and lineage metadata.';
comment on table vnext_core.evidence_links is
    'Workspace-consistent links from immutable Evidence to the graph node it supports or limits.';
