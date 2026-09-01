"""Atomic RLS-backed persistence for explicit legacy Case imports."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.errors import ErrorCode, VNextError
from services.vnext.legacy_case_import import (
    LEGACY_FORMAT,
    LEGACY_IMPORT_MODE,
    LEGACY_SCHEMA_VERSION,
    LegacyEvidenceDraft,
    ParsedLegacyCase,
)
from services.vnext.persistence import (
    CASE_WRITE_ROLES,
    _CASE_COLUMNS,
    _append_audit,
    _bounded_text,
    _case_record,
    CaseRecord,
)


_HASH = re.compile(r"^[0-9a-f]{64}$")
_IMPORT_COLUMNS = (
    "legacy_case_import_id, workspace_id, case_id, actor_user_id, legacy_format, "
    "legacy_client_id_hash, schema_version, import_mode, imported_at, "
    "client_created_at, client_updated_at, accepted_field_classes, "
    "dropped_field_classes, warnings, idempotency_record_id, request_id"
)


@dataclass(frozen=True)
class LegacyCaseImportRecord:
    legacy_case_import_id: UUID
    workspace_id: UUID
    case_id: UUID
    actor_user_id: UUID
    legacy_format: str
    legacy_client_id_hash: str
    schema_version: int
    import_mode: str
    imported_at: datetime
    client_created_at: datetime | None
    client_updated_at: datetime | None
    accepted_field_classes: tuple[str, ...]
    dropped_field_classes: tuple[str, ...]
    warnings: tuple[str, ...]
    idempotency_record_id: UUID
    request_id: str


@dataclass(frozen=True)
class LegacyImportWriteResult:
    case: CaseRecord
    import_record: LegacyCaseImportRecord
    evidence_ids: tuple[UUID, ...]


def _import_record(row: tuple[Any, ...]) -> LegacyCaseImportRecord:
    return LegacyCaseImportRecord(
        legacy_case_import_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        case_id=UUID(str(row[2])),
        actor_user_id=UUID(str(row[3])),
        legacy_format=str(row[4]),
        legacy_client_id_hash=str(row[5]),
        schema_version=int(row[6]),
        import_mode=str(row[7]),
        imported_at=row[8],
        client_created_at=row[9],
        client_updated_at=row[10],
        accepted_field_classes=tuple(str(item) for item in row[11]),
        dropped_field_classes=tuple(str(item) for item in row[12]),
        warnings=tuple(str(item) for item in row[13]),
        idempotency_record_id=UUID(str(row[14])),
        request_id=str(row[15]),
    )


def _json(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    if len(encoded.encode("utf-8")) > 16_384:
        raise VNextError.validation_failed()
    return encoded


def _content_hash(draft: LegacyEvidenceDraft) -> str:
    return hashlib.sha256(
        _json(
            {
                "fact_type": draft.fact_type,
                "value": draft.value,
                "value_schema": draft.value_schema,
                "status": draft.evidence_status,
                "coverage_status": draft.coverage_status,
                "quality_status": draft.quality_status,
            }
        ).encode("utf-8")
    ).hexdigest()


def _database_error(error: Exception) -> VNextError:
    sqlstate = str(getattr(error, "sqlstate", ""))
    constraint = str(getattr(getattr(error, "diag", None), "constraint_name", ""))
    if sqlstate == "23505" and constraint == "uq_vnext_legacy_import_scoped_client":
        return VNextError.duplicate_legacy_import(
            details={"import_status": "duplicate_requires_explicit_choice"}
        )
    if sqlstate == "42501":
        return VNextError.permission_denied()
    if sqlstate == "23503":
        return VNextError.not_found()
    if sqlstate == "23514":
        return VNextError.validation_failed()
    if sqlstate in {"23505", "40001", "40P01"}:
        return VNextError(ErrorCode.MAINTENANCE)
    return VNextError(ErrorCode.INTERNAL_ERROR)


class PostgresLegacyCaseImportRepository:
    """Persist the Case, import record, evidence, audit, and completion atomically."""

    def __init__(
        self,
        principal_context: DatabasePrincipalContext,
        authorizer: WorkspaceAuthorizer,
    ) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    def get_import_by_id(
        self,
        *,
        principal: AuthenticatedPrincipal,
        legacy_case_import_id: UUID,
    ) -> LegacyImportWriteResult:
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT " + _IMPORT_COLUMNS + " FROM vnext_private.legacy_case_imports "
                "WHERE legacy_case_import_id = %s",
                (legacy_case_import_id,),
            ).fetchone()
            if row is None:
                raise VNextError.not_found()
            record = _import_record(row)
            case_row = connection.execute(
                "SELECT " + _CASE_COLUMNS + " FROM vnext_core.cases "
                "WHERE workspace_id = %s AND case_id = %s",
                (record.workspace_id, record.case_id),
            ).fetchone()
            if case_row is None:
                raise VNextError.not_found()
            evidence_rows = connection.execute(
                "SELECT evidence.evidence_id FROM vnext_core.evidence_items evidence "
                "JOIN vnext_core.evidence_links link "
                "ON link.workspace_id = evidence.workspace_id "
                "AND link.evidence_id = evidence.evidence_id "
                "JOIN vnext_core.property_graph_nodes node "
                "ON node.workspace_id = link.workspace_id "
                "AND node.property_graph_node_id = link.subject_node_id "
                "WHERE node.workspace_id = %s AND node.node_type = 'case' "
                "AND node.record_id = %s AND evidence.source_id = 'legacy-saved-case-v1' "
                "ORDER BY evidence.created_at, evidence.evidence_id",
                (record.workspace_id, record.case_id),
            ).fetchall()
        self._authorizer.require_workspace_role(
            principal, record.workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        return LegacyImportWriteResult(
            case=_case_record(case_row),
            import_record=record,
            evidence_ids=tuple(UUID(str(item[0])) for item in evidence_rows),
        )

    def import_case(
        self,
        *,
        principal: AuthenticatedPrincipal,
        workspace_id: UUID,
        legacy_client_id_hash: str,
        parsed: ParsedLegacyCase,
        request_id: str,
        idempotency_record_id: UUID,
    ) -> LegacyImportWriteResult:
        membership = self._authorizer.require_workspace_role(
            principal, workspace_id, allowed_roles=CASE_WRITE_ROLES
        )
        if not _HASH.fullmatch(legacy_client_id_hash):
            raise VNextError.validation_failed()
        selected_request_id = _bounded_text(request_id, maximum=128)
        import_id = uuid4()
        try:
            with self._principal_context.transaction(principal) as connection:
                duplicate = connection.execute(
                    "SELECT case_id FROM vnext_private.legacy_case_imports "
                    "WHERE workspace_id = %s AND actor_user_id = %s "
                    "AND legacy_format = %s AND legacy_client_id_hash = %s",
                    (workspace_id, principal.user_id, LEGACY_FORMAT, legacy_client_id_hash),
                ).fetchone()
                if duplicate is not None:
                    raise VNextError.duplicate_legacy_import(
                        details={
                            "import_status": "duplicate_requires_explicit_choice",
                            "existing_case_id": str(duplicate[0]),
                        }
                    )
                idempotency = connection.execute(
                    "SELECT idempotency_key_hash FROM vnext_private.idempotency_records "
                    "WHERE workspace_id = %s AND actor_user_id = %s "
                    "AND idempotency_record_id = %s AND http_method = 'POST' "
                    "AND canonical_route = '/v1/cases/import-legacy' "
                    "AND operation_status = 'pending' FOR UPDATE",
                    (workspace_id, principal.user_id, idempotency_record_id),
                ).fetchone()
                if idempotency is None:
                    raise VNextError.idempotency_conflict()
                idempotency_key_hash = str(idempotency[0])

                case_row = connection.execute(
                    "INSERT INTO vnext_core.cases ("
                    "workspace_id, purpose, status, title, identity_status, created_by_user_id"
                    ") VALUES (%s, 'buy_due_diligence', 'open', %s, 'legacy_unverified', %s) "
                    "RETURNING " + _CASE_COLUMNS,
                    (workspace_id, parsed.title, principal.user_id),
                ).fetchone()
                if case_row is None:
                    raise VNextError.permission_denied()
                case = _case_record(case_row)
                node_row = connection.execute(
                    "INSERT INTO vnext_core.property_graph_nodes ("
                    "workspace_id, node_type, record_id, created_by_user_id"
                    ") VALUES (%s, 'case', %s, %s) RETURNING property_graph_node_id",
                    (workspace_id, case.case_id, principal.user_id),
                ).fetchone()
                if node_row is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                case_node_id = UUID(str(node_row[0]))

                evidence_ids: list[UUID] = []
                for draft in parsed.evidence:
                    evidence_id = uuid4()
                    coverage = {
                        "geography": {"status": draft.coverage_status},
                        "time": {"status": "unknown"},
                        "subject_scope": "case",
                        "fields": sorted(draft.value) if draft.value else [],
                        "gaps": list(draft.limitations),
                    }
                    quality = {
                        "validation_status": draft.quality_status,
                        "source_record_status": "user",
                        "limitations": list(draft.limitations),
                    }
                    lineage = {
                        "source_record_id_hash": legacy_client_id_hash,
                        "transformation": "legacy_import_allowlist",
                        "transformation_version": "saved-case-v1-import-v1",
                        "source_schema_version": LEGACY_SCHEMA_VERSION,
                    }
                    connection.execute(
                        "INSERT INTO vnext_core.evidence_items ("
                        "evidence_id, workspace_id, fact_type, value, value_schema, source_id, "
                        "source_type, source_environment, retrieved_at, coverage_status, "
                        "coverage, evidence_status, quality_status, quality, license_status, "
                        "license, lineage, content_hash, created_by_user_id"
                        ") VALUES (%s, %s, %s, %s::jsonb, %s, 'legacy-saved-case-v1', "
                        "'user', 'production', clock_timestamp(), %s, %s::jsonb, %s, %s, "
                        "%s::jsonb, 'not_applicable', '{}'::jsonb, %s::jsonb, %s, %s)",
                        (
                            evidence_id, workspace_id, draft.fact_type,
                            None if draft.value is None else _json(draft.value),
                            draft.value_schema, draft.coverage_status, _json(coverage),
                            draft.evidence_status, draft.quality_status, _json(quality),
                            _json(lineage), _content_hash(draft), principal.user_id,
                        ),
                    )
                    connection.execute(
                        "INSERT INTO vnext_core.evidence_links ("
                        "workspace_id, evidence_id, subject_node_id, link_type, fact_scope, "
                        "created_by_user_id) VALUES (%s, %s, %s, 'describes', %s, %s)",
                        (workspace_id, evidence_id, case_node_id, draft.fact_type, principal.user_id),
                    )
                    evidence_ids.append(evidence_id)

                import_row = connection.execute(
                    "INSERT INTO vnext_private.legacy_case_imports ("
                    "legacy_case_import_id, workspace_id, case_id, actor_user_id, legacy_format, "
                    "legacy_client_id_hash, schema_version, import_mode, client_created_at, "
                    "client_updated_at, accepted_field_classes, dropped_field_classes, warnings, "
                    "idempotency_record_id, request_id"
                    ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "RETURNING " + _IMPORT_COLUMNS,
                    (
                        import_id, workspace_id, case.case_id, principal.user_id, LEGACY_FORMAT,
                        legacy_client_id_hash, LEGACY_SCHEMA_VERSION, LEGACY_IMPORT_MODE,
                        parsed.client_created_at, parsed.client_updated_at,
                        list(parsed.accepted_field_classes), list(parsed.dropped_field_classes),
                        list(parsed.warnings), idempotency_record_id, selected_request_id,
                    ),
                ).fetchone()
                if import_row is None:
                    raise VNextError(ErrorCode.INTERNAL_ERROR)
                record = _import_record(import_row)
                _append_audit(
                    connection,
                    principal=principal,
                    workspace_id=workspace_id,
                    event_type="legacy_case.imported",
                    resource_type="case",
                    resource_id=case.case_id,
                    request_id=selected_request_id,
                    outcome="succeeded",
                    idempotency_key_hash=idempotency_key_hash,
                    metadata={
                        "operation_status": "imported_unverified",
                        "membership_role": membership.role.value,
                        "new_version": case.version,
                        "legacy_format": LEGACY_FORMAT,
                        "legacy_case_import_id": str(import_id),
                        "accepted_field_classes": list(parsed.accepted_field_classes),
                        "dropped_field_classes": list(parsed.dropped_field_classes),
                        "warning_codes": list(parsed.warnings),
                    },
                )
                completed = connection.execute(
                    "UPDATE vnext_private.idempotency_records SET "
                    "operation_status = 'succeeded', response_status_code = 201, "
                    "response_reference_type = 'legacy_case_import', "
                    "response_reference_id = %s, updated_at = clock_timestamp() "
                    "WHERE workspace_id = %s AND actor_user_id = %s "
                    "AND idempotency_record_id = %s AND operation_status = 'pending' "
                    "RETURNING idempotency_record_id",
                    (import_id, workspace_id, principal.user_id, idempotency_record_id),
                ).fetchone()
                if completed is None:
                    raise VNextError.idempotency_conflict()
                return LegacyImportWriteResult(
                    case=case,
                    import_record=record,
                    evidence_ids=tuple(evidence_ids),
                )
        except VNextError:
            raise
        except Exception as error:
            raise _database_error(error) from None
