-- 018_add_vnext_spatial_foundation.sql
--
-- Stage 2A Slice 1: append-only parcel geometry versions, a global immutable
-- spatial layer registry, and tenant-scoped immutable spatial observations.
-- Geometry persistence and observations are evidence, not identity proof or
-- human confirmation. This migration deliberately does not enable PostGIS.

create table vnext_core.spatial_layers (
    spatial_layer_id uuid primary key default gen_random_uuid(),
    layer_key text not null,
    layer_version bigint not null,
    title text not null,
    category text not null,
    provider_id text not null,
    provider_version text not null,
    source_id text not null,
    source_type text not null,
    source_environment text not null,
    authority_class text not null,
    geometry_types text[] not null,
    source_crs jsonb not null,
    supported_crs jsonb not null,
    coverage_semantics jsonb not null,
    temporal_semantics text not null,
    refresh_semantics text not null,
    license_status text not null,
    license jsonb not null,
    attribution text not null,
    evidence_requirements text[] not null,
    provenance_requirements text[] not null,
    limitations text[] not null,
    availability text not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint uq_vnext_spatial_layers_key_version
        unique (layer_key, layer_version),
    constraint uq_vnext_spatial_layers_id_version
        unique (spatial_layer_id, layer_version),
    constraint ck_vnext_spatial_layers_key
        check (layer_key ~ '^[a-z0-9][a-z0-9._-]{1,119}$'),
    constraint ck_vnext_spatial_layers_version
        check (layer_version >= 1),
    constraint ck_vnext_spatial_layers_title
        check (char_length(btrim(title)) between 1 and 160),
    constraint ck_vnext_spatial_layers_category
        check (category ~ '^[a-z0-9][a-z0-9._-]{1,119}$'),
    constraint ck_vnext_spatial_layers_provider
        check (
            provider_id ~ '^[a-z0-9][a-z0-9._-]{1,119}$'
            and char_length(btrim(provider_version)) between 1 and 80
        ),
    constraint ck_vnext_spatial_layers_source
        check (
            source_id ~ '^[a-z0-9][a-z0-9._-]{1,79}$'
            and source_type in (
                'official', 'partner', 'user', 'deterministic',
                'document', 'demo', 'test'
            )
            and source_environment in ('production', 'demo', 'test')
        ),
    constraint ck_vnext_spatial_layers_authority
        check (
            (authority_class = 'official' and source_type = 'official')
            or (authority_class = 'derived' and source_type = 'deterministic')
            or (authority_class = 'user_supplied' and source_type = 'user')
            or (
                authority_class = 'synthetic'
                and source_type in ('demo', 'test')
                and source_environment in ('demo', 'test')
                and availability <> 'available'
            )
            or (
                authority_class = 'unknown'
                and source_type in ('official', 'partner', 'document')
            )
        ),
    constraint ck_vnext_spatial_layers_geometry_types
        check (
            cardinality(geometry_types) between 1 and 4
            and array_position(geometry_types, null) is null
            and geometry_types <@ array[
                'Point', 'LineString', 'Polygon', 'MultiPolygon'
            ]::text[]
        ),
    constraint ck_vnext_spatial_layers_source_crs
        check (
            jsonb_typeof(source_crs) = 'array'
            and jsonb_array_length(source_crs) between 1 and 32
            and octet_length(source_crs::text) <= 8192
        ),
    constraint ck_vnext_spatial_layers_supported_crs
        check (
            jsonb_typeof(supported_crs) = 'array'
            and jsonb_array_length(supported_crs) between 1 and 32
            and supported_crs @> '[{"identifier":"EPSG:4326","coordinate_order":"longitude_latitude"}]'::jsonb
            and octet_length(supported_crs::text) <= 8192
        ),
    constraint ck_vnext_spatial_layers_coverage
        check (
            jsonb_typeof(coverage_semantics) = 'object'
            and octet_length(coverage_semantics::text) <= 16384
        ),
    constraint ck_vnext_spatial_layers_temporal
        check (temporal_semantics in (
            'snapshot', 'effective_interval', 'live_observation', 'unknown'
        )),
    constraint ck_vnext_spatial_layers_refresh
        check (refresh_semantics in (
            'event_driven', 'periodic', 'manual', 'immutable_release', 'unknown'
        )),
    constraint ck_vnext_spatial_layers_license
        check (
            license_status in (
                'approved', 'owner_review_required', 'restricted',
                'prohibited', 'not_applicable', 'unknown'
            )
            and jsonb_typeof(license) = 'object'
            and octet_length(license::text) <= 16384
            and license ->> 'attribution' = attribution
        ),
    constraint ck_vnext_spatial_layers_attribution
        check (char_length(btrim(attribution)) between 1 and 500),
    constraint ck_vnext_spatial_layers_requirements
        check (
            cardinality(evidence_requirements) between 1 and 32
            and cardinality(provenance_requirements) between 1 and 32
            and array_position(evidence_requirements, null) is null
            and array_position(provenance_requirements, null) is null
        ),
    constraint ck_vnext_spatial_layers_limitations
        check (
            cardinality(limitations) between 1 and 32
            and array_position(limitations, null) is null
        ),
    constraint ck_vnext_spatial_layers_availability
        check (availability in (
            'available', 'limited', 'unavailable', 'pending_approval'
        ))
);

create index idx_vnext_spatial_layers_key_latest
    on vnext_core.spatial_layers (layer_key, layer_version desc);

create table vnext_core.parcel_geometry_versions (
    parcel_geometry_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    parcel_identity_reference_id uuid not null,
    geometry_version bigint not null,
    supersedes_geometry_id uuid,
    geometry_type text not null,
    source_geometry_wkb bytea not null,
    source_geometry_sha256 text not null,
    source_crs text not null,
    source_coordinate_order text not null,
    normalized_geometry jsonb not null,
    normalized_crs text not null,
    normalized_coordinate_order text not null,
    precision_value double precision,
    precision_unit text not null,
    precision_method text not null,
    tolerance double precision not null,
    tolerance_unit text not null,
    geometry_source text not null,
    source_id text not null,
    source_type text not null,
    source_environment text not null,
    provider_id text not null,
    provider_version text not null,
    source_record_id text,
    authority_class text not null,
    retrieved_at timestamptz not null,
    effective_at timestamptz,
    valid_from timestamptz,
    valid_to timestamptz,
    coverage_status text not null,
    coverage jsonb not null,
    processing_lineage jsonb not null,
    evidence_id uuid not null,
    idempotency_record_id uuid not null,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_parcel_geometry_workspace
        foreign key (workspace_id)
        references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_parcel_geometry_reference
        foreign key (workspace_id, parcel_identity_reference_id)
        references vnext_core.property_identity_references(
            workspace_id, identity_reference_id
        ) on delete restrict,
    constraint fk_vnext_parcel_geometry_supersedes
        foreign key (workspace_id, supersedes_geometry_id)
        references vnext_core.parcel_geometry_versions(
            workspace_id, parcel_geometry_id
        ) on delete restrict,
    constraint fk_vnext_parcel_geometry_evidence
        foreign key (workspace_id, evidence_id)
        references vnext_core.evidence_items(workspace_id, evidence_id)
        on delete restrict,
    constraint fk_vnext_parcel_geometry_idempotency
        foreign key (workspace_id, idempotency_record_id)
        references vnext_private.idempotency_records(
            workspace_id, idempotency_record_id
        ) on delete restrict,
    constraint fk_vnext_parcel_geometry_creator
        foreign key (created_by_user_id)
        references auth.users(id) on delete restrict,
    constraint uq_vnext_parcel_geometry_workspace_geometry
        unique (workspace_id, parcel_geometry_id),
    constraint uq_vnext_parcel_geometry_parcel_version
        unique (workspace_id, parcel_identity_reference_id, geometry_version),
    constraint uq_vnext_parcel_geometry_superseded_once
        unique (workspace_id, supersedes_geometry_id),
    constraint uq_vnext_parcel_geometry_idempotency
        unique (idempotency_record_id),
    constraint ck_vnext_parcel_geometry_version
        check (
            geometry_version >= 1
            and (
                (geometry_version = 1 and supersedes_geometry_id is null)
                or (geometry_version > 1 and supersedes_geometry_id is not null)
            )
        ),
    constraint ck_vnext_parcel_geometry_no_self_supersession
        check (
            supersedes_geometry_id is null
            or supersedes_geometry_id <> parcel_geometry_id
        ),
    constraint ck_vnext_parcel_geometry_type
        check (geometry_type in ('Polygon', 'MultiPolygon')),
    constraint ck_vnext_parcel_geometry_source_bytes
        check (
            octet_length(source_geometry_wkb) between 9 and 8388608
            and source_geometry_sha256 ~ '^[0-9a-f]{64}$'
        ),
    constraint ck_vnext_parcel_geometry_source_crs
        check (
            char_length(source_crs) between 1 and 160
            and source_coordinate_order in (
                'longitude_latitude', 'easting_northing', 'x_y'
            )
        ),
    constraint ck_vnext_parcel_geometry_normalized
        check (
            normalized_crs = 'EPSG:4326'
            and normalized_coordinate_order = 'longitude_latitude'
            and jsonb_typeof(normalized_geometry) = 'object'
            and normalized_geometry ->> 'type' = geometry_type
            and octet_length(normalized_geometry::text) <= 8388608
        ),
    constraint ck_vnext_parcel_geometry_precision
        check (
            (precision_value is null or precision_value >= 0)
            and precision_unit ~ '^[a-z0-9][a-z0-9._-]{1,119}$'
            and precision_method ~ '^[a-z0-9][a-z0-9._-]{1,119}$'
        ),
    constraint ck_vnext_parcel_geometry_tolerance
        check (
            tolerance >= 0
            and tolerance_unit ~ '^[a-z0-9][a-z0-9._-]{1,119}$'
        ),
    constraint ck_vnext_parcel_geometry_source_key
        check (geometry_source ~ '^[a-z0-9][a-z0-9._-]{1,119}$'),
    constraint ck_vnext_parcel_geometry_provenance
        check (
            source_id ~ '^[a-z0-9][a-z0-9._-]{1,79}$'
            and source_type in (
                'official', 'partner', 'user', 'deterministic',
                'document', 'demo', 'test'
            )
            and source_environment in ('production', 'demo', 'test')
            and provider_id ~ '^[a-z0-9][a-z0-9._-]{1,119}$'
            and char_length(btrim(provider_version)) between 1 and 80
            and (
                source_record_id is null
                or char_length(source_record_id) between 1 and 240
            )
        ),
    constraint ck_vnext_parcel_geometry_authority
        check (
            (authority_class = 'official' and source_type = 'official')
            or (authority_class = 'derived' and source_type = 'deterministic')
            or (authority_class = 'user_supplied' and source_type = 'user')
            or (
                authority_class = 'synthetic'
                and source_type in ('demo', 'test')
                and source_environment in ('demo', 'test')
            )
            or (
                authority_class = 'unknown'
                and source_type in ('official', 'partner', 'document')
            )
        ),
    constraint ck_vnext_parcel_geometry_valid_time
        check (valid_from is null or valid_to is null or valid_from < valid_to),
    constraint ck_vnext_parcel_geometry_coverage
        check (
            coverage_status in ('complete', 'partial', 'unknown', 'unavailable')
            and jsonb_typeof(coverage) = 'object'
            and coverage ->> 'status' = coverage_status
            and jsonb_typeof(coverage -> 'gaps') = 'array'
            and octet_length(coverage::text) <= 16384
        ),
    constraint ck_vnext_parcel_geometry_lineage
        check (
            jsonb_typeof(processing_lineage) = 'array'
            and octet_length(processing_lineage::text) <= 16384
        )
);

create unique index uq_vnext_parcel_geometry_source_record
    on vnext_core.parcel_geometry_versions (
        workspace_id, parcel_identity_reference_id,
        source_id, provider_id, source_record_id
    ) where source_record_id is not null;

create index idx_vnext_parcel_geometry_parcel_history
    on vnext_core.parcel_geometry_versions (
        workspace_id, parcel_identity_reference_id, geometry_version desc
    );

create index idx_vnext_parcel_geometry_evidence
    on vnext_core.parcel_geometry_versions (workspace_id, evidence_id);

create table vnext_core.spatial_observations (
    spatial_observation_id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null,
    subject_type text not null,
    subject_id uuid not null,
    parcel_geometry_id uuid,
    spatial_layer_id uuid not null,
    observation_status text not null,
    result jsonb,
    coverage_status text not null,
    coverage jsonb not null,
    evidence_id uuid not null,
    source_id text not null,
    source_type text not null,
    source_environment text not null,
    provider_id text not null,
    provider_version text not null,
    source_record_id text,
    authority_class text not null,
    retrieved_at timestamptz not null,
    effective_at timestamptz,
    processing_lineage jsonb not null,
    license_status text not null,
    license jsonb not null,
    confidence double precision,
    confidence_method text,
    limitations text[] not null,
    idempotency_record_id uuid not null,
    created_by_user_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    constraint fk_vnext_spatial_observation_workspace
        foreign key (workspace_id)
        references vnext_core.workspaces(workspace_id) on delete restrict,
    constraint fk_vnext_spatial_observation_geometry
        foreign key (workspace_id, parcel_geometry_id)
        references vnext_core.parcel_geometry_versions(
            workspace_id, parcel_geometry_id
        ) on delete restrict,
    constraint fk_vnext_spatial_observation_layer
        foreign key (spatial_layer_id)
        references vnext_core.spatial_layers(spatial_layer_id)
        on delete restrict,
    constraint fk_vnext_spatial_observation_evidence
        foreign key (workspace_id, evidence_id)
        references vnext_core.evidence_items(workspace_id, evidence_id)
        on delete restrict,
    constraint fk_vnext_spatial_observation_idempotency
        foreign key (workspace_id, idempotency_record_id)
        references vnext_private.idempotency_records(
            workspace_id, idempotency_record_id
        ) on delete restrict,
    constraint fk_vnext_spatial_observation_creator
        foreign key (created_by_user_id)
        references auth.users(id) on delete restrict,
    constraint uq_vnext_spatial_observation_workspace_observation
        unique (workspace_id, spatial_observation_id),
    constraint uq_vnext_spatial_observation_idempotency
        unique (idempotency_record_id),
    constraint ck_vnext_spatial_observation_subject
        check (subject_type in (
            'property', 'identity_reference', 'address', 'geo_reference',
            'parcel', 'building', 'case'
        )),
    constraint ck_vnext_spatial_observation_status
        check (observation_status in (
            'present', 'absent', 'no_match', 'unavailable', 'unknown',
            'partial_coverage', 'provider_error', 'stale', 'not_assessed'
        )),
    constraint ck_vnext_spatial_observation_result
        check (
            (
                observation_status in ('present', 'partial_coverage', 'stale')
                and result is not null
                and jsonb_typeof(result) = 'object'
                and octet_length(result::text) <= 32768
            )
            or (
                observation_status in (
                    'absent', 'no_match', 'unavailable', 'unknown',
                    'provider_error', 'not_assessed'
                )
                and result is null
            )
        ),
    constraint ck_vnext_spatial_observation_coverage
        check (
            coverage_status in ('complete', 'partial', 'unknown', 'unavailable')
            and jsonb_typeof(coverage) = 'object'
            and coverage ->> 'status' = coverage_status
            and jsonb_typeof(coverage -> 'gaps') = 'array'
            and octet_length(coverage::text) <= 16384
            and (
                observation_status <> 'absent'
                or (
                    coverage_status = 'complete'
                    and coverage -> 'gaps' = '[]'::jsonb
                )
            )
            and (
                observation_status <> 'partial_coverage'
                or coverage_status = 'partial'
            )
        ),
    constraint ck_vnext_spatial_observation_provenance
        check (
            source_id ~ '^[a-z0-9][a-z0-9._-]{1,79}$'
            and source_type in (
                'official', 'partner', 'user', 'deterministic',
                'document', 'demo', 'test'
            )
            and source_environment in ('production', 'demo', 'test')
            and provider_id ~ '^[a-z0-9][a-z0-9._-]{1,119}$'
            and char_length(btrim(provider_version)) between 1 and 80
            and (
                source_record_id is null
                or char_length(source_record_id) between 1 and 240
            )
        ),
    constraint ck_vnext_spatial_observation_authority
        check (
            (authority_class = 'official' and source_type = 'official')
            or (authority_class = 'derived' and source_type = 'deterministic')
            or (authority_class = 'user_supplied' and source_type = 'user')
            or (
                authority_class = 'synthetic'
                and source_type in ('demo', 'test')
                and source_environment in ('demo', 'test')
            )
            or (
                authority_class = 'unknown'
                and source_type in ('official', 'partner', 'document')
            )
        ),
    constraint ck_vnext_spatial_observation_lineage
        check (
            jsonb_typeof(processing_lineage) = 'array'
            and octet_length(processing_lineage::text) <= 16384
        ),
    constraint ck_vnext_spatial_observation_license
        check (
            license_status in (
                'approved', 'owner_review_required', 'restricted',
                'prohibited', 'not_applicable', 'unknown'
            )
            and jsonb_typeof(license) = 'object'
            and octet_length(license::text) <= 16384
        ),
    constraint ck_vnext_spatial_observation_confidence
        check (
            (confidence is null and confidence_method is null)
            or (
                confidence between 0 and 1
                and char_length(btrim(confidence_method)) between 1 and 120
            )
        ),
    constraint ck_vnext_spatial_observation_limitations
        check (
            cardinality(limitations) between 0 and 32
            and array_position(limitations, null) is null
            and (
                observation_status = 'present'
                or cardinality(limitations) >= 1
            )
        )
);

create unique index uq_vnext_spatial_observation_source_record
    on vnext_core.spatial_observations (
        workspace_id, subject_type, subject_id,
        spatial_layer_id, source_id, provider_id, source_record_id
    ) where source_record_id is not null;

create index idx_vnext_spatial_observations_subject
    on vnext_core.spatial_observations (
        workspace_id, subject_type, subject_id, retrieved_at desc
    );

create index idx_vnext_spatial_observations_geometry
    on vnext_core.spatial_observations (
        workspace_id, parcel_geometry_id, retrieved_at desc
    ) where parcel_geometry_id is not null;

create index idx_vnext_spatial_observations_layer
    on vnext_core.spatial_observations (
        workspace_id, spatial_layer_id, retrieved_at desc
    );

create function vnext_private.guard_spatial_append_only()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    raise exception using errcode = '42501', message = 'vnext_spatial_history_is_append_only';
end
$$;

revoke all on function vnext_private.guard_spatial_append_only() from public;

create trigger trg_vnext_spatial_layers_append_only
before update or delete on vnext_core.spatial_layers
for each row execute function vnext_private.guard_spatial_append_only();

create trigger trg_vnext_parcel_geometry_append_only
before update or delete on vnext_core.parcel_geometry_versions
for each row execute function vnext_private.guard_spatial_append_only();

create trigger trg_vnext_spatial_observations_append_only
before update or delete on vnext_core.spatial_observations
for each row execute function vnext_private.guard_spatial_append_only();

create function vnext_private.guard_parcel_geometry_version()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
    parent vnext_core.parcel_geometry_versions%rowtype;
    linked_evidence vnext_core.evidence_items%rowtype;
begin
    if not exists (
        select 1
        from vnext_core.property_identity_references reference
        where reference.workspace_id = new.workspace_id
          and reference.identity_reference_id = new.parcel_identity_reference_id
          and reference.reference_type = 'parcel'
    ) then
        raise exception using errcode = '23514', message = 'vnext_spatial_parcel_reference_invalid';
    end if;

    if new.supersedes_geometry_id is not null then
        select * into parent
        from vnext_core.parcel_geometry_versions geometry
        where geometry.workspace_id = new.workspace_id
          and geometry.parcel_geometry_id = new.supersedes_geometry_id;
        if not found
           or parent.parcel_identity_reference_id <> new.parcel_identity_reference_id
           or new.geometry_version <> parent.geometry_version + 1 then
            raise exception using errcode = '23514', message = 'vnext_spatial_geometry_supersession_invalid';
        end if;
    end if;

    select * into linked_evidence
    from vnext_core.evidence_items evidence
    where evidence.workspace_id = new.workspace_id
      and evidence.evidence_id = new.evidence_id;
    if not found
       or linked_evidence.fact_type <> 'spatial.parcel_geometry.v1'
       or linked_evidence.source_id <> new.source_id
       or linked_evidence.source_type <> new.source_type
       or linked_evidence.source_environment <> new.source_environment
       or linked_evidence.provider is distinct from new.provider_id
       or linked_evidence.retrieved_at <> new.retrieved_at then
        raise exception using errcode = '23514', message = 'vnext_spatial_geometry_evidence_invalid';
    end if;

    if not exists (
        select 1
        from vnext_private.idempotency_records idempotency
        where idempotency.workspace_id = new.workspace_id
          and idempotency.idempotency_record_id = new.idempotency_record_id
          and idempotency.actor_user_id = new.created_by_user_id
          and idempotency.http_method = 'POST'
          and idempotency.canonical_route = '/internal/vnext/spatial/parcel-geometries'
          and idempotency.operation_status = 'pending'
    ) then
        raise exception using errcode = '23514', message = 'vnext_spatial_geometry_idempotency_invalid';
    end if;
    return new;
end
$$;

revoke all on function vnext_private.guard_parcel_geometry_version() from public;

create trigger trg_vnext_parcel_geometry_guard
before insert on vnext_core.parcel_geometry_versions
for each row execute function vnext_private.guard_parcel_geometry_version();

create function vnext_private.guard_spatial_observation()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
    selected_layer vnext_core.spatial_layers%rowtype;
    linked_evidence vnext_core.evidence_items%rowtype;
    expected_evidence_status text;
begin
    if new.subject_type = 'property' then
        if not exists (
            select 1 from vnext_core.property_entities property
            where property.workspace_id = new.workspace_id
              and property.property_entity_id = new.subject_id
        ) then
            raise exception using errcode = '23514', message = 'vnext_spatial_subject_invalid';
        end if;
    elsif new.subject_type in (
        'identity_reference', 'address', 'geo_reference', 'parcel', 'building'
    ) then
        if not exists (
            select 1 from vnext_core.property_identity_references reference
            where reference.workspace_id = new.workspace_id
              and reference.identity_reference_id = new.subject_id
              and (
                  new.subject_type = 'identity_reference'
                  or reference.reference_type = new.subject_type
              )
        ) then
            raise exception using errcode = '23514', message = 'vnext_spatial_subject_invalid';
        end if;
        if new.parcel_geometry_id is not null and not exists (
            select 1 from vnext_core.parcel_geometry_versions geometry
            where geometry.workspace_id = new.workspace_id
              and geometry.parcel_geometry_id = new.parcel_geometry_id
              and geometry.parcel_identity_reference_id = new.subject_id
        ) then
            raise exception using errcode = '23514', message = 'vnext_spatial_subject_geometry_invalid';
        end if;
    elsif new.subject_type = 'case' then
        if not exists (
            select 1 from vnext_core.cases case_record
            where case_record.workspace_id = new.workspace_id
              and case_record.case_id = new.subject_id
        ) then
            raise exception using errcode = '23514', message = 'vnext_spatial_subject_invalid';
        end if;
    else
        raise exception using errcode = '23514', message = 'vnext_spatial_subject_invalid';
    end if;

    select * into selected_layer
    from vnext_core.spatial_layers layer
    where layer.spatial_layer_id = new.spatial_layer_id;
    if not found
       or selected_layer.provider_id <> new.provider_id
       or selected_layer.source_id <> new.source_id
       or selected_layer.source_type <> new.source_type
       or selected_layer.source_environment <> new.source_environment
       or selected_layer.authority_class <> new.authority_class then
        raise exception using errcode = '23514', message = 'vnext_spatial_layer_provenance_invalid';
    end if;

    expected_evidence_status := case new.observation_status
        when 'present' then 'available'
        when 'absent' then 'available'
        when 'no_match' then 'unknown'
        when 'unavailable' then 'unavailable'
        when 'unknown' then 'unknown'
        when 'partial_coverage' then 'limited'
        when 'provider_error' then 'unavailable'
        when 'stale' then 'stale'
        when 'not_assessed' then 'unknown'
    end;
    select * into linked_evidence
    from vnext_core.evidence_items evidence
    where evidence.workspace_id = new.workspace_id
      and evidence.evidence_id = new.evidence_id;
    if not found
       or linked_evidence.fact_type <> 'spatial.layer_observation.v1'
       or linked_evidence.source_id <> new.source_id
       or linked_evidence.source_type <> new.source_type
       or linked_evidence.source_environment <> new.source_environment
       or linked_evidence.provider is distinct from new.provider_id
       or linked_evidence.retrieved_at <> new.retrieved_at
       or linked_evidence.evidence_status <> expected_evidence_status
       or linked_evidence.coverage_status <> (case new.coverage_status
            when 'complete' then 'known'
            else new.coverage_status
          end) then
        raise exception using errcode = '23514', message = 'vnext_spatial_observation_evidence_invalid';
    end if;

    if not exists (
        select 1
        from vnext_private.idempotency_records idempotency
        where idempotency.workspace_id = new.workspace_id
          and idempotency.idempotency_record_id = new.idempotency_record_id
          and idempotency.actor_user_id = new.created_by_user_id
          and idempotency.http_method = 'POST'
          and idempotency.canonical_route = '/internal/vnext/spatial/observations'
          and idempotency.operation_status = 'pending'
    ) then
        raise exception using errcode = '23514', message = 'vnext_spatial_observation_idempotency_invalid';
    end if;
    return new;
end
$$;

revoke all on function vnext_private.guard_spatial_observation() from public;

create trigger trg_vnext_spatial_observations_guard
before insert on vnext_core.spatial_observations
for each row execute function vnext_private.guard_spatial_observation();

alter table vnext_core.parcel_geometry_versions enable row level security;
alter table vnext_core.parcel_geometry_versions force row level security;
alter table vnext_core.spatial_observations enable row level security;
alter table vnext_core.spatial_observations force row level security;

revoke all on table vnext_core.spatial_layers from public;
revoke all on table vnext_core.parcel_geometry_versions from public;
revoke all on table vnext_core.spatial_observations from public;

grant select on vnext_core.spatial_layers to vnext_api;
grant select, insert on vnext_core.parcel_geometry_versions to vnext_api;
grant select, insert on vnext_core.spatial_observations to vnext_api;

create policy parcel_geometry_active_member_select
on vnext_core.parcel_geometry_versions
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = parcel_geometry_versions.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy parcel_geometry_active_writer_insert
on vnext_core.parcel_geometry_versions
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = parcel_geometry_versions.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

create policy spatial_observations_active_member_select
on vnext_core.spatial_observations
for select
to vnext_api
using (
    exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = spatial_observations.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    )
);

create policy spatial_observations_active_writer_insert
on vnext_core.spatial_observations
for insert
to vnext_api
with check (
    created_by_user_id = (select auth.uid())
    and exists (
        select 1 from vnext_core.workspace_members member
        where member.workspace_id = spatial_observations.workspace_id
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'manager', 'member')
    )
);

comment on table vnext_core.spatial_layers is
    'Global immutable system metadata. Registry rows contain no credentials; application principals are read-only.';
comment on table vnext_core.parcel_geometry_versions is
    'Tenant-scoped append-only parcel geometry evidence. Persistence never confirms parcel identity.';
comment on table vnext_core.spatial_observations is
    'Tenant-scoped append-only spatial observations preserving unknown, unavailable, no-match, partial, and provider-error states.';
