"""RLS-backed bounded reads for PropertyEntity, graph, and Evidence APIs."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any
from uuid import UUID

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.authorization import WorkspaceAuthorizer
from services.vnext.db_principal import DatabasePrincipalContext
from services.vnext.errors import VNextError
from services.vnext.property_graph import (
    _EVIDENCE_COLUMNS,
    _PROPERTY_COLUMNS,
    _RELATION_COLUMNS,
    EvidenceRecord,
    EvidenceStatus,
    IdentityReferenceStatus,
    PropertyEntityRecord,
    PropertyRelationRecord,
    PropertyRelationStatus,
    PropertyRelationType,
    SourceEnvironment,
    SourceType,
    _evidence_record,
    _property_record,
    _relation_record,
)

MAX_READ_LIMIT = 100
_PROPERTY_READ_COLUMNS = ", ".join(
    f"property.{column.strip()}" for column in _PROPERTY_COLUMNS.split(",")
)


@dataclass(frozen=True)
class GraphPosition:
    created_at: datetime
    relation_id: UUID


@dataclass(frozen=True)
class EvidencePosition:
    fact_type: str
    effective_from: datetime | None
    retrieved_at: datetime
    evidence_id: UUID


@dataclass(frozen=True)
class PropertyGraphNodeRecord:
    property_graph_node_id: UUID
    workspace_id: UUID
    node_type: str
    record_id: UUID
    display_label: str
    reference_status: IdentityReferenceStatus | None
    source_id: str | None
    source_type: SourceType | None
    source_environment: SourceEnvironment | None
    valid_from: datetime | None
    valid_to: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class PropertyGraphPage:
    property: PropertyEntityRecord
    nodes: tuple[PropertyGraphNodeRecord, ...]
    relations: tuple[PropertyRelationRecord, ...]
    as_of: datetime | None
    next_position: GraphPosition | None


@dataclass(frozen=True)
class PropertyEvidencePage:
    property: PropertyEntityRecord
    evidence: tuple[EvidenceRecord, ...]
    next_position: EvidencePosition | None


def _node_record(row: tuple[Any, ...]) -> PropertyGraphNodeRecord:
    return PropertyGraphNodeRecord(
        property_graph_node_id=UUID(str(row[0])),
        workspace_id=UUID(str(row[1])),
        node_type=str(row[2]),
        record_id=UUID(str(row[3])),
        display_label=str(row[4]),
        reference_status=(
            None if row[5] is None else IdentityReferenceStatus(str(row[5]))
        ),
        source_id=None if row[6] is None else str(row[6]),
        source_type=None if row[7] is None else SourceType(str(row[7])),
        source_environment=(None if row[8] is None else SourceEnvironment(str(row[8]))),
        valid_from=row[9],
        valid_to=row[10],
        created_at=row[11],
    )


def _relation_filters(
    *,
    alias: str,
    as_of: datetime | None,
    relation_type: PropertyRelationType | None,
    status: PropertyRelationStatus | None,
) -> tuple[list[str], list[object]]:
    clauses: list[str] = []
    params: list[object] = []
    if relation_type is not None:
        clauses.append(f"{alias}.relation_type = %s")
        params.append(relation_type.value)
    if status is None:
        clauses.append(f"{alias}.relation_status IN ('confirmed', 'disputed')")
    else:
        clauses.append(f"{alias}.relation_status = %s")
        params.append(status.value)
    if as_of is not None:
        clauses.extend(
            (
                f"({alias}.valid_from IS NULL OR {alias}.valid_from <= %s)",
                f"({alias}.valid_to IS NULL OR {alias}.valid_to > %s)",
            )
        )
        params.extend((as_of, as_of))
    elif status is None:
        clauses.append(f"{alias}.valid_to IS NULL")
    return clauses, params


class PostgresPropertyReadRepository:
    """Read allowlisted property aggregates under app authorization and RLS."""

    def __init__(
        self,
        principal_context: DatabasePrincipalContext,
        authorizer: WorkspaceAuthorizer,
    ) -> None:
        self._principal_context = principal_context
        self._authorizer = authorizer

    def _find_property(
        self,
        *,
        principal: AuthenticatedPrincipal,
        property_entity_id: UUID,
    ) -> PropertyEntityRecord:
        with self._principal_context.transaction(principal) as connection:
            row = connection.execute(
                "SELECT " + _PROPERTY_READ_COLUMNS + ", node.property_graph_node_id, "
                "confirmation.identity_decision_id, confirmation.created_at, "
                "confirmation.actor_user_id, confirmation.identity_resolution_id "
                "FROM vnext_core.property_entities property "
                "JOIN vnext_core.property_graph_nodes node "
                "ON node.workspace_id = property.workspace_id "
                "AND node.node_type = 'property' "
                "AND node.record_id = property.property_entity_id "
                "LEFT JOIN LATERAL ("
                "SELECT decision.identity_decision_id, decision.created_at, "
                "decision.actor_user_id, decision.identity_resolution_id "
                "FROM vnext_core.identity_decisions decision "
                "WHERE decision.workspace_id = property.workspace_id "
                "AND decision.property_entity_id = property.property_entity_id "
                "AND decision.decision_type = 'confirmed' "
                "ORDER BY decision.created_at DESC, decision.identity_decision_id DESC "
                "LIMIT 1"
                ") confirmation ON true "
                "WHERE property.property_entity_id = %s",
                (property_entity_id,),
            ).fetchone()
        if row is None:
            raise VNextError.not_found()
        property_record = replace(
            _property_record(row[:9], row[9]),
            confirmation_id=(
                None if len(row) < 14 or row[10] is None else UUID(str(row[10]))
            ),
            confirmed_at=None if len(row) < 14 else row[11],
            confirmed_by_user_id=(
                None if len(row) < 14 or row[12] is None else UUID(str(row[12]))
            ),
            confirmed_resolution_id=(
                None if len(row) < 14 or row[13] is None else UUID(str(row[13]))
            ),
        )
        # The lookup above is already RLS-filtered. This second boundary keeps
        # application authorization explicit and fails closed on membership
        # infrastructure errors without turning a path UUID into an oracle.
        self._authorizer.require_workspace_access(
            principal,
            property_record.workspace_id,
        )
        return property_record

    def get_property(
        self,
        *,
        principal: AuthenticatedPrincipal,
        property_entity_id: UUID,
    ) -> PropertyEntityRecord:
        return self._find_property(
            principal=principal,
            property_entity_id=property_entity_id,
        )

    def get_graph(
        self,
        *,
        principal: AuthenticatedPrincipal,
        property_entity_id: UUID,
        as_of: datetime | None = None,
        relation_type: PropertyRelationType | None = None,
        status: PropertyRelationStatus | None = None,
        position: GraphPosition | None = None,
        limit: int = 25,
    ) -> PropertyGraphPage:
        if (
            limit < 1
            or limit > MAX_READ_LIMIT
            or as_of is not None
            and as_of.utcoffset() is None
        ):
            raise VNextError.validation_failed()
        property_record = self._find_property(
            principal=principal,
            property_entity_id=property_entity_id,
        )
        direct_clauses, direct_params = _relation_filters(
            alias="edge",
            as_of=as_of,
            relation_type=None,
            status=status,
        )
        relation_clauses, relation_params = _relation_filters(
            alias="relation",
            as_of=as_of,
            relation_type=relation_type,
            status=status,
        )
        cursor_clause = ""
        cursor_params: list[object] = []
        if position is not None:
            if position.created_at.utcoffset() is None:
                raise VNextError.validation_failed()
            cursor_clause = (
                " AND (relation.created_at, relation.property_relation_id) < (%s, %s)"
            )
            cursor_params.extend((position.created_at, position.relation_id))
        direct_sql = " AND ".join(direct_clauses)
        relation_sql = " AND ".join(relation_clauses)
        statement = (
            "WITH RECURSIVE connected_nodes(node_id, depth) AS ("
            "SELECT %s::uuid, 0 UNION SELECT CASE "
            "WHEN edge.from_node_id = connected.node_id THEN edge.to_node_id "
            "ELSE edge.from_node_id END, connected.depth + 1 "
            "FROM vnext_core.property_relations edge "
            "JOIN connected_nodes connected ON "
            "edge.from_node_id = connected.node_id OR edge.to_node_id = connected.node_id "
            "WHERE edge.workspace_id = %s AND connected.depth < 2 "
            f"AND {direct_sql}"
            ") SELECT "
            + _RELATION_COLUMNS
            + " FROM vnext_core.property_relations relation "
            "WHERE relation.workspace_id = %s "
            "AND relation.from_node_id IN (SELECT node_id FROM connected_nodes) "
            "AND relation.to_node_id IN (SELECT node_id FROM connected_nodes) "
            f"AND {relation_sql}{cursor_clause} "
            "ORDER BY relation.created_at DESC, relation.property_relation_id DESC LIMIT %s"
        )
        params = [
            property_record.property_graph_node_id,
            property_record.workspace_id,
            *direct_params,
            property_record.workspace_id,
            *relation_params,
            *cursor_params,
            limit + 1,
        ]
        with self._principal_context.transaction(principal) as connection:
            rows = connection.execute(statement, tuple(params)).fetchall()
            has_more = len(rows) > limit
            selected_rows = rows[:limit]
            node_ids = {property_record.property_graph_node_id}
            for row in selected_rows:
                node_ids.add(UUID(str(row[2])))
                node_ids.add(UUID(str(row[3])))
            node_rows = connection.execute(
                "SELECT node.property_graph_node_id, node.workspace_id, node.node_type, "
                "node.record_id, COALESCE(property.display_label, reference.display_value), "
                "reference.reference_status, reference.source_id, reference.source_type, "
                "reference.source_environment, reference.valid_from, reference.valid_to, "
                "node.created_at FROM vnext_core.property_graph_nodes node "
                "LEFT JOIN vnext_core.property_entities property "
                "ON node.workspace_id = property.workspace_id "
                "AND node.node_type = 'property' AND node.record_id = property.property_entity_id "
                "LEFT JOIN vnext_core.property_identity_references reference "
                "ON node.workspace_id = reference.workspace_id "
                "AND node.node_type = reference.reference_type "
                "AND node.record_id = reference.identity_reference_id "
                "WHERE node.workspace_id = %s AND node.property_graph_node_id = ANY(%s) "
                "ORDER BY node.node_type, node.property_graph_node_id",
                (property_record.workspace_id, list(node_ids)),
            ).fetchall()
        relations = tuple(_relation_record(row) for row in selected_rows)
        next_position = None
        if has_more and selected_rows:
            last = selected_rows[-1]
            next_position = GraphPosition(
                created_at=last[17],
                relation_id=UUID(str(last[0])),
            )
        return PropertyGraphPage(
            property=property_record,
            nodes=tuple(_node_record(row) for row in node_rows),
            relations=relations,
            as_of=as_of,
            next_position=next_position,
        )

    def get_evidence(
        self,
        *,
        principal: AuthenticatedPrincipal,
        property_entity_id: UUID,
        fact_type: str | None = None,
        status: EvidenceStatus | None = None,
        effective_at: datetime | None = None,
        position: EvidencePosition | None = None,
        limit: int = 25,
    ) -> PropertyEvidencePage:
        if (
            limit < 1
            or limit > MAX_READ_LIMIT
            or effective_at is not None
            and effective_at.utcoffset() is None
            or fact_type is not None
            and (len(fact_type) > 120 or not fact_type)
        ):
            raise VNextError.validation_failed()
        property_record = self._find_property(
            principal=principal,
            property_entity_id=property_entity_id,
        )
        filters: list[str] = []
        filter_params: list[object] = []
        if fact_type is not None:
            filters.append("evidence.fact_type = %s")
            filter_params.append(fact_type)
        if status is not None:
            filters.append("evidence.evidence_status = %s")
            filter_params.append(status.value)
        if effective_at is not None:
            filters.extend(
                (
                    "(evidence.effective_from IS NULL OR evidence.effective_from <= %s)",
                    "(evidence.effective_to IS NULL OR evidence.effective_to > %s)",
                )
            )
            filter_params.extend((effective_at, effective_at))
        cursor_sql = ""
        cursor_params: list[object] = []
        if position is not None:
            if position.retrieved_at.utcoffset() is None or (
                position.effective_from is not None
                and position.effective_from.utcoffset() is None
            ):
                raise VNextError.validation_failed()
            cursor_sql = (
                " AND (evidence.fact_type > %s "
                "OR (evidence.fact_type = %s AND "
                "COALESCE(evidence.effective_from, '-infinity'::timestamptz) "
                "< COALESCE(%s::timestamptz, '-infinity'::timestamptz)) "
                "OR (evidence.fact_type = %s AND "
                "COALESCE(evidence.effective_from, '-infinity'::timestamptz) "
                "= COALESCE(%s::timestamptz, '-infinity'::timestamptz) "
                "AND evidence.retrieved_at < %s) "
                "OR (evidence.fact_type = %s AND "
                "COALESCE(evidence.effective_from, '-infinity'::timestamptz) "
                "= COALESCE(%s::timestamptz, '-infinity'::timestamptz) "
                "AND evidence.retrieved_at = %s AND evidence.evidence_id > %s))"
            )
            cursor_params.extend(
                (
                    position.fact_type,
                    position.fact_type,
                    position.effective_from,
                    position.fact_type,
                    position.effective_from,
                    position.retrieved_at,
                    position.fact_type,
                    position.effective_from,
                    position.retrieved_at,
                    position.evidence_id,
                )
            )
        filter_sql = "" if not filters else " AND " + " AND ".join(filters)
        statement = (
            "WITH RECURSIVE subject_nodes(node_id, depth) AS ("
            "SELECT %s::uuid, 0 UNION SELECT CASE "
            "WHEN relation.from_node_id = subject.node_id THEN relation.to_node_id "
            "ELSE relation.from_node_id END, subject.depth + 1 "
            "FROM vnext_core.property_relations relation "
            "JOIN subject_nodes subject ON "
            "relation.from_node_id = subject.node_id OR relation.to_node_id = subject.node_id "
            "WHERE relation.workspace_id = %s AND subject.depth < 2), "
            "direct_evidence(evidence_id) AS ("
            "SELECT link.evidence_id FROM vnext_core.evidence_links link "
            "WHERE link.workspace_id = %s "
            "AND link.subject_node_id IN (SELECT node_id FROM subject_nodes) "
            "UNION SELECT relation.evidence_id "
            "FROM vnext_core.property_relations relation "
            "WHERE relation.workspace_id = %s AND relation.evidence_id IS NOT NULL "
            "AND relation.from_node_id IN (SELECT node_id FROM subject_nodes) "
            "AND relation.to_node_id IN (SELECT node_id FROM subject_nodes)), "
            "evidence_scope(evidence_id, depth) AS ("
            "SELECT evidence_id, 0 FROM direct_evidence UNION SELECT CASE "
            "WHEN lineage.child_evidence_id = scope.evidence_id "
            "THEN lineage.parent_evidence_id ELSE lineage.child_evidence_id END, "
            "scope.depth + 1 FROM vnext_core.evidence_lineage lineage "
            "JOIN evidence_scope scope ON lineage.child_evidence_id = scope.evidence_id "
            "OR lineage.parent_evidence_id = scope.evidence_id "
            "WHERE lineage.workspace_id = %s AND scope.depth < 8"
            ") SELECT "
            + _EVIDENCE_COLUMNS
            + " FROM vnext_core.evidence_items evidence "
            "WHERE evidence.workspace_id = %s "
            "AND evidence.evidence_id IN (SELECT evidence_id FROM evidence_scope)"
            f"{filter_sql}{cursor_sql} "
            "ORDER BY evidence.fact_type ASC, "
            "COALESCE(evidence.effective_from, '-infinity'::timestamptz) DESC, "
            "evidence.retrieved_at DESC, evidence.evidence_id ASC LIMIT %s"
        )
        params = (
            property_record.property_graph_node_id,
            property_record.workspace_id,
            property_record.workspace_id,
            property_record.workspace_id,
            property_record.workspace_id,
            property_record.workspace_id,
            *filter_params,
            *cursor_params,
            limit + 1,
        )
        with self._principal_context.transaction(principal) as connection:
            rows = connection.execute(statement, params).fetchall()
        has_more = len(rows) > limit
        selected_rows = rows[:limit]
        evidence = tuple(_evidence_record(row) for row in selected_rows)
        next_position = None
        if has_more and evidence:
            last = evidence[-1]
            next_position = EvidencePosition(
                fact_type=last.fact_type,
                effective_from=last.effective_from,
                retrieved_at=last.retrieved_at,
                evidence_id=last.evidence_id,
            )
        return PropertyEvidencePage(
            property=property_record,
            evidence=evidence,
            next_position=next_position,
        )
